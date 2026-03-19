#!/usr/bin/env python3
# Cloud-Based Hash Verification (CBHV) — Pi 5 Laptop Broker
#
# Receives raw H.264 video chunks over MQTT, fetches the pre-stored SHA-256
# hash from Firebase Realtime DB, recomputes locally, and compares them.
# Verified chunks are written to an .h264 output file.
#
# Expected MQTT payload (from pi5_cbhv.py):
#   [chunk_data (variable)] [seq_num (4)] [hash_time_us (4)] [upload_latency_us (4)]
#
# Output files per run (now stress-labelled):
#   verified_stream_<stress>_<run>.h264
#   raw_packet_data_<stress>_<run>.csv
#   benchmark_summary_<stress>_<run>.csv

import argparse
import csv
import datetime
import hashlib
import os
import statistics
import struct
import time

import paho.mqtt.client as mqtt
import requests

# --- CONFIGURATION ---
MQTT_BROKER  = "localhost"
TOPIC        = "cam/cbhv"

# Paste your Firebase Realtime Database URL here (no trailing slash).
# Must match FIREBASE_URL in pi5_cbhv.py.
FIREBASE_URL = "https://senior-project-bdb33-default-rtdb.firebaseio.com"

# Retry logic for the race condition where the MQTT packet arrives
# before the Pi's Firebase upload completes.
FETCH_MAX_RETRIES  = 5
FETCH_RETRY_DELAY_S = 0.1   # 100 ms between retries

# Sentinel written by Pi when its Firebase upload failed
UPLOAD_FAILED_SENTINEL = 0xFFFFFFFF

# --- ARGUMENTS: STRESS LABEL FOR FILENAMES ---
parser = argparse.ArgumentParser(description="CBHV broker with stress-labelled output filenames.")
parser.add_argument(
    "-s",
    "--stress",
    type=int,
    default=0,
    help="CPU load percentage label (0, 25, 50, 75, 99, etc.) used only to tag output filenames.",
)
args = parser.parse_args()

STRESS_LABEL = f"stress{args.stress}" if args.stress > 0 else "stress0"

# --- FILE SETUP ---
current_dir = r"C:\Users\green\Documents\Senior_Project_Repo\Broker\Pi5\CBHV\results"
os.makedirs(current_dir, exist_ok=True)

RUN_ID = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_NAME = f"{STRESS_LABEL}_{RUN_ID}"

VIDEO_FILE   = os.path.join(current_dir, f"verified_stream_{BASE_NAME}.h264")
RAW_LOG_FILE = os.path.join(current_dir, f"raw_packet_data_{BASE_NAME}.csv")
SUMMARY_FILE = os.path.join(current_dir, f"benchmark_summary_{BASE_NAME}.csv")

video_file = open(VIDEO_FILE, "wb")

# Data storage
metrics_buffer    = []
hash_times        = []
upload_latencies  = []
fetch_latencies   = []
verify_times      = []
failures          = 0

print(f"--- CBHV BENCHMARK RUN {RUN_ID} READY ({STRESS_LABEL}) ---")
print(f"Directory:    {current_dir}")
print(f"Firebase URL: {FIREBASE_URL}")
print(f"Waiting for stream on '{TOPIC}'...")


