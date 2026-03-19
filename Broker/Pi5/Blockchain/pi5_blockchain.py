#!/usr/bin/env python3
# Simple blockchain-style integrity sender for Pi 5
#
# Treats each H.264 chunk as a block in a hash chain:
#   prev_block_hash_(n) = block_hash_(n-1) (or 32x0 for genesis)
#   chunk_hash_n        = SHA256(chunk_data)
#   block_hash_n        = SHA256(prev_block_hash_n || chunk_hash_n)
#
# Payload per chunk:
#   [chunk_data][index(4)][hash_time_us(4)][prev_block_hash(32)][block_hash(32)]
#
# This is designed to pair with Broker/Pi5/Blockchain/broker_blockchain.py

import argparse
import hashlib
import os
import struct
import threading
import time

import paho.mqtt.client as mqtt
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import PyavOutput
import subprocess
import signal

# --- CONFIGURATION ---
MQTT_BROKER = "laptop.local"
TOPIC = "cam/blockchain"
CHUNK_SIZE = 4096

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


# --- 1. ARGUMENT PARSING ---
parser = argparse.ArgumentParser(description="Pi 5 blockchain-style integrity sender")
parser.add_argument("-s", "--stress", type=int, default=0, help="CPU load percentage (0-100)")
parser.add_argument("-t", "--time", type=int, default=60, help="Recording duration in seconds")
args = parser.parse_args()

RECORD_SECONDS = args.time

# --- 2. SETUP MQTT ---
print(f"Connecting to MQTT broker at {MQTT_BROKER}...")
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER, 1883)
client.loop_start()

# --- 3. CREATE A PIPE ---
# r_fd = Python worker reads from here, w_fd = camera writes to here
r_fd, w_fd = os.pipe()


# --- 4. HASH-CHAIN WORKER ---
def blockchain_worker(read_fd: int) -> None:
    """Reads H.264 chunks, builds a hash chain, and publishes over MQTT."""
    index = 0
    prev_block_hash = b"\x00" * 32  # genesis

    print("Worker: Started — listening for video chunks...")

    with os.fdopen(read_fd, "rb") as pipe_reader:
        while True:
            try:
                chunk = pipe_reader.read(CHUNK_SIZE)
                if not chunk:
                    break

                # 1. HASH chunk and measure time
                h_start = time.perf_counter()
                chunk_hash = hashlib.sha256(chunk).digest()
                hash_time_us = int((time.perf_counter() - h_start) * 1_000_000)

                # 2. COMPUTE block hash = SHA256(prev_block_hash || chunk_hash)
                block_hash = hashlib.sha256(prev_block_hash + chunk_hash).digest()

                # 3. BUILD FOOTER
                footer = struct.pack("<II", index, hash_time_us) + prev_block_hash + block_hash

                # 4. PUBLISH
                client.publish(TOPIC, chunk + footer)

                if index % 50 == 0:
                    print(
                        f"Block #{index:<5} | Size: {len(chunk)} B | HashTime: {hash_time_us} us"
                    )

                prev_block_hash = block_hash
                index += 1

            except Exception as e:
                print(f"Worker Error: {e}")
                break

    print("Worker: Stopped.")


# Start worker thread
t = threading.Thread(target=blockchain_worker, args=(r_fd,))
t.daemon = True
t.start()

# --- 5. CAMERA SETUP & RECORDING ---
print("Configuring Camera...")
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (640, 480), "format": "YUV420"},
    controls={"FrameDurationLimits": (33333, 33333)},  # ~30 FPS
)
picam2.configure(config)
picam2.start()

encoder = H264Encoder(bitrate=2_000_000)
output = PyavOutput(f"pipe:{w_fd}", format="h264")

# Start stress test before recording
start_stress_test(cpu_load=args.stress)

print(f"Recording for {RECORD_SECONDS} seconds with stress={args.stress}%...")
picam2.start_recording(encoder, output)

try:
    time.sleep(RECORD_SECONDS)
except KeyboardInterrupt:
    print("\nStopping early...")

# --- CLEANUP ---
print("Cleaning up...")
picam2.stop_recording()
picam2.stop()
os.close(w_fd)  # signal worker: no more data
stop_stress_test()
t.join(timeout=2)
client.disconnect()
print("Done.")
