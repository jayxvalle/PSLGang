"""
 This is a parser that takes a .mzML file from the mass spectrometers and parsers through
 looking for "" and "" and storing them inside of the "" file for storage. 
"""

"""
The parser is looking for:
 MS Level: 2
 Value: value
"""


import re
import xml.etree.ElementTree as ET
import json
import os
import sys
import matplotlib.pyplot as plt


# Temp path to .mzML file (will prefer a file in the Data/ folder if present)
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(script_dir, ".."))

default_paths = [
    os.path.join(repo_root, "Data", "CVBS_1_Dis_neg_1.mzML"),
    os.path.join(repo_root, "data", "sample.mzML"),
]
if len(sys.argv) > 1:
    mzml_path = sys.argv[1]
else:
    mzml_path = None
    for p in default_paths:
        if os.path.exists(p):
            mzml_path = p
            break
    if mzml_path is None:
        # fallback to repo-root relative path used previously
        mzml_path = os.path.join(repo_root, "data", "sample.mzML")


def parse_mzml(mzml_path):
    if not os.path.exists(mzml_path):
        raise FileNotFoundError(f"mzML file not found: {mzml_path}")
    
    tree = ET.parse(mzml_path)
    root = tree.getroot()

    # Extract default namespace if present
    m = re.match(r"\{(.+)\}", root.tag)
    ns = {"ns": m.group(1)} if m else None

    spectra_data = []

    # Choose the correct find expression depending on whether a namespace was found
    if ns:
        spectrum_iter = root.findall(".//ns:spectrum", ns)
        cvparam_expr = ".//ns:cvParam"
    else:
        spectrum_iter = root.findall(".//spectrum")
        cvparam_expr = ".//cvParam"

    for spectrum in spectrum_iter:
        spec_id = spectrum.get("id")

        # Using a regular expression to extract just the "scan="" part, then fallback to original if no match
        match = re.search(r"(scan=\d+)", spec_id or "")
        spec_id = match.group(1) if match else spec_id

        # Extracting only the value for each measurement to simplify output.
        ms_level = None
        base_peak_mz = None
        base_peak_intensity = None

        for param in spectrum.findall(cvparam_expr, ns if ns else None):
            name = param.get("name")
            value = param.get("value")

            if name == "ms level":
                ms_level = value
            elif name == "base peak m/z":
                base_peak_mz = value
            elif name == "base peak intensity":
                base_peak_intensity = value

        # Only keep spectra where ms level == "1"
        if ms_level == "1":
            spectra_data.append({
                "id": spec_id,
                "ms_level": ms_level,
                "base_peak_mz": base_peak_mz,
                "base_peak_intensity": base_peak_intensity,
            })

    return spectra_data


if __name__ == "__main__":
    try:
        spectra = parse_mzml(mzml_path)

        base_name = os.path.splitext(os.path.basename(mzml_path))[0]
        output_path = os.path.join(os.path.dirname(mzml_path), f"{base_name}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(spectra, f, indent=2)

        print(f"Extracted {len(spectra)} ms-level=1 spectra to {output_path}")
    except Exception as e:
        print(f"Error while parsing mzML: {e}")
        raise