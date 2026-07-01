---
name: electromagnetics
description: >
  Electromagnetics and RF engineering workflows: transmission line analysis,
  S-parameter characterization with scikit-rf, antenna design fundamentals,
  field simulation with MEEP (FDTD), and microwave network analysis. Load
  this skill for antenna design, transmission line problems, microwave circuits,
  RF component characterization, or electromagnetic field simulation tasks.
license: Apache-2.0
category: electrical-engineering
metadata:
  third_party:
    - kind: library
      name: scikit-rf
      license: BSD-3-Clause
      info_url: https://scikit-rf.readthedocs.io/
    - kind: library
      name: meep
      license: GPL-2.0
      info_url: https://meep.readthedocs.io/
---

# Electromagnetics

## Transmission line analysis with scikit-rf

```python
import skrf as rf
import numpy as np

# Load a Touchstone S-parameter file (.s2p)
ntw = rf.Network("device.s2p")

# Basic properties
print(f"Frequency range: {ntw.f[0]/1e9:.2f} - {ntw.f[-1]/1e9:.2f} GHz")
print(f"S11 at {ntw.f[50]/1e9:.1f} GHz: {ntw.s[50, 0, 0]:.4f}")

# Return loss (dB) and insertion loss
RL = ntw.s11.s_db        # return loss at port 1
IL = ntw.s21.s_db        # insertion loss (forward gain if amplifier)

# Plot S-parameters
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ntw.plot_s_db(m=0, n=0, ax=ax, label="S11")
ntw.plot_s_db(m=1, n=0, ax=ax, label="S21")
ax.set_ylim(-40, 5)
fig.savefig("s_params.png", dpi=150)
```

### Transmission line calculations

```python
class TransmissionLine:
    """Lossless transmission line analysis."""
    def __init__(self, Z0, v_phase, length):
        self.Z0 = Z0           # characteristic impedance (Ohm)
        self.vp = v_phase      # phase velocity (m/s), e.g. 0.66*3e8 for coax
        self.l  = length       # length (m)

    def beta(self, f):
        return 2 * np.pi * f / self.vp   # phase constant (rad/m)

    def input_impedance(self, ZL, f):
        """Input impedance for a terminated transmission line."""
        b = self.beta(f)
        j = 1j
        bl = b * self.l
        Zin = self.Z0 * (ZL + j*self.Z0*np.tan(bl)) / (self.Z0 + j*ZL*np.tan(bl))
        return Zin

    def reflection_coefficient(self, ZL):
        """Voltage reflection coefficient at load."""
        return (ZL - self.Z0) / (ZL + self.Z0)

    def vswr(self, ZL):
        """Voltage Standing Wave Ratio."""
        Gamma = abs(self.reflection_coefficient(ZL))
        return (1 + Gamma) / (1 - Gamma) if Gamma < 1 else float("inf")

# Example: 50-Ohm coax, 0.15 m, f = 2.4 GHz
tl = TransmissionLine(Z0=50, v_phase=0.66*3e8, length=0.15)
ZL = 75 + 25j   # load impedance
Zin = tl.input_impedance(ZL, f=2.4e9)
print(f"Zin = {Zin.real:.2f} + {Zin.imag:.2f}j  Ohm")
print(f"VSWR = {tl.vswr(ZL):.2f}")
```

## Antenna fundamentals

