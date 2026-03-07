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

    # Boost 2: Physics
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
    if len(entry) > 2000:
        depth_bonus = min((len(entry) - 2000) / 1000.0, 0.5)
        rigor += depth_bonus
        print(f"[DEBUG] Depth Boost: +{depth_bonus:.2f}")

    return min(rigor, 10.0)

# Test with the exact content from the user's [15:30:33] entry
test_content = """**Technical Research Brief: Metric Perturbations & Higher-Dimensional Black Hole Stability**

The mathematical framework governing the stability analysis of higher-dimensional black holes against metric perturbations primarily involves partial differential equations (PDEs) derived from linearizing the Einstein field equations. This typically employs a gauge-invariant formalism, decomposing perturbations into tensor, vector, and scalar modes based on their tensorial behaviour, leading to master equations. Crucially, the stability analysis relies on demonstrating that the spatial derivative part of these master equations forms a positive, self-adjoint operator in an appropriate function space (e.g., \( L^2 \)), ensuring the absence of normalisable negative-frequency modes that would indicate instability.

A specific logic hole exists in reconciling the stability results for certain higher-dimensional black holes (e.g., higher-dimensional Schwarzschild, Source 1) with the identified instabilities of others, particularly highly rotating Myers-Perry black holes (Source 4). While tensor and vector modes are proven stable for diverse maximally symmetric black holes, the transition to instability for specific rotating configurations suggests a complex dependence on horizon topology and angular momentum that is not yet fully understood or unified within the current self-adjoint operator analysis.
"""

print(f"Testing Content Length: {len(test_content)}")
final_score = calculate_rigor(test_content)
print(f"\nFINAL RIGOR SCORE: {final_score:.2f}")
print(f"RESULT: {'VERIFIED' if final_score >= 4.0 else 'REJECTED'}")
