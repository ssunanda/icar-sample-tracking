"""
Complete Record Upload with Full Metadata from CSV
===================================================
This script:
1. Reads metadata from all_raw_records.csv
2. For a test file, extracts: ID, source, sample, type, units, tags, methods, notes
3. Maps to correct ODR fields
4. Uploads record with data file

Test with one record first, then batch upload.
"""

import pandas as pd
from pathlib import Path
from ODR_API_Client import ODRAPIClient

# =============================================================================
# CONFIGURATION
# =============================================================================
BASE_URL = "https://www.odr.io/api/v4"
USERNAME = "amshahid@ncsu.edu"
PASSWORD = "qkh8fjd6adh*NPU!ekn"
DATASET_UUID = "063c0d3d4bd183ab0dda87c544ae"

# Paths
CSV_PATH = Path(r"C:\Users\abdul\Box\2021_SCOBI\ODR_data_release\raw_main\defs\all_raw_records.csv")
DATA_DIR = Path(r"c:\Users\abdul\Downloads\raw_main-selected\raw_main\data")

# =============================================================================
# FIELD UUIDS (constants for this dataset)
# =============================================================================
FIELD_UUIDS = {
    "Data File": "a65467babf8a1ac7e1d7319e3928",
    "Data Type": "996f2f04be5e12bc6d251e54bb8f",
    "Source ID": "98c0dc4db715d503abc93fa598f9",
    "Class": "676b2e7658da32d4c518b3877401",
    "Subclass": "bcf6ab5a9b02de9e0594772f2c2a",
    "Sample Type": "423044bee60c5e83fcb7fbf1b713",
    "Source Citation": "0719c6187a235650b437bb742bf9",
    "Notes": "adc43cecf7714687c865ca79f078",
    "Source Links": "cb24ce292d861629416b51c40aa0",
    "Tags": "0000000000000000000000000000",  # TODO: Get actual UUID
    "Units": "0000000000000000000000000001",  # TODO: Get actual UUID  
    "Methods": "0000000000000000000000000002",  # TODO: Get actual UUID
}

# Classification mapping
SAMPLE_CLASSES = {
    "bone": "Indicative", "tooth": "Indicative", "microorganism": "Indicative",
    "plant": "Indicative", "soil": "Indicative", "human": "Indicative",
    "microbialmat": "Indicative", "basalt": "Non-Indicative", "meteorite": "Non-Indicative",
    "lunarregolith": "Non-Indicative", "marsregolith": "Non-Indicative",
    "magnetite": "Non-Indicative", "calcite": "Non-Indicative", "clay": "Non-Indicative",
    "carbonatite": "Non-Indicative", "coralskeleton": "Non-Indicative",
    "kerogen": "Non-Indicative", "ice": "Non-Indicative", "snow": "Non-Indicative",
    "sand": "Non-Indicative", "silt": "Non-Indicative", "seawater": "Non-Indicative",
}

SAMPLE_SUBCLASSES = {
    "bone": "Non-Alive", "tooth": "Non-Alive", "microorganism": "Alive",
    "plant": "Alive", "human": "Non-Alive", "microbialmat": "Alive",
    "soil": "Mixed", "seawater": "Mixed",
}


def load_metadata():
    """Load metadata CSV into a DataFrame indexed by #ID."""
    # Header starts with #ID, so we read it without treating # as comment
    df = pd.read_csv(CSV_PATH)
    # Rename #ID column to id
    df = df.rename(columns={'#ID': 'id'})
    df = df.set_index("id")
    return df


def discover_radio_options(client):
    """Fetch existing records to get radio option UUIDs."""
    print("📋 Discovering radio options from ODR...")
    ds = client.get_dataset(DATASET_UUID)
    
    options = {"Data Type": {}, "Sample Type": {}, "Class": {}, "Subclass": {}}
    
    for rec in ds.get("records", []):
        for field in rec.get("fields", []):
            fname = field.get("field_name")
            if fname in options:
                for val in field.get("values", []):
                    name = val.get("name")
                    uuid = val.get("template_radio_option_uuid")
                    if name and uuid:
                        options[fname][name] = uuid
    
    print(f"   Data Types: {len(options['Data Type'])} options")
    print(f"   Sample Types: {len(options['Sample Type'])} options")
    print(f"   Classes: {len(options['Class'])} options")
    print(f"   Subclasses: {len(options['Subclass'])} options")
    
    return options


def find_data_file(record_id, data_type, sample_type, source_id):
    """Find the actual data file path for a record."""
    # Path pattern: data/{type}/{sample}/{source}/*.csv
    search_dir = DATA_DIR / data_type.lower() / sample_type / source_id
    
    if not search_dir.exists():
        return None
    
    # Look for CSV files (not in src/)
    for f in search_dir.glob("*.csv"):
        if "src" not in str(f.parent):
            # Check if filename matches record_id
            if record_id in f.stem:
                return f
    
    # Try just the first CSV file
    csv_files = [f for f in search_dir.glob("*.csv") if "src" not in str(f.parent)]
    return csv_files[0] if csv_files else None


