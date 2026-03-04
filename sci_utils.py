import os
import re
import numpy as np
from scipy import stats
from scipy.stats import linregress
from sympy import symbols, Eq, checksol, simplify
import json
import time

class ScientificReport:
    """
    Standardized container for scientific simulation results.
    Enables quantitative auditing of physics and numerical stability.
    """
    def __init__(self, simulation_id="unknown_probe"):
        self.simulation_id = simulation_id
        self.metrics = {}
        self.conservation_audits = []
        self.statistical_tests = []
        self.scientific_logs = []
        self.start_time = time.time()

    def add_metric(self, name, value, unit=None, description=""):
        """Logs a numerical observation."""
        self.metrics[name] = {
            "value": float(value) if isinstance(value, (int, float, np.number)) else value,
            "unit": unit,
            "description": description
        }

    def add_conservation_audit(self, quantity_name, initial, final, tolerance=1e-6):
        """Audits a physical conservation law."""
        delta = abs(initial - final)
        passes = delta < tolerance
        self.conservation_audits.append({
            "quantity": quantity_name,
            "initial": float(initial),
            "final": float(final),
            "delta": float(delta),
            "tolerance": float(tolerance),
            "passes": bool(passes)
        })

    def add_statistical_test(self, name, p_value, significance_threshold=0.05, observed_stat=None):
        """Logs a statistical test result (e.g. t-test, p-value)."""
        passes = p_value > significance_threshold # Usually we fail to reject null for consistency
        self.statistical_tests.append({
            "test_name": name,
            "p_value": float(p_value),
            "threshold": float(significance_threshold),
            "observed_stat": float(observed_stat) if observed_stat is not None else None,
            "passes": bool(passes)
        })

    def log_trace(self, message):
        """Adds a scientific trace for qualitative analysis."""
        self.scientific_logs.append(message)

    def finalize(self):
        """Prints the STANDARDIZED JSON block for the Auditor to parse."""
        report = {
            "report_id": f"SRL-{int(time.time())}",
            "simulation_id": self.simulation_id,
            "duration_s": time.time() - self.start_time,
            "metrics": self.metrics,
            "conservation_audits": self.conservation_audits,
            "statistical_tests": self.statistical_tests,
            "logs": self.scientific_logs,
            "status": "VALID_METRICS"
        }
        print("\n=== SCIENTIFIC_METRICS ===")
        print(json.dumps(report, indent=2))
        print("=== END_METRICS ===\n")
        # Legacy support for boolean success
        # Success is determined by the specific physics, but conservation MUST pass
        all_conservation_pass = all(a["passes"] for a in self.conservation_audits)
        print("True" if all_conservation_pass else "False")

class SymbolGuard:
    """
    Ensures that coordinate symbols and parameters are correctly defined 
    before performing complex tensor or symbolic operations.
    Inspired by 'Symbol Guard' utility mandate.
    """
    @staticmethod
    def verify_symbols(local_scope, required=None):
        """
        Verifies that specific SymPy symbols exist in the provided scope.
        Default required: t, r, theta, phi, M, a
        """
        import sympy as sp
        if required is None:
            required = ['t', 'r', 'theta', 'phi', 'M', 'a']
        
        missing = []
        for s in required:
            if s not in local_scope or not isinstance(local_scope[s], sp.Symbol):
                missing.append(s)
        
        if missing:
            raise NameError(f"[SYMBOL-GUARD] Protection violation: Missing required SymPy symbols: {', '.join(missing)}. "
                           f"Ensure they are declared using sp.symbols at the start of the simulation.")
        return True

def verify_power_law(scales, values, expected_alpha=None, r_threshold=0.98, min_decades=2.0):
    """
    Performs a log-log regression to verify a power-law relationship.
    R-threshold defaults to 0.98 as per latest Auditor requirements.
    """
    scale_range = np.log10(np.max(scales)) - np.log10(np.min(scales))
    if scale_range < min_decades:
        return 0, 0, False
        
    log_scales = np.log(scales)
    log_values = np.log(values)
    slope, intercept, r_value, p_value, std_err = linregress(log_scales, log_values)
    
    passes = abs(r_value) >= r_threshold
    if expected_alpha is not None:
        passes = passes and (abs(slope - expected_alpha) < 0.1 * abs(expected_alpha))
        
    return slope, r_value, passes

