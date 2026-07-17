"""
Simple test to upload one record with all metadata from CSV
"""
import pandas as pd
from pathlib import Path
from ODR_API_Client import ODRAPIClient

# Config
BASE_URL = "https://www.odr.io/api/v4"
USERNAME = "amshahid@ncsu.edu"
PASSWORD = "qkh8fjd6adh*NPU!ekn"
DATASET_UUID = "063c0d3d4bd183ab0dda87c544ae"
CSV_PATH = Path(r"C:\Users\abdul\Box\2021_SCOBI\ODR_data_release\raw_main\defs\all_raw_records.csv")
DATA_DIR = Path(r"c:\Users\abdul\Downloads\raw_main-selected\raw_main\data")

# Field UUIDs
FIELD_UUIDS = {
    "Data File": "a65467babf8a1ac7e1d7319e3928",
    "Data Type": "996f2f04be5e12bc6d251e54bb8f",
    "Source ID": "98c0dc4db715d503abc93fa598f9",
    "Class": "676b2e7658da32d4c518b3877401",
    "Subclass": "bcf6ab5a9b02de9e0594772f2c2a",
    "Sample Type": "423044bee60c5e83fcb7fbf1b713",
    "Notes": "adc43cecf7714687c865ca79f078",
}

print("=" * 60)
print("SIMPLE TEST - Upload One Record with Full Metadata")
print("=" * 60)

# Load metadata
print("\n1. Loading CSV metadata...")
df = pd.read_csv(CSV_PATH)
df = df.rename(columns={'#ID': 'id'})
df = df.set_index('id')
print(f"   Loaded {len(df)} records")

# Get test record
test_id = "table6-175R-1"
row = df.loc[test_id]
print(f"\n2. Metadata for {test_id}:")
print(f"   source: {row['source']}")
print(f"   sample: {row['sample']}")
print(f"   type: {row['type']}")
print(f"   units: {row['units']}")
print(f"   tags: {row['tags']}")
print(f"   methods: {row['methods']}")
print(f"   notes: {row['notes']}")

# Find data file
file_path = DATA_DIR / row['type'] / row['sample'] / row['source'] / f"{test_id}.csv"
print(f"\n3. Data file: {file_path}")
print(f"   Exists: {file_path.exists()}")

# Auth
print("\n4. Authenticating...")
client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
client.authenticate()
print("   Done!")

# Discover radio options
print("\n5. Discovering radio options...")
ds = client.get_dataset(DATASET_UUID)
radio_opts = {"Data Type": {}, "Sample Type": {}, "Class": {}, "Subclass": {}}
for rec in ds.get("records", []):
    for field in rec.get("fields", []):
        fname = field.get("field_name")
        if fname in radio_opts:
            for val in field.get("values", []):
                if val.get("name") and val.get("template_radio_option_uuid"):
                    radio_opts[fname][val["name"]] = val["template_radio_option_uuid"]

print(f"   Data Types: {list(radio_opts['Data Type'].keys())}")
print(f"   Sample Types: {list(radio_opts['Sample Type'].keys())}")
print(f"   Classes: {list(radio_opts['Class'].keys())}")

# Create record
print("\n6. Creating new record...")
rec = client.create_record(DATASET_UUID)
print(f"   Created: {rec.get('record_name')} ({rec.get('record_uuid')})")

# Build metadata fields
fields = []

# Source ID
fields.append({
    "field_name": "Source ID",
    "field_uuid": FIELD_UUIDS["Source ID"],
    "value": str(row['source'])
})

# Data Type
dtype = str(row['type']).capitalize()
if dtype in radio_opts["Data Type"]:
    fields.append({
        "field_name": "Data Type",
        "field_uuid": FIELD_UUIDS["Data Type"],
        "values": [{
            "template_radio_option_uuid": radio_opts["Data Type"][dtype],
            "name": dtype,
            "selected": 1
        }]
    })

# Sample Type
sample = str(row['sample'])
if sample in radio_opts["Sample Type"]:
    fields.append({
        "field_name": "Sample Type", 
        "field_uuid": FIELD_UUIDS["Sample Type"],
        "values": [{
            "template_radio_option_uuid": radio_opts["Sample Type"][sample],
            "name": sample,
            "selected": 1
        }]
    })

# Class
if "Non-Indicative" in radio_opts["Class"]:
    fields.append({
        "field_name": "Class",
        "field_uuid": FIELD_UUIDS["Class"],
        "values": [{
            "template_radio_option_uuid": radio_opts["Class"]["Non-Indicative"],
            "name": "Non-Indicative",
            "selected": 1
        }]
    })

# Notes - SKIPPED due to ShortVarchar limit (field length restriction)
# notes = f"Tags:{row['tags']} | Methods:{row['methods']} | Units:{row['units']}"
# notes = notes[:250]  # Truncate if too long
# fields.append({
#     "field_name": "Notes",
#     "field_uuid": FIELD_UUIDS["Notes"],
#     "value": notes
# })

print(f"\n7. Pushing {len(fields)} metadata fields...")
for f in fields:
    print(f"   - {f['field_name']}: {f.get('value', f.get('values', [{}])[0].get('name', '?'))}")

rec["fields"] = fields
client.push_record(rec)
print("   Done!")

# Upload file
print(f"\n8. Uploading file: {file_path.name}")
client.upload_file(
    file_path=str(file_path),
    record_uuid=rec["record_uuid"],
    dataset_uuid=DATASET_UUID,
    template_field_uuid="",
    field_uuid=FIELD_UUIDS["Data File"],
    name=file_path.name
)
print("   Done!")

print(f"\n" + "=" * 60)
print(f"SUCCESS! View at: https://www.odr.io/view/record/{rec['record_uuid']}")
print("=" * 60)
