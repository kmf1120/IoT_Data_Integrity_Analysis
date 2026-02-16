import paho.mqtt.client as mqtt
import struct
import time
import os
import csv
import statistics
import datetime
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

# --- CONFIGURATION ---
MQTT_BROKER = "localhost" 
TOPIC = "cam"

# --- UPDATED DIRECTORY SETUP ---
# Using the specific path you requested
current_dir = r"C:\Users\green\Documents\Senior_Project_Repo\Broker\Pi5\device_level_signing\results"

if not os.path.exists(current_dir):
    os.makedirs(current_dir)

# --- GLOBAL NUMBERING LOGIC ---
# This finds the NEXT available ID number that hasn't been used by any of the 3 file types
def get_global_run_id(directory):
    run_id = 1
    while True:
        v_exists = os.path.exists(os.path.join(directory, f"final_signed_stream_{run_id}.h264"))
        r_exists = os.path.exists(os.path.join(directory, f"raw_packet_data_{run_id}.csv"))
        s_exists = os.path.exists(os.path.join(directory, f"benchmark_summary_{run_id}.csv"))
        if not (v_exists or r_exists or s_exists):
            return run_id
        run_id += 1

RUN_ID = get_global_run_id(current_dir)

# Define all file paths with the SAME Run ID
OUTPUT_VIDEO = os.path.join(current_dir, f"final_signed_stream_{RUN_ID}.h264")
RAW_LOG_FILE = os.path.join(current_dir, f"raw_packet_data_{RUN_ID}.csv")
SUMMARY_FILE = os.path.join(current_dir, f"benchmark_summary_{RUN_ID}.csv")

# Open video file for writing
video_file = open(OUTPUT_VIDEO, "wb")

# Data Storage
metrics_buffer = [] 
sign_times = []
verify_times = []
failures = 0

print(f"--- BENCHMARK RUN #{RUN_ID} READY ---")
print(f"Directory: {current_dir}")
print(f"Saving to: Video ({RUN_ID}), Raw Logs ({RUN_ID}), Summary ({RUN_ID})")
print(f"Waiting for stream on '{TOPIC}'...")

def on_message(client, userdata, msg):
    global failures
    payload = msg.payload
    
    try:
        # 1. Unpack Footer [Data] [Sig(64)] [Pub(32)] [Time(4)]
        device_sign_time_us = struct.unpack('<I', payload[-4:])[0]
        pub_key_bytes = payload[-36:-4]
        signature = payload[-100:-36]
        chunk_data = payload[:-100]

        # 2. Benchmark Verification
        v_start = time.perf_counter_ns()
        
        is_valid = False
        try:
            verify_key = VerifyKey(pub_key_bytes)
            verify_key.verify(chunk_data, signature)
            is_valid = True
            video_file.write(chunk_data)
        except BadSignatureError:
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
            print(f"Chunk #{chunk_id:<5} | Sign: {device_sign_time_us:<4}us | Verify: {laptop_verify_time_us:<6.2f}us")

    except Exception as e:
        print(f"Error: {e}")

def finalize_benchmark():
    print(f"\n{'='*20} RUN {RUN_ID} COMPLETE {'='*20}")
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
        writer.writerow(["Chunk_ID", "Size_Bytes", "SignTime_uS", "VerifyTime_uS", "Valid"])
        writer.writerows(metrics_buffer)

    # Save Run Summary
    with open(SUMMARY_FILE, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Run_ID", "Timestamp", "Total_Chunks", "Success_Rate", "Avg_Sign_uS", "Max_Sign_uS", "Avg_Verify_uS", "Max_Verify_uS"])
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
    os.startfile(current_dir) # Automatically open the results folder

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message

try:
    client.connect(MQTT_BROKER, 1883)
    client.subscribe(TOPIC)
    client.loop_forever()
except KeyboardInterrupt:
    finalize_benchmark()
    client.disconnect()