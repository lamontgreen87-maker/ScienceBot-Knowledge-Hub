import os
import json
import time
import sys

# Ensure the current directory is in the path for imports
sys.path.append(os.getcwd())

from agent import ScienceBot
from preflight_repair import PreflightRepair

def test_preflight_repair():
    print("--- Verifying Advanced Preflight Repair (Lambdify + Symbols) ---")
    
    # 1. Mock code with complex .subs() and Symbol Mismatch
    bad_code = """
# 1. SYMBOLIC SETUP
import sympy as sp
t, y = sp.symbols('t y')
# Missing ALPHA in symbols!

# 3. THE IMMUTABLE LAW
ALPHA = 0.5
expr = t * y * ALPHA
# Chained .subs() should be lambdified
val = expr.subs(t, 0.5).subs(y, 1.0)

# Iterative .subs() should be lambdified
for i in range(10):
    rhs = expr.subs(y, 2.0)

def fractional_ode(t, y):
    return ALPHA * y

# 4. HIGH-FIDELITY EXECUTION
"""
    
    mock_hypothesis = {
        "topic": "SymPy Stability Test",
        "hypothesis": "Testing lambdify conversion",
        "required_constants": {"ALPHA": 0.5},
        "atomic_specification": {"dependent_variable": {"symbol": "y"}}
    }
    
    # 2. Test preflight_repair skill directly
    print("\n[TEST] Running PreflightRepair.apply_all...")
    repaired_code, repairs = PreflightRepair.apply_all(bad_code, mock_hypothesis)
    
    print(f"Repairs applied: {repairs}")
    
    # Check for lambdify conversion (chained)
    if "sp.lambdify((t, y), expr, 'numpy')(0.5, 1.0)" in repaired_code:
        print("SUCCESS: Chained .subs() converted to lambdify.")
    else:
        print("FAILURE: Chained .subs() lambdify conversion failed.")
        print(f"Code Snippet: {repaired_code[repaired_code.find('val ='):repaired_code.find('val =')+100]}")

    # Check for lambdify conversion (single/iterative)
    if "sp.lambdify(y, expr, 'numpy')(2.0)" in repaired_code:
        print("SUCCESS: Iterative .subs() converted to lambdify.")
    else:
        print("FAILURE: Iterative .subs() lambdify conversion failed.")

    # Check for symbol alignment
    if "symbols('t y ALPHA')" in repaired_code:
        print("SUCCESS: Missing symbol 'ALPHA' added to symbols() call.")
    else:
        print("FAILURE: Symbol alignment failed.")

    # 3. Test Agent Integration (logging to hallucination_log.md)
    print("\n[TEST] Verifying ScienceBot.lint_code integration...")
    if os.path.exists("bot.lock"):
        os.remove("bot.lock")
        
    # Mock config
    with open("config.json", 'r') as f:
        config = json.load(f)
    
    bot = ScienceBot("config.json")
    is_valid, issues, msg, final_code = bot.lint_code(bad_code, mock_hypothesis)
    
    print(f"Lint Integration Result: {is_valid}")
    
    # Check if log was written
    log_path = os.path.join(bot.config['paths']['memory'], "hallucination_log.md")
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            log_content = f.read()
            if "Converted chained .subs()" in log_content:
                print("SUCCESS: Advanced repair logged to hallucination_log.md.")
            else:
                print("FAILURE: Advanced repair not found in log.")
    else:
        print("FAILURE: hallucination_log.md not found.")

if __name__ == "__main__":
    test_preflight_repair()
