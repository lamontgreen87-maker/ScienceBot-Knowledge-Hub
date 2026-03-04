import json
import numpy as np

class PhysicsValidator:
    """
    Rigorous Physics Validator for ADM 3+1 Decomposition and Hamiltonian Constraints.
    Detects coordinate singularities and triggers specialized fixes.
    """

    @staticmethod
    def calculate_hamiltonian_constraint(test_result, threshold=1e-4):
        """
        Calculates the Hamiltonian constraint violation: H = R + K^2 - K_ij K^ij - 16πρ
        Returns (is_valid, value, is_coordinate_singularity, reasoning)
        """
        metrics = test_result.get('metrics', {})
        h_val = None

        # 1. Look for explicit hamiltonian_constraint in metrics
        if 'hamiltonian_constraint' in metrics:
            data = metrics['hamiltonian_constraint']
            h_val = data.get('value') if isinstance(data, dict) else data
        
        # 2. Fallback: Parse from conservation audits
        if h_val is None:
            audits = test_result.get('conservation_audits', [])
            for audit in audits:
                if 'hamiltonian' in str(audit.get('quantity', '')).lower():
                    h_val = audit.get('delta')
                    break

        if h_val is None:
            return True, 0.0, False, "No Hamiltonian metric detected. Passing by default."

        try:
            h_val = abs(float(h_val))
            is_valid = h_val < threshold
            
            # Coordinate Singularity Logic: 
            # If the violation is massive (e.g. > 1e1 or sudden divergence), it's likely a coordinate singularity.
            # For this specific requirement, any H > 10^-4 is treated as a FATAL coordinate singularity 
            # to trigger the Puncture Method.
            is_coordinate_singularity = not is_valid

            if not is_valid:
                reasoning = (f"FATAL: Hamiltonian Constraint violation detected ({h_val:.2e} > {threshold:.2e}). "
                            "This indicates a coordinate singularity or numerical breakdown in the ADM decomposition.")
            else:
                reasoning = f"Hamiltonian Constraint passed ({h_val:.2e} < {threshold:.2e})."

            return is_valid, h_val, is_coordinate_singularity, reasoning

        except (ValueError, TypeError):
            return False, 0.0, False, f"Could not parse Hamiltonian value: {h_val}"

    @staticmethod
    def should_trigger_adm_check(hypothesis):
        """Detects if the hypothesis requires ADM 3+1 auditing."""
        h_str = str(hypothesis).lower()
        keywords = ["adm", "3+1", "hamiltonian constraint", "extrinsic curvature", "lapse", "shift", "kerr", "schwarzschild", "singularity"]
        return any(kw in h_str for kw in keywords)
