import unittest
from template_validation import TemplateValidator

class TestMathBlueprintValidator(unittest.TestCase):
    def setUp(self):
        self.hypothesis = {
            "target_complexity_score": 55,
            "required_constants": {"ALPHA": 1.5, "BETA": 2.0},
            "mathematical_implementation_guide": "must implement memory windows and resource depletion",
            "hypothesis": "Uses grunwald_letnikov_diff and ricci_curvature_scalar for anomalous behavior.",
            "topic": "Anomalous Relaxation Manifold"
        }

    def test_constant_algebraic_multiplier(self):
        # Good code using constants correctly
        good_code = """
# 1. SYMBOLIC SETUP
import sympy as sp
t, y = sp.symbols('t y')

# 2. CONSTANT INJECTION
constants = {'ALPHA': 1.5, 'BETA': 2.0}

# 3. THE IMMUTABLE LAW
expr = constants['ALPHA'] * y + constants['BETA'] * t
"""
        ok, issues = TemplateValidator.validate_constants(good_code, self.hypothesis)
        self.assertTrue(ok)
        
        # Bad code missing BETA and value mismatch
        bad_code = """
import sympy as sp
constants = {'ALPHA': 1.4} 
"""
        ok, issues = TemplateValidator.validate_constants(bad_code, self.hypothesis)
        self.assertFalse(ok)
        self.assertTrue(any("Missing constant: BETA" in i for i in issues))
        self.assertTrue(any("Value mismatch for ALPHA" in i for i in issues))

    def test_primitive_function_implementation(self):
        good_code = """
grunwald_letnikov_diff(f, t, y, ALPHA)
ricci_curvature_scalar(metric, point)
"""
        ok, issues = TemplateValidator.validate_primitive_alignment(good_code, self.hypothesis)
        self.assertTrue(ok)

        bad_code = "solve_ivp(f, t, y)"
        ok, issues = TemplateValidator.validate_primitive_alignment(bad_code, self.hypothesis)
        self.assertFalse(ok)
        self.assertTrue(any("grunwald_letnikov_diff" in i for i in issues))

    def test_mathematical_blueprint_validation_and_complexity(self):
        # Test complexity mandates based on Iteration 3501 (requires iterations and resource tokens)
        good_code = """
# 4. HIGH-FIDELITY EXECUTION
resource = 100
memory = []
for i in range(10):
    resource -= 1 # depletion
    memory.append(resource)
    if False: break # failure probability
"""
        ok, issues = TemplateValidator.validate_complexity_depth(good_code, self.hypothesis)
        self.assertTrue(ok)

        ok_struct, issues_struct = TemplateValidator.validate_structural_fidelity(good_code, self.hypothesis)
        self.assertTrue(ok_struct)

        bad_code = """
results = solve_ivp(f, (0, 10), [1.0])
"""
        ok, issues = TemplateValidator.validate_complexity_depth(bad_code, self.hypothesis)
        self.assertFalse(ok)

    def test_banned_methods(self):
        # Code with banned subs explicitly
        bad_code = """expr.subs('ALPHA', 1.5)"""
        ok, issues = TemplateValidator.validate_banned_patterns(bad_code)
        self.assertFalse(ok)
        self.assertTrue(any("banned operation '.subs()'" in i.lower() for i in issues))

if __name__ == '__main__':
    unittest.main()
