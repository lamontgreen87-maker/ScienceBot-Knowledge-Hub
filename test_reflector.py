import sys
import os
import time

sys.path.insert(0, 'c:/continuous')

import json
from reflector import Reflector

if __name__ == "__main__":
    c_path = 'c:/continuous/config.json'
    with open(c_path, 'r') as f:
        c = json.load(f)
        
    r = Reflector(c_path, None)
    
    insight = "The root cause of the audit failure is that the simulation code is too simplistic and does not fully align with the research hypothesis or the required complexity standards. Specifically: Low Code Complexity."
    
    print("Triggering Creator Suggestion Phase...")
    creator_suggestion = r.consult_reasoner(
        question=(
            f"The recent swarm iteration generated this insight about agent failures: '{insight}'.\n"
            f"As a Senior AI Architect, provide exactly ONE concrete, technical recommendation "
            f"for the HUMAN DEVELOPER on how to improve this agentic framework's source code. "
            f"Direct your advice to the human creator. Be specific about which file/prompt/logic to change."
        ),
        context="Scientific research agent evaluating itself. You are giving advice to the human who wrote your code.",
        label="[CREATOR-SUGGESTION]"
    )
    
    print("\n--- DEEPSEEK ADVICE ---\n")
    print(creator_suggestion)
    print("\n-----------------------\n")
    
    suggestions_file = os.path.join(c['paths']['memory'], "CREATOR_SUGGESTIONS.md")
    with open(suggestions_file, 'a', encoding='utf-8') as f:
        f.write(
            f"## [CREATOR SUGGESTION] Iteration Manual - {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"**Context / Insight**: {insight}\n\n"
            f"**Agent's Structural Advice to You**:\n{creator_suggestion}\n\n"
            f"---\n\n"
        )
