#!/usr/bin/env python3
# NeoPixel library strandtest example with MQTT & Ed25519 Signing
# Modified for Benchmark

import time
import argparse
import struct
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

# --- CRYPTO & MQTT SETUP ---
# Generate a fresh key pair for this session
signing_key = SigningKey.generate()
verify_key = signing_key.verify_key
pub_key_bytes = verify_key.encode()

# Initialize MQTT
client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with code {rc}")

try:
    client.on_connect = on_connect
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_start() # Run MQTT in the background
except Exception as e:
    print(f"Failed to connect to MQTT: {e}")

# --- THE INTERCEPTOR FUNCTION ---
def sign_and_show(strip):
    """
    Captures LED state, signs it, sends it to MQTT, then updates physical LEDs.
    """
    # 1. CAPTURE: Get the current color of all 60 pixels
    # Returns a list of integers (e.g., [16711680, 0, 255...])
    pixel_data = [strip.getPixelColor(i) for i in range(strip.numPixels())]
    
    # 2. PACK: Convert list of integers to binary data
    # '<' = Little Endian, 'I' = Unsigned Int
    msg_bytes = struct.pack(f'<{strip.numPixels()}I', *pixel_data)

    # 3. SIGN & BENCHMARK
    start_time = time.perf_counter()
    
    # Cryptographic signing
    signed_obj = signing_key.sign(msg_bytes)
    signature = signed_obj.signature
    
    # Calculate duration in Microseconds
    sign_time_us = int((time.perf_counter() - start_time) * 1_000_000)

    # 4. CONSTRUCT PAYLOAD: [Data] [Sig] [Pub] [Time]
    time_bytes = struct.pack('<I', sign_time_us)
    full_payload = msg_bytes + signature + pub_key_bytes + time_bytes

    # 5. PUBLISH
    client.publish(MQTT_TOPIC, full_payload)

    # 6. PHYSICAL UPDATE
    strip.show()


# --- ANIMATION FUNCTIONS (Updated to use sign_and_show) ---
def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        sign_and_show(strip) # <--- INTERCEPTED
        time.sleep(wait_ms/1000.0)

def theaterChase(strip, color, wait_ms=50, iterations=10):
    """Movie theater light style chaser animation."""
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, color)
            sign_and_show(strip) # <--- INTERCEPTED
            time.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, 0)

def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
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
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((i+j) & 255))
        sign_and_show(strip) # <--- INTERCEPTED
        time.sleep(wait_ms/1000.0)

def rainbowCycle(strip, wait_ms=20, iterations=5):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        sign_and_show(strip) # <--- INTERCEPTED
        time.sleep(wait_ms/1000.0)

def theaterChaseRainbow(strip, wait_ms=50):
    """Rainbow movie theater light style chaser animation."""
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, wheel((i+j) % 255))
            sign_and_show(strip) # <--- INTERCEPTED
            time.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, 0)

# Main program logic follows:
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clear', action='store_true', help='clear the display on exit')
    args = parser.parse_args()

    # Create NeoPixel object with appropriate configuration.
    strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    print ('Press Ctrl-C to quit.')
    if not args.clear:
        print('Use "-c" argument to clear LEDs on exit')

    try:
        while True:
            # We reduced iterations slightly for quicker benchmarking cycles
            print ('Color wipe animations.')
            colorWipe(strip, Color(255, 0, 0), wait_ms=20)
            colorWipe(strip, Color(0, 255, 0), wait_ms=20)
            colorWipe(strip, Color(0, 0, 255), wait_ms=20)
            print ('Theater chase animations.')
            theaterChase(strip, Color(127, 127, 127))
            theaterChase(strip, Color(127,   0,   0))
            theaterChase(strip, Color(  0,   0, 127))
            print ('Rainbow animations.')
            rainbow(strip)
            rainbowCycle(strip)
            theaterChaseRainbow(strip)

    except KeyboardInterrupt:
        if args.clear:
            colorWipe(strip, Color(0,0,0), 10)
