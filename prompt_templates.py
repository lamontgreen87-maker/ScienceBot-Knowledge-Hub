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

### RESEARCH MANDATE:
{rigor_mandate}
5. **NO PLACEHOLDER PHYSICS**: Forbid generic equations (e.g., dy/dt = y/t) unless explicitly requested for simple tests.
6. **MATHEMATICAL FIDELITY**: You MUST provide LaTeX-ready derivations in `derivation_steps` that bridge the hypothesis to the `mathematical_blueprint`.

Respond in JSON ONLY (after your <think> block):
{
    "topic": "{topic}",
    "hypothesis": "Non-trivial falsifiable prediction using specific physics vocabulary",
    "derivation_steps": "A rigorous step-by-step mathematical bridge from the theoretical concept to the RHS blueprint (50-100 words).",
    "simulation_context": "Physics/Environment context with literature-grounded terminology",
    "literature_grounding": "Citations supporting the use of specific constants/primitives",
    "physics_primer": "A rigorous technical overview (3-5 sentences) explaining why this mathematical approach is valid for the topic and how it aligns with the requested primitives.",
    "atomic_specification": {
        "independent_variable": {"name": "t", "symbol": "t"},
        "dependent_variable": {"name": "y", "symbol": "y"},
        "symbolic_parameters": ["t", "y", "ALPHA", "BETA"]
    },
    "mathematical_blueprint": "SymPy-ready RHS (e.g. constants['ALPHA'] * y + constants['BETA'] * t)",
    "mathematical_implementation_guide": "High-Fidelity architecture (e.g. 50-step Rolling Memory Window with specific kernels. Resource depletion enabled.)",
    "required_constants": { "ALPHA": "0.7291", "BETA": "1.4582" },
    "target_complexity_score": "75"
}
"""

# --- MANDATE VARIANTS ---
FAST_CYCLE_MANDATE = """
1. **LOGIC HOLE IDENTIFICATION**: Identify a specific "hole" or contradiction in our current understanding of the manifold/tensor.
2. **INCREMENTAL SYNTHESIS**: Focus on building a bridge between existing findings. Do not attempt a total solution.
3. **FOUNDATIONAL-LOGIC**: This is a HIGH-SPEED 70B cycle. Focus on hardening the mathematical foundation in under 2 minutes.
4. **PITHY DERIVATION**: Max 3 sentences. No sprawling theories; just the essential incremental logic to build upon.
"""

DEEP_RESEARCH_MANDATE = """
1. **KNOWLEDGE CONSOLIDATION**: You MUST start with a <think> block synthesizing all atomic 8B findings into a coherent theoretical framework.
2. **INCREMENTAL RIGOR**. Build meticulously on previously validated constants. NO "giant leaps" without proof.
3. **DERIVATION FIELD**: You MUST include a rigorous `derivation_steps` field (50-100 words) explaining how this finding completes a specific logic hole.
4. **EXTREME COMPLEXITY**: MANDATE 'non-linear tensor fields', 'singular boundary conditions (Kerr/Schwarzschild)', 'topological soliton dynamics', or 'fractal event-horizon encoding'. NO SIMPLE ODEs.
5. **MANDATORY SKELETON**: All simulation code resulting from this hypothesis MUST follow the 5-part structure: # 1. SYMBOLIC SETUP, # 2. CONSTANT INJECTION, # 3. THE IMMUTABLE LAW, # 4. HIGH-FIDELITY EXECUTION, # 5. DATA LOGGING.
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
from sci_utils import ScientificReport, verify_power_law, verify_conservation, verify_scale_invariance, symbolic_to_numeric_bridge, add_noise, verify_confidence_level, verify_structural_consistency, grunwald_letnikov_diff, ricci_scalar_symbolic, SymbolGuard

# 1. SYMBOLIC SETUP
{symbolic_setup}

# 2. CONSTANT INJECTION (REQUIRED CONSTANTS FROM ENVIRONMENT)
constants = {{
    {constants_dict_content}
}}

# 3. THE IMMUTABLE LAW (Explicit RHS)
# NO .subs() ALLOWED FOR CALCULATIONS. 
# Use constants['VAR'] as algebraic multipliers directly in the expression.
# expr = constants['ALPHA'] * y + ... 

# 4. HIGH-FIDELITY EXECUTION LOOP
# MUST use sp.lambdify(symbols, expr, 'numpy') to convert symbolic logic to vectorized functions.
# solve_ivp is discouraged; use manual loops for granular entropy/resource dynamics.
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

