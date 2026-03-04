import json

class RelativityValidator:
    """
    Sub-module for Physics Auditor to verify Einstein Field Equation (EFE) simulations.
    Specifically monitors Hamiltonian Constraint violations.
    """
    
    @staticmethod
    def validate_hamiltonian_constraint(test_result, threshold=1e-4):
        """
        Checks if the Hamiltonian constraint violation exceeds the permissible threshold.
        Returns (is_valid, value, reasoning).
        """
        metrics = test_result.get('metrics', {})
        
        # Look for hamiltonian_constraint in the metrics
        h_constraint = None
        
        # Check standard metrics dict
        if 'hamiltonian_constraint' in metrics:
            metric_data = metrics['hamiltonian_constraint']
            if isinstance(metric_data, dict):
                h_constraint = metric_data.get('value')
            else:
                h_constraint = metric_data
        
        # Fallback: scan logs or raw metrics if needed
        if h_constraint is None:
            # Maybe it was added as a conservation audit?
            audits = test_result.get('conservation_audits', [])
            for audit in audits:
                if 'hamiltonian' in audit.get('quantity', '').lower():
                    h_constraint = audit.get('delta')
                    break
        
        if h_constraint is None:
            return True, None, "No Hamiltonian constraint metric detected. Skipping GR check."
        
        try:
            h_val = abs(float(h_constraint))
            if h_val > threshold:
                return False, h_val, f"Hamiltonian Constraint violation ({h_val:.2e}) exceeds threshold ({threshold:.2e}). FATAL relativity error."
            return True, h_val, f"Hamiltonian Constraint violation ({h_val:.2e}) is within acceptable limits."
        except (ValueError, TypeError):
            return False, None, f"Could not parse Hamiltonian constraint value: {h_constraint}"

    @staticmethod
    def should_trigger_gr_check(hypothesis):
        """Determines if the hypothesis involves relativity and requires GR auditing."""
        h_str = str(hypothesis).lower()
        gr_keywords = ["einstein", "field equation", "metric tensor", "spacetime", "ricci", "schwarzschild", "kerr", "general relativity", "gravitational"]
        return any(kw in h_str for kw in gr_keywords)
