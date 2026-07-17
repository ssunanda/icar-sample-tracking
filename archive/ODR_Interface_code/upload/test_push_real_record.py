"""
Push a REAL Record to ODR with Metadata + Data File
====================================================
This pushes: data/isotopic/magnetite/Pillinger_1999.csv
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "client"))
from ODR_API_Client import ODRAPIClient

# Configuration
BASE_URL = "https://www.odr.io/api/v4"
USERNAME = "amshahid@ncsu.edu"
PASSWORD = "qkh8fjd6adh*NPU!ekn"
DATASET_UUID = "063c0d3d4bd183ab0dda87c544ae"

# Real data file to upload (resolved relative to repo root)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_FILE = os.path.join(REPO_ROOT, "raw_main", "data", "isotopic", "magnetite", "Pillinger_1999.csv")

# Metadata from the file path
METADATA = {
    "Source ID": "Pillinger_1999",
    "Source Links": "https://doi.org/10.1126/science.285.5429.876",  # Example DOI
}

# Field UUIDs for this dataset
FIELD_UUIDS = {
    "Source ID": "98c0dc4db715d503abc93fa598f9",
    "Source Links": "cb24ce292d861629416b51c40aa0",
    "Source Citation": "0719c6187a235650b437bb742bf9",
    "Data File": "a65467babf8a1ac7e1d7319e3928",
}


def main():
    print("=" * 60)
    print("PUSH REAL RECORD TO ODR")
    print("=" * 60)
    print(f"\nData file: {os.path.basename(DATA_FILE)}")
    print(f"Type: isotopic | Sample: magnetite | Source: Pillinger_1999")
    
    # 1. Authenticate
    print("\n1. Authenticating...")
    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.authenticate()
    print("   Done!")
    
    # 2. Create record
    print("\n2. Creating new record...")
    new_record = client.create_record(DATASET_UUID)
    record_uuid = new_record.get("record_uuid")
    record_name = new_record.get("record_name")
    print(f"   Created: {record_name}")
    
    # 3. Add metadata
    print("\n3. Adding metadata...")
    new_record["fields"] = []
    for field_name, value in METADATA.items():
        new_record["fields"].append({
            "field_name": field_name,
            "field_uuid": FIELD_UUIDS[field_name],
            "value": value
        })
        print(f"   - {field_name}: {value}")
    
    # 4. Push metadata first
    print("\n4. Pushing metadata to ODR...")
    client.push_record(new_record)
    print("   Done!")
    
    # 5. Upload the actual data file
    print("\n5. Uploading data file...")
    if os.path.exists(DATA_FILE):
        client.upload_file(
            file_path=DATA_FILE,
            record_uuid=record_uuid,
            dataset_uuid=DATASET_UUID,
            template_field_uuid="",
            field_uuid=FIELD_UUIDS["Data File"],
            name=os.path.basename(DATA_FILE)
        )
        print(f"   Uploaded: {os.path.basename(DATA_FILE)}")
    else:
        print(f"   ERROR: File not found: {DATA_FILE}")
    
    # 6. Verify
    print("\n6. Verifying...")
    fetched = client.get_record(record_uuid)
    print("   Fields saved:")
    for f in fetched.get("fields", []):
        name = f.get("field_name")
        val = f.get("value")
        files = f.get("files", [])
        if val:
            print(f"   - {name}: {val}")
        if files:
            for file in files:
                print(f"   - {name}: {file.get('original_name')} ({file.get('file_size')} bytes)")
    
    print("\n" + "=" * 60)
    print("SUCCESS!")
    print("=" * 60)
    print(f"\nRecord Name: {record_name}")
    print(f"Record UUID: {record_uuid}")
    print(f"\nView at: https://odr.io/view/record/{record_uuid}")


if __name__ == "__main__":
    main()
