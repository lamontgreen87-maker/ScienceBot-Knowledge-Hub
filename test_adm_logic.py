import sympy as sp
from sci_utils import verify_adm_constraints

def test_schwarzschild_adm():
    # Define Schwarzschild Metric in Schwarzschild local coords (t, r, theta, phi)
    t, r, theta, phi = sp.symbols('t r theta phi', real=True)
    M = sp.symbols('M', positive=True)
    
    # g_tt = -(1-2M/r), g_rr = 1/(1-2M/r), g_theta_theta = r^2, g_phi_phi = r^2 sin^2 theta
    g = sp.Matrix([
        [-(1-2*M/r), 0, 0, 0],
        [0, 1/(1-2*M/r), 0, 0],
        [0, 0, r**2, 0],
        [0, 0, 0, r**2 * sp.sin(theta)**2]
    ])
    
    is_valid, constraints, reasoning = verify_adm_constraints(g, [t, r, theta, phi])
    
    print(f"ADM Validation Result: {is_valid}")
    print(f"Constraints: {constraints}")
    print(f"Reasoning: {reasoning}")
    
    if is_valid:
        print("SUCCESS: ADM Logic correctly identified Schwarzschild metric structure.")
    else:
        print("FAILURE: ADM Logic rejected Schwarzschild metric.")

if __name__ == "__main__":
    test_schwarzschild_adm()
