# SCOBI Local Metadata System - How Your PI Designed It

## Overview

Your PI designed a **CSV-based metadata tracking system** separate from ODR. The core is a master CSV file (`defs/all_raw_records.csv`) that tracks all scientific data files.

## Master Metadata File Structure

### File: `defs/all_raw_records.csv`

```csv
#ID,source,sample,type,tags,notes,downloadable,url,sourcefile
kleine_2018_1,kleine_2018,meteorite,isotopic,,"",True,https://...,kleine_2018.csv
ehlmann_2012_1,ehlmann_2012,basalt,reflectance,biosignature,,True,https://...,ehlmann_2012.csv
RRUFF_R061108,RRUFF,mineral,raman,,,True,https://...,RRUFF_Augite_R061108.txt
```

### Column Definitions (from SCOBI_records.ipynb)

```python
RAW_RECORD_COLS = [
    'id',           # Unique identifier (e.g., "kleine_2018_1")
    'source',       # Data source (e.g., "kleine_2018", "RELAB", "USGS")
    'sample',       # Sample type (e.g., "meteorite", "tooth", "bone")
    'type',         # Data type (e.g., "isotopic", "reflectance", "raman", "elemental")
    'tags',         # Semicolon-separated tags
    'notes',        # Free-text notes
    'downloadable', # Boolean: can be downloaded from URL?
    'url',          # Download URL (semicolon-separated if multiple)
    'sourcefile'    # Original filename (semicolon-separated if multiple)
]
```

## Data Type Metadata

Your PI defined strict column naming for each data type:

```python
TYPE_COL_NAMES = {
    "elemental": {
        'x': "constituent",      # Element name (C, N, O, Fe, etc.)
        'y': "fraction"          # Fraction 0-1
    },
    "isotopic": {
        'x': "measurement",      # Isotope name (d13C, d18O, etc.)
        'y': "permille"          # Per-mille value
    },
    "reflectance": {
        'x': "wavelength_(nm)",  # Wavelength in nanometers
        'y': "intensity"         # Reflectance intensity 0-1
    },
    "raman": {
        'x': "wavenumber_(cm-1)", # Wavenumber in cm⁻¹
        'y': "intensity_arb"      # Arbitrary intensity units
    }
}
```

**Key insight**: All parsers convert raw data to these standard column names!

## Sample Classification Metadata

Two-level classification system:

### Level 1: Biosignature Relevance

```python
SAMPLE_CLASSES = {
    "bone": "indicative",           # Potential biosignature
    "tooth": "indicative",
    "microorganism": "indicative",
    "plant": "indicative",
    "soil": "indicative",

    "basalt": "non-indicative",     # Not a biosignature
    "meteorite": "non-indicative",
    "lunarregolith": "non-indicative"
    # ... etc
}
```

### Level 2: Life Status

```python
SAMPLE_SUBCLASSES = {
    "bone": "non-alive",           # Was alive, now dead
    "tooth": "non-alive",
    "microorganism": "alive",      # Currently alive
    "plant": "alive",

    "soil": "mixed",               # May contain alive + non-alive
    "seawater": "mixed",

    "basalt": "non-indicative",    # Never alive
    "meteorite": "non-indicative"
}
```

## How Metadata Flows Through the System

### Step 1: Read Master CSV

From `load_raw_records.ipynb`:

```python
# Define directories
DATA_DIR = 'data'
DEFS_DIR = "defs"
ALL_RAW_FILE = "all_raw_records.csv"
BIBS_FILE = "scobi_citations.bib"

# Read master metadata file
all_raw_records_df = pd.read_csv(os.path.join(DEFS_DIR, ALL_RAW_FILE))
# Result: DataFrame with columns [#ID, source, sample, type, tags, etc.]
```

### Step 2: Create Record Objects

```python
# Create SCOBI_record_raw object for each row
all_raw_records = [
    SCOBI_record_raw(row, DATA_DIR)
    for idx, row in all_raw_records_df.iterrows()
]

# Each record now has attributes from the CSV:
#   r.id = "kleine_2018_1"
#   r.source = "kleine_2018"
#   r.sample = "meteorite"
#   r.type = "isotopic"
#   r.url = ["https://..."]
#   r.sourcefile = ["kleine_2018.csv"]
```

