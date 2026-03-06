from base_module import BaseModule
import json

class Auditor(BaseModule):
    COMPONENT_NAME = "critic"
    def __init__(self, config, ui=None):
        super().__init__(config, ui)

    def verify(self, test_result):
        if self.ui:
            self.ui.print_log(f"[AUDITOR] Rigorous auditing of: {test_result['hypothesis']['topic']}")
        
        code = test_result.get('code', '')
        output = test_result.get('raw_output', '')
        hypothesis = test_result.get('hypothesis', {})
        
        # ── DETERMINISTIC PREFLIGHT CHECK ──
        from template_validation import TemplateValidator
        report = TemplateValidator.run_all_checks(code, hypothesis)
        preflight_failed = not report["valid"]
        preflight_issues = report["errors"] + report["repair_directives"] if preflight_failed else []

        # We will check if we should return preflight results now, or wait for physics checks
        from physics_validator import PhysicsValidator
        is_adm_simulation = PhysicsValidator.should_trigger_adm_check(hypothesis)

        if preflight_failed and not is_adm_simulation:
            if self.ui:
                self.ui.print_log(f"\033[1;33m[AUDITOR] Deterministic Preflight FAILED ({len(preflight_issues)} issues).\033[0m")
            return {
                "audit_passed": False,
                "rejection_type": "FIXABLE",
                "test_coverage": "Failed Preflight",
                "cheat_detected": False,
                "reasoning": "Deterministic failure: " + " | ".join(preflight_issues)
            }

        # --- FEATURE 3: SymPy Static Limit Verification for the Auditor ---
        analytical_truth_block = ""
        blueprint = hypothesis.get('mathematical_blueprint', '')
        if blueprint:
            from sci_utils import verify_algebraic_limits
            atomic_spec = hypothesis.get('atomic_specification', {})
            blueprint_vars = atomic_spec.get('symbolic_parameters', [])
            all_constants = test_result.get('metrics', {}).get('extracted_constants', {}) # Pass empty dict if not parsed yet
            success, limits, err = verify_algebraic_limits(blueprint, blueprint_vars, all_constants)
            
            if success:
                analytical_truth_block = f"""
8. **Mathematical Truth Alignment (CRITICAL)**: SymPy statically analyzed `{blueprint}` and found its limit as t->inf is {limits.get('limit_t_inf')}. Does the output numerical behavior align with this analytical limit? REJECT if the code fails to match the mathematical truth.
"""
        
        prompt = f"""
As a Technical Auditor, review this Scientific Simulation code and output:

Hypothesis: {hypothesis.get('hypothesis', 'N/A')}
Simulation Code:
{code}
Output: {output}
Scientific Metrics:
{json.dumps(test_result.get('metrics', {}), indent=2)}

=== MANDATORY COMPLIANCE CHECKLIST ===
1. **The 'constants' Dictionary**: Does the code define `constants = {{ ... }}` with the exact hypothesis values?
2. **Template Compliance**: Does the code contain ALL 5 mandatory skeleton comments?
3. **Symbol Alignment**: Are the symbols (`t`, `y`, etc.) matched exactly from the hypothesis?
4. **Primitive Integrity**: If fractional calculus is used, is `grunwald_letnikov_diff` present with a manual loop? REJECT if `solve_ivp` is used for fractional.
5. **No Negative Evidence**: REJECT if `.subs()` or `def` blocks (excluding allowed utilities) are detected.
6. **Scientific Rigor**: Does the code implement the specific 'Mathematical Implementation Guide' from the hypothesis?
7. **Quantitative Soundness**: Review the 'Scientific Metrics'. REJECT if conservation audits fail (passes: false) or if metrics are missing entirely for non-trivial hypotheses.{analytical_truth_block}

Respond in JSON ONLY:
{{
    "audit_passed": true/false,
    "rejection_type": "FIXABLE|FATAL|NONE",
    "test_coverage": "summary of cases checked",
    "cheat_detected": true/false,
    "reasoning": "technical explanation (be extremely specific for FIXABLE)"
}}
JSON:"""
        # Math-First: Symbolic verification is best handled by Qwen-Math.
        target_model = self.config['hardware'].get('math_model') or self.config['hardware'].get('reasoning_model')

        if self.ui:
            self.ui.print_log(f"[AUDITOR] Performing symbolic check using {target_model}...")

        response = self._query_llm(prompt, model=target_model)
        from json_utils import extract_and_validate
        audit, error = extract_and_validate(response, "audit")
        
        # ── RETRY LOOP (Creator Suggestion 3456) ──
        if error:
            if self.ui:
                self.ui.print_log(f"\033[1;33m[AUDITOR] JSON Validation Error: {error}. Retrying Turn 2...\033[0m")
            
            retry_prompt = prompt + f"\n\nCRITICAL JSON ERROR: {error}. Respond ONLY with a valid JSON object matching the required schema."
            response = self._query_llm(retry_prompt, model=target_model)
            audit, error = extract_and_validate(response, "audit")

        if audit:
            # ── FEATURE: ADM PHYSICS AUDIT (Hamiltonian Constraint) ──
            from physics_validator import PhysicsValidator
            if PhysicsValidator.should_trigger_adm_check(hypothesis):
                if self.ui:
                    self.ui.print_log("[AUDITOR] ADM 3+1 / GR detected. Triggering Hamiltonian Constraint check...")
                
                is_valid, h_val, is_singularity, physics_reasoning = PhysicsValidator.calculate_hamiltonian_constraint(test_result)
                
                if not is_valid:
                    audit["audit_passed"] = False
                    
                    if is_singularity:
                        reasoner_model = self.config['hardware'].get('reasoning_model')
                        if self.ui:
                            self.ui.print_log(f"\033[1;31m[AUDITOR] FATAL COORDINATE SINGULARITY: {h_val:.2e}. Requesting PUNCTURE METHOD fix...\033[0m")
                        
                        analysis_prompt = f"""
                        FATAL ERROR: ADM Hamiltonian Constraint Violation ({h_val:.2e} > 1e-4).
                        Topic: {hypothesis.get('topic')}
                        Status: Coordinate Singularity Detected.
                        
                        The current simulation has collapsed due to a coordinate singularity. 
                        MANDATORY FIX: You MUST implement the 'Puncture Method' (moving-puncture or fixed-puncture) to handle the singularity without coordinate collapse.
                        
                        1. Re-analyze the metric decomposition.
                        2. Provide a specific mathematical patch using the Puncture Method.
                        3. Update the 'mathematical_implementation_guide' to include puncture handling.

                        Simulation Code:
                        {code}
                        """
                        analysis = self._query_llm(analysis_prompt, model=reasoner_model)
                        
                        audit["rejection_type"] = "FATAL"
                        audit["reasoning"] = f"{physics_reasoning}\n\n=== PUNCTURE METHOD DIAGNOSIS ===\n{analysis}"
                    else:
                        # Regular validation failure (small H violation)
                        audit["rejection_type"] = "FIXABLE"
                        audit["reasoning"] = physics_reasoning
                else:
                    if self.ui:
                        self.ui.print_log(f"\033[1;32m[AUDITOR] Hamiltonian Constraint check passed ({h_val:.2e}).\033[0m")
                
                # --- VACUUM EINSTEIN AUDIT (G_ab = 0) ---
                symbolic_metric = test_result.get('metrics', {}).get('symbolic_metric')
                coords = test_result.get('metrics', {}).get('coords')
                if symbolic_metric and coords and "black hole" in str(hypothesis).lower():
                    if self.ui: self.ui.print_log("[AUDITOR] Black Hole detected. Verifying Vacuum Einstein Equations (G_uv = 0)...")
                    from sci_utils import verify_vacuum_einstein
                    is_vacuum, vacuum_failures, vacuum_reasoning = verify_vacuum_einstein(symbolic_metric, coords)
                    if not is_vacuum:
                        audit["audit_passed"] = False
                        audit["rejection_type"] = "FATAL"
                        audit["reasoning"] = f"{audit.get('reasoning', '')}\n\nVACUUM VIOLATION: Metric is not a vacuum solution. G_uv components non-zero: {vacuum_failures}"
                    else:
                        if self.ui: self.ui.print_log("\033[1;32m[AUDITOR] Vacuum Einstein Audit PASSED.\033[0m")
            
            # ── FEATURE: BIANCHI IDENTITY RIGOR CHECK ──
            if PhysicsValidator.should_trigger_adm_check(hypothesis) or "metric" in code.lower():
                if self.ui:
                    self.ui.print_log("[AUDITOR] Manifold detected. Verifying Bianchi Identity (nabla_b G^a_b = 0)...")
                
                try:
                    # We need to extract the metric matrix and coordinates from the code
                    # This is complex, so we'll look for standard naming in the simulation output or code
                    # For now, we'll try to re-simulate the symbolic part if possible, 
                    # but a better way is to have the Lab provide a 'symbolic_metric' in test_result.
                    symbolic_metric = test_result.get('symbolic_metric')
                    coords = test_result.get('coords')
                    
                    if symbolic_metric and coords:
                        from sci_utils import verify_bianchi_identity
                        is_valid_bianchi, failures = verify_bianchi_identity(symbolic_metric, coords)
                        
                        if not is_valid_bianchi:
                            audit["audit_passed"] = False
                            audit["rejection_type"] = "FATAL"
                            fail_msg = f"BIANCHI IDENTITY VIOLATION: Coordinate divergence in components: {failures}"
                            audit["reasoning"] = f"{audit.get('reasoning', '')}\n\n{fail_msg}"
                            
                            # Log to hallucination_log.md
                            log_path = os.path.join(self.config['paths']['memory'], "hallucination_log.md")
                            with open(log_path, 'a', encoding='utf-8') as f:
                                f.write(f"\n### [{time.strftime('%Y-%m-%d %H:%M:%S')}] Bianchi Violation: {hypothesis.get('topic')}\n")
                                f.write(f"**Hypothesis**: {hypothesis.get('hypothesis')}\n")
                                f.write(f"**Failures**: {json.dumps(failures, indent=2)}\n")
                                f.write(f"**Status**: FATAL REJECTION\n---\n")
                            
                            if self.ui:
                                self.ui.print_log(f"\033[1;31m[AUDITOR] FATAL: Bianchi Identity Violated! Logged to hallucination_log.md\033[0m")
                        else:
                            if self.ui:
                                self.ui.print_log("\033[1;32m[AUDITOR] Bianchi Identity verified (nabla_b G^a_b = 0).\033[0m")
                except Exception as e:
                    if self.ui:
                        self.ui.print_log(f"[AUDITOR] Bianchi Check skipped: {e}")

            # ── MERGE DEFERRED PREFLIGHT ISSUES ──
            if preflight_failed and is_adm_simulation:
                audit["audit_passed"] = False
                # If it wasn't already FATAL, make it FIXABLE due to preflight
                if audit.get("rejection_type") != "FATAL":
                    audit["rejection_type"] = "FIXABLE"
                audit["reasoning"] = f"Preflight Issues: {' | '.join(preflight_issues)}\n\n" + audit.get("reasoning", "")

            return audit
        
        # Fallback for failures
        if self.ui:
            self.ui.print_log("[AUDITOR] Failed to extract JSON from response.")
        
        return {
            "audit_passed": False,
            "test_coverage": "Failed",
            "cheat_detected": False,
            "rejection_type": "FATAL",
            "reasoning": "Audit Error: Could not extract valid JSON from LLM response."
        }

    def verify_batch(self, test_results):
        """
        [COLLECTIVE AUDIT]
        Takes a list of simulation results and performs a comparative audit using the 72B model.
        """
        if not test_results:
            return []

        if self.ui:
            self.ui.print_log(f"\033[1;33m[COLLECTIVE AUDIT] Auditing batch of {len(test_results)} results.\033[0m")

        target_model = self.config['hardware'].get('math_model') or self.config['hardware'].get('reasoning_model')
        
        results_summary = ""
        for i, res in enumerate(test_results):
            h = res.get('hypothesis', {})
            results_summary += f"--- RESULT {i+1} ---\n"
            results_summary += f"Topic: {h.get('topic')}\n"
            results_summary += f"Hypothesis: {h.get('hypothesis')}\n"
            
            # Extract final 500 chars of output to see ScientificReport result
            raw_out = str(res.get('raw_output', ''))
            out_preview = raw_out[-500:] if len(raw_out) > 500 else raw_out
            results_summary += f"Output Preview (End of Stream):\n{out_preview}\n"
            
            metrics = res.get('metrics', {})
            results_summary += f"Metrics: {json.dumps(metrics)}\n\n"

        prompt = f"""
As the Chief Auditor, review this batch of {len(test_results)} scientific simulations.
Identify patterns in failures and successes. Be extremely strict about scientific rigor, unit consistency, and algebraic alignment.

DATA:
{results_summary}

Respond in JSON ONLY:
{{
    "audit_reports": [
        {{
            "index": 0,
            "audit_passed": true/false,
            "rejection_type": "FIXABLE|FATAL|NONE",
            "reasoning": "detailed technical explanation"
        }},
        ...
    ],
    "collective_insight": "Common failure modes or shared breakthroughs discovered across the batch."
}}
"""
        response = self._query_llm(prompt, model=target_model, temperature=0.2)
        
        from json_utils import extract_and_validate
        data, error = extract_and_validate(response, "batch_audit")
        
        if data and "audit_reports" in data:
            if self.ui and "collective_insight" in data:
                self.ui.print_log(f"\033[1;33m[COLLECTIVE AUDIT] Global Insight: {data['collective_insight']}\033[0m")
            return data["audit_reports"]
            
        if self.ui:
             self.ui.print_log(f"\033[1;31m[COLLECTIVE AUDIT] Batch audit failed: {error or 'Malformed JSON'}. Falling back to individual auditing.\033[0m")
        return []
