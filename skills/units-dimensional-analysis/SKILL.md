---
name: units-dimensional-analysis
description: >
  Unit checking, dimensional analysis, and dimensionless number workflows
  using the Pint library. Ensures all engineering calculations carry units,
  catches dimensional inconsistencies, and surfaces relevant dimensionless
  groups (Reynolds, Nusselt, Froude, Strouhal, etc.). Load this skill
  whenever starting a calculation that combines quantities from different
  unit systems or when verifying dimensional homogeneity of derived equations.
license: Apache-2.0
category: engineering-science
metadata:
  third_party:
    - kind: library
      name: Pint
      license: BSD-3-Clause
      info_url: https://pint.readthedocs.io/
---

# Units and Dimensional Analysis

## Pint setup and basic usage

Every engineering calculation should carry units to catch errors early.
Pint provides a `Quantity` type that propagates units through arithmetic.

```python
from pint import UnitRegistry

ureg = UnitRegistry()
Q_ = ureg.Quantity

# Define quantities with units
F = Q_(1000, "N")
A = Q_(0.05, "m**2")
sigma = (F / A).to("MPa")
print(sigma)   # 0.02 MPa

# Automatic conversion
v = Q_(60, "mph").to("m/s")
print(v.magnitude, v.units)   # 26.822... meter / second

# Dimensionality check
try:
    wrong = F + A   # N + m^2 -> DimensionalityError
except Exception as e:
    print("Caught:", e)
```

## Unit conversion table for common engineering quantities

```python
CONVERSIONS = {
    "pressure":      {"Pa": 1, "kPa": 1e-3, "MPa": 1e-6, "psi": 1/6894.76,
                      "bar": 1e-5, "atm": 1/101325},
    "length":        {"m": 1, "mm": 1e3, "cm": 1e2, "km": 1e-3,
                      "in": 39.3701, "ft": 3.28084},
    "force":         {"N": 1, "kN": 1e-3, "MN": 1e-6, "lbf": 0.224809},
    "energy":        {"J": 1, "kJ": 1e-3, "MJ": 1e-6, "kWh": 1/3.6e6,
                      "BTU": 1/1055.06, "cal": 1/4.184},
    "power":         {"W": 1, "kW": 1e-3, "MW": 1e-6, "hp": 1/745.7},
    "temperature":   {"K": "base", "C": "K - 273.15", "F": "K * 9/5 - 459.67"},
    "mass_flow":     {"kg/s": 1, "kg/h": 3600, "t/h": 3.6, "lb/s": 1/0.453592},
    "dynamic_visc":  {"Pa*s": 1, "mPa*s": 1e3, "cP": 1e3},
}

def convert(value, from_unit, to_unit):
    """Convert using Pint."""
    return Q_(value, from_unit).to(to_unit)

# Example
p = convert(150, "psi", "MPa")
print(f"150 psi = {p:.4f}")
```

## Dimensionless number library

```python
def reynolds(rho_kg_m3, U_m_s, L_m, mu_Pa_s):
    """Re = rho*U*L/mu  (inertia/viscous)"""
    return (rho_kg_m3 * U_m_s * L_m) / mu_Pa_s

def nusselt(h_W_m2K, L_m, k_W_mK):
    """Nu = h*L/k  (convective/conductive heat transfer)"""
    return (h_W_m2K * L_m) / k_W_mK

def prandtl(cp_J_kgK, mu_Pa_s, k_W_mK):
    """Pr = cp*mu/k  (momentum/thermal diffusivity)"""
    return (cp_J_kgK * mu_Pa_s) / k_W_mK

def grashof(g_m_s2, beta_1_K, dT_K, L_m, nu_m2_s):
    """Gr = g*beta*dT*L^3/nu^2  (buoyancy/viscous in natural convection)"""
    return (g_m_s2 * beta_1_K * dT_K * L_m**3) / nu_m2_s**2

def rayleigh(Gr, Pr):
    """Ra = Gr*Pr  (natural convection)"""
    return Gr * Pr

def mach(U_m_s, a_m_s):
    """Ma = U/a  (flow velocity/speed of sound)"""
    return U_m_s / a_m_s

def froude(U_m_s, g_m_s2, L_m):
    """Fr = U/sqrt(g*L)  (inertia/gravity, open-channel flow)"""
    import numpy as np
    return U_m_s / np.sqrt(g_m_s2 * L_m)

def strouhal(f_Hz, L_m, U_m_s):
    """St = f*L/U  (vortex shedding frequency)"""
    return (f_Hz * L_m) / U_m_s

def weber(rho_kg_m3, U_m_s, L_m, sigma_N_m):
    """We = rho*U^2*L/sigma  (inertia/surface tension)"""
    return (rho_kg_m3 * U_m_s**2 * L_m) / sigma_N_m

def euler(dP_Pa, rho_kg_m3, U_m_s):
    """Eu = dP/(rho*U^2/2)  (pressure forces/inertia)"""
    return dP_Pa / (0.5 * rho_kg_m3 * U_m_s**2)

def biot(h_W_m2K, L_m, k_W_mK):
    """Bi = h*L/k  (surface convection/internal conduction)"""
    return (h_W_m2K * L_m) / k_W_mK

def fourier(alpha_m2_s, t_s, L_m):
    """Fo = alpha*t/L^2  (transient heat conduction)"""
    return (alpha_m2_s * t_s) / L_m**2

DIMENSIONLESS_NUMBERS = {
    "Reynolds (Re)": "rho*U*L/mu  — inertia/viscous",
    "Nusselt (Nu)":  "h*L/k  — convective/conductive",
    "Prandtl (Pr)":  "cp*mu/k  — momentum/thermal diffusivity",
    "Grashof (Gr)":  "g*beta*dT*L^3/nu^2  — natural convection buoyancy",
    "Rayleigh (Ra)": "Gr*Pr  — natural convection",
    "Mach (Ma)":     "U/a  — compressibility",
    "Froude (Fr)":   "U/sqrt(g*L)  — gravity/inertia",
    "Strouhal (St)": "f*L/U  — vortex shedding",
    "Weber (We)":    "rho*U^2*L/sigma  — surface tension",
    "Biot (Bi)":     "h*L/k  — surface/internal thermal resistance",
    "Fourier (Fo)":  "alpha*t/L^2  — dimensionless time for heat conduction",
    "Euler (Eu)":    "dP/(rho*U^2/2)  — pressure coefficient",
}
```

