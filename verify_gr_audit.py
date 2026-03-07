import sympy as sp
from sci_utils import verify_ricci_integrity, verify_vacuum_einstein

def test_lorentzian_enforcement():
    print("Testing Lorentzian Enforcement...")
    t, r, theta, phi = sp.symbols('t r theta phi')
    coords = [t, r, theta, phi]
    
    # Euclidean Metric (Banned)
    g_eucl = sp.Matrix([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])
    valid, msg = verify_ricci_integrity(g_eucl, coords)
    print(f"Euclidean Result: Valid={valid}, Msg={msg}")

    # Lorentzian Metric (Allowed)
    g_lor = sp.Matrix([
        [-1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])
    valid, msg = verify_ricci_integrity(g_lor, coords)
    print(f"Lorentzian Result: Valid={valid}, Msg={msg}")

def test_vacuum_audit():
    print("\nTesting Vacuum Audit...")
    t, r, theta, phi = sp.symbols('t r theta phi')
    M = sp.symbols('M')
    coords = [t, r, theta, phi]
    
    # Schwarzschild Metric (Vacuum)
    f = 1 - 2*M/r
    g_schwarz = sp.Matrix([
        [-f, 0, 0, 0],
        [0, 1/f, 0, 0],
        [0, 0, r**2, 0],
        [0, 0, 0, r**2 * sp.sin(theta)**2]
    ])
    is_vacuum, failures, msg = verify_vacuum_einstein(g_schwarz, coords)
    print(f"Schwarzschild Result: Vacuum={is_vacuum}, Msg={msg}")

    # Non-Vacuum Metric
    g_non_vacuum = g_schwarz.copy()
    g_non_vacuum[0,0] = -1 # Breaks the f factor relationship
    is_vacuum, failures, msg = verify_vacuum_einstein(g_non_vacuum, coords)
    print(f"Non-Vacuum Result: Vacuum={is_vacuum}, Msg={msg}")

if __name__ == "__main__":
    test_lorentzian_enforcement()
    test_vacuum_audit()
