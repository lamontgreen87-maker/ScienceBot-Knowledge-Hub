from template_validation import TemplateValidator

# 1. A "BAD" simulation (has .subs, banned def, and low complexity)
bad_code = """
import numpy as np
import sympy as sp
from sci_utils import ScientificReport, verify_confidence_level

# 1. SYMBOLIC SETUP
t, y = sp.symbols('t y')
ALPHA = 0.5

# 2. CONSTANT INJECTION
constants = {'ALPHA': 0.5}

# 3. THE IMMUTABLE LAW
expr = y / t
expr = expr.subs({'ALPHA': 0.5}) # BANNED SUBS

# 4. HIGH-FIDELITY EXECUTION
def fractional_ode(t, y): # BANNED DEF
    return t * y

y_vals = [1.0]
for step in range(10): # Too simple (low complexity)
    y_vals.append(y_vals[-1] + 1)

# 5. DATA LOGGING
report = ScientificReport(simulation_id="test")
report.finalize()
"""

# 2. A "GOOD" simulation
good_code = """
import numpy as np
import sympy as sp
from sci_utils import ScientificReport, verify_confidence_level

# 1. SYMBOLIC SETUP
t, y = sp.symbols('t y')

# 2. CONSTANT INJECTION (REQUIRED CONSTANTS FROM ENVIRONMENT)
constants = {
    'ALPHA': 0.7291,
    'BETA': 1.4582
}

# 3. THE IMMUTABLE LAW (Explicit RHS)
# Algebraic multiplier used, no .subs()
expr = constants['ALPHA'] * y + constants['BETA'] * t

# 4. HIGH-FIDELITY EXECUTION
t_vals = np.linspace(0, 10, 100); h = t_vals[1] - t_vals[0]
y_vals = [1.0]
resource_capacity = 100.0
failure_probability = 0.02
memory_buffer = []

# --- INNER LOOP: PRE-SIMULATION ANALYSIS ---
for i in range(1, 10):
    check = i * 0.1

# --- MAIN PHYSICS LOOP ---
for i in range(1, len(t_vals)):
    # 4a. Memory Window (Rolling Buffer)
    memory_buffer.append(y_vals[-1])
    if len(memory_buffer) > 50: memory_buffer.pop(0)
    
    # 4b. Resource depletion logic (Fidelity)
    resource_capacity -= 0.5 * y_vals[-1]
    if resource_capacity <= 0 or np.random.random() < failure_probability:
        break
    
    # 4c. Fractal Map Scaling & GL-Diff
    scaling_factor = y_vals[-1] ** (1 / constants['ALPHA'])
    # Simulation Logic
    y_vals.append(y_vals[-1] + 0.1)

# 5. DATA LOGGING
report = ScientificReport(simulation_id="test")
report.finalize()
"""

hypothesis = {
    "topic": "Anomalous Diffusion in Fractal Spacetime",
    "hypothesis": "The diffusion scaling z=1.5 follows a fractional power law.",
    "simulation_context": "Cryogenic nitrogen environment.",
    "required_constants": {"ALPHA": "0.7291", "BETA": "1.4582"},
    "target_complexity_score": "60",
    "mathematical_implementation_guide": "Implement a 50-step Rolling Memory Window and a Fractal Map scaling logic."
}

def run_tests():
    print("=== TESTING BAD CODE ===")
    report_bad = TemplateValidator.run_all_checks(bad_code, hypothesis)
    print(f"Valid: {report_bad['valid']}")
    print("Errors:", report_bad["errors"])
    print("Directives:", report_bad["repair_directives"])

    print("\n=== TESTING GOOD CODE ===")
    # Note: good_code snippet above doesn't have the primitives but it passes the basic structure
    report_good = TemplateValidator.run_all_checks(good_code, hypothesis)
    print(f"Valid: {report_good['valid']}")
    if not report_good['valid']:
        print("Errors:", report_good["errors"])
        print("Directives:", report_good["repair_directives"])

    # --- TEST 4: Geometric Fidelity (FAIL) ---
    print("\n[TEST 4] Geometric Fidelity (Curvature without Matrix)...")
    geo_hypothesis = {
        "topic": "Ricci Flow",
        "hypothesis": "Test curvature",
        "mathematical_implementation_guide": "Use ricci_curvature_scalar."
    }
    bad_geo_code = """
# 1. SYMBOLIC SETUP
# Missing g = Matrix
# 4. HIGH-FIDELITY EXECUTION
# No Matrix call
"""
    ok, issues = TemplateValidator.validate_geometric_fidelity(bad_geo_code, geo_hypothesis)
    print(f"Result: {'PASS' if ok else 'FAIL'}")
    if not ok: print(f"Issues: {issues}")

    # --- TEST 5: Symbolic Injection (FAIL) ---
    print("\n[TEST 5] Symbolic Injection (Missing Constant in symbols)...")
    sym_hypothesis = {
        "required_constants": {"ALPHA": 0.5}
    }
    bad_sym_code = """
import sympy as sp
t, y = sp.symbols('t y')
ALPHA = 0.5
"""
    ok, issues = TemplateValidator.validate_symbolic_injection(bad_sym_code, sym_hypothesis)
    print(f"Result: {'PASS' if ok else 'FAIL'}")
    if not ok: print(f"Issues: {issues}")

if __name__ == "__main__":
    run_tests()
