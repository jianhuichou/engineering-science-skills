---
name: heat-transfer
description: >
  Analytical and numerical heat transfer workflows: conduction (Fourier,
  finite-difference), convection (forced and natural), radiation (Stefan-
  Boltzmann, view factors), and combined modes. Covers 1-D and 2-D transient
  analysis, fin efficiency, heat exchanger design (LMTD, NTU-effectiveness),
  and thermal resistance networks. Load this skill for thermal analysis,
  thermal management, or HVAC design tasks.
license: Apache-2.0
category: mechanical-engineering
---

# Heat Transfer

## Modes at a glance

| Mode | Governing equation | Key parameter |
|---|---|---|
| Conduction | q = -k * A * dT/dx | Thermal conductivity k (W/m-K) |
| Convection | q = h * A * (Ts - T_inf) | Heat transfer coefficient h (W/m^2-K) |
| Radiation | q = epsilon * sigma * A * (Ts^4 - Tsurr^4) | Emissivity epsilon, sigma = 5.67e-8 |

## 1-D steady-state conduction: thermal resistance network

```python
def thermal_resistance_wall(layers):
    """
    Total thermal resistance for a composite plane wall.
    layers: list of (k_W_mK, thickness_m)
    Returns R_total (K/W per unit area).
    """
    return sum(t / k for k, t in layers)

def heat_flux(T_hot, T_cold, R_total):
    """q'' = (T_hot - T_cold) / R_total  (W/m^2 when R is per unit area)."""
    return (T_hot - T_cold) / R_total

# Example: insulated wall
layers = [(0.9, 0.20), (0.04, 0.10), (0.5, 0.012)]  # concrete, insulation, gypsum
R = thermal_resistance_wall(layers)
q = heat_flux(T_hot=22, T_cold=-10, R_total=R)
print(f"R = {R:.3f} m^2-K/W,  q = {q:.1f} W/m^2")
```

## Convection correlations

```python
import numpy as np

def h_forced_pipe(Re, Pr, D, k_fluid, L=None):
    """
    h for internal forced convection in a pipe.
    Uses Dittus-Boelter (Re > 10000) or Sieder-Tate.
    Returns h (W/m^2-K).
    """
    if Re > 10000:
        Nu = 0.023 * Re**0.8 * Pr**0.4   # Dittus-Boelter, heating
    elif Re > 2300:
        # Transitional — use Gnielinski
        f = (0.790 * np.log(Re) - 1.64)**(-2)
        Nu = (f/8 * (Re - 1000) * Pr) / (1 + 12.7 * (f/8)**0.5 * (Pr**(2/3) - 1))
    else:
        Nu = 3.66   # laminar, uniform wall temp
    if L:
        Nu = max(Nu, 1.86 * (Re * Pr * D / L)**(1/3))
    return Nu * k_fluid / D

def h_natural_vertical_plate(Ts, T_inf, L, fluid="air"):
    """
    h for natural convection on a vertical plate (Churchill-Chu).
    Returns h (W/m^2-K).
    """
    props = {
        "air":   {"k": 0.026, "nu": 1.56e-5, "alpha": 2.21e-5, "beta": 1/298},
        "water": {"k": 0.609, "nu": 1.00e-6, "alpha": 1.43e-7, "beta": 2.1e-4},
    }
    p = props[fluid]
    Pr = p["nu"] / p["alpha"]
    Ra = 9.81 * p["beta"] * abs(Ts - T_inf) * L**3 / (p["nu"] * p["alpha"])
    Nu = (0.825 + 0.387 * Ra**(1/6) / (1 + (0.492/Pr)**(9/16))**(8/27))**2
    return Nu * p["k"] / L
```

## Fin efficiency and fin array

```python
def fin_efficiency_rectangular(L, t, k, h):
    """
    Efficiency of a rectangular fin.
    L : fin length (m)
    t : fin thickness (m)
    k : fin conductivity (W/m-K)
    h : convection coefficient (W/m^2-K)
    Returns eta_fin (dimensionless, 0-1).
    """
    P = 2 * (t + 1)    # perimeter per unit width (approx. for wide fin)
    Ac = t * 1         # cross-section per unit width
    m = np.sqrt(h * P / (k * Ac))
    Lc = L + t / 2    # corrected length
    eta = np.tanh(m * Lc) / (m * Lc)
    return eta
```

