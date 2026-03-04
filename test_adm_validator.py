import sys
import unittest
from unittest.mock import MagicMock
import json

# Add current directory to path
import os
sys.path.append(os.getcwd())

from physics_validator import PhysicsValidator
from critic import Auditor

class TestADMValidator(unittest.TestCase):
    def setUp(self):
        self.config = {
            "hardware": {
                "reasoning_model": "deepseek-r1:70b",
                "math_model": "qwen2.5-math:latest"
            }
        }
        self.auditor = Auditor(self.config)
        # Mock _query_llm to avoid actual API calls
        self.auditor._query_llm = MagicMock(return_value="Mocked Reasoner Response")

    def test_adm_trigger(self):
        """Test if ADM check is triggered for Kerr metric."""
        hypothesis = {"topic": "Kerr Metric Simulation", "hypothesis": "ADM 3+1"}
        self.assertTrue(PhysicsValidator.should_trigger_adm_check(hypothesis))

    def test_hamiltonian_pass(self):
        """Test if Hamiltonian constraint passes for small violation."""
        test_result = {
            "metrics": {"hamiltonian_constraint": 5e-6}
        }
        is_valid, val, is_sing, reason = PhysicsValidator.calculate_hamiltonian_constraint(test_result)
        self.assertTrue(is_valid)
        self.assertFalse(is_sing)
        self.assertLess(val, 1e-4)

    def test_coordinate_singularity_fatal(self):
        """Test if H > 10^-4 triggers FATAL coordinate singularity and Puncture Method request."""
        hypothesis = {"topic": "Black Hole Spacetime", "hypothesis": "ADM 3+1 decomposition"}
        test_result = {
            "hypothesis": hypothesis,
            "metrics": {"hamiltonian_constraint": 0.5}, # Massive violation
            "code": "print('ADM simulation')",
            "raw_output": "Violation: 0.5"
        }
        
        # We need to mock _query_llm for both the audit and the reasoner analysis
        self.auditor._query_llm.side_effect = [
            '{"audit_passed": true, "rejection_type": "NONE", "test_coverage": "all", "cheat_detected": false, "reasoning": "pass"}', # Initial audit
            "The Hamiltonian violation is extreme. You must use the Puncture Method." # Reasoner analysis
        ]
        
        audit = self.auditor.verify(test_result)
        
        print(f"DEBUG Audit Result: {audit}")
        self.assertFalse(audit["audit_passed"])
        self.assertEqual(audit["rejection_type"], "FATAL")
        self.assertIn("PUNCTURE METHOD", audit["reasoning"])

if __name__ == "__main__":
    unittest.main()
