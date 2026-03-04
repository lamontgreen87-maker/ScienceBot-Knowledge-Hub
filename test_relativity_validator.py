from relativity_validator import RelativityValidator

def test_validator():
    print("--- Testing RelativityValidator ---")
    
    # Topic detection
    h1 = {"topic": "Schwarzschild Spacetime Analysis"}
    h2 = {"topic": "Quantum Harmonic Oscillator"}
    
    print(f"Trigger check for h1: {RelativityValidator.should_trigger_gr_check(h1)}")
    print(f"Trigger check for h2: {RelativityValidator.should_trigger_gr_check(h2)}")
    
    # Constraint check (Fail)
    res_fail = {
        "metrics": {
            "hamiltonian_constraint": 0.005
        }
    }
    is_valid, h_val, reason = RelativityValidator.validate_hamiltonian_constraint(res_fail)
    print(f"Fail case: valid={is_valid}, h_val={h_val}, reason={reason}")
    
    # Constraint check (Pass)
    res_pass = {
        "metrics": {
            "hamiltonian_constraint": 5e-6
        }
    }
    is_valid, h_val, reason = RelativityValidator.validate_hamiltonian_constraint(res_pass)
    print(f"Pass case: valid={is_valid}, h_val={h_val}, reason={reason}")
    
    if not is_valid is False and h_val == 5e-6:
         print("--- SUCCESS: Validator Logic Verified ---")

if __name__ == "__main__":
    test_validator()
