### System Environment ###

## Broker/Verifier: ##

OS Name:                       Microsoft Windows 11 Home
OS Version:                    10.0.26100 N/A Build 26100
OS Manufacturer:               Microsoft Corporation
OS Configuration:              Standalone Workstation
OS Build Type:                 Multiprocessor Free
Registered Organization:       HP
System Manufacturer:           HP
System Model:                  OMEN by HP Laptop PC
System Type:                   x64-based PC
Processor(s):                  1 Processor(s) Installed.
                               [01]: AMD64 Family 23 Model 96 Stepping 1 AuthenticAMD ~2900 Mhz
BIOS Version:                  AMI F.13, 3/4/2021
Total Physical Memory:         15,731 MB
Available Physical Memory:     6,761 MB
Virtual Memory: Max Size:      19,827 MB
Network Card(s):               3 NIC(s) Installed.
                               [02]: Intel(R) Wi-Fi 6 AX200 160MHz

## Thermometer Device: ##

Chip Model: ESP32-D0WD-V3
Chip Revision: 301
CPU Frequency: 240 MHz
Flash Size: 4 MB
Flash Speed: 80 MHz
Free Heap: 287160 bytes
SDK Version: v5.5.1-931-g9bb7aa84fe

## Smart Lights Device: ##

# CPU:
Architecture:                aarch64
  CPU op-mode(s):            32-bit, 64-bit
  Byte Order:                Little Endian
CPU(s):                      4
  On-line CPU(s) list:       0-3
Vendor ID:                   ARM
  Model name:                Cortex-A53
    Model:                   4
    Thread(s) per core:      1
    Core(s) per cluster:     4
    Socket(s):               -
    Cluster(s):              1
    Stepping:                r0p4
    CPU(s) scaling MHz:      43%
    CPU max MHz:             1400.0000
    CPU min MHz:             600.0000
    BogoMIPS:                38.40
    Flags:                   fp asimd evtstrm crc32 cpuid
Caches (sum of all):
  L1d:                       128 KiB (4 instances)
  L1i:                       128 KiB (4 instances)
  L2:                        512 KiB (1 instance)
NUMA:
  NUMA node(s):              1
  NUMA node0 CPU(s):         0-3
Vulnerabilities:
  Gather data sampling:      Not affected
  Indirect target selection: Not affected
  Itlb multihit:             Not affected
  L1tf:                      Not affected
  Mds:                       Not affected
  Meltdown:                  Not affected
  Mmio stale data:           Not affected
  Reg file data sampling:    Not affected
  Retbleed:                  Not affected
  Spec rstack overflow:      Not affected
  Spec store bypass:         Not affected
  Spectre v1:                Mitigation; __user pointer sanitization
  Spectre v2:                Not affected
  Srbds:                     Not affected
  Tsa:                       Not affected
  Tsx async abort:           Not affected
  Vmscape:                   Not affected

# Kernal Version:
Linux pi3 6.12.47+rpt-rpi-v8 #1 SMP PREEMPT Debian 1:6.12.47-1+rpt1 (2025-09-16) aarch64 GNU/Linux

# Memory:
                 total        used        free      shared  buff/cache   available
Mem:             906         149         662           4         149         756
Swap:            905           0         905

# Storage Name:
SC16G
# Storage Speed:
0x0235844300000000
# Available Storage:
Filesystem      Size  Used Avail Use% Mounted on
/dev/mmcblk0p2   15G  3.0G   11G  22% /

# Pi 3B+ Revision:
Revision        : a020d4

# Baseline Tasks:
top - 22:25:01 up 41 min,  1 user,  load average: 0.00, 0.00, 0.00
Tasks: 143 total,   1 running, 142 sleeping,   0 stopped,   0 zombie
%Cpu(s):  0.1 us,  0.2 sy,  0.0 ni, 99.8 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :    906.0 total,    659.5 free,    150.5 used,    152.3 buff/cache
MiB Swap:    906.0 total,    906.0 free,      0.0 used.    755.6 avail Mem



## Camera Device: ##

# CPU:
Architecture:                aarch64
  CPU op-mode(s):            32-bit, 64-bit
  Byte Order:                Little Endian
CPU(s):                      4
  On-line CPU(s) list:       0-3
Vendor ID:                   ARM
  Model name:                Cortex-A76
    Model:                   1
    Thread(s) per core:      1
    Core(s) per cluster:     4
    Socket(s):               -
    Cluster(s):              1
    Stepping:                r4p1
    CPU(s) scaling MHz:      62%
    CPU max MHz:             2400.0000
    CPU min MHz:             1500.0000
    BogoMIPS:                108.00
    Flags:                   fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp cpuid asimdrdm lrcpc dcpop asimddp
