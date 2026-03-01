import requests
import json
import os
import sys

def get_gpu_telemetry(url):
    """Queries Ollama /api/ps to get VRAM usage of loaded models."""
    try:
        target = url.replace("/api/generate", "/api/ps")
        if "/api/ps" not in target:
            target = url.rstrip('/') + "/api/ps"
            
        response = requests.get(target, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error querying {url}: {e}")
    return None

def calculate_swarm_expansion(config_path="config.json"):
    if not os.path.exists(config_path):
        return

    with open(config_path, 'r') as f:
        config = json.load(f)

    api_url = config['hardware'].get('api_url')
    if not api_url: return

    telemetry = get_gpu_telemetry(api_url)
    if not telemetry: return

    # In multi-GPU Ollama nodes, size_vram can be > card capacity. 
    # We look at the largest reported size_vram as a baseline for Total Capacity.
    max_detected_card_vram = 0
    loaded_vram_sum = 0
    
    models = telemetry.get('models', [])
    for model in models:
        vram = model.get('size_vram', 0)
        loaded_vram_sum += vram
        if vram > max_detected_card_vram:
            max_detected_card_vram = vram

    # Heuristic: Total Capacity is likely the sum of card capacities.
    # If we see 169GB total loaded, we are likely on a 192GB or 256GB node.
    TOTAL_CAPACITY_GB = (loaded_vram_sum / 1e9) + 12 # Start with loaded + safety
    
    # Snap to nearest common GPU cluster size
    if TOTAL_CAPACITY_GB > 160:
        TOTAL_CAPACITY_GB = 196 # High-tier cluster
    elif TOTAL_CAPACITY_GB > 80:
        TOTAL_CAPACITY_GB = 160 # assume 2x 80GB
    elif TOTAL_CAPACITY_GB > 48:
        TOTAL_CAPACITY_GB = 80  # assume 1x 80GB
    elif TOTAL_CAPACITY_GB > 24:
        TOTAL_CAPACITY_GB = 48  # assume 2x 24GB or 1x 48GB
    else:
        TOTAL_CAPACITY_GB = 24  # assume 1x 24GB

    # For high-capacity machines (192GB+), we can be more aggressive.
    if TOTAL_CAPACITY_GB >= 192:
        HEADROOM_GB = 6.0
        WORKER_COST_GB = 2.5 # Very aggressive KV cache estimation for high-RAM nodes
    else:
        HEADROOM_GB = 8.0
        WORKER_COST_GB = 5.5 
    
    available_vram_gb = TOTAL_CAPACITY_GB - (loaded_vram_sum / 1e9) - HEADROOM_GB
    
    recommended_workers = int(available_vram_gb // WORKER_COST_GB)
    # Clip to 2-12 range
    recommended_workers = max(2, min(recommended_workers, config['hardware'].get('turbo_workers', 12)))

    current_workers = config['hardware'].get('max_swarm_workers', 4)
    
    # Check for offloading lag (if size > size_vram for any model)
    lag_detected = False
    for model in models:
        if model.get('size', 0) > model.get('size_vram', 0):
            lag_detected = True
            break
            
    if lag_detected:
        print("[AUTOSCALER] Model offloading detected! Downscaling for stability.")
        recommended_workers = 2

    print(f"[AUTOSCALER] Total VRAM Capacity: {TOTAL_CAPACITY_GB} GB")
    print(f"[AUTOSCALER] Loaded Models: {len(models)}")
    print(f"[AUTOSCALER] Available Headroom: {available_vram_gb:.2f} GB")
    print(f"[AUTOSCALER] Recommendation: {recommended_workers} workers (Current: {current_workers})")

    if recommended_workers != current_workers:
        config['hardware']['max_swarm_workers'] = recommended_workers
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"[AUTOSCALER] Config UPDATED.")
    else:
        print(f"[AUTOSCALER] No change required.")

if __name__ == "__main__":
    calculate_swarm_expansion()
