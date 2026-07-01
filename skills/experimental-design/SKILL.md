---
name: experimental-design
description: >
  Design of experiments (DOE), uncertainty quantification, and measurement
  calibration workflows. Covers factorial designs, response surface methods,
  Latin hypercube sampling, uncertainty propagation (Monte Carlo and GUM),
  and sensor calibration. Uses pyDOE2, scipy, numpy, and uncertainties.
  Load this skill for planning experiments, propagating measurement uncertainty,
  or analyzing calibration data.
license: Apache-2.0
category: engineering-science
metadata:
  third_party:
    - kind: library
      name: pyDOE2
      license: BSD-3-Clause
      info_url: https://github.com/clicumu/pyDOE2
    - kind: library
      name: uncertainties
      license: BSD-3-Clause
      info_url: https://pythonhosted.org/uncertainties/
---

# Experimental Design and Uncertainty

## Design of Experiments (DOE)

### Full factorial design

```python
from pyDOE2 import fullfact, ff2n, ccdesign, lhs
import numpy as np
import pandas as pd

def full_factorial(factors):
    """
    Generate a full factorial design.
    factors : dict {factor_name: [level_1, level_2, ...]}
    Returns DataFrame with all combinations.
    """
    levels = [len(v) for v in factors.values()]
    design = fullfact(levels)
    rows = []
    for run in design:
        row = {}
        for i, (name, values) in enumerate(factors.items()):
            row[name] = values[int(run[i])]
        rows.append(row)
    return pd.DataFrame(rows)

# Example: 2-level, 3-factor experiment
factors = {
    "Temperature_C": [20, 80],
    "Pressure_bar":  [1, 10],
    "Flow_Lpm":      [2, 8],
}
design = full_factorial(factors)
print(design.to_string(index=False))
```

### 2^k fractional factorial

```python
def fractional_factorial_2k(k, fraction=1):
    """
    2^(k-fraction) fractional factorial design (coded levels: -1/+1).
    k        : number of factors
    fraction : 2^fraction reduction (1 = half-fraction, 2 = quarter)
    Returns coded design matrix.
    """
    return ff2n(k - fraction)
```

### Central composite design (Response Surface)

```python
def central_composite(factor_names, alpha="rotatable", face="circumscribed"):
    """
    Generate a central composite design for response surface methodology.
    factor_names : list of factor names
    Returns DataFrame with coded (-1 to +1) and star (+-alpha) points.
    """
    k = len(factor_names)
    design_matrix = ccdesign(k, alpha=alpha, face=face)
    return pd.DataFrame(design_matrix, columns=factor_names)
```

### Latin Hypercube Sampling

```python
def latin_hypercube(factor_bounds, n_samples=50, criterion="centermaximin"):
    """
    Latin Hypercube Sampling for space-filling designs.
    factor_bounds : dict {name: (lo, hi)}
    Returns DataFrame with physical values.
    """
    k = len(factor_bounds)
    lhs_coded = lhs(k, samples=n_samples, criterion=criterion)   # [0,1] range
    df = pd.DataFrame(lhs_coded, columns=list(factor_bounds.keys()))
    for col, (lo, hi) in factor_bounds.items():
        df[col] = lo + df[col] * (hi - lo)
    return df
```

## Response surface regression

```python
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

def fit_response_surface(X_df, y, degree=2):
    """
    Fit a polynomial response surface model.
    X_df : DataFrame of factor values
    y    : response array
    Returns (model, poly_features, R^2, predicted_values).
    """
    poly = PolynomialFeatures(degree=degree, include_bias=True)
    X_poly = poly.fit_transform(X_df.values)
    model = LinearRegression().fit(X_poly, y)
    y_pred = model.predict(X_poly)
    R2 = r2_score(y, y_pred)
    return model, poly, R2, y_pred

def predict_response(model, poly, factor_dict):
    """Predict response at new factor levels."""
    X_new = np.array([[v for v in factor_dict.values()]])
    return model.predict(poly.transform(X_new))[0]
```

## Uncertainty propagation (GUM method)

