import argparse
import csv
import datetime
import os
import statistics
import struct
import subprocess
import threading
import time

import psutil
import paho.mqtt.client as mqtt

# ============================================
# Broker + Verifier for ESP32 -> Kubo IPFS CID
# ============================================
# INPUT topic payload format:
#   [utf8_sensor_message][sequence_id:uint32 little-endian][device_time_us:uint32 little-endian]
# Backward compatibility:
#   [utf8_sensor_message][device_time_us:uint32 little-endian]
# OUTPUT topic payload format:
#   [utf8_sensor_message][cid_utf8][cid_len:uint16 little-endian][hash_time_us:uint32 little-endian]

# --- CONFIG ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

TOPIC_RAW_IN = "therm_raw"
TOPIC_IPFS_OUT = "therm_ipfs"

VALIDATION_MODE = "double_hash"  # "double_hash" or "single_hash"
WARMUP_SECONDS = 30
REPUBLISH_QOS = 1

IPFS_EXE = r"C:\Users\green\kubo\kubo\ipfs.exe"

# --- ARGUMENTS: STRESS LABEL FOR FILENAMES ---
parser = argparse.ArgumentParser(description="ESP32 IPFS broker with stress-labelled output.")
parser.add_argument(
    "-s",
    "--stress",
    type=int,
    default=0,
    help="CPU/load label (0, 25, 50, 75, 99, etc.) used only to tag output filenames.",
)
args = parser.parse_args()

STRESS_LABEL = f"stress{args.stress}" if args.stress > 0 else "stress0"


CURRENT_DIR = os.path.join(
    r"C:\Users\green\Documents\Senior_Project_Repo\Broker\ESP32\IPFS",
    "results",
)
os.makedirs(CURRENT_DIR, exist_ok=True)


RUN_ID = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
RAW_LOG_FILE = os.path.join(CURRENT_DIR, f"raw_packet_data_ipfs_{STRESS_LABEL}_{RUN_ID}.csv")
SUMMARY_FILE = os.path.join(CURRENT_DIR, f"benchmark_summary_ipfs_{STRESS_LABEL}_{RUN_ID}.csv")

# metrics_buffer row:
# [Chunk_ID, Sequence_ID, Size_Bytes, DeviceTime_uS, HashTime_uS, VerifyTime_uS, CID_Valid, Published]
metrics_buffer = []
device_times = []
hash_times = []
verify_times = []
failures = 0
received_total = 0
warmup_skipped = 0
expected_sequence_id = None
missing_sequence_count = 0
out_of_order_count = 0
benchmark_start_monotonic = time.monotonic()

print(f"--- BENCHMARK RUN {RUN_ID} READY (ESP32 -> REAL IPFS, {STRESS_LABEL}) ---")
print(f"Directory: {CURRENT_DIR}")
print(f"Input topic : {TOPIC_RAW_IN}")
print(f"Output topic: {TOPIC_IPFS_OUT}")
print(f"Validation mode: {VALIDATION_MODE}")
print(f"Warm-up seconds: {WARMUP_SECONDS}")
print(f"Republish QoS: {REPUBLISH_QOS}")


_ipfs_repo_dir = os.environ.get("IPFS_PATH") or os.path.join(os.path.expanduser("~"), ".ipfs")
IPFS_REPO_LOCK = os.path.join(_ipfs_repo_dir, "repo.lock")
IPFS_MAX_RETRIES = 3
IPFS_RETRY_DELAY = 0.5  # seconds
_ipfs_lock = threading.Lock()  # serialise all ipfs subprocess calls — one at a time


def _clear_stale_lock():
    """Remove the IPFS repo.lock file if no ipfs process is actually running."""
    if not os.path.exists(IPFS_REPO_LOCK):
        return False
    for proc in psutil.process_iter(["name"]):
        try:
            if "ipfs" in proc.info["name"].lower():
                return False  # real process holds it — don't remove
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    try:
        os.remove(IPFS_REPO_LOCK)
        print(f"[IPFS] Removed stale lock: {IPFS_REPO_LOCK}")
        return True
    except OSError as e:
        print(f"[IPFS] Could not remove stale lock: {e}")
        return False


