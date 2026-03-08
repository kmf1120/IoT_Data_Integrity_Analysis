#!/usr/bin/env python3
# Cloud-Based Hash Verification (CBHV) — Laptop Broker / Verifier
#
# Receives raw LED data over MQTT, fetches the pre-stored SHA-256 hash from
# Firebase Realtime DB, recomputes the hash locally, and compares them.
#
# Expected MQTT payload structure (from pi3_cbhv.py):
#   [msg_bytes (240)] [seq_num (4)] [hash_time_us (4)] [upload_latency_us (4)]
#
# CSV output columns:
#   Entry, MessageHex, SeqNum, HashTime_uS, UploadLatency_uS,
#   FetchLatency_uS, VerifyTime_uS, Valid

import paho.mqtt.client as mqtt
import struct
import hashlib
import csv
import os
import time
import requests

# --- CONFIGURATION ---
MQTT_BROKER = "localhost"          # Broker runs on this machine
TOPIC       = "light/cbhv"
MAX_LOGS    = 5000

# Paste your Firebase Realtime Database URL here (no trailing slash).
# Must match the FIREBASE_URL in pi3_cbhv.py.
FIREBASE_URL = "https://senior-project-bdb33-default-rtdb.firebaseio.com"

# How many times to retry a Firebase GET if the hash isn't there yet
# (race condition: MQTT packet arrives before Firebase upload completes).
FETCH_MAX_RETRIES = 5
FETCH_RETRY_DELAY_S = 0.1   # 100 ms between retries

# Sentinel written by Pi when its Firebase upload failed
UPLOAD_FAILED_SENTINEL = 0xFFFFFFFF

# --- FILE SETUP ---
current_dir   = os.path.dirname(os.path.abspath(__file__))
results_dir   = os.path.join(current_dir, "results")
os.makedirs(results_dir, exist_ok=True)

base_filename = "benchmark_cbhv_results"
extension     = ".csv"
counter       = 1
while os.path.exists(os.path.join(results_dir, f"{base_filename}_{counter}{extension}")):
    counter += 1
log_file_path = os.path.join(results_dir, f"{base_filename}_{counter}{extension}")

results_buffer = []
failures       = 0

print(f"Logging to:    {log_file_path}")
print(f"Firebase URL:  {FIREBASE_URL}")
print(f"Ready. Listening for CBHV data on '{TOPIC}'...")


# ---------------------------------------------------------------------------
# FIREBASE FETCH
# ---------------------------------------------------------------------------
def fetch_cloud_hash(seq_num):
    """
    Fetches the SHA-256 hash stored by the Pi for the given sequence number.
    Retries up to FETCH_MAX_RETRIES times to handle the race where the MQTT
    packet arrives before the Firebase upload completes.
    Returns (hash_hex, fetch_latency_us) or (None, fetch_latency_us).
    """
    url = f"{FIREBASE_URL}/hashes/{seq_num}.json"
    for attempt in range(FETCH_MAX_RETRIES):
        t_start = time.perf_counter()
        try:
            resp = requests.get(url, timeout=3)
            fetch_latency_us = int((time.perf_counter() - t_start) * 1_000_000)
            if resp.ok:
                data = resp.json()
                if isinstance(data, dict) and "hash" in data:
                    return data["hash"], fetch_latency_us
            # Hash not there yet — wait and retry
            if attempt < FETCH_MAX_RETRIES - 1:
                time.sleep(FETCH_RETRY_DELAY_S)
        except requests.RequestException as e:
            fetch_latency_us = int((time.perf_counter() - t_start) * 1_000_000)
            print(f"[Firebase] Fetch error for seq={seq_num} (attempt {attempt+1}): {e}")
            if attempt < FETCH_MAX_RETRIES - 1:
                time.sleep(FETCH_RETRY_DELAY_S)

    return None, fetch_latency_us


