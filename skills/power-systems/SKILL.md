---
name: power-systems
description: >
  Power systems analysis: load flow, short-circuit/fault analysis, protection
  coordination, and stability analysis using pandapower and PyPSA. Load this
  skill for network power flow, fault level calculation, grid planning, or
  renewable energy integration studies.
license: Apache-2.0
category: electrical-engineering
metadata:
  third_party:
    - kind: library
      name: pandapower
      license: BSD-3-Clause
      info_url: https://pandapower.readthedocs.io/
    - kind: library
      name: PyPSA
      license: MIT
      info_url: https://pypsa.org/
---

# Power Systems Analysis

## Load flow with pandapower

```python
import pandapower as pp
import pandapower.networks as pn

# Build a simple radial network from scratch
net = pp.create_empty_network(sn_mva=100)

# Buses
b1 = pp.create_bus(net, vn_kv=110, name="HV bus")
b2 = pp.create_bus(net, vn_kv=20,  name="MV bus")
b3 = pp.create_bus(net, vn_kv=20,  name="Load bus")

# Slack (grid connection)
pp.create_ext_grid(net, bus=b1, vm_pu=1.02, name="Grid")

# Transformer
pp.create_transformer(net, hv_bus=b1, lv_bus=b2, std_type="40 MVA 110/20 kV")

# Line
pp.create_line(net, from_bus=b2, to_bus=b3, length_km=5,
               std_type="NAYY 4x50 SE", name="Feeder 1")

# Load
pp.create_load(net, bus=b3, p_mw=8.0, q_mvar=3.0, name="Load 1")

# Solve load flow (Newton-Raphson by default)
pp.runpp(net)

# Results
print(net.res_bus[["vm_pu", "va_degree"]])
print(net.res_line[["p_from_mw", "q_from_mvar", "loading_percent"]])
```

## Using built-in test networks

```python
# IEEE test cases
net_ieee9  = pn.case9()
net_ieee14 = pn.case14()
net_ieee30 = pn.case30()

pp.runpp(net_ieee14)
print(f"Total load: {net_ieee14.res_load.p_mw.sum():.2f} MW")
print(f"Max bus voltage: {net_ieee14.res_bus.vm_pu.max():.4f} pu")
print(f"Min bus voltage: {net_ieee14.res_bus.vm_pu.min():.4f} pu")
```

## Short-circuit / fault analysis

```python
import pandapower.shortcircuit as sc

# Three-phase fault
sc.calc_sc(net, fault="3ph", branch_results=True)
print(net.res_bus_sc[["ikss_ka", "skss_mw"]])

# Single-phase fault
sc.calc_sc(net, fault="1ph", branch_results=False)
print("Max fault current (kA):", net.res_bus_sc.ikss_ka.max())
```

## Optimal power flow (OPF)

```python
# Set generator cost curves
pp.create_poly_cost(net, element=0, et="ext_grid", cp1_eur_per_mw=10)

# For generators:
# pp.create_gen(net, bus=b2, p_mw=5, vm_pu=1.0, controllable=True)
# pp.create_poly_cost(net, element=gen_idx, et="gen", cp1_eur_per_mw=30)

pp.runopp(net)
print("OPF cost:", net.res_cost, "EUR/h")
```

## PyPSA: multi-period / energy system planning

```python
import pypsa
import pandas as pd, numpy as np

network = pypsa.Network()
network.set_snapshots(pd.date_range("2024-01-01", periods=24, freq="h"))

network.add("Bus", "bus0")
network.add("Bus", "bus1")

network.add("Line", "line01", bus0="bus0", bus1="bus1",
            x=0.1, r=0.01, s_nom=200)

network.add("Generator", "wind",  bus="bus0", p_nom=100,
            marginal_cost=0,
            p_max_pu=pd.Series(np.random.uniform(0.2, 0.9, 24),
                                index=network.snapshots))
network.add("Generator", "gas",   bus="bus0", p_nom=200, marginal_cost=50)
network.add("Load",      "load1", bus="bus1",
            p_set=pd.Series(np.random.uniform(80, 150, 24),
                             index=network.snapshots))

network.optimize()

print("Total cost:", network.objective, "EUR")
print("Wind curtailment:", (network.generators_t.p_max_pu["wind"] * 100
      - network.generators_t.p["wind"]).clip(lower=0).sum(), "MWh")
```

## Per-unit system conversion

```python
def to_per_unit(V_actual, V_base, S_base, Z_actual=None, I_actual=None):
    """
    Convert to per-unit system.
    V_base : base voltage (V or kV, consistent with V_actual)
    S_base : base power (VA or MVA)
    Returns dict of pu values.
    """
    Z_base = V_base**2 / S_base
    I_base = S_base / (np.sqrt(3) * V_base)   # for 3-phase
    result = {"V_pu": V_actual / V_base}
    if Z_actual is not None:
        result["Z_pu"] = Z_actual / Z_base
    if I_actual is not None:
        result["I_pu"] = I_actual / I_base
    return result
```

## Protection coordination (time-overcurrent relay)

```python
def inverse_time_relay_tripping(I_fault, I_pickup, TDS, curve="IEC Normal Inverse"):
    """
    Tripping time for an inverse-time overcurrent relay.
    I_fault  : fault current (A)
    I_pickup : pickup current setting (A)
    TDS      : time dial setting (0.05 - 10.0 typical)
    Returns tripping time in seconds.
    """
    M = I_fault / I_pickup
    if M <= 1:
        return float("inf")  # relay does not operate

    curves = {
        "IEC Normal Inverse":  (0.14, 0.02),
        "IEC Very Inverse":    (13.5, 1.0),
        "IEC Extremely Inverse": (80.0, 2.0),
        "IEEE Moderately Inverse": (0.0515, 0.02),
    }
    A, B = curves[curve]
    t = TDS * A / (M**B - 1)
    return t

# Example: coordination check
t_downstream = inverse_time_relay_tripping(5000, 200, TDS=0.2)
t_upstream   = inverse_time_relay_tripping(5000, 400, TDS=0.5)
print(f"Downstream trips at {t_downstream:.3f} s, upstream at {t_upstream:.3f} s")
print(f"Coordination margin: {t_upstream - t_downstream:.3f} s (min 0.3 s required)")
```

## Reporting

For every power systems study, report:
1. Network topology and base case data (bus count, voltage levels, installed capacity).
2. Load flow: bus voltage profile (magnitude and angle), line loading percentage,
   reactive power balance.
3. Violations: under/over-voltage (typical limits: 0.95-1.05 pu), thermal overload.
4. Fault study: maximum and minimum fault currents at each bus, fault level (MVA).
5. Protection coordination: time-current curves with margins, selectivity table.
6. Standard used (IEC 60909 for short circuit, NERC standards for transmission,
   IEEE 1547 for distributed resources).
