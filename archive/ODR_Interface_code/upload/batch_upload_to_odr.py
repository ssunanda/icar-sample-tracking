"""
Batch Upload Script for Elemental and Isotopic Data to ODR
===========================================================
This script uploads all processed CSV files from data/elemental and data/isotopic
to ODR with proper metadata.

Usage:
    python batch_upload_to_odr.py [--dry-run] [--limit N]
    
Options:
    --dry-run   Show what would be uploaded without actually uploading
    --limit N   Only upload first N files (for testing)
"""

import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "client"))
from ODR_API_Client import ODRAPIClient

# =============================================================================
# CONFIGURATION
# =============================================================================
BASE_URL = "https://www.odr.io/api/v4"
USERNAME = "amshahid@ncsu.edu"
PASSWORD = "qkh8fjd6adh*NPU!ekn"
DATASET_UUID = "063c0d3d4bd183ab0dda87c544ae"

# Base data directory
DATA_DIR = Path(r"c:\Users\abdul\Downloads\raw_main-selected\raw_main\data")

# Data types to process
DATA_TYPES_TO_UPLOAD = ["elemental", "isotopic"]

# =============================================================================
# FIELD UUIDS (known constants)
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
}

# =============================================================================
# SAMPLE CLASSIFICATION (from LOCAL_METADATA_SYSTEM.md)
# =============================================================================
SAMPLE_CLASSES = {
    "bone": "Indicative",
    "tooth": "Indicative",
    "microorganism": "Indicative",
    "plant": "Indicative",
    "soil": "Indicative",
    "human": "Indicative",
    "microbialmat": "Indicative",
    "basalt": "Non-Indicative",
    "meteorite": "Non-Indicative",
    "lunarregolith": "Non-Indicative",
    "marsregolith": "Non-Indicative",
    "magnetite": "Non-Indicative",
    "calcite": "Non-Indicative",
    "clay": "Non-Indicative",
    "carbonatite": "Non-Indicative",
    "coralskeleton": "Non-Indicative",
    "kerogen": "Non-Indicative",
    "ice": "Non-Indicative",
    "snow": "Non-Indicative",
    "sand": "Non-Indicative",
    "silt": "Non-Indicative",
    "seawater": "Non-Indicative",
    "shell": "Non-Indicative",
    "chalk": "Non-Indicative",
}

SAMPLE_SUBCLASSES = {
    "bone": "Non-Alive",
    "tooth": "Non-Alive",
    "microorganism": "Alive",
    "plant": "Alive",
    "human": "Non-Alive",
    "microbialmat": "Alive",
    "soil": "Mixed",
    "seawater": "Mixed",
    "basalt": "Non-Indicative",
    "meteorite": "Non-Indicative",
    "lunarregolith": "Non-Indicative",
    "marsregolith": "Non-Indicative",
    "magnetite": "Non-Indicative",
    "calcite": "Non-Indicative",
    "clay": "Non-Indicative",
    "carbonatite": "Non-Indicative",
    "coralskeleton": "Non-Indicative",
    "kerogen": "Non-Indicative",
    "ice": "Non-Indicative",
    "snow": "Non-Indicative",
    "sand": "Non-Indicative",
    "silt": "Non-Indicative",
    "shell": "Non-Indicative",
    "chalk": "Non-Indicative",
}

# =============================================================================
# RADIO OPTION UUIDS (will be populated from existing records)
# =============================================================================
RADIO_OPTIONS = {
    "Data Type": {},
    "Sample Type": {},
    "Class": {},
    "Subclass": {},
}


def discover_radio_options(client):
    """Fetch existing records to discover radio option UUIDs."""
    print("📋 Discovering radio option UUIDs from existing records...")
    ds = client.get_dataset(DATASET_UUID)
    
    for rec in ds.get("records", []):
        for field in rec.get("fields", []):
            fname = field.get("field_name")
            if fname in RADIO_OPTIONS:
                for val in field.get("values", []):
                    name = val.get("name")
                    uuid = val.get("template_radio_option_uuid")
                    if name and uuid and name not in RADIO_OPTIONS[fname]:
                        RADIO_OPTIONS[fname][name] = uuid
    
    print("   Found options:")
    for field, opts in RADIO_OPTIONS.items():
        print(f"   {field}: {list(opts.keys())}")


def find_files_to_upload():
    """Find all CSV files to upload (not in src/ folders)."""
    files = []
    
    for data_type in DATA_TYPES_TO_UPLOAD:
        type_dir = DATA_DIR / data_type
        if not type_dir.exists():
            print(f"⚠️ Directory not found: {type_dir}")
            continue
        
        # Walk through sample types
        for sample_dir in type_dir.iterdir():
            if not sample_dir.is_dir():
                continue
            sample_type = sample_dir.name
            
            # Walk through source directories
            for source_dir in sample_dir.iterdir():
                if not source_dir.is_dir():
                    continue
                source_id = source_dir.name
                
                # Find CSV files NOT in src/ subdirectory
                for file in source_dir.glob("*.csv"):
                    if "src" not in str(file.parent):
                        files.append({
                            "path": file,
                            "data_type": data_type.capitalize(),
                            "sample_type": sample_type,
                            "source_id": source_id,
                            "filename": file.name,
                        })
    
    return files


