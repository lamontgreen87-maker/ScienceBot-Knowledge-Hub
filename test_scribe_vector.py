import os
import json
import time
import sys

# Ensure current directory is in path
sys.path.append(os.getcwd())

from vector_memory import VectorMemory
from explorer import CuriosityEngine

def test_vector_recall():
    print("--- Verifying Vector Memory Upgrade (v2) ---")
    
    config = {
        "paths": {"memory": "memory_test", "discoveries": "discoveries_test"},
        "hardware": {
            "local_url": "http://localhost:11434/api/embeddings", 
            "embedding_model": "nomic-embed-text",
            "api_url": "http://localhost:11434/api/generate"
        },
        "research": {"use_ollama_embeddings": False}
    }
    
    if not os.path.exists("memory_test"): os.makedirs("memory_test")
    
    try:
        vm = VectorMemory(config)
        explorer = CuriosityEngine(config)
        
        # 1. Seed
        print("\n[STEP 1] Seeding...")
        vm.embed_research(
            topic="Kerr Metric Singularity",
            text="SUCCESS_TEXT",
            metadata={"type": "success"},
            is_failure=False
        )
        vm.embed_research(
            topic="Kerr Metric Substitution Error",
            text="FAILURE_TEXT",
            metadata={"type": "failure"},
            is_failure=True
        )
        
        # 2. Decompose Mock
        print("\n[STEP 2] Testing decompose_topic injection...")
        captured_prompt = []
        
        def mock_query(prompt, **kwargs):
            captured_prompt.append(prompt)
            return json.dumps({"vectors": [{"name": "V1", "area": "A1", "high_curiosity": False}]})
        
        explorer._query_llm = mock_query
        explorer.decompose_topic("Kerr Metric Optimization")
        
        if captured_prompt:
            p = captured_prompt[0]
            if "### SEMANTIC RECALL (PAST ATTEMPTS):" in p:
                print("SUCCESS: Recall header found.")
                if "SUCCESS_TEXT" in p: print("SUCCESS: Past success found.")
                if "FAILURE_TEXT" in p: print("SUCCESS: Past failure found.")
            else:
                print("FAILURE: Recall header missing.")
        else:
            print("FAILURE: No prompt captured.")

        # 3. Strategic Selection Mock
        print("\n[STEP 3] Testing strategic selection context...")
        captured_context = []
        def mock_consult(question, context=None, **kwargs):
            captured_context.append(context)
            return "New Topic"
        
        explorer.consult_reasoner = mock_consult
        explorer.strategic_topic_selection()
        
        if captured_context and captured_context[0]:
            ctx = captured_context[0]
            if "Recent Verified Discoveries (Vector Memory):" in ctx:
                print("SUCCESS: Vector context found in Strategic selection.")
            else:
                print("FAILURE: Vector context missing.")
        else:
            print("FAILURE: No context captured.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    test_vector_recall()
