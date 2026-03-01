"""
Standard Physical Constants and Unit Conversions for Science Bot.
All units are in SI (International System of Units).
"""
import numpy as np

CONSTANTS = {
    "c": 299792458,           # Speed of Light (m/s)
    "G": 6.67430e-11,        # Gravitational Constant (m^3 kg^-1 s^-2)
    "h": 6.62607015e-34,     # Planck Constant (J s)
    "hbar": 1.0545718e-34,   # Reduced Planck Constant (J s)
    "k_B": 1.380649e-23,     # Boltzmann Constant (J/K)
    "sigma": 5.670374419e-8, # Stefan-Boltzmann Constant (W m^-2 K^-4)
    "N_A": 6.02214076e23,    # Avogadro constant (mol^-1)
    "R": 8.314462618,        # Gas constant (J K^-1 mol^-1)
}

def convert_to_si(value, unit_from):
    """Simple unit conversion utility."""
    conversions = {
        "eV": 1.602176634e-19, # to Joules
        "km": 1000.0,
        "cm": 0.01,
        "mm": 0.001,
        "degree": np.pi / 180.0,
    }
    return value * conversions.get(unit_from, 1.0)
