# Firebase Realtime DB — Setup Guide for CBHV

This guide walks you through getting a free Firebase Realtime Database running
so `pi3_cbhv.py` (Pi 3) and `broker_cbhv.py` (laptop) can share hash records.

---

## 1. Create a Firebase Project (5 min)

1. Go to **https://console.firebase.google.com**
2. Click **"Add project"**
3. Give it a name (e.g., `senior-project-cbhv`) — disable Google Analytics if prompted
4. Click **"Create project"** and wait for it to provision

---

## 2. Create the Realtime Database (3 min)

1. In the left sidebar click **Build → Realtime Database**
2. Click **"Create Database"**
3. Choose the nearest region (US usually gives the lowest latency)
4. When prompted for security rules, select **"Start in test mode"**
   - This allows unauthenticated read/write — fine for a lab benchmark
   - The rules expire after 30 days; you can extend them in the Rules tab
5. Click **"Enable"**

---

## 3. Get Your Database URL

After the database is created you'll see a URL at the top of the Data tab:

```
https://senior-project-cbhv-default-rtdb.firebaseio.com/
```

Copy this URL — you need it in both scripts.

---

## 4. Update Both Scripts

Open **`pi3_cbhv.py`** on the Pi and **`broker_cbhv.py`** on the laptop.
Replace the placeholder in each file:

```python
# BEFORE
FIREBASE_URL = "https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com"

# AFTER (your actual URL, no trailing slash)
FIREBASE_URL = "https://senior-project-cbhv-default-rtdb.firebaseio.com"
```

---

## 5. Install the `requests` Library

Both scripts use `requests` for the Firebase REST API.

**On the Pi 3:**
```bash
pip3 install requests
```

**On the laptop (if not already installed):**
```bash
pip install requests
```

No Firebase SDK is needed — the Realtime DB has a built-in REST API.

---

## 6. Verify the Database Rules

In the Firebase console go to **Realtime Database → Rules** and confirm:

```json
{
  "rules": {
    ".read": "now < <expiry_timestamp>",
    ".write": "now < <expiry_timestamp>"
  }
}
```

For the duration of your benchmarking you can simplify to:

```json
{
  "rules": {
    ".read": true,
    ".write": true
  }
}
```

> **Note:** Revert to restrictive rules or delete the database after your
> benchmarking is finished so random internet traffic cannot write to it.

---

## 7. Test Connectivity (Optional)

From the Pi, run a quick sanity check with `curl`:

```bash
curl -X PUT \
  "https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com/test.json" \
  -d '"hello"'
```

You should see `"hello"` echoed back and it should appear in the Firebase
console under the Data tab.

---

## 8. Run the Benchmark

**On the laptop** (start broker first):
```bash
python broker_cbhv.py
```

**On the Pi 3** (after broker is ready):
```bash
sudo python3 pi3_cbhv.py
```

Results are saved to `results/benchmark_cbhv_results_<n>.csv` automatically
once `MAX_LOGS` (5000) messages are collected.

---

## Data Flow Summary

```
Pi 3
 ├─ SHA-256(LED data)  ──PUT──►  Firebase Realtime DB
 └─ [raw data + seq]  ──MQTT──►  Laptop broker
                                      │
                                 GET hash(seq) from Firebase
                                      │
                                 SHA-256(raw data) == cloud hash?
                                      │
                                 Write row to CSV
```

---

## CSV Output Columns

| Column | Description |
|---|---|
| `Entry` | Sequential message number |
| `MessageHex` | First 20 hex chars of raw LED data |
| `SeqNum` | Sequence number (links MQTT packet to Firebase entry) |
| `HashTime_uS` | Time to compute SHA-256 on the Pi (microseconds) |
| `UploadLatency_uS` | Round-trip time for Pi→Firebase PUT (microseconds) |
| `FetchLatency_uS` | Round-trip time for Laptop←Firebase GET (microseconds) |
| `VerifyTime_uS` | Local SHA-256 recompute + compare on laptop (microseconds) |
| `Valid` | `True` / `False` / `UNVERIFIABLE` |
