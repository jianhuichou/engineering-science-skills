---
name: mechanical-design
description: >
  Mechanical design workflows: tolerance stack-up analysis, fatigue and
  fracture mechanics, gear and shaft design, design-for-manufacturing (DFM)
  rules, and design optimization. Uses scipy, numpy, and sympy. Load this
  skill for component sizing, tolerance analysis, fatigue life prediction,
  or DFM review tasks.
license: Apache-2.0
category: mechanical-engineering
---

# Mechanical Design

## Tolerance stack-up analysis

```python
import numpy as np

def worst_case_stackup(tolerances):
    """
    Worst-case tolerance stack-up.
    tolerances: list of (nominal, +tol, -tol) tuples
    Returns (nominal_sum, max_total, min_total).
    """
    nominal = sum(n for n, p, m in tolerances)
    worst_plus  = sum(abs(p) for n, p, m in tolerances)
    worst_minus = sum(abs(m) for n, p, m in tolerances)
    return nominal, nominal + worst_plus, nominal - worst_minus

def rss_stackup(tolerances):
    """
    Statistical (RSS) tolerance stack-up.
    Assumes bilateral tolerances: (nominal, tol) each.
    Returns (nominal_sum, plus_3sigma, minus_3sigma).
    """
    nominal = sum(n for n, t in tolerances)
    rss_tol = np.sqrt(sum(t**2 for n, t in tolerances))
    return nominal, nominal + 3*rss_tol, nominal - 3*rss_tol

# Example: assembly gap
parts = [(25.0, 0.05), (10.0, 0.03), (8.0, 0.02)]   # (nominal mm, bilateral tol)
nom, hi, lo = rss_stackup(parts)
print(f"Nominal gap: {nom:.2f} mm  [{lo:.3f}, {hi:.3f}] mm (3-sigma)")
```

## Fatigue: S-N curve and Miner's rule

```python
def sn_cycles_to_failure(S_a, Su, Se, b=-0.085):
    """
    Cycles to failure from a two-point S-N line (log-log).
    S_a : alternating stress (MPa)
    Su  : ultimate tensile strength (MPa)
    Se  : endurance limit (MPa)
    b   : slope of S-N line (Basquin exponent, typically -0.085 for steel)
    """
    # S-N line: S = C * N^b  =>  N = (S/C)^(1/b)
    # Anchored at (10^3, 0.9*Su) and (10^6, Se) per Shigley convention
    N1, S1 = 1e3, 0.9 * Su
    N2, S2 = 1e6, Se
    b_calc = np.log10(S1/S2) / np.log10(N2/N1) * (-1)
    C = S1 / N1**(b_calc)
    if S_a <= Se:
        return np.inf   # infinite life
    return (S_a / C)**(1/(-b_calc))

def miners_rule(stress_cycles):
    """
    Palmgren-Miner cumulative damage.
    stress_cycles: list of (S_a, n_applied, Nf) tuples
    Returns damage fraction D (failure when D >= 1).
    """
    return sum(n / Nf for S_a, n, Nf in stress_cycles if Nf != np.inf)

# Example
import numpy as np
Su, Se = 600, 200   # MPa, AISI 1045 steel (approximate)
# Stress spectrum
spectrum = [(250, 1e5), (300, 5e4), (350, 1e4)]
cycles_data = [(S, n, sn_cycles_to_failure(S, Su, Se)) for S, n in spectrum]
D = miners_rule(cycles_data)
print(f"Miner's damage D = {D:.3f}  ({'FAIL' if D >= 1 else 'safe'})")
```

## Modified Goodman diagram

```python
def goodman_check(S_a, S_m, Se, Su, Sf=None):
    """
    Modified Goodman fatigue safety factor.
    S_a : alternating stress amplitude (MPa)
    S_m : mean stress (MPa)
    Se  : corrected endurance limit (MPa)
    Su  : ultimate strength (MPa)
    Sf  : fracture strength for Morrow; if None, uses Su
    Returns safety factor nf (> 1 = safe).
    """
    Sf = Sf or Su
    nf = 1 / (S_a/Se + S_m/Sf)
    return nf
```