## Heat exchanger: LMTD method

```python
def lmtd_counter(Thi, Tho, Tci, Tco):
    """Log mean temperature difference for counter-flow HX."""
    dT1 = Thi - Tco
    dT2 = Tho - Tci
    if abs(dT1 - dT2) < 1e-6:
        return dT1
    return (dT1 - dT2) / np.log(dT1 / dT2)

def hx_area(Q_W, U, LMTD):
    """Required heat transfer area A (m^2). U in W/m^2-K."""
    return Q_W / (U * LMTD)

# Example: counter-flow water-to-water HX
LMTD = lmtd_counter(Thi=80, Tho=50, Tci=20, Tco=45)
A = hx_area(Q_W=50e3, U=1500, LMTD=LMTD)
print(f"LMTD = {LMTD:.1f} K,  A = {A:.2f} m^2")
```

## Heat exchanger: NTU-effectiveness

```python
def hx_effectiveness_counterflow(NTU, Cr):
    """
    Effectiveness of a counter-flow HX.
    NTU = U*A / C_min
    Cr  = C_min / C_max  (heat capacity rate ratio)
    """
    if Cr == 1:
        return NTU / (1 + NTU)
    return (1 - np.exp(-NTU * (1 - Cr))) / (1 - Cr * np.exp(-NTU * (1 - Cr)))
```

## 2-D transient conduction: finite differences

```python
def transient_2d_conduction(T0, Tb, alpha, dx, dy, dt, n_steps):
    """
    Explicit finite-difference solution of 2-D transient conduction.
    T0     : initial temperature array (ny x nx)
    Tb     : boundary temperature (constant, all edges)
    alpha  : thermal diffusivity (m^2/s)
    dx, dy : grid spacing (m)
    dt     : time step (s) -- must satisfy Fourier stability: dt <= dx^2/(4*alpha)
    """
    import numpy as np
    T = T0.copy().astype(float)
    Fo_x = alpha * dt / dx**2
    Fo_y = alpha * dt / dy**2
    assert Fo_x + Fo_y <= 0.5, f"Stability criterion violated: Fo_x+Fo_y={Fo_x+Fo_y:.3f} > 0.5"

    for _ in range(n_steps):
        Tn = T.copy()
        T[1:-1, 1:-1] = (Tn[1:-1, 1:-1]
                         + Fo_x * (Tn[1:-1, 2:] - 2*Tn[1:-1, 1:-1] + Tn[1:-1, :-2])
                         + Fo_y * (Tn[2:, 1:-1] - 2*Tn[1:-1, 1:-1] + Tn[:-2, 1:-1]))
        T[0, :] = T[-1, :] = T[:, 0] = T[:, -1] = Tb   # boundary conditions
    return T
```

## Radiation: Stefan-Boltzmann and view factors

```python
SIGMA = 5.670374e-8   # W/m^2-K^4

def radiation_heat_flux(T1_K, T2_K, eps1=1.0, eps2=1.0, F12=1.0):
    """
    Net radiation between two large parallel plates (infinite-plate approximation
    when F12=1). Returns q'' (W/m^2) from surface 1 to surface 2.
    """
    denom = 1/eps1 + 1/eps2 - 1   # radiation resistance for parallel plates
    return SIGMA * (T1_K**4 - T2_K**4) / denom

# View factor for two coaxial disks (Howell et al., Catalog No. C-12)
def view_factor_parallel_disks(R1, R2, h):
    """View factor F_12 for two coaxial parallel disks."""
    r1, r2 = R1/h, R2/h
    S = 1 + (1 + r2**2) / r1**2
    return 0.5 * (S - np.sqrt(S**2 - 4 * (r2/r1)**2))
```

## Validation checks

- Fourier stability criterion satisfied for explicit FD: dt <= dx^2 / (4*alpha).
- Heat balance: total heat in = total heat out + change in stored energy.
- NTU-effectiveness values bounded [0, 1].
- LMTD requires both temperature differences to be positive (no temperature
  cross in co-current flow beyond Tco > Thi).
- Nusselt number correlations valid only within their stated Re/Pr range.
- State fluid properties and their temperature basis in every report.