def create_record_fields(file_info, missing_options):
    """Create the fields array for a record. Skips radio options not in ODR."""
    fields = []
    
    # Text fields - always added
    fields.append({
        "field_name": "Source ID",
        "field_uuid": FIELD_UUIDS["Source ID"],
        "value": file_info["source_id"]
    })
    
    # Radio field: Data Type
    data_type = file_info["data_type"]
    if data_type in RADIO_OPTIONS["Data Type"]:
        fields.append({
            "field_name": "Data Type",
            "field_uuid": FIELD_UUIDS["Data Type"],
            "values": [{
                "template_radio_option_uuid": RADIO_OPTIONS["Data Type"][data_type],
                "name": data_type,
                "selected": 1
            }]
        })
    else:
        missing_options.add(f"Data Type: {data_type}")
    
    # Radio field: Sample Type (skip if not in ODR)
    sample = file_info["sample_type"]
    if sample in RADIO_OPTIONS["Sample Type"]:
        fields.append({
            "field_name": "Sample Type",
            "field_uuid": FIELD_UUIDS["Sample Type"],
            "values": [{
                "template_radio_option_uuid": RADIO_OPTIONS["Sample Type"][sample],
                "name": sample,
                "selected": 1
            }]
        })
    else:
        missing_options.add(f"Sample Type: {sample}")
    
    # Radio field: Class
    class_name = SAMPLE_CLASSES.get(sample, "Non-Indicative")
    if class_name in RADIO_OPTIONS["Class"]:
        fields.append({
            "field_name": "Class",
            "field_uuid": FIELD_UUIDS["Class"],
            "values": [{
                "template_radio_option_uuid": RADIO_OPTIONS["Class"][class_name],
                "name": class_name,
                "selected": 1
            }]
        })
    else:
        missing_options.add(f"Class: {class_name}")
    
    # Radio field: Subclass
    subclass_name = SAMPLE_SUBCLASSES.get(sample, "Non-Indicative")
    if subclass_name in RADIO_OPTIONS["Subclass"]:
        fields.append({
            "field_name": "Subclass",
            "field_uuid": FIELD_UUIDS["Subclass"],
            "values": [{
                "template_radio_option_uuid": RADIO_OPTIONS["Subclass"][subclass_name],
                "name": subclass_name,
                "selected": 1
            }]
        })
    else:
        missing_options.add(f"Subclass: {subclass_name}")
    
    return fields


def upload_file(client, file_info, missing_options, dry_run=False):
    """Upload a single file to ODR."""
    try:
        if dry_run:
            print(f"   [DRY RUN] Would upload: {file_info['filename']}")
            print(f"             Type: {file_info['data_type']}, Sample: {file_info['sample_type']}, Source: {file_info['source_id']}")
            return True
        
        # Create record
        record = client.create_record(DATASET_UUID)
        record_uuid = record.get("record_uuid")
        
        # Add metadata fields (skips missing radio options)
        record["fields"] = create_record_fields(file_info, missing_options)
        
        # Push metadata
        client.push_record(record)
        
        # Upload file
        client.upload_file(
            file_path=str(file_info["path"]),
            record_uuid=record_uuid,
            dataset_uuid=DATASET_UUID,
            template_field_uuid="",
            field_uuid=FIELD_UUIDS["Data File"],
            name=file_info["filename"]
        )
        
        print(f"   ✅ {file_info['filename']} -> Record {record.get('record_name')}")
        return True
        
    except Exception as e:
        print(f"   ❌ {file_info['filename']}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Batch upload data to ODR")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be uploaded")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of files to upload")
    args = parser.parse_args()
    
    print("=" * 60)
    print("BATCH UPLOAD TO ODR")
    print("=" * 60)
    
    # Authenticate
    print("\n📡 Authenticating...")
    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.authenticate()
    print("   Done!")
    
    # Discover radio options
    discover_radio_options(client)
    
    # Find files
    print("\n📂 Finding files to upload...")
    files = find_files_to_upload()
    print(f"   Found {len(files)} files")
    
    if args.limit > 0:
        files = files[:args.limit]
        print(f"   Limited to {len(files)} files")
    
    # Show summary by type
    by_type = {}
    for f in files:
        key = f"{f['data_type']}/{f['sample_type']}"
        by_type[key] = by_type.get(key, 0) + 1
    
    print("\n📊 Files by type:")
    for key, count in sorted(by_type.items()):
        print(f"   {key}: {count}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No files will be uploaded")
    
    # Confirm
    if not args.dry_run:
        print(f"\n⚠️ About to upload {len(files)} files to ODR.")
        response = input("Continue? (y/n): ")
        if response.lower() != "y":
            print("Cancelled.")
            return
    
    # Upload
    print("\n📤 Uploading...")
    success = 0
    failed = 0
    missing_options = set()  # Track missing radio options
    
    for i, file_info in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] {file_info['filename']}")
        if upload_file(client, file_info, missing_options, dry_run=args.dry_run):
            success += 1
        else:
            failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("COMPLETE!")
    print("=" * 60)
    print(f"\n✅ Successful: {success}")
    print(f"❌ Failed: {failed}")
    
    if missing_options:
        print(f"\n⚠️ Missing radio options (fields skipped):")
        for opt in sorted(missing_options):
            print(f"   - {opt}")


if __name__ == "__main__":
    main()