## Shaft design

```python
def shaft_diameter_de_goodman(Mm, Ma, Tm, Ta, Se, Sy, Su, Kf=1.0, Kfs=1.0):
    """
    Minimum shaft diameter via ASME DE-Goodman criterion (Shigley's Eq. 6-41).
    Mm, Ma : mean and alternating bending moment (N-mm)
    Tm, Ta : mean and alternating torque (N-mm)
    Se     : endurance limit (MPa)
    Sy, Su : yield and ultimate strength (MPa)
    Kf, Kfs: stress concentration factors for bending and shear
    Returns minimum diameter d (mm).
    """
    A = np.sqrt(4*(Kf*Ma)**2 + 3*(Kfs*Ta)**2)
    B = np.sqrt(4*(Kf*Mm)**2 + 3*(Kfs*Tm)**2)
    d = (16/np.pi * (A/Se + B/Su))**(1/3)
    return d
```

## Gear design (AGMA simplified)

```python
def gear_tangential_force(P_W, pitch_dia_m, rpm):
    """
    Tangential load on a gear tooth.
    P_W : transmitted power (W)
    pitch_dia_m : pitch circle diameter (m)
    rpm : rotational speed (rpm)
    Returns Wt (N).
    """
    omega = rpm * 2 * np.pi / 60   # rad/s
    T = P_W / omega                # torque (N-m)
    Wt = 2 * T / pitch_dia_m
    return Wt
```

## Design-for-manufacturing (DFM) checklist

Before finalising a design, verify the following:

1. **Tolerances**: Are tolerances achievable with the specified process?
   Rule of thumb: standard machining ±0.05 mm, precision ±0.01 mm, grinding ±0.003 mm.
2. **Wall thickness** (injection moulding / casting): Maintain uniform wall
   thickness (typically 2–4 mm for plastics; 4–8 mm for castings) to avoid
   sink marks and differential shrinkage.
3. **Draft angles**: Minimum 1° for moulded or cast parts; 2–3° for textured
   surfaces.
4. **Radii**: Internal corners radius >= wall thickness / 2 to reduce stress
   concentration and aid material flow.
5. **Assembly**: Minimise part count. Every fastener is an assembly step; prefer
   snap fits or press fits where loads allow.
6. **Standardization**: Use standard hole sizes (ISO preferred fits), standard
   thread sizes (ISO metric), standard material stock thicknesses.

## Surface finish symbols (ISO 1302)

```
Ra  : arithmetic mean roughness
Rz  : mean roughness depth (peak-to-valley average)
Rmax: maximum peak-to-valley height

Typical process Ra:
  Rough turning    : 3.2 - 12.5 um
  Finish turning   : 0.8 - 3.2 um
  Grinding         : 0.2 - 0.8 um
  Lapping/honing   : 0.025 - 0.1 um
```

## Endurance limit modifiers (Marin equation)

```python
def endurance_limit_corrected(Su_MPa, ka_surface, kb_size, kc_load,
                               kd_temp=1.0, ke_reliability=1.0):
    """
    Corrected endurance limit Se via Marin factors (Shigley's).
    Se' = 0.5 * Su for steel (Su <= 1400 MPa).
    Returns Se (MPa).
    """
    Se_prime = 0.5 * Su_MPa if Su_MPa <= 1400 else 700
    return ka_surface * kb_size * kc_load * kd_temp * ke_reliability * Se_prime
```

## Reporting

Every mechanical design analysis should report:
1. Material specification (grade, minimum guaranteed properties with standard
   reference, e.g. ASTM A36, AISI 4140-HT).
2. Applied loads and load case (static, cyclic, impact).
3. Stress analysis method (analytical, FEM, or hand calculation with source).
4. Failure criteria used (von Mises, max shear, Goodman, etc.).
5. Safety factors and governing failure mode.
6. Manufacturing notes (tolerances, finishes, process constraints).
