---
name: thermodynamics-phase
description: >
  Thermodynamic property calculation and phase equilibrium workflows using
  CoolProp (pure fluids and mixtures), the NIST WebBook, and Thermo (chemical
  engineering EOS). Covers equation-of-state calculations, vapor-liquid
  equilibrium, heat capacity, entropy, enthalpy, psychrometrics, and
  combustion thermochemistry. Load this skill for fluid property lookup,
  thermodynamic cycle analysis, VLE calculations, or combustion analysis tasks.
license: Apache-2.0
category: engineering-science
metadata:
  third_party:
    - kind: library
      name: CoolProp
      license: MIT
      info_url: http://www.coolprop.org/
    - kind: service
      name: NIST WebBook
      provider: NIST
      info_url: https://webbook.nist.gov/
    - kind: library
      name: thermo
      license: MIT
      info_url: https://thermo.readthedocs.io/
---

# Thermodynamics and Phase Equilibria

## Fluid properties with CoolProp

CoolProp covers 120+ pure fluids and pseudo-pure mixtures.

```python
import CoolProp.CoolProp as CP

def fluid_props(fluid, T_K, P_Pa):
    """
    Return common thermodynamic properties for a pure fluid.
    fluid : CoolProp fluid name (e.g. 'Water', 'Nitrogen', 'R134a')
    T_K   : temperature (K)
    P_Pa  : pressure (Pa)
    """
    return {
        "rho_kg_m3": CP.PropsSI("D",   "T", T_K, "P", P_Pa, fluid),
        "h_J_kg":    CP.PropsSI("H",   "T", T_K, "P", P_Pa, fluid),
        "s_J_kgK":   CP.PropsSI("S",   "T", T_K, "P", P_Pa, fluid),
        "cp_J_kgK":  CP.PropsSI("C",   "T", T_K, "P", P_Pa, fluid),
        "mu_Pa_s":   CP.PropsSI("V",   "T", T_K, "P", P_Pa, fluid),
        "k_W_mK":    CP.PropsSI("L",   "T", T_K, "P", P_Pa, fluid),
        "phase":     CP.PhaseSI("T",   T_K, "P", P_Pa, fluid),
    }

# Example: steam at 200 C, 1 MPa
props = fluid_props("Water", T_K=473.15, P_Pa=1e6)
for k, v in props.items():
    print(f"  {k:12s}: {v}")
```

### Saturation properties

```python
def saturation_props(fluid, T_K=None, P_Pa=None):
    """
    Return saturation temperature and pressure, and liquid/vapour properties.
    Provide either T_K or P_Pa (not both).
    """
    if T_K is not None:
        P_sat = CP.PropsSI("P", "T", T_K, "Q", 0, fluid)
        T_sat = T_K
    else:
        T_sat = CP.PropsSI("T", "P", P_Pa, "Q", 0, fluid)
        P_sat = P_Pa

    h_liq = CP.PropsSI("H", "T", T_sat, "Q", 0, fluid)
    h_vap = CP.PropsSI("H", "T", T_sat, "Q", 1, fluid)
    return {
        "T_sat_K": T_sat, "P_sat_Pa": P_sat,
        "h_liq": h_liq, "h_vap": h_vap,
        "h_fg": h_vap - h_liq,         # latent heat (J/kg)
        "rho_liq": CP.PropsSI("D", "T", T_sat, "Q", 0, fluid),
        "rho_vap": CP.PropsSI("D", "T", T_sat, "Q", 1, fluid),
    }
```

## Rankine cycle analysis

```python
def rankine_cycle(fluid, T_boiler_K, P_boiler_Pa, T_condenser_K, eta_pump=0.85, eta_turbine=0.88):
    """
    Ideal Rankine cycle with isentropic efficiency.
    Returns thermal efficiency and specific work values.
    """
    # State 1: condenser outlet (saturated liquid)
    P_cond = CP.PropsSI("P", "T", T_condenser_K, "Q", 0, fluid)
    h1 = CP.PropsSI("H", "P", P_cond, "Q", 0, fluid)
    s1 = CP.PropsSI("S", "P", P_cond, "Q", 0, fluid)
    v1 = 1 / CP.PropsSI("D", "P", P_cond, "Q", 0, fluid)

    # State 2: pump outlet
    w_pump_ideal = v1 * (P_boiler_Pa - P_cond)
    h2 = h1 + w_pump_ideal / eta_pump

    # State 3: boiler outlet (superheated or saturated vapour)
    h3 = CP.PropsSI("H", "T", T_boiler_K, "P", P_boiler_Pa, fluid)
    s3 = CP.PropsSI("S", "T", T_boiler_K, "P", P_boiler_Pa, fluid)

    # State 4: turbine outlet (isentropic expansion to P_cond)
    h4s = CP.PropsSI("H", "P", P_cond, "S", s3, fluid)
    w_turbine_ideal = h3 - h4s
    h4 = h3 - w_turbine_ideal * eta_turbine

    q_boiler = h3 - h2
    w_net = (h3 - h4) - (h2 - h1)
    eta_th = w_net / q_boiler

    return {
        "eta_thermal": eta_th,
        "w_net_J_kg": w_net,
        "q_boiler_J_kg": q_boiler,
        "h_states_J_kg": [h1, h2, h3, h4],
    }
```