def ipfs_only_hash(data_bytes: bytes) -> str:
    with _ipfs_lock:  # only one ipfs subprocess at a time — avoids repo.lock races
        for attempt in range(1, IPFS_MAX_RETRIES + 1):
            try:
                result = subprocess.run(
                    [IPFS_EXE, "add", "-q", "--only-hash", "--cid-version=1", "--raw-leaves", "-"],
                    input=data_bytes,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                )
                return result.stdout.decode("utf-8").strip()
            except subprocess.CalledProcessError as e:
                err_msg = e.stderr.decode("utf-8", errors="ignore").strip()
                if "someone else has the lock" in err_msg or "repo.lock" in err_msg:
                    print(f"[IPFS] Lock contention (attempt {attempt}/{IPFS_MAX_RETRIES}): {err_msg}")
                    _clear_stale_lock()
                    time.sleep(IPFS_RETRY_DELAY)
                else:
                    print(f"[IPFS ERROR] {err_msg}")
                    return ""
        print(f"[IPFS ERROR] Failed after {IPFS_MAX_RETRIES} attempts due to lock contention")
        return ""


def percentile(values, pct):
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    index = int((pct / 100.0) * (len(sorted_vals) - 1))
    return sorted_vals[index]


def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe(TOPIC_RAW_IN)
    print(f"Subscribed to '{TOPIC_RAW_IN}'")


def on_message(client, userdata, msg):
    global failures, received_total, warmup_skipped
    global expected_sequence_id, missing_sequence_count, out_of_order_count

    payload = msg.payload
    received_total += 1

    try:
        if len(payload) < 4:
            raise ValueError("Payload too short for device time footer")

        if len(payload) >= 8:
            device_time_us = struct.unpack("<I", payload[-4:])[0]
            sequence_id = struct.unpack("<I", payload[-8:-4])[0]
            chunk_data = payload[:-8]
        else:
            device_time_us = struct.unpack("<I", payload[-4:])[0]
            sequence_id = None
            chunk_data = payload[:-4]

        if sequence_id is not None:
            if expected_sequence_id is None:
                expected_sequence_id = sequence_id + 1
            else:
                if sequence_id > expected_sequence_id:
                    missing_sequence_count += sequence_id - expected_sequence_id
                    expected_sequence_id = sequence_id + 1
                elif sequence_id < expected_sequence_id:
                    out_of_order_count += 1
                else:
                    expected_sequence_id += 1

        h_start = time.perf_counter_ns()
        cid = ipfs_only_hash(chunk_data)
        hash_time_us = (time.perf_counter_ns() - h_start) / 1000

        if not cid:
            if (time.monotonic() - benchmark_start_monotonic) >= WARMUP_SECONDS:
                failures += 1
            return

        cid_bytes = cid.encode("utf-8")
        cid_len = len(cid_bytes)
        if cid_len > 65535:
            raise ValueError("CID too long for uint16 footer")

        out_payload = (
            chunk_data
            + cid_bytes
            + struct.pack("<H", cid_len)
            + struct.pack("<I", int(hash_time_us))
        )
        published = client.publish(TOPIC_IPFS_OUT, out_payload, qos=REPUBLISH_QOS).rc == mqtt.MQTT_ERR_SUCCESS

        if VALIDATION_MODE == "double_hash":
            v_start = time.perf_counter_ns()
            verify_cid = ipfs_only_hash(chunk_data)
            verify_time_us = (time.perf_counter_ns() - v_start) / 1000
            cid_valid = verify_cid == cid
        else:
            verify_time_us = 0.0
            cid_valid = True

        in_warmup = (time.monotonic() - benchmark_start_monotonic) < WARMUP_SECONDS
        if in_warmup:
            warmup_skipped += 1
            return

        if not cid_valid:
            failures += 1
            print(f"⚠️ CID mismatch at Chunk #{len(metrics_buffer) + 1}")

        chunk_id = len(metrics_buffer) + 1
        device_times.append(device_time_us)
        hash_times.append(hash_time_us)
        verify_times.append(verify_time_us)
        metrics_buffer.append(
            [
                chunk_id,
                sequence_id if sequence_id is not None else "",
                len(chunk_data),
                device_time_us,
                f"{hash_time_us:.2f}",
                f"{verify_time_us:.2f}",
                cid_valid,
                published,
            ]
        )

        if chunk_id % 100 == 0:
            print(
                f"Chunk #{chunk_id:<5} | Dev: {device_time_us:<5}us | "
                f"Hash: {hash_time_us:<8.2f}us | Verify: {verify_time_us:<8.2f}us | "
                f"Valid: {cid_valid} | MissingSeq: {missing_sequence_count} | OoO: {out_of_order_count}"
            )

    except Exception as e:
        if (time.monotonic() - benchmark_start_monotonic) >= WARMUP_SECONDS:
            failures += 1
        print(f"Error: {e}")


def finalize_benchmark():
    print(f"\n{'=' * 20} RUN {RUN_ID} COMPLETE (ESP32 IPFS) {'=' * 20}")
    print(f"Messages received total: {received_total}")
    print(f"Warm-up skipped: {warmup_skipped}")
    print(f"Missing sequence estimate: {missing_sequence_count}")
    print(f"Out-of-order estimate: {out_of_order_count}")

    if not metrics_buffer:
        print("No data collected.")
        return

    total_chunks = len(metrics_buffer)
    avg_device = statistics.mean(device_times)
    avg_hash = statistics.mean(hash_times)
    avg_verify = statistics.mean(verify_times)
    max_device = max(device_times)
    max_hash = max(hash_times)
    max_verify = max(verify_times)
    p50_hash = percentile(hash_times, 50)
    p95_hash = percentile(hash_times, 95)
    p99_hash = percentile(hash_times, 99)
    p50_verify = percentile(verify_times, 50)
    p95_verify = percentile(verify_times, 95)
    p99_verify = percentile(verify_times, 99)
    success_rate = ((total_chunks - failures) / total_chunks) * 100 if total_chunks else 0.0

    with open(RAW_LOG_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Chunk_ID",
                "Sequence_ID",
                "Size_Bytes",
                "DeviceTime_uS",
                "HashTime_uS",
                "VerifyTime_uS",
                "CID_Valid",
                "Published",
            ]
        )
        writer.writerows(metrics_buffer)

    with open(SUMMARY_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Run_ID",
                "Timestamp",
                "Validation_Mode",
                "Warmup_Seconds",
                "Messages_Received_Total",
                "Warmup_Skipped",
                "Total_Chunks",
                "Success_Rate",
                "Missing_Sequence_Estimate",
                "OutOfOrder_Estimate",
                "Avg_Device_uS",
                "Max_Device_uS",
                "Avg_Hash_uS",
                "Max_Hash_uS",
                "P50_Hash_uS",
                "P95_Hash_uS",
                "P99_Hash_uS",
                "Avg_Verify_uS",
                "Max_Verify_uS",
                "P50_Verify_uS",
                "P95_Verify_uS",
                "P99_Verify_uS",
            ]
        )
        writer.writerow(
            [
                RUN_ID,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                VALIDATION_MODE,
                WARMUP_SECONDS,
                received_total,
                warmup_skipped,
                total_chunks,
                f"{success_rate:.2f}%",
                missing_sequence_count,
                out_of_order_count,
                f"{avg_device:.2f}",
                max_device,
                f"{avg_hash:.2f}",
                f"{max_hash:.2f}",
                f"{p50_hash:.2f}",
                f"{p95_hash:.2f}",
                f"{p99_hash:.2f}",
                f"{avg_verify:.2f}",
                f"{max_verify:.2f}",
                f"{p50_verify:.2f}",
                f"{p95_verify:.2f}",
                f"{p99_verify:.2f}",
            ]
        )

    print(f"Results saved as run #{RUN_ID} in: {CURRENT_DIR}")
    try:
        os.startfile(CURRENT_DIR)
    except Exception:
        pass


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT)
        client.loop_forever()
    except KeyboardInterrupt:
        finalize_benchmark()
        client.disconnect()


if __name__ == "__main__":
    main()
