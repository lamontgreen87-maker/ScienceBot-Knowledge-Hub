import json
from vector_memory import VectorMemory

def test_vm():
    print("--- Directly Testing VectorMemory ---")
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    vm = VectorMemory(config)
    
    query = "Black Hole Spacetime Curvature"
    print(f"Querying for: '{query}'")
    
    matches = vm.query_past_research(query, n_results=3)
    
    print(f"Found {len(matches)} matches:")
    for i, m in enumerate(matches):
        print(f"  {i+1}. Topic: {m['topic']} ({m['type']})")
        # print(f"     Content: {m['content'][:100]}...")
    
    if len(matches) > 0:
        print("--- SUCCESS: Vector Retrieval Verified ---")
    else:
        print("--- FAILED: No results returned ---")

if __name__ == "__main__":
    test_vm()
