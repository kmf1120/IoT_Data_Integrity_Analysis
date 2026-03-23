/*
 * Blockchain-style integrity sender — ESP32 (BME280)
 *
 * Treats each sensor reading as a block in a hash chain:
 *   prev_block_hash_(n) = block_hash_(n-1) (or 32x0 for genesis)
 *   msg_hash_n          = SHA256(msg_bytes)
 *   block_hash_n        = SHA256(prev_block_hash_n || msg_hash_n)
 *
 * Payload per MQTT message:
 *   [msg_bytes][index(4)][hash_time_us(4)][prev_block_hash(32)][block_hash(32)]
 *
 * Designed to pair with Broker/ESP32/Blockchain/broker_blockchain_esp32.py
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <Adafruit_BME280.h>
#include <mbedtls/sha256.h>
#include "wifi_secrets.h"

// ---------------------------------------------------------------------------
// DEBUG
// ---------------------------------------------------------------------------
#define DEBUG 0

#if DEBUG
  #define DEBUG_PRINT(x)   Serial.print(x)
  #define DEBUG_PRINTLN(x) Serial.println(x)
#else
  #define DEBUG_PRINT(x)
  #define DEBUG_PRINTLN(x)
#endif

// ---------------------------------------------------------------------------
// STRESS CONFIG (optional background CPU load)
// ---------------------------------------------------------------------------
#define STRESS_ENABLED 1   // Set to 0 to disable
#define STRESS_CORE    0   // Core 0 handles WiFi; Core 1 handles Arduino loop

// ---------------------------------------------------------------------------
// NETWORK / MQTT CONFIG
// ---------------------------------------------------------------------------
const char* ssid        = SECRET_SSID;
const char* password    = SECRET_PASS;
const char* mqtt_server = "laptop.local";   // <--- CHANGE TO YOUR LAPTOP IP/HOSTNAME
const int   mqtt_port   = 1883;
const char* topic       = "therm/blockchain";

// ---------------------------------------------------------------------------
// BME280
// ---------------------------------------------------------------------------
#define BME_SCK  18
#define BME_MISO 19
#define BME_MOSI 23
#define BME_CS    5
Adafruit_BME280 bme(BME_CS);

// ---------------------------------------------------------------------------
// MQTT
// ---------------------------------------------------------------------------
WiFiClient   espClient;
PubSubClient mqttClient(espClient);

// ---------------------------------------------------------------------------
// GLOBALS
// ---------------------------------------------------------------------------
uint32_t blockIndex        = 0;
unsigned long lastPublish  = 0;
#define PUBLISH_INTERVAL_MS 10

static uint8_t prev_block_hash[32] = {0};  // genesis

// ---------------------------------------------------------------------------
// STRESS TASK (~99% CPU load via 99:1 busy:idle duty cycle)
// ---------------------------------------------------------------------------
void stressTask(void* pvParameters) {
    const int busyTicks = 99;
    const int idleTicks = 1;
    volatile float x = 1.5f;

    while (true) {
        // Busy phase
        for (int i = 0; i < busyTicks; i++) {
            for (int j = 0; j < 1000; j++) {
                x = sqrt(x * 3.14159f / 2.71828f);
                if (x > 1000.0f || x < 0.1f) {
                    x = 1.5f;
                }
            }
        }

        // Idle phase
        for (int i = 0; i < idleTicks; i++) {
            vTaskDelay(1);
        }
    }
}

// ---------------------------------------------------------------------------
// SHA-256 HELPER — returns digest and duration (us)
// ---------------------------------------------------------------------------
uint32_t sha256Digest(const uint8_t* data, size_t len, uint8_t* out_digest) {
    mbedtls_sha256_context ctx;
    mbedtls_sha256_init(&ctx);

    uint32_t t_start = micros();
    mbedtls_sha256_starts(&ctx, 0);          // 0 = SHA-256 (not SHA-224)
    mbedtls_sha256_update(&ctx, data, len);
    mbedtls_sha256_finish(&ctx, out_digest);
    uint32_t duration_us = micros() - t_start;

    mbedtls_sha256_free(&ctx);
    return duration_us;
}

// ---------------------------------------------------------------------------
// MQTT RECONNECT
// ---------------------------------------------------------------------------
void reconnectMQTT() {
    while (!mqttClient.connected()) {
        String clientId = "ESP32-BC-" + String(random(0xffff), HEX);
        if (mqttClient.connect(clientId.c_str())) {
            DEBUG_PRINTLN("MQTT connected.");
        } else {
            delay(5000);
        }
    }
}

// ---------------------------------------------------------------------------
// SETUP
// ---------------------------------------------------------------------------
void setup() {
    Serial.begin(115200);
    while (!Serial) { delay(10); }

    delay(2000);
    Serial.println("\n--- ESP32 BLOCKCHAIN START ---");
    Serial.printf("Chip: %s  Rev: %d  CPU: %d MHz\n",
                  ESP.getChipModel(), ESP.getChipRevision(), ESP.getCpuFreqMHz());
    Serial.printf("Free Heap: %lu bytes\n", (unsigned long)ESP.getFreeHeap());

    // WiFi
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
    Serial.printf("\nWiFi connected: %s\n", WiFi.localIP().toString().c_str());

    // BME280
    SPI.begin(BME_SCK, BME_MISO, BME_MOSI, BME_CS);
    if (!bme.begin()) {
        Serial.println("BME280 not found! Check wiring.");
        while (1);
    }

    // MQTT
    mqttClient.setServer(mqtt_server, mqtt_port);

    // Optional stress task
    #if STRESS_ENABLED
        xTaskCreatePinnedToCore(stressTask, "StressTask", 2048, NULL, 1, NULL, STRESS_CORE);
        Serial.println("Background stressor started.");
    #endif

    Serial.printf("MQTT: %s:%d  topic: %s\n", mqtt_server, mqtt_port, topic);
    Serial.println("--- READY ---");
}

// ---------------------------------------------------------------------------
// LOOP
// ---------------------------------------------------------------------------
void loop() {
    if (!mqttClient.connected()) {
        reconnectMQTT();
    }
    mqttClient.loop();

    if (millis() - lastPublish >= PUBLISH_INTERVAL_MS) {
        lastPublish = millis();

        // 1. READ SENSOR
        float temp = bme.readTemperature();
        float hum  = bme.readHumidity();
        float pres = bme.readPressure() / 100.0F;

        char msgBuffer[64];
        size_t msgLen = snprintf(msgBuffer, sizeof(msgBuffer),
                                 "t=%.2f,h=%.2f,p=%.2f", temp, hum, pres);

        // 2. HASH MESSAGE & BUILD BLOCK
        uint8_t msg_hash[32];
        uint32_t hashTime_us = sha256Digest((const uint8_t*)msgBuffer, msgLen, msg_hash);

        uint8_t combined[64];
        memcpy(combined, prev_block_hash, 32);
        memcpy(combined + 32, msg_hash, 32);

        uint8_t block_hash[32];
        (void)sha256Digest(combined, sizeof(combined), block_hash);  // time not recorded separately

        // 3. BUILD FOOTER [index(4)][hash_time(4)][prev_hash(32)][block_hash(32)]
        uint8_t footer[72];
        memcpy(footer,      &blockIndex,    4);
        memcpy(footer + 4,  &hashTime_us,   4);
        memcpy(footer + 8,  prev_block_hash, 32);
        memcpy(footer + 40, block_hash,     32);

        // 4. BUILD PAYLOAD [msg_bytes][footer]
        size_t payloadLen = msgLen + sizeof(footer);
        uint8_t payload[payloadLen];
        memcpy(payload,           msgBuffer, msgLen);
        memcpy(payload + msgLen,  footer,    sizeof(footer));

        mqttClient.publish(topic, payload, payloadLen);

        if (blockIndex % 100 == 0) {
            Serial.printf("Block #%lu | Hash: %lu us | %s\n",
                          (unsigned long)blockIndex,
                          (unsigned long)hashTime_us,
                          msgBuffer);
        }

        memcpy(prev_block_hash, block_hash, 32);
        blockIndex++;
    }
}
