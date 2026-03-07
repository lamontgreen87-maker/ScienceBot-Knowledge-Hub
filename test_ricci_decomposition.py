import sys
import os
import json
from unittest.mock import MagicMock

# Mock necessary imports for lab.py
sys.modules['physical_constants'] = MagicMock()
sys.modules['base_module'] = MagicMock()
sys.modules['prompt_templates'] = MagicMock()
sys.modules['template_validation'] = MagicMock()
sys.modules['vector_memory'] = MagicMock()

# Import the class to test
from lab import SimulationLab

def test_ricci_flow_decomposition():
    config = {
        'hardware': {'api_url': ['http://localhost:11434']},
        'paths': {'memory': '.', 'tests': '.'},
        'research': {'simulation_fidelity': 'ULTRA'}
    }
    lab = SimulationLab(config)
    lab.ui = MagicMock()
    lab._query_llm = MagicMock(side_effect=[
        "```python\nt, r, theta, phi = sp.symbols('t r theta phi', real=True)\ng = sp.Matrix([[-1,0,0,0],[0,1,0,0],[0,0,r**2,0],[0,0,0,r**2*sp.sin(theta)**2]])\ncoords = [t,r,theta,phi]\n```",
        "```python\nricci = ricci_scalar_symbolic(g, coords)\nexpr = -2 * ricci\n```",
        "```python\nimport numpy as np\nimport sympy as sp\n# Full script logic\nsol_y = np.zeros(10); sol_t = np.linspace(0,1,10)\nprint('=== SCIENTIFIC_METRICS ===')\nprint('{}')\n```"
    ])
    
    hypothesis = {
        'topic': 'Ricci flow on Schwarzschild manifold',
        'hypothesis': 'Testing if Ricci induction stabilizes the horizon.',
        'atomic_specification': {
            'independent_variable': {'symbol': 't'},
            'dependent_variable': {'symbol': 'g'}
        }
    }
    
    print("Testing Ricci Flow Decomposition...")
    result_code = lab.generate_simulation(hypothesis, "Ricci flow test")
    
    # Check if UI log for Ricci Flow was called
    logs = [call[0][0] for call in lab.ui.print_log.call_args_list]
    if any("Ricci Flow detected" in l for l in logs):
        print("PASS: Decomposition trigger detected.")
    
    if any("DECOMPOSITION Phase 1" in l for l in logs):
        print("PASS: Phase 1 log found.")
        
    print("Final code snippet:")
    print(result_code[:200] + "...")

if __name__ == "__main__":
    test_ricci_flow_decomposition()
