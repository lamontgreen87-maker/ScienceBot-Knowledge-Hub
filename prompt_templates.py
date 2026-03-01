"""
Centralized library for all Scientific Swarm prompts.
Ensures consistency across components and hardens output compliance.
"""

# === HYPOTHESIS GENERATION ===
HYPOTHESIS_GENERATION_PROMPT = """
You are a Scientific Methodology Engine.

Topic: {topic}
Research Data: {research_context}
{dream_guidance}
{dynamic_rules}
{driving_question}

=== IMPLEMENTABLE PHYSICS MENU ===
{implementable_physics_menu}

### RIGOR MANDATE (Iter 3456, 3511, 3356):
1. NO Trivial constants (1.0, 0.5). Use non-repeating, high-precision physical values (e.g. 0.7291, 1.4582).
2. MUST include a `mathematical_implementation_guide` that details state transitions, memory windows, or resource pools.
3. MUST define specific contextual constants in `required_constants` utilizing clear placeholders like `{constant_value}`.
4. COMPLEXITY MANDATE: Mandate the use of 'resource-limited kernels', 'dynamic thresholds', or 'non-linear state decay' to ensure simulation depth.
5. VOCABULARY MANDATE: Use domain-specific terminology (e.g., 'Anomalous Relaxation', 'Manifold Curvature') in the `hypothesis` and `simulation_context`.

Respond in JSON ONLY:
{{
    "topic": "{topic}",
    "hypothesis": "Non-trivial falsifiable prediction using specific physics vocabulary",
    "simulation_context": "Physics/Environment context with literature-grounded terminology",
    "literature_grounding": "Citations supporting the use of specific constants/primitives",
    "physics_primer": "Reasoning for the framework, explicitly naming the primitives to be used (e.g. 'grunwald_letnikov_diff' or 'add_noise' depending on menu choice)",
    "atomic_specification": {{
        "independent_variable": {{"name": "t", "symbol": "t"}},
        "dependent_variable": {{"name": "y", "symbol": "y"}},
        "symbolic_parameters": ["t", "y", "ALPHA", "BETA"]
    }},
    "mathematical_blueprint": "SymPy-ready RHS (e.g. constants['ALPHA'] * y + constants['BETA'] * t)",
    "mathematical_implementation_guide": "High-Fidelity architecture (e.g. 50-step Rolling Memory Window with specific kernels. Resource depletion enabled.)",
    "required_constants": {{ "ALPHA": "0.7291", "BETA": "1.4582" }},
    "target_complexity_score": "50-80"
}}
"""

# === SIMULATION GENERATION ===
SIMULATION_GENERATION_PROMPT = """
{description}

{dynamic_rules}

Write a Python simulation for the following hypothesis.

Hypothesis: {hypothesis_text}
{symbol_guard_block}
Blueprint: {blueprint}
Constants: {constants_list}
Context: {context}
Architecture: {guide}

{physics_templates}

{primitive_mandate}

### MANDATORY SKELETON:
```python
import numpy as np
import sympy as sp
{import_block}
from sci_utils import ScientificReport, verify_power_law, verify_conservation, verify_scale_invariance, symbolic_to_numeric_bridge, add_noise, verify_confidence_level, verify_structural_consistency, grunwald_letnikov_diff, ricci_curvature_scalar

# 1. SYMBOLIC SETUP
{symbolic_setup}

# 2. CONSTANT INJECTION (REQUIRED CONSTANTS FROM ENVIRONMENT)
constants = {{
    {constants_dict_content}
}}

# 3. THE IMMUTABLE LAW (Explicit RHS)
# expr = constants['ALPHA'] * y + ... # Use algebraic multipliers. .subs() is FORBIDDEN.

# 4. HIGH-FIDELITY EXECUTION LOOP
# MUST implement granular state transitions (step-by-step).
# MUST incorporate environmental factors (e.g., time_steps=200, initial_resource=100.0, resource_consumption_rate, failure_probability=0.05).
# If the guide mentions 'Memory Windows', you MUST use a rolling buffer list.
# If the guide mentions 'Fractal Maps', you MUST implement power-law scaling directly.
# EXAMPLE:
# resource = 100.0
# failure_prob = 0.05
# for step in range(len(t_vals)):
#     resource -= consumption_rate * y_vals[-1]
#     if resource < 0 or np.random.random() < failure_prob: break
#     ... update state ...

# 5. DATA LOGGING (REQUIRED: Use ScientificReport)
# report = ScientificReport(simulation_id="hypothesis_id")
# report.finalize()
```

### LITERAL LAWS (Violation = Immediate Rejection):
- NO `.subs()`: Use variables as algebraic multipliers (e.g., `ALPHA * y`).
- NO `def` for physics: Use `lambdify` or `lambda` for the main RHS.
- NO Trivial Loops: For complexity {target_complexity_score}, you MUST implement multi-step state updates (resource/energy/decay).
- NO Placeholders: All constants MUST be initialized with high-precision values and utilized as algebraic multipliers.
- ARCHITECTURAL FIDELITY: If you promise 'Memory Windows', 'Resource Depletion', or 'Fractal Maps' in your guide, they MUST be present in the code.
- VOCABULARY ALIGNMENT: Use the physics terminology from the hypothesis in your comments and variables.
"""

