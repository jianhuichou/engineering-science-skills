---
name: building-codes
description: >
  Engineering standards and building code workflows. Covers retrieval and
  cross-referencing of IBC, ASCE 7, AISC 360, ACI 318, Eurocode, and related
  standards. Load this skill when a task requires citing code provisions,
  performing load combination checks, or documenting code compliance. All
  design values must be grounded in retrieved or explicitly cited standard
  text — never recalled from training alone.
license: Apache-2.0
category: civil-engineering
---

# Building Codes and Engineering Standards

Engineering claims — load combinations, strength reduction factors, drift
limits, seismic hazard parameters — must be grounded in a specific edition
of a standard, not recalled from training. This skill establishes the
retrieval and citation workflow and documents key provisions from the most
commonly referenced standards.

## Principle: cite, don't recall

When a calculation uses a code-specified value (phi factor, importance factor,
spectral acceleration, load factor, deflection limit), state:
- The standard by name, section number, and edition year.
- The table or equation identifier.
- The value used.

Example: "Flexural resistance factor phi = 0.90 per AISC 360-22 Section F1."

Never write a code value without the citation. If you are unsure of the
current edition or a specific provision, retrieve it first.

## ASCE 7 — Minimum Design Loads

**Load combinations (ASCE 7-22 Section 2.3.1, LRFD):**

| Combination | Expression |
|---|---|
| 1 | 1.4D |
| 2 | 1.2D + 1.6L + 0.5(Lr or S or R) |
| 3 | 1.2D + 1.6(Lr or S or R) + (L or 0.5W) |
| 4 | 1.2D + 1.0W + L + 0.5(Lr or S or R) |
| 5 | 0.9D + 1.0W |
| 6 | 1.2D + 1.0E + L + 0.2S |
| 7 | 0.9D + 1.0E |

D=dead, L=live, Lr=roof live, S=snow, R=rain, W=wind, E=seismic.

**Seismic hazard (ASCE 7-22 Chapter 11):**
- Site class A–F based on Vs30.
- Design spectral parameters SDS and SD1 from USGS Unified Hazard Tool or
  ASCE 7 Hazard Tool (https://asce7hazardtool.online/).
- Always retrieve SDS/SD1 from the tool for the project location and site
  class rather than using generic values.

```python
# Example: retrieve USGS seismic hazard data
import urllib.request, json

lat, lon = 37.77, -122.42   # San Francisco
url = (f"https://earthquake.usgs.gov/hazards/designmaps/us/json.php"
       f"?latitude={lat}&longitude={lon}&siteClass=D&returnPeriod=2475")
with urllib.request.urlopen(url) as r:
    data = json.loads(r.read())
# data contains Ss, S1, SDS, SD1 per ASCE 7 site class D
```

## IBC — International Building Code

Key occupancy/use provisions:
- Table 1604.3: deflection limits (L/360 for floor live load, L/240 for
  roof with live/snow, L/480 for elements supporting brittle finishes).
- Table 1607.1: minimum uniformly distributed live loads by occupancy.
- Chapter 16: structural design requirements and reference to ASCE 7.

## AISC 360 — Steel Construction

LRFD design check template for beams (Chapter F):

```python
# AISC 360-22 beam flexure check
def aisc_flexure_check(Mu_kNm, Zx_cm3, Fy_MPa, Lb_m=0, Lp_m=None, Lr_m=None, Mp_kNm=None):
    """
    Simplified AISC 360 Chapter F beam check.
    Mu_kNm : required moment (kN-m)
    Zx_cm3 : plastic section modulus (cm^3)
    Fy_MPa : yield stress (MPa)
    Lb_m   : unbraced length (m)
    Returns phi*Mn (kN-m) and DCR.
    """
    phi = 0.90
    Mp = Fy_MPa * Zx_cm3 * 1e3 / 1e6  # kN-m (MPa*cm^3 = N*mm = 1e-3 kN-m)
    if Mp_kNm:
        Mp = Mp_kNm

    if Lp_m and Lr_m and Lb_m > Lp_m:
        if Lb_m <= Lr_m:
            # Inelastic LTB (linear interpolation)
            Mn = Mp - (Mp - 0.7*Fy_MPa * Zx_cm3 * 1e3 / 1e6) * (Lb_m - Lp_m) / (Lr_m - Lp_m)
        else:
            # Elastic LTB -- simplified; use AISC tables for Cb
            Mn = 0.7 * Fy_MPa * Zx_cm3 * 1e3 / 1e6
        phi_Mn = phi * min(Mn, Mp)
    else:
        phi_Mn = phi * Mp

    DCR = Mu_kNm / phi_Mn
    return phi_Mn, DCR
```

## ACI 318 — Concrete

Strength reduction factors phi (ACI 318-19 Table 21.2.1):

| Action | phi |
|---|---|
| Tension-controlled flexure/axial | 0.90 |
| Compression-controlled (spirals) | 0.75 |
| Compression-controlled (tied) | 0.65 |
| Shear/torsion | 0.75 |
| Bearing | 0.65 |

Minimum reinforcement ratio for beams (ACI 318-19 Section 9.6.1.2):
```
rho_min = max(0.25*sqrt(f'c)/fy, 1.4/fy)   # f'c, fy in MPa
```

## Eurocode framework (EN 1990 / EN 1991 / EN 1992-1-1 / EN 1993-1-1)

Fundamental load combination (EN 1990 Eq. 6.10):
```
Sum(gamma_Gi * Gk,i) + gamma_Q1 * Qk,1 + Sum(gamma_Qi * psi_0i * Qk,i)
```
Persistent/transient: gamma_G = 1.35 (unfavourable), 1.0 (favourable);
gamma_Q = 1.5. National Annexes modify psi factors — always check the
applicable NA.

## USGS and NEHRP data retrieval

For seismic design, retrieve spectral accelerations from USGS web services:

```python
def get_usgs_seismic(lat, lon, risk_cat="II", site_class="D", edition="asce7-22"):
    """
    Retrieve USGS design map parameters for a site.
    Returns dict with Ss, S1, SDS, SD1.
    """
    import urllib.request, json, urllib.parse
    params = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon,
        "riskCategory": risk_cat, "siteClass": site_class, "title": "Site"
    })
    url = f"https://earthquake.usgs.gov/ws/designmaps/{edition}.json?{params}"
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read())["response"]["data"]
```

## Code check reporting template

Every code compliance check deliverable should include:

1. Applicable standard(s) with edition year and relevant section/table numbers.
2. Design inputs: loads, geometry, material properties, site parameters.
3. Load combinations applied (by standard reference).
4. For each element checked: demand, capacity, phi*Rn or Rd, and DCR.
5. Governing failure mode for each element.
6. Pass/Fail summary table.

Flag any provision where the edition year is uncertain; retrieve the current
edition from the publisher or the standard-development body's website before
using it in a calculation that will be acted upon.