### Step 3: Metadata-Driven File Organization

```python
# File path determined by metadata:
# data/{type}/{sample}/{source}/{id}.csv

# Example:
# r.id = "kleine_2018_1"
# r.type = "isotopic"
# r.sample = "meteorite"
# r.source = "kleine_2018"
# → File path: data/isotopic/meteorite/kleine_2018/kleine_2018_1.csv
```

### Step 4: Auto-Classification

```python
# When record is created, automatic classification:
def __init__(self, series, datadir):
    SCOBI_record.__init__(self, series)

    # Auto-classify based on sample type
    self.classified = self.SAMPLE_CLASSES[self.sample]
    # e.g., "tooth" → "indicative"

    self.subclassified = self.SAMPLE_SUBCLASSES[self.sample]
    # e.g., "tooth" → "non-alive"
```

## Validation System

Your PI uses metadata for validation:

### Element Validation (for `type="elemental"`)

```python
ELEMENTS = ['Ac', 'Ag', 'Al', 'Am', ..., 'Zn', 'Zr']  # All valid elements

def checkelements(self, testline):
    """Check if line starts with valid element name"""
    el = re.match(r"\s*([A-Z][a-z]?)\d?([A-Z])?\d?[^\w]", testline)
    if el:
        return all([e for e in el.groups() if e in self.ELEMENTS])
    return False
```

### Isotope Validation (for `type="isotopic"`)

```python
ISOTOPES = ['d13C', 'd18O_VSMOW', 'd18O_VPDB', 'd2H', 'd15N', 'd34S', 'd30Si']

def checkisotopes(self, testline):
    """Check if line starts with valid isotope name"""
    iso = re.match(r"\s*(d\d\d?[A-Z][a-z]?_?[A-Z]{0,5})[^\w]", testline)
    if iso:
        return any([i for i in iso.groups() if i in self.ISOTOPES])
    return False
```

### Numeric Validation (for `type="reflectance"` or `"raman"`)

```python
def checknumeric(self, testline):
    """Check if line is valid numeric data"""
    # Reject lines with letters (except E for scientific notation)
    hasletters = re.search(r"(.*[A-DF-Za-df-z].*)", testline)
    hasnumbers = re.search(r"\d", testline)

    return (not hasletters) and hasnumbers
```

## Bibliography Metadata

Separate BibTeX file for citations:

### File: `defs/scobi_citations.bib`

```bibtex
@article{kleine_2018,
  author = {Kleine, T. and ...},
  title = {Tungsten isotopes in meteorites...},
  journal = {Science},
  year = {2018}
}

@misc{RELAB,
  title = {{RELAB} Spectral Library Bundle},
  url = {https://pds.jpl.nasa.gov/...},
  year = {2020}
}
```

### How PI Loads It

```python
import pybtex.database

# Load bibliography
all_raw_bibs = pybtex.database.parse_file(
    os.path.join(DEFS_DIR, BIBS_FILE),
    bib_format='bibtex'
)

# Attach to records
for r in all_raw_records:
    r.read_bib(all_raw_bibs)
    # Now r.bib contains the BibTeX entry for r.source
```

## Complete Workflow Example

```python
# 1. Load metadata
all_raw_records_df = pd.read_csv("defs/all_raw_records.csv")
all_raw_bibs = pybtex.database.parse_file("defs/scobi_citations.bib")

# 2. Create record objects
all_raw_records = [
    SCOBI_record_raw(row, "data")
    for idx, row in all_raw_records_df.iterrows()
]

# 3. For each record, read data and bibliography
for r in all_raw_records:
    # Read processed data file
    r.read_raw()  # Reads: data/{type}/{sample}/{source}/{id}.csv

    # Attach bibliography
    r.read_bib(all_raw_bibs)

    # Now available:
    #   r.id = "kleine_2018_1"
    #   r.type = "isotopic"
    #   r.sample = "meteorite"
    #   r.source = "kleine_2018"
    #   r.classified = "non-indicative"
    #   r.subclassified = "non-indicative"
    #   r.data_df = DataFrame with columns ["measurement", "permille"]
    #   r.bib = BibTeX citation string
```

