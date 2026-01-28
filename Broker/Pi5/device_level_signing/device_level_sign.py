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
MQTT_BROKER = "laptop.local"
TOPIC = "cam"
OUTPUT_VIDEO = "final_signed_stream.h264"
RAW_LOG_FILE = "raw_packet_data.csv"      # Detailed log (1400+ rows)
SUMMARY_FILE = "benchmark_summary.csv"    # One row per run

# --- SETUP ---
if os.path.exists(OUTPUT_VIDEO): os.remove(OUTPUT_VIDEO)
if os.path.exists(RAW_LOG_FILE): os.remove(RAW_LOG_FILE)

video_file = open(OUTPUT_VIDEO, "wb")

# Data Storage
metrics_buffer = [] 
sign_times = []
verify_times = []
failures = 0
total_bytes = 0

print(f"--- BENCHMARK READY ---")
print(f"Waiting for stream on '{TOPIC}'...")

def on_message(client, userdata, msg):
    global failures, total_bytes
    payload = msg.payload
    
    try:
        # 1. Unpack Footer
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
        
        # Laptop Verify Time (us)
        laptop_verify_time_us = (time.perf_counter_ns() - v_start) / 1000

        # 3. Store Data
        chunk_id = len(metrics_buffer) + 1
        chunk_size = len(chunk_data)
        total_bytes += chunk_size
        
        sign_times.append(device_sign_time_us)
        verify_times.append(laptop_verify_time_us)
        
        metrics_buffer.append([chunk_id, chunk_size, device_sign_time_us, f"{laptop_verify_time_us:.2f}", is_valid])

        # Live Feed (Sampled)
        if chunk_id % 100 == 0:
            print(f"Chunk #{chunk_id:<5} | Sign: {device_sign_time_us:<4}us | Verify: {laptop_verify_time_us:<6.2f}us")

    except Exception as e:
        print(f"Error: {e}")

def finalize_benchmark():
    print("\n" + "="*50)
    print("           BENCHMARK COMPLETE           ")
    print("="*50)
    
    video_file.close()
    
    if not metrics_buffer:
        print("No data collected.")
        return

    # --- 1. STATISTICS CALCULATION ---
    total_chunks = len(metrics_buffer)
    
    # Calculate Averages
    avg_sign = statistics.mean(sign_times)
    avg_verify = statistics.mean(verify_times)
    
    # Find Max Outliers and their Location
    max_sign = max(sign_times)
    max_sign_index = sign_times.index(max_sign) + 1 # +1 because ID starts at 1
    
    max_verify = max(verify_times)
    max_verify_index = verify_times.index(max_verify) + 1
    
    success_rate = ((total_chunks - failures)/total_chunks)*100

    # --- 2. PRINT REPORT ---
    print(f"Total Chunks:   {total_chunks}")
    print(f"Success Rate:   {success_rate:.2f}%")
    print("-" * 50)
    print(f"DEVICE SIGNING (Pi 5):")
    print(f"  Average:      {avg_sign:.2f} us")
    print(f"  Max Spike:    {max_sign} us (Occurred at Chunk #{max_sign_index})")
    print("-" * 50)
    print(f"BROKER VERIFYING (Laptop):")
    print(f"  Average:      {avg_verify:.2f} us")
    print(f"  Max Spike:    {max_verify:.2f} us (Occurred at Chunk #{max_verify_index})")
    print("="*50)

    # --- 3. SAVE RAW LOGS (Detailed) ---
    with open(RAW_LOG_FILE, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Chunk_ID", "Size_Bytes", "SignTime_uS", "VerifyTime_uS", "Valid"])
        writer.writerows(metrics_buffer)
    print(f"Detailed logs -> {RAW_LOG_FILE}")

    # --- 4. SAVE SUMMARY ROW (Append Mode) ---
    # This allows you to run the test 10 times and get 10 rows in this file
    file_exists = os.path.exists(SUMMARY_FILE)
    with open(SUMMARY_FILE, "a", newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Total_Chunks", "Avg_Sign_uS", "Max_Sign_uS", "Avg_Verify_uS", "Max_Verify_uS"])
        
        writer.writerow([
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_chunks,
            f"{avg_sign:.2f}",
            max_sign,
            f"{avg_verify:.2f}",
            f"{max_verify:.2f}"
        ])
    print(f"Summary stats -> {SUMMARY_FILE}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
client.connect(MQTT_BROKER, 1883)
client.subscribe(TOPIC)

try:
    client.loop_forever()
except KeyboardInterrupt:
    finalize_benchmark()
    client.disconnect()