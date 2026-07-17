"""Try different ways to get ODR JWT token"""
import requests

base = "https://odr.io"
creds = {"username": "amshahid@ncsu.edu", "password": "qkh8fjd6adh*NPU!ekn"}

print("Testing JWT token acquisition methods...\n")

# Try different endpoints
endpoints = [
    "/api/v4/token",
    "/api/v3/token",
    "/api/token",
    "/api/v4/jwt/token",
    "/api/v4/oauth/token",
    "/api/v4/auth/token",
    "/token",
    "/jwt/token",
]

for ep in endpoints:
    url = base + ep
    # Try POST with JSON
    r = requests.post(url, json=creds, timeout=10)
    if r.status_code == 200:
        print(f"✅ {ep} (JSON POST): {r.status_code}")
        try:
            print(f"   Response: {r.json()}")
        except:
            print(f"   Response: {r.text[:200]}")
    else:
        print(f"❌ {ep}: {r.status_code}")

print("\n\nTrying with different payloads on /api/v4/token...")
payloads = [
    ("_username/_password", {"_username": creds["username"], "_password": creds["password"]}),
    ("email/password", {"email": creds["username"], "password": creds["password"]}),
    ("user/pass", {"user": creds["username"], "pass": creds["password"]}),
]

for name, payload in payloads:
    r = requests.post(base + "/api/v4/token", json=payload, timeout=10)
    print(f"  {name}: {r.status_code}")
