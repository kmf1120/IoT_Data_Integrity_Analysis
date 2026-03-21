#!/usr/bin/env python3
# Simple blockchain-style integrity sender for Pi 3 (LED-based)
#
# Treats each LED frame as a block in a hash chain:
#   prev_block_hash_(n) = block_hash_(n-1) (or 32x0 for genesis)
#   frame_hash_n        = SHA256(led_frame_bytes)
#   block_hash_n        = SHA256(prev_block_hash_n || frame_hash_n)
#
# Payload per MQTT message:
#   [led_frame_bytes][index(4)][hash_time_us(4)][prev_block_hash(32)][block_hash(32)]
#
# Designed to pair with Broker/Pi3/Blockchain/broker_blockchain_led.py

import argparse
import hashlib
import os
import struct
import time
import subprocess
import signal

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
MQTT_BROKER = "laptop.local"   # Update to your laptop hostname/IP if needed
TOPIC       = "light/blockchain"

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
# HASH-CHAIN SENDER
# ---------------------------------------------------------------------------

def hash_and_publish(strip, index: int, client: mqtt.Client) -> int:
    """Capture LED frame, build block, and publish over MQTT.

    Returns the next index to use.
    """
    # Capture current LED state
    pixel_data = [strip.getPixelColor(i) for i in range(strip.numPixels())]
    frame_bytes = struct.pack(f"<{strip.numPixels()}I", *pixel_data)

    # Hash frame and compute block hash
    h_start = time.perf_counter()
    frame_hash = hashlib.sha256(frame_bytes).digest()
    hash_time_us = int((time.perf_counter() - h_start) * 1_000_000)

    global prev_block_hash
    block_hash = hashlib.sha256(prev_block_hash + frame_hash).digest()

    footer = struct.pack("<II", index, hash_time_us) + prev_block_hash + block_hash
    payload = frame_bytes + footer

    client.publish(TOPIC, payload)

    if index % 50 == 0:
        print(f"Block #{index:<5} | Frame bytes: {len(frame_bytes)} | HashTime: {hash_time_us} us")

    prev_block_hash = block_hash
    return index + 1


# Simple animation using the blockchain sender

def colorWipe_blockchain(strip, color, wait_ms, client):
    global block_index
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        block_index = hash_and_publish(strip, block_index, client)
        strip.show()
        time.sleep(wait_ms / 1000.0)


def theaterChase_blockchain(strip, color, wait_ms, iterations, client):
    global block_index
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, color)
            block_index = hash_and_publish(strip, block_index, client)
            strip.show()
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


def rainbow_blockchain(strip, wait_ms, iterations, client):
    global block_index
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((i + j) & 255))
        block_index = hash_and_publish(strip, block_index, client)
        strip.show()
        time.sleep(wait_ms / 1000.0)


def rainbowCycle_blockchain(strip, wait_ms, iterations, client):
    global block_index
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        block_index = hash_and_publish(strip, block_index, client)
        strip.show()
        time.sleep(wait_ms / 1000.0)


def theaterChaseRainbow_blockchain(strip, wait_ms, client):
    global block_index
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, wheel((i + j) % 255))
            block_index = hash_and_publish(strip, block_index, client)
            strip.show()
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, 0)


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pi 3 blockchain-style LED sender")
    parser.add_argument("-c", "--clear", action="store_true", help="clear the display on exit")
    parser.add_argument("-s", "--stress", type=int, default=0, help="CPU load percentage (0-100)")
    args = parser.parse_args()

    strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ,
                               LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    # Setup MQTT
    print(f"Connecting to MQTT broker at {MQTT_BROKER}...")
    client = mqtt.Client()
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_start()

    # Blockchain state
    prev_block_hash = b"\x00" * 32
    block_index = 0

    # Start stress if requested
    start_stress_test(cpu_load=args.stress)

    print("Press Ctrl-C to quit.")
    if not args.clear:
        print('Use "-c" argument to clear LEDs on exit')

    try:
        while True:
            print("Color wipe animations.")
            colorWipe_blockchain(strip, Color(255, 0, 0), wait_ms=20, client=client)
            colorWipe_blockchain(strip, Color(0, 255, 0), wait_ms=20, client=client)
            colorWipe_blockchain(strip, Color(0, 0, 255), wait_ms=20, client=client)
            print("Theater chase animations.")
            theaterChase_blockchain(strip, Color(127, 127, 127), wait_ms=50, iterations=10, client=client)
            theaterChase_blockchain(strip, Color(127,   0,   0), wait_ms=50, iterations=10, client=client)
            theaterChase_blockchain(strip, Color(  0,   0, 127), wait_ms=50, iterations=10, client=client)
            print("Rainbow animations.")
            rainbow_blockchain(strip, wait_ms=20, iterations=1, client=client)
            rainbowCycle_blockchain(strip, wait_ms=20, iterations=5, client=client)
            theaterChaseRainbow_blockchain(strip, wait_ms=50, client=client)

    except KeyboardInterrupt:
        if args.clear:
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, 0)
            strip.show()
    finally:
        stop_stress_test()
        client.loop_stop()
        client.disconnect()
