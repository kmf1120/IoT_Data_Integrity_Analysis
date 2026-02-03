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