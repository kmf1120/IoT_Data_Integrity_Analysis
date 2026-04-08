"""Generate poster-ready bar charts (avg across stress levels, min/max error bars).
Target poster area: 16.24 in tall x 13.32 in wide.
  DLS        13.32 x 3.50
  IPFS       13.32 x 3.50
  Blockchain 13.32 x 3.50
  CBHV       13.32 x 5.74
  Total height ≈ 16.24 in
"""

import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os

matplotlib.use("Agg")
plt.rcParams.update({
    "font.size": 18,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "xtick.labelsize": 18,
    "ytick.labelsize": 16,
    "legend.fontsize": 16,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "charts")
os.makedirs(OUTPUT_DIR, exist_ok=True)

devices = ["ESP32", "Pi3B+", "Pi5"]
colors = ["#4C72B0", "#55A868", "#C44E52"]
DPI = 300

def plot_bars(ax, data, title):
    """Plot one bar per device with min/max error bars."""
    x = np.arange(len(devices))
    width = 0.5
    for i, dev in enumerate(devices):
        vals = np.array(data[dev])
        avg = vals.mean()
        lo = avg - vals.min()
        hi = vals.max() - avg
        ax.bar(x[i], avg, width, color=colors[i],
               yerr=[[lo], [hi]], capsize=8, error_kw={"linewidth": 2})
    ax.set_ylabel("Time (μs)")
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(devices)

# ── Chart sizing ──
W = 13.32
H_SMALL = 2.80   # 1×2 subplots
H_LARGE = 4.59   # 2×2 subplots

# ── Table 1: Device-Level Signing ──
sign_times = {
    "ESP32":  [46284.49, 46283.79, 46284.46, 46283.34],
    "Pi3B+":  [474.94, 327.10, 305.44, 349.35],
    "Pi5":    [165.53, 139.97, 149.95, 173.04],
}
verify_times = {
    "ESP32":  [221.86, 213.71, 224.83, 200.95],
    "Pi3B+":  [229.71, 224.16, 225.62, 234.95],
    "Pi5":    [309.94, 293.77, 282.89, 286.30],
}
fig, axes = plt.subplots(1, 2, figsize=(W, H_SMALL))
plot_bars(axes[0], sign_times, "Sign Time (μs)")
plot_bars(axes[1], verify_times, "Verify Time (μs)")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "device_level_signing.png"), dpi=DPI)
plt.close()

# ── Table 2: IPFS ──
ipfs_sign = {
    "ESP32":  [55801.28, 56000.33, 55846.72, 56441.69],
    "Pi3B+":  [151696.28, 171711.30, 217979.31, 312606.20],
    "Pi5":    [41028.91, 43186.04, 50659.78, 67410.98],
}
ipfs_verify = {
    "ESP32":  [55739.74, 55825.88, 55964.37, 56464.96],
    "Pi3B+":  [57641.43, 57633.71, 60819.18, 66310.45],
    "Pi5":    [56720.36, 56793.89, 56586.69, 56757.51],
}
fig, axes = plt.subplots(1, 2, figsize=(W, H_SMALL))
plot_bars(axes[0], ipfs_sign, "Hash Time (μs)")
plot_bars(axes[1], ipfs_verify, "Verify Time (μs)")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "ipfs.png"), dpi=DPI)
plt.close()

# ── Table 3: CBHV ──
cbhv_sign = {
    "ESP32":  [108.90, 110.76, 114.20, 110.19],
    "Pi3B+":  [55.85, 55.87, 59.30, 62.78],
    "Pi5":    [38.92, 57.82, 40.01, 34.58],
}
cbhv_verify = {
    "ESP32":  [9.19, 7.54, 8.28, 8.28],
    "Pi3B+":  [8.25, 9.17, 9.34, 9.33],
    "Pi5":    [12.15, 11.33, 11.23, 10.83],
}
cbhv_upload = {
    "ESP32":  [657293.87, 688852.25, 654455.20, 625925.04],
    "Pi3B+":  [306299.37, 309788.72, 302502.34, 362875.63],
    "Pi5":    [194542.71, 185595.14, 182026.13, 186856.30],
}
cbhv_fetch = {
    "ESP32":  [597101.32, 606731.97, 603936.42, 603971.66],
    "Pi3B+":  [587717.93, 616538.70, 604580.05, 605366.96],
    "Pi5":    [605297.30, 608261.73, 603277.78, 607351.62],
}
fig, axes = plt.subplots(2, 2, figsize=(W, H_LARGE))
plot_bars(axes[0, 0], cbhv_sign, "Hash Time (μs)")
plot_bars(axes[0, 1], cbhv_verify, "Verify Time (μs)")
plot_bars(axes[1, 0], cbhv_upload, "Upload Time (μs)")
plot_bars(axes[1, 1], cbhv_fetch, "Fetch Time (μs)")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "cbhv.png"), dpi=DPI)
plt.close()

# ── Table 4: Blockchain ──
bc_sign = {
    "ESP32":  [62.72, 63.91, 64.75, 64.07],
    "Pi3B+":  [59.93, 48.71, 52.90, 56.67],
    "Pi5":    [25.66, 23.35, 29.83, 33.95],
}
bc_verify = {
    "ESP32":  [8.77, 8.15, 8.19, 7.93],
    "Pi3B+":  [19.62, 18.83, 19.07, 19.06],
    "Pi5":    [30.49, 29.29, 29.65, 30.24],
}
fig, axes = plt.subplots(1, 2, figsize=(W, H_SMALL))
plot_bars(axes[0], bc_sign, "Hash Time (μs)")
plot_bars(axes[1], bc_verify, "Verify Time (μs)")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "blockchain.png"), dpi=DPI)
plt.close()

print("Charts saved to:", OUTPUT_DIR)
for f in sorted(os.listdir(OUTPUT_DIR)):
    print(f"  {f}")
