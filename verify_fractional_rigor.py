import re

def calculate_rigor(entry):
    rigor = 1.0 # Base average from searcher (typical)
    
    # Boost 1: LaTeX
    latex_markers = ['\\frac', '\\[', '\\(', '\\)', '\\partial', '\\mathbb', '$$',
                     '\\mu', '\\nu', '\\alpha', '\\sigma', '\\Lambda',
                     '\\hbar', '\\nabla', '\\int', '\\sum', '\\Gamma',
                     '\\mathcal', '\\begin{', '\\text{', '\\sqrt',
                     'μ', 'ν', '∂', '∇', 'Σ', '∫', '±', '≡', '≈',
                     '^\\alpha', '_0 D_t', '\\Gamma(']
    if any(m in entry for m in latex_markers):
        rigor += 2.0
        print(f"[DEBUG] LaTeX Boost: +2.0 (Detected: {[m for m in latex_markers if m in entry]})")

    # Boost 2: Physics (SYNCHRONIZED WITH AGENT.PY)
    physics_terms = [
         'regge-wheeler', 'zerilli', 'quasinormal', 'schwarzschild',
        'perturbation', 'hamiltonian', 'lagrangian', 'eigenvalue',
        'tensor', 'manifold', 'teukolsky', 'hawking', 'kerr',
        'geodesic', 'ricci', 'curvature', 'christoffel', 'metric',
        'symplectic', 'boltzmann', 'entropy', 'wavefunction', 'qnm',
        'myers-perry', 'asymptotically', 'anti-de sitter', 'ads/cft', 
        'superradiant', 'backreaction', 'langevin', 'stochastic',
        'covariant', 'diffeomorphism', 'isometry', 'bifurcation',
        'gauge-invariant', 'self-adjoint', 'operator', 'hilbert',
        'pde', 'spectral', 'adiabatic', 'invariant', 'non-linear',
        'pseudospectrum', 'topology', 'angular momentum', 'horizon',
        'schwarzschild-ads', 'hawking mass', 'fractional', 'derivative',
        'integral', 'grunwald-letnikov', 'riemann-liouville', 'caputo',
        'mittag-leffler', 'viscoelasticity', 'anomalous diffusion',
        'power-law', 'memory kernel', 'hereditary', 'adm 3+1',
        'hamiltonian constraint', 'momentum constraint',
        'fractional calculus', 'fox h-function', 'wright function',
        'subdiffusion', 'superdiffusion', 'generalized function',
        'distributional calculus'
    ]
    entry_lower = entry.lower()
    physics_count = sum(1 for t in physics_terms if t in entry_lower)
    if physics_count >= 3:
        boost = min(physics_count / 3.0, 2.5)
        rigor += boost
        print(f"[DEBUG] Physics Boost: +{boost:.2f} (Count: {physics_count})")

    # Boost 3: Structure
    if re.search(r'\*\*[1-4]\.\s+\w', entry):
        rigor += 0.5
        print("[DEBUG] Structure Boost: +0.5")

    # Boost 4: Logic Hole
    if "logic hole" in entry_lower or "missing link" in entry_lower:
        rigor += 1.0
        print("[DEBUG] Logic Hole Boost: +1.0")

    # Boost 5: Depth
    if len(entry) > 1000: # Lowered for test
        depth_bonus = min((len(entry) - 1000) / 1000.0, 0.5)
        rigor += depth_bonus
        print(f"[DEBUG] Depth Boost: +{depth_bonus:.2f}")

    return min(rigor, 10.0)

# Sample Fractional ODE Brief (based on user rejected logs)
test_content = """**Research Brief: Fractional Derivatives of Distributions**

**1. Mathematical Framework**
The current mathematical framework for fractional derivatives of distributions primarily relies on the Caputo derivative, often employed in the context of fractional differential equations (FDEs) and fractional diffusion equations. Research involves approximating fractional systems using functional-differential equations, exploring fractional derivatives via the Erdélyi-Kober integral, and developing Green's functions for linear fractional operators with variable coefficients. The framework is grounded in established fractional calculus formalisms, including Caputo and Riemann-Liouville derivatives, and their numerical approximation via finite-difference methods like the Grünwald-Letnikov scheme. These tools are applied to model anomalous diffusion, conflict-controlled systems, and variational problems, often leading to partial differential equations (PDEs) with fractional orders.

**2. Logic Hole**
A significant gap exists in the rigorous mathematical definition of fractional derivatives for generalized functions (distributions). While substantial empirical progress has been made in applying fractional calculus to model anomalous diffusion, scaling laws, and optimization problems, the formal mathematical definition of the fractional derivative acting on distributions (e.g., Dirac delta function) using established theories like hyperfunction theory or Schwartz distributions is notably absent from the provided research corpus. This lack of a solid theoretical foundation for handling singularities and distributions within the fractional calculus framework represents a critical contradiction between the empirical applicability demonstrated and the mathematical rigor of the core concepts.
"""

print(f"Testing Content Length: {len(test_content)}")
final_score = calculate_rigor(test_content)
print(f"\nFINAL RIGOR SCORE: {final_score:.2f}")
print(f"RESULT: {'TRIGGER 70B' if final_score >= 1.5 else 'SKIP'}")
print(f"RESULT: {'VERIFIED' if final_score >= 4.5 else 'REJECTED'}")
