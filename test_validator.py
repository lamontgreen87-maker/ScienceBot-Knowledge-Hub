import sys
import os

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from json_utils import extract_and_validate

def test_validator():
    print("Testing Hypothesis Validation...")
    valid_hypothesis = {
        "topic": "Quantum Dynamics",
        "hypothesis": "Test",
        "simulation_context": "None",
        "physics_primer": "None",
        "atomic_specification": {
            "independent_variable": {},
            "dependent_variable": {},
            "symbolic_parameters": ["t"]
        },
        "mathematical_blueprint": "expr = ...",
        "mathematical_implementation_guide": "None",
        "target_complexity_score": 40,
        "required_constants": {"A": 1},
        "extra_info": "This should be allowed"
    }
    
    import json
    data, error = extract_and_validate(json.dumps(valid_hypothesis), "hypothesis")
    print(f"Valid Hypothesis Test: {'PASSED' if data else 'FAILED'} (Error: {error})")
    
    invalid_hypothesis = {
        "topic": "Missing constants"
        # required_constants is missing
    }
    data, error = extract_and_validate(json.dumps(invalid_hypothesis), "hypothesis")
    print(f"Invalid Hypothesis Test (Missing Constants): {'PASSED' if not data else 'FAILED'} (Error: {error})")

    print("\nTesting Audit Validation...")
    valid_audit = {
        "audit_passed": True,
        "rejection_type": "NONE",
        "reasoning": "Perfect",
        "something_extra": "Allowed"
    }
    data, error = extract_and_validate(json.dumps(valid_audit), "audit")
    print(f"Valid Audit Test: {'PASSED' if data else 'FAILED'} (Error: {error})")
    
    invalid_audit = {
        "audit_passed": True,
        "rejection_type": "INVALID_TYPE", # Not in enum
        "reasoning": "Bad Type"
    }
    data, error = extract_and_validate(json.dumps(invalid_audit), "audit")
    print(f"Invalid Audit Test (Bad Enum): {'PASSED' if not data else 'FAILED'} (Error: {error})")

if __name__ == "__main__":
    test_validator()
