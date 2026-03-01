import re
import json
import ast
from json_utils import extract_json

class TemplateValidator:
    """
    Centralized validation engine inspired by Creator Suggestions 3456, 3466, 3481, 3501, 3511.
    Ensures absolute compliance with scientific templates and mathematical consistency.
    """
    
    MANDATORY_SECTIONS = [
        "1. SYMBOLIC SETUP",
        "2. CONSTANT INJECTION",
        "3. THE IMMUTABLE LAW",
        "4. HIGH-FIDELITY EXECUTION",
        "5. DATA LOGGING"
    ]

    ALLOWED_DEF_PREFIXES = (
        'verify_', 'add_', 'metric_', 'preflight_', 'symbolic_',
        'simulation_loop', 'update_state', 'physics_model', 'env_func', 
        'rho_func', 'metric_func', 'helper_', 'resource_', 'calculate_'
    )

    BANNED_DEF_NAMES = (
        'fractional_ode', 'solve_fractions', 'solve_system', 'rhs', 'ode_func'
    )

    @staticmethod
    def validate_template_structure(code):
        """Checks for the presence of the 5-part mandatory skeleton (Suggestion 3501)."""
        missing = []
        for section in TemplateValidator.MANDATORY_SECTIONS:
            # Check for standard header markers (e.g. # 1. SYMBOLIC SETUP)
            if section not in code:
                missing.append(section)
        return len(missing) == 0, missing

    @staticmethod
    def validate_constants(code, hypothesis):
        """Verifies constants are defined and match hypothesis exactly (Suggestion 3501, 3511)."""
        issues = []
        required_consts = hypothesis.get('required_constants', {})
        
        try:
            tree = ast.parse(code)
            code_constants = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == 'constants':
                            if isinstance(node.value, ast.Dict):
                                for k, v in zip(node.value.keys, node.value.values):
                                    key_name = None
                                    if hasattr(k, 'value'): # Python 3.8+
                                        key_name = k.value
                                    elif hasattr(k, 's'):
                                        key_name = k.s
                                        
                                    if key_name:
                                        if isinstance(v, ast.Constant):
                                            code_constants[key_name] = v.value
                                        elif isinstance(v, ast.UnaryOp) and isinstance(v.op, ast.USub) and isinstance(v.operand, ast.Constant):
                                            code_constants[key_name] = -v.operand.value
            
            for name, expected in required_consts.items():
                if name not in code_constants:
                    issues.append(f"Missing constant: {name} is required by the hypothesis but missing from 'constants' dict.")
                else:
                    actual = code_constants[name]
                    try:
                        if abs(float(actual) - float(expected)) > 1e-7:
                            issues.append(f"Value mismatch for {name}: Expected {expected}, got {actual}")
                    except (ValueError, TypeError):
                        issues.append(f"Non-numeric value for {name}: {actual}")
        except Exception as e:
            issues.append(f"AST parsing failed for constants check: {str(e)}")
            
        return len(issues) == 0, issues

    @staticmethod
    def validate_banned_patterns(code):
        """Strictly enforces prohibitions against .subs() and custom physics defs (Iteration 3481, 3501)."""
        issues = []
        
        # 1. Regex check for .subs() (Banned in code, allowed in comments)
        subs_found = False
        for line in code.splitlines():
            if '.subs' in line and not line.strip().startswith('#'):
                subs_found = True
                break
        if subs_found:
            issues.append("REPAIR DIRECTIVE: Banned operation '.subs()' detected. Use algebraic multipliers (e.g. ALPHA * y) instead of substitution.")

        # 2. AST check for unauthorized 'def' blocks
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check for explicitly banned names (often used as crutches)
                    if node.name in TemplateValidator.BANNED_DEF_NAMES:
                        issues.append(f"REPAIR DIRECTIVE: Forbidden 'def' block: '{node.name}'. Use 'lambdify' for physics or the provided high-fidelity skeleton.")
                    
                    # Check for prefixes (must be a known helper)
                    elif not node.name.startswith(TemplateValidator.ALLOWED_DEF_PREFIXES):
                        issues.append(f"REPAIR DIRECTIVE: Unauthorized 'def' block: '{node.name}'. Physics laws must be explicit (lambdify/lambda); helpers must use allowed prefixes (e.g. metric_func, helper_).")
        except:
            pass # Syntax errors handled elsewhere

        return len(issues) == 0, issues

    @staticmethod
    def validate_complexity_depth(code, hypothesis):
        """Ensures 'High-Fidelity' requirements (Iteration 3336, 3501)."""
        issues = []
        target = hypothesis.get('target_complexity_score', 40)
        try:
            if isinstance(target, str) and '-' in target:
                target = int(target.split('-')[0])
            target = int(target)
        except:
            target = 40

        # High-Fidelity keywords from Creator Suggestion (Iteration 3336)
        fidelity_keywords = [
            'resource', 'capacity', 'failure', 'probability', 'depletion', 
            'decay', 'threshold', 'history', 'window', 'buffer', 'steps', 
            'iteration', 'noise', 'stochastic'
        ]
        
        matches = [kw for kw in fidelity_keywords if kw in code.lower()]
        
        if target >= 50 and len(matches) < 3:
            issues.append(f"REPAIR DIRECTIVE: Low Logic Fidelity. For complexity {target}, you MUST implement granular state transitions (resource depletion, failure probabilities, or history windows).")

        # Basic structure check (loops)
        # Using regex for speed, but AST is better if needed
        loops = len(re.findall(r'for\s+|while\s+', code))
        min_loops = 2 if target >= 60 else 1
        if loops < min_loops:
            issues.append(f"REPAIR DIRECTIVE: Insufficient simulation depth. Expected at least {min_loops} iterative loops.")

        return len(issues) == 0, issues

    @staticmethod
    def validate_structural_fidelity(code, hypothesis):
        """Ensures promised architectural patterns are actually implemented (Iteration 3511)."""
        issues = []
        guide = hypothesis.get('mathematical_implementation_guide', '').lower()
        
        # 1. Memory Window / Buffer Check
        if 'memory window' in guide or 'buffer' in guide or 'rolling' in guide:
            # Look for list initialization and append/pop or slicing
            if not (re.search(r'\[\s*\]', code) and ('.append(' in code or 'pop(0)' in code or '[-' in code)):
                issues.append("REPAIR DIRECTIVE: Missing 'Memory Window' implementation. The guide requires a rolling buffer (e.g., a list with append/pop) to store historical states.")

        # 2. Fractal Map / Scaling Check
        if 'fractal map' in guide or 'scaling' in guide:
            # Look for power operations or recursive-like loops
            if not (re.search(r'\*\*\s*[\d\.]+', code) or 'alpha' in code.lower()):
                issues.append("REPAIR DIRECTIVE: Missing 'Fractal Map' logic. The guide requires explicit power-law scaling or fractal dimension mapping (e.g., y ** (1/alpha)).")

        # 3. Resource Pool / Depletion Check
        if 'resource' in guide or 'depletion' in guide or 'pool' in guide:
            # Look for a resource variable being decremented in a loop
            if not re.search(r'(\w+)\s*-=\s*', code):
                issues.append("REPAIR DIRECTIVE: Missing 'Resource Pool' logic. The guide requires a resource variable that depletes over time steps.")

        return len(issues) == 0, issues

    @staticmethod
    def validate_vocabulary_alignment(code, hypothesis):
        """Checks if domain-specific terms are present in the code or comments (Suggestion 3511)."""
        issues = []
        # Extract keywords from hypothesis and context
        combined_text = (hypothesis.get('topic', '') + " " + hypothesis.get('hypothesis', '') + " " + hypothesis.get('simulation_context', '')).lower()
        
        # Common physics/math keywords to look for
        key_terms = re.findall(r'\b[a-z]{5,}\b', combined_text)
        stop_words = {'through', 'between', 'against', 'during', 'without', 'because', 'should', 'would', 'could', 'about', 'these', 'those', 'their', 'there'}
        key_terms = [t for t in set(key_terms) if t not in stop_words]
        
        # Check if at least some the key terms appear in the code (low bar: 10%)
        matches = [t for t in key_terms if t in code.lower()]
        if len(key_terms) > 3 and len(matches) / len(key_terms) < 0.1:
            issues.append(f"REPAIR DIRECTIVE: Low Vocabulary Alignment. The code does not use terminology from the hypothesis (e.g., {', '.join(list(key_terms)[:3])}). Add comments reflecting the physics.")
            
        return len(issues) == 0, issues

    @staticmethod
    def validate_primitive_alignment(code, hypothesis):
        """Ensures promised primitives are actually called (Iteration 3456, 3471)."""
        issues = []
        hypothesis_str = str(hypothesis).lower()
        
        PRIMITIVE_MAP = {
            "grunwald_letnikov_diff": ["fractional", "gl-diff", "grunwald"],
            "ricci_curvature_scalar": ["ricci", "curvature", "ricci flow"],
        }
        
        for p, triggers in PRIMITIVE_MAP.items():
            if any(t in hypothesis_str for t in triggers):
                if p not in code:
                    issues.append(f"REPAIR DIRECTIVE: Missing required primitive '{p}' as indicated by the hypothesis physics.")

        return len(issues) == 0, issues

    @staticmethod
    def validate_geometric_fidelity(code, hypothesis):
        """Checks for Metric Tensor (sp.Matrix) when Curvature/Ricci is promised."""
        issues = []
        h_str = str(hypothesis).lower()
        
        # Triggers for General Relativity / Differential Geometry
        geo_triggers = ["ricci", "curvature", "metric tensor", "manifold", "geodesic", "riemannian"]
        
        if any(t in h_str for t in geo_triggers):
            # Look for sp.Matrix or Matrix definition
            if not (re.search(r'Matrix\s*\(', code) or re.search(r'sp\.Matrix\s*\(', code)):
                issues.append("REPAIR DIRECTIVE: Missing Metric Tensor. Your hypothesis requires geometric curvature, but no 'sp.Matrix' was defined for the metric tensor 'g'.")
            
            # Look for ricci_curvature_scalar primitive call
            if "ricci" in h_str and "ricci_curvature_scalar" not in code:
                issues.append("REPAIR DIRECTIVE: Missing Ricci Primitive. Use 'ricci_curvature_scalar(metric_func, coords)' to compute curvature.")

        return len(issues) == 0, issues

    @staticmethod
    def validate_symbolic_injection(code, hypothesis):
        """Ensures all hypothesis constants are registered in sp.symbols()."""
        issues = []
        required_consts = hypothesis.get('required_constants', {})
        
        if not required_consts:
            return True, []

        # Find the line starting with sp.symbols or symbols
        symbol_match = re.search(r'symbols\s*\(\s*[\'"](.*?)[\'"]', code)
        if not symbol_match:
            issues.append("REPAIR DIRECTIVE: Missing symbolic registration. Use 'sp.symbols()' to define your independent and dependent variables.")
        else:
            registered_symbols = set(re.split(r'[\s,]+', symbol_match.group(1)))
            for const in required_consts.keys():
                if const not in registered_symbols:
                    issues.append(f"REPAIR DIRECTIVE: Constant '{const}' is used but not registered in sp.symbols(). Add it to the symbols() call.")
                    
        return len(issues) == 0, issues

    @staticmethod
    def run_all_checks(code, hypothesis):
        """Executes the complete unified rigor suite."""
        report = {
            "valid": True,
            "errors": [],
            "repair_directives": []
        }
        
        # 1. Base Structure
        ok, m_issues = TemplateValidator.validate_template_structure(code)
        if not ok:
            report["valid"] = False
            report["errors"].append(f"Missing mandatory template sections: {', '.join(m_issues)}")
            
        # 2. Constants (Injection + Value Match)
        ok, c_issues = TemplateValidator.validate_constants(code, hypothesis)
        if not ok:
            report["valid"] = False
            report["errors"].extend(c_issues)
            
        # 3. Banned Patterns (.subs, def)
        ok, b_issues = TemplateValidator.validate_banned_patterns(code)
        if not ok:
            report["valid"] = False
            report["repair_directives"].extend(b_issues)
            
        # 4. Complexity & Fidelity
        ok, d_issues = TemplateValidator.validate_complexity_depth(code, hypothesis)
        if not ok:
            report["valid"] = False
            report["repair_directives"].extend(d_issues)
            
        # 5. Structural Fidelity (Memory Windows, etc.)
        ok, s_issues = TemplateValidator.validate_structural_fidelity(code, hypothesis)
        if not ok:
            report["valid"] = False
            report["repair_directives"].extend(s_issues)

        # 6. Primitive Alignment
        ok, a_issues = TemplateValidator.validate_primitive_alignment(code, hypothesis)
        if not ok:
            report["valid"] = False
            report["repair_directives"].extend(a_issues)

        # 7. Vocabulary Alignment
        ok, v_issues = TemplateValidator.validate_vocabulary_alignment(code, hypothesis)
        if not ok:
            report["valid"] = False
            report["repair_directives"].extend(v_issues)

        # 8. Geometric Fidelity
        ok, g_issues = TemplateValidator.validate_geometric_fidelity(code, hypothesis)
        if not ok:
            report["valid"] = False
            report["repair_directives"].extend(g_issues)

        # 9. Symbolic Injection
        ok, i_issues = TemplateValidator.validate_symbolic_injection(code, hypothesis)
        if not ok:
            report["valid"] = False
            report["repair_directives"].extend(i_issues)
            
        return report
