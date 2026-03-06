import subprocess
import os
import requests
import json
import re
from physical_constants import get_all_ground_truth
from base_module import BaseModule

class SimulationLab(BaseModule):
    COMPONENT_NAME = "lab"
    def __init__(self, config, ui=None, vm=None):
        super().__init__(config, ui)
        self.vm = vm

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
            primitive_mandate += "- **PRIMITIVE MANDATE**: Use `ricci_scalar_symbolic` with a real 4D `sp.Matrix` (e.g. Kerr/Schwarzschild). Placeholder matrices will be REJECTED.\n"
            physics_templates += """
### REFERENCE IMPLEMENTATION: Black Hole Metrics / Ricci Curvature
Use this EXACT pattern for 4D spacetime:
```python
# --- Correct 4D Metric Matrix Pattern ---
import sympy as sp
t, r, theta, phi = sp.symbols('t r theta phi', real=True)
M, a = sp.symbols('M a', real=True) # constants['M'], constants['A']
# Define the metric g_mu_nu (e.g. Kerr Metric components)
# ... define g_tt, g_rr, etc ...
g = sp.Matrix([
    [-(1 - 2*M*r/(r**2)), 0, 0, 0], 
    [0, 1/(1 - 2*M*r/(r**2)), 0, 0],
    [0, 0, r**2, 0],
    [0, 0, 0, r**2 * sp.sin(theta)**2]
]) # Schwarzschild example
coords = [t, r, theta, phi]
# Calculate symbolic curvature expression
curvature_expr = ricci_scalar_symbolic(g, coords)
# Use the symbolic curvature in your expr logic
expr = constants['ALPHA'] * curvature_expr
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
        
        # --- HIGH FIDELITY MANDATE (Ultra-Fidelity Upgrade) ---
        fidelity_level = self.config.get('research', {}).get('simulation_fidelity', 'STANDARD')
        
        if fidelity_level == 'ULTRA':
            fidelity_injection = """
### ULTRA-FIDELITY EXECUTION STANDARDS:
- **PRECISION MANTRA**: You MUST use `np.float64` for all arrays and `sp.Float(val, 64)` for constants.
- `TIME_STEPS = 10000` (Ultra-high resolution for horizon proximity)
- `DT = 0.001` (Micro-granular integration)
- `FAILURE_PROBABILITY = 0.005` (Reduced numerical noise)
- **GPU ACCELERATION**: Use `sp.lambdify(..., modules=['cupy'])` or `modules=['torch', 'numpy']` for tensor operations.
- **VRAM UTILIZATION**: Use large numerical grids (minimum 1000x1000). The A100/H100 VRAM is allocated for this.
"""
        else:
            fidelity_injection = """
### HIGH-FIDELITY EXECUTION STANDARDS:
Your code MUST define and utilize these specific complexity parameters:
- `TIME_STEPS = 2000`
- `DT = 0.01`
- `FAILURE_PROBABILITY = 0.02`
- **NUMPY CONVERSION**: You MUST use `sp.lambdify(..., 'numpy')` for all loop-based calculations. NEVER use `.subs()` or `.evalf()` for numerical updates.
"""
        if "Black Hole" in hypothesis.get('topic', '') or "Metric" in str(hypothesis):
            fidelity_injection += "\n**VRAM MANDATE**: This is a high-fidelity simulation. Use 500x500 or larger numerical grids where applicable. Your matrices must be real 4x4 spacetime tensors. Placeholder code will be REJECTED. Utilize the 288GB cluster capacity.\n"
            fidelity_injection += "\n**VACUUM MANDATE**: This simulation must satisfy the Vacuum Einstein Equations ($G_{\\mu\\nu} = 0$). An automatic audit script will verify your symbolic metric 'g'. If it is not a vacuum solution, the simulation will be REJECTED.\n"
        
        # --- FEATURE: HIERARCHICAL PROBLEM DECOMPOSITION ---
        # Broadened to include all complex Ricci/Geometric tasks that often hallucinate skeleton sections.
        is_complex_geometric = any(kw in str(hypothesis).lower() for kw in ["ricci flow", "ricci curvature", "metric tensor", "spacetime metric", "curvature tensor"])
        if is_complex_geometric:
            if self.ui: self.ui.print_log("\033[1;36m[LAB] Complex Geometric Task detected. Triggering Hierarchical Decomposition (3-Phase)...\033[0m")
            return self.decompose_geometric_task(hypothesis, description, model)

        try:
            prompt = SIMULATION_GENERATION_PROMPT.format(
                description=description,
                dynamic_rules=dynamic_rulebook_section,
                hypothesis_text=hypothesis.get('hypothesis', 'Advanced Theory'),
                symbol_guard_block=symbol_guard_block,
                blueprint=blueprint_block,
                constants_list=constants_list,
                context=hypothesis.get('simulation_context', 'Scientific scenario'),
                guide=hypothesis.get('mathematical_implementation_guide', 'N/A'),
                physics_templates=physics_templates,
                primitive_mandate=primitive_mandate + fidelity_injection,
                import_block=import_block,
                symbolic_setup=symbolic_setup,
                constants_dict_content=constants_dict_content,
                target_complexity_score=hypothesis.get('target_complexity_score', 40)
            )
        except KeyError as e:
            if self.ui: self.ui.print_log(f"\033[1;31m[CRITICAL] Simulation Prompt Formatting Error: Missing Key {e}\033[0m")
            return "Error: Internal mapping failure in laboratory generator."

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
        
        # --- FEATURE: SYMBOLIC MANIFOLD EXTRACTION ---
        # Append a snippet to the code to attempt to serialize 'g' (metric) and 'coords' 
        # so the Auditor can perform Bianchi checks.
        extraction_snippet = """