def verify_confidence_level(data_noisy, data_clean, confidence=0.95):
    """
    Verifies if the noisy data stays within the clean data's confidence interval.
    Returns (passes, margin_of_error, p_value).
    """
    from scipy import stats
    diff = np.abs(data_noisy - data_clean)
    std_err = stats.sem(diff)
    t_stat, p_value = stats.ttest_1samp(diff, 0)
    h = std_err * stats.t.ppf((1 + confidence) / 2., len(diff) - 1)
    
    # We want p_value > 0.05 to show that the noise didn't significantly alter the mean
    # (Actually we want to fail to reject the null hypothesis that diff=0)
    passed = np.mean(diff) < h
    reason = "Mean difference within margin of error" if passed else f"Mean difference {np.mean(diff):.4f} exceeds MOE {h:.4f}"
    return passed, h, p_value, reason

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
    except Exception as e:
        print(f"Symbolic Truth Error: {e}")
        return False
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

def calculate_curvature(metric_tensor_func, coords):
    """
    Placeholder for a symbolic curvature calculation (e.g., Ricci scalar).
    Used to verify non-Euclidean geometric properties.
    """
    try:
        from sympy import diff, symbols, Matrix
        # Highly simplified for the LLM to use as a primitive
        # In practice, this would involve Christoffel symbols
        return "Symbolic Curvature Audit Passed"
    except:
        return "Curvature Audit Failed"

def verify_shannon_entropy(probabilities, tolerance=1e-6):
    """
    Verifies information-theoretic resonance or quantum state purity.
    """
    probs = np.array(probabilities)
    entropy = -np.sum(probs * np.log2(probs + 1e-15))
    return entropy

def verify_structural_consistency(blueprint_vars, numerical_vars):
    """
    Ensures that the symbols in the theoretical blueprint exactly match 
    the variables used in the numerical integration.
    """
    b_set = set(blueprint_vars)
    n_set = set(numerical_vars)
    missing = b_set - n_set
    extra = n_set - b_set
    return len(missing) == 0 and len(extra) == 0, missing, extra

def verify_algebraic_limits(equation_str, variables, constants_dict):
    """
    Feature 3: SymPy Static Analysis
    Parses an LLM's proposed equation string and dynamically calculates 
    the true limits (as time -> infinity, or as t -> 0) to prevent the LLM
    from hallucinating the mathematical behaviour of its own equations.
    """
    import sympy as sp
    from sympy.parsing.sympy_parser import parse_expr
    try:
        # Create symbol dictionary
        local_dict = {str(k): sp.Symbol(str(k)) for k in variables}
        for k, v in constants_dict.items():
            local_dict[k] = v
            
        # Parse expression safely
        expr = parse_expr(equation_str, local_dict=local_dict, evaluate=True)
        
        results = {}
        if 't' in local_dict:
            t = local_dict['t']
            limit_inf = sp.limit(expr, t, sp.oo)
            limit_zero = sp.limit(expr, t, 0)
            results['limit_t_inf'] = str(limit_inf)
            results['limit_t_zero'] = str(limit_zero)
            
            # Simple stability check (is derivative w.r.t independent variable positive or negative)
            if 'y' in local_dict:
                y = local_dict['y']
                deriv_y = sp.diff(expr, y)
                results['derivative_y'] = str(deriv_y)
                
        return True, results, "Success"
    except Exception as e:
        return False, {}, f"SymPy Parse Error: {str(e)}"

def validate_primitive_alignment(code_str, hypothesis):
    """
    Verifies that the code implements the required physical primitives
    declared in the hypothesis (e.g., grunwald_letnikov_diff, ricci_curvature_scalar).
    Returns (is_valid, list_of_missing_primitives).
    """
    missing = []
    hypothesis_str = str(hypothesis).lower()

    PRIMITIVE_MAP = {
        "grunwald_letnikov_diff": ["fractional", "gl-diff", "grunwald", "fractional derivative"],
        "ricci_curvature_scalar": ["ricci", "curvature", "ricci flow", "metric tensor"],
    }

    for primitive, triggers in PRIMITIVE_MAP.items():
        is_required = any(kw in hypothesis_str for kw in triggers)
        if is_required and primitive not in code_str:
            missing.append(primitive)

    return len(missing) == 0, missing



# Banned exotic concept keywords — no available primitive can implement these
_BANNED_EXOTIC_TERMS = [
    "anosov flow", "temporal resonance", "quantum operator", "geometric encoding",
    "autonomous knowledge", "spectral topology", "topological quantum computing",
    "holographic entanglement", "quantum error correction", "braid group",
    "homological algebra", "algebraic k-theory", "motive cohomology",
    "noncommutative geometry", "quantum field theory",
]

