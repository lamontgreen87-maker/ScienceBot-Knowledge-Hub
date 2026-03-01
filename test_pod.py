import requests
import json

urls = [
    "http://149.36.1.181:32218/api/tags",
    "http://149.36.1.181:32219/api/tags"
]

for url in urls:
    print(f"Checking {url}...")
    try:
        response = requests.get(url, timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:100]}")
    except Exception as e:
        print(f"  FAILED: {e}")
