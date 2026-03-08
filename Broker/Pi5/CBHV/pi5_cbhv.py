#!/usr/bin/env python3
# Cloud-Based Hash Verification (CBHV) — Pi 5 Sender
#
# Records video via Picamera2, splits it into 4096-byte chunks,
# computes SHA-256 per chunk, uploads the hash to Firebase Realtime DB,
# then publishes raw chunk data over MQTT for independent verification.
#
# Payload structure per chunk:
#   [chunk_data (variable)] [seq_num (4)] [hash_time_us (4)] [upload_latency_us (4)]
#
# Requires (in venv):
#   pip install requests paho-mqtt picamera2 pyav

import time
import os
import struct
import hashlib
import threading
import requests
import paho.mqtt.client as mqtt
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import PyavOutput

# --- CONFIGURATION ---
MQTT_BROKER    = "laptop.local"   # <--- CHANGE TO YOUR LAPTOP HOSTNAME OR IP
TOPIC          = "cam/cbhv"
RECORD_SECONDS = 60
CHUNK_SIZE     = 4096

# --- FIREBASE CONFIGURATION ---
# Must match broker_cbhv.py on the laptop.
# Example: "https://senior-project-bdb33-default-rtdb.firebaseio.com"
FIREBASE_URL = "https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com"

# Sentinel packed into upload_latency_us when a Firebase upload fails
UPLOAD_FAILED_SENTINEL = 0xFFFFFFFF

# ---------------------------------------------------------------------------
# MQTT SETUP
# ---------------------------------------------------------------------------
print("Connecting to MQTT...")
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER, 1883)
client.loop_start()


# ---------------------------------------------------------------------------
# FIREBASE HELPER
# ---------------------------------------------------------------------------
def upload_hash(seq, hash_hex):
    """
    PUTs the SHA-256 hash for the given chunk sequence number to Firebase.
    Returns upload round-trip latency in microseconds, or UPLOAD_FAILED_SENTINEL.
    """
    url = f"{FIREBASE_URL}/hashes/{seq}.json"
    t_start = time.perf_counter()
    try:
        resp = requests.put(url, json={"hash": hash_hex}, timeout=5)
        resp.raise_for_status()
        return int((time.perf_counter() - t_start) * 1_000_000)
    except requests.RequestException as e:
        print(f"[Firebase] Upload failed for seq={seq}: {e}")
        return UPLOAD_FAILED_SENTINEL


# ---------------------------------------------------------------------------
# PIPE + CAMERA SETUP
# ---------------------------------------------------------------------------
# r_fd = Python reads from here, w_fd = camera writes to here
r_fd, w_fd = os.pipe()


# ---------------------------------------------------------------------------
# HASHING WORKER
# ---------------------------------------------------------------------------
def hashing_worker(read_fd):
    """
    Reads raw H.264 chunks from the pipe, hashes each one, uploads to Firebase,
    and publishes an MQTT packet with benchmarking metadata.
    """
    seq_num = 0
    print("Worker: Started — listening for video chunks...")

    with os.fdopen(read_fd, 'rb') as pipe_reader:
        while True:
            try:
                chunk = pipe_reader.read(CHUNK_SIZE)
                if not chunk:
                    break  # End of stream

                # 1. HASH & BENCHMARK
                h_start  = time.perf_counter()
                hash_hex = hashlib.sha256(chunk).hexdigest()
                hash_time_us = int((time.perf_counter() - h_start) * 1_000_000)

                # 2. UPLOAD TO FIREBASE (synchronous — measures round-trip latency)
                upload_latency_us = upload_hash(seq_num, hash_hex)

                # 3. BUILD MQTT PAYLOAD — [chunk_data][seq][hash_time][upload_latency]
                footer = struct.pack('<III', seq_num, hash_time_us, upload_latency_us)
                client.publish(TOPIC, chunk + footer)

                if seq_num % 50 == 0:
                    print(f"Chunk #{seq_num:<5} | Size: {len(chunk)} B | "
                          f"Hash: {hash_time_us} us | Upload: {upload_latency_us} us")

                seq_num += 1

            except Exception as e:
                print(f"Worker Error: {e}")
                break

    print("Worker: Stopped.")


# Start worker thread
t = threading.Thread(target=hashing_worker, args=(r_fd,))
t.start()

# ---------------------------------------------------------------------------
# CAMERA SETUP & RECORDING
# ---------------------------------------------------------------------------
print("Configuring Camera...")
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (640, 480), "format": "YUV420"},
    controls={"FrameDurationLimits": (33333, 33333)}
)
picam2.configure(config)
picam2.start()

encoder = H264Encoder(bitrate=2000000)
output  = PyavOutput(f"pipe:{w_fd}", format="h264")

print(f"Recording for {RECORD_SECONDS} seconds...")
print(f"Firebase URL: {FIREBASE_URL}")
print(f"MQTT broker:  {MQTT_BROKER}  topic: {TOPIC}")
picam2.start_recording(encoder, output)

try:
    time.sleep(RECORD_SECONDS)
except KeyboardInterrupt:
    print("Stopping early...")

# ---------------------------------------------------------------------------
# CLEANUP
# ---------------------------------------------------------------------------
picam2.stop_recording()
picam2.stop()
os.close(w_fd)    # Signal worker: no more data
t.join()          # Wait for worker to flush
client.disconnect()
print("Done.")
