---
name: signal-processing
description: >
  Digital signal processing workflows: filtering, spectral analysis, FFT,
  spectrogram, window functions, resampling, noise analysis, and signal
  conditioning. Uses scipy.signal and numpy. Load this skill for data
  acquisition processing, sensor signal analysis, audio processing,
  vibration analysis, or communications signal tasks.
license: Apache-2.0
category: electrical-engineering
---

# Signal Processing

## Core workflow: load, condition, analyze, visualize

```python
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

# Simulate a noisy signal for examples below
fs = 10000   # Hz
t = np.linspace(0, 1, fs, endpoint=False)
x = (np.sin(2*np.pi*100*t) +
     0.5*np.sin(2*np.pi*300*t) +
     0.1*np.random.randn(fs))
```

## Filtering

```python
def bandpass_filter(data, f_low, f_high, fs, order=4):
    """Zero-phase Butterworth bandpass filter."""
    nyq = fs / 2
    b, a = signal.butter(order, [f_low/nyq, f_high/nyq], btype="band")
    return signal.filtfilt(b, a, data)

def notch_filter(data, f_notch, Q, fs):
    """Notch (band-stop) filter at f_notch Hz."""
    b, a = signal.iirnotch(f_notch / (fs/2), Q)
    return signal.filtfilt(b, a, data)

# Example: isolate 50-200 Hz component
x_filt = bandpass_filter(x, f_low=50, f_high=200, fs=fs, order=4)
```

## Spectral analysis

```python
def power_spectral_density(data, fs, window="hann", nperseg=None):
    """
    Welch's method PSD estimate.
    Returns (frequencies Hz, PSD in units^2/Hz).
    """
    if nperseg is None:
        nperseg = min(len(data), 1024)
    f, Pxx = signal.welch(data, fs=fs, window=window, nperseg=nperseg,
                           noverlap=nperseg//2, scaling="density")
    return f, Pxx

def rms_in_band(f, Pxx, f_low, f_high):
    """RMS level within a frequency band (from PSD)."""
    mask = (f >= f_low) & (f <= f_high)
    return np.sqrt(np.trapz(Pxx[mask], f[mask]))

f, Pxx = power_spectral_density(x, fs)
rms_100_200 = rms_in_band(f, Pxx, 100, 200)
print(f"RMS in 100-200 Hz band: {rms_100_200:.4f}")
```

## Short-time Fourier transform

```python
def stft_analysis(data, fs, window="hann", nperseg=256, overlap_fraction=0.5):
    """
    STFT for time-varying spectral content.
    Returns (f Hz, t s, Zxx complex spectrogram).
    """
    noverlap = int(nperseg * overlap_fraction)
    f, t_stft, Zxx = signal.stft(data, fs=fs, window=window,
                                   nperseg=nperseg, noverlap=noverlap)
    return f, t_stft, Zxx

def plot_spectrogram(f, t, Zxx, title="Spectrogram"):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.pcolormesh(t, f, 20*np.log10(np.abs(Zxx) + 1e-12),
                  shading="gouraud", cmap="inferno")
    ax.set_ylabel("Frequency (Hz)"); ax.set_xlabel("Time (s)")
    ax.set_title(title)
    fig.colorbar(ax.collections[0], ax=ax, label="dB")
    return fig
```

## Window functions

| Window | Main-lobe width | Side-lobe level | Use case |
|---|---|---|---|
| Rectangular | Narrowest | -13 dB | Short bursts, no leakage concern |
| Hann | Moderate | -31 dB | General spectral analysis |
| Hamming | Moderate | -41 dB | Speech processing |
| Blackman | Wide | -57 dB | High dynamic-range spectral analysis |
| Flat-top | Very wide | -93 dB | Amplitude-accurate calibration |
| Kaiser (beta=14) | Wide | -100+ dB | Filter design, custom sidelobes |

```python
from scipy.signal.windows import hann, blackman, flattop, kaiser
win = hann(M=1024)
```

## Resampling and interpolation

```python
def resample_signal(data, fs_original, fs_target):
    """
    Resample signal to a new sample rate using polyphase filtering.
    Returns resampled data and new time array.
    """
    from math import gcd
    g = gcd(int(fs_target), int(fs_original))
    up, down = int(fs_target)//g, int(fs_original)//g
    data_resampled = signal.resample_poly(data, up, down)
    t_new = np.arange(len(data_resampled)) / fs_target
    return data_resampled, t_new
```

## Noise floor and SNR

```python
def estimate_snr(data, fs, f_signal, bandwidth=10.0):
    """
    Estimate SNR (dB) from PSD.
    f_signal  : center frequency of signal (Hz)
    bandwidth : signal bandwidth (Hz)
    Noise estimated from the rest of the spectrum.
    """
    f, Pxx = power_spectral_density(data, fs)
    sig_mask  = np.abs(f - f_signal) <= bandwidth/2
    noise_mask = ~sig_mask & (f > 0)
    P_sig   = np.trapz(Pxx[sig_mask], f[sig_mask])
    P_noise = np.trapz(Pxx[noise_mask], f[noise_mask])
    snr_db = 10 * np.log10(P_sig / (P_noise + 1e-300))
    return snr_db

def thd(data, fs, f_fundamental, n_harmonics=5):
    """
    Total Harmonic Distortion (%).
    Computes ratio of harmonic power to fundamental power.
    """
    f, Pxx = power_spectral_density(data, fs, nperseg=len(data))
    def band_power(fc, bw=5):
        mask = np.abs(f - fc) <= bw
        return np.trapz(Pxx[mask], f[mask])
    P1 = band_power(f_fundamental)
    P_harm = sum(band_power(f_fundamental*(k+2)) for k in range(n_harmonics))
    return 100 * np.sqrt(P_harm / (P1 + 1e-300))
```

## Peak detection and event extraction

```python
from scipy.signal import find_peaks

def detect_peaks(data, fs, threshold_factor=3.0, min_distance_s=0.01):
    """
    Detect signal peaks above threshold_factor * RMS.
    Returns (peak_times_s, peak_amplitudes).
    """
    rms = np.sqrt(np.mean(data**2))
    min_distance_samples = int(min_distance_s * fs)
    peaks, props = find_peaks(np.abs(data),
                               height=threshold_factor * rms,
                               distance=min_distance_samples)
    times = peaks / fs
    return times, data[peaks]
```

## Digital filter design: Parks-McClellan (equiripple)

```python
def design_equiripple_lowpass(f_pass, f_stop, fs, ripple_db=1, atten_db=60):
    """
    Design an FIR equiripple lowpass filter using Parks-McClellan.
    Returns FIR coefficients h.
    """
    nyq = fs / 2
    # Estimate required order
    n = int(signal.kaiserord(atten_db, (f_stop - f_pass) / nyq)[0])
    n += n % 2   # ensure even order for Type I FIR
    h = signal.remez(n + 1, [0, f_pass/nyq, f_stop/nyq, 1],
                     [1, 0], weight=[1, 10**((atten_db - ripple_db)/20)])
    return h
```

## Reporting

For every signal processing analysis, report:
1. Signal source, sample rate, bit depth (if applicable), and record length.
2. Preprocessing applied (filtering, resampling, windowing) with parameter values.
3. Frequency resolution: df = fs / N_FFT.
4. Dominant frequency components with amplitude and phase.
5. RMS, peak, and SNR values in relevant frequency bands.
6. Figures: time trace, PSD (log-log or log-linear), and spectrogram when time-varying.
