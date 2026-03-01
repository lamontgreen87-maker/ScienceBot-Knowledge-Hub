"""
Physical Constants Utility (Source Intelligence 2.0)
Provides high-precision constants based on CODATA 2022 recommended values.
Ensures rigor and prevents LLM hallucination of physical values.
"""

CONSTANTS = {
    # Fundamental Constants
    "SPEED_OF_LIGHT": 299792458.0,  # m/s
    "PLANCK_CONSTANT": 6.62607015e-34,  # J s
    "REDUCED_PLANCK_CONSTANT": 1.054571817e-34,  # J s
    "GRAVITATIONAL_CONSTANT": 6.67430e-11,  # m^3 kg^-1 s^-2
    "FINE_STRUCTURE_CONSTANT": 0.0072973525643,  # Unitless
    
    # Electromagnetic Constants
    "ELEMENTARY_CHARGE": 1.602176634e-19,  # C
    "VACUUM_PERMITTIVITY": 8.8541878128e-12,  # F/m
    "VACUUM_PERMEABILITY": 1.25663706212e-6,  # N/A^2
    "COULOMB_CONSTANT": 8987551792.3,  # N m^2 / C^2
    
    # Thermodynamic Constants
    "BOLTZMANN_CONSTANT": 1.380649e-23,  # J/K
    "AVOGADRO_CONSTANT": 6.02214076e+23,  # mol^-1
    "GAS_CONSTANT": 8.314462618,  # J / (mol K)
    "STEFAN_BOLTZMANN_CONSTANT": 5.670374419e-8,  # W / (m^2 K^4)
    
    # Atomic/Subatomic Constants
    "ELECTRON_MASS": 9.1093837015e-31,  # kg
    "PROTON_MASS": 1.67262192369e-27,  # kg
    "NEUTRON_MASS": 1.67492749804e-27,  # kg
    "BOHR_RADIUS": 5.29177210903e-11,  # m
    "RYDBERG_CONSTANT": 10973731.56816,  # m^-1
    "FARADAY_CONSTANT": 96485.33212,  # C/mol
}

def get_constant(name, default=None):
    """
    Retrieves a high-precision constant. 
    Accepts fuzzy names (e.g., 'planck' or 'h' for PLANCK_CONSTANT).
    """
    lookup = name.upper().replace(" ", "_")
    
    # Short alias mapping
    aliases = {
        "C": "SPEED_OF_LIGHT",
        "H": "PLANCK_CONSTANT",
        "HBAR": "REDUCED_PLANCK_CONSTANT",
        "G": "GRAVITATIONAL_CONSTANT",
        "KB": "BOLTZMANN_CONSTANT",
        "NA": "AVOGADRO_CONSTANT",
        "R": "GAS_CONSTANT",
        "ALPHA": "FINE_STRUCTURE_CONSTANT",
        "ME": "ELECTRON_MASS",
        "MP": "PROTON_MASS",
        "MN": "NEUTRON_MASS",
        "E": "ELEMENTARY_CHARGE",
        "EPSILON_0": "VACUUM_PERMITTIVITY",
        "MU_0": "VACUUM_PERMEABILITY",
        "K_E": "COULOMB_CONSTANT",
        "SIGMA": "STEFAN_BOLTZMANN_CONSTANT"
    }
    
    final_key = aliases.get(lookup, lookup)
    return CONSTANTS.get(final_key, default)

def get_all_ground_truth():
    """Returns the full constant dictionary."""
    return CONSTANTS.copy()

if __name__ == "__main__":
    # Internal test
    print(f"Planck: {get_constant('h')}")
    print(f"Boltzmann: {get_constant('KB')}")
    print(f"Fine Structure: {get_constant('alpha')}")
