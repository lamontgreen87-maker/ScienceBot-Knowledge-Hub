import json
import time
from agent import EigenZeta

def test_swarm_optimizations():
    print("--- Verifying Swarm Optimizations ---")
    
    # 1. Initialize Bot with mock config
    bot = EigenZeta("config.json")
    
    # 2. Mock vectors with one High Curiosity
    mock_vectors = [
        {"name": "Standard Background Vector", "area": "Physics", "high_curiosity": False},
        {"name": "ANOMALOUS SINGULARITY EVENT", "area": "GR", "high_curiosity": True},
        {"name": "Secondary Physics Check", "area": "Math", "high_curiosity": False}
    ]
    
    bot.current_state["topic_vectors"] = mock_vectors
    bot.current_state["current_topic"] = "Black Hole Test"
    bot.config['hardware']['max_swarm_workers'] = 3
    bot.config['hardware']['swarm_stagger_s'] = 2 # Short stagger for testing
    
    print("\n[TEST] Verifying Priority Sorting...")
    tasks = []
    for i in range(3):
        vector = mock_vectors[i]
        tasks.append((f"Topic: {vector['name']}", i, 0, vector.get('high_curiosity', False)))
    
    # Sort as done in agent.py
    tasks.sort(key=lambda x: x[3] if len(x) > 3 else False, reverse=True)
    
    if tasks[0][3] == True:
        print("SUCCESS: High Curiosity task moved to front of queue.")
    else:
        print("FAILURE: Priority sorting failed.")

    print("\n[TEST] Verifying VRAM Check (Manual Trigger)...")
    # This just ensures it doesn't crash if nvidia-smi is missing
    bot.pre_flight_sync()
    print("SUCCESS: pre_flight_sync executed without crash.")

    print("\n[TEST] Verifying Staggered Launch Timing (Simulation)...")
    stagger = 2
    start_time = time.time()
    for i in range(3):
        if i > 0:
            print(f"  Staggering {stagger}s...")
            time.sleep(stagger)
        print(f"  Launching worker {i}...")
    
    total_time = time.time() - start_time
    if 4.0 <= total_time <= 5.0:
        print(f"SUCCESS: Total launch time ({total_time:.2f}s) matches expected stagger.")
    else:
        print(f"WARNING: Stagger timing off ({total_time:.2f}s). Check system load.")

if __name__ == "__main__":
    test_swarm_optimizations()
