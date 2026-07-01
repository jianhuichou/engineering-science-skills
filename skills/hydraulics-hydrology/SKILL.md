---
name: hydraulics-hydrology
description: >
  Open-channel hydraulics and hydrological analysis: Manning's equation,
  HEC-RAS/HEC-HMS data import, rational method, unit hydrograph, storm
  routing, and stormwater design. Load this skill for watershed analysis,
  flood routing, culvert sizing, channel design, or stormwater management tasks.
license: Apache-2.0
category: civil-engineering
metadata:
  third_party:
    - kind: service
      name: USGS National Water Information System (NWIS)
      info_url: https://waterdata.usgs.gov/nwis
      privacy_url: https://www.usgs.gov/privacy-policy
    - kind: service
      name: NOAA Atlas 14 (precipitation frequency)
      info_url: https://hdsc.nws.noaa.gov/hdsc/pfds/
---

# Hydraulics and Hydrology

## Open-channel flow (Manning's equation)

```python
import numpy as np

def mannings_velocity(n, R, S):
    """
    Flow velocity using Manning's equation (SI units).
    n : Manning's roughness coefficient (dimensionless)
    R : hydraulic radius (m) = A / P
    S : channel slope (m/m)
    Returns V (m/s).
    """
    return (1.0 / n) * R**(2/3) * S**0.5

def mannings_discharge(n, A, R, S):
    """Flow rate Q (m^3/s)."""
    return A * mannings_velocity(n, R, S)

def rectangular_channel(b, y, n, S):
    """
    Normal depth flow in a rectangular channel.
    b : bottom width (m)
    y : flow depth (m)
    Returns V (m/s) and Q (m^3/s).
    """
    A = b * y
    P = b + 2 * y
    R = A / P
    V = mannings_velocity(n, R, S)
    return V, A * V

# Example: concrete rectangular channel
V, Q = rectangular_channel(b=3.0, y=1.2, n=0.013, S=0.001)
print(f"V = {V:.2f} m/s,  Q = {Q:.2f} m^3/s")
```

**Common Manning's n values:**

| Material | n range |
|---|---|
| Concrete (good finish) | 0.011 - 0.013 |
| Corrugated metal pipe | 0.021 - 0.030 |
| Earthen channel, clean | 0.022 - 0.026 |
| Natural stream, clean | 0.025 - 0.035 |
| Natural stream, weedy | 0.035 - 0.050 |

## Normal depth by iteration

```python
from scipy.optimize import brentq

def normal_depth(Q, b, n, S, y_lo=0.01, y_hi=20.0):
    """Find normal depth yn for a rectangular channel."""
    def residual(y):
        A = b * y; P = b + 2*y; R = A/P
        return (1/n) * A * R**(2/3) * S**0.5 - Q
    return brentq(residual, y_lo, y_hi)

yn = normal_depth(Q=5.0, b=3.0, n=0.013, S=0.001)
print(f"Normal depth: {yn:.3f} m")
```

## Rational method (peak runoff)

```python
def rational_method(C, i_mm_hr, A_ha):
    """
    Peak runoff Q (m^3/s) using the Rational Method.
    C       : runoff coefficient (0-1)
    i_mm_hr : rainfall intensity (mm/hr) for the design storm
    A_ha    : drainage area (hectares)
    """
    return C * (i_mm_hr / 3600) * (A_ha * 1e4) / 1000
    # Q = C * i[m/s] * A[m^2]

Q_peak = rational_method(C=0.70, i_mm_hr=75, A_ha=10.5)
print(f"Q_peak = {Q_peak:.2f} m^3/s")
```

**Typical runoff coefficients (C):**

| Land use | C range |
|---|---|
| Commercial / downtown | 0.70 - 0.95 |
| Residential (lawns) | 0.25 - 0.40 |
| Parks, cemeteries | 0.10 - 0.25 |
| Impervious pavement | 0.70 - 0.95 |
| Forest / woodland | 0.05 - 0.25 |

## NOAA Atlas 14 — precipitation frequency

Retrieve design storm intensity from NOAA's precipitation frequency server:

