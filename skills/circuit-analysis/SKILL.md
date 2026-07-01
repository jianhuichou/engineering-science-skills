---
name: circuit-analysis
description: >
  SPICE netlist parsing and circuit simulation, symbolic circuit analysis with
  lcapy, and Python-based circuit solvers. Covers DC/AC/transient analysis,
  Thevenin/Norton equivalents, filter design, op-amp circuits, and two-port
  parameters. Load this skill for circuit simulation, network analysis, or
  analog circuit design tasks.
license: Apache-2.0
category: electrical-engineering
metadata:
  third_party:
    - kind: library
      name: PySpice
      license: GPL-3.0
      info_url: https://pyspice.fabrice-salvaire.fr/
    - kind: library
      name: lcapy
      license: MIT
      info_url: https://lcapy.readthedocs.io/
---

# Circuit Analysis

## Symbolic analysis with lcapy

lcapy provides symbolic circuit analysis using SymPy under the hood.

```python
from lcapy import Circuit

# Define circuit as a netlist string
cct = Circuit("""
V1 1 0 10
R1 1 2 1k
R2 2 0 2k
C1 2 0 1u
""")

# DC operating point
Vout_dc = cct["2"].V.dc
print("Vout DC:", Vout_dc)

# AC transfer function
H = cct["2"].V / cct["V1"].V
print("Transfer function H(s):", H.simplify())
print("Voltage divider:", H(f=1e3))  # evaluate at 1 kHz
```

### Impedance and admittance

```python
from lcapy import R, C, L, Vac

# Series RLC impedance
Z = R(1e3) + L(1e-3) + C(1e-6)
print("Z(s):", Z.Z)
print("|Z| at 1 kHz:", abs(complex(Z.Z(j=2*3.14159*1e3))))
```

## Node voltage method (MNA) from scratch

For quick custom solvers without lcapy:

```python
import numpy as np

def solve_dc_mna(nodes, voltage_sources, resistors):
    """
    Solve DC circuit using Modified Nodal Analysis.
    nodes           : list of node names (ground = "0" or "GND")
    voltage_sources : list of (name, pos_node, neg_node, V)
    resistors       : list of (name, node_a, node_b, R)
    Returns dict {node: voltage}.
    """
    # Map nodes to indices (excluding ground)
    node_list = [n for n in nodes if n not in ("0", "GND")]
    n = len(node_list); m = len(voltage_sources)
    idx = {name: i for i, name in enumerate(node_list)}

    G = np.zeros((n + m, n + m))
    b = np.zeros(n + m)

    for _, na, nb, R in resistors:
        g = 1.0 / R
        if na in idx: G[idx[na], idx[na]] += g
        if nb in idx: G[idx[nb], idx[nb]] += g
        if na in idx and nb in idx:
            G[idx[na], idx[nb]] -= g
            G[idx[nb], idx[na]] -= g

    for k, (_, pn, nn, V) in enumerate(voltage_sources):
        row = n + k
        if pn in idx: G[row, idx[pn]] = 1; G[idx[pn], row] = 1
        if nn in idx: G[row, idx[nn]] = -1; G[idx[nn], row] = -1
        b[row] = V

    x = np.linalg.solve(G, b)
    return {name: x[i] for name, i in idx.items()}
```

## PySpice simulation workflow

```python
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

circuit = Circuit("RC Low-pass")
circuit.V("input", "in", circuit.gnd, 1@u_V)
circuit.R(1, "in", "out", 1@u_kOhm)
circuit.C(1, "out", circuit.gnd, 1@u_uF)

from PySpice.Spice.NgSpice.Shared import NgSpiceShared
simulator = circuit.simulator(temperature=25, nominal_temperature=25)
analysis = simulator.ac(variation="dec", number_of_points=100,
                        start_frequency=1@u_Hz, stop_frequency=1@u_MHz)

import numpy as np, pandas as pd
freq = np.array(analysis.frequency)
Vout = np.abs(np.array(analysis["out"]))
df = pd.DataFrame({"freq_Hz": freq, "Vout_V": Vout})
```

## Filter design with scipy

