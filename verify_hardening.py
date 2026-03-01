import sys
from audit_functions import get_preflight_report

test_hypothesis = {
    "hypothesis": "Anomalous diffusion in fractional media.",
    "required_constants": {"ALPHA": "0.7", "BETA": "1.2"}
}

test_code_bad = """
import numpy as np
import sympy as sp

# Missing constants dictionary
ALPHA = 0.7
expr = sp.symbols('y') * ALPHA
# Using .subs()
val = expr.subs(sp.symbols('y'), 1.0)

# Missing mandatory skeleton sections
"""

test_code_good = """
import numpy as np
import sympy as sp

# 1. SYMBOLIC SETUP
t, y = sp.symbols('t y')

# 2. CONSTANT INJECTION
constants = {
    'ALPHA': 0.7,
    'BETA': 1.2
}

# 3. THE IMMUTABLE LAW
expr = constants['ALPHA'] * y

# 4. HIGH-FIDELITY EXECUTION
# Resource pool decay...

# 5. DATA LOGGING
print("P-Value: 0.04")
"""

print("--- Testing BAD Code ---")
reports_bad = get_preflight_report(test_code_bad, test_hypothesis)
for r in reports_bad:
    print(f"Issue: {r}")

print("\n--- Testing GOOD Code ---")
reports_good = get_preflight_report(test_code_good, test_hypothesis)
if not reports_good:
    print("Preflight PASSED")
else:
    for r in reports_good:
        print(f"Issue: {r}")
