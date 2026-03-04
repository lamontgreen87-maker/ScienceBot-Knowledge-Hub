import sys
import os
import sympy as sp

# Ensure current directory is in path
sys.path.append(os.getcwd())

from sci_utils import SymbolGuard
from template_validation import TemplateValidator

def test_symbol_guard():
    print("--- Testing Symbol Guard Utility ---")
    
    # 1. Test SymbolGuard.verify_symbols directly
    t, r = sp.symbols('t r')
    scope = {'t': t, 'r': r, 'sp': sp}
    
    print("[TEST] Verifying existing symbols...")
    try:
        SymbolGuard.verify_symbols(scope, required=['t', 'r'])
        print("SUCCESS: Existing symbols verified.")
    except Exception as e:
        print(f"FAILURE: Unexpected error: {e}")

    print("[TEST] Verifying missing symbols...")
    try:
        SymbolGuard.verify_symbols(scope, required=['t', 'phi'])
        print("FAILURE: Should have raised NameError for missing 'phi'.")
    except NameError as e:
        print(f"SUCCESS: Caught expected NameError: {e}")
    except Exception as e:
        print(f"FAILURE: Caught unexpected error type: {type(e).__name__}: {e}")

    # 2. Test TemplateValidator enforcement
    print("\n--- Testing TemplateValidator Enforcement ---")
    
    bad_code = """
import sympy as sp
from sci_utils import SymbolGuard
t, r = sp.symbols('t r')
# Missing SymbolGuard.verify_symbols(locals())
expr = t * r
"""
    
    good_code = """
import sympy as sp
from sci_utils import SymbolGuard
t, r = sp.symbols('t r')
SymbolGuard.verify_symbols(locals(), required=['t', 'r'])
expr = t * r
"""
    
    mock_hypothesis = {"topic": "Symbol Guard Test"}
    
    print("[TEST] Validating code WITHOUT Symbol Guard...")
    ok, issues = TemplateValidator.validate_symbol_guard_presence(bad_code, mock_hypothesis)
    if not ok:
        print(f"SUCCESS: Correctly flagged missing guard. Issues: {issues}")
    else:
        print("FAILURE: Failed to flag code missing the guard.")

    print("[TEST] Validating code WITH Symbol Guard...")
    ok, issues = TemplateValidator.validate_symbol_guard_presence(good_code, mock_hypothesis)
    if ok:
        print("SUCCESS: Correctly accepted code with guard.")
    else:
        print(f"FAILURE: Incorrectly flagged code with guard. Issues: {issues}")

if __name__ == "__main__":
    test_symbol_guard()
