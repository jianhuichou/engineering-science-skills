---
name: vibration-dynamics
description: >
  Vibration and structural dynamics workflows: natural frequency computation,
  mode shapes, FFT-based signal analysis, response spectrum, and random
  vibration. Uses scipy (signal, linalg), numpy, and matplotlib. Load this
  skill for modal analysis, vibration diagnostics, seismic response spectrum,
  rotating machinery, or NVH analysis tasks.
license: Apache-2.0
category: mechanical-engineering
---

# Vibration and Dynamics

## Single-degree-of-freedom (SDOF) system

```python
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

def sdof_ode(t, y, omega_n, zeta, F_func):
    """
    SDOF oscillator: x'' + 2*zeta*omega_n*x' + omega_n^2*x = F(t)/m
    State vector y = [x, xdot].
    """
    x, xdot = y
    xddot = F_func(t) - 2*zeta*omega_n*xdot - omega_n**2 * x
    return [xdot, xddot]

def sdof_free_response(m, k, c, x0, v0, t_end, dt=0.001):
    """Free vibration of a SDOF system."""
    omega_n = np.sqrt(k/m)
    zeta = c / (2 * m * omega_n)
    t_span = (0, t_end)
    t_eval = np.arange(0, t_end, dt)
    sol = solve_ivp(sdof_ode, t_span, [x0, v0],
                    t_eval=t_eval, args=(omega_n, zeta, lambda t: 0),
                    method="RK45", rtol=1e-6)
    return sol.t, sol.y[0]

# Example: 100 kg mass, 10 kN/m spring, 200 N-s/m damper
t, x = sdof_free_response(m=100, k=10e3, c=200, x0=0.01, v0=0, t_end=2)
omega_n = np.sqrt(10e3/100)
print(f"Natural frequency: {omega_n/(2*np.pi):.2f} Hz")
```

## Multi-DOF: eigenvalue problem

```python
from scipy.linalg import eigh

def modal_analysis(K, M):
    """
    Compute natural frequencies and mode shapes.
    K : stiffness matrix (n x n)
    M : mass matrix (n x n)
    Returns omega_n (rad/s) and mode_shapes (columns) sorted by frequency.
    """
    eigenvalues, eigenvectors = eigh(K, M)
    omega_n = np.sqrt(np.abs(eigenvalues))   # rad/s
    idx = np.argsort(omega_n)
    return omega_n[idx], eigenvectors[:, idx]

# Example: 3-DOF shear building
m_val = 1000   # kg per floor
k_val = 5e5    # N/m per story
n = 3

M = np.diag([m_val] * n)
K = np.zeros((n, n))
for i in range(n):
    K[i, i] += k_val
    if i > 0:
        K[i, i]   += k_val
        K[i, i-1] -= k_val
        K[i-1, i] -= k_val

omega_n, modes = modal_analysis(K, M)
freqs_hz = omega_n / (2 * np.pi)
print("Natural frequencies (Hz):", freqs_hz.round(3))
```

## FFT-based frequency analysis

```python
def frequency_spectrum(signal, dt):
    """
    Compute single-sided amplitude spectrum.
    signal : 1-D array of measured values
    dt     : time step (s)
    Returns (frequencies Hz, amplitudes).
    """
    n = len(signal)
    fft = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(n, d=dt)
    amplitudes = 2 * np.abs(fft) / n
    amplitudes[0] /= 2   # DC component not doubled
    return freqs, amplitudes

def peak_frequencies(freqs, amplitudes, n_peaks=5, min_freq=1.0):
    """Return the n_peaks dominant frequencies above min_freq Hz."""
    from scipy.signal import find_peaks
    mask = freqs >= min_freq
    idx, props = find_peaks(amplitudes[mask], height=amplitudes[mask].max()*0.05)
    actual_idx = np.where(mask)[0][idx]
    top = actual_idx[np.argsort(amplitudes[actual_idx])[-n_peaks:]]
    return freqs[top], amplitudes[top]
```

## Short-time Fourier transform (STFT) / spectrogram

