
import json
import os
from unittest import mock
from agent import ScienceBot

# Mock UI
class MockUI:
    def print_log(self, msg): print(f"[MOCK-UI] {msg}")
    def set_status(self, status): print(f"[MOCK-UI-STATUS] {status}")

def test_study_loop():
    print("--- Setting up ScienceBot with Mocks ---")
    
    # Patch ScienceBot to prevent real init effects (like lock files)
    with mock.patch('agent.ScienceBot.__init__', return_value=None):
        bot = ScienceBot()
        bot.config = {
            "hardware": {"api_url": "http://mock-api", "large_model": "mock-model"},
            "research": {"study_loop_count": 2},
            "paths": {"memory": "memory/"}
        }
        bot.ui = MockUI()
        bot.current_state = {}
        
        # Manually initialize mocked components
        bot.searcher = mock.Mock()
        bot.explorer = mock.Mock()
        bot.lab = mock.Mock()
        bot.reflector = mock.Mock()
        bot.auditor = mock.Mock()
        bot.reflector.get_micro_sleep_lessons.return_value = "Prior Knowledge"
        bot.auditor.consult_reasoner.return_value = "Pre-validated"
        
        # Configure behavior
        bot.searcher.contemplate.return_value = "Initial Research Brief"
        bot.explorer.form_questions.return_value = {"selected_question": "Does math work?"}
        bot.lab.run_probe.return_value = "Probe Result: Math works."
        bot.searcher.deepen_research.return_value = "Final Research Brief with Probe Data"
        
        print("--- Executing process_single_hypothesis ---")
        bot.process_single_hypothesis("Quantum Friction", 0, 1)
        
        # Verify calls
        print("\n--- Verifying Component Interactions ---")
        print(f"Contemplate called: {bot.searcher.contemplate.called}")
        print(f"Form Questions called count: {bot.explorer.form_questions.call_count}")
        print(f"Run Probe called: {bot.lab.run_probe.called}")
        print(f"Deepen Research called: {bot.searcher.deepen_research.called}")
        
        if bot.searcher.deepen_research.call_count == 1 and bot.lab.run_probe.call_count == 1:
            print("\nSUCCESS: ScienceBot correctly executed exactly 1 deep-dive round (Loop count 2).")
        else:
            print(f"\nFAILURE: Component call counts incorrect. Probes: {bot.lab.run_probe.call_count}, Deepen: {bot.searcher.deepen_research.call_count}")

if __name__ == "__main__":
    test_study_loop()
