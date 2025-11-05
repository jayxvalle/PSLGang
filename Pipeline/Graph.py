import argparse
import json
import matplotlib.pyplot as plt
import numpy as np
import csv
import os
import math
from typing import Optional, List


# Constants (CH2 repeat unit)
CH2_EXACT_MASS = 14.01565
CH2_NOMINAL_MASS = 14.0


def safe_float(val: Optional[object]) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        try:
            return float(str(val).replace(",", ""))
        except Exception:
            return None


def kendrick_mass(mz: float, repeat_nominal: float = CH2_NOMINAL_MASS, repeat_exact: float = CH2_EXACT_MASS) -> float:
    return mz * (repeat_nominal / repeat_exact)


def kmd_fractional(mz: float) -> float:
    km = kendrick_mass(mz)
    return km - math.floor(km)


def kmd_round(mz: float) -> float:
    km = kendrick_mass(mz)
    return round(km) - km


def load_json(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def augment_and_compute(data: list) -> list:
    """
    Compute Kendrick mass defect for all MS1 spectra using full arrays if available.
    """
    filtered = [rec for rec in data if rec.get("ms_level") == "1"]

    for rec in filtered:
        mz_array = rec.get("m_z_array")
        intensity_array = rec.get("intensity_array")

        if mz_array and intensity_array:
            # Compute Kendrick mass and defects for every point
            rec["kendrick_mz"] = [kendrick_mass(mz) for mz in mz_array]
            rec["kendrick_fraction"] = [kmd_fractional(mz) for mz in mz_array]
            rec["kendrick_round"] = [kmd_round(mz) for mz in mz_array]
        else:
            # fallback to base peak if arrays are missing
            mz = safe_float(rec.get("base_peak_mz"))
            rec["kendrick_mz"] = [kendrick_mass(mz)] if mz else []
            rec["kendrick_fraction"] = [kmd_fractional(mz)] if mz else []
            rec["kendrick_round"] = [kmd_round(mz)] if mz else []

    print(f"Filtered {len(filtered)} MS1 spectra for plotting")
    return filtered


def plot_data(data: list, method: str = "round",
              lower_y: float = 0.05, upper_y: float = 0.2,
              lower_x: Optional[float] = None, upper_x: Optional[float] = None,
              max_points: Optional[int] = 50000) -> dict:

    x, y, c = [], [], []

    # flatten all scans
    for rec in data:
        mz_array = rec.get("m_z_array")
        intensity_array = rec.get("intensity_array")
        if mz_array and intensity_array:
            y_vals = rec["kendrick_fraction"] if method == "fractional" else rec["kendrick_round"]
            x.extend(mz_array)
            y.extend(y_vals)
            c.extend(intensity_array)

    if not x:
        print("No data to plot.")
        return {"Noise": None, "Figure": None}

    x = np.array(x)
    y = np.array(y)
    c = np.array(c)
    log_c = np.log(np.maximum(c, 1.0))

    # Set x limits if not given
    lower_x = np.min(x) if lower_x is None else lower_x
    upper_x = np.max(x) if upper_x is None else upper_x

    # Computed noise region (it's computed, just not drawn) -- line 120-126
    noise_mask = (y > 0.0011232*x + lower_y) & (y < 0.0011232*x + upper_y) & (x >= lower_x) & (x <= upper_x)
    noise_values = log_c[noise_mask]
    noise_level = float(np.exp(np.mean(noise_values))) if len(noise_values) > 0 else None

    # Optionally downsample points for plotting
    if max_points and len(x) > max_points:
        idx = np.random.choice(len(x), max_points, replace=False)
        x_plot, y_plot, c_plot = x[idx], y[idx], log_c[idx]
    else:
        x_plot, y_plot, c_plot = x, y, log_c

    # Plotting
    fig, ax = plt.subplots(figsize=(10, 8))
    scatter = plt.scatter(x_plot, y_plot, c=c_plot, cmap="viridis", s=3, alpha=0.7)
    plt.colorbar(scatter, label="ln(intensity)")
    
    # # Noise region lines
    # ax.plot([lower_x, upper_x], [0.0011232*lower_x + lower_y, 0.0011232*upper_x + lower_y],
    #         color='red', lw=1)
    # ax.plot([lower_x, upper_x], [0.0011232*lower_x + upper_y, 0.0011232*upper_x + upper_y],
    #         color='red', lw=1)
    # ax.axvline(lower_x, color='red', lw=1)
    # ax.axvline(upper_x, color='red', lw=1)

    plt.xlabel("Ion Mass (m/z)")
    plt.ylabel(f"Kendrick Mass Defect ({method})")
    plt.title("KMD Signal to Noise Determination Plot (MS1 spectra)")
    plt.grid(True, linestyle="--", linewidth=0.3, alpha=0.5)
    plt.tight_layout()
    plt.show()

    # return {"Noise": noise_level, "Figure": fig}

def export_to_csv(data: List[dict], outpath: str) -> None:
    with open(outpath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id", "mz", "kendrick_mass", "kmd_fraction", "kmd_round", "intensity"])
        for rec in data:
            mz = safe_float(rec.get("base_peak_mz") or rec.get("mz"))
            writer.writerow([
                rec.get("id"),
                mz,
                rec.get("kendrick_mass"),
                rec.get("kendrick_mass_defect_fraction"),
                rec.get("kendrick_mass_defect_round"),
                rec.get("base_peak_intensity"),
            ])
    print(f"Exported CSV to {outpath}")


def main():
    ap = argparse.ArgumentParser(description="Compute KMD for parser JSON and plot results")
    ap.add_argument("json_path", nargs="?", help="Path to JSON file", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "CVBS_1_Dis_neg_1.json"))
    ap.add_argument("--augment", action="store_true", help="Overwrite JSON adding kmd fields")
    ap.add_argument("--method", choices=["fractional", "round"], default="round", help="Which KMD variant to plot (default: round)")
    ap.add_argument("--csv", help="Optional path to export CSV summary")
    args = ap.parse_args()

    if not os.path.exists(args.json_path):
        print(f"JSON file not found: {args.json_path}")
        raise SystemExit(1)

    data = load_json(args.json_path)
    data = augment_and_compute(data)

    if args.augment:
        # write augmented JSON (backup original)
        bak = args.json_path + ".bak"
        try:
            os.replace(args.json_path, bak)
            print(f"Backed up original to {bak}")
        except Exception:
            bak = None
        with open(args.json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    if args.csv:
        export_to_csv(data, args.csv)

    plot_data(data, method=args.method)


if __name__ == "__main__":
    main()