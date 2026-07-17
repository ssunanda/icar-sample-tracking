"""Test ODR session-based authentication"""
import requests

# Create a session to maintain cookies
session = requests.Session()

# Try form-based login
print("1. Testing session-based login...")
login_url = "https://odr.io/login"

# First get the login page to get CSRF token if needed
r1 = session.get(login_url)
print(f"   GET login: {r1.status_code}")
print(f"   Cookies after GET: {dict(session.cookies)}")

# Now POST credentials
login_data = {
    "username": "amshahid@ncsu.edu", 
    "password": "qkh8fjd6adh*NPU!ekn"
}
r2 = session.post(login_url, data=login_data, allow_redirects=True)
print(f"   POST login: {r2.status_code}")
print(f"   Cookies after POST: {dict(session.cookies)}")
print(f"   Final URL: {r2.url}")

# Now try to access API endpoint with session
print("\n2. Testing API access with session cookies...")
api_url = "https://odr.io/api/v4/dataset/063c0d3d4bd183ab0dda87c544ae"
r3 = session.get(api_url, timeout=30)
print(f"   GET dataset: {r3.status_code}")
print(f"   Content-Type: {r3.headers.get('Content-Type')}")

if r3.status_code == 200:
    try:
        data = r3.json()
        print(f"   ✅ SUCCESS! Records: {data.get('count', 0)}")
    except:
        print(f"   Response (first 300): {r3.text[:300]}")
else:
    print(f"   Response (first 300): {r3.text[:300]}")