# === REPAIR PROMPT ===
REPAIR_PROMPT = """
# HIGH-FIDELITY REPAIR PROTOCOL
Your previous simulation code failed the scientific rigor audit. 
You must REPAIR the code by following the specific REPAIR DIRECTIVES provided below.

## SCIENTIFIC CONTEXT
Topic: {topic}
Hypothesis: {hypothesis}
Implementation Guide: {implementation_guide}

## AUDIT FAILURES
{audit_report}

## LITERAL SYNTAX EXAMPLES (MANDATORY PATTERNS)
You MUST follow these exact patterns for your code to be accepted:

### 1. The Multiplier Rule (NO .subs())
Incorrect: `expr.subs(symbol, value)`
Correct: 
```python
# 3. THE IMMUTABLE LAW
# Use constants['VAR'] directly as an algebraic multiplier
expr = constants['ALPHA'] * y + constants['BETA'] * t
```

### 2. Required Import Block
```python
from sci_utils import ScientificReport, verify_power_law, verify_conservation, verify_scale_invariance, symbolic_to_numeric_bridge, add_noise, verify_confidence_level, verify_structural_consistency, grunwald_letnikov_diff, ricci_curvature_scalar
```

### 3. High-Fidelity Execution (Loops, not simple ODEs)
If the audit mentions "Trivial Loops" or "High-Fidelity", you MUST use an explicit loop:
```python
# 4. HIGH-FIDELITY EXECUTION
for i in range(1, len(t_vals)):
    # Calculate update with resource depletion or memory
    resource_use = y_vals[-1] * constants['DECAY']
    # ... update logic ...
```

## MANDATORY REPAIR STEPS
1.  Address EVERY failure in the audit report above.
2.  Maintain the 5-part mandatory template: (1) Symbolic Setup, (2) Constant Injection, (3) Immutable Law, (4) High-Fidelity Execution, (5) ScientificReport.
3.  Ensure ALL constants are used algebraically (e.g., `ALPHA * y`).
4.  Return ONLY the complete, corrected Python code.
"""

# === QUESTION FORMATION ===
QUESTION_FORMATION_PROMPT = """
Identify 3-5 specific, falsifiable questions for the topic: {topic}

Context: {context}
Prior Findings: {prior_findings}

You MUST think carefully about these questions before answering. 
Start your response with a <think>...</think> block to reason through the knowledge gaps.
After thinking, respond in JSON ONLY:
{{
    "questions": [
        {{"question": "...", "rationale": "...", "testable_with": "..."}}
    ],
    "selected_question": "The best one",
    "selection_rationale": "Why"
}}
"""

# ── EXPLORATORY PROTOTYPING ──

PROBE_GENERATION_PROMPT = """
You are a mathematical researcher performing "Exploratory Prototyping".
Your goal is to write a MINIMAL, self-contained Python script to verify a specific concept.

Concept to Test: {concept}
Research Context: {context}

=== CONSTRAINTS ===
- Code MUST be less than 20 lines.
- Use only `numpy`, `sympy`, `scipy`, or `sci_utils` primitives.
- Print exactly one clear result (e.g., "Convergence: True", "Ratio: 1.5").
- Do NOT use `solve_ivp` unless absolutely necessary; prefer simple Euler or SymPy analysis.
- The script must be executable as-is.

Respond in JSON ONLY:
{{
    "probe_id": "short_snake_case_id",
    "objective": "What this probe is testing",
    "code": "print('result...')",
    "expected_insight": "What a successful run implies"
}}
JSON:"""

RESEARCH_AUGMENTATION_PROMPT = """
You are a Lead Scientist synthesizing a deep-dive research brief.
You have the initial research, the results of targeted follow-up searches, and the data from a mathematical probe.

Topic: {topic}
Initial Brief: {initial_brief}

=== NEW WEB FINDINGS ===
{web_findings}

=== LAB PROBE RESULTS ===
{probe_results}

Synthesize an augmented research brief (5-8 sentences).
- Integrate the numerical evidence from the probe.
- Cross-reference the new web findings with the initial brief.
- Identify the FINAL falsifiable gap that the upcoming hypothesis must address.
- Be extremely specific about mathematical constants or behaviors observed.

Augmented Brief:"""

# === ADVERSARIAL DEBATE ===
DEBATE_PROMPT_CRITIC = """
You are a peer-review mathematical CRITIC.
Topic: {topic}

The PROPOSER has submitted the following mathematical hypothesis for simulation:
{proposer_argument}

=== YOUR MANDATE ===
Aggressively try to destroy this hypothesis. Find dimension mismatches, trivial boundary physics, topological flaws, or variables that do not make sense in the context.
This is ROUND {round}.

If the PROPOSER's math is robust and survives your scrutiny, end your response with EXACTLY the phrase: "DEBATE_CONCLUSION_ACCEPT".
If the PROPOSER's math is flawed beyond repair, end your response with EXACTLY the phrase: "DEBATE_CONCLUSION_REJECT".
Otherwise, state your attack.

Start your response with a <think> block to reason through the physics.
Critic Attack:"""

DEBATE_PROMPT_PROPOSER = """
You are a mathematical PROPOSER defending your hypothesis.
Topic: {topic}

The CRITIC has attacked your math with the following:
{critic_attack}

=== YOUR MANDATE ===
Defend your math. Rebut the critic's points with rigorous algebraic logic. Correct any genuine errors in your blueprint, but defend the core mechanics aggressively.
This is ROUND {round}.

Start your response with a <think> block to reason through the attack.
Proposer Defense:"""
