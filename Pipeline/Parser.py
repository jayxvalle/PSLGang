"""
mzML Parser for full MS1 spectra
- Extracts base peak info AND full m/z/intensity arrays
- Saves JSON suitable for plotting in your GUI
"""

import os
import sys
import re
import json
import base64
import zlib
import numpy as np
import xml.etree.ElementTree as ET
from decimal import Decimal

# -------------------------------------------------------------------
# File path setup
# -------------------------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(script_dir, ".."))

default_paths = [
    os.path.join(repo_root, "Data", "CVBS_1_Dis_neg_1.mzML"),
    os.path.join(repo_root, "data", "sample.mzML"),
]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        mzml_path = sys.argv[1]
    else:
        mzml_path = next((p for p in default_paths if os.path.exists(p)), None)
        if mzml_path is None:
            raise SystemExit("No .mzML file specified or found in Data/ directory.")

# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def fmt_num_str(s):
    """Convert numeric strings to plain decimal strings for JSON."""
    if s is None:
        return None
    try:
        d = Decimal(str(s))
        return format(d, "f")
    except Exception:
        return s


def decode_binary_array(binary_elem, ns):
    """
    Decode a <binaryDataArray> element into a NumPy array.
    Returns (name, data_array)
    """
    dtype = np.float64
    compressed = False
    array_name = "unknown"

    for cv in binary_elem.findall("ns:cvParam", ns):
        name = cv.attrib.get("name", "").lower()
        if "32-bit float" in name:
            dtype = np.float32
        if "64-bit float" in name:
            dtype = np.float64
        if "zlib compression" in name:
            compressed = True
        if "intensity array" in name or "m/z array" in name:
            array_name = cv.attrib.get("name")

    encoded_text = binary_elem.find("ns:binary", ns).text
    decoded = base64.b64decode(encoded_text)
    if compressed:
        decoded = zlib.decompress(decoded)

    data = np.frombuffer(decoded, dtype=dtype)
    return array_name, data


# -------------------------------------------------------------------
# Main parser
# -------------------------------------------------------------------
def parse_mzml_full_spectra(mzml_path):
    """Parse mzML file and extract full MS1 spectra."""
    if not os.path.exists(mzml_path):
        raise FileNotFoundError(mzml_path)

    tree = ET.parse(mzml_path)
    root = tree.getroot()
    m = re.match(r"\{(.+)\}", root.tag)
    ns = {"ns": m.group(1)} if m else None

    spectra_data = []

    spectrum_iter = root.findall(".//ns:spectrum", ns) if ns else root.findall(".//spectrum")
    cvparam_expr = ".//ns:cvParam" if ns else ".//cvParam"

    for spectrum in spectrum_iter:
        spec_id = spectrum.get("id")
        match = re.search(r"(scan=\d+)", spec_id or "")
        spec_id = match.group(1) if match else spec_id

        ms_level = base_peak_mz = base_peak_intensity = None
        for param in spectrum.findall(cvparam_expr, ns):
            name = param.get("name")
            value = param.get("value")
            if name == "ms level":
                ms_level = value
            elif name == "base peak m/z":
                base_peak_mz = value
            elif name == "base peak intensity":
                base_peak_intensity = value

        if ms_level != "1":
            continue  # only MS1

        spectrum_info = {
            "id": spec_id,
            "ms_level": ms_level,
            "base_peak_mz": fmt_num_str(base_peak_mz),
            "base_peak_intensity": fmt_num_str(base_peak_intensity),
        }

        # Extract full binary arrays
        m_z_array = None
        intensity_array = None
        for binary_elem in spectrum.findall(".//ns:binaryDataArray", ns):
            try:
                name, data = decode_binary_array(binary_elem, ns)
                if "m/z" in name.lower():
                    m_z_array = data.tolist()
                elif "intensity" in name.lower():
                    intensity_array = data.tolist()
            except Exception as e:
                spectrum_info["binary_error"] = str(e)

        spectrum_info["m_z_array"] = m_z_array
        spectrum_info["intensity_array"] = intensity_array

        spectra_data.append(spectrum_info)

    return spectra_data