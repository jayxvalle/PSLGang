"""
 This is a parser that takes a .mzML file from the mass spectrometers and parsers through
 looking for "" and "" and storing them inside of the "" file for storage. 
"""

"""
The parser is looking for:
 MS Level: 2
 Value: value
"""


import xml.etree.ElementTree as ET
import json
import os

#Temp path to .mzML file
mzml_path = "data/sample.mzML"

#Parsing the XML file
tree = ET.parse(mzml_path)
root = tree.getroot()

#Handle XML namespace
#ns = {"mzml" : }

#collect spectrum data
spectra_data = []

