
import json
from json_utils import extract_json, extract_and_validate, normalize_data

def test_extraction():
    print("--- Testing JSON Extraction ---")
    chatter = """
Here is the data you requested:
```json
{
    "key": "value",
    "list": [1, 2, 3]
}
```
I hope this helps!
"""
    data = extract_json(chatter)
    print(f"Extracted: {data}")
    return data and data.get("key") == "value"

def test_normalization():
    print("\n--- Testing Data Normalization ---")
    bad_data = {
        "required_constants": {
            "ALPHA": "0.7291 m/s",
            "BETA": "1.4582"
        },
        "topic": "Normalization Test"
    }
    normalized = normalize_data(bad_data, "hypothesis")
    print(f"Normalized: {normalized['required_constants']}")
    alpha = normalized['required_constants']['ALPHA']
    beta = normalized['required_constants']['BETA']
    return isinstance(alpha, float) and alpha == 0.7291 and isinstance(beta, float) and beta == 1.4582

def test_validation():
    print("\n--- Testing Schema Validation ---")
    # Missing required 'physics_primer'
    bad_hypo = {
        "topic": "Failure",
        "hypothesis": "Test",
        "mathematical_blueprint": "y = t",
        "mathematical_implementation_guide": "Manual",
        "required_constants": {}
    }
    data, error = extract_and_validate(json.dumps(bad_hypo), "hypothesis")
    print(f"Validation Error (Expected): {error}")
    return error and "physics_primer" in error

if __name__ == "__main__":
    results = [
        test_extraction(),
        test_normalization(),
        test_validation()
    ]
    
    if all(results):
        print("\nSUCCESS: JSON Hardening logic is verified.")
    else:
        print("\nFAILURE: One or more JSON tests failed.")
        import sys
        sys.exit(1)
