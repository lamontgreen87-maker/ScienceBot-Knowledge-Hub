
import json
import os
import sys
import time

# Mock Display to avoid UI issues in scratch script
class MockUI:
    def print_log(self, msg):
        print(f"[LOG] {msg}")
    def set_status(self, msg):
        print(f"[STATUS] {msg}")
    def print_chat(self, role, msg):
        print(f"[{role}] {msg}")
    def print_study_conclusion(self, topic, summary):
        print(f"[STUDY] {topic}: {summary}")
    def shutdown(self):
        print("[SYSTEM] Shutdown.")

from agent import ScienceBot

def run_manual_audit():
    print("=== STARTING MANUAL SCIENCE AUDIT ===")
    ui = MockUI()
    bot = ScienceBot()
    bot.ui = ui
    
    # 1. Science Integrity Audit
    bot.science_integrity_audit()
    
    # 2. Reflector Dream Phase
    print("\n=== STARTING DREAM PHASE (REFLECTION) ===")
    insight = bot.reflector.reflect()
    print(f"\n[INSIGHT] {insight}")
    
    # 3. Method Advisor Logic (Creator Advice)
    print("\n=== GENERATING CREATOR ADVISE ===")
    failures = bot._safe_load_json(os.path.join(bot.config['paths']['memory'], 'failures.json'), default=[])
    discoveries_dir = bot.config['paths']['discoveries']
    # Recursive count for subdirectories
    disc_count = sum([len(files) for r, d, files in os.walk(discoveries_dir) if any(f.endswith('.json') for f in files)])
    
    fail_types = {}
    for fv in failures[-30:]:
        rt = fv.get('audit_reason', 'unknown')[:100]
        fail_types[rt] = fail_types.get(rt, 0) + 1
    top_fails = sorted(fail_types.items(), key=lambda x: -x[1])[:3]
    
    current_iter = bot.current_state.get('iteration_count', 0)
    
    advice = bot.reflector.consult_reasoner(
        question=(
            f"After {current_iter} iterations, we have {disc_count} discoveries and {len(failures)} failures. "
            f"Most frequent failure modes: {top_fails}. "
            "As the project's lead AI Architect, provide ONE high-level strategic recommendation "
            "for the human developer on how to improve the framework's reliability or scientific depth. "
            "Write it directly to the human 'Creator' as actionable advice."
        ),
        context="Full system audit and strategic review.",
        label="[AUDIT-ADVISOR]"
    )
    
    if advice:
        advice_md = os.path.join(bot.config['paths']['memory'], "..", "CREATOR_ADVICE.md")
        with open(advice_md, 'a', encoding='utf-8') as f:
            f.write(f"\n## [MANUAL AUDIT ADVICE] {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{advice}\n\n---\n")
        print(f"\n[ADVICE] Strategy updated in CREATOR_ADVICE.md")
    
    print("\n=== AUDIT COMPLETE ===")

if __name__ == "__main__":
    run_manual_audit()
