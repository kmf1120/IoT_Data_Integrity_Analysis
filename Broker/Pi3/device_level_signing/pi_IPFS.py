#!/usr/bin/env python3
# NeoPixel library strandtest example with MQTT, Ed25519 Signing, and Stress-Testing
# Developed for IoT Data Integrity Benchmark

import time
import argparse
import struct
import subprocess
import os
import signal
import paho.mqtt.client as mqtt
from rpi_ws281x import *
from nacl.signing import SigningKey

# --- CONFIGURATION ---
MQTT_BROKER = "laptop.local"  # <--- CHANGE THIS TO YOUR LAPTOP IP
MQTT_TOPIC = "light"
LED_COUNT = 60
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 65
LED_INVERT = False
LED_CHANNEL = 0

# --- STRESS TESTING SETUP ---
stress_process = None

def start_stress_test(cpu_load=50):
    """Starts stress-ng in the background to simulate heavy system load."""
    global stress_process
    print(f"--- STARTING STRESS TEST: {cpu_load}% CPU LOAD ---")
    # Pi 3B+ has 4 cores. We stress all 4 at the target load percentage.
    stress_command = [
        "stress-ng",
        "--cpu", "4",
        "--cpu-load", str(cpu_load),
        "--quiet"
    ]
    # Use os.setsid to ensure we can kill the entire process group later
    stress_process = subprocess.Popen(stress_command, preexec_fn=os.setsid)

def stop_stress_test():
    """Cleanly terminates the stress-ng background process."""
    global stress_process
    if stress_process:
        print("--- STOPPING STRESS TEST ---")
        try:
            os.killpg(os.getpgid(stress_process.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass

# --- CRYPTO & MQTT SETUP ---
signing_key = SigningKey.generate()
verify_key = signing_key.verify_key
pub_key_bytes = verify_key.encode()

client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with code {rc}")

try:
    client.on_connect = on_connect
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_start()
except Exception as e:
    print(f"Failed to connect to MQTT: {e}")

# --- THE INTERCEPTOR FUNCTION ---
def sign_and_show(strip):
    """Captures LED state, signs it, sends it to MQTT, then updates physical LEDs."""
    # 1. CAPTURE
    pixel_data = [strip.getPixelColor(i) for i in range(strip.numPixels())]

    # 2. PACK
    msg_bytes = struct.pack(f'<{strip.numPixels()}I', *pixel_data)

    # 3. SIGN & BENCHMARK
    start_time = time.perf_counter()
    signed_obj = signing_key.sign(msg_bytes)
    signature = signed_obj.signature
    sign_time_us = int((time.perf_counter() - start_time) * 1_000_000)

    # 4. CONSTRUCT PAYLOAD: [Data] [Sig] [Pub] [Time]
    time_bytes = struct.pack('<I', sign_time_us)
    full_payload = msg_bytes + signature + pub_key_bytes + time_bytes

    # 5. PUBLISH
    client.publish(MQTT_TOPIC, full_payload)

    # 6. PHYSICAL UPDATE
    strip.show()

# --- ANIMATION FUNCTIONS ---
def colorWipe(strip, color, wait_ms=50):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        sign_and_show(strip)
        time.sleep(wait_ms/1000.0)

def theaterChase(strip, color, wait_ms=50, iterations=10):
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, color)
            sign_and_show(strip)
            time.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, 0)

def wheel(pos):
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def rainbow(strip, wait_ms=20, iterations=1):
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((i+j) & 255))
        sign_and_show(strip)
        time.sleep(wait_ms/1000.0)

def rainbowCycle(strip, wait_ms=20, iterations=5):
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        sign_and_show(strip)
        time.sleep(wait_ms/1000.0)

def theaterChaseRainbow(strip, wait_ms=50):
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, wheel((i+j) % 255))
            sign_and_show(strip)
            time.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, 0)

# --- MAIN LOGIC ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clear', action='store_true', help='clear the display on exit')
    parser.add_argument('-s', '--stress', type=int, default=0, help='CPU load percentage (0-100)')
    args = parser.parse_args()

    strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    # Trigger stress test if requested via argument
    if args.stress > 0:
        start_stress_test(cpu_load=args.stress)

    print('Press Ctrl-C to quit.')

    try:
        while True:
            print('Running Color Wipe...')
            colorWipe(strip, Color(255, 0, 0), wait_ms=20)
            colorWipe(strip, Color(0, 255, 0), wait_ms=20)
            colorWipe(strip, Color(0, 0, 255), wait_ms=20)

            print('Running Rainbow...')
            rainbow(strip)
            rainbowCycle(strip)

    except KeyboardInterrupt:
        stop_stress_test()
        if args.clear:
            colorWipe(strip, Color(0,0,0), 10)
        print("\nBenchmark terminated.")