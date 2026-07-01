---
name: materials-characterization
description: >
  Materials characterization workflows: XRD phase identification, SEM/TEM
  image analysis, phase diagram interpretation, and crystallographic analysis
  using pymatgen and diffpy. Covers Rietveld refinement setup, electron
  microscopy analysis, and Materials Project data retrieval. Load this skill
  for materials structure determination, phase analysis, or microstructure
  characterization tasks.
license: Apache-2.0
category: engineering-science
metadata:
  third_party:
    - kind: service
      name: Materials Project
      provider: Lawrence Berkeley National Laboratory
      info_url: https://materialsproject.org/
      privacy_url: https://materialsproject.org/terms
    - kind: library
      name: pymatgen
      license: MIT
      info_url: https://pymatgen.org/
    - kind: library
      name: diffpy.CMI
      license: BSD-3-Clause
      info_url: https://www.diffpy.org/
---

# Materials Characterization

## XRD analysis with pymatgen

```python
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pymatgen.core import Structure
from pymatgen.ext.matproj import MPRester

# Retrieve structure from Materials Project API
def get_mp_structure(formula, api_key=None):
    """
    Retrieve the most stable structure from the Materials Project.
    api_key: set via MP_API_KEY environment variable or pass directly.
    """
    import os
    key = api_key or os.environ.get("MP_API_KEY")
    if not key:
        raise EnvironmentError("Set MP_API_KEY environment variable")
    with MPRester(key) as mpr:
        entries = mpr.get_entries(formula, inc_structure=True)
        # Return lowest-energy entry
        entries.sort(key=lambda e: e.energy_per_atom)
        return entries[0].structure

# Simulate XRD pattern
def simulate_xrd(structure, wavelength="CuKa", two_theta_range=(10, 80)):
    """
    Simulate powder XRD pattern.
    Returns (two_theta, intensities, hkl_list).
    """
    calc = XRDCalculator(wavelength=wavelength)
    pattern = calc.get_pattern(structure, two_theta_range=two_theta_range)
    return pattern.x, pattern.y, pattern.hkls

# Example (requires MP_API_KEY)
# struct = get_mp_structure("Fe2O3")
# two_theta, intensity, hkl = simulate_xrd(struct)
```

### Peak identification from measured data

```python
import numpy as np
from scipy.signal import find_peaks
from scipy.optimize import curve_fit

def find_xrd_peaks(two_theta, intensity, min_height=0.05, prominence=0.03):
    """
    Identify peak positions in a measured XRD pattern.
    min_height  : fraction of maximum intensity
    prominence  : minimum prominence fraction of maximum
    Returns (peak_positions_deg, peak_intensities).
    """
    I_max = intensity.max()
    peaks, props = find_peaks(intensity,
                               height=min_height * I_max,
                               prominence=prominence * I_max,
                               width=2)
    return two_theta[peaks], intensity[peaks]

def pseudo_voigt(x, x0, FWHM, eta, amplitude):
    """Pseudo-Voigt peak profile (mix of Gaussian and Lorentzian)."""
    sigma = FWHM / (2 * np.sqrt(2 * np.log(2)))
    G = np.exp(-0.5 * ((x - x0)/sigma)**2)
    L = 1 / (1 + ((x - x0)/(FWHM/2))**2)
    return amplitude * (eta * L + (1 - eta) * G)

def fit_xrd_peak(two_theta, intensity, peak_pos_guess, window=2.0):
    """
    Fit a single XRD peak with a pseudo-Voigt profile.
    Returns fitted (center_deg, FWHM_deg, intensity_max).
    """
    mask = np.abs(two_theta - peak_pos_guess) <= window
    x_win, y_win = two_theta[mask], intensity[mask]
    p0 = [peak_pos_guess, 0.3, 0.5, y_win.max()]
    try:
        popt, _ = curve_fit(pseudo_voigt, x_win, y_win, p0=p0,
                             bounds=([peak_pos_guess-1, 0.01, 0, 0],
                                     [peak_pos_guess+1, 5.0, 1, np.inf]))
        return popt[0], popt[1], popt[3]   # center, FWHM, amplitude
    except Exception:
        return peak_pos_guess, 0.3, y_win.max()
```

### Scherrer crystallite size

```python
def scherrer_size(FWHM_deg, two_theta_deg, wavelength_A=1.5406, K=0.94):
    """
    Scherrer equation for crystallite size.
    FWHM_deg     : FWHM of the diffraction peak (degrees 2-theta)
    two_theta_deg: peak position (degrees 2-theta)
    wavelength_A : X-ray wavelength in Angstroms (Cu K-alpha = 1.5406 A)
    K            : Scherrer constant (0.94 for spherical crystallites)
    Returns crystallite size in nm.
    """
    beta = np.radians(FWHM_deg)
    theta = np.radians(two_theta_deg / 2)
    return (K * wavelength_A) / (beta * np.cos(theta)) / 10   # A -> nm
```

