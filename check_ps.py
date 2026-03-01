import requests
import json

base_url = "http://157.157.221.30:60471"
try:
    r = requests.get(f"{base_url}/api/ps")
    ps = r.json()
    models = ps.get("models", [])
    if not models:
        print("No models loaded.")
    else:
        for m in models:
            name = m.get("name")
            vram = m.get("size_vram", 0) / 1e9
            total = m.get("size", 0) / 1e9
            print(f"Model: {name}")
            print(f"  VRAM: {vram:.2f} GB")
            print(f"  Total: {total:.2f} GB")
            print(f"  % in VRAM: {(vram/total)*100:.1f}%")
except Exception as e:
    print(f"Error: {e}")