# ---------------------------------------------------------------------------
# FIREBASE FETCH
# ---------------------------------------------------------------------------
def fetch_cloud_hash(seq_num):
    """
    Fetches the SHA-256 hash stored by the Pi for the given sequence number.
    Retries up to FETCH_MAX_RETRIES times to handle the upload race condition.
    Returns (hash_hex, fetch_latency_us) or (None, fetch_latency_us).
    """
    url = f"{FIREBASE_URL}/hashes/{seq_num}.json"
    fetch_latency_us = 0
    for attempt in range(FETCH_MAX_RETRIES):
        t_start = time.perf_counter()
        try:
            resp = requests.get(url, timeout=3)
            fetch_latency_us = int((time.perf_counter() - t_start) * 1_000_000)
            if resp.ok:
                data = resp.json()
                if isinstance(data, dict) and "hash" in data:
                    return data["hash"], fetch_latency_us
            if attempt < FETCH_MAX_RETRIES - 1:
                time.sleep(FETCH_RETRY_DELAY_S)
        except requests.RequestException as e:
            fetch_latency_us = int((time.perf_counter() - t_start) * 1_000_000)
            print(f"[Firebase] Fetch error seq={seq_num} attempt {attempt+1}: {e}")
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
        # Footer is last 12 bytes: [seq(4)][hash_time(4)][upload_latency(4)]
        if len(payload) < 13:
            raise ValueError(f"Payload too short ({len(payload)} bytes)")

        upload_latency_us = struct.unpack('<I', payload[-4:])[0]
        hash_time_us      = struct.unpack('<I', payload[-8:-4])[0]
        seq_num           = struct.unpack('<I', payload[-12:-8])[0]
        chunk_data        = payload[:-12]

        # 1. FETCH stored hash from Firebase (with retry)
        cloud_hash, fetch_latency_us = fetch_cloud_hash(seq_num)

        # 2. RECOMPUTE locally & benchmark
        v_start      = time.perf_counter()
        local_hash   = hashlib.sha256(chunk_data).hexdigest()
        verify_time_us = int((time.perf_counter() - v_start) * 1_000_000)

        # 3. COMPARE
        if cloud_hash is None:
            is_valid = "UNVERIFIABLE"
            failures += 1
        elif local_hash == cloud_hash:
            is_valid = True
            video_file.write(chunk_data)  # Only write verified chunks
        else:
            is_valid = False
            failures += 1
            print(f"TAMPERED chunk #{seq_num}!")

        # 4. STORE METRICS
        upload_display = upload_latency_us if upload_latency_us != UPLOAD_FAILED_SENTINEL else "UPLOAD_FAILED"
        chunk_id = len(metrics_buffer) + 1
        hash_times.append(hash_time_us)
        fetch_latencies.append(fetch_latency_us)
        verify_times.append(verify_time_us)
        if upload_latency_us != UPLOAD_FAILED_SENTINEL:
            upload_latencies.append(upload_latency_us)

        metrics_buffer.append([
            chunk_id, len(chunk_data), seq_num,
            hash_time_us, upload_display,
            fetch_latency_us, verify_time_us,
            is_valid
        ])

        if chunk_id % 50 == 0:
            print(f"Chunk #{chunk_id:<5} | Seq: {seq_num} | Hash: {hash_time_us} us | "
                  f"Fetch: {fetch_latency_us} us | Verify: {verify_time_us} us | Valid: {is_valid}")

    except Exception as e:
        print(f"Error parsing payload: {e}")


# ---------------------------------------------------------------------------
# FINALIZE
# ---------------------------------------------------------------------------
def finalize_benchmark():
    print(f"\n{'='*20} RUN {RUN_ID} COMPLETE ({STRESS_LABEL}) {'='*20}")
    video_file.close()

    if not metrics_buffer:
        print("No data collected.")
        return

    total_chunks = len(metrics_buffer)
    success_rate = ((total_chunks - failures) / total_chunks) * 100

    avg_hash   = statistics.mean(hash_times)   if hash_times   else 0
    avg_upload = statistics.mean(upload_latencies) if upload_latencies else float('nan')
    avg_fetch  = statistics.mean(fetch_latencies)  if fetch_latencies  else 0
    avg_verify = statistics.mean(verify_times)  if verify_times  else 0

    max_hash   = max(hash_times)   if hash_times   else 0
    max_fetch  = max(fetch_latencies)  if fetch_latencies  else 0
    max_verify = max(verify_times)  if verify_times  else 0

    # Raw per-chunk log
    with open(RAW_LOG_FILE, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Chunk_ID", "Size_Bytes", "SeqNum",
            "HashTime_uS", "UploadLatency_uS",
            "FetchLatency_uS", "VerifyTime_uS", "Valid"
        ])
        writer.writerows(metrics_buffer)

    # Single-row summary
    with open(SUMMARY_FILE, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Run_ID", "Stress_Label", "Timestamp", "Total_Chunks", "Success_Rate",
            "Avg_Hash_uS", "Max_Hash_uS",
            "Avg_Upload_uS", "Avg_Fetch_uS", "Max_Fetch_uS",
            "Avg_Verify_uS", "Max_Verify_uS"
        ])
        writer.writerow([
            RUN_ID,
            STRESS_LABEL,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_chunks,
            f"{success_rate:.2f}%",
            f"{avg_hash:.2f}", max_hash,
            f"{avg_upload:.2f}",
            f"{avg_fetch:.2f}", max_fetch,
            f"{avg_verify:.2f}", max_verify
        ])

    print(f"Total Chunks:      {total_chunks}")
    print(f"Success Rate:      {success_rate:.2f}%")
    print(f"Avg Hash (Pi 5):   {avg_hash:.2f} us")
    print(f"Avg Upload:        {avg_upload:.2f} us  ({avg_upload/1000:.2f} ms)")
    print(f"Avg Fetch:         {avg_fetch:.2f} us  ({avg_fetch/1000:.2f} ms)")
    print(f"Avg Verify:        {avg_verify:.2f} us")
    print(f"Results saved with base name: {BASE_NAME}")

    try:
        os.startfile(current_dir)
    except Exception:
        pass  # Non-Windows fallback


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message

try:
    client.connect(MQTT_BROKER, 1883)
    client.subscribe(TOPIC)
    client.loop_forever()
except KeyboardInterrupt:
    print("\nStopped by user.")
    if metrics_buffer:
        print(f"Saving {len(metrics_buffer)} partial results...")
        finalize_benchmark()
    else:
        print("No data collected.")
    client.disconnect()
except ConnectionRefusedError:
    print("Error: Could not connect to MQTT broker. Is Mosquitto running?")
