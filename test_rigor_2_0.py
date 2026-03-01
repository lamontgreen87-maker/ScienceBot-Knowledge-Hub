
import json
import sys
import os
from template_processing import get_rigor_report, verify_constant_values, validate_primitive_runtime, check_complexity_depth

def test_constant_mismatch():
    print("--- Testing Constant Value Verification ---")
    hypothesis = {
        "required_constants": {"ALPHA": 0.7291, "BETA": 1.4582}
    }
    
    # Mismatch: ALPHA is 0.5 in code but 0.7291 in hypothesis
    bad_code = """
constants = {
    'ALPHA': 0.5,
    'BETA': 1.4582
}
# 3. THE IMMUTABLE LAW
y = constants['ALPHA'] * t + constants['BETA']
"""
    issues = verify_constant_values(bad_code, hypothesis)
    print(f"Mismatch Issues Found: {issues}")
    return any("value mismatch" in i for i in issues)

def test_low_complexity():
    print("\n--- Testing Complexity Depth ---")
    # One-liner, no loops
    bad_code = "y = t"
    issues = check_complexity_depth(bad_code)
    print(f"Low Complexity Issues: {issues}")
    return len(issues) > 0

def test_high_complexity():
    print("\n--- Testing High Complexity Pass ---")
    good_code = """
import numpy as np
constants = {'ALPHA': 0.7291, 'BETA': 1.1234}
# 4. HIGH-FIDELITY EXECUTION LOOP
state = np.zeros(100)
resources = 1.0
for t in range(100):
    resources -= 0.01 * np.mean(state) # call 1, 2
    noise = np.random.normal(0, 0.1) # call 3
    state = state * constants['ALPHA'] + noise * constants['BETA'] # call 4
    if resources < 0: # call 5 (implicit in logic but we need calls)
        state = np.clip(state, -1, 1) # call 6
        break
"""
    issues = check_complexity_depth(good_code)
    print(f"High Complexity Issues: {issues}")
    return len(issues) == 0

def test_primitive_runtime():
    print("\n--- Testing Primitive Runtime (Load Test) ---")
    # This should pass if sci_utils is findable
    code = "y = grunwald_letnikov_diff(f, t, y, 0.5)"
    issues = validate_primitive_runtime(code)
    print(f"Runtime Issues: {issues}")
    return len(issues) == 0

if __name__ == "__main__":
    results = [
        test_constant_mismatch(),
        test_low_complexity(),
        test_high_complexity(),
        test_primitive_runtime()
    ]
    
    if all(results):
        print("\nSUCCESS: Rigor Hardening 2.0 logic is verified.")
    else:
        print("\nFAILURE: One or more Rigor 2.0 tests failed.")
        sys.exit(1)