### COMPLIANT ONE-SHOT EXAMPLE (Copy this structure exactly):
```python
import numpy as np
import sympy as sp
from sci_utils import ScientificReport, verify_power_law, verify_conservation, verify_scale_invariance, symbolic_to_numeric_bridge, add_noise, verify_confidence_level, verify_structural_consistency, grunwald_letnikov_diff, ricci_scalar_symbolic

# 1. SYMBOLIC SETUP
t, y = sp.symbols('t y')
# MANDATORY: Verify symbols exist before use
SymbolGuard.verify_symbols(locals(), required=['t', 'y'])

# 2. CONSTANT INJECTION
# Use THE EXACT values provided in the constants list above.
constants = {
    'ALPHA': 0.729,  # Example: constant from hypothesis
    'BETA': 1.458    # Example: constant from environment
}

# 3. THE IMMUTABLE LAW (Explicit RHS)
# Use algebraic multipliers. .subs() is STRICTLY FORBIDDEN.
expr = constants['ALPHA'] * y + constants['BETA'] * t

# 4. HIGH-FIDELITY EXECUTION LOOP
# Use a loop, not solve_ivp, to capture granular entropy.
f_rhs = sp.lambdify((t, y), expr, 'numpy')
t_vals = np.linspace(0, 10, 500)
y_vals = [1.0]
resource = 100.0
for i in range(1, len(t_vals)):
    resource -= 0.05 * y_vals[-1] # entropy factor
    if resource < 0 or np.random.random() < 0.02: break
    dy = f_rhs(t_vals[i], y_vals[-1])
    y_vals.append(y_vals[-1] + dy * (t_vals[1] - t_vals[0]))
sol_y = np.array(y_vals); sol_t = t_vals[:len(y_vals)]

# 5. DATA LOGGING
report = ScientificReport(simulation_id="demo_id")
report.log_metric("final_state", float(sol_y[-1]))
report.finalize()
```

### LITERAL LAWS (Violation = FATAL REJECTION):
- **MULTIPLIER RULE**: NEVER use `.subs()` for final calculations. You MUST use `constants['VAR']` as an algebraic multiplier directly in the SymPy expression.
    - *FATAL ERROR*: `expr = y.subs(ALPHA, 0.5)`
    - *CORRECT*: `expr = constants['ALPHA'] * y`
- **NUMPY BACKEND MANDATE**: All symbolic expressions MUST be converted via `sp.lambdify(symbols, expr, 'numpy')` before evaluation in a loop. Evaluation via `.evalf()` or `.subs()` in a loop is FORBIDDEN.
    - *CORRECT*: `f_rhs = sp.lambdify((t, y), expr, 'numpy')`
- **NO PHYSICS DEFS**: NO `def` for physics laws or derivatives. Use `sp.lambdify` or `lambda`. 
    - *FATAL ERROR*: `def rhs(t, y): return constants['ALPHA'] * y`
- **EXPLICIT CONSTANTS**: You MUST define a `constants = { ... }` dictionary in section #2 exactly matching the hypothesis requirements.

- **RESOURCE DYNAMICS**: Implement an `initial_resource` and a `consumption_rate` variable to prevent infinite loops and simulate entropy.
- **SYMBOL GUARD MANDATE**: You MUST call `SymbolGuard.verify_symbols(locals(), required=[...])` at the end of section #1. This prevents scope errors during tensor contractions.
- VOCABULARY ALIGNMENT: Use the physics terminology (e.g., 'Schwarzschild Radius', 'Kerr Metric') from the hypothesis in your comments.
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
from sci_utils import ScientificReport, verify_power_law, verify_conservation, verify_scale_invariance, symbolic_to_numeric_bridge, add_noise, verify_confidence_level, verify_structural_consistency, grunwald_letnikov_diff, ricci_scalar_symbolic
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
2.  Maintain the 5-part mandatory template: (1) Symbolic Setup, (2) Constant Injection, (3) Immutable Law, (4) High-Fidelity Execution, (5) DATA LOGGING.
3.  Ensure ALL constants are used algebraically (e.g., `ALPHA * y`).
4.  **CHECKLIST FOR SUCCESS (NON-NEGOTIABLE):**
    - [ ] NO `def` blocks for physics laws or derivatives. Use `sp.lambdify(..., 'numpy')`.
    - [ ] NO `.subs()` or `.evalf()` used for final calculations or inside loops.
    - [ ] Use `sp.symbols` for all independent/dependent variables.
    - [ ] **MANDATORY**: Call `SymbolGuard.verify_symbols(locals())` before any symbolic physics.
    - [ ] The simulation must produce a `ScientificReport` within the DATA LOGGING section.
5.  Return ONLY the complete, corrected Python code.
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
