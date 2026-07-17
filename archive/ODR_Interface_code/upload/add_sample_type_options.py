"""
Add Sample Type Radio Options to ODR
=====================================
This script:
1. Reads all_raw_records.csv to get unique sample types
2. Creates dummy records with each sample type to add them as radio options
3. Then deletes those dummy records (or you can manually delete)
"""

import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "client"))
from ODR_API_Client import ODRAPIClient

# Configuration
BASE_URL = "https://www.odr.io/api/v4"
USERNAME = "amshahid@ncsu.edu"
PASSWORD = "qkh8fjd6adh*NPU!ekn"
DATASET_UUID = "063c0d3d4bd183ab0dda87c544ae"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = str(REPO_ROOT / "defs" / "all_raw_records.csv")
AUTO_CONFIRM = os.environ.get("AUTO_CONFIRM", "").lower() in ("1", "true", "y", "yes")

# Field UUIDs
SAMPLE_TYPE_FIELD_UUID = "423044bee60c5e83fcb7fbf1b713"

def get_unique_sample_types():
    """Extract unique sample types from the CSV."""
    samples = set()
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and not row[0].startswith('#'):  # Skip header/comments
                if len(row) > 2:
                    samples.add(row[2])  # sample column is index 2
    return sorted(samples)


def main():
    print("=" * 60)
    print("ADD SAMPLE TYPE RADIO OPTIONS TO ODR")
    print("=" * 60)
    
    # Get unique sample types
    print("\n1. Extracting unique sample types from CSV...")
    samples = get_unique_sample_types()
    print(f"   Found {len(samples)} unique sample types:")
    for s in samples:
        print(f"   - {s}")
    
    # Authenticate
    print("\n2. Authenticating...")
    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.authenticate()
    print("   Done!")
    
    # Get existing sample type options
    print("\n3. Checking existing sample type options in ODR...")
    ds = client.get_dataset(DATASET_UUID)
    existing_samples = set()
    for rec in ds.get("records", []):
        for field in rec.get("fields", []):
            if field.get("field_name") == "Sample Type":
                for val in field.get("values", []):
                    name = val.get("name")
                    if name:
                        existing_samples.add(name)
    
    print(f"   Existing options: {sorted(existing_samples)}")
    
    # Find missing sample types
    missing = sorted(set(samples) - existing_samples)
    if not missing:
        print("\n✅ All sample types already exist in ODR!")
        return
    
    print(f"\n4. Missing sample types to add ({len(missing)}):")
    for s in missing:
        print(f"   - {s}")
    
    # Confirm
    print(f"\n⚠️ This will create {len(missing)} temporary records to add these options.")
    if AUTO_CONFIRM:
        print("AUTO_CONFIRM=1 — proceeding without prompt.")
    else:
        response = input("Continue? (y/n): ")
        if response.lower() != "y":
            print("Cancelled.")
            return
    
    # Create records with each missing sample type
    print("\n5. Creating records with missing sample types...")
    created_records = []
    
    for sample in missing:
        print(f"   Adding: {sample}...")
        
        # Create record
        rec = client.create_record(DATASET_UUID)
        record_uuid = rec.get("record_uuid")
        
        # Add sample type - just use the name (ODR should create the option)
        rec["fields"] = [{
            "field_name": "Sample Type",
            "field_uuid": SAMPLE_TYPE_FIELD_UUID,
            "values": [{
                "name": sample,
                "selected": 1
            }]
        }]
        
        # Push
        try:
            client.push_record(rec)
            created_records.append(record_uuid)
            print(f"   ✅ Added '{sample}' (record {rec.get('record_name')})")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    print(f"\n============================================================")
    print(f"COMPLETE!")
    print(f"============================================================")
    print(f"\nCreated {len(created_records)} temporary records to add sample type options.")
    print(f"\nYou can now delete these records manually in ODR if desired.")
    print(f"The sample type options will remain available for future records.")


if __name__ == "__main__":
    main()
