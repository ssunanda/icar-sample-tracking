"""
Test Script: Push a Record with Metadata to ODR
================================================
Final working version - uses only confirmed text fields.
"""

from ODR_API_Client import ODRAPIClient

# Configuration
BASE_URL = "https://odr.io/api/v4"
USERNAME = "amshahid@ncsu.edu"
PASSWORD = "qkh8fjd6adh*NPU!ekn"
DATASET_UUID = "063c0d3d4bd183ab0dda87c544ae"

def main():
    print("=" * 60)
    print("ODR RECORD PUSH TEST")
    print("=" * 60)
    
    # Authenticate
    print("\n1. Authenticating...")
    client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)
    client.authenticate()
    print("   Done!")
    
    # Create record
    print("\n2. Creating new record...")
    new_record = client.create_record(DATASET_UUID)
    record_uuid = new_record.get("record_uuid")
    record_name = new_record.get("record_name")
    print(f"   Created: {record_name} (UUID: {record_uuid})")
    
    # Add metadata fields
    print("\n3. Adding metadata fields...")
    new_record["fields"] = [
        {
            "field_name": "Source ID",
            "field_uuid": "98c0dc4db715d503abc93fa598f9",
            "value": "TEST_API_FINAL"
        },
        {
            "field_name": "Source Links",
            "field_uuid": "cb24ce292d861629416b51c40aa0",
            "value": "https://example.com/test"
        },
    ]
    print("   - Source ID: TEST_API_FINAL")
    print("   - Source Links: https://example.com/test")
    
    # Push to ODR
    print("\n4. Pushing record to ODR...")
    client.push_record(new_record)
    print("   Success!")
    
    # Verify
    print("\n5. Verifying...")
    fetched = client.get_record(record_uuid)
    print("   Record verified on ODR!")
    print("\n   Saved fields:")
    for f in fetched.get("fields", []):
        val = f.get("value")
        if val:
            print(f"   - {f.get('field_name')}: {val}")
    
    print("\n" + "=" * 60)
    print("SUCCESS!")
    print("=" * 60)
    print(f"\nView your record at:")
    print(f"https://odr.io/view/record/{record_uuid}")


if __name__ == "__main__":
    main()