def create_record_payload(meta_row, radio_options):
    """Create the fields payload for a record."""
    fields = []
    
    # Source ID (text)
    fields.append({
        "field_name": "Source ID",
        "field_uuid": FIELD_UUIDS["Source ID"],
        "value": str(meta_row["source"])
    })
    
    # Data Type (radio)
    data_type = str(meta_row["type"]).capitalize()
    if data_type in radio_options["Data Type"]:
        fields.append({
            "field_name": "Data Type",
            "field_uuid": FIELD_UUIDS["Data Type"],
            "values": [{
                "template_radio_option_uuid": radio_options["Data Type"][data_type],
                "name": data_type,
                "selected": 1
            }]
        })
    
    # Sample Type (radio)
    sample = str(meta_row["sample"])
    if sample in radio_options["Sample Type"]:
        fields.append({
            "field_name": "Sample Type",
            "field_uuid": FIELD_UUIDS["Sample Type"],
            "values": [{
                "template_radio_option_uuid": radio_options["Sample Type"][sample],
                "name": sample,
                "selected": 1
            }]
        })
    
    # Class (radio)
    class_name = SAMPLE_CLASSES.get(sample, "Non-Indicative")
    if class_name in radio_options["Class"]:
        fields.append({
            "field_name": "Class",
            "field_uuid": FIELD_UUIDS["Class"],
            "values": [{
                "template_radio_option_uuid": radio_options["Class"][class_name],
                "name": class_name,
                "selected": 1
            }]
        })
    
    # Subclass (radio)
    subclass_name = SAMPLE_SUBCLASSES.get(sample, "Non-Indicative")
    if subclass_name in radio_options["Subclass"]:
        fields.append({
            "field_name": "Subclass",
            "field_uuid": FIELD_UUIDS["Subclass"],
            "values": [{
                "template_radio_option_uuid": radio_options["Subclass"][subclass_name],
                "name": subclass_name,
                "selected": 1
            }]
        })
    
    # Notes (text) - combine tags, methods, units, notes
    notes_parts = []
    if pd.notna(meta_row.get("tags")) and str(meta_row["tags"]) != "nan":
        notes_parts.append(f"Tags: {meta_row['tags']}")
    if pd.notna(meta_row.get("methods")) and str(meta_row["methods"]) != "nan":
        notes_parts.append(f"Methods: {meta_row['methods']}")
    if pd.notna(meta_row.get("units")) and str(meta_row["units"]) != "nan":
        notes_parts.append(f"Units: {meta_row['units']}")
    if pd.notna(meta_row.get("notes")) and str(meta_row["notes"]) != "nan":
        notes_parts.append(f"Notes: {meta_row['notes']}")
    
    if notes_parts:
        fields.append({
            "field_name": "Notes",
            "field_uuid": FIELD_UUIDS["Notes"],
            "value": " | ".join(notes_parts)
        })
    
    return fields


def upload_single_record(client, record_id, meta_row, radio_options, dry_run=False):
    """Upload a single record with full metadata."""
    data_type = str(meta_row["type"])
    sample = str(meta_row["sample"])
    source = str(meta_row["source"])
    
    # Find data file
    file_path = find_data_file(record_id, data_type, sample, source)
    
    print(f"\n📄 Record: {record_id}")
    print(f"   Source: {source}")
    print(f"   Type: {data_type} | Sample: {sample}")
    print(f"   File: {file_path.name if file_path else 'NOT FOUND'}")
    
    if not file_path:
        print("   ❌ Data file not found, skipping")
        return False
    
    if dry_run:
        print("   [DRY RUN] Would upload with metadata")
        return True
    
    try:
        # Create record
        rec = client.create_record(DATASET_UUID)
        record_uuid = rec.get("record_uuid")
        print(f"   Created: {rec.get('record_name')}")
        
        # Add metadata fields
        rec["fields"] = create_record_payload(meta_row, radio_options)
        
        # Push metadata
        client.push_record(rec)
        print("   ✅ Metadata pushed")
        
        # Upload file
        client.upload_file(
            file_path=str(file_path),
            record_uuid=record_uuid,
            dataset_uuid=DATASET_UUID,
            template_field_uuid="",
            field_uuid=FIELD_UUIDS["Data File"],
            name=file_path.name
        )
        print(f"   ✅ File uploaded: {file_path.name}")
        print(f"   🔗 View: https://odr.io/view/record/{record_uuid}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("COMPLETE RECORD UPLOAD TEST")
    print("=" * 60)
    
    # Load metadata
    print("\n1. Loading metadata from CSV...")
    meta = load_metadata()
    print(f"   Loaded {len(meta)} records")
    
    # Authenticate
    print("\n2. Authenticating...")
    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.authenticate()
    print("   Done!")
    
    # Discover radio options
    radio_options = discover_radio_options(client)
    
    # Test with one record - pick first elemental basalt
    print("\n3. Testing with sample record...")
    test_id = "table6-175R-1"  # Dick_1992 basalt elemental
    
    if test_id in meta.index:
        row = meta.loc[test_id]
        print(f"\n   Metadata for '{test_id}':")
        print(f"   - source: {row['source']}")
        print(f"   - sample: {row['sample']}")
        print(f"   - type: {row['type']}")
        print(f"   - units: {row['units']}")
        print(f"   - tags: {row['tags']}")
        print(f"   - methods: {row['methods']}")
        
        # Upload
        success = upload_single_record(client, test_id, row, radio_options)
        
        if success:
            print("\n" + "=" * 60)
            print("✅ TEST SUCCESSFUL!")
            print("=" * 60)
    else:
        print(f"   ❌ Record '{test_id}' not found in metadata")


if __name__ == "__main__":
    main()
