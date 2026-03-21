import argparse
import csv
import datetime
import os
import struct
import time
import subprocess

import paho.mqtt.client as mqtt

# --- CONFIGURATION ---
MQTT_BROKER = "localhost"
TOPIC = "light"
MAX_LOGS = 800
IPFS_EXE = r"C:\Users\green\kubo\kubo\ipfs.exe"

# --- ARGUMENTS: STRESS LABEL FOR FILENAMES ---
parser = argparse.ArgumentParser(description="Pi 3 LED IPFS broker with stress-labelled output.")
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
current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(current_dir, exist_ok=True)

RUN_ID = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
base_filename = f"benchmark_pi_ipfs_{STRESS_LABEL}_{RUN_ID}.csv"
log_file_path = os.path.join(current_dir, base_filename)

results_buffer = []
failures = 0

print(f"Logging to: {log_file_path}")
print(f"Ready. Listening for light data on '{TOPIC}'...")

def ipfs_only_hash(data_bytes: bytes) -> str:
    """
    Returns CID (v1) for data_bytes without storing it.
    Requires local IPFS daemon and `ipfs` CLI on PATH.
    """
    try:
        result = subprocess.run(
            [IPFS_EXE, "add", "-q", "--only-hash", "--cid-version=1", "--raw-leaves", "-"],
            input=data_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return result.stdout.decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
        print(f"[IPFS ERROR] {e.stderr.decode('utf-8', errors='ignore').strip()}")
        return ""

def on_message(client, userdata, msg):
    global failures
    payload = msg.payload

    try:
        # Structure: [Data][CID][CID_LEN(2)][Time(4)]
        if len(payload) < 6:
            raise ValueError("Payload too short to contain CID_LEN + Time.")

        sign_time_us = struct.unpack('<I', payload[-4:])[0]
        cid_len = struct.unpack('<H', payload[-6:-4])[0]

        if cid_len <= 0:
            raise ValueError("CID length invalid.")

        cid_start = len(payload) - 4 - 2 - cid_len
        if cid_start < 0:
            raise ValueError("CID length exceeds payload size.")

        cid_bytes = payload[cid_start:cid_start + cid_len]
        raw_msg_bytes = payload[:cid_start]

        # Convert binary LED data to Hex for readable CSV logging
        raw_msg_hex = raw_msg_bytes.hex()[:20] + "..."

        # Benchmark Verification (CID recompute)
        v_start = time.perf_counter_ns()

        is_valid = False
        computed_cid = ipfs_only_hash(raw_msg_bytes)
        if computed_cid and computed_cid.encode("utf-8") == cid_bytes:
            is_valid = True
        else:
            failures += 1

        v_end = time.perf_counter_ns()
        verify_time_us = (v_end - v_start) / 1000

        # Store in Buffer
        entry_number = len(results_buffer)
        results_buffer.append([entry_number, raw_msg_hex, sign_time_us, f"{verify_time_us:.2f}", is_valid])

        # Progress Indicator
        if len(results_buffer) % 100 == 0:
            print(f"Collected: {len(results_buffer)}/{MAX_LOGS} | Failures: {failures}")

        if len(results_buffer) >= MAX_LOGS:
            finalize_benchmark(client)

    except Exception as e:
        print(f"Error parsing payload: {e}")

def finalize_benchmark(client):
    print("\nBenchmark Complete! Writing to file...")

    with open(log_file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Entry", "MessageHex", "SignTime_uS", "VerifyTime_uS", "Valid"])
        writer.writerows(results_buffer)

    total = len(results_buffer)
    fail_rate = (failures / total) * 100 if total > 0 else 0
    avg_sign = sum(row[2] for row in results_buffer) / total if total > 0 else 0
    avg_verify = sum(float(row[3]) for row in results_buffer) / total if total > 0 else 0

    print("--- RESULTS (Pi 3 vs Laptop) ---")
    print(f"Total Messages:  {total}")
    print(f"Failure Rate:    {fail_rate:.2f}%")
    print(f"Avg Sign Time:   {avg_sign:.2f} us (Pi 3)")
    print(f"Avg Verify Time: {avg_verify:.2f} us (Laptop)")

    client.disconnect()
    os._exit(0)

# Initialize MQTT
client = mqtt.Client()
client.on_message = on_message

try:
    client.connect(MQTT_BROKER, 1883)
    client.subscribe(TOPIC)
    client.loop_forever()
except KeyboardInterrupt:
    print("\nStopped by user.")
except ConnectionRefusedError:
    print("Error: Could not connect to MQTT Broker. Is Mosquitto running?")