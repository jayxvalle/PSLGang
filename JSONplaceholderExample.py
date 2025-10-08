import json
import os

# Example placeholder spectra data from parser
# (In your parser, you'd actually collect MS level, value, etc.)
spectra_data = [
    {"ms_level": 2, "value": 12345.6, "scan_id": 1},
    {"ms_level": 2, "value": 9876.5, "scan_id": 2}
]

# Where to store JSON
output_path = "parsed_spectra.json"

# Write to JSON
with open(output_path, "w") as f:
    json.dump(spectra_data, f, indent=2)

print(f"Saved {len(spectra_data)} spectra records to {output_path}")
