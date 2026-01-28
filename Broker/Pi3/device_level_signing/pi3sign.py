import paho.mqtt.client as mqtt
import struct
import csv
import os
import time
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

# --- CONFIGURATION ---
# Since this runs ON the laptop (where the broker is), use localhost
# for pi 3
MQTT_BROKER = "localhost" 
TOPIC = "light"
MAX_LOGS = 5000 

# File Setup
current_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(current_dir, "benchmark_pi_results.csv")

results_buffer = []
failures = 0

print(f"Logging to: {log_file_path}")
print(f"Ready. Listening for light data on '{TOPIC}'...")

def on_message(client, userdata, msg):
    global failures
    payload = msg.payload
    
    try:
        # Structure: [Data] [Sig(64)] [Pub(32)] [Time(4)]
        
        # 1. Extract Footer (Last 100 bytes)
        sign_time_us = struct.unpack('<I', payload[-4:])[0]
        pub_key_bytes = payload[-36:-4]
        signature = payload[-100:-36]
        
        # 2. Extract Data (Everything before the footer)
        raw_msg_bytes = payload[:-100]
        
        # Convert binary LED data to Hex for readable CSV logging
        # We only log the first 20 chars to keep the CSV file size manageable
        raw_msg_hex = raw_msg_bytes.hex()[:20] + "..."

        # 3. Benchmark Verification
        v_start = time.perf_counter_ns()
        
        is_valid = False
        try:
            # Recreate the key from the bytes sent in the packet
            verify_key = VerifyKey(pub_key_bytes)
            verify_key.verify(raw_msg_bytes, signature)
            is_valid = True
        except BadSignatureError:
            is_valid = False
            failures += 1
        
        v_end = time.perf_counter_ns()
        verify_time_us = (v_end - v_start) / 1000

        # 4. Store in Buffer
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
    os._exit(0) # Force exit to stop the loop

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