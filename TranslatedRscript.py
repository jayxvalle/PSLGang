"""
kmd_noise.py

Python translation of the R function `KMDNoise` for estimating signal-to-noise
from a single mass spectrum using Kendrick Mass Defect (KMD) boundaries.

Author: (translated for team example)
Dependencies: pandas, numpy, matplotlib

Usage example:
    import pandas as pd
    df = pd.read_csv("spectrum.csv")  # columns: mass, intensity
    result = kmd_noise(df)
    print(result["Noise"])
    fig = result["Figure"]   # matplotlib.figure.Figure

This file exposes one function: kmd_noise(...)
"""

from typing import Optional, Dict, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import warnings


def kmd_noise(
    df: pd.DataFrame,
    upper_y: float = 0.2,
    lower_y: float = 0.05,
    upper_x: Optional[float] = None,
    lower_x: Optional[float] = None,
    slope: float = 0.0011232,
) -> Dict[str, Any]:
    """
    Estimate noise level from a single mass spectrum using KMD boundaries.

    Preconditions
    -------------
    - `df` is a pandas.DataFrame with at least two columns:
        * first column: ion mass (float)
        * second column: intensity (float, strictly positive preferred)
      Column names do not matter (function will expect mass in df.columns[0] and
      intensity in df.columns[1]) but it's convenient to pass a DataFrame with
      columns named ['mass', 'intensity'].
    - intensities should be strictly positive for log-transform. Non-positive
      intensities will be dropped from calculations.

    Parameters
    ----------
    df : pandas.DataFrame
        Spectrum table where column 0 is mass and column 1 is intensity.
    upper_y : float, default 0.2
        Y-intercept for the upper KMD boundary (red line).
    lower_y : float, default 0.05
        Y-intercept for the lower KMD boundary (red line).
    upper_x : Optional[float], default None
        Upper x (mass) limit for the noise-selection window. If None uses
        max(mass) from data.
    lower_x : Optional[float], default None
        Lower x (mass) limit for the noise-selection window. If None uses
        min(mass) from data.
    slope : float, default 0.0011232
        Slope used for the bounding lines in the KMD plot (kept same as R).

    Returns
    -------
    dict
        {
            "Noise": float or np.nan,   # geometric mean of intensities in the selected noise region
            "Figure": matplotlib.figure.Figure  # the generated KMD plot with boundaries
        }

    Postconditions
    --------------
    - Returns a dictionary with the noise estimate (geometric mean) and a
      matplotlib Figure object showing:
        * points: mass (x) vs KMD (y) colored by ln(intensity)
        * red boundary lines (upper and lower)
        * vertical red lines at lower_x and upper_x
    - If no peaks fall into the noise selection region, Noise is np.nan and a
      warning is issued.

    Time Complexity
    ---------------
    Let n = number of rows in df.
        - Creating derived columns: O(n)
        - Filtering and averaging: O(n)
        - Plotting: O(n) (matplotlib scatter)
    Overall: O(n) time, O(n) additional memory for intermediate columns.

    Notes
    -----
    - This function intentionally mirrors the R implementation: it computes
      KMD = round(mass) - (mass * (14 / 14.01565)), logs intensities and uses
      the mean of the log(intensity) in the selected KMD window, then exponentiates
      that mean back to intensity-space (geometric mean).
    - If your intensities are zero or negative, consider adding a small offset
      before using this function, or clean your data first.
    """

    # --- Defensive copy & basic checks ------------------------------------
    if df.shape[1] < 2:
        raise ValueError("Input DataFrame must have at least two columns: mass and intensity")

    data = df.copy().reset_index(drop=True)
    mass_col = data.columns[0]
    intensity_col = data.columns[1]
    data = data.rename(columns={mass_col: "mass", intensity_col: "intensity"})

    # Drop rows with NaN mass
    data = data.dropna(subset=["mass"])

    # Default x-bounds if not provided
    if upper_x is None:
        upper_x = float(data["mass"].max())
    if lower_x is None:
        lower_x = float(data["mass"].min())

    # --- KMD calculations -------------------------------------------------
    # Kendrick mass scaling used in the R original
    data["KM"] = data["mass"] * (14.0 / 14.01565)
    data["NM"] = np.round(data["mass"])
    data["KMD"] = data["NM"] - data["KM"]

    # log intensity (natural log). For non-positive intensities, set to NaN so they
    # are excluded from mean/log operations just like R would produce -Inf.
    # But we'll drop -Inf values when computing means.
    # Keep original intensities for any further needs.
    # Convert to float to prevent integer division surprises.
    data["intensity"] = pd.to_numeric(data["intensity"], errors="coerce").astype(float)
    data.loc[data["intensity"] <= 0, "ln_int"] = np.nan
    data.loc[data["intensity"] > 0, "ln_int"] = np.log(data.loc[data["intensity"] > 0, "intensity"])

    # Limit unrealistic ln_int values (mimic R's later filter df <- df[df$int > -100 & df$int < 100,])
    # Keep the same bounds: remove absurd logs outside (-100, 100)
    data = data[(data["ln_int"].isna()) | ((data["ln_int"] > -100) & (data["ln_int"] < 100))].copy()

    # --- Build limits (for plotting aesthetics) ---------------------------
    # Create a Limits dataframe similar to R for plotting boundary lines over sensible mass range
    num_min = int(np.floor(data["mass"].min() / 12.0))
    num_max = int(np.ceil(data["mass"].max() / 12.0))
    Numbers = np.arange(num_min, num_max + 1)
    Limits = pd.DataFrame({"Number": Numbers})
    Limits["mass"] = Limits["Number"] * 12.0
    Limits["KMD_low"] = slope * Limits["mass"] + lower_y
    Limits["KMD_up"] = slope * Limits["mass"] + upper_y

    # --- Select points inside noise window and within x-bounds ----------------
    mask_sn = (
        (data["KMD"] > (slope * data["mass"] + lower_y))
        & (data["KMD"] < (slope * data["mass"] + upper_y))
        & (data["mass"] >= lower_x)
        & (data["mass"] <= upper_x)
    )
    SN = data.loc[mask_sn, :]

    # Compute noise as exp(mean(ln_intensity)) -> geometric mean of intensity values
    if SN["ln_int"].dropna().size == 0:
        Noise = np.nan
        warnings.warn(
            "No peaks found in the selected KMD noise window. Returning Noise=np.nan.", UserWarning
        )
    else:
        mean_ln = SN["ln_int"].dropna().mean()
        Noise = float(np.exp(mean_ln))

    # --- Generate plot (matplotlib) --------------------------------------
    # Color by ln(intensity). We'll set the color limits using min/max ln_int in the filtered (display) data.
    fig, ax = plt.subplots(figsize=(10, 6))

    # Prepare scatter: use ln_int as color; points with NaN ln_int will be plotted faint gray.
    # For numeric color mapping, replace NaN with some sentinel; but we'll plot NaNs separately.
    plot_df = data.copy()
    cmap = plt.get_cmap("RdYlBu_r")  # blue->red-ish diverging (no explicit color choice requirement)
    vmin = np.nanmin(plot_df["ln_int"].values)
    vmax = np.nanmax(plot_df["ln_int"].values)

    # Points with ln_int not NaN
    has_ln = plot_df["ln_int"].notna()
    sc = ax.scatter(
        plot_df.loc[has_ln, "mass"],
        plot_df.loc[has_ln, "KMD"],
        c=plot_df.loc[has_ln, "ln_int"],
        cmap=cmap,
        s=10,
        alpha=0.6,
        vmin=vmin,
        vmax=vmax,
        edgecolors="none",
    )

    # Points w/out ln_int (zero/negative intensity) as very faint gray (if any)
    if (~has_ln).any():
        ax.scatter(
            plot_df.loc[~has_ln, "mass"],
            plot_df.loc[~has_ln, "KMD"],
            c="lightgray",
            s=8,
            alpha=0.5,
            label="non-positive intensity",
        )

    # Add the two boundary lines: y = slope * x + intercept
    x_vals = np.linspace(plot_df["mass"].min(), plot_df["mass"].max(), 200)
    ax.plot(x_vals, slope * x_vals + lower_y, color="red", linewidth=1.5)
    ax.plot(x_vals, slope * x_vals + upper_y, color="red", linewidth=1.5)

    # Vertical x-bounds
    ax.axvline(lower_x, color="red", linewidth=1.2)
    ax.axvline(upper_x, color="red", linewidth=1.2)

    # Colorbar for ln(int)
    if np.isfinite(vmin) and np.isfinite(vmax):
        cbar = fig.colorbar(sc, ax=ax)
        cbar.set_label("ln(intensity)", fontsize=12)

    # Labels and theme roughly matching the R ggplot theme_bw + bold text
    ax.set_xlabel("Ion Mass", fontsize=14, fontweight="bold")
    ax.set_ylabel("Kendrick Mass Defect", fontsize=14, fontweight="bold")
    ax.set_title("KMD Signal to Noise Determination Plot", fontsize=16, fontweight="bold")
    ax.tick_params(axis="both", labelsize=12)
    ax.grid(True, linestyle="--", alpha=0.2)

    plt.tight_layout()

    # --- Return results ---------------------------------------------------
    return {"Noise": Noise, "Figure": fig}





 # --- How to connect to parser 

from parser import parse_mzml      # your existing parser function
from kmd_noise import kmd_noise    # the KMD noise estimation function
import pandas as pd

# Path to your mzML file (the same way Parser.py resolves it)
mzml_path = "data/sample.mzML"

# Step 1: Parse the mzML file to extract MS level 1 peaks
spectra = parse_mzml(mzml_path)

# Step 2: Convert the list of dictionaries into a DataFrame
df = pd.DataFrame(spectra)

# Step 3: Convert types to numeric (the parser returns strings)
df["mass"] = pd.to_numeric(df["base_peak_mz"], errors="coerce")
df["intensity"] = pd.to_numeric(df["base_peak_intensity"], errors="coerce")

# Step 4: Apply the KMD-based noise estimation
result = kmd_noise(df)

# Step 5: Output the result
print(f"Estimated noise level: {result['Noise']:.4f}")
result["Figure"].savefig("KMD_NoisePlot.png", dpi=300)




