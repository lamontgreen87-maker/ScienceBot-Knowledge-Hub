import re
import os
import time

def calculate_rigor(entry):
    # Extract base score from summary line if possible
    match = re.search(r"OVERALL RIGOR SCORE: ([\d.]+)/10", entry)
    rigor = float(match.group(1)) if match else 1.0 # Default to 1.0 if not found
    
    # Boost 1: LaTeX
    latex_markers = ['\\frac', '\\[', '\\(', '\\)', '\\partial', '\\mathbb', '$$',
                     '\\mu', '\\nu', '\\alpha', '\\sigma', '\\Lambda',
                     '\\hbar', '\\nabla', '\\int', '\\sum', '\\Gamma',
                     '\\mathcal', '\\begin{', '\\text{', '\\sqrt',
                     'μ', 'ν', '∂', '∇', 'Σ', '∫', '±', '≡', '≈']
    if any(m in entry for m in latex_markers):
        rigor += 2.0

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
        'ergosphere', 'derivation', 'formalism', 'gcm', 'adm mass',
        'schwarzschild-ads', 'hawking mass'
    ]
    entry_lower = entry.lower()
    physics_count = sum(1 for t in physics_terms if t in entry_lower)
    if physics_count >= 3:
        rigor += min(physics_count / 3.0, 2.5)

    # Boost 3: Structure
    if re.search(r'\*\*[1-4]\.\s+\w', entry):
        rigor += 0.5

    # Boost 4: Logic Hole
    if "logic hole" in entry_lower or "missing link" in entry_lower:
        rigor += 1.0

    # Boost 5: Depth
    if len(entry) > 2000:
        depth_bonus = min((len(entry) - 2000) / 1000.0, 0.5)
        rigor += depth_bonus

    return min(rigor, 10.0)

def force_audit():
    path = "memory/swarm_buffer.md"
    if not os.path.exists(path):
        print("Buffer not found.")
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    entries = content.split("---")
    new_entries = []
    
    header = entries[0] # The bit before the first ---
    new_entries.append(header)
    
    verified_count = 0
    rejected_count = 0

    for entry in entries[1:]:
        if not entry.strip(): continue
        
        if "AUDIT: PENDING" in entry:
            # Re-audit
            lines = entry.strip().split('\n')
            header_line = lines[0]
            body = '\n'.join(lines[1:])
            
            # Extract topic
            topic_match = re.search(r"\] (.*?) \| STATUS:", header_line)
            topic = topic_match.group(1) if topic_match else "Unknown"
            
            rigor = calculate_rigor(entry)
            status = "VERIFIED" if rigor >= 4.0 else "REJECTED"
            reason = "" if status == "VERIFIED" else " | REASON: Insufficient mathematical rigor"
            
            # Reconstruct header
            # Keep original timestamp
            ts_match = re.search(r"### \[(\d{2}:\d{2}:\d{2})\]", header_line)
            ts = ts_match.group(1) if ts_match else "00:00:00"
            
            new_header = f"### [{ts}] {topic} | STATUS: Success | AUDIT: {status} | RIGOR: {rigor:.2f}{reason}"
            new_entry = f"\n{new_header}\n{body}\n"
            new_entries.append(new_entry)
            
            if status == "VERIFIED": verified_count += 1
            else: rejected_count += 1
        else:
            new_entries.append(entry)

    with open(path, "w", encoding="utf-8") as f:
        f.write("---".join(new_entries))
    
    print(f"Audit Complete: {verified_count} VERIFIED, {rejected_count} REJECTED.")

if __name__ == "__main__":
    force_audit()