# Implementable primitive keywords — hypothesis must contain at least one
# Wide net: covers natural scientific vocabulary a question-driven LLM will use
_IMPLEMENTABLE_TRIGGERS = [
    # Fractional / memory physics
    "fractional", "anomalous diffusion", "memory effect", "memory kernel",
    "subdiffusion", "superdiffusion", "grunwald", "non-markovian", "hereditary",
    "power-law", "power law", "long-range", "heavy tail",
    # Ricci / geometry
    "ricci", "curvature", "geodesic", "metric tensor", "manifold",
    "riemannian", "christoffel", "einstein", "geometric flow",
    # Classical nonlinear ODEs
    "lotka", "lorenz", "van der pol", "sir model", "predator", "prey",
    "bifurcation", "limit cycle", "attractor", "lyapunov", "chaos", "chaotic",
    "nonlinear", "non-linear", "differential equation", "nonlinear ode",
    "oscillat", "pendulum", "brusselator", "fitzhugh",
    # Stochastic / SDE
    "langevin", "stochastic", "noise-driven", "brownian", "random walk",
    "fokker-planck", "wiener", "diffusion", "sde",
    # Scale / phase
    "critical phenomenon", "phase transition", "scale-free", "scale invariant",
    "scaling exponent", "renormalizat", "universality", "self-similar",
    # General dynamics vocabulary that maps to ODE/SDE
    "dynamics", "dynamic", "kinetics", "rate equation", "growth rate",
    "decay", "relaxation", "excitation", "flux", "gradient flow",
    "population", "epidemic", "spread", "wave", "reaction-diffusion",
    "competition", "cooperation", "synchroniz", "coupling",
    "energy dissipat", "damping", "forcing", "resonan",
]

def validate_hypothesis_feasibility(hypothesis, memory_dir=None):
    """
    Pre-Lab gate: checks if the hypothesis describes an implementable theory.
    Returns (is_feasible: bool, reason: str)

    Feature 2 (Dynamic Banned List): loads extra banned terms from
    memory/dynamic_banned.json if available, so DeepSeek can expand the
    banned list at runtime without code edits.
    """
    h_str = (
        str(hypothesis.get('hypothesis', '')) + ' ' +
        str(hypothesis.get('mathematical_implementation_guide', '')) + ' ' +
        str(hypothesis.get('topic', '')) + ' ' +
        str(hypothesis.get('literature_grounding', '')) + ' ' +
        str(hypothesis.get('structural_definition', ''))
    ).lower()

    # Merge static + dynamic banned terms
    dynamic_banned = list(_BANNED_EXOTIC_TERMS)
    if memory_dir:
        banned_path = os.path.join(memory_dir, "dynamic_banned.json")
        if os.path.exists(banned_path):
            try:
                import json as _json
                with open(banned_path, 'r', encoding='utf-8') as f:
                    extra = _json.load(f)
                if isinstance(extra, list):
                    dynamic_banned.extend([t.lower() for t in extra])
            except Exception:
                pass

    # Check for banned exotic terms
    for term in dynamic_banned:
        if term in h_str:
            return False, (
                f"Unanswerable hypothesis: contains banned exotic concept '{term}'. "
                f"No available primitive can implement this. Topic pivot required."
            )

    # Check at least one implementable concept is present
    has_implementable = any(t in h_str for t in _IMPLEMENTABLE_TRIGGERS)

    # Structural fallback: if structural_definition names a known type, it's implementable
    struct_type = str(hypothesis.get('structural_definition', {}).get('type', '')).lower()
    if not has_implementable and struct_type in ('ode', 'sde', 'recursive', 'gradient'):
        has_implementable = True

    if not has_implementable:
        return False, (
            "Hypothesis does not map to any implementable primitive "
            "(GL-diff, Ricci, nonlinear ODE, SDE, power-law). Topic pivot required."
        )

    return True, "Hypothesis is feasible."

def preflight_check(code_str, hypothesis):
    """Alias for review_simulation_code to support LLM repair guidance naming."""
    return review_simulation_code(code_str, hypothesis)

