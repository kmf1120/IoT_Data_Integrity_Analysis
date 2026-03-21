#!/usr/bin/env python3
# Cloud-Based Hash Verification (CBHV) — Pi 3 Sender
# Captures LED state, computes SHA-256, uploads hash to Firebase Realtime DB,
# then publishes raw data over MQTT for independent verification on the laptop.
#
# Payload structure (252 bytes total for 60 LEDs):
#   [msg_bytes (240)] [seq_num (4)] [hash_time_us (4)] [upload_latency_us (4)]
#
# seq_num lets the broker look up the correct hash on Firebase.
# hash_time_us and upload_latency_us are benchmarking metrics from the Pi side.

import time
import argparse
import struct
import hashlib
import subprocess
import signal
import os

import requests
import paho.mqtt.client as mqtt
from rpi_ws281x import *

# --- LED CONFIGURATION ---
LED_COUNT      = 60
LED_PIN        = 18
LED_FREQ_HZ    = 800000
LED_DMA        = 10
LED_BRIGHTNESS = 65
LED_INVERT     = False
LED_CHANNEL    = 0

# --- MQTT CONFIGURATION ---
MQTT_BROKER = "laptop.local"   # <--- CHANGE THIS TO YOUR LAPTOP HOSTNAME OR IP
MQTT_TOPIC  = "light/cbhv"

# --- FIREBASE CONFIGURATION ---
# Realtime Database URL for your Firebase project (no trailing slash).
# Must match the URL used by the CBHV broker.
FIREBASE_URL = "https://senior-project-bdb33-default-rtdb.firebaseio.com"

# Sentinel value packed into upload_latency_us when a Firebase upload fails.
UPLOAD_FAILED_SENTINEL = 0xFFFFFFFF

# --- STRESS TESTING SETUP ---
stress_process = None


def start_stress_test(cpu_load: int) -> None:
    """Starts stress-ng in the background at the requested CPU load."""
    global stress_process
    if cpu_load <= 0:
        print("--- STRESS DISABLED (0%) ---")
        return

    print(f"--- STARTING STRESS TEST: {cpu_load}% CPU LOAD ---")
    cmd = [
        "stress-ng",
        "--cpu",
        "4",
        "--cpu-load",
        str(cpu_load),
        "--quiet",
    ]
    stress_process = subprocess.Popen(cmd, preexec_fn=os.setsid)


def stop_stress_test() -> None:
    """Cleanly terminates the stress-ng process."""
    global stress_process
    if stress_process is not None:
        print("--- STOPPING STRESS TEST ---")
        try:
            os.killpg(os.getpgid(stress_process.pid), signal.SIGTERM)
        except Exception:
            pass
        stress_process = None

# ---------------------------------------------------------------------------
# MQTT SETUP
# ---------------------------------------------------------------------------
seq_num = 0
client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected to broker with code {rc}")

try:
    client.on_connect = on_connect
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_start()  # Run MQTT in the background
except Exception as e:
    print(f"[MQTT] Failed to connect: {e}")


# ---------------------------------------------------------------------------
# FIREBASE HELPERS
# ---------------------------------------------------------------------------
def upload_hash(seq, hash_hex):
    """
    PUTs the SHA-256 hash for the given sequence number to Firebase.
    Returns upload round-trip latency in microseconds, or UPLOAD_FAILED_SENTINEL.
    """
    url = f"{FIREBASE_URL}/hashes/{seq}.json"
    t_start = time.perf_counter()
    try:
        resp = requests.put(url, json={"hash": hash_hex}, timeout=5)
        resp.raise_for_status()
        latency_us = int((time.perf_counter() - t_start) * 1_000_000)
        return latency_us
    except requests.RequestException as e:
        print(f"[Firebase] Upload failed for seq={seq}: {e}")
        return UPLOAD_FAILED_SENTINEL