Caches (sum of all):
  L1d:                       256 KiB (4 instances)
  L1i:                       256 KiB (4 instances)
  L2:                        2 MiB (4 instances)
  L3:                        2 MiB (1 instance)
NUMA:
  NUMA node(s):              8
  NUMA node0 CPU(s):         0-3
  NUMA node1 CPU(s):         0-3
  NUMA node2 CPU(s):         0-3
  NUMA node3 CPU(s):         0-3
  NUMA node4 CPU(s):         0-3
  NUMA node5 CPU(s):         0-3
  NUMA node6 CPU(s):         0-3
  NUMA node7 CPU(s):         0-3
Vulnerabilities:
  Gather data sampling:      Not affected
  Indirect target selection: Not affected
  Itlb multihit:             Not affected
  L1tf:                      Not affected
  Mds:                       Not affected
  Meltdown:                  Not affected
  Mmio stale data:           Not affected
  Reg file data sampling:    Not affected
  Retbleed:                  Not affected
  Spec rstack overflow:      Not affected
  Spec store bypass:         Mitigation; Speculative Store Bypass disabled via prctl
  Spectre v1:                Mitigation; __user pointer sanitization
  Spectre v2:                Mitigation; CSV2, BHB
  Srbds:                     Not affected
  Tsa:                       Not affected
  Tsx async abort:           Not affected
  Vmscape:                   Not affected

  # Kernal Version:
  Linux pi5 6.12.47+rpt-rpi-2712 #1 SMP PREEMPT Debian 1:6.12.47-1+rpt1 (2025-09-16) aarch64 GNU/Linux

  # Memory:
                 total        used        free      shared  buff/cache   available
    Mem:            8063         253        7635          13         256        7809
    Swap:           2047           0        2047

# Storage Name:
SDABC
# Storage Speed:
02b5800300000000
# Available Storage:
Filesystem      Size  Used Avail Use% Mounted on
/dev/mmcblk0p2   14G  4.5G  8.8G  34% /

# Pi 5 Revision:
Revision        : d04171
# Baseline Tasks:
top - 22:31:15 up 47 min,  1 user,  load average: 0.00, 0.00, 0.00
Tasks: 162 total,   1 running, 161 sleeping,   0 stopped,   0 zombie
%Cpu(s):  0.0 us,  0.0 sy,  0.0 ni,100.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :   8063.0 total,   7630.9 free,    257.2 used,    256.9 buff/cache
MiB Swap:   2048.0 total,   2048.0 free,      0.0 used.   7805.8 avail Mem


### MQTT Configuration ###
Thermometor Device: <PubSubClient.h>
Smart Lights Device: paho.mqtt.client
Camera Device: paho.mqtt.client
Broker/Verifier: paho.mqtt.client

# Baseline Test Environment
With no (configured) background tasks running (check if this is true), baseline tests were conducted to measure latency on each of the IoT devices.
This included the latency of the signing time; the additional time required to perform an Ed25519 hash calculation. This also included the latency of the verification time; the additional time required by the broker to perform a signature verification of the Ed25519 Signature (for device level signing operations)

---

## Device-Level Signing Results (Consolidated)

### ESP32 Thermometer (Broker verification)
Source: `Broker/ESP32/device_level_signing/results/benchmark_results.csv`  
Total entries: **10,000**  
Success rate: **100.00%**

| Metric | Value |
|---|---:|
| Avg Sign Time (uS) | 46,319.87 |
| Max Sign Time (uS) | 46,393.00 |
| Avg Verify Time (uS) | 202.94 |
| Max Verify Time (uS) | 981.80 |

### Pi3 Smart Lights (Broker verification)

| Scenario | Source File | Total Entries | Success Rate | Avg Sign (uS) | Max Sign (uS) | Avg Verify (uS) | Max Verify (uS) |
|---|---|---:|---:|---:|---:|---:|---:|
| Early Dev Run | `Broker/Pi3/device_level_signing/benchmark_pi_results_1.csv` | 5,000 | 100.00% | 99,192.21 | 194,199.00 | 36,497.29 | 56,841.50 |
| No Stress | `Broker/Pi3/device_level_signing/results/benchmark_pi_results.csv` | 5,000 | 100.00% | 487.07 | 910.00 | 239.83 | 817.80 |
| Stress 50 | `Broker/Pi3/device_level_signing/results/benchmark_pi_results_(stress-50).csv` | 5,000 | 100.00% | 294.40 | 5,265.00 | 212.41 | 10,549.70 |
| Stress 99 | `Broker/Pi3/device_level_signing/results/benchmark_pi_results_(stress-99).csv` | 5,000 | 100.00% | 339.17 | 4,800.00 | 216.40 | 855.70 |

