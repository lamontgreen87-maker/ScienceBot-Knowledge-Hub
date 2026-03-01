
import numpy as np
from sci_utils import grunwald_letnikov_diff

# 1. SYMBOLIC SETUP
t, MSD, ALPHA, H = sp.symbols('time mean_squared_displacement alpha Hurst_exponent')

# 2. CONSTANT INJECTION (REQUIRED CONSTANTS FROM ENVIRONMENT)
constants = {
    'H': 0.8,
    'ALPHA_MIN': 0.6,
    'ALPHA_MAX': 1.4,
}

# 3. THE IMMUTABLE LAW (Explicit RHS)
expr = (2*H)/(MSD**(1+2*H)) * sp.diff(MSD, t) + ALPHA * MSD**2
immutable_law = expr

# Immutable Law Definition with Constants and Algebraic Multipliers
ALPHA_multiplier = constants['ALPHA_MIN'] + (constants['ALPHA_MAX'] - constants['ALPHA_MIN']) * ALPHA
expr_with_constants = immutable_law.substitute({H: constants['H'], ALPHA: ALPHA_multiplier})

# 4. HIGH-FIDELITY EXECUTION LOOP
t_vals = np.linspace(0, 5, 200); h = t_vals[1] - t_vals[0]
MSD_vals = [1.0]  # initial condition

for alpha_val in np.linspace(constants['ALPHA_MIN'], constants['ALPHA_MAX'], 4):
    y_vals = []
    f_rhs = sp.lambdify((t, MSD), expr_with_constants.substitute(ALPHA=alpha_val), 'numpy')
    
    for i in range(1, len(t_vals)):
        dy = grunwald_letnikov_diff(lambda ti, yi: f_rhs(ti, yi), t_vals[i], MSD_vals[-1], h)
        y_vals.append(MSD_vals[-1] + dy * h)
        
    MSD_vals.extend(y_vals)

sol_MSD = np.array(MSD_vals); sol_t = np.concatenate([t_vals]*4)

# 5. DATA LOGGING
print(f"Optimal range of fractional derivative orders: {np.linspace(constants['ALPHA_MIN'], constants['ALPHA_MAX'], 4)}")
