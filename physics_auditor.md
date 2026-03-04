# Agent Skill: Physics Auditor (Relativity)

This skill enables the agent to rigorously verify simulations involving General Relativity (GR) and the Einstein Field Equations (EFE).

## Core Objective
Ensure numerical solutions for the metric tensor $g_{\mu\nu}$ satisfy the fundamental constraints of GR, specifically the **Hamiltonian Constraint**.

## Context: The Hamiltonian Constraint
In the 3+1 (ADM) formalism of numerical relativity, the Hamiltonian Constraint is given by:
$$ \mathcal{H} \equiv R + K^2 - K_{ij}K^{ij} - 16\pi\rho = 0 $$
where:
- $R$ is the Ricci scalar of the 3-metric.
- $K_{ij}$ is the extrinsic curvature.
- $K$ is the trace of $K_{ij}$.
- $\rho$ is the energy density.

## Verification Rules
1. **Threshold**: The absolute value of the Hamiltonian constraint violation $|\mathcal{H}|$ must not exceed $10^{-4}$ at any point in the simulation or in the final state metrics.
2. **Detection**:
    - The simulation code must log the Hamiltonian constraint via the `ScientificReport` utility.
    - The `RelativityValidator` sub-module automatically scans `Scientific Metrics` for `hamiltonian_constraint`.
3. **Fatal Rejection**: If $|\mathcal{H}| > 10^{-4}$:
    - Flag as **FATAL**.
    - Trigger a **DeepSeek-R1 reasoning round** to analyze if the failure is due to gauge choice, numerical instability, or fundamental mathematical error in the hypothesis.

## Implementation Guide
When generating GR simulations:
- Always include Christoffel symbol calculations.
- Compute the extrinsic curvature $K_{ij}$ if evolution is involved.
- Add `report.add_metric("hamiltonian_constraint", H_value)` to the `ScientificReport`.
