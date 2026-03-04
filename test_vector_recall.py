import json
import os
from agent import ScienceBot

def test_recall():
    print("--- Testing ChromaDB Recall ---")
    bot = ScienceBot(config_path="config.json")
    
    # Test query
    query = "Black Hole Spacetime Curvature"
    print(f"Querying for topics similar to: '{query}'")
    
    results = bot.get_past_topics(query=query, n=5)
    
    print(f"Top {len(results)} matches found:")
    for i, res in enumerate(results):
        print(f"  {i+1}. {res}")
    
    if not results:
        print("  FAILED: No results returned.")
    else:
        print("  SUCCESS: Semantic recall verified.")
    print("-------------------------------")

if __name__ == "__main__":
    test_recall()
