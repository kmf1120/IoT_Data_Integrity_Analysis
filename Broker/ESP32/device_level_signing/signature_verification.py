import paho.mqtt.client as mqtt
import struct
import csv
import os
import time
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

# --- CONFIGURATION ---
MQTT_BROKER = "localhost" 
TOPIC = "therm"
MAX_LOGS = 10000

# File Setup
current_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(current_dir, "benchmark_results.csv")

# Memory Buffer
results_buffer = []
failures = 0

print(f"Ready. Listening for 10k messages on topic '{TOPIC}'...")

def on_message(client, userdata, msg):
    global failures
    payload = msg.payload
    
    try:
        # 1. Slice Payload [msg][sig(64)][pub(32)][time(4)]
        # Extract SignTime (Last 4 bytes)
        sign_time_us = struct.unpack('<I', payload[-4:])[0]
        
        # Extract Public Key (32 bytes before the time)
        pub_key_bytes = payload[-36:-4]
        
        # Extract Signature (64 bytes before the public key)
        signature = payload[-100:-36]
        
        # Extract Raw Message (Everything else)
        raw_msg_bytes = payload[:-100]
        raw_msg_str = raw_msg_bytes.decode('ascii')

        # 2. Benchmark Verification
        # We use nanoseconds for high precision, then convert to microseconds
        v_start = time.perf_counter_ns()
        
        is_valid = False
        try:
            verify_key = VerifyKey(pub_key_bytes)
            verify_key.verify(raw_msg_bytes, signature)
            is_valid = True
        except BadSignatureError:
            is_valid = False
            failures += 1
        
        v_end = time.perf_counter_ns()
        verify_time_us = (v_end - v_start) / 1000

        # 3. Store in Buffer
        entry_number = len(results_buffer)
        results_buffer.append([entry_number, raw_msg_str, sign_time_us, f"{verify_time_us:.2f}", is_valid])

        # 4. Progress Tracking
        if len(results_buffer) % 500 == 0:
            print(f"Collected: {len(results_buffer)}/{MAX_LOGS} | Current Failures: {failures}")

        # 5. Completion Logic
        if len(results_buffer) >= MAX_LOGS:
            finalize_benchmark(client)
            
    except Exception as e:
        print(f"Error parsing payload: {e}")

def finalize_benchmark(client):
    print("\nBenchmark Complete! Writing to file...")
    
    with open(log_file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Entry", "Message", "SignTime_uS", "VerifyTime_uS", "Valid"])
        writer.writerows(results_buffer)
    
    # Calculate Stats
    total = len(results_buffer)
    fail_rate = (failures / total) * 100
    avg_sign = sum(row[2] for row in results_buffer) / total
    avg_verify = sum(float(row[3]) for row in results_buffer) / total

    print("--- RESULTS ---")
    print(f"Total Messages:  {total}")
    print(f"Failure Rate:    {fail_rate:.2f}%")
    print(f"Avg Sign Time:   {avg_sign:.2f} us")
    print(f"Avg Verify Time: {avg_verify:.2f} us")
    print(f"File Saved:      {log_file_path}")
    
    client.disconnect()

# Initialize MQTT
client = mqtt.Client()
client.on_message = on_message

try:
    client.connect(MQTT_BROKER, 1883)
    client.subscribe(TOPIC)
    client.loop_forever()
except KeyboardInterrupt:
    print("\nStopped by user. Data not saved.")