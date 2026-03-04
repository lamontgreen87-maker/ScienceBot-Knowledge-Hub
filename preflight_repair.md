# Agent Skill: Preflight Repair

## Purpose
This skill defines the autonomous "self-healing" logic used by the research agent to catch and fix recurring syntax and architectural errors in generated SimulationLab code before it reaches the Auditor.

## Core Directives

### 1. Symbolic Substitution Collapse
- **Problem**: Models often use `.subs()` in the simulation loop, which is extremely slow and causes SymPy performance bottlenecks.
- **Fix**: Replace `.subs(SYMBOL, VALUE)` with direct algebraic multiplication or `lambdify`.
- **Instruction**: If you see `expr.subs(param, val)`, refactor it to `expr` where `param` is hardcoded as `val`, or pass it as a numeric argument to a lambdified function.

### 2. Forbidden 'def' Blocks (The "Crutch" Pattern)
- **Problem**: Models use `def rhs(t, y): return ...` instead of SymPy expressions, which breaks symbolic analysis and auditing.
- **Fix**: Convert unauthorized `def` blocks into `sp.lambdify` or raw SymPy expressions.
- **Allowed Exception**: Helper functions prefixed with `verify_`, `calculate_`, or `metric_` are acceptable.

### 3. Header Alignment
- **Problem**: Missing or mislabeled "MANDATORY SECTIONS" (1-5).
- **Fix**: Re-insert or re-number headers to maintain the standard 5-part skeleton.

## Logging Requirements
- All autonomous repairs MUST be logged to `hallucination_log.md`.
- Include the **Physics Topic**, the **Error Pattern**, and the **Patched Logic**.
