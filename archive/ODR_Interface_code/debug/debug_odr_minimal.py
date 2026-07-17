"""Debug ODR API response - minimal test"""
import requests

BASE_URL = "https://odr.io/api/v4"
USERNAME = "amshahid@ncsu.edu"
PASSWORD = "qkh8fjd6adh*NPU!ekn"

print("1. Testing auth endpoint directly...")
auth_url = f"{BASE_URL}/auth"
resp = requests.post(auth_url, json={"username": USERNAME, "password": PASSWORD})
print(f"   Status: {resp.status_code}")
print(f"   Content-Type: {resp.headers.get('Content-Type', 'unknown')}")

if resp.status_code == 200:
    try:
        data = resp.json()
        token = data.get("token", "")
        print(f"   Token: {token[:30]}..." if token else "   No token!")
        
        print("\n2. Testing get dataset...")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        ds_url = f"{BASE_URL}/dataset/063c0d3d4bd183ab0dda87c544ae"
        ds_resp = requests.get(ds_url, headers=headers, timeout=30)
        print(f"   Status: {ds_resp.status_code}")
        print(f"   Content-Type: {ds_resp.headers.get('Content-Type', 'unknown')}")
        
        if ds_resp.status_code == 200:
            ds_data = ds_resp.json()
            print(f"   Records: {ds_data.get('count', 0)}")
            print("   First 3 sample types found:")
            sample_types = set()
            for rec in ds_data.get("records", [])[:10]:
                for f in rec.get("fields", []):
                    if f.get("field_name") == "Sample Type":
                        for v in f.get("values", []):
                            if v.get("name"):
                                sample_types.add(v.get("name"))
            for st in sorted(sample_types)[:5]:
                print(f"      - {st}")
        else:
            print(f"   Error: {ds_resp.text[:200]}")
            
    except Exception as e:
        print(f"   JSON error: {e}")
        print(f"   Raw (first 500 chars): {resp.text[:500]}")
else:
    print(f"   Auth failed! Response: {resp.text[:500]}")
