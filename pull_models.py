import requests
import json
import threading
import sys

servers = [
    "http://64.247.201.10:10565",
    "http://69.30.85.128:22021",
    "http://194.68.245.208:22082",
    "http://194.68.245.199:22041"
]

models = [
    "deepseek-r1:70b",
    "deepseek-r1:32b",
    "deepseek-r1:8b"
]

def pull_model(server, model):
    url = f"{server}/api/pull"
    print(f"Starting pull for {model} on {server}...")
    try:
        response = requests.post(url, json={"name": model}, stream=True)
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                status = data.get("status")
                if status == "success":
                    print(f"[SUCCESS] {model} on {server} is fully downloaded.")
                    return
                elif "error" in data:
                    print(f"[ERROR] {model} on {server}: {data['error']}")
                    return
    except Exception as e:
        print(f"[ERROR] Failed to connect to {server}: {e}")

def main():
    threads = []
    # Only pull 70b on the A100 (primary) and maybe 32b/8b on the rest, or just pull all on all.
    # To be safe and since A100 is primary, let's pull 70b on 64.247.201.10:10565
    # The others can pull 32b and 8b.
    # Actually, config.json maps everything to api_url or secondary_gpu. 
    # Let's just pull 70b on A100, and 32b/8b on all of them.
    for server in servers:
        models_to_pull = models if "64.247.201.10" in server else ["deepseek-r1:32b", "deepseek-r1:8b"]
        for model in models_to_pull:
            t = threading.Thread(target=pull_model, args=(server, model))
            threads.append(t)
            t.start()

    print("Initiated pulls in the background. Waiting for completion...")
    for t in threads:
        t.join()
    print("All pull requests finished.")

if __name__ == "__main__":
    main()
