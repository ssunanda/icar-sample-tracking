# ODR Metadata System - How It Works

## Overview

Your PI is using a **field-based metadata system** where each ODR record contains multiple "fields" that act as metadata descriptors for the scientific data files.

## Record Structure (From Notebook Analysis)

```json
{
  "database_uuid": "063c0d3d4bd183ab0dda87c544ae",
  "record_name": "772962",
  "record_uuid": "60862b03967fc4e8a73d57326b39",
  "template_uuid": "",

  "_record_metadata": {
    "_create_date": "2025-06-18 20:15:29",
    "_update_date": "2025-06-27 03:56:44",
    "_create_auth": "someone@example.edu"
  },

  "fields": [
    {
      "field_name": "Data File",
      "field_uuid": "a65467babf8a1ac7e1d7319e3928",
      "files": [...]
    },
    {
      "field_name": "Source",
      "value": "RRUFF (v2)"
    },
    {
      "field_name": "Source Link",
      "value": "https://..."
    },
    {
      "field_name": "Source Citation",
      "value": "@misc{RELAB, ...}"
    }
  ]
}
```

## Key Metadata Fields Your PI Uses

From the notebook output, Cell 15116401 shows all field names:

1. **Class** - Sample classification (indicative/non-indicative)
2. **Data File** - The actual scientific data file (CSV, TXT, TAB)
3. **Data Type** - Type of data (reflectance, raman, elemental, isotopic)
4. **Notes** - Free-text notes
5. **Sample Type** - What was measured (tooth, bone, meteorite, etc.)
6. **Source** - Where data came from (RELAB, USGS, RRUFF, etc.)
7. **Source Citation** - BibTeX citation
8. **Source Link** - URL to original data
9. **Subclass** - Finer classification (alive, non-alive, mixed)

## How Metadata Connects Local Files to ODR

### Current System (from load_raw_records.ipynb)

```python
# Local record tracking (in defs/all_raw_records.csv)
columns = ['#ID', 'source', 'sample', 'type', 'tags', 'notes',
           'downloadable', 'url', 'sourcefile']

# Example row:
# ID: kleine_2018_1
# source: kleine_2018
# sample: meteorite
# type: isotopic
# sourcefile: kleine_2018.csv
```

### PI's Mapping Strategy

**Local File Path Pattern**:
```
data/{type}/{sample}/{source}/{id}.csv
```

**Example**:
```
data/reflectance/meteorite/RELAB/RELAB_sample_001.csv
```

**ODR Record**: The same file is stored as:
- Record Name: "772924" (auto-generated ID)
- Field "Data Type": "reflectance"
- Field "Sample Type": "meteorite"
- Field "Source": "RELAB"
- Field "Data File": Attached file "RELAB_sample_001.csv"

## How Your PI Accesses Metadata

### Method 1: Iterating Through Fields

```python
# From notebook Cell 15116401
for record in dataset.get('records', []):
    for field in record.get('fields', []):
        field_name = field.get('field_name')

        # Text fields have 'value'
        if 'value' in field:
            value = field.get('value')

        # File fields have 'files' array
        if 'files' in field:
            for file_info in field.get('files', []):
                filename = file_info.get('original_name')
                file_uuid = file_info.get('file_uuid')
```

### Method 2: Using Helper Function (from ODR_API_Client.py)

```python
def set_field_value(self, record: Dict, field_name: str, new_value) -> None:
    """Find field by name and update its value"""
    for fld in record.get("fields", []):
        if fld.get("field_name") == field_name:
            if "value" in fld:
                fld["value"] = new_value
            return

    # Field doesn't exist - create it
    record.setdefault("fields", []).append({
        "field_name": field_name,
        "value": new_value
    })
```

### Method 3: Direct Field Access Pattern

```python
def get_field_value(record: Dict, field_name: str) -> str:
    """Extract a specific metadata field value"""
    for field in record.get('fields', []):
        if field.get('field_name') == field_name:
            return field.get('value', '')
    return None

# Usage:
source = get_field_value(record, "Source")
data_type = get_field_value(record, "Data Type")
sample_type = get_field_value(record, "Sample Type")
```

## Metadata for File Path Mapping (Critical for Sync)

### Problem
You need to map between:
- Local: `data/reflectance/meteorite/RELAB/sample_001.csv`
- ODR: Record with UUID `abc123...`

### Solution: Use Metadata Fields

```python
def build_local_path_from_metadata(record: Dict, data_dir: str) -> str:
    """Build local path using ODR metadata fields"""

    # Extract metadata
    data_type = None
    sample_type = None
    source = None
    filename = None

    for field in record.get('fields', []):
        field_name = field.get('field_name')

        if field_name == "Data Type":
            data_type = field.get('value')
        elif field_name == "Sample Type":
            sample_type = field.get('value')
        elif field_name == "Source":
            source = field.get('value')
        elif field_name == "Data File":
            files = field.get('files', [])
            if files:
                filename = files[0].get('original_name')

    # Build path
    if all([data_type, sample_type, source, filename]):
        return os.path.join(data_dir, data_type, sample_type, source, filename)
    else:
        return None
```

### Why This Is Better Than Filename Search

**Current sync manager**:
```python
# Searches entire data/ tree for filename
for root, dirs, filenames in os.walk(self.data_dir):
    if original_name in filenames:
        return os.path.join(root, original_name)
# Problem: Slow, can find wrong file if duplicates exist
```

**With metadata**:
```python
# Direct path construction
path = os.path.join(
    data_dir,
    get_field_value(record, "Data Type"),
    get_field_value(record, "Sample Type"),
    get_field_value(record, "Source"),
    get_original_filename(record)
)
# Fast, unambiguous, correct
```