# ---------------------------------------------------------------------------
# CORE INTERCEPTOR
# ---------------------------------------------------------------------------
def hash_and_show(strip):
    """
    Captures the current LED state, computes SHA-256, uploads to Firebase,
    publishes an MQTT packet with benchmarking metadata, then updates the LEDs.
    """
    global seq_num

    # 1. CAPTURE — read all 60 pixel colors as a list of ints
    pixel_data = [strip.getPixelColor(i) for i in range(strip.numPixels())]

    # 2. PACK — convert to binary (little-endian unsigned ints)
    msg_bytes = struct.pack(f'<{strip.numPixels()}I', *pixel_data)

    # 3. HASH & BENCHMARK — time SHA-256 on the Pi
    h_start = time.perf_counter()
    hash_hex = hashlib.sha256(msg_bytes).hexdigest()
    hash_time_us = int((time.perf_counter() - h_start) * 1_000_000)

    # 4. UPLOAD TO FIREBASE — synchronous so we can measure round-trip latency
    upload_latency_us = upload_hash(seq_num, hash_hex)

    # 5. BUILD MQTT PAYLOAD — [data][seq][hash_time][upload_latency]
    seq_bytes            = struct.pack('<I', seq_num)
    hash_time_bytes      = struct.pack('<I', hash_time_us)
    upload_latency_bytes = struct.pack('<I', upload_latency_us)
    full_payload = msg_bytes + seq_bytes + hash_time_bytes + upload_latency_bytes

    # 6. PUBLISH
    client.publish(MQTT_TOPIC, full_payload)

    # 7. PHYSICAL UPDATE
    strip.show()

    seq_num += 1


# ---------------------------------------------------------------------------
# ANIMATION FUNCTIONS (unchanged logic, hash_and_show replaces strip.show)
# ---------------------------------------------------------------------------
def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        hash_and_show(strip)
        time.sleep(wait_ms / 1000.0)

def theaterChase(strip, color, wait_ms=50, iterations=10):
    """Movie theater light style chaser animation."""
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, color)
            hash_and_show(strip)
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, 0)

def wheel(pos):
    """Generate rainbow colors across 0–255 positions."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def rainbow(strip, wait_ms=20, iterations=1):
    """Draw rainbow that fades across all pixels at once."""
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((i + j) & 255))
        hash_and_show(strip)
        time.sleep(wait_ms / 1000.0)

def rainbowCycle(strip, wait_ms=20, iterations=5):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        hash_and_show(strip)
        time.sleep(wait_ms / 1000.0)

def theaterChaseRainbow(strip, wait_ms=50):
    """Rainbow movie theater light style chaser animation."""
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, wheel((i + j) % 255))
            hash_and_show(strip)
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, 0)


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clear', action='store_true',
                        help='clear the display on exit')
    parser.add_argument('-s', '--stress', type=int, default=0,
                        help='CPU load percentage for stress-ng (0-100)')
    args = parser.parse_args()

    strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ,
                               LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    # Start CPU stress if requested
    start_stress_test(cpu_load=args.stress)

    print('Press Ctrl-C to quit.')
    if not args.clear:
        print('Use "-c" argument to clear LEDs on exit')
    print(f'Firebase URL: {FIREBASE_URL}')
    print(f'MQTT broker:  {MQTT_BROKER}  topic: {MQTT_TOPIC}')

    try:
        while True:
            print('Color wipe animations.')
            colorWipe(strip, Color(255, 0, 0), wait_ms=20)
            colorWipe(strip, Color(0, 255, 0), wait_ms=20)
            colorWipe(strip, Color(0, 0, 255), wait_ms=20)
            print('Theater chase animations.')
            theaterChase(strip, Color(127, 127, 127))
            theaterChase(strip, Color(127,   0,   0))
            theaterChase(strip, Color(  0,   0, 127))
            print('Rainbow animations.')
            rainbow(strip)
            rainbowCycle(strip)
            theaterChaseRainbow(strip)

    except KeyboardInterrupt:
        if args.clear:
            colorWipe(strip, Color(0, 0, 0), 10)
    finally:
        stop_stress_test()