## Phase diagram interpretation with pymatgen

```python
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDPlotter

def plot_phase_diagram(entries):
    """
    Plot a phase diagram from a list of computed entries.
    entries : list of pymatgen ComputedEntry objects from MP.
    """
    pd = PhaseDiagram(entries)
    plotter = PDPlotter(pd, show_unstable=True)
    # Returns a matplotlib figure
    return plotter.get_plot(label_unstable=False)

# Example with Materials Project data:
# with MPRester(key) as mpr:
#     entries = mpr.get_entries_in_chemsys(["Fe", "O"])
# pd_fig = plot_phase_diagram(entries)
```

## SEM/TEM image analysis

```python
from skimage import io, filters, measure, morphology
import numpy as np

def analyze_sem_grains(image_path, pixel_size_um=0.1, threshold_method="otsu"):
    """
    Segment and measure grains in a grayscale SEM micrograph.
    pixel_size_um : physical size of one pixel in micrometers
    Returns DataFrame with grain area, perimeter, equivalent diameter.
    """
    import pandas as pd
    img = io.imread(image_path, as_gray=True)

    # Denoise and threshold
    img_smooth = filters.gaussian(img, sigma=2)
    if threshold_method == "otsu":
        thresh = filters.threshold_otsu(img_smooth)
    else:
        thresh = filters.threshold_local(img_smooth, block_size=51)

    binary = img_smooth > thresh
    # Remove small objects and holes
    binary = morphology.remove_small_objects(binary, min_size=50)
    binary = morphology.remove_small_holes(binary, area_threshold=200)

    # Label and measure regions
    labeled = measure.label(binary)
    props = measure.regionprops_table(
        labeled, img,
        properties=["area", "perimeter", "equivalent_diameter",
                     "eccentricity", "mean_intensity"]
    )
    df = pd.DataFrame(props)
    df["area_um2"] = df["area"] * pixel_size_um**2
    df["diameter_um"] = df["equivalent_diameter"] * pixel_size_um
    return df

def grain_size_statistics(grain_df):
    """Compute ASTM grain size number G and statistics."""
    N = len(grain_df)
    mean_area = grain_df["area_um2"].mean()
    # ASTM E112: G = -6.6439 * log10(mean_area) + 16.02  (area in mm^2)
    mean_area_mm2 = mean_area * 1e-6
    G = -6.6439 * np.log10(mean_area_mm2) + 16.02 if mean_area_mm2 > 0 else None
    return {
        "count": N,
        "mean_diameter_um": grain_df["diameter_um"].mean(),
        "median_diameter_um": grain_df["diameter_um"].median(),
        "std_diameter_um": grain_df["diameter_um"].std(),
        "ASTM_grain_size_G": G
    }
```

## EDS / elemental analysis

```python
def parse_eds_spectrum(energies_keV, counts, elements=None):
    """
    Identify element peaks in an EDS spectrum.
    energies_keV : array of photon energy bins (keV)
    counts       : array of counts per bin
    elements     : list of element symbols to check; None = common elements
    Returns list of (element, line, energy_keV, counts_peak).
    """
    # Standard characteristic X-ray lines (K-alpha)
    K_ALPHA = {
        "C": 0.277, "N": 0.392, "O": 0.525, "Al": 1.487, "Si": 1.740,
        "Ti": 4.511, "Cr": 5.415, "Fe": 6.404, "Ni": 7.472, "Cu": 8.048,
        "Zn": 8.639, "Mo": 17.44, "Ag": 22.16, "Au": 9.713
    }
    if elements:
        check = {el: K_ALPHA[el] for el in elements if el in K_ALPHA}
    else:
        check = K_ALPHA

    found = []
    for el, E in check.items():
        idx = np.argmin(np.abs(energies_keV - E))
        window = np.abs(energies_keV - E) < 0.1   # 100 eV window
        if window.any() and counts[window].max() > counts.mean() * 3:
            found.append((el, "Ka", E, counts[window].max()))

    return sorted(found, key=lambda x: x[3], reverse=True)
```

## Reporting

For every characterization result, report:
1. Instrument and measurement conditions (X-ray wavelength, voltage/current,
   detector type, sample preparation).
2. For XRD: identified phases, peak positions vs. reference (ICDD/COD card),
   crystallite size where applicable.
3. For SEM/TEM: magnification, scale bar, grain size distribution statistics,
   ASTM grain size number.
4. For EDS: elemental composition (wt% and at%) with detection limits noted.
5. Reference database or calculated pattern used for phase matching.
6. Uncertainties: counting statistics, instrument broadening, calibration.
