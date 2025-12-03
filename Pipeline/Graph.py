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
    # # shift to allow negative values (center around 0)
    # return frac if frac < 1 else frac - 1


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
    lower_x: Optional[float] = None, upper_x: Optional[float] = None,
    max_points: Optional[int] = 100000, band_margin: float = 0.05) -> dict: #Change max_points to 'None' to disable downsampling

    """Compute and plot Kendrick Mass Defect (KMD) points inside a dynamic band.

    Parameters
    - data: list of spectra (dictionaries) produced by the parser
    - method: 'round' or 'fractional' KMD variant
    - lower_x/upper_x: optional x-range bounds; default to data min/max
    - max_points: optional downsampling threshold for plotting
    - band_margin: small vertical margin added to the computed band per chunk

    Returns a dict with keys: 'Noise' (computed noise level) and 'Figure' (matplotlib Figure)
    """

    # Flatten spectra arrays into point lists
    # We collect all m/z, corresponding KMD y-values, and intensities into x, y, c arrays.
    x, y, c = [], [], []

    # Flatten all scans
    for rec in data:
        mz_array = rec.get("m_z_array")
        intensity_array = rec.get("intensity_array")
        if mz_array and intensity_array:
            # choose y-values according to requested method
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
    log_c = np.log(np.maximum(c, 1.0))  # use for coloring

    # Determine x-range for band computation
    lower_x = np.min(x) if lower_x is None else lower_x
    upper_x = np.max(x) if upper_x is None else upper_x

    # Compute a dynamic KMD band across x:
    # We compute local min/max y-values per x-window and shift them by the diagonal slope
    # to form a slanted band that follows the data distribution.
    slope = 0.0011232 # defines the diagonal tilt of the band
    sorted_idx = np.argsort(x)
    x_sorted = x[sorted_idx]
    y_sorted = y[sorted_idx]

    window_size = max(1, len(x_sorted)//100) # divides the x-axis into segments to compute a smooth envelope
    x_band, y_low, y_high = [], [], []
    for i in range(0, len(x_sorted), window_size):
        x_chunk = x_sorted[i:i+window_size]
        y_chunk = y_sorted[i:i+window_size]
        if len(x_chunk) == 0:
            continue
        x_mean = np.mean(x_chunk)
        x_band.append(x_mean)
        # expand local min/max by the slope*position and a small margin
        y_low.append(np.min(y_chunk) + slope * x_mean - band_margin)
        y_high.append(np.max(y_chunk) + slope * x_mean + band_margin)

    x_band = np.array(x_band)
    y_low = np.array(y_low)
    y_high = np.array(y_high)

    # extend the band arrays so they cover the entire [lower_x, upper_x] interval
    x_band = np.concatenate([[lower_x], x_band, [upper_x]])
    y_low = np.concatenate([[y_low[0]], y_low, [y_low[-1]]])
    y_high = np.concatenate([[y_high[0]], y_high, [y_high[-1]]])

    # Vertical tiling and filtering
    # The band can be located above the base KMD range (>1). To include points
    # that match the band after shifting by integer Kendrick repeats, we tile the y-values
    # vertically by integer offsets and then apply the band mask to the tiled coordinates.
    from numpy import interp
    tile_range = np.arange(-6, 7)  # vertical offsets; adjust for more/less repetition
    x_tiles = np.tile(x, len(tile_range))
    y_tiles = np.concatenate([y + k for k in tile_range])
    c_tiles = np.tile(c, len(tile_range))

    band_lower_tiles = interp(x_tiles, x_band, y_low)
    band_upper_tiles = interp(x_tiles, x_band, y_high)

    inside_mask = (
        (y_tiles >= band_lower_tiles)
        & (y_tiles <= band_upper_tiles)
        & (x_tiles >= lower_x)
        & (x_tiles <= upper_x)
    )

    x_plot = x_tiles[inside_mask]
    y_plot = y_tiles[inside_mask]
    c_plot = np.log(np.maximum(c_tiles[inside_mask], 1.0))

    if len(x_plot) == 0:
        return {"Noise": None, "Figure": None}

    # downsampling to keep the plots responsive
    if max_points and len(x_plot) > max_points:
        idx = np.random.choice(len(x_plot), max_points, replace=False)
        x_plot, y_plot, c_plot = x_plot[idx], y_plot[idx], c_plot[idx]

    # Compute noise from points inside the band
    noise_level = float(np.exp(np.mean(c_plot))) if len(c_plot) > 0 else None

    # Plotting
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.fill_between(
        x_band,
        y_low,
        y_high,
        color='lightblue',
        alpha=0.3,
        label='KMD range',
        zorder=1
    )

    # Scatter points only inside band
    ax.scatter(
        x_plot,
        y_plot,
        c=c_plot,
        cmap="viridis",
        s=3,
        alpha=0.7,
        zorder=2
    )
    # attach colorbar
    plt.colorbar(ax.collections[1], ax=ax, label="ln(intensity)")

    # --- Overlay base peaks inside the band ---
    try:
        bp_x, bp_y, bp_c = [], [], []
        for rec in data:
            mz_bp = safe_float(rec.get("base_peak_mz") or rec.get("mz"))
            inten_bp = safe_float(rec.get("base_peak_intensity") or rec.get("intensity"))
            if mz_bp is None:
                continue
            y_bp = kmd_fractional(mz_bp) if method == "fractional" else kmd_round(mz_bp)
            lower_bp = np.interp(mz_bp, x_band, y_low)
            upper_bp = np.interp(mz_bp, x_band, y_high)
            if lower_bp <= y_bp <= upper_bp:
                bp_x.append(mz_bp)
                bp_y.append(y_bp)
                bp_c.append(inten_bp or 0.0)

        if bp_x:
            bp_x = np.array(bp_x)
            bp_y = np.array(bp_y)
            bp_c = np.log(np.maximum(np.array(bp_c), 1.0))
            ax.scatter(
                bp_x,
                bp_y,
                c=bp_c,
                cmap="viridis",
                s=30,
                edgecolors="black",
                linewidths=0.6,
                alpha=0.5,
                zorder=10,
                label="Base peaks",
            )
            ax.legend(loc="upper right")
    except Exception:
        # do not fail the whole plotting routine just because base-peak overlay failed
        pass

    # Adjust y-limits to include band and base peaks
    all_y = np.concatenate([y_plot, y_low, y_high])
    if 'bp_y' in locals():
        all_y = np.concatenate([all_y, bp_y])
    y_min, y_max = np.min(all_y), np.max(all_y)
    y_padding = 0.05 * (y_max - y_min)
    ax.set_ylim(y_min - y_padding, y_max + y_padding)

    # Grid behind everything
    ax.grid(True, linestyle="--", linewidth=0.3, alpha=0.5, zorder=0)
    ax.set_xlabel("Ion Mass (m/z)")
    ax.set_ylabel(f"Kendrick Mass Defect ({method})")
    ax.set_title("KMD Signal to Noise Determination Plot (MS1 spectra)")
    plt.tight_layout()

    return {"Noise": noise_level, "Figure": fig}



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