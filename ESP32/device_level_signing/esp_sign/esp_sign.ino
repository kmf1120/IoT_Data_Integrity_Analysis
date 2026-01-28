#include <WiFi.h>
#include <PubSubClient.h>
#include <Ed25519.h>
#include <SPI.h>
#include <Adafruit_BME280.h>
#include <wifi_secrets.h>

#define DEBUG 0 // Set to 0 for the actual 10k benchmark to ensure max speed

#if DEBUG
  #define DEBUG_BEGIN(x) Serial.begin(x)
  #define DEBUG_PRINT(x) Serial.print(x)
  #define DEBUG_PRINTLN(x) Serial.println(x)
#else
  #define DEBUG_BEGIN(x)
  #define DEBUG_PRINT(x)
  #define DEBUG_PRINTLN(x)
#endif

// put this all in a config header
const char* ssid = SECRET_SSID;
const char* password = SECRET_PASS;
const char* mqtt_server = "laptop.local"; 
const int mqtt_port = 1883;
const char* topic = "therm";

// BME280 SPI Pins
#define BME_SCK 18
#define BME_MISO 19
#define BME_MOSI 23
#define BME_CS 5
Adafruit_BME280 bme(BME_CS);

// Ed25519
#define ED25519_PRIVATE_KEY_SIZE 32
#define ED25519_PUBLIC_KEY_SIZE 32
#define ED25519_SIGNATURE_SIZE 64
uint8_t privateKey[ED25519_PRIVATE_KEY_SIZE];
uint8_t publicKey[ED25519_PUBLIC_KEY_SIZE];

WiFiClient espClient;
PubSubClient client(espClient);
unsigned long lastPublish = 0;

void reconnectMQTT(); // Forward declaration

void setup() {
  DEBUG_BEGIN(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); }

  SPI.begin(BME_SCK, BME_MISO, BME_MOSI, BME_CS);
  if (!bme.begin()) { while (1); }

  Ed25519::generatePrivateKey(privateKey);
  Ed25519::derivePublicKey(publicKey, privateKey);

  client.setServer(mqtt_server, mqtt_port);
}

void loop() {
  if (!client.connected()) {
    reconnectMQTT();
  }
  client.loop();

  // interval set to 10ms for rapid benchmarking
  if (millis() - lastPublish > 10) {
    lastPublish = millis();

    float temp = bme.readTemperature();
    float hum  = bme.readHumidity();
    float pres = bme.readPressure() / 100.0F;

    char msgBuffer[64];
    size_t msgLen = snprintf(msgBuffer, sizeof(msgBuffer), "t=%.2f,h=%.2f,p=%.2f", temp, hum, pres);

    uint8_t signature[ED25519_SIGNATURE_SIZE];

    // Benchmark the signing process
    uint32_t startMicros = micros();
    Ed25519::sign(signature, privateKey, publicKey, (const uint8_t*)msgBuffer, msgLen);
    uint32_t signTime = micros() - startMicros;

    // Build Binary Payload: [msg][sig][pub][time]
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