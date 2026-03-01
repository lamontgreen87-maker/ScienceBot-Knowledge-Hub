"""
Centralized Validation Module for Template Adherence and Scientific Rigor.
Inspired by Creator Suggestion 3456.
"""
import re
import json
import ast
import sys

def validate_hypothesis_schema(hypothesis_json):
    """Ensures the LLM-generated hypothesis follows the exact required schema."""
    required_keys = [
        "topic", "hypothesis", "physics_primer", "atomic_specification",
        "mathematical_blueprint", "mathematical_implementation_guide", 
        "required_constants"
    ]
    missing = [k for k in required_keys if k not in hypothesis_json]
    
    # Check atomic_specification sub-keys
    if "atomic_specification" in hypothesis_json:
        sub_keys = ["independent_variable", "dependent_variable", "symbolic_parameters"]
        for sk in sub_keys:
            if sk not in hypothesis_json["atomic_specification"]:
                missing.append(f"atomic_specification.{sk}")
                
    return len(missing) == 0, missing

def validate_fractional_primitives(code):
    """
    Checks if fractional calculus primitives (like grunwald_letnikov_diff)
    are used with correct argument structures.
    """
    issues = []
    
    # Check for grunwald_letnikov_diff usage
    if "grunwald_letnikov_diff" in code:
        # Simple regex to check for common argument errors
        # Expected: grunwald_letnikov_diff(f_func, t_eval, alpha, ...)
        if re.search(r'grunwald_letnikov_diff\s*\([^,)]+\s*\)', code):
            issues.append("grunwald_letnikov_diff called with too few arguments.")
            
    # Check for ricci_curvature_scalar usage
    if "ricci_curvature_scalar" in code:
        if "metric_func" not in code:
            issues.append("ricci_curvature_scalar requires a 'metric_func' definition.")
            
    return issues

def check_constant_usage_rigor(code, hypothesis):
    """
    Ensures constants are not just defined but actually used in the Immutable Law.
    """
    issues = []
    required_consts = hypothesis.get('required_constants', {})
    
    # Look for the section # 3. THE IMMUTABLE LAW
    law_match = re.search(r'# 3\. THE IMMUTABLE LAW(.*?)(?=# 4|$)', code, re.DOTALL)
    if not law_match:
        return ["Section '# 3. THE IMMUTABLE LAW' is missing or malformed."]
        
    law_content = law_match.group(1)
    
    for c in required_consts.keys():
        if c not in law_content and f"constants['{c}']" not in law_content:
            issues.append(f"Constant '{c}' is defined but not present in the Immutable Law.")
            
    return issues

def verify_constant_values(code, hypothesis):
    """
    Deterministically checks that values for constants in the code match the hypothesis.
    """
    issues = []
    required_consts = hypothesis.get('required_constants', {})
    
    # Extract constants dict from code using AST
    try:
        tree = ast.parse(code)
        code_constants = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'constants':
                        if isinstance(node.value, ast.Dict):
                            for k, v in zip(node.value.keys, node.value.values):
                                if isinstance(k, ast.Constant):
                                    # Handle numeric constants
                                    if isinstance(v, ast.Constant):
                                        code_constants[k.value] = v.value
                                    elif isinstance(v, ast.UnaryOp) and isinstance(v.op, ast.USub) and isinstance(v.operand, ast.Constant):
                                        code_constants[k.value] = -v.operand.value
        
        for name, expected_val in required_consts.items():
            if name in code_constants:
                actual_val = code_constants[name]
                try:
                    if abs(float(actual_val) - float(expected_val)) > 1e-6:
                        issues.append(f"Constant '{name}' value mismatch: Expected {expected_val}, got {actual_val}")
                except (ValueError, TypeError):
                    issues.append(f"Constant '{name}' has non-numeric value: {actual_val}")
            else:
                issues.append(f"Constant '{name}' defined in hypothesis but missing from code's 'constants' dictionary.")
    except Exception as e:
        issues.append(f"Failed to parse constants for value verification: {e}")
        
    return issues

