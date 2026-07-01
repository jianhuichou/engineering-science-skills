---
name: geotechnical-analysis
description: >
  Geotechnical engineering workflows: soil classification, bearing capacity,
  slope stability, and settlement analysis. Uses Python libraries (geopy,
  scipy, numpy) and USGS/NEHRP data connectors. Load this skill for
  foundation design, earthwork, retaining wall, or site characterization tasks.
license: Apache-2.0
category: civil-engineering
---

# Geotechnical Analysis

Geotechnical analysis converts site investigation data (borehole logs, SPT
N-values, lab tests) into foundation design parameters, bearing capacity
estimates, slope stability factors of safety, and settlement predictions.

## Soil classification

### USCS (Unified Soil Classification System)

```python
import numpy as np

def uscs_classify(fines_pct, sand_pct, gravel_pct, LL=None, PI=None, Cu=None, Cc=None):
    """
    Returns USCS symbol and description.
    fines_pct: % passing No. 200 sieve
    LL, PI: Atterberg limits (required for fine-grained soils)
    Cu, Cc: uniformity and curvature coefficients (required for coarse)
    """
    if fines_pct > 50:
        # Fine-grained
        if LL is None or PI is None:
            raise ValueError("LL and PI required for fine-grained classification")
        if LL < 50:
            return ("CL", "Lean clay") if PI > 7 and PI >= 0.73*(LL-20) else ("ML", "Silt")
        else:
            return ("CH", "Fat clay") if PI >= 0.73*(LL-20) else ("MH", "Elastic silt")
    else:
        # Coarse-grained
        prefix = "G" if gravel_pct > sand_pct else "S"
        if fines_pct < 5:
            if Cu is None or Cc is None:
                raise ValueError("Cu and Cc required for clean coarse soil")
            well = (Cu >= 4 if prefix == "G" else Cu >= 6) and 1 <= Cc <= 3
            return (f"{prefix}W", "Well-graded") if well else (f"{prefix}P", "Poorly-graded")
        else:
            return (f"{prefix}M", "Silty") if PI < 4 else (f"{prefix}C", "Clayey")
```

## Bearing capacity (Terzaghi / Meyerhof)

```python
def terzaghi_bearing_capacity(c, phi_deg, gamma, Df, B, shape="strip"):
    """
    Ultimate bearing capacity using Terzaghi equations.
    c       : cohesion (kPa)
    phi_deg : friction angle (degrees)
    gamma   : unit weight (kN/m^3)
    Df      : depth of footing (m)
    B       : width of footing (m)
    shape   : 'strip' | 'square' | 'circular'
    Returns qu in kPa.
    """
    import numpy as np
    phi = np.radians(phi_deg)
    Nq = np.exp(np.pi * np.tan(phi)) * np.tan(np.radians(45) + phi/2)**2
    Nc = (Nq - 1) / np.tan(phi) if phi_deg > 0 else 5.14
    Ng = 2 * (Nq + 1) * np.tan(phi)

    if shape == "strip":
        qu = c * Nc + gamma * Df * Nq + 0.5 * gamma * B * Ng
    elif shape == "square":
        qu = 1.3 * c * Nc + gamma * Df * Nq + 0.4 * gamma * B * Ng
    elif shape == "circular":
        qu = 1.3 * c * Nc + gamma * Df * Nq + 0.3 * gamma * B * Ng
    else:
        raise ValueError(f"Unknown shape: {shape}")
    return qu

# Example
qu = terzaghi_bearing_capacity(c=20, phi_deg=30, gamma=18, Df=1.5, B=2.0, shape="square")
q_allowable = qu / 3.0  # FS = 3
print(f"qu = {qu:.1f} kPa,  q_allow = {q_allowable:.1f} kPa")
```

## SPT-based correlations

```python
def spt_to_phi(N60, sigma_v_kPa):
    """Approximate friction angle from corrected SPT N60 (Wolff 1989)."""
    CN = min(2.0, (100 / sigma_v_kPa)**0.5)   # overburden correction
    N1_60 = CN * N60
    phi = 27.1 + 0.3 * N1_60 - 0.00054 * N1_60**2
    return phi   # degrees

def spt_to_cu(N60):
    """Undrained shear strength estimate for clays (kPa)."""
    return 6.25 * N60  # approximate, Stroud (1974)
```

## Slope stability (Bishop simplified method)

```python
def bishop_simplified(slices):
    """
    slices: list of dicts, each with keys:
      W    : slice weight (kN)
      b    : slice width (m)
      alpha: base inclination angle (degrees, positive downslope)
      l    : arc length of base (m)
      c    : cohesion on base (kPa)
      phi  : friction angle on base (degrees)
      u    : pore pressure on base (kPa)
    Returns FS (factor of safety).
    """
    import numpy as np
    from scipy.optimize import brentq

    def FS_eq(FS):
        num = 0.0
        den = 0.0
        for s in slices:
            a = np.radians(s["alpha"])
            p = np.radians(s["phi"])
            W, b, c, phi, u, l = s["W"], s["b"], s["c"], s["phi"], s["u"], s["l"]
            m_alpha = np.cos(a) + np.sin(a) * np.tan(p) / FS
            num += (c * b + (W - u * b) * np.tan(p)) / m_alpha
            den += W * np.sin(a)
        return num / den - FS

    FS = brentq(FS_eq, 1e-3, 20.0)
    return FS
```

## Settlement (consolidation)

```python
def consolidation_settlement(Cc, e0, sigma_v0, delta_sigma, H, Cs=None, sigma_pc=None):
    """
    Primary consolidation settlement.
    Cc       : compression index
    e0       : initial void ratio
    sigma_v0 : initial effective vertical stress (kPa)
    delta_sigma : stress increase (kPa) from Boussinesq or 2:1 distribution
    H        : layer thickness (m)
    Cs       : swelling index (for OC clay, optional)
    sigma_pc : preconsolidation pressure (kPa, optional)
    Returns settlement in m.
    """
    import numpy as np
    sigma_f = sigma_v0 + delta_sigma

    if sigma_pc and Cs and sigma_v0 < sigma_pc < sigma_f:
        # Overconsolidated -> normally consolidated transition
        Sc = (H / (1 + e0)) * (Cs * np.log10(sigma_pc / sigma_v0)
                                + Cc * np.log10(sigma_f / sigma_pc))
    elif sigma_pc and Cs and sigma_f <= sigma_pc:
        Sc = (H / (1 + e0)) * Cs * np.log10(sigma_f / sigma_v0)
    else:
        Sc = (H / (1 + e0)) * Cc * np.log10(sigma_f / sigma_v0)
    return Sc
```

## Stress increase below a footing (Boussinesq 2:1 approximation)

```python
def boussinesq_2to1(Q, B, L, z):
    """
    Vertical stress increase at depth z below center of a rectangular loaded area.
    Q : total load (kN)
    B, L : footing dimensions (m)
    z    : depth (m)
    """
    delta_sigma = Q / ((B + z) * (L + z))
    return delta_sigma  # kPa
```

## Reporting pattern

For every geotechnical analysis, report:
1. Site/borehole data source and assumptions (water table depth, unit weights
   used, standard cited — ASCE 7, FHWA, Eurocode 7).
2. Computed parameters table (phi, c, Cc, e0, N-values with corrections).
3. Design values with factor of safety applied.
4. Settlement estimates at multiple depths if applicable.

State all assumptions explicitly. Geotechnical parameters carry significant
uncertainty; bound results with a sensitivity range where the input variability
is high (e.g., SPT-derived phi ranges by +/-3 degrees).