## Metadata for Parsing (Source-Specific)

Your PI uses `source` metadata to select parser:

```python
PARSERS = {
    'Hyttinen_2020': getODSIDB,    # TIFF files with masks
    'Jiang_2025': getJiang,        # Custom CSV transpose
    'Li_2023': getLi,              # ZIP with specific CSV
    'NIST': getNIST,               # Subject-based columns
    'SOLSA': getrod,               # CIF format .rod files
    'RELAB': getRELAB,             # Special comment handling
    'USGS': getUSGS,               # ZIP archives
    'Vu_2025': getVu               # Column extraction
    # default: getcsv              # Standard CSV/TSV
}

# Usage:
if r.source in PARSERS.keys():
    data_df = PARSERS[r.source](r, rawfiles)
else:
    data_df = getcsv(rawfiles)
```

## Metadata-Driven Download

```python
# From metadata
if r.downloadable:
    for url, sourcefile in zip(r.url, r.sourcefile):
        # Download from URL
        savepath = os.path.join(
            r.datadir,
            r.type,
            r.sample,
            r.source,
            "src-new",    # New downloads go to src-new/
            sourcefile
        )
        response = requests.get(url)
        # Save file...
```

## Key Patterns Your PI Uses

### 1. Metadata Determines File Path

```python
# NOT hardcoded paths!
# Uses metadata: type + sample + source + id

filepath = os.path.join(
    datadir,
    record.type,     # "isotopic"
    record.sample,   # "meteorite"
    record.source,   # "kleine_2018"
    record.id + ".csv"  # "kleine_2018_1.csv"
)
```

### 2. Metadata Validates Data

```python
# Different validation based on record.type
validator = VALIDATORS[record.type]

if validator(line):
    # Keep this line of data
else:
    # Skip invalid line
```

### 3. Metadata Normalizes Columns

```python
# All parsers output standard columns based on record.type
col_x = TYPE_COL_NAMES[record.type]['x']  # "wavenumber_(cm-1)"
col_y = TYPE_COL_NAMES[record.type]['y']  # "intensity_arb"

df.columns = [col_x, col_y]
```

### 4. Metadata Enables Filtering

```python
# Filter by type
raman_records = [r for r in all_raw_records if r.type == 'raman']

# Filter by sample
tooth_records = [r for r in all_raw_records if r.sample == 'tooth']

# Filter by classification
indicative_records = [r for r in all_raw_records if r.classified == 'indicative']

# Complex filter
rs = [r for r in all_raw_records if (r.type == 'raman' and r.sample == 'bone')]
```

## Summary: Metadata Purpose

1. **Organization**: Determines file paths (`data/{type}/{sample}/{source}/`)
2. **Validation**: Filters valid data lines (elements, isotopes, numerics)
3. **Normalization**: Standardizes column names across sources
4. **Classification**: Auto-categorizes samples (indicative/non-indicative, alive/non-alive)
5. **Parsing**: Selects correct parser based on source
6. **Citation**: Links data to bibliography
7. **Discovery**: Enables filtering and querying records

## Where Metadata Lives

```
defs/
├── all_raw_records.csv    # Master metadata: id, source, sample, type, url, etc.
└── scobi_citations.bib    # Bibliography metadata

data/
└── {type}/
    └── {sample}/
        └── {source}/
            ├── src/               # Original source files
            ├── src-new/           # Downloaded updates
            └── {id}.csv           # Processed data (metadata in filename/path)
```

## Why This Design?

Your PI chose this because:

1. **CSV is portable** - No database needed
2. **File path encodes metadata** - Can infer type/sample/source from path
3. **Separate data from metadata** - Data files are clean, metadata in separate CSV
4. **Version control friendly** - Git can track changes to CSV
5. **Human readable** - Easy to inspect and edit
6. **Flexible** - Can add new columns without breaking code
