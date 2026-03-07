import os
import sys

# Ensure root is first in path to bypass stale tests/sci_utils.py
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# Clear any previously loaded sci_utils to ensure fresh import from root
if 'sci_utils' in sys.modules:
    del sys.modules['sci_utils']

import sympy as sp
import json
from sci_utils import ricci_scalar_symbolic

# Mock config for tests
config = {
    "paths": {"memory": "memory/"},
    "hardware": {"local_url": "http://localhost:11434/api/generate"}
}

if not os.path.exists('config.json'):
    with open('config.json', 'w') as f:
        json.dump(config, f)

# Define a simple Schwarzschild metric
t, r, theta, phi = sp.symbols('t r theta phi', real=True)
M = sp.symbols('M', real=True)
g = sp.Matrix([
    [-(1 - 2*M/r), 0, 0, 0],
    [0, 1/(1 - 2*M/r), 0, 0],
    [0, 0, r**2, 0],
    [0, 0, 0, r**2 * sp.sin(theta)**2]
])
coords = [t, r, theta, phi]

print("--- Test 1: First Derivation (Should Cache) ---")
import time
start = time.time()
res1 = ricci_scalar_symbolic(g, coords)
print(f"Result: {res1}")
print(f"Time: {time.time() - start:.4f}s")

print("\n--- Test 2: Second Call (Should Hit Cache) ---")
start = time.time()
res2 = ricci_scalar_symbolic(g, coords)
print(f"Result: {res2}")
print(f"Time: {time.time() - start:.4f}s")

if res1 == res2:
    print("\n[SUCCESS] Cache consistency verified.")
else:
    print("\n[FAILURE] Results differ.")
