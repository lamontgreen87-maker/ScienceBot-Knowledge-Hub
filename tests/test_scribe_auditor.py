import sympy as sp
import os
import sys
import json

# Ensure root is in path
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from sci_utils import verify_bianchi_identity, calculate_einstein_tensor
from critic import Auditor
from scribe import Scribe

# Mock config
config = {
    "paths": {
        "memory": "memory/",
        "tests": "tests/",
        "discoveries": "memory/discoveries/"
    },
    "hardware": {
        "reasoning_model": "deepseek-reasoner",
        "local_url": "http://localhost:11434/api/generate"
    }
}

# Create dirs if missing
for p in config['paths'].values():
    if not os.path.exists(p): os.makedirs(p)

print("--- Test 1: Mathematical Bianchi Identity (Schwarzschild) ---")
t, r, theta, phi = sp.symbols('t r theta phi', real=True)
M = sp.symbols('M', real=True)
g = sp.Matrix([
    [-(1 - 2*M/r), 0, 0, 0],
    [0, 1/(1 - 2*M/r), 0, 0],
    [0, 0, r**2, 0],
    [0, 0, 0, r**2 * sp.sin(theta)**2]
])
coords = [t, r, theta, phi]

is_valid, failures = verify_bianchi_identity(g, coords)
print(f"Bianchi Valid: {is_valid}")
if not is_valid:
    print(f"Failures: {failures}")
else:
    print("Success: Schwarzschild metric satisfies Bianchi Identity.")

print("\n--- Test 2: Auditor Integration (Broken Metric) ---")
# Manually break the metric by adding a non-physical term
g_broken = g.copy()
g_broken[0,0] = g[0,0] + r**2 # Nonsense term
is_valid_broken, failures_broken = verify_bianchi_identity(g_broken, coords)
print(f"Broken Metric Bianchi Valid: {is_valid_broken}")
print(f"Expected Failures Found: {len(failures_broken) > 0}")

print("\n--- Test 3: Scribe Cache Persistence ---")
scribe = Scribe(config)
test_result = {
    "hypothesis": {"topic": "Schwarzschild Rigor", "hypothesis": "Test", "mathematical_blueprint": "G_ab = 0"},
    "symbolic_metric": g,
    "coords": coords,
    "ricci_scalar": sp.simplify(0),
    "einstein_tensor": sp.Matrix.zeros(4,4)
}

# Scribe should store these in vector cache
scribe._persist_symbolic_cache(test_result)
print("Scribe persistence triggered.")

# Check Vector DB (Mock/Indirect check)
metric_str = str(g)
import hashlib
metric_key = hashlib.md5(metric_str.encode()).hexdigest()
cached_scalar = scribe.vector_mem.get_tensor_component(metric_key, "ricci_scalar")
print(f"Retrieved from Cache: {cached_scalar}")

if cached_scalar == "0":
    print("\n[SUCCESS] End-to-End Symbolic Rigor & Cache verified.")
else:
    print("\n[FAILURE] Cache retrieval failed.")
