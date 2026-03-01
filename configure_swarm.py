import json
import os
import sys

def get_gpu_info():
    """Probes NVIDIA GPUs using torch for VRAM and count."""
    try:
        import torch
        if not torch.cuda.is_available():
            return None
        
        gpus = []
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            gpus.append({
                "id": i,
                "name": props.name,
                "vram_gb": round(props.total_memory / (1024**3), 2)
            })
        return gpus
    except ImportError:
        return None
    except Exception as e:
        print(f"[ERROR] GPU Probing failed: {e}")
        return None

def configure():
    print("--- Swarm Hardware Configurator ---")
    
    config_path = "config.json"
    if not os.path.exists(config_path):
        print(f"[FATAL] {config_path} not found.")
        return

    with open(config_path, 'r') as f:
        config = json.load(f)

    gpus = get_gpu_info()
    
    if not gpus:
        print("[WARNING] No local NVIDIA GPUs detected via torch. Falling back to default worker count.")
        workers = 2
        gpu_count = 1
    else:
        gpu_count = len(gpus)
        total_vram = sum(g[1] for g in [(g['id'], g['vram_gb']) for g in gpus])
        print(f"[INFO] Detected {gpu_count} GPU(s):")
        for g in gpus:
            print(f"  - GPU {g['id']}: {g['name']} ({g['vram_gb']} GB)")

        # Heuristic: 1 worker per 24GB of VRAM (conservative for 70B models)
        # If we have 2x 32GB (5090s) or similar, we should aim for 2-4 workers.
        # But if we split models across cards, we can be more aggressive.
        workers = max(2, int(total_vram / 20))
        print(f"[CONFIG] Calculating optimal swarm size: {workers} workers.")

    # Apply configuration
    config['hardware']['max_swarm_workers'] = workers
    
    # If 2+ GPUs, split the work
    if gpu_count > 1:
        print("[CONFIG] Multi-GPU detected. Splitting Explorer and Lab backends.")
        # We assume local execution on ports 11434 and 11435 based on resilient_swarm.sh
        config['hardware']['api_url'] = "http://localhost:11434/api/generate"
        config['hardware']['secondary_gpu'] = "http://localhost:11435/api/generate"
        
        config['hardware']['gpu_mapping'] = {
            "explorer": "secondary_gpu", # Strategic (DeepSeek)
            "lab": "api_url",            # Execution (Llama/Qwen)
            "critic": "secondary_gpu",   # Auditing (DeepSeek)
            "reflector": "secondary_gpu",# Reflection (DeepSeek)
            "math_engine": "api_url"      # Calculation (Qwen)
        }
    else:
        print("[CONFIG] Single GPU mode. Resetting mapping to primary API.")
        # Ensure mapping points to the same card
        for key in config['hardware']['gpu_mapping']:
            config['hardware']['gpu_mapping'][key] = "api_url"

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    print(f"\n[SUCCESS] Updated {config_path} with {workers} workers and dual-GPU mapping.")

if __name__ == "__main__":
    configure()
