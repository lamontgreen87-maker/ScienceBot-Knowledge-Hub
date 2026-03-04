import json
from critic import Auditor

def test_efe_audit():
    print("--- Executing EFE Physics Audit Verification ---")
    
    # Mock config
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    auditor = Auditor(config)
    
    # 1. Mock Test Result with GR Topic and Hamiltonian Violation
    mock_result = {
        "hypothesis": {
            "topic": "Schwarzschild Event Horizon Stability",
            "hypothesis": "Testing the stability of numerical Schwarzschild spacetime under perturbations.",
            "mathematical_blueprint": "g_mu_nu = Schwarzschild_expression"
        },
        "code": "# 4. HIGH-FIDELITY EXECUTION\n# Simulation of Schwarzschild spacetime\nimport numpy as np\ndef ricci_curvature_scalar(): pass",
        "raw_output": "Simulation complete. Results found.",
        "metrics": {
            "hamiltonian_constraint": {
                "value": 0.005,  # Exceeds 1e-4 threshold
                "unit": "adm_units"
            }
        }
    }
    
    print(f"Triggering audit for topic: {mock_result['hypothesis']['topic']}")
    print(f"Forced Hamiltonian Violation: {mock_result['metrics']['hamiltonian_constraint']['value']}")
    
    # Re-mock the LLM call to skip the general check and focus on the GR logic
    # or just let it run if the mock result passes the first level
    
    # Note: verify() calls _query_llm. We expect it to pass the general audit
    # then fail on the RelativityValidator check.
    
    audit_report = auditor.verify(mock_result)
    
    print("\n--- AUDIT REPORT ---")
    print(f"Passed: {audit_report.get('audit_passed')}")
    print(f"Rejection Type: {audit_report.get('rejection_type')}")
    print(f"Reasoning Preview: {audit_report.get('reasoning', '')[:300]}...")
    
    if not audit_report.get('audit_passed') and audit_report.get('rejection_type') == 'FATAL':
        if 'REASONER ANALYSIS' in audit_report.get('reasoning', ''):
            print("\nSUCCESS: Hamiltonian violation detected and Reasoner triggered.")
        else:
            print("\nPARTIAL SUCCESS: Hamiltonian violation detected, but Reasoner analysis missing.")
    else:
        print("\nFAILURE: Audit did not correctly flag the Hamiltonian violation.")

if __name__ == "__main__":
    test_efe_audit()
