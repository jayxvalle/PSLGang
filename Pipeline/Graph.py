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


def augment_and_compute(data: List[dict], augment: bool = False) -> List[dict]:
    counts_by_ms = {}
    for rec in data:
        ms_level = rec.get("ms_level")
        counts_by_ms[ms_level] = counts_by_ms.get(ms_level, 0) + 1

        mz = safe_float(rec.get("base_peak_mz") or rec.get("mz"))
        intensity = safe_float(rec.get("base_peak_intensity"))
        if mz is None:
            rec["kendrick_mass"] = None
            rec["kendrick_mass_defect_fraction"] = None
            rec["kendrick_mass_defect_round"] = None
            continue

        km = kendrick_mass(mz)
        rec["kendrick_mass"] = km
        rec["kendrick_mass_defect_fraction"] = kmd_fractional(mz)
        rec["kendrick_mass_defect_round"] = kmd_round(mz)

    print("Counts by ms_level:")
    for k, v in counts_by_ms.items():
        print(f"  ms_level={k}: {v} records")

    return data


def plot_data(data: List[dict], method: str = "fractional") -> None:
    x = []
    y = []
    c = []
    for rec in data:
        mz = safe_float(rec.get("base_peak_mz") or rec.get("mz"))
        if mz is None:
            continue
        x.append(mz)
        if method == "fractional":
            y.append(rec.get("kendrick_mass_defect_fraction"))
        else:
            y.append(rec.get("kendrick_mass_defect_round"))
        c.append(safe_float(rec.get("base_peak_intensity")) or 0.0)

    if not x:
        print("No data to plot.")
        return

    x = np.array(x)
    y = np.array(y)
    c = np.array(c)

    log_c = np.log(np.maximum(c, 1.0))

    plt.figure(figsize=(10, 6))
    
    # Added a temporary random jitter to x and y to help see stacked points
    x_jittered = x + np.random.normal(0, 2, size=len(x))
    y_jittered = y + np.random.normal(0, 2, size=len(y))
    scatter = plt.scatter(x_jittered, y_jittered, c=log_c, cmap="viridis", s=3, alpha=0.7)

    plt.xlabel("Ion Mass (m/z)")
    plt.ylabel("Kendrick Mass Defect ({})".format(method))
    plt.title("Kendrick Mass Defect plot")
    cb = plt.colorbar(scatter)
    cb.set_label("ln(intensity)")
    plt.grid(True, linestyle="--", linewidth=0.3, alpha=0.5)
    plt.tight_layout()
    plt.show()


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
    data = augment_and_compute(data, augment=args.augment)

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