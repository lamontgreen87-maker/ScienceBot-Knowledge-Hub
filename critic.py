from base_module import BaseModule

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
        if not report["valid"]:
            preflight_issues = report["errors"] + report["repair_directives"]
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
            results_summary += f"Output Preview: {str(res.get('raw_output'))[:300]}\n"
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