### Pi5 Camera (Device-level signing benchmark summaries)

| Scenario | Source File | Timestamp | Total Chunks | Success Rate | Avg Sign (uS) | Max Sign (uS) | Avg Verify (uS) | Max Verify (uS) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| No Stress | `Broker/Pi5/device_level_signing/results/no stress/benchmark_summary.csv` | 2026-01-26 16:30:34 | 4,238 | N/A | 165.53 | 3,465 | 309.94 | 913.70 |
| Stress 25 | `Broker/Pi5/device_level_signing/results/stress25/benchmark_summary_1.csv` | 2026-02-07 16:09:32 | 4,230 | 100.00% | 139.97 | 5,161 | 293.77 | 5,067.70 |
| Stress 50 | `Broker/Pi5/device_level_signing/results/stress50/benchmark_summary1.csv` | 2026-02-07 16:01:24 | 4,377 | N/A | 149.95 | 7,629 | 282.89 | 10,570.00 |
| Stress 75 | `Broker/Pi5/device_level_signing/results/stress75/benchmark_summary_1.csv` | 2026-02-07 16:11:23 | 4,230 | 100.00% | 158.46 | 5,565 | 292.48 | 1,257.90 |
| Stress 99 | `Broker/Pi5/device_level_signing/results/stress99/benchmark_summary_1.csv` | 2026-02-07 16:13:00 | 4,228 | 100.00% | 173.04 | 7,376 | 286.30 | 1,385.70 |

---

## IPFS Results (Consolidated)

### Pi5 IPFS Hash + Verify

| Run | Source File | Timestamp | Total Chunks | Success Rate | Avg Hash (uS) | Max Hash (uS) | Avg Verify (uS) | Max Verify (uS) |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1 | `Broker/Pi5/IPFS/results/benchmark_summary_1.csv` | 2026-02-15 22:01:42 | 2,481 | 100.00% | 19,855.99 | 32,443.00 | 36,607.57 | 49,253.40 |
| 2 | `Broker/Pi5/IPFS/results/benchmark_summary_2.csv` | 2026-02-15 22:09:16 | 2,692 | 100.00% | 19,913.55 | 29,267.00 | 36,743.69 | 47,372.20 |

### ESP32 -> Broker/Kubo IPFS Pipeline

| Run | Source File | Timestamp | Total Chunks | Success Rate | Avg Device (uS) | Max Device (uS) | Avg Hash (uS) | Max Hash (uS) | P50 Hash (uS) | P95 Hash (uS) | Avg Verify (uS) | Max Verify (uS) | P50 Verify (uS) | P95 Verify (uS) |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `Broker/ESP32/IPFS/results/benchmark_summary_1.csv` | 2026-03-01 19:43:00 | 52 | 100.00% | 448.27 | 495 | 62,062.56 | 382,014.00 | — | — | 55,782.32 | 62,952.70 | — | — |
| 2 | `Broker/ESP32/IPFS/results/benchmark_summary_2.csv` | 2026-03-01 19:54:38 | 5,939 | 100.00% | 449.05 | 568 | 56,378.79 | 293,549.80 | — | — | 56,580.27 | 716,918.90 | — | — |
| 3 | `Broker/ESP32/IPFS/results/benchmark_summary_3.csv` | 2026-03-01 20:33:49 | 772 | 76.94% | 450.93 | 533 | 56,482.97 | 88,893.90 | 55,605.30 | 62,254.20 | 52,269.25 | 87,903.50 | 54,930.50 | 58,613.30 |
| 4 | `Broker/ESP32/IPFS/results/benchmark_summary_4.csv` | 2026-03-01 20:41:47 | 119 | 91.60% | 448.18 | 516 | 216,208.58 | 1,137,796.30 | 60,431.80 | 597,412.50 | 245,431.04 | 1,618,677.20 | 60,155.50 | 618,591.90 |
| 5 | `Broker/ESP32/IPFS/results/benchmark_summary_5.csv` | 2026-03-01 20:54:20 | 5,029 | 100.00% | 448.51 | 529 | 57,599.96 | 383,334.70 | 55,252.50 | 66,373.20 | 57,684.23 | 648,736.60 | 55,292.60 | 66,472.40 |

