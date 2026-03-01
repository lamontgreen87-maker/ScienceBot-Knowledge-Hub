import numpy as np
from scipy import stats
from scipy.stats import linregress
from sympy import symbols, Eq, checksol, simplify

def verify_power_law(scales, values, expected_alpha=None, r_threshold=0.95, min_decades=2.0):
    """
    Performs a log-log regression to verify a power-law relationship.
    Mandates a minimum number of decades (orders of magnitude) for the scale set.
    """
    scale_range = np.log10(np.max(scales)) - np.log10(np.min(scales))
    if scale_range < min_decades:
        return 0, 0, False # Fails if scale set is too narrow
        
    log_scales = np.log(scales)
    log_values = np.log(values)
    slope, intercept, r_value, p_value, std_err = linregress(log_scales, log_values)
    
    passes = abs(r_value) >= r_threshold
    if expected_alpha is not None:
        # Check if slope is within 10% of expected alpha
        passes = passes and (abs(slope - expected_alpha) < 0.1 * abs(expected_alpha))
        
    return slope, r_value, passes

def verify_conservation(initial_val, final_val, tolerance=1e-8):
    """Verifies if a quantity is conserved within a tolerance."""
    delta = abs(initial_val - final_val)
    return delta < tolerance, delta

def symbolic_to_numeric_bridge(equation_str, symbols_list, numerical_inputs):
    """
    Converts a SymPy equation to a numerical function and tests it against inputs.
    Ensures that the 'Symbolic' theory matches the 'Numerical' simulation.
    """
    from sympy import lambdify, symbols as sympy_symbols
    from sympy.parsing.sympy_parser import parse_expr
    
    try:
        expr = parse_expr(equation_str)
        syms = [sympy_symbols(s) for s in symbols_list]
        num_func = lambdify(syms, expr, 'numpy')
        
        # Test function (numerical_inputs should be a list of arrays/values)
        expected_output = num_func(*numerical_inputs)
        return expected_output
    except Exception as e:
        print(f"Bridge Error: {e}")
        return None

def symbolic_truth_test(equation_str, solution_dict):
    """
    Uses SymPy to rigorously verify if a solution satisfies an equation.
    equation_str: e.g. 'y - x**2' (assumed = 0)
    """
    try:
        from sympy.parsing.sympy_parser import parse_expr
        expr = parse_expr(equation_str)
        is_true = simplify(expr.subs(solution_dict)) == 0
        return is_true
def add_noise(data, noise_type='gaussian', level=0.05):
    """
    Injects noise into a numerical array.
    noise_type: 'gaussian' or 'poisson'
    level: scale of noise relative to data mean
    """
    data = np.array(data)
    if noise_type == 'gaussian':
        noise = np.random.normal(0, level * np.abs(np.mean(data)), data.shape)
        return data + noise
    elif noise_type == 'poisson':
        # Poisson is typically for counts; we scale for continuous if needed
        return np.random.poisson(data)
    return data

def verify_scale_invariance(numerical_func, x_val, b_factor=2.0, alpha=1.5, tolerance=1e-2):
    """
    Directly tests the scaling identity: f(bx) = b^alpha * f(x).
    This proves Scale-Invariance rather than just guessing it via regression.
    """
    try:
        f_x = numerical_func(x_val)
        f_bx = numerical_func(x_val * b_factor)
        if f_x == 0 or np.isnan(f_x) or np.isnan(f_bx):
            return False, 0.0
            
        actual_ratio = f_bx / f_x
        expected_ratio = b_factor ** alpha
        relative_error = abs(actual_ratio - expected_ratio) / expected_ratio
        
        return relative_error < tolerance, relative_error
    except Exception as e:
        print(f"Scaling Audit Error: {e}")
        return False, 1.0
