import json
import matplotlib.pyplot as plt
import numpy as np
import csv
import os

# Constants
CH2_EXACT_MASS = 14.01565
CH2_NOMINAL_MASS = 14

# Locate JSON
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "CVBS_1_Dis_neg_1.json")

# Load JSON file
with open(file_path, "r") as f:
    data = json.load(f)

print("Number of entries in JSON:", len(data))
print("First 3 entries:", data[:3])

# Debug: Count how many entries have numeric base peak values
numeric_base_peak_count = sum(
    1 for entry in data 
    if "base_peak_mz" in entry and entry["base_peak_mz"].replace('.', '', 1).isdigit()
)
print("Number of entries with numeric-like base_peak_mz:", numeric_base_peak_count)
# Prepare lists
mz_values, kmd_values, intensities = [], [], []

# Each entry = one scan point
for entry in data:
    mz = float(entry["base_peak_mz"])
    intensity = float(entry["base_peak_intensity"])

    kendrick_mass = mz * (CH2_NOMINAL_MASS / CH2_EXACT_MASS)
    kmd = round(mz) - kendrick_mass

    mz_values.append(mz)
    kmd_values.append(kmd)
    intensities.append(intensity)

# Convert to numpy arrays for faster math
mz_values = np.array(mz_values)
kmd_values = np.array(kmd_values)
intensities = np.array(intensities)

# Apply log transform for visualization
log_intensity = np.log(np.maximum(intensities, 1))

# Plot
plt.figure(figsize=(9, 6), dpi=100)
sc = plt.scatter(mz_values, kmd_values, c=log_intensity, s=15, alpha=0.7, cmap="jet")
plt.grid(True, linestyle="--", linewidth=0.3, alpha=0.5)
plt.xlabel("Ion Mass (m/z)")
plt.ylabel("Kendrick Mass Defect (KMD)")
plt.title("KMD Signal-to-Noise Determination Heatmap")
cb = plt.colorbar(sc)
cb.set_label("ln(Intensity)")
plt.xlim(np.min(mz_values), np.max(mz_values))
plt.ylim(np.min(kmd_values), np.max(kmd_values))
plt.tight_layout()
plt.show()

# Export CSV
def export_to_csv(output_path):
    with open(output_path, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["scan", "mz", "kmd", "intensity"])
        for i, (mz, kmd, intensity) in enumerate(zip(mz_values, kmd_values, intensities), start=1):
            writer.writerow([i, mz, kmd, intensity])
    print(f"✅ Exported {len(mz_values)} points to {output_path}")

# export_to_csv(os.path.join(script_dir, "kmd_results.csv"))