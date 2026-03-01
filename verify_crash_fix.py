import json
import os
from lab import SimulationLab

def test_fix():
    print("Verifying SIMULATION_GENERATION_PROMPT formatting fix...")
    config = {
        'paths': {
            'memory': 'c:/continuous/memory',
            'discoveries': 'c:/continuous/discoveries'
        },
        'hardware': {
            'local_model': 'llama3.1:8b',
            'large_model': 'llama3.1:8b',
            'math_model': 'mightykatun/qwen2.5-math:72b',
            'api_url': 'http://localhost:11434/api/generate'
        }
    }
    
    lab = SimulationLab(config)
    
    hypothesis = {
        'hypothesis': 'Anomalous diffusion in porous media follows fractional kinetics.',
        'mathematical_blueprint': 'ALPHA * y + BETA * t',
        'mathematical_implementation_guide': 'Use 50-step memory window with fractional kernels.',
        'atomic_specification': {
            'independent_variable': {'symbol': 't'},
            'dependent_variable': {'symbol': 'y'}
        }
    }
    
    description = "Testing the formatting fix for iteration 3511."
    
    try:
        # This will trigger SIMULATION_GENERATION_PROMPT.format(...)
        prompt = lab.generate_simulation(hypothesis, description)
        print("SUCCESS: Prompt formatted correctly without KeyError.")
    except KeyError as e:
        print(f"FAILURE: KeyError still present: {e}")
    except Exception as e:
        print(f"ERROR: Unexpected error during test: {e}")

if __name__ == "__main__":
    test_fix()
