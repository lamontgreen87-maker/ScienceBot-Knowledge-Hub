import requests
import time
import json
import sys

# The endpoint you provided
API_URL = "http://38.147.83.25:31276/api/tags"

def monitor():
    print(f"--- Monitoring Downloads on {API_URL} ---")
    print("Pre-pulling check... (Pulse every 5s)")
    
    last_models = set()
    
    while True:
        try:
            response = requests.get(API_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                
                if not models:
                    print(f"[{time.strftime('%H:%M:%S')}] No models fully downloaded yet. Still pulling...")
                else:
                    for m in models:
                        name = m.get('name')
                        size_gb = m.get('size', 0) / (1024**3)
                        if name not in last_models:
                            print(f"--- [COMPLETE] Model Ready: {name} ({size_gb:.2f} GB) ---")
                            last_models.add(name)
            else:
                print(f"Error: Server returned {response.status_code}")
                
        except Exception as e:
            print(f"Connection Error: {e}")
            
        time.sleep(10)

if __name__ == "__main__":
    monitor()
