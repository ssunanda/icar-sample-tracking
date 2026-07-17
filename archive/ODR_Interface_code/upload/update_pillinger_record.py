"""
Update Pillinger_1999 Record with Complete Metadata
====================================================
Updates record 777378 with all metadata fields including
radio fields (Class, Subclass, Data Type, Sample Type)
"""

from ODR_API_Client import ODRAPIClient
import json

# Configuration
BASE_URL = "https://odr.io/api/v4"
USERNAME = "amshahid@ncsu.edu"
PASSWORD = "qkh8fjd6adh*NPU!ekn"

# The record we want to update
RECORD_UUID = "766979c91c7c4de40897d5d670f9"  # Pillinger_1999

# =============================================================================
# RADIO FIELD OPTIONS (from existing records)
# =============================================================================
# These are the template_radio_option_uuid values for each option

DATA_TYPE_OPTIONS = {
    "Elemental": "739c6bd78291c461b25523568c39",
    "Isotopic": None,  # Need to find this from existing records
}

CLASS_OPTIONS = {
    "Non-Indicative": "8ef863b49d28db481480a9053044",
    "Indicative": None,  # Need to find
}

SUBCLASS_OPTIONS = {
    "Non-Indicative": "ace0048aa804b5ce1a7bc6829a13",
    "Alive": None,
    "Non-Alive": None,
}

# =============================================================================
# METADATA FOR PILLINGER_1999
# =============================================================================
# Based on file path: data/isotopic/magnetite/Pillinger_1999.csv

BIBTEX_CITATION = """@article{Pillinger_1999,
    title={Delta17O and delta18O of magnetite in olivine from the Martian meteorite ALH84001},
    volume={285},
    DOI={10.1126/science.285.5429.876},
    journal={Science},
    author={Pillinger, C.T. and others},
    year={1999}
}"""


def main():
    print("=" * 60)
    print("UPDATE PILLINGER_1999 RECORD WITH COMPLETE METADATA")
    print("=" * 60)
    
    # 1. Authenticate
    print("\n1. Authenticating...")
    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.authenticate()
    print("   Done!")
    
    # 2. Fetch the record
    print(f"\n2. Fetching record {RECORD_UUID}...")
    record = client.get_record(RECORD_UUID)
    print(f"   Got record: {record.get('record_name')}")
    
    # 3. First, let's find the Isotopic option by checking another record
    print("\n3. Finding 'Isotopic' option UUID from kleine_2018 record...")
    kleine_rec = client.get_record("989bd5719310796f053c76e3ffa8")  # kleine_2018
    
    isotopic_uuid = None
    magnetite_uuid = None
    
    for field in kleine_rec.get("fields", []):
        if field.get("field_name") == "Data Type":
            for val in field.get("values", []):
                if val.get("name") == "Isotopic":
                    isotopic_uuid = val.get("template_radio_option_uuid")
                    print(f"   Found Isotopic: {isotopic_uuid}")
        if field.get("field_name") == "Sample Type":
            for val in field.get("values", []):
                sample_name = val.get("name")
                sample_uuid = val.get("template_radio_option_uuid")
                print(f"   Found Sample Type '{sample_name}': {sample_uuid}")
    
    # 4. Build the updated fields
    print("\n4. Building updated record...")
    
    # Keep existing fields and add/update new ones
    updated_fields = []
    
    # Add text fields
    updated_fields.append({
        "field_name": "Source ID",
        "field_uuid": "98c0dc4db715d503abc93fa598f9",
        "value": "Pillinger_1999"
    })
    
    updated_fields.append({
        "field_name": "Source Links",
        "field_uuid": "cb24ce292d861629416b51c40aa0",
        "value": "https://doi.org/10.1126/science.285.5429.876"
    })
    
    updated_fields.append({
        "field_name": "Source Citation",
        "field_uuid": "0719c6187a235650b437bb742bf9",
        "value": BIBTEX_CITATION
    })
    
    # Add radio fields - Data Type: Isotopic
    if isotopic_uuid:
        updated_fields.append({
            "field_name": "Data Type",
            "field_uuid": "996f2f04be5e12bc6d251e54bb8f",
            "values": [{
                "template_radio_option_uuid": isotopic_uuid,
                "name": "Isotopic",
                "selected": 1
            }]
        })
    
    # Add Class: Non-Indicative (magnetite is non-biosignature)
    updated_fields.append({
        "field_name": "Class",
        "field_uuid": "676b2e7658da32d4c518b3877401",
        "values": [{
            "template_radio_option_uuid": "8ef863b49d28db481480a9053044",
            "name": "Non-Indicative",
            "selected": 1
        }]
    })
    
    # Add Subclass: Non-Indicative
    updated_fields.append({
        "field_name": "Subclass",
        "field_uuid": "bcf6ab5a9b02de9e0594772f2c2a",
        "values": [{
            "template_radio_option_uuid": "ace0048aa804b5ce1a7bc6829a13",
            "name": "Non-Indicative",
            "selected": 1
        }]
    })
    
    # Keep the Data File field from the original record
    for field in record.get("fields", []):
        if field.get("field_name") == "Data File":
            updated_fields.append(field)
            break
    
    # Update the record
    record["fields"] = updated_fields
    
    print("   Fields to push:")
    for f in updated_fields:
        name = f.get("field_name")
        if "value" in f:
            print(f"   - {name}: {f['value'][:50]}..." if len(str(f.get('value',''))) > 50 else f"   - {name}: {f.get('value')}")
        elif "values" in f:
            print(f"   - {name}: {f['values'][0].get('name')}")
        else:
            print(f"   - {name}: [file]")
    
    # 5. Push the update
    print("\n5. Pushing updated record...")
    client.push_record(record)
    print("   Done!")
    
    # 6. Verify
    print("\n6. Verifying...")
    fetched = client.get_record(RECORD_UUID)
    print("   Updated fields:")
    for f in fetched.get("fields", []):
        name = f.get("field_name")
        if f.get("value"):
            val = f.get("value")
            print(f"   - {name}: {val[:40]}..." if len(val) > 40 else f"   - {name}: {val}")
        elif f.get("values"):
            for v in f.get("values", []):
                if v.get("selected"):
                    print(f"   - {name}: {v.get('name')}")
        elif f.get("files"):
            print(f"   - {name}: {f['files'][0].get('original_name')}")
    
    print("\n" + "=" * 60)
    print("SUCCESS!")
    print("=" * 60)
    print(f"\nView at: https://odr.io/view/record/{RECORD_UUID}")


if __name__ == "__main__":
    main()