## Metadata Timeline (from _field_metadata)

Each field has its own metadata tracking:

```json
{
  "field_name": "Source",
  "value": "RRUFF (v2)",
  "_field_metadata": {
    "_create_date": "2025-06-19 16:32:20",
    "_update_date": "2025-06-19 16:32:20",
    "_create_auth": "someone@example.edu",
    "_public_date": "2200-01-01 00:00:00"
  }
}
```

**Key insight**: Use `_update_date` for conflict detection!

```python
def get_odr_file_info(record: Dict) -> Dict:
    """Get file info including update timestamp"""
    for field in record.get("fields", []):
        if field.get("field_name") == "Data File":
            return {
                "file_uuid": field['files'][0].get("file_uuid"),
                "original_name": field['files'][0].get("original_name"),
                # Use field metadata for timestamp!
                "odr_timestamp": field.get("_field_metadata", {}).get("_update_date"),
                "size": int(field['files'][0].get("file_size", 0))
            }
    return None
```

## How PI Populates Metadata (Workflow)

### Step 1: Create Record
```python
# Creates empty record with auto-generated ID
new_record = client.create_record(DATASET_UUID)
# Returns: {"record_uuid": "abc123...", "record_name": "773223"}
```

### Step 2: Add Metadata Fields
```python
# Set text metadata
client.set_field_value(new_record, "Data Type", "reflectance")
client.set_field_value(new_record, "Sample Type", "meteorite")
client.set_field_value(new_record, "Source", "RELAB")
client.set_field_value(new_record, "Source Link", "https://...")
client.set_field_value(new_record, "Source Citation", bibtex_citation)
client.set_field_value(new_record, "Class", "non-indicative")
client.set_field_value(new_record, "Subclass", "non-indicative")
```

### Step 3: Upload Data File
```python
# Upload actual data file
client.upload_file(
    file_path="data/reflectance/meteorite/RELAB/sample_001.csv",
    record_uuid=new_record['record_uuid'],
    dataset_uuid=DATASET_UUID,
    template_field_uuid="",  # Found from existing records
    field_uuid="",           # Will be "Data File" field
    name="sample_001.csv"
)
```

### Step 4: Push to ODR
```python
# Save all changes
client.push_record(new_record)
```

## Metadata-Driven Sync Strategy

### Enhanced Sync Manager

Update `SCOBI_sync_manager.py` to use metadata:

```python
def _get_local_filepath_for_record(self, record: Dict) -> Optional[str]:
    """Use metadata fields to construct local path"""

    # Extract from metadata fields
    data_type = None
    sample_type = None
    source = None
    filename = None

    for field in record.get('fields', []):
        field_name = field.get('field_name')

        if field_name == "Data Type":
            data_type = field.get('value', '').lower()
        elif field_name == "Sample Type":
            sample_type = field.get('value', '').lower()
        elif field_name == "Source":
            source = field.get('value')
        elif field_name == "Data File":
            files = field.get('files', [])
            if files:
                filename = files[0].get('original_name')

    # Construct path
    if all([data_type, sample_type, source, filename]):
        local_path = os.path.join(
            self.data_dir,
            data_type,      # reflectance, raman, etc.
            sample_type,    # meteorite, tooth, etc.
            source,         # RELAB, USGS, etc.
            filename        # actual .csv file
        )

        # Verify it exists
        if os.path.exists(local_path):
            return local_path
        else:
            print(f"⚠️  Metadata path doesn't exist: {local_path}")
            return None

    # Fallback to filename search if metadata incomplete
    if filename:
        for root, dirs, filenames in os.walk(self.data_dir):
            if filename in filenames:
                return os.path.join(root, filename)

    return None
```

## Complete Example: Reading Metadata

```python
from ODR_API_Client import ODRAPIClient

client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
client.authenticate()

# Get a record
record = client.get_record("60862b03967fc4e8a73d57326b39")

# Extract all metadata
metadata = {}
for field in record.get('fields', []):
    field_name = field.get('field_name')

    if 'value' in field:
        # Text field
        metadata[field_name] = field.get('value')
    elif 'files' in field:
        # File field
        files = field.get('files', [])
        if files:
            metadata[field_name] = {
                'filename': files[0].get('original_name'),
                'uuid': files[0].get('file_uuid'),
                'size': files[0].get('file_size')
            }

print("Metadata extracted:")
for key, value in metadata.items():
    print(f"  {key}: {value}")

# Output:
# Source: RRUFF (v2)
# Source Link: https://pds-geosciences.wustl.edu/...
# Source Citation: @misc{RELAB, ...}
# Data File: {'filename': 'test_upload.txt', 'uuid': 'b488...', 'size': '30'}
```

## Key Takeaways

1. **Metadata is in `fields` array**: Each field has `field_name` + (`value` OR `files`)

2. **Three types of fields**:
   - Text fields: `{"field_name": "Source", "value": "RELAB"}`
   - File fields: `{"field_name": "Data File", "files": [...]}`
   - Checkbox: `{"field_name": "...", "selected": 1}`

3. **Timestamps in `_field_metadata`**: Use for conflict detection

4. **Path mapping**: Use metadata fields (Data Type, Sample Type, Source) to build local paths

5. **Helper functions**:
   - `get_field_value(record, field_name)` - Extract text field
   - `set_field_value(record, field_name, value)` - Update text field
   - `get_original_filename(record)` - Extract filename from Data File field

6. **Your sync system should**:
   - Read metadata to find local path (fast, accurate)
   - Check `_update_date` in `_field_metadata` for change detection
   - Preserve all metadata when uploading new files
