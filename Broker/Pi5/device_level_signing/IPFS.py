import paho.mqtt.client as mqtt
import struct
import time
import os
import csv
import statistics
import datetime
import subprocess

# --- CONFIGURATION ---
MQTT_BROKER = "localhost" 
TOPIC = "cam"
IPFS_EXE = r"C:\Users\green\kubo\kubo\ipfs.exe"

# --- UPDATED DIRECTORY SETUP ---
current_dir = r"C:\Users\green\Documents\Senior_Project_Repo\Broker\Pi5\IPFS\results"

if not os.path.exists(current_dir):
    os.makedirs(current_dir)

# --- GLOBAL NUMBERING LOGIC ---
def get_global_run_id(directory):
    run_id = 1
    while True:
        v_exists = os.path.exists(os.path.join(directory, f"final_ipfs_stream_{run_id}.h264"))
        r_exists = os.path.exists(os.path.join(directory, f"raw_packet_data_{run_id}.csv"))
        s_exists = os.path.exists(os.path.join(directory, f"benchmark_summary_{run_id}.csv"))
        if not (v_exists or r_exists or s_exists):
            return run_id
        run_id += 1

RUN_ID = get_global_run_id(current_dir)

# Define all file paths with the SAME Run ID
OUTPUT_VIDEO = os.path.join(current_dir, f"final_ipfs_stream_{RUN_ID}.h264")
RAW_LOG_FILE = os.path.join(current_dir, f"raw_packet_data_{RUN_ID}.csv")
SUMMARY_FILE = os.path.join(current_dir, f"benchmark_summary_{RUN_ID}.csv")

# Open video file for writing
video_file = open(OUTPUT_VIDEO, "wb")

# Data Storage
metrics_buffer = [] 
sign_times = []
verify_times = []
failures = 0

print(f"--- BENCHMARK RUN #{RUN_ID} READY (IPFS) ---")
print(f"Directory: {current_dir}")
print(f"Saving to: Video ({RUN_ID}), Raw Logs ({RUN_ID}), Summary ({RUN_ID})")
print(f"Waiting for stream on '{TOPIC}'...")

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
        # 1. Unpack Footer [Data] [CID] [CID_LEN(2)] [Time(4)]
        if len(payload) < 6:
            raise ValueError("Payload too short.")

        device_sign_time_us = struct.unpack('<I', payload[-4:])[0]
        cid_len = struct.unpack('<H', payload[-6:-4])[0]

        if cid_len <= 0:
            raise ValueError("CID length invalid.")

        cid_start = len(payload) - 4 - 2 - cid_len
        if cid_start < 0:
            raise ValueError("CID length exceeds payload size.")

        cid_bytes = payload[cid_start:cid_start + cid_len]
        chunk_data = payload[:cid_start]

        # 2. Benchmark Verification (CID recompute)
        v_start = time.perf_counter_ns()
        
        is_valid = False
        computed_cid = ipfs_only_hash(chunk_data)
        if computed_cid and computed_cid.encode("utf-8") == cid_bytes:
            is_valid = True
            video_file.write(chunk_data)
        else:
            is_valid = False
            failures += 1
            print(f"⚠️ FAILURE at Chunk #{len(metrics_buffer)}")
        
        laptop_verify_time_us = (time.perf_counter_ns() - v_start) / 1000

        # 3. Store Data
        chunk_id = len(metrics_buffer) + 1
        sign_times.append(device_sign_time_us)
        verify_times.append(laptop_verify_time_us)
        metrics_buffer.append([chunk_id, len(chunk_data), device_sign_time_us, f"{laptop_verify_time_us:.2f}", is_valid])

        if chunk_id % 100 == 0:
            print(f"Chunk #{chunk_id:<5} | Hash: {device_sign_time_us:<4}us | Verify: {laptop_verify_time_us:<6.2f}us")

    except Exception as e:
        print(f"Error: {e}")

def finalize_benchmark():
    print(f"\n{'='*20} RUN {RUN_ID} COMPLETE (IPFS) {'='*20}")
    video_file.close()
    
    if not metrics_buffer:
        print("No data collected.")
        return

    # Statistics
    total_chunks = len(metrics_buffer)
    avg_sign = statistics.mean(sign_times)
    avg_verify = statistics.mean(verify_times)
    max_sign = max(sign_times)
    max_verify = max(verify_times)
    success_rate = ((total_chunks - failures)/total_chunks)*100

    # Save Detailed Raw Log
    with open(RAW_LOG_FILE, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Chunk_ID", "Size_Bytes", "HashTime_uS", "VerifyTime_uS", "Valid"])
        writer.writerows(metrics_buffer)

    # Save Run Summary
    with open(SUMMARY_FILE, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Run_ID", "Timestamp", "Total_Chunks", "Success_Rate", "Avg_Hash_uS", "Max_Hash_uS", "Avg_Verify_uS", "Max_Verify_uS"])
        writer.writerow([
            RUN_ID,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_chunks,
            f"{success_rate:.2f}%",
            f"{avg_sign:.2f}",
            max_sign,
            f"{avg_verify:.2f}",
            f"{max_verify:.2f}"
        ])
    
    print(f"Results saved as set #{RUN_ID} in results folder.")
    os.startfile(current_dir)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message

try:
    client.connect(MQTT_BROKER, 1883)
    client.subscribe(TOPIC)
    client.loop_forever()
except KeyboardInterrupt:
    finalize_benchmark()
    client.disconnect()