# ---------------------------------------------------------------------------
# MQTT CALLBACK
# ---------------------------------------------------------------------------
def on_message(client, userdata, msg):
    global failures
    payload = msg.payload

    try:
        # Payload footer is the last 12 bytes: [seq(4)][hash_time(4)][upload_latency(4)]
        if len(payload) < 12:
            raise ValueError(f"Payload too short ({len(payload)} bytes)")

        upload_latency_us = struct.unpack('<I', payload[-4:])[0]
        hash_time_us      = struct.unpack('<I', payload[-8:-4])[0]
        seq_num           = struct.unpack('<I', payload[-12:-8])[0]
        raw_msg_bytes     = payload[:-12]

        # Readable hex snippet for CSV (first 20 chars only)
        raw_msg_hex = raw_msg_bytes.hex()[:20] + "..."

        # 1. FETCH stored hash from Firebase (includes retry logic)
        cloud_hash, fetch_latency_us = fetch_cloud_hash(seq_num)

        # 2. RECOMPUTE hash locally & benchmark
        v_start      = time.perf_counter()
        local_hash   = hashlib.sha256(raw_msg_bytes).hexdigest()
        v_end        = time.perf_counter()
        verify_time_us = int((v_end - v_start) * 1_000_000)

        # 3. COMPARE
        if cloud_hash is None:
            is_valid = "UNVERIFIABLE"
            failures += 1
        elif local_hash == cloud_hash:
            is_valid = True
        else:
            is_valid = False
            failures += 1

        # 4. LOG
        upload_display = upload_latency_us if upload_latency_us != UPLOAD_FAILED_SENTINEL else "UPLOAD_FAILED"
        entry_number   = len(results_buffer)
        results_buffer.append([
            entry_number,
            raw_msg_hex,
            seq_num,
            hash_time_us,
            upload_display,
            fetch_latency_us,
            verify_time_us,
            is_valid
        ])

        # Progress indicator
        if len(results_buffer) % 100 == 0:
            print(f"Collected: {len(results_buffer)}/{MAX_LOGS} | Failures/Unverifiable: {failures}")

        if len(results_buffer) >= MAX_LOGS:
            finalize_benchmark(client)

    except Exception as e:
        print(f"Error parsing payload: {e}")


# ---------------------------------------------------------------------------
# FINALIZE
# ---------------------------------------------------------------------------
def finalize_benchmark(client):
    print("\nBenchmark complete! Writing results...")

    with open(log_file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Entry", "MessageHex", "SeqNum",
            "HashTime_uS", "UploadLatency_uS",
            "FetchLatency_uS", "VerifyTime_uS", "Valid"
        ])
        writer.writerows(results_buffer)

    total = len(results_buffer)
    fail_rate  = (failures / total) * 100 if total > 0 else 0

    # Only average rows where upload succeeded
    valid_upload = [r for r in results_buffer if r[4] != "UPLOAD_FAILED"]
    avg_hash     = sum(r[3] for r in results_buffer) / total if total else 0
    avg_upload   = sum(r[4] for r in valid_upload) / len(valid_upload) if valid_upload else float('nan')
    avg_fetch    = sum(r[5] for r in results_buffer) / total if total else 0
    avg_verify   = sum(r[6] for r in results_buffer) / total if total else 0

    print("--- CBHV RESULTS (Pi 3 → Firebase → Laptop) ---")
    print(f"Total Messages:        {total}")
    print(f"Failure/Unverifiable:  {failures} ({fail_rate:.2f}%)")
    print(f"Avg Hash Time (Pi 3):  {avg_hash:.2f} us")
    print(f"Avg Upload Latency:    {avg_upload:.2f} us  ({avg_upload/1000:.2f} ms)")
    print(f"Avg Fetch Latency:     {avg_fetch:.2f} us  ({avg_fetch/1000:.2f} ms)")
    print(f"Avg Verify Time:       {avg_verify:.2f} us")
    print(f"Results saved to:      {log_file_path}")

    client.disconnect()
    os._exit(0)


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
client = mqtt.Client()
client.on_message = on_message

try:
    client.connect(MQTT_BROKER, 1883)
    client.subscribe(TOPIC)
    client.loop_forever()
except KeyboardInterrupt:
    print("\nStopped by user.")
    if results_buffer:
        print(f"Saving {len(results_buffer)} partial results...")
        finalize_benchmark(client)
    else:
        print("No data collected.")
except ConnectionRefusedError:
    print("Error: Could not connect to MQTT broker. Is Mosquitto running?")
