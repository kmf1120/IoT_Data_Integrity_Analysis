#include <WiFi.h>
#include <PubSubClient.h>
#include <Ed25519.h>
#include <SPI.h>
#include <Adafruit_BME280.h>
#include <wifi_secrets.h>

#define DEBUG 0 

#if DEBUG
  #define DEBUG_BEGIN(x) Serial.begin(x)
  #define DEBUG_PRINT(x) Serial.print(x)
  #define DEBUG_PRINTLN(x) Serial.println(x)
#else
  #define DEBUG_BEGIN(x)
  #define DEBUG_PRINT(x)
  #define DEBUG_PRINTLN(x)
#endif

// --- STRESS CONFIG ---
#define STRESS_ENABLED 1  // Set to 0 to disable
#define STRESS_CORE 0     // Core 0 handles WiFi, Core 1 handles Arduino loop

const char* ssid = SECRET_SSID;
const char* password = SECRET_PASS;
const char* mqtt_server = "laptop.local"; 
const int mqtt_port = 1883;
const char* topic = "therm";

#define BME_SCK 18
#define BME_MISO 19
#define BME_MOSI 23
#define BME_CS 5
Adafruit_BME280 bme(BME_CS);

#define ED25519_PRIVATE_KEY_SIZE 32
#define ED25519_PUBLIC_KEY_SIZE 32
#define ED25519_SIGNATURE_SIZE 64
uint8_t privateKey[ED25519_PRIVATE_KEY_SIZE];
uint8_t publicKey[ED25519_PUBLIC_KEY_SIZE];

WiFiClient espClient;
PubSubClient client(espClient);
unsigned long lastPublish = 0;

void reconnectMQTT(); 

// --- STRESS TASK ---
void stressTask(void * pvParameters) {
    volatile float x = 1.5; 
    while(true) {
        for(int i = 0; i < 1000; i++) {
            x = sqrt(x * 3.14159 / 2.71828);
            if (x > 1000.0 || x < 0.1) x = 1.5;
        }
        vTaskDelay(1); // Prevents Watchdog Timer (WDT) reset
    }
}

void setup() {
  DEBUG_BEGIN(115200);
  Serial.begin(115200);
  while (!Serial) { delay(10); } 
  
  delay(2000); 
  Serial.println("\n--- START OF LOG ---");
  Serial.println("### ESP32 System Environment ###");
  
  Serial.print("Chip Model: "); Serial.println(ESP.getChipModel());
  Serial.print("Chip Revision: "); Serial.println(ESP.getChipRevision());
  Serial.print("CPU Frequency: "); Serial.print(ESP.getCpuFreqMHz()); Serial.println(" MHz");
  
  Serial.print("Flash Size: "); Serial.print(ESP.getFlashChipSize() / (1024 * 1024)); Serial.println(" MB");
  Serial.print("Flash Speed: "); Serial.print(ESP.getFlashChipSpeed() / 1000000); Serial.println(" MHz");
  
  Serial.print("Free Heap: "); Serial.print(ESP.getFreeHeap()); Serial.println(" bytes");
  Serial.print("SDK Version: "); Serial.println(ESP.getSdkVersion());
  Serial.println("#################################");

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); }

  SPI.begin(BME_SCK, BME_MISO, BME_MOSI, BME_CS);
  if (!bme.begin()) { while (1); }

  Ed25519::generatePrivateKey(privateKey);
  Ed25519::derivePublicKey(publicKey, privateKey);

  client.setServer(mqtt_server, mqtt_port);

  // --- START STRESSER ---
  #if STRESS_ENABLED
    xTaskCreatePinnedToCore(stressTask, "StressTask", 2048, NULL, 1, NULL, STRESS_CORE);
    Serial.println("Background Stressor Started.");
  #endif
}

void loop() {
  if (!client.connected()) {
    reconnectMQTT();
  }
  client.loop();

  if (millis() - lastPublish > 10) {
    lastPublish = millis();

    float temp = bme.readTemperature();
    float hum  = bme.readHumidity();
    float pres = bme.readPressure() / 100.0F;

    char msgBuffer[64];
    size_t msgLen = snprintf(msgBuffer, sizeof(msgBuffer), "t=%.2f,h=%.2f,p=%.2f", temp, hum, pres);

    uint8_t signature[ED25519_SIGNATURE_SIZE];

    uint32_t startMicros = micros();
    Ed25519::sign(signature, privateKey, publicKey, (const uint8_t*)msgBuffer, msgLen);
    uint32_t signTime = micros() - startMicros;

    size_t payloadLen = msgLen + ED25519_SIGNATURE_SIZE + ED25519_PUBLIC_KEY_SIZE + sizeof(signTime);
    uint8_t payload[payloadLen];

    memcpy(payload, msgBuffer, msgLen);
    memcpy(payload + msgLen, signature, ED25519_SIGNATURE_SIZE);
    memcpy(payload + msgLen + ED25519_SIGNATURE_SIZE, publicKey, ED25519_PUBLIC_KEY_SIZE);
    memcpy(payload + msgLen + ED25519_SIGNATURE_SIZE + ED25519_PUBLIC_KEY_SIZE, &signTime, sizeof(signTime));

    client.publish(topic, payload, payloadLen);
  }
}

void reconnectMQTT() {
  while (!client.connected()) {
    String clientId = "ESP32-Bench-" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      DEBUG_PRINTLN("Connected to Broker");
    } else {
      delay(5000);
    }
  }
}