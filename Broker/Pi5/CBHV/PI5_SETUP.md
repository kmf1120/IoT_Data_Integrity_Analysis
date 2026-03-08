# Pi 5 CBHV — Setup & Run Guide

The Firebase project is already created from the Pi 3 setup.
This guide covers only what's different or new for the Pi 5.

---

## 1. Update the Firebase URL in Both Scripts

You already have your project ID: `senior-project-bdb33`

Open **`Pi5/CBHV/pi5_cbhv.py`** (on the Pi 5) and **`Broker/Pi5/CBHV/broker_cbhv.py`** (on the laptop)
and replace the placeholder in both:

```python
# BEFORE
FIREBASE_URL = "https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com"

# AFTER
FIREBASE_URL = "https://senior-project-bdb33-default-rtdb.firebaseio.com"
```

Also update the MQTT broker address in `pi5_cbhv.py`:
```python
MQTT_BROKER = "laptop.local"   # or your laptop's IP address
```

---

## 2. Set Up the Venv on the Pi 5

Pi 5 also runs Raspberry Pi OS Bookworm, so use a venv.
The Pi 5 already has `picamera2` installed system-wide, but we need it
accessible in the venv too — use `--system-site-packages` to inherit it:

```bash
# Create a venv that can see system packages (needed for picamera2)
python3 -m venv ~/rgb/CBHV/venv --system-site-packages

# Activate it
source ~/rgb/CBHV/venv/bin/activate

# Install remaining dependencies
pip install requests paho-mqtt
```

> **Why `--system-site-packages`?**
> `picamera2` is installed via `apt` into the system Python, not pip.
> Using `--system-site-packages` lets the venv see it without reinstalling.
> `requests` and `paho-mqtt` still install cleanly into the venv on top.

---

## 3. Copy the Script to the Pi 5

From your laptop, use `scp` to transfer the script:

```bash
scp Pi5/CBHV/pi5_cbhv.py kf@pi5.local:~/rgb/CBHV/pi5_cbhv.py
```

Or create the file directly on the Pi 5 using `nano`:

```bash
mkdir -p ~/rgb/CBHV
nano ~/rgb/CBHV/pi5_cbhv.py
```

---

## 4. Run the Benchmark

**On the laptop** — start the broker first:
```powershell
& C:/Users/green/Documents/Senior_Project_Repo/.venv/Scripts/python.exe `
  C:/Users/green/Documents/Senior_Project_Repo/Broker/Pi5/CBHV/broker_cbhv.py
```

**On the Pi 5** — then start recording:
```bash
source ~/rgb/CBHV/venv/bin/activate
sudo ~/rgb/CBHV/venv/bin/python ~/rgb/CBHV/pi5_cbhv.py
```

The script records for **60 seconds** by default (set by `RECORD_SECONDS = 60`).
Press Ctrl+C on the Pi to stop early — the broker will save whatever was collected.

---

## 5. Output Files

Results land in `Broker/Pi5/CBHV/results/`:

| File | Description |
|---|---|
| `verified_stream_<n>.h264` | Reassembled video — verified chunks only |
| `raw_packet_data_<n>.csv` | Per-chunk detail log |
| `benchmark_summary_<n>.csv` | Single-row run summary |

### raw_packet_data columns

| Column | Description |
|---|---|
| `Chunk_ID` | Monotonic chunk counter |
| `Size_Bytes` | Size of this chunk in bytes |
| `SeqNum` | Sequence number (links to Firebase entry) |
| `HashTime_uS` | SHA-256 time on Pi 5 (microseconds) |
| `UploadLatency_uS` | Pi 5 → Firebase PUT round-trip (microseconds) |
| `FetchLatency_uS` | Laptop ← Firebase GET round-trip (microseconds) |
| `VerifyTime_uS` | Local SHA-256 recompute + compare (microseconds) |
| `Valid` | `True` / `False` / `UNVERIFIABLE` |

---

## 6. Key Differences vs Pi 3 CBHV

| | Pi 3 CBHV | Pi 5 CBHV |
|---|---|---|
| Data source | NeoPixel LED state (60 × 4 bytes = 240 B) | H.264 video chunks (up to 4096 B) |
| MQTT topic | `light/cbhv` | `cam/cbhv` |
| Output | CSV only | CSV + `.h264` video file |
| Chunk count | ~5000 LED frames | ~hundreds of video chunks per 60s |
| Firebase path pattern | `/hashes/<seq>` | `/hashes/<seq>` (same DB, different run) |

Both use the same Firebase project — they won't collide because each run
starts `seq_num` from 0 and the broker only looks up hashes during its
own active session. Old hash entries in Firebase don't affect new runs.

---

## 7. Play Back the Verified Video

On the laptop after the run:

```powershell
ffplay "C:\Users\green\Documents\Senior_Project_Repo\Broker\Pi5\CBHV\results\verified_stream_1.h264"
```

Or open it in VLC. If `ffplay` isn't installed, use:
```powershell
ffmpeg -i verified_stream_1.h264 verified_stream_1.mp4
```
to convert it first, then open the `.mp4` in any player.