### IPFS Notes
- Pi5 IPFS runs show stable hash/verify timing around ~20 ms / ~36 ms.
- ESP32 pipeline runs #2 and #5 provide long-duration datasets (5,939 and 5,029 chunks respectively); device-side prep remained near ~449 µS across all runs while broker-side Kubo hash/verify dominated latency.
- Run #3 (76.94% success rate) reflects packet loss at the MQTT ingress layer, not a signing or hashing failure.
- Run #4 (119 chunks, 91.60% success) shows extreme broker-side latency spikes (Max Hash: 1,137,796 µS; Max Verify: 1,618,677 µS); P50 values (~60 ms) indicate these are outliers, not representative of steady-state performance.
- Runs #3–#5 include P50/P95/P99 percentile columns in the source CSVs; runs #1–#2 predate that schema and report avg/max only.

---

## System Environment Info (Copied/Confirmed)

The system environment block above was retained as the canonical environment record for:
- Broker/Verifier (Windows 11 laptop)
- Thermometer Device (ESP32)
- Smart Lights Device (Pi3)
- Camera Device (Pi5)

Additional ESP32 flash/run confirmation captured during latest IPFS Arduino deployment:
- Board: `esp32:esp32:esp32`
- Chip: `ESP32-D0WD-V3 (revision v3.1)`
- Upload port: `COM5`
- Flash/upload completed successfully via esptool.

---

## Special Consideration Notes:

There is currently no mature, production-ready IPFS node implementation for ESP32 that can run the full Kubo/libp2p stack (peer discovery, block exchange, datastore, and networking services) directly on-device. This is primarily a hardware and software ecosystem limitation: ESP32 memory, storage, and CPU constraints are not well matched to full IPFS node requirements.

Because of this, the ESP32 was used as a constrained edge publisher, and a broker/gateway host performed true IPFS operations using Kubo (`ipfs add --only-hash`) on the received payload. This preserves real IPFS CID generation while still allowing device-side timing and stress behavior to be measured.

Interpretation note for results:
- ESP32 device timing reflects sensor read + payload construction + MQTT publish overhead.
- IPFS hash/verify timing reflects host-side Kubo and verifier execution, not native ESP32 hashing.
- End-to-end integrity remains valid because CIDs are generated and checked by a real IPFS implementation.
- This architecture should be reported as **ESP32 + IPFS gateway orchestration**, not standalone ESP32-native IPFS.

Additional benchmark caveats (what each applies to):

1) Workload mismatch across IPFS runs
- Concern: ESP32 IPFS payloads are fixed at 25 bytes, while Pi5 IPFS chunks are mostly ~4 KB. Direct latency comparisons are therefore not apples-to-apples.
- Applies to: **cross-platform IPFS comparison** (ESP32 IPFS pipeline vs Pi5 IPFS pipeline), not within-run comparisons on the same device.
- Evidence: `Broker/ESP32/IPFS/results/raw_packet_data_2.csv` and `Broker/Pi5/IPFS/results/raw_packet_data_2.csv`.

2) Outlier sensitivity in ESP32 IPFS hash/verify time
- Concern: ESP32 IPFS run data has extreme max latency spikes (run #2 Max Verify: 716,918.9 µS; run #4 Max Hash: 1,137,796.3 µS, Max Verify: 1,618,677.2 µS; run #5 Max Verify: 648,736.6 µS), so averages alone are highly misleading.
- Applies to: **ESP32 IPFS benchmark interpretation** and any summary table that uses only avg/max metrics.
- Recommendation: use P50/P95 as the primary performance indicators; report avg/max as supplementary range data only.
- Evidence: `Broker/ESP32/IPFS/results/benchmark_summary_2.csv`, `benchmark_summary_4.csv`, `benchmark_summary_5.csv`.

3) Double-hash measurement effect
- Concern: in default validation mode (`double_hash`), `broker_ipfs.py` computes CID once for publish and a second time for verification, which increases host compute cost versus a single-pass pipeline.
- Applies to: **ESP32 -> broker/Kubo IPFS pipeline only** (the host running `Broker/ESP32/IPFS/broker_ipfs.py`, e.g., laptop/Pi broker), not the ESP32 microcontroller itself.
- Note: this can be switched to `single_hash` mode when throughput-focused benchmarking is needed.
- Evidence: `Broker/ESP32/IPFS/broker_ipfs.py`.

4) MQTT reliability mode (mixed QoS path)
- Concern: the ESP32 sender path still uses QoS 0 (possible packet loss without retransmit), while broker republish now uses QoS 1; success rate still reflects received/validated packets, not guaranteed delivery of all generated packets from device origin.
- Applies to: **ESP32 -> broker ingress reliability interpretation** and end-to-end delivery claims.
- Evidence: `ESP32/ipfs/esp32_ipfs/esp32_ipfs.ino` and `Broker/ESP32/IPFS/broker_ipfs.py`.
