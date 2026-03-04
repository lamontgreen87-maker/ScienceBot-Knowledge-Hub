import os
import json
import time
from vector_memory import VectorMemory

def migrate():
    # Load config to get paths
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    vm = VectorMemory(config)
    
    print("--- Starting Migration to ChromaDB ---")
    
    # 1. Migrate Discoveries
    discoveries_dir = config['paths']['discoveries']
    success_count = 0
    if os.path.exists(discoveries_dir):
        print(f"Scanning discoveries in {discoveries_dir}...")
        for root, dirs, files in os.walk(discoveries_dir):
            for file in files:
                if file.endswith(".json"):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            data = json.load(f)
                        
                        hyp = data.get('hypothesis', {})
                        topic = hyp.get('topic', 'Unknown')
                        text = f"Hypothesis: {hyp.get('hypothesis', '')}\nBlueprint: {hyp.get('mathematical_blueprint', '')}"
                        metadata = {
                            "field": hyp.get('field', 'general'),
                            "timestamp": data.get('timestamp', time.time())
                        }
                        
                        if vm.embed_research(topic, text, metadata=metadata, is_failure=False):
                            success_count += 1
                            if success_count % 10 == 0:
                                print(f"  Embedded {success_count} discoveries...")
                    except Exception as e:
                        print(f"  Failed to process {file}: {e}")
    
    print(f"Total discoveries migrated: {success_count}")
    
    # 2. Migrate Failures
    failure_log = os.path.join(config['paths']['memory'], "failures.json")
    failure_count = 0
    if os.path.exists(failure_log):
        print(f"Scanning failures in {failure_log}...")
        try:
            with open(failure_log, 'r', encoding='utf-8', errors='ignore') as f:
                failures = json.load(f)
            
            for fv in failures:
                topic = fv.get('topic', 'Unknown')
                data = fv.get('data', {}) or {}
                if not isinstance(data, dict): data = {}
                
                hyp = data.get('hypothesis', {}) or {}
                text = f"Reason: {fv.get('audit_reason')}\nHypothesis: {hyp.get('hypothesis', 'N/A')}"
                
                metadata = {
                    "audit_reason": str(fv.get('audit_reason', ''))[:200],
                    "timestamp": fv.get('timestamp', time.time())
                }
                
                if vm.embed_research(topic, text, metadata=metadata, is_failure=True):
                    failure_count += 1
                    if failure_count % 10 == 0:
                        print(f"  Embedded {failure_count} failures...")
        except Exception as e:
            print(f"  Failed to process failures.json: {e}")
            
    print(f"Total failures migrated: {failure_count}")
    print("--- Migration Complete ---")

if __name__ == "__main__":
    migrate()