import sympy as sp
import json as _json
try:
    if 'g' in locals() and 'coords' in locals():
        # Serialize the metric and coords for the Auditor
        manifest = {
            "metric": str(g),
            "coords": [str(c) for c in coords]
        }
        print("\\n=== MANIFOLD_MANIFEST ===")
        print(_json.dumps(manifest))
        print("=== END_MANIFEST ===")
except:
    pass
"""
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(code + extraction_snippet)
            
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
            
            # --- MANIFOLD MANIFEST PARSING ---
            if "=== MANIFOLD_MANIFEST ===" in output:
                try:
                    manifest_segment = output.split("=== MANIFOLD_MANIFEST ===")[1].split("=== END_MANIFEST ===")[0]
                    manifest = json.loads(manifest_segment.strip())
                    
                    # Parse back into SymPy objects for the Auditor
                    from sympy import Matrix, symbols as sympy_symbols
                    from sympy.parsing.sympy_parser import parse_expr
                    
                    # 1. Parse coordinates
                    coords_syms = [sympy_symbols(c) for c in manifest['coords']]
                    
                    # 2. Parse metric matrix
                    # Setup local dict for parsing
                    local_dict = {str(s): s for s in coords_syms}
                    # Matrix(str) works for simple representations
                    g_expr = parse_expr(manifest['metric'], local_dict=local_dict)
                    
                    metrics['symbolic_metric'] = g_expr
                    metrics['coords'] = coords_syms
                except Exception as e:
                    if self.ui: self.ui.print_log(f"[LAB] ERROR parsing manifold manifest: {e}")

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

    def decompose_geometric_task(self, hypothesis, description, model=None):
        """
        Breaks down a complex Ricci Flow / Geometric task into 3 sequential phases
        to ensure high fidelity and executability.
        """
        topic = hypothesis.get('topic', 'Geometric Manifold')
        
        # Phase 1: Symbolic Manifold Definition
        if self.ui: self.ui.print_log("[LAB] DECOMPOSITION Phase 1: Symbolic Manifold Definition...")
        
        # Coordinate Resilience Mandate for Black Holes
        coord_mandate = ""
        if any(kw in topic.lower() for kw in ["black hole", "schwarzschild", "kerr", "singularity", "horizon"]):
            coord_mandate = "MANDATE: Use Eddington-Finkelstein or Kruskal-Szekeres coordinates to avoid horizon singularities (r=2M)."

        p1_prompt = f"""
### RICCI FLOW DECOMPOSITION: PHASE 1 (SYMBOLIC MANIFOLD)
Topic: {topic}
Task: Define the symbolic coordinate system and the metric tensor matrix `g`.
{coord_mandate}
REQUIRED: 
- Use `sp.symbols(..., real=True)`.
- Define a 4x4 `sp.Matrix` named `g`.
- Output ONLY the python code for this section. No preamble.
"""
        p1_code = self._query_llm(p1_prompt, model=model, temperature=0.1)
        p1_code = self._extract_code(p1_code)

        # Phase 2: Curvature & Flow Equations
        if self.ui: self.ui.print_log("[LAB] DECOMPOSITION Phase 2: Curvature & Flow Derivation...")
        p2_prompt = f"""
### RICCI FLOW DECOMPOSITION: PHASE 2 (CURVATURE & FLOW)
Topic: {topic}
Context: {p1_code}
Task: Using the metric `g` defined above, derive the Ricci Scalar / Tensor and formulate the Flow equation (dg/dt = -2*Ricci).
REQUIRED:
- Use `ricci_scalar_symbolic(g, coords)`.
- Define the symbolic `expr` for the flow.
- Output ONLY the python code for derivation and `expr` definition.
"""
        p2_code = self._query_llm(p2_prompt, model=model, temperature=0.1)
        p2_code = self._extract_code(p2_code)

        # Phase 3: Integration & Logging
        if self.ui: self.ui.print_log("[LAB] DECOMPOSITION Phase 3: Integration & Logging...")
        p3_prompt = f"""
### RICCI FLOW DECOMPOSITION: PHASE 3 (NUMERICAL INTEGRATION)
Topic: {topic}
Hypothesis: {hypothesis.get('hypothesis')}
Components: 
{p1_code}
{p2_code}
Task: Combine the above into a full executable script.
REQUIRED:
- Implement `np.float64` precision.
- Use `sp.lambdify` for the numerical loop.
- Include a `# 5. DATA LOGGING` section with `=== SCIENTIFIC_METRICS ===`.
- The final variable must be `sol_y` and `sol_t`.
"""
        final_code = self._query_llm(p3_prompt, model=model, temperature=0.2)
        return final_code

    def _extract_code(self, raw_text):
        if '```python' in raw_text:
            return raw_text.split('```python')[1].split('```')[0].strip()
        elif '```' in raw_text:
            return raw_text.split('```')[1].split('```')[0].strip()
        return raw_text.strip()
