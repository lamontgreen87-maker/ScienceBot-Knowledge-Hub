import subprocess
import os
import requests
import json
import re
from physical_constants import get_all_ground_truth
from base_module import BaseModule

class SimulationLab(BaseModule):
    COMPONENT_NAME = "lab"
    def __init__(self, config, ui=None):
        super().__init__(config, ui)

    def run_probe(self, concept, context, model=None):
        """
        Generates and executes a minimal mathematical probe.
        concept: The mathematical assumption/concept to test.
        context: Research context for the concept.
        """
        from prompt_templates import PROBE_GENERATION_PROMPT
        import subprocess
        import os

        if self.ui:
            self.ui.print_log(f"\033[1;36m[LAB] Generating exploratory probe: {concept[:60]}...\033[0m")

        prompt = PROBE_GENERATION_PROMPT.format(concept=concept, context=context)
        # Use the specialized math engine for probe generation (default to math_model if not provided)
        target_model = model or self.config['hardware'].get('math_model')
        response = self._query_llm(prompt, model=target_model, temperature=0.2)
        probe_data = self._extract_json(response)

        if not probe_data or 'code' not in probe_data:
            return "Probe Generation Failed"

        code = probe_data['code']
        temp_file = "probe_temp.py"
        
        # Ensure imports are present in the probe
        header = "import numpy as np\nimport sympy as sp\nfrom scipy.integrate import solve_ivp\n"
        full_code = header + code

        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(full_code)
            
            result = subprocess.run(
                ["python", temp_file], 
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
            
            if self.ui:
                self.ui.print_log(f"[LAB] Probe Result: {output[:100]}")
            
            return output if output else "No output from probe."
        except Exception as e:
            return f"Probe Execution Error: {e}"
        finally:
            if os.path.exists(temp_file):
                try: os.remove(temp_file)
                except: pass

    def _extract_hypothesis_numerics(self, hypothesis):
        """
        Extracts specific numeric claims from the hypothesis text so the code
        generator is forced to implement them rather than inventing arbitrary constants.
        Returns a dict of {CONSTANT_NAME: value_str}.
        Merges with required_constants (hypothesis wins on conflicts).
        """
        import re
        result = dict(hypothesis.get('required_constants', {}))

        # Scan hypothesis text + blueprint for patterns like z=1.5, alpha=0.7, BETA=2.3
        scan_text = " ".join([
            hypothesis.get('hypothesis', ''),
            hypothesis.get('mathematical_blueprint', ''),
            hypothesis.get('mathematical_implementation_guide', ''),
        ])

        # Match patterns: z=1.5, ALPHA=0.7, beta = 2.3, exponent z = 1.5
        patterns = [
            r'\b([A-Za-z][A-Za-z_]{0,8})\s*=\s*(-?\d+\.?\d*)',   # VAR = num
            r'\b(z|alpha|beta|eta|kappa|gamma|mu|nu|sigma|tau)\s*[=≈]\s*(-?\d+\.?\d*)',  # greek
        ]
        for pat in patterns:
            for m in re.finditer(pat, scan_text, re.IGNORECASE):
                name = m.group(1).upper()
                val  = m.group(2)
                # Skip obviously non-constant tokens
                if name in ('IF', 'IN', 'IS', 'AT', 'DO', 'OR', 'TO', 'BY', 'OF'):
                    continue
                if name not in result:   # don't override explicit required_constants
                    result[name] = val
        return result

    def generate_simulation(self, hypothesis, description, model=None):
        if self.ui:
            self.ui.print_log(f"[LAB] Generating high-fidelity simulation for: {hypothesis.get('topic', 'Unknown')}")

        atomic = hypothesis.get('atomic_specification', {})
        blueprint_symbols = atomic.get('symbolic_parameters', ['t', 'y'])
        ctx = hypothesis.get('simulation_context', 'N/A')
        
        # Advanced Primitive Detection
        needs_fractional = "fractional" in str(hypothesis).lower() or "grunwald" in str(hypothesis).lower()
        needs_ricci = "ricci" in str(hypothesis).lower() or "curvature" in str(hypothesis).lower()
        needs_manifold = "manifold" in str(hypothesis).lower() or "non-euclidean" in str(hypothesis).lower() or "metric tensor" in str(hypothesis).lower()

        primitive_mandate = ""
        physics_templates = ""

        if needs_fractional:
            primitive_mandate += "- **PRIMITIVE MANDATE**: Use `grunwald_letnikov_diff` for all fractional derivative orders. Standard solvers like `solve_ivp` are FORBIDDEN.\n"
            physics_templates += """
### REFERENCE IMPLEMENTATION: Fractional Derivative (GL-diff)
Use this EXACT pattern for fractional physics. Copy it and substitute your constants:
```python
# --- Correct GL-diff Pattern ---
ALPHA = 0.7  # fractional order (algebraic multiplier, NOT .subs())
t_vals = np.linspace(0, 5, 200); h = t_vals[1] - t_vals[0]
y_vals = [1.0]  # initial condition
f_rhs = sp.lambdify((t, y), expr, 'numpy')  # expr is your symbolic RHS
for i in range(1, len(t_vals)):
    dy = grunwald_letnikov_diff(lambda ti, yi: f_rhs(ti, yi), t_vals[i], y_vals[-1], ALPHA, h)
    y_vals.append(y_vals[-1] + dy * h)
sol_y = np.array(y_vals); sol_t = t_vals
```
"""
        if needs_ricci:
            primitive_mandate += "- **PRIMITIVE MANDATE**: Use `ricci_curvature_scalar` with a real metric matrix function. Placeholder matrices will be REJECTED.\n"
            physics_templates += """
### REFERENCE IMPLEMENTATION: Ricci Flow / Metric Tensor
Use this EXACT pattern:
```python
# --- Correct Metric Matrix Pattern ---
import sympy as sp
theta, phi = sp.symbols('theta phi', real=True)
# Define a real metric (e.g. S2 sphere metric)
def metric_func(coords):
    t, p = coords
    return np.array([[1.0, 0.0], [0.0, np.sin(t)**2 + 1e-9]])
point = [np.pi/4, np.pi/4]
curvature = ricci_curvature_scalar(metric_func, point)
print(f"Ricci Curvature: {curvature}")
```
"""
        if needs_manifold:
            physics_templates += """
### REFERENCE IMPLEMENTATION: Non-Euclidean Manifold / Memory Window
```python
# --- Correct Memory Window Pattern ---
WINDOW = 50  # history steps
memory = []
for i in range(1, len(t_vals)):
    memory.append(y_vals[-1])
    if len(memory) > WINDOW: memory.pop(0)
    weighted_hist = np.mean(memory) if memory else 0.0
    dy = f_rhs(t_vals[i], y_vals[-1]) + KAPPA * weighted_hist
    y_vals.append(y_vals[-1] + dy * h)
```
"""

        # Skeleton Adjustments
        import_block = "from scipy.integrate import solve_ivp"
        if needs_fractional:
            import_block = "# solve_ivp is FORBIDDEN for fractional physics."

        # Extract all numeric constants from hypothesis text + required_constants
        all_constants = self._extract_hypothesis_numerics(hypothesis)
        constants_list = "\n".join([f"- **{k}** = {v}  ← USE THIS EXACT VALUE" for k, v in all_constants.items()])
        if not constants_list:
            constants_list = "- No specific constants required beyond standard physics."

        # Blueprint enforcement block
        blueprint = hypothesis.get('mathematical_blueprint', '')
        blueprint_block = ""
        if blueprint:
            blueprint_block = f"""
### MANDATORY SYMBOLIC BLUEPRINT:
Your `expr` MUST reflect this equation. Do not substitute a generic ODE:
  {blueprint}
Every symbol in this equation must appear in your code as an algebraic constant or variable.
"""

        # Symbol Alignment Guard (Atomic Specification)
        atomic_spec = hypothesis.get('atomic_specification', {})
        ind_sym = atomic_spec.get('independent_variable', {}).get('symbol', 't')
        dep_sym = atomic_spec.get('dependent_variable', {}).get('symbol', 'y')
        symbol_guard_block = f"""
### SYMBOL ALIGNMENT GUARD (MANDATORY):
You MUST use these specific symbols from the hypothesis:
- Independent Variable: `{ind_sym}`
- Dependent Variable: `{dep_sym}`
If you use generic symbols like `y` when the hypothesis says `{dep_sym}`, the simulation will be REJECTED.
"""

        # --- FEATURE 3: SymPy Static Limit Injection ---
        if blueprint:
            from sci_utils import verify_algebraic_limits
            blueprint_vars = atomic_spec.get('symbolic_parameters', [])
            success, limits, err = verify_algebraic_limits(blueprint, blueprint_vars, all_constants)
            if success:
                symbol_guard_block += f"""
### ANALYTICAL TRUTH (SYMPY PRE-CALCULATED):
We have statically analyzed your equation `{blueprint}`.
The ACTUAL mathematical limits of this equation are:
- Limit as {ind_sym} -> infinity: {limits.get('limit_t_inf', 'Unknown')}
- Limit as {ind_sym} -> 0: {limits.get('limit_t_zero', 'Unknown')}
- Stability Derivative (dy/d{ind_sym}): {limits.get('derivative_y', 'Unknown')}
Your simulation code MUST reflect this algebraic reality. Do not fake or force limits that contradict this math.
"""
                if self.ui: self.ui.print_log(f"\033[1;36m[SYMPY] Calculated Truth Limits: t->inf = {limits.get('limit_t_inf')}\033[0m")
            else:
                if self.ui: self.ui.print_log(f"\033[1;33m[SYMPY] Static Analysis Failed: {err}\033[0m")

        # ── DYNAMIC RULEBOOK INJECTION ──
        dynamic_rulebook_section = ""
        import os
        rulebook_path = os.path.join(self.config['paths'].get('memory', ''), "dynamic_rulebook.json")
        if os.path.exists(rulebook_path):
            rules = self._safe_load_json(rulebook_path, default=[])
            if rules:
                formatted_rules = "\n".join([f"  {i+1}. {r}" for i, r in enumerate(rules)])
                dynamic_rulebook_section = f"""
=== DYNAMIC A.I. RULES (Learned from past failures — NON-NEGOTIABLE) ===
{formatted_rules}
=== END DYNAMIC RULES ===
"""
                if self.ui:
                    self.ui.print_log(f"\033[1;36m[LAB] Attached {len(rules)} Dynamic Rules to code generation constraint.\033[0m")

        # ── MODULAR PROMPT INJECTION ──
        from prompt_templates import SIMULATION_GENERATION_PROMPT
        
        # Prepare constants list and dict content
        all_constants = self._extract_hypothesis_numerics(hypothesis)
        constants_list = "\n".join([f"- **{k}** = {v}" for k, v in all_constants.items()])
        constants_dict_content = ",\n    ".join([f"'{k}': {v}" for k, v in all_constants.items()])

        symbolic_setup = f"t, {dep_sym} = sp.symbols('t {dep_sym}')"
        
        prompt = SIMULATION_GENERATION_PROMPT.format(
            description=description,
            dynamic_rules=dynamic_rulebook_section,
            hypothesis_text=hypothesis.get('hypothesis', 'N/A'),
            symbol_guard_block=symbol_guard_block,
            blueprint=hypothesis.get('mathematical_blueprint', 'N/A'),
            constants_list=constants_list or "None",
            context=ctx,
            guide=hypothesis.get('mathematical_implementation_guide', 'N/A'),
            physics_templates=physics_templates,
            primitive_mandate=primitive_mandate,
            import_block=import_block,
            symbolic_setup=symbolic_setup,
            constants_dict_content=constants_dict_content or "'DUMMY': 1.0",
            blueprint_symbols=str(blueprint_symbols),
            ground_truth_constants=json.dumps(get_all_ground_truth(), indent=4),
            target_complexity_score=hypothesis.get('target_complexity_score', 20)
        )
        # Prioritize the specialized math engine for high-fidelity simulation generation
        return self._query_llm(prompt, model=model, temperature=0.2)

    def run_simulation(self, code, hypothesis):
        if not code:
            return {"hypothesis": hypothesis, "raw_output": "Error: No code generated", "status": "Failed"}

        if '```python' in code:
            code = code.split('```python')[1].split('```')[0]
        elif '```' in code:
            code = code.split('```')[1].split('```')[0]
            
        # Pre-simulation Validation: Unified Code Review Framework (Iteration 3456, 3501)
        from template_validation import TemplateValidator
        
        report = TemplateValidator.run_all_checks(code, hypothesis)
        if not report["valid"]:
            issues = report["errors"] + report["repair_directives"]
            if self.ui:
                self.ui.print_log(f"[LAB] Code Rigor Audit FAILED ({len(issues)} issues). Queuing for repair.")
                for iss in issues[:3]:
                    self.ui.print_log(f"  ↳ {iss}")
            
            # Construct a clear failure message for the repair loop
            feedback = "SIMULATION RIGOR AUDIT FAILED.\n"
            if report["errors"]:
                feedback += "Structural Errors:\n- " + "\n- ".join(report["errors"]) + "\n"
            if report["repair_directives"]:
                feedback += "Repair Directives (NON-NEGOTIABLE):\n- " + "\n- ".join(report["repair_directives"])
                
            return {"hypothesis": hypothesis, "raw_output": f"Preflight Rejection: {feedback}", "status": "Failed", "code": code}
        
        # Complexity check (informational pass/warn — already in review but log separately)
        raw_complexity = str(hypothesis.get('target_complexity_score', 20))
        target_complexity = 20
        match = re.search(r'(\d+)', raw_complexity)
        if match:
            target_complexity = int(match.group(1))
        actual_complexity = calculate_code_complexity(code)
        if self.ui:
            self.ui.print_log(f"[LAB] Code Review PASSED. Complexity: {actual_complexity}/{target_complexity}")
        

        script_path = os.path.join(self.config['paths']['tests'], "last_simulation.py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(code)
            
        target_complexity = int(hypothesis.get('target_complexity_score', 20))
        base_timeout = 20 + target_complexity # Scale timeout with complexity
        multiplier = self.get_system_health()
        current_timeout = base_timeout * (2 if multiplier < 1.0 else 1)
        
        try:
            result = subprocess.run(['python', script_path], capture_output=True, timeout=current_timeout, text=True)
            output = result.stdout.strip()
            
            # Extract Scientific Metrics JSON
            metrics = {}
            if "=== SCIENTIFIC_METRICS ===" in output:
                try:
                    metrics_segment = output.split("=== SCIENTIFIC_METRICS ===")[1].split("=== END_METRICS ===")[0]
                    metrics = json.loads(metrics_segment.strip())
                except:
                    pass

            return {
                "hypothesis": hypothesis,
                "raw_output": output,
                "metrics": metrics,
                "status": "Success" if "True" in output.splitlines()[-2:] else "Failed",
                "code": code
            }
        except subprocess.TimeoutExpired:
            return {"hypothesis": hypothesis, "raw_output": "Timeout", "status": "Failed", "code": code}
        except Exception as e:
            return {"hypothesis": hypothesis, "raw_output": str(e), "status": "Error", "code": code}

    def repair_simulation(self, broken_code, feedback, hypothesis, model=None, searcher=None):
        """
        Uses LLM to fix a simulation script based on Auditor/Preflight feedback.
        Also injects dream-phase audit guidance and Stack Overflow assistance.
        """
        if self.ui:
            self.ui.print_log(f"[LAB] Triggering Repair Phase: Addressing feedback...")
        
        # ── Step 1: Technical Support (Suggestion 3481) ──
        support_context = ""
        if searcher and any(term in feedback.lower() for term in ['error', 'numpy', 'scipy', 'logic', 'recursion']):
            self.ui.print_log("[LAB] Searching Stack Overflow for technical fix...")
            # Extract the specific error or key terms from feedback
            query_terms = feedback.split(':')[-1].strip()[:50]
            so_results = searcher.search_technical(query_terms, site_type='stackoverflow', max_results=2)
            if so_results:
                support_context = "\n### STACK OVERFLOW TECHNICAL CONTEXT:\n"
                for res in so_results:
                    support_context += f"  - {res['title']}: {res['body'][:500]}\n"
        
        # ── Step 2: Dream-phase audit guidance extraction ──
        dream_guidance_block = ""
        try:
            import os as _os
            guidance_path = _os.path.join(self.config['paths']['memory'], "dream_audit_guidance.json")
            guidance_log = self._safe_load_json(guidance_path, default=[])
            if guidance_log:
                latest = guidance_log[-1]
                repair_addition = latest.get('repair_prompt_addition', '')
                violated = latest.get('violated_criteria', [])
                if repair_addition or violated:
                    dream_guidance_block = "\n### DREAM-PHASE AUDIT INTELLIGENCE:\n"
                    if violated:
                        for v in violated:
                            dream_guidance_block += f"  - {v.get('criterion_name','?')}: {v.get('repair_directive','')}\n"
                    if repair_addition:
                        dream_guidance_block += f"  - Note: {repair_addition}\n"
        except Exception:
            pass

        # ── Step 3: Prompt Construction ──
        from prompt_templates import REPAIR_PROMPT
        
        # Aggregate feedback types into the audit_report
        audit_report = f"MAIN FEEDBACK: {feedback}\n"
        if dream_guidance_block:
            audit_report += dream_guidance_block
        if support_context:
            audit_report += support_context
            
        prompt = REPAIR_PROMPT.format(
            topic=hypothesis.get('topic', 'Unknown'),
            hypothesis=hypothesis.get('hypothesis', 'N/A'),
            implementation_guide=hypothesis.get('mathematical_implementation_guide', 'N/A'),
            audit_report=audit_report
        )
        # Repair phase is highly mathematical; prioritize the specialized engine
        return self._query_llm(prompt, model=model, temperature=0.2)