def validate_primitive_runtime(code):
    """
    Attempts a minimal runtime 'smoke test' for advanced primitives.
    Only checks if the symbols exist and can be initialized.
    """
    issues = []
    if "grunwald_letnikov_diff" in code or "ricci_curvature_scalar" in code:
        # We don't want to run the FULL simulation, just check if the primitives are loadable
        import subprocess
        import os
        
        test_script = f"""
import sys
try:
    from sci_utils import grunwald_letnikov_diff, ricci_curvature_scalar
    # Success if we can import them
    sys.exit(0)
except Exception as e:
    print(e)
    sys.exit(1)
"""
        tmp_path = "tmp_primitive_test.py"
        with open(tmp_path, "w") as f:
            f.write(test_script)
            
        try:
            result = subprocess.run([sys.executable, tmp_path], capture_output=True, text=True, timeout=15)
            if result.returncode != 0:
                issues.append(f"Primitive Runtime Verification FAILED: {result.stdout.strip() or result.stderr.strip()}")
        except Exception as e:
            issues.append(f"Could not execute primitive runtime check: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    return issues

def check_complexity_depth(code, hypothesis):
    """
    Static analysis to ensure code isn't too simplistic.
    Thresholds scale with the target_complexity_score.
    """
    issues = []
    target = hypothesis.get('target_complexity_score', 40)
    try:
        # Handle "50-80" style ranges
        if isinstance(target, str) and '-' in target:
            target = int(target.split('-')[0])
        else:
            target = int(target)
    except:
        target = 40

    try:
        tree = ast.parse(code)
        loops = 0
        calls = 0
        ifs = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                loops += 1
            if isinstance(node, ast.Call):
                calls += 1
            if isinstance(node, ast.If):
                ifs += 1
                
        # Higher thresholds for higher target complexity
        min_loops = 1 if target < 60 else 2
        min_calls = 5 if target < 60 else 8
        
        if loops < min_loops:
            issues.append(f"Simulation lacks sufficient iterative loops ({loops}/{min_loops}). High-rigor simulations require nested state logic.")
        if calls < min_calls:
            issues.append(f"Low operational density ({calls}/{min_calls} calls). Expected higher fidelity logic for target complexity {target}.")
    except:
        pass 
    return issues

def verify_constant_multipliers(code, hypothesis):
    """
    Ensures required constants are used as algebraic multipliers (e.g. ALPHA * y)
    rather than being hardcoded or ignored in the physics logic.
    """
    issues = []
    required_consts = hypothesis.get('required_constants', {})
    
    # Check if the constants are present in the multiplication context
    # This is a heuristic check looking for '* CONSTANT' or 'CONSTANT *'
    for c in required_consts.keys():
        # Look for the constant used near a multiplication operator or as a factor
        pattern = rf'(\*|\/)\s*{c}\b|\b{c}\s*\*|\b{c}\s*\/'
        if not re.search(pattern, code):
            issues.append(f"Constant '{c}' is defined but not used as an algebraic multiplier. Hard-coding values or ignoring variables decreases simulation rigor.")
            
    return issues

def get_rigor_report(code, hypothesis):
    """
    Aggregates the high-level rigor checks for the Agent loop.
    """
    report = []
    
    # 1. Primitive usage (Static)
    report.extend(validate_fractional_primitives(code))
    
    # 2. Constant usage rigor (Presence in law)
    report.extend(check_constant_usage_rigor(code, hypothesis))
    
    # 3. Constant Value Verification (AST Value Match)
    report.extend(verify_constant_values(code, hypothesis))
    
    # 4. Constant Multiplier Check (Algebraic Scaling)
    report.extend(verify_constant_multipliers(code, hypothesis))
    
    # 5. Primitive Runtime Verification (Smoke Test)
    import sys 
    report.extend(validate_primitive_runtime(code))
    
    # 6. Complexity Depth check
    report.extend(check_complexity_depth(code, hypothesis))
    
    return report