```python
def noaa_pfds(lat, lon, return_period_yr=100, duration_hr=1):
    """
    Retrieve precipitation frequency estimates from NOAA Atlas 14.
    Returns intensity in mm/hr for the given return period and duration.
    """
    import urllib.request, json
    # NOAA PFDS REST API
    url = (f"https://hdsc.nws.noaa.gov/cgi-bin/hdsc/new/fe_text_mean.csv"
           f"?lat={lat}&lon={lon}&type=pf&data=depth&units=metric&series=pds")
    # Note: NOAA PFDS does not have a clean REST JSON API; retrieve the CSV
    # and parse the row matching the desired duration and return period.
    # For automation, use the NOAA Precip Frequency Data Server REST endpoint.
    raise NotImplementedError(
        "Query NOAA Atlas 14 via https://hdsc.nws.noaa.gov/hdsc/pfds/ for "
        f"lat={lat}, lon={lon}. Select duration={duration_hr}h and "
        f"ARI={return_period_yr} yr to obtain design rainfall depth."
    )
```

For programmatic access, use the USGS National Water Information System API:

```python
def usgs_streamflow(site_no, start_date, end_date):
    """
    Retrieve daily mean streamflow (m^3/s) from USGS NWIS.
    site_no : USGS station number (string, e.g. "01646500")
    """
    import urllib.request, json
    url = (f"https://waterservices.usgs.gov/nwis/dv/"
           f"?format=json&sites={site_no}"
           f"&startDT={start_date}&endDT={end_date}"
           f"&parameterCd=00060")   # 00060 = discharge
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.loads(r.read())
    series = data["value"]["timeSeries"][0]["values"][0]["value"]
    import pandas as pd
    df = pd.DataFrame(series)
    df["dateTime"] = pd.to_datetime(df["dateTime"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce") * 0.0283168  # cfs -> m^3/s
    return df.set_index("dateTime")[["value"]].rename(columns={"value": "Q_m3s"})
```

## HEC-RAS results parsing

HEC-RAS exports results to HDF5 (`.hdf`) for steady/unsteady flow:

```python
import h5py, pandas as pd

def read_hec_ras_profiles(hdf_path, plan="Plan 01"):
    """
    Extract water surface elevation and flow profiles from HEC-RAS HDF output.
    Returns a DataFrame indexed by river station.
    """
    with h5py.File(hdf_path, "r") as f:
        results = f[f"Results/Steady/Output/Output Blocks/Base Output/Steady Profiles"]
        profiles = {}
        for profile in results.keys():
            grp = results[profile]
            stations = grp["River Sta"][:]
            wse = grp["W.S. Elev"][:]
            q = grp["Flow"][:]
            profiles[profile] = pd.DataFrame(
                {"WSE_m": wse, "Q_m3s": q}, index=stations
            )
    return profiles
```

## Culvert sizing (headwater depth)

```python
def culvert_headwater(Q, D, L, n=0.013, S=0.01, ke=0.5):
    """
    Approximate headwater depth for a circular culvert (outlet control).
    Q : design discharge (m^3/s)
    D : culvert diameter (m)
    L : culvert length (m)
    n : Manning's n for culvert material
    ke: entrance loss coefficient
    Returns HW (m) — headwater depth above culvert inlet invert.
    """
    import numpy as np
    A = np.pi * D**2 / 4
    P = np.pi * D
    R = A / P
    # Full-flow velocity using Manning's
    V = (1/n) * R**(2/3) * S**0.5
    # Headwater for outlet control (energy equation simplified)
    V_design = Q / A
    hf = (n**2 * V_design**2 * L) / R**(4/3)  # friction head loss
    he = ke * V_design**2 / (2 * 9.81)         # entrance loss
    HW = D + hf + he + S * L
    return HW
```

## Reporting

For hydraulic analyses, always report:
1. Design storm return period and source of rainfall data (NOAA Atlas 14,
   local IDF, or measured gauge data with station ID and period of record).
2. Watershed area, land use, and runoff coefficient or CN used.
3. Peak flow estimate and the method (Rational, SCS TR-55, unit hydrograph).
4. Channel/pipe capacity and whether it exceeds the design flow.
5. Freeboard and overflow risk at the design return period.
6. Applicable standard (ASCE, FHWA, state DOT drainage manual — state edition).