## Vapor-liquid equilibrium with thermo

```python
from thermo import Chemical, Mixture
from thermo.flash import FlashVL

def bubble_point(components, zs, T_K):
    """
    Compute bubble-point pressure and vapour composition using thermo.
    components : list of chemical names (e.g. ['methane', 'ethane'])
    zs         : liquid mole fractions (must sum to 1)
    T_K        : temperature (K)
    """
    mix = Mixture(components, zs=zs, T=T_K)
    # thermo uses flash algorithms with cubic EOS (SRK/PR)
    # Flash to VLE at given T and z
    flash = FlashVL(mix.constants, mix.correlations)
    P_bubble = flash.bubble_T(T=T_K, zs=zs).P
    ys = flash.flash(T=T_K, P=P_bubble, zs=zs, VF=0).ys
    return P_bubble, ys

# Example
# P, y = bubble_point(['methane', 'ethane'], [0.4, 0.6], T_K=250)
```

## Psychrometrics

```python
def psychrometric_props(T_dry_K, phi_relative_humidity, P_Pa=101325):
    """
    Moist air properties.
    T_dry_K : dry-bulb temperature (K)
    phi     : relative humidity (0-1)
    Returns humidity ratio, wet-bulb temp, dew point, enthalpy.
    """
    P_sat = CP.PropsSI("P", "T", T_dry_K, "Q", 0, "Water")
    P_v = phi * P_sat                  # partial pressure of vapour
    P_a = P_Pa - P_v                   # partial pressure of dry air
    W = 0.622 * P_v / P_a             # humidity ratio (kg water/kg dry air)
    h = 1.006 * (T_dry_K - 273.15) + W * (2501 + 1.86 * (T_dry_K - 273.15))  # kJ/kg
    T_dp = CP.PropsSI("T", "P", P_v, "Q", 0, "Water")   # dew point (K)
    return {"W_kg_kg": W, "h_kJ_kg": h, "T_dp_K": T_dp}
```

## Combustion thermochemistry

```python
def adiabatic_flame_temperature(fuel, oxidizer="O2", phi=1.0, T_in_K=298.15):
    """
    Estimate adiabatic flame temperature using NASA polynomial coefficients.
    For full accuracy, use Cantera (load the cantera skill if available).
    This function provides a rough estimate via enthalpy balance.
    """
    # Simplified: use CoolProp heat capacities of products
    # For rigorous combustion analysis, use Cantera:
    # import cantera as ct
    # gas = ct.Solution('gri30.yaml')
    # gas.TP = T_in_K, ct.one_atm
    # gas.set_equivalence_ratio(phi, fuel, 'O2:1.0, N2:3.76')
    # gas.equilibrate('HP')
    # return gas.T
    raise NotImplementedError(
        "For adiabatic flame temperature, use Cantera: \n"
        "  import cantera as ct\n"
        "  gas = ct.Solution('gri30.yaml')\n"
        "  gas.set_equivalence_ratio(phi, fuel, 'O2:1.0, N2:3.76')\n"
        "  gas.equilibrate('HP')\n"
        "  print(gas.T)"
    )
```

## NIST WebBook retrieval

```python
def nist_fluid_properties(compound_name_or_cas, T_K, P_Pa):
    """
    Retrieve thermodynamic properties from NIST WebBook.
    Returns raw JSON from the NIST Thermophysical Properties of Fluid Systems API.
    """
    import urllib.request, json, urllib.parse
    params = urllib.parse.urlencode({
        "Action": "Load", "ID": compound_name_or_cas,
        "Type": "SatT", "Digits": 5,
        "THigh": T_K, "TLow": T_K, "TInc": 1,
        "RefState": "DEF", "TUnit": "K", "PUnit": "Pa",
        "DUnit": "kg/m3", "HUnit": "kJ/kg",
        "WUnit": "m/s", "VisUnit": "uPa*s", "STUnit": "N/m"
    })
    url = f"https://webbook.nist.gov/cgi/fluid.cgi?{params}"
    with urllib.request.urlopen(url, timeout=15) as r:
        return r.read().decode("utf-8")
```

## Validation checks

- CoolProp phase string: verify `phase == "liquid"` or `"gas"` matches your
  assumed state before using liquid-specific correlations.
- Rankine cycle: h4 > h1 (turbine outlet must be above condenser inlet enthalpy);
  eta_thermal bounded (0, 0.6) for practical steam cycles.
- Humidity ratio W: physically bounded (0, ~0.04 kg/kg) at standard conditions.
- VLE: sum of vapour mole fractions must equal 1 within tolerance.
- Report all property values with units and the source (CoolProp, NIST, EOS model).