```python
LAMBDA_DICT = {f: 3e8/f for f in [433e6, 868e6, 2.4e9, 5.8e9, 24e9]}

def dipole_feedpoint(f_hz, wire_radius=0.001):
    """
    Approximate feedpoint impedance of a half-wave dipole.
    Returns (R_rad + R_loss, X) in Ohm (simplified, free space).
    """
    lam = 3e8 / f_hz
    # Half-wave dipole in free space: R ~ 73 Ohm, X ~ 42 Ohm (slightly long)
    # Resonant (slightly shorter): X ~ 0
    return 73.1, 42.5   # approximate, use NEC2 for accurate values

def isotropic_gain_dbi_to_dbd(dBi):
    """Convert gain from dBi to dBd (relative to half-wave dipole, 2.15 dB)."""
    return dBi - 2.15

def effective_aperture(G_linear, wavelength):
    """Effective aperture Ae = G * lambda^2 / (4*pi) in m^2."""
    return G_linear * wavelength**2 / (4 * np.pi)

def friis_received_power(P_tx_W, G_tx, G_rx, f_hz, d_m):
    """
    Friis transmission equation: received power in free space.
    Returns P_rx (W).
    """
    lam = 3e8 / f_hz
    return P_tx_W * G_tx * G_rx * (lam / (4 * np.pi * d_m))**2

# Link budget example
P_rx = friis_received_power(P_tx_W=0.1, G_tx=10, G_rx=2, f_hz=2.4e9, d_m=100)
print(f"P_rx = {10*np.log10(P_rx/1e-3):.1f} dBm")
```

## MEEP FDTD simulation (2-D example)

```python
import meep as mp

# 2-D waveguide simulation
cell = mp.Vector3(16, 8, 0)
geometry = [mp.Block(mp.Vector3(mp.inf, 1, mp.inf),
                     center=mp.Vector3(),
                     material=mp.Medium(epsilon=12))]

sources = [mp.Source(mp.GaussianSource(frequency=0.15, fwidth=0.1),
                     component=mp.Ez,
                     center=mp.Vector3(-7, 0))]

pml_layers = [mp.PML(1.0)]
resolution = 10

sim = mp.Simulation(cell_size=cell, boundary_layers=pml_layers,
                    geometry=geometry, sources=sources,
                    resolution=resolution)

# Flux monitor for transmission
f_trans = sim.add_flux(0.15, 0.1, 50,
                        mp.FluxRegion(center=mp.Vector3(6, 0),
                                      size=mp.Vector3(0, 2)))

sim.run(until=200)
trans_flux = mp.get_fluxes(f_trans)
print("Transmission flux:", trans_flux)
```

## Impedance matching: L-network

```python
def l_network_match(Rs, Xs, RL, XL, f_hz):
    """
    L-network impedance match from source (Rs+jXs) to load (RL+jXL).
    Returns two solutions (jX_series, jX_shunt) as lumped element values.
    Positive = inductor, negative = capacitor.
    """
    omega = 2 * np.pi * f_hz
    Q = np.sqrt(max(Rs, RL) / min(Rs, RL) - 1)

    def reactance_to_element(X):
        if X > 0:
            return f"L = {X/omega*1e9:.2f} nH"
        else:
            return f"C = {-1/(omega*X)*1e12:.2f} pF"

    if Rs > RL:
        Xs_net = Q * RL
        Xp_net = -(Rs / Q)
    else:
        Xp_net = Q * Rs
        Xs_net = -(RL / Q)

    return (reactance_to_element(Xs_net - Xs),
            reactance_to_element(Xp_net - XL))
```

## EMC rules of thumb

- Wavelength at 1 GHz in free space: 30 cm. Any PCB trace longer than lambda/20 (1.5 cm) can radiate.
- Ground plane return current follows the path of least inductance at high frequency (directly below the signal trace).
- Common-mode current on cables drives far-field emissions; ferrite beads reduce common-mode.
- Rise time (10-90%) bandwidth: BW_Hz ~ 0.35 / t_rise_s.
- Skin depth in copper at f: delta = 66.1 / sqrt(f_Hz) nm (approximately 2 um at 1 GHz).

## Reporting

For every EM/RF analysis, report:
1. Frequency range and operating frequency.
2. Characteristic impedance and matching network values with topology.
3. S-parameters: |S11| dB (return loss), |S21| dB (insertion/transmission) at key frequencies.
4. VSWR and reflection coefficient magnitude at critical interfaces.
5. For FDTD: cell size relative to wavelength (must be < lambda/10), PML thickness, run time (> 3x decay time).
6. Standard or specification against which performance is evaluated (e.g. IEEE 802.11, FCC Part 15).
