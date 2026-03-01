
import json
from unittest import mock
from template_processing import validate_hypothesis_schema, get_rigor_report

def test_hypothesis_schema():
    print("--- Testing Hypothesis Schema Validation ---")
    bad_hypothesis = {
        "topic": "Test",
        "hypothesis": "Test"
        # Missing many keys
    }
    is_valid, missing = validate_hypothesis_schema(bad_hypothesis)
    print(f"Bad Hypothesis Valid: {is_valid}, Missing: {missing}")
    
    good_hypothesis = {
        "topic": "Test",
        "hypothesis": "Test",
        "physics_primer": "Test",
        "atomic_specification": {
            "independent_variable": "x",
            "dependent_variable": "y",
            "symbolic_parameters": ["a"]
        },
        "mathematical_blueprint": "Test",
        "mathematical_implementation_guide": "Test",
        "required_constants": {"ALPHA": 0.5}
    }
    is_valid, missing = validate_hypothesis_schema(good_hypothesis)
    print(f"Good Hypothesis Valid: {is_valid}, Missing: {missing}")
    
    return is_valid and not any(missing)

def test_rigor_report():
    print("\n--- Testing Rigor Report (Constants & Primitives) ---")
    hypothesis = {
        "required_constants": {"ALPHA": 0.5}
    }
    
    # Missing ALPHA in Law section
    bad_code = """
# 1. SYMBOLIC SETUP
# 2. CONSTANT INJECTION
constants = {'ALPHA': 0.5}
# 3. THE IMMUTABLE LAW
y = t**2 
# 4. HIGH-FIDELITY EXECUTION
# 5. DATA LOGGING
"""
    issues = get_rigor_report(bad_code, hypothesis)
    print(f"Bad Code Issues: {issues}")
    
    # Correct usage
    good_code = """
# 1. SYMBOLIC SETUP
# 2. CONSTANT INJECTION
constants = {'ALPHA': 0.5}
# 3. THE IMMUTABLE LAW
y = constants['ALPHA'] * t**2
# 4. HIGH-FIDELITY EXECUTION
# 5. DATA LOGGING
"""
    issues = get_rigor_report(good_code, hypothesis)
    print(f"Good Code Issues: {issues}")
    
    # Primitive check
    primitive_code = """
# 1. SYMBOLIC SETUP
# 2. CONSTANT INJECTION
# 3. THE IMMUTABLE LAW
y = grunwald_letnikov_diff(f) # Too few args
# 4. HIGH-FIDELITY EXECUTION
# 5. DATA LOGGING
"""
    issues = get_rigor_report(primitive_code, hypothesis)
    print(f"Primitive Errors: {issues}")
    
    return len(issues) > 0 # Should detect errors

if __name__ == "__main__":
    h_ok = test_hypothesis_schema()
    r_ok = test_rigor_report()
    
    if h_ok and r_ok:
        print("\nSUCCESS: Rigor Framework is functional.")
    else:
        print("\nFAILURE: Rigor Framework checks did not behave as expected.")
