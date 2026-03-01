import numpy as np
from sci_utils import ScientificReport, verify_confidence_level
import json

def test_statistical_report():
    print("Testing ScientificReport with Statistical Tests...")
    report = ScientificReport(simulation_id="test_rigor_001")
    
    # 1. Test standard metric
    report.add_metric("Signal Strength", 0.85, unit="mbar")
    
    # 2. Test statistical test (Manual)
    report.add_statistical_test("Alpha-Decay Consistency", p_value=0.08, significance_threshold=0.05)
    
    # 3. Test verify_confidence_level integration
    clean = np.linspace(0, 10, 100)
    noisy = clean + np.random.normal(0, 0.1, 100)
    passed, h, p_val, reason = verify_confidence_level(noisy, clean)
    
    print(f"Confidence Level Test: Passed={passed}, Reason={reason}")
    report.add_statistical_test("Robustness Test", p_val, significance_threshold=0.05)
    report.log_trace(f"Rigor Audit: {reason}")
    
    # 4. Finalize and capture output
    print("\nFinalizing Report:")
    report.finalize()

if __name__ == "__main__":
    test_statistical_report()