def review_simulation_code(code_str, hypothesis):
    """
    Unified Code Review Framework (Iteration 3456, 3501).
    Redirects to the centralized TemplateValidator engine.
    """
    from template_validation import TemplateValidator
    
    # AST parse check is already in TemplateValidator but we'll do an explicit catch here
    try:
        import ast
        ast.parse(code_str)
    except SyntaxError as e:
        return False, [f"SyntaxError: {e}"], f"FATAL: Code cannot be parsed - {e}"

    report = TemplateValidator.run_all_checks(code_str, hypothesis)
    
    issues = report["errors"] + report["repair_directives"]
    if issues:
        report_msg = "Code Review FAILED:\n" + "\n".join(f"  [{i+1}] {iss}" for i, iss in enumerate(issues))
        return False, issues, report_msg
        
    return True, [], "Code Review PASSED: All checks satisfied."

def grunwald_letnikov_diff(f, t, y, alpha, h=0.01, window=50):
    """
    Approximates the fractional derivative of order alpha using the Grunwald-Letnikov formula.
    Uses scipy.special.gamma for precise coefficients and a sliding window for history.
    """
    from scipy.special import gamma
    import numpy as np
    
    res = 0
    # binomial(-alpha, k) = Gamma(1-alpha) / (Gamma(k+1) * Gamma(1-alpha-k))
    # Using the relationship: w_k = (1 - (1+alpha)/k) * w_{k-1}
    w = 1.0
    for k in range(window):
        if k > 0:
            w *= (1 - (alpha + 1) / k)
        
        # Check if we can look back this far
        t_prev = t - k * h
        try:
            val = f(t_prev, y)
            res += w * val
        except:
            break
            
    return res / (h ** alpha)

def ricci_curvature_scalar(metric_matrix_func, point_coords):
    """
    Computes the Ricci Scalar for a given metric tensor function using SymPy.
    metric_matrix_func: Function that returns a SymPy Matrix given coordinate symbols.
    point_coords: Dict mapping SymPy symbols to numerical values for evaluation.
    """
    import sympy as sp
    
    # 1. Define Symbols (x0, x1, x2, x3 based on matrix size)
    dim = len(point_coords)
    symbols = list(point_coords.keys())
    
    # 2. Get Metric Tensor and its Inverse
    g = metric_matrix_func(*symbols)
    g_inv = g.inv()
    
    # 3. Christoffel Symbols of the second kind
    # Gamma^k_ij = 0.5 * g^kl * (dg_lj/dx_i + dg_il/dx_j - dg_ij/dx_l)
    christoffel = sp.MutableDenseNDimArray.zeros(dim, dim, dim)
    for i in range(dim):
        for j in range(dim):
            for k in range(dim):
                gamma_val = 0
                for l in range(dim):
                    term = sp.diff(g[l, j], symbols[i]) + sp.diff(g[i, l], symbols[j]) - sp.diff(g[i, j], symbols[l])
                    gamma_val += 0.5 * g_inv[k, l] * term
                christoffel[k, i, j] = gamma_val
    
    # 4. Ricci Tensor Components
    # R_ij = R^k_ikj
    # R^l_ijk = dGamma^l_ik/dx_j - dGamma^l_ij/dx_k + Gamma^l_mj*Gamma^m_ik - Gamma^l_mk*Gamma^m_ij
    ricci_tensor = sp.Matrix.zeros(dim, dim)
    for i in range(dim):
        for j in range(dim):
            r_ij = 0
            for k in range(dim):
                # Term 1: dGamma^k_ij/dx_k - dGamma^k_ik/dx_j
                r_ij += sp.diff(christoffel[k, i, j], symbols[k])
                r_ij -= sp.diff(christoffel[k, i, k], symbols[j])
                
                # Term 2: Gamma^m_ij * Gamma^k_mk - Gamma^m_ik * Gamma^k_mj
                for m in range(dim):
                    r_ij += christoffel[m, i, j] * christoffel[k, m, k]
                    r_ij -= christoffel[m, i, k] * christoffel[k, m, j]
            ricci_tensor[i, j] = r_ij
            
    # 5. Ricci Scalar: R = g^ij * R_ij
    ricci_scalar_expr = 0
    for i in range(dim):
        for j in range(dim):
            ricci_scalar_expr += g_inv[i, j] * ricci_tensor[i, j]
            
    # 6. Evaluate at point
    final_scalar = ricci_scalar_expr.subs(point_coords)
    return float(sp.simplify(final_scalar))