## Buckingham Pi theorem helper

```python
def buckingham_pi(variables):
    """
    Find dimensionless groups via the Buckingham Pi theorem.
    variables : dict {name: {M: exponent, L: exponent, T: exponent, ...}}
    Returns the number of Pi groups: Pi = n - r
    where n = number of variables, r = rank of dimensional matrix.
    """
    import numpy as np
    names = list(variables.keys())
    dims  = sorted({d for v in variables.values() for d in v})
    matrix = np.zeros((len(dims), len(names)))
    for j, name in enumerate(names):
        for i, dim in enumerate(dims):
            matrix[i, j] = variables[name].get(dim, 0)
    rank = np.linalg.matrix_rank(matrix)
    n_pi = len(names) - rank
    return {
        "n_variables": len(names), "rank": rank, "n_pi_groups": n_pi,
        "dimensional_matrix": matrix, "dimensions": dims, "variables": names
    }

# Example: pipe flow -- Delta_P, rho, mu, U, D, L
pipe_vars = {
    "dP":  {"M": 1, "L": -1, "T": -2},
    "rho": {"M": 1, "L": -3},
    "mu":  {"M": 1, "L": -1, "T": -1},
    "U":   {"L":  1, "T": -1},
    "D":   {"L":  1},
    "L":   {"L":  1},
}
result = buckingham_pi(pipe_vars)
print(f"6 variables, rank {result['rank']} -> {result['n_pi_groups']} Pi groups")
# -> 3 Pi groups: Re, L/D, Eu (or friction factor)
```

## Unit consistency check for equations

```python
def check_equation_dimensions(lhs_units, rhs_units):
    """
    Verify that the left- and right-hand sides of an equation are dimensionally
    consistent.
    lhs_units, rhs_units : Pint unit strings or Quantity objects
    """
    if isinstance(lhs_units, str):
        lhs_units = ureg.parse_expression(lhs_units)
    if isinstance(rhs_units, str):
        rhs_units = ureg.parse_expression(rhs_units)
    lhs_dim = ureg.get_dimensionality(lhs_units)
    rhs_dim = ureg.get_dimensionality(rhs_units)
    if lhs_dim == rhs_dim:
        print("CONSISTENT:", lhs_dim)
    else:
        print(f"INCONSISTENT: LHS={lhs_dim}, RHS={rhs_dim}")

# Example: check that rho*U^2 has units of pressure
check_equation_dimensions("kg/m/s^2", "(kg/m^3) * (m/s)^2")
```

## Best practices for unit-safe calculations

1. Define all input values as `Quantity` objects at the top of the calculation.
2. Let Pint propagate units through every operation.
3. Call `.to("desired_unit")` explicitly at the point where you interpret a result.
4. Never strip units with `.magnitude` except for final output formatting.
5. Use `dimensionless` when a ratio cancels units — `result.to("dimensionless")`.
6. Report all results with units. "sigma = 120" is incomplete;
   "sigma = 120 MPa" is a result.
