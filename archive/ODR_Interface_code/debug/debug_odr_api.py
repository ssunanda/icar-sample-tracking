"""Debug ODR API response"""
from ODR_API_Client import ODRAPIClient

BASE_URL = "https://odr.io/api/v4"
USERNAME = "amshahid@ncsu.edu"
PASSWORD = "qkh8fjd6adh*NPU!ekn"

print("Testing ODR API...")
client = ODRAPIClient(BASE_URL, USERNAME, PASSWORD)

print("\n1. Authenticating...")
client.authenticate()
print("   Token:", client.headers.get("Authorization", "")[:50] + "...")

print("\n2. Testing get_record...")
try:
    rec = client.get_record("766979c91c7c4de40897d5d670f9")
    print("   Record name:", rec.get("record_name"))
except Exception as e:
    print(f"   Error: {e}")

print("\n3. Testing create_record...")
try:
    new_rec = client.create_record("063c0d3d4bd183ab0dda87c544ae")
    print("   Created:", new_rec.get("record_name"), new_rec.get("record_uuid"))
    
    # Add minimal metadata
    new_rec["fields"] = [{
        "field_name": "Source ID",
        "field_uuid": "98c0dc4db715d503abc93fa598f9",
        "value": "TEST_DEBUG"
    }]
    
    print("\n4. Testing push_record...")
    client.push_record(new_rec)
    print("   Push successful!")
    
    print(f"\n   View at: https://odr.io/view/record/{new_rec['record_uuid']}")
    
except Exception as e:
    print(f"   Error: {e}")