```python
from scipy.signal import spectrogram

def compute_spectrogram(signal, fs, nperseg=256):
    """
    Compute spectrogram for time-varying frequency content.
    fs : sampling frequency (Hz)
    Returns (f Hz, t s, Sxx power spectral density).
    """
    f, t, Sxx = spectrogram(signal, fs=fs, nperseg=nperseg,
                             noverlap=nperseg//2, scaling="spectrum")
    return f, t, Sxx
```

## Response spectrum (seismic)

```python
def response_spectrum(accel_record, dt, damping_ratios=None, T_range=None):
    """
    Compute pseudo-acceleration response spectrum Sa(T) from a ground motion.
    accel_record : ground acceleration (m/s^2 or g)
    dt           : time step (s)
    damping_ratios : list of zeta values (default [0.02, 0.05, 0.10])
    T_range      : period array (s); default 0.01 to 4 s
    Returns dict {zeta: (T_array, Sa_array)}.
    """
    if damping_ratios is None:
        damping_ratios = [0.02, 0.05, 0.10]
    if T_range is None:
        T_range = np.logspace(-2, np.log10(4), 200)

    results = {}
    for zeta in damping_ratios:
        Sa = []
        for T in T_range:
            omega_n = 2 * np.pi / T
            sol = solve_ivp(
                lambda t, y: [
                    y[1],
                    -np.interp(t, np.arange(len(accel_record))*dt, accel_record)
                    - 2*zeta*omega_n*y[1] - omega_n**2*y[0]
                ],
                (0, len(accel_record)*dt), [0, 0],
                t_eval=np.arange(len(accel_record))*dt,
                method="RK45", rtol=1e-6, atol=1e-8
            )
            Sa.append(omega_n**2 * np.max(np.abs(sol.y[0])))
        results[zeta] = (T_range, np.array(Sa))
    return results
```

## Rotating machinery diagnostics

Key frequencies for fault identification:

```python
def rotating_machine_frequencies(rpm, n_blades=None, n_balls=None,
                                  pitch_dia=None, ball_dia=None, contact_angle_deg=0):
    """
    Compute characteristic frequencies for rotating machine fault diagnosis.
    All frequencies returned in Hz.
    """
    f_r = rpm / 60   # shaft rotation frequency

    freqs = {"shaft_1x": f_r, "shaft_2x": 2*f_r}

    if n_blades:
        freqs["blade_passing"] = f_r * n_blades

    if n_balls and pitch_dia and ball_dia:
        ca = np.radians(contact_angle_deg)
        BPFO = n_balls/2 * f_r * (1 - ball_dia/pitch_dia * np.cos(ca))
        BPFI = n_balls/2 * f_r * (1 + ball_dia/pitch_dia * np.cos(ca))
        BSF  = pitch_dia/(2*ball_dia) * f_r * (1 - (ball_dia/pitch_dia*np.cos(ca))**2)
        freqs.update({"BPFO": BPFO, "BPFI": BPFI, "BSF": BSF})

    return freqs
```

## Damping ratio estimation (half-power bandwidth)

```python
def half_power_bandwidth(freqs, amplitudes):
    """
    Estimate damping ratio from frequency response using half-power method.
    Returns zeta (dimensionless).
    """
    peak_idx = np.argmax(amplitudes)
    fn = freqs[peak_idx]
    half_power = amplitudes[peak_idx] / np.sqrt(2)
    # Find f1, f2 on either side of peak
    left  = np.where(amplitudes[:peak_idx] <= half_power)[0]
    right = np.where(amplitudes[peak_idx:] <= half_power)[0]
    if left.size == 0 or right.size == 0:
        return None
    f1 = freqs[left[-1]]
    f2 = freqs[peak_idx + right[0]]
    zeta = (f2 - f1) / (2 * fn)
    return zeta
```

## Reporting

For every vibration analysis, report:
1. System description (DOF count, mass/stiffness/damping values, units).
2. Natural frequencies and mode shapes for all significant modes.
3. Damping ratios and basis (measured, assumed, or code-specified).
4. Forcing function description and frequency range of interest.
5. Peak response values (displacement, velocity, acceleration) and location.
6. Resonance risk assessment: are any excitation frequencies within 10% of a
   natural frequency? If so, state the resonance margin and recommended action.