```python
from scipy import signal

def design_butterworth_lowpass(fc_hz, order, fs_hz):
    """
    Design a Butterworth low-pass filter.
    Returns (b, a) coefficients for use with scipy.signal.filtfilt.
    """
    Wn = fc_hz / (fs_hz / 2)   # normalized cutoff frequency
    b, a = signal.butter(order, Wn, btype="low")
    return b, a

def apply_filter(b, a, data):
    from scipy.signal import filtfilt
    return filtfilt(b, a, data)

# Frequency response
def filter_frequency_response(b, a, fs_hz, n_points=1024):
    import numpy as np
    w, H = signal.freqz(b, a, worN=n_points, fs=fs_hz)
    return w, 20 * np.log10(np.abs(H))   # dB

# Bode plot
import matplotlib.pyplot as plt
b, a = design_butterworth_lowpass(fc_hz=1000, order=4, fs_hz=48000)
w, H_dB = filter_frequency_response(b, a, fs_hz=48000)
fig, ax = plt.subplots()
ax.semilogx(w, H_dB)
ax.set_xlabel("Frequency (Hz)"); ax.set_ylabel("Magnitude (dB)")
ax.grid(True, which="both")
fig.savefig("bode_lowpass.png", dpi=150)
```

## Thevenin equivalent

```python
def thevenin_from_measurements(V_oc, V_short, I_short):
    """
    Thevenin equivalent from open-circuit and short-circuit measurements.
    V_oc     : open-circuit voltage (V)
    I_short  : short-circuit current (A)
    Returns (V_th, R_th).
    """
    R_th = V_oc / I_short
    V_th = V_oc
    return V_th, R_th
```

## Op-amp analysis

```python
def inverting_amplifier(Rin_ohm, Rf_ohm):
    """Closed-loop gain of inverting op-amp configuration."""
    return -Rf_ohm / Rin_ohm

def non_inverting_amplifier(R1_ohm, Rf_ohm):
    """Closed-loop gain of non-inverting op-amp configuration."""
    return 1 + Rf_ohm / R1_ohm

def instrumentation_amplifier_gain(R1, R2, Rgain):
    """
    Gain of a 3-op-amp INA.
    Standard formula: G = (1 + 2*R1/Rgain) * R2/R1 for matched resistors.
    """
    return (1 + 2 * R1 / Rgain) * (R2 / R1)
```

## Two-port parameters

```python
def z_to_s(Z, Z0=50):
    """Convert Z-parameters to S-parameters (2-port, real Z0)."""
    import numpy as np
    Z11, Z12, Z21, Z22 = Z[0,0], Z[0,1], Z[1,0], Z[1,1]
    denom = (Z11 + Z0) * (Z22 + Z0) - Z12 * Z21
    S11 = ((Z11 - Z0) * (Z22 + Z0) - Z12 * Z21) / denom
    S12 = 2 * Z12 * Z0 / denom
    S21 = 2 * Z21 * Z0 / denom
    S22 = ((Z11 + Z0) * (Z22 - Z0) - Z12 * Z21) / denom
    return np.array([[S11, S12], [S21, S22]])
```

## Netlist format conventions (SPICE)

```
* SPICE netlist syntax
* R<name> <node+> <node-> <value>
* C<name> <node+> <node-> <value>
* L<name> <node+> <node-> <value>
* V<name> <node+> <node-> <type> <params>
* .AC DEC 100 1 1MEG        ; frequency sweep
* .DC V1 0 5 0.01           ; DC sweep
* .TRAN 1n 1u               ; transient, step=1ns, end=1us
* .PROBE                     ; save all node voltages
* .END
```

## Common errors

| Symptom | Cause / fix |
|---|---|
| `SingularMatrix` in MNA | Floating node — every node must have a DC path to ground |
| PySpice segfault on `ac()` | ngspice not installed or PATH not set; install `ngspice` system package |
| lcapy symbolic expression too complex | Use `.simplify()` or `.subs({...})` to substitute numerical values |
| Filter instability in `filtfilt` | Filter order too high relative to data length; reduce order or increase data length |
