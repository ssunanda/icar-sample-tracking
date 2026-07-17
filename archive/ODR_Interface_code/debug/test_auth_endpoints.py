"""Test different ODR API auth endpoints"""
import requests

endpoints = ['/login', '/auth', '/authenticate', '/user/login', '/access_token']
base = "https://odr.io/api/v4"
payload = {"username": "amshahid@ncsu.edu", "password": "qkh8fjd6adh*NPU!ekn"}

print("Testing various auth endpoints...")
for ep in endpoints:
    url = base + ep
    r = requests.post(url, json=payload)
    print(f"  {ep}: {r.status_code}")

# Also try without /api/v4 prefix
print("\nTrying without /api/v4...")
for ep in ['/api/login', '/api/token', '/login']:
    url = "https://odr.io" + ep
    r = requests.post(url, json=payload)
    print(f"  {ep}: {r.status_code}")
