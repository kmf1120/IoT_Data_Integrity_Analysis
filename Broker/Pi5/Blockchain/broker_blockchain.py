#!/usr/bin/env python3
# Blockchain-style integrity broker for Pi 5
#
# Expected payload per MQTT message from pi5_blockchain.py:
#   [chunk_data][index(4)][hash_time_us(4)][prev_block_hash(32)][block_hash(32)]
#
# The broker recomputes chunk_hash = SHA256(chunk_data) and
# block_hash' = SHA256(prev_block_hash || chunk_hash), verifies
# the chain, and only writes valid chunks to the output .h264 file.

import argparse
import csv
import datetime
import hashlib
import os
import statistics
import struct
import time

import paho.mqtt.client as mqtt

# --- CONFIGURATION ---
MQTT_BROKER = "localhost"
TOPIC = "cam/blockchain"

# --- ARGUMENTS: STRESS LABEL FOR FILENAMES ---
parser = argparse.ArgumentParser(description="Blockchain integrity broker with stress-labelled output.")
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
current_dir = r"C:\Users\green\Documents\Senior_Project_Repo\Broker\Pi5\Blockchain\results"
os.makedirs(current_dir, exist_ok=True)

RUN_ID = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_NAME = f"{STRESS_LABEL}_{RUN_ID}"

VIDEO_FILE = os.path.join(current_dir, f"verified_stream_blockchain_{BASE_NAME}.h264")
RAW_LOG_FILE = os.path.join(current_dir, f"raw_packet_data_blockchain_{BASE_NAME}.csv")
SUMMARY_FILE = os.path.join(current_dir, f"benchmark_summary_blockchain_{BASE_NAME}.csv")

video_file = open(VIDEO_FILE, "wb")

# Data storage
metrics_buffer = []  # rows: [Index, Size_Bytes, HashTime_uS, VerifyTime_uS, PrevHash_OK, Valid]
hash_times = []
verify_times = []
failures = 0

expected_prev_hash = b"\x00" * 32  # genesis

print(f"--- BLOCKCHAIN BENCHMARK RUN {RUN_ID} READY ({STRESS_LABEL}) ---")
print(f"Directory: {current_dir}")
print(f"Waiting for stream on '{TOPIC}'...")


# ---------------------------------------------------------------------------
# MQTT CALLBACK
# ---------------------------------------------------------------------------
def on_message(client, userdata, msg):
    global failures, expected_prev_hash
    payload = msg.payload

    try:
        # Footer is last 72 bytes: [index(4)][hash_time(4)][prev_hash(32)][block_hash(32)]
        if len(payload) < 72:
            raise ValueError(f"Payload too short ({len(payload)} bytes)")

        footer = payload[-72:]
        chunk_data = payload[:-72]

        index, hash_time_us = struct.unpack("<II", footer[:8])
        prev_hash = footer[8:40]
        block_hash = footer[40:72]

        # Verify prev_hash continuity
        prev_ok = prev_hash == expected_prev_hash

        # Recompute chunk hash and block hash
        v_start = time.perf_counter()
        chunk_hash = hashlib.sha256(chunk_data).digest()
        recomputed_block_hash = hashlib.sha256(prev_hash + chunk_hash).digest()
        verify_time_us = int((time.perf_counter() - v_start) * 1_000_000)

        valid_block = prev_ok and (recomputed_block_hash == block_hash)

        if valid_block:
            video_file.write(chunk_data)
            expected_prev_hash = block_hash
        else:
            failures += 1
            print(
                f"INVALID block index={index} | prev_ok={prev_ok} | "
                f"hash_match={recomputed_block_hash == block_hash}"
            )

        # Store metrics
        metrics_buffer.append([
            index,
            len(chunk_data),
            hash_time_us,
            verify_time_us,
            prev_ok,
            valid_block,
        ])
        hash_times.append(hash_time_us)
        verify_times.append(verify_time_us)

        if index % 50 == 0:
            print(
                f"Block #{index:<5} | Size: {len(chunk_data)} B | "
                f"Hash: {hash_time_us} us | Verify: {verify_time_us} us | Valid: {valid_block}"
            )

    except Exception as e:
        print(f"Error parsing payload: {e}")


# ---------------------------------------------------------------------------
# FINALIZE
# ---------------------------------------------------------------------------

def finalize_benchmark():
    print(f"\n{'=' * 20} RUN {RUN_ID} COMPLETE ({STRESS_LABEL}) {'=' * 20}")
    video_file.close()

    if not metrics_buffer:
        print("No data collected.")
        return

    total_blocks = len(metrics_buffer)
    valid_blocks = sum(1 for _, _, _, _, _, v in metrics_buffer if v)
    success_rate = (valid_blocks / total_blocks) * 100 if total_blocks else 0.0

    avg_hash = statistics.mean(hash_times) if hash_times else 0.0
    avg_verify = statistics.mean(verify_times) if verify_times else 0.0
    max_hash = max(hash_times) if hash_times else 0.0
    max_verify = max(verify_times) if verify_times else 0.0

    # Raw per-block log
    with open(RAW_LOG_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Block_Index",
            "Size_Bytes",
            "HashTime_uS",
            "VerifyTime_uS",
            "PrevHash_OK",
            "Valid",
        ])
        writer.writerows(metrics_buffer)

    # Single-row summary
    with open(SUMMARY_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Run_ID",
            "Stress_Label",
            "Timestamp",
            "Total_Blocks",
            "Valid_Blocks",
            "Success_Rate",
            "Avg_Hash_uS",
            "Max_Hash_uS",
            "Avg_Verify_uS",
            "Max_Verify_uS",
        ])
        writer.writerow([
            RUN_ID,
            STRESS_LABEL,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_blocks,
            valid_blocks,
            f"{success_rate:.2f}%",
            f"{avg_hash:.2f}",
            max_hash,
            f"{avg_verify:.2f}",
            max_verify,
        ])

    print(f"Total Blocks:      {total_blocks}")
    print(f"Valid Blocks:      {valid_blocks}")
    print(f"Success Rate:      {success_rate:.2f}%")
    print(f"Avg Hash (Pi 5):   {avg_hash:.2f} us")
    print(f"Avg Verify (PC):   {avg_verify:.2f} us")
    print(f"Results base name: {BASE_NAME}")

    try:
        os.startfile(current_dir)
    except Exception:
        pass


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
        print(f"Saving {len(metrics_buffer)} blocks...")
        finalize_benchmark()
    else:
        print("No data collected.")
    client.disconnect()
except ConnectionRefusedError:
    print("Error: Could not connect to MQTT broker. Is Mosquitto running?")