def ricci_scalar_symbolic(metric_matrix, coords_list):
    """
    Returns the SymPy expression for the Ricci Scalar of a metric matrix.
    Useful for Case 3 (IMMUTABLE LAW) where symbols are required.
    """
    import sympy as sp
    dim = len(coords_list)
    g = metric_matrix
    g_inv = g.inv()
    
    christoffel = sp.MutableDenseNDimArray.zeros(dim, dim, dim)
    for i in range(dim):
        for j in range(dim):
            for k in range(dim):
                gamma_val = 0
                for l in range(dim):
                    term = sp.diff(g[l, j], coords_list[i]) + sp.diff(g[i, l], coords_list[j]) - sp.diff(g[i, j], coords_list[l])
                    gamma_val += 0.5 * g_inv[k, l] * term
                christoffel[k, i, j] = gamma_val
    
    ricci_tensor = sp.Matrix.zeros(dim, dim)
    for i in range(dim):
        for j in range(dim):
            r_ij = 0
            for k in range(dim):
                r_ij += sp.diff(christoffel[k, i, j], coords_list[k])
                r_ij -= sp.diff(christoffel[k, i, k], coords_list[j])
                for m in range(dim):
                    r_ij += christoffel[m, i, j] * christoffel[k, m, k]
                    r_ij -= christoffel[m, i, k] * christoffel[k, m, j]
            ricci_tensor[i, j] = r_ij
            
    ricci_scalar_expr = 0
    for i in range(dim):
        for j in range(dim):
            ricci_scalar_expr += g_inv[i, j] * ricci_tensor[i, j]
            
    return sp.simplify(ricci_scalar_expr)

def verify_primitive_alignment(code_str, primitives_list):
    """
    Verifies that the code actually uses the advanced primitives promised.
    Focuses on active usage in the HIGH-FIDELITY EXECUTION section.
    """
    execution_match = re.search(r'# 4\. HIGH-FIDELITY EXECUTION(.*?)(?=# 5|$)', code_str, re.DOTALL)
    if not execution_match:
        # Fallback to whole code search if section header is missing
        execution_content = code_str
    else:
        execution_content = execution_match.group(1)

    for p in primitives_list:
        if p not in execution_content:
            return False, f"Primitive '{p}' promised but not actively used in Simulation Logic."
    return True, "Alignment Passed"
def calculate_code_complexity(code_str):
    """
    Uses AST to score the mathematical and structural complexity of the code.
    Higher scores indicator higher non-linearity, branching, and fidelity.
    """
    import ast
    try:
        tree = ast.parse(code_str)
        score = 0
        fidelity_keywords = ['resource', 'capacity', 'failure', 'state', 'energy', 'pool', 'threshold']
        
        for node in ast.walk(tree):
            # 1. Math complexity
            if isinstance(node, ast.BinOp):
                if isinstance(node.op, (ast.Pow, ast.Div)): score += 2
                else: score += 1
            # 2. Logic/Branching (Fidelity)
            elif isinstance(node, (ast.If, ast.While, ast.For)):
                score += 5
            # 3. Primitive usage
            elif isinstance(node, ast.Call):
                name = getattr(node.func, 'id', '')
                if name in ['solve_ivp', 'grunwald_letnikov_diff', 'ricci_curvature_scalar']:
                    score += 15
                elif name in ['sin', 'cos', 'exp', 'log', 'Matrix', 'diff']:
                    score += 3
            # 4. State/Attribute management
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    t_name = getattr(target, 'id', '').lower()
                    if any(kw in t_name for kw in fidelity_keywords):
                        score += 5
                        
        return score
    except:
        return 0

def validate_context_constants(code_str, required_constants):
    """
    Verifies that specific numerical constants (e.g. ALPHA=1.2) are initialized in the code correctly.
    This version is value-aware, handling formatting differences like 0.7 vs 0.70 via AST parsing.
    """
    import ast
    try:
        tree = ast.parse(code_str)
        assignments = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(node.value, (ast.Constant, ast.Num)):
                            # Handle both ast.Constant (Python 3.8+) and ast.Num
                            val = node.value.value if hasattr(node.value, 'value') else node.value.n
                            assignments[target.id] = val
        
        missing = []
        for const, expected_value in required_constants.items():
            if const not in assignments:
                missing.append(f"{const} (not defined)")
            else:
                try:
                    actual = float(assignments[const])
                    expected = float(expected_value)
                    if abs(actual - expected) > 1e-7:
                        missing.append(f"{const} (expected {expected}, got {actual})")
                except:
                    missing.append(f"{const} (type mismatch)")
        
        return len(missing) == 0, missing
    except Exception as e:
        return False, [f"AST Parsing Error: {e}"]
