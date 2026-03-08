/*
 * Cloud-Based Hash Verification (CBHV) — ESP32 Sender
 *
 * Reads BME280 sensor data, computes SHA-256 of the message using the
 * built-in mbedTLS library, uploads the hash to Firebase Realtime DB
 * over HTTPS, then publishes raw data over MQTT for verification.
 *
 * Payload structure:
 *   [msg_bytes (variable)] [seq_num (4)] [hash_time_us (4)] [upload_latency_us (4)]
 *
 * Libraries required (Arduino Library Manager):
 *   - PubSubClient   (Nick O'Leary)
 *   - Adafruit BME280
 *   - Adafruit Unified Sensor
 *
 * Built-in ESP32 (no install needed):
 *   - WiFi.h, HTTPClient.h, WiFiClientSecure.h, mbedtls/sha256.h
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
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
// STRESS CONFIG
// ---------------------------------------------------------------------------
#define STRESS_ENABLED 1   // Set to 0 to disable
#define STRESS_CORE    0   // Core 0 handles WiFi; Core 1 handles Arduino loop

// ---------------------------------------------------------------------------
// CONFIGURATION
// ---------------------------------------------------------------------------
const char* ssid       = SECRET_SSID;
const char* password   = SECRET_PASS;
const char* mqtt_server = "laptop.local";   // <--- CHANGE TO YOUR LAPTOP IP/HOSTNAME
const int   mqtt_port  = 1883;
const char* topic      = "therm/cbhv";

// Firebase Realtime Database URL (no trailing slash)
// Must match broker_cbhv.py on the laptop
const char* FIREBASE_URL = "https://senior-project-bdb33-default-rtdb.firebaseio.com";

// Sentinel written when Firebase upload fails (max uint32)
#define UPLOAD_FAILED_SENTINEL 0xFFFFFFFFUL

// Publish interval (milliseconds). Kept at 10 ms to match original benchmark.
// NOTE: Firebase HTTPS round-trips (~100-200 ms) will throttle effective rate —
// this is an intentional, measurable cost of CBHV on constrained hardware.
#define PUBLISH_INTERVAL_MS 10

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
uint32_t seqNum       = 0;
unsigned long lastPublish = 0;

// ---------------------------------------------------------------------------
// STRESS TASK (optional background load, same as original)
// ---------------------------------------------------------------------------
void stressTask(void* pvParameters) {
    volatile float x = 1.5f;
    while (true) {
        for (int i = 0; i < 1000; i++) {
            x = sqrt(x * 3.14159f / 2.71828f);
            if (x > 1000.0f || x < 0.1f) x = 1.5f;
        }
        vTaskDelay(1);
    }
}

// ---------------------------------------------------------------------------
// FIREBASE UPLOAD
// Uploads {"hash":"<hexstring>"} to /hashes/<seq>.json via HTTPS PUT.
// Returns round-trip latency in microseconds, or UPLOAD_FAILED_SENTINEL.
// ---------------------------------------------------------------------------
uint32_t uploadHash(uint32_t seq, const char* hashHex) {
    char url[128];
    snprintf(url, sizeof(url), "%s/hashes/%lu.json", FIREBASE_URL, (unsigned long)seq);

    // Use WiFiClientSecure with certificate verification disabled.
    // Acceptable for a closed lab benchmark; do not use in production.
    WiFiClientSecure secureClient;
    secureClient.setInsecure();

    HTTPClient http;
    http.begin(secureClient, url);
    http.addHeader("Content-Type", "application/json");

    char body[80];
    snprintf(body, sizeof(body), "{\"hash\":\"%s\"}", hashHex);

    uint32_t t_start = micros();
    int httpCode = http.PUT(body);
    uint32_t latency_us = micros() - t_start;

    http.end();

    if (httpCode != 200) {
        Serial.printf("[Firebase] PUT failed seq=%lu  HTTP %d\n", (unsigned long)seq, httpCode);
        return UPLOAD_FAILED_SENTINEL;
    }
    return latency_us;
}

// ---------------------------------------------------------------------------
// SHA-256 HELPER
// Uses mbedTLS (built into ESP32 Arduino). Fills hashHex with 64-char hex + \0.
// Returns duration in microseconds.
// ---------------------------------------------------------------------------
uint32_t sha256Hex(const uint8_t* data, size_t len, char* hashHex) {
    uint8_t hash[32];
    mbedtls_sha256_context ctx;
    mbedtls_sha256_init(&ctx);

    uint32_t t_start = micros();
    mbedtls_sha256_starts(&ctx, 0);          // 0 = SHA-256 (not SHA-224)
    mbedtls_sha256_update(&ctx, data, len);
    mbedtls_sha256_finish(&ctx, hash);
    uint32_t duration_us = micros() - t_start;

    mbedtls_sha256_free(&ctx);

    for (int i = 0; i < 32; i++) {
        sprintf(hashHex + (i * 2), "%02x", hash[i]);
    }
    hashHex[64] = '\0';
    return duration_us;
}

// ---------------------------------------------------------------------------
// MQTT RECONNECT
// ---------------------------------------------------------------------------
void reconnectMQTT() {
    while (!mqttClient.connected()) {
        String clientId = "ESP32-CBHV-" + String(random(0xffff), HEX);
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
    Serial.println("\n--- ESP32 CBHV START ---");
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

    // Stress task
    #if STRESS_ENABLED
        xTaskCreatePinnedToCore(stressTask, "StressTask", 2048, NULL, 1, NULL, STRESS_CORE);
        Serial.println("Background stressor started.");
    #endif

    Serial.printf("Firebase: %s\n", FIREBASE_URL);
    Serial.printf("MQTT:     %s:%d  topic: %s\n", mqtt_server, mqtt_port, topic);
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

        // 2. SHA-256 HASH & BENCHMARK
        char hashHex[65];
        uint32_t hashTime_us = sha256Hex((const uint8_t*)msgBuffer, msgLen, hashHex);

        // 3. UPLOAD TO FIREBASE
        uint32_t uploadLatency_us = uploadHash(seqNum, hashHex);

        // 4. BUILD MQTT PAYLOAD — [msg][seq(4)][hash_time(4)][upload_latency(4)]
        size_t payloadLen = msgLen + 12;
        uint8_t payload[payloadLen];

        memcpy(payload, msgBuffer, msgLen);
        memcpy(payload + msgLen,     &seqNum,           4);
        memcpy(payload + msgLen + 4, &hashTime_us,      4);
        memcpy(payload + msgLen + 8, &uploadLatency_us, 4);

        // 5. PUBLISH
        mqttClient.publish(topic, payload, payloadLen);

        if (seqNum % 100 == 0) {
            Serial.printf("Seq #%lu | Hash: %lu us | Upload: %lu us | %s\n",
                          (unsigned long)seqNum,
                          (unsigned long)hashTime_us,
                          (unsigned long)uploadLatency_us,
                          msgBuffer);
        }

        seqNum++;
    }
}
