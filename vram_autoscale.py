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

    # 1. Aggregate unique GPU URLs (Multi-Port Support)
    urls = set()
    if config['hardware'].get('api_url'): urls.add(config['hardware']['api_url'])
    if config['hardware'].get('secondary_gpu'): urls.add(config['hardware']['secondary_gpu'])
    # Extract from mapping
    mapping = config['hardware'].get('gpu_mapping', {})
    for target in mapping.values():
        val = config['hardware'].get(target)
        if val: urls.add(val)
    
    total_loaded_vram = 0
    all_models = []
    
    for url in urls:
        telemetry = get_gpu_telemetry(url)
        if telemetry:
            models = telemetry.get('models', [])
            all_models.extend(models)
            for model in models:
                total_loaded_vram += model.get('size_vram', 0)

    # 2. Capacity Detection (Override vs Heuristic)
    # Forced override from config (Priority 1)
    TOTAL_CAPACITY_GB = config['hardware'].get('vram_capacity_gb')
    
    if not TOTAL_CAPACITY_GB:
        # Heuristic: Start with loaded + safety buffer (Priority 2)
        detected_sum_gb = (total_loaded_vram / 1e9)
        # Snap to nearest common GPU cluster size
        if detected_sum_gb > 280:
            TOTAL_CAPACITY_GB = 320 # 4x A100-80GB or similar
        elif detected_sum_gb > 240:
            TOTAL_CAPACITY_GB = 288 # 3x RTX 6000 ADA (96GB each)
        elif detected_sum_gb > 200:
            TOTAL_CAPACITY_GB = 256 # 8x 32GB or 4x 64GB
        elif detected_sum_gb > 180:
            TOTAL_CAPACITY_GB = 196 # High-tier cluster
        elif detected_sum_gb > 150:
            TOTAL_CAPACITY_GB = 192 # 4x A100-40GB or 8x 24GB
        elif detected_sum_gb > 80:
            TOTAL_CAPACITY_GB = 160 # 2x 80GB
        elif detected_sum_gb > 48:
            TOTAL_CAPACITY_GB = 80  # 1x 80GB
        elif detected_sum_gb > 24:
            TOTAL_CAPACITY_GB = 48  # 2x 24GB or 1x 48GB
        else:
            TOTAL_CAPACITY_GB = 24  # 1x 24GB
            if detected_sum_gb > 12: TOTAL_CAPACITY_GB = 48 # Edge case

    # 3. Scaling Logic (Context windows are the primary cost on high-capacity nodes)
    HEADROOM_GB = 25.0     # More headroom for the 397B MoE model to hydrate
    WORKER_COST_GB = 18.0   # Qwen 3.5-27B / QwQ-32B cost (approx 15-18GB each)
    
    available_vram_gb = TOTAL_CAPACITY_GB - (total_loaded_vram / 1e9) - HEADROOM_GB
    
    recommended_workers = int(available_vram_gb // WORKER_COST_GB)
    # Clip to 2-32 range for high-capacity clusters
    max_cap = config['hardware'].get('turbo_workers', 24)
    recommended_workers = max(2, min(recommended_workers, max_cap))

    current_workers = config['hardware'].get('max_swarm_workers', 4)
    
    # Also scale the Fast Lane (8B researchers)
    current_fast_lane = config['hardware'].get('fast_lane_concurrency', 4)
    recommended_fast_lane = max(4, int(recommended_workers // 3))
    
    # Check for offloading lag
    lag_detected = any(m.get('size', 0) > m.get('size_vram', 0) for m in all_models)
            
    if lag_detected:
        print("[AUTOSCALER] Model offloading detected! Downscaling for stability.")
        recommended_workers = 2

    print(f"[AUTOSCALER] Total VRAM Capacity: {TOTAL_CAPACITY_GB} GB")
    print(f"[AUTOSCALER] Loaded Models: {len(all_models)}")
    print(f"[AUTOSCALER] Available Headroom: {available_vram_gb:.2f} GB")
    print(f"[AUTOSCALER] Recommendation: {recommended_workers} workers (Current: {current_workers})")

    if recommended_workers != current_workers or recommended_fast_lane != current_fast_lane:
        config['hardware']['max_swarm_workers'] = recommended_workers
        config['hardware']['fast_lane_concurrency'] = recommended_fast_lane
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"[AUTOSCALER] Config UPDATED: {recommended_workers} workers, {recommended_fast_lane} fast-lanes.")
    else:
        print(f"[AUTOSCALER] No change required.")

if __name__ == "__main__":
    calculate_swarm_expansion()
