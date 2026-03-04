import sys
import os

# Ensure current directory is in path
sys.path.append(os.getcwd())

from preflight_repair import PreflightRepair

def test_singularity_softener():
    print("--- Testing Singularity Softener Utility ---")
    
    hypothesis = {
        "topic": "Schwarzschild Black Hole Evaporation",
        "required_constants": {"M": 1.0}
    }
    
    bad_code = """
# 1. SYMBOLIC SETUP
t, r = sp.symbols('t r')
SymbolGuard.verify_symbols(locals(), required=['t', 'r'])

# 2. CONSTANT INJECTION (REQUIRED CONSTANTS FROM ENVIRONMENT)
constants = {
    'M': 1.0
}

# 3. THE IMMUTABLE LAW (Explicit RHS)
# Division by r and (r - 2*M)
rs = 2 * constants['M']
acceleration = 1 / (r - rs)
potential = -constants['M'] / r

# 4. HIGH-FIDELITY EXECUTION LOOP
for i in range(100):
    # Logic using y_vals
    y_vals.append(y_vals[-1] + 0.1)
"""
    
    print("[TEST] Applying Singularity Softener repairs...")
    repaired_code, repairs = PreflightRepair.apply_all(bad_code, hypothesis)
    
    print("\n[REPAIRS LOGGED]:")
    for r in repairs:
        print(f"- {r}")

    # Verification checks
    success = True
    print("\n--- RESULTS ---")
    
    checks = {
        "Epsilon": "EPSILON = 1e-9" in repaired_code,
        "rs Softened": "(r - rs) + EPSILON" in repaired_code,
        "r Softened": "(r + EPSILON)" in repaired_code,
        "Horizon Guard": "if y_vals[-1] < 0.01: break" in repaired_code
    }
    
    for name, ok in checks.items():
        print(f"{name}: {'PASS' if ok else 'FAIL'}")
        if not ok: success = False

    if success:
        print("\nALL_PASS")
    else:
        print("\nSOME_FAIL")
        # Print only the first 500 chars to avoid buffer issues
        print(repaired_code[:500] + "...")

if __name__ == "__main__":
    test_singularity_softener()