```python
def uncertainty_gum(func, nominal_inputs, uncertainties, n_montecarlo=10000):
    """
    Propagate measurement uncertainty using GUM (Guide to Uncertainty in Measurement).
    Combines analytical partial derivatives with Monte Carlo verification.

    func            : callable, result = func(*inputs)
    nominal_inputs  : list of nominal input values
    uncertainties   : list of standard uncertainties (k=1) for each input
    n_montecarlo    : number of MC samples for validation
    Returns (nominal_result, combined_uncertainty_k1, mc_validation_dict).
    """
    from uncertainties import ufloat
    import numpy as np

    # Analytical propagation via uncertainties package
    u_inputs = [ufloat(val, unc) for val, unc in zip(nominal_inputs, uncertainties)]
    u_result = func(*u_inputs)
    nominal = u_result.nominal_value
    u_combined = u_result.std_dev

    # Monte Carlo verification
    mc_samples = np.column_stack([
        np.random.normal(val, unc, n_montecarlo)
        for val, unc in zip(nominal_inputs, uncertainties)
    ])
    mc_results = np.array([func(*row) for row in mc_samples])
    mc_dict = {
        "mean": mc_results.mean(),
        "std":  mc_results.std(),
        "p2_5": np.percentile(mc_results, 2.5),
        "p97_5": np.percentile(mc_results, 97.5),
    }
    return nominal, u_combined, mc_dict

# Example: density = mass / volume
# rho, u_rho, mc = uncertainty_gum(
#     func=lambda m, V: m / V,
#     nominal_inputs=[10.023, 0.00512],   # kg, m^3
#     uncertainties=[0.001, 0.00001]
# )
# print(f"rho = {rho:.3f} +/- {u_rho:.4f} kg/m^3 (k=1)")
```

## Calibration: linear least squares

```python
def linear_calibration(x_reference, y_measured, confint_level=0.95):
    """
    Fit a linear calibration curve y = a + b*x using OLS.
    Returns (a, b, uncertainty_a, uncertainty_b, R^2, residuals).
    """
    from scipy import stats
    slope, intercept, r_value, p_value, std_err = stats.linregress(x_reference, y_measured)
    n = len(x_reference)
    y_pred = intercept + slope * np.array(x_reference)
    residuals = np.array(y_measured) - y_pred
    s_res = np.sqrt(np.sum(residuals**2) / (n - 2))

    Sxx = np.sum((np.array(x_reference) - np.mean(x_reference))**2)
    se_slope = s_res / np.sqrt(Sxx)
    se_intercept = s_res * np.sqrt(np.sum(np.array(x_reference)**2) / (n * Sxx))

    t_crit = stats.t.ppf((1 + confint_level) / 2, df=n-2)
    return {
        "intercept": intercept, "slope": slope,
        "u_intercept": se_intercept * t_crit,
        "u_slope": se_slope * t_crit,
        "R2": r_value**2, "residuals": residuals,
        "confidence_level": confint_level
    }
```

## ANOVA for factor significance

```python
def one_way_anova(groups):
    """
    One-way ANOVA to test if factor levels produce significantly different responses.
    groups : dict {group_name: array_of_observations}
    Returns (F_statistic, p_value, interpretation).
    """
    from scipy.stats import f_oneway
    F, p = f_oneway(*groups.values())
    interp = "significant (reject H0 at 5%)" if p < 0.05 else "not significant (fail to reject H0)"
    return F, p, interp
```

## Reporting

For every experimental design and analysis, report:
1. Experimental objectives, response variables, and factor levels with units.
2. Design type, number of runs, and randomization strategy.
3. Regression model equation and coefficients with uncertainties.
4. R^2 and residual analysis (normality, homoscedasticity).
5. ANOVA table: source, SS, df, MS, F, p-value.
6. Uncertainty budget: each input variable, its standard uncertainty,
   sensitivity coefficient, and contribution to combined uncertainty.
7. Expanded uncertainty (k=2 for 95% coverage) in final reported values.
8. Reference: GUM:2008 (JCGM 100:2008) for uncertainty; ISO 5725 for accuracy.
