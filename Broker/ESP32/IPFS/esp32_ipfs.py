# pyright: reportMissingImports=false

import network
import time
from umqtt.simple import MQTTClient

try:
	import ujson as json
except ImportError:
	import json

# ==============================
# ESP32 MicroPython IPFS Sender
# ==============================
# Payload format (raw topic):
#   [utf8_sensor_message][device_time_us:uint32 little-endian]
# Broker script will generate REAL IPFS CID via Kubo and republish.

# --- Wi-Fi / MQTT CONFIG ---
WIFI_SSID = "291DPR"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

MQTT_BROKER = "laptop.local"  # laptop/Pi running broker_ipfs.py
MQTT_PORT = 1883
MQTT_CLIENT_ID = "esp32-ipfs-sender"
MQTT_TOPIC_RAW = b"therm_raw"

# Publish every 10 ms to mirror your current benchmark cadence
PUBLISH_INTERVAL_MS = 10

# Set to 1 to simulate stress workload on ESP32 loop
STRESS_ENABLED = 1


def connect_wifi():
	wlan = network.WLAN(network.STA_IF)
	wlan.active(True)
	if wlan.isconnected():
		return wlan

	print("Connecting to Wi-Fi...")
	wlan.connect(WIFI_SSID, WIFI_PASSWORD)

	timeout_s = 20
	start = time.time()
	while not wlan.isconnected():
		if time.time() - start > timeout_s:
			raise RuntimeError("Wi-Fi connection timeout")
		time.sleep_ms(200)

	print("Wi-Fi connected:", wlan.ifconfig())
	return wlan


def connect_mqtt():
	client = MQTTClient(
		client_id=MQTT_CLIENT_ID,
		server=MQTT_BROKER,
		port=MQTT_PORT,
		keepalive=60,
	)
	client.connect()
	print("MQTT connected to", MQTT_BROKER)
	return client


def build_sensor_message(counter):
	# Replace with real sensor reads if needed.
	# This keeps your benchmark runnable even without sensor libs.
	temp_c = 24.0 + ((counter % 20) * 0.05)
	hum = 45.0 + ((counter % 15) * 0.10)
	pres_hpa = 1012.0 + ((counter % 10) * 0.08)
	payload_dict = {
		"seq": counter,
		"t": round(temp_c, 2),
		"h": round(hum, 2),
		"p": round(pres_hpa, 2),
		"ts_ms": time.ticks_ms(),
	}
	return json.dumps(payload_dict)


def little_endian_u32(value):
	return bytes((value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF, (value >> 24) & 0xFF))


def run():
	connect_wifi()
	client = connect_mqtt()

	counter = 0
	last_print = time.ticks_ms()

	while True:
		start_us = time.ticks_us()

		msg = build_sensor_message(counter)
		msg_bytes = msg.encode("utf-8")

		if STRESS_ENABLED:
			x = 1.5
			for _ in range(300):
				x = (x * 3.14159 / 2.71828) ** 0.5
				if x > 1000.0 or x < 0.1:
					x = 1.5

		device_time_us = time.ticks_diff(time.ticks_us(), start_us)
		payload = msg_bytes + little_endian_u32(device_time_us)

		try:
			client.publish(MQTT_TOPIC_RAW, payload, qos=0)
		except Exception as e:
			print("MQTT publish failed, reconnecting:", e)
			time.sleep_ms(200)
			client = connect_mqtt()
			continue

		counter += 1

		if time.ticks_diff(time.ticks_ms(), last_print) > 1000:
			print("published", counter, "msgs | last_size=", len(payload), "bytes")
			last_print = time.ticks_ms()

		time.sleep_ms(PUBLISH_INTERVAL_MS)


if __name__ == "__main__":
	run()
