# uncertainties recipes

Verified against uncertainties 3.2.3 with NumPy 2.5.1 and SciPy 1.18.0. The package
performs first-order (linear) propagation with analytic derivatives, tracking
correlations automatically through every operation. Everything it does is the GUM
uncertainty framework; it does not perform Monte Carlo propagation and does not check
whether linearization was appropriate.

## Variables and the correlation they carry

```python
from uncertainties import ufloat

x = ufloat(1.0, 0.1)
x - x                    # 0.0+/-0        the same variable, perfectly correlated
x - ufloat(1.0, 0.1)     # 0.00+/-0.14    two independent variables
```

That pair of lines is the whole design. A `ufloat` is an *identity*, not a number with
an attached error bar, and the difference of a variable with itself is exactly zero.
This is the correct answer, and it is why arithmetic on ufloats beats manual quadrature
in any expression where a quantity appears more than once.

The corollary is the most common defect:

```python
copy = ufloat(x.nominal_value, x.std_dev)   # a NEW, independent variable
x - copy                                    # 0.00+/-0.14, not 0
```

Rebuilding a variable from `.nominal_value` and `.std_dev` throws away every correlation
it carried. So does serializing to JSON and back, storing in a DataFrame column of
floats, or passing through any interface that speaks in pairs of numbers.
`scripts/audit_units.py` flags this construction as `UNC004`.

## Correlated inputs

```python
import numpy as np
from uncertainties import correlated_values, correlation_matrix, covariance_matrix

cov = np.array([[0.04, 0.012],
                [0.012, 0.09]])
a, b = correlated_values([1.0, 2.0], cov)

a + b                            # 3.0+/-0.4
correlation_matrix([a, b])[0][1] # 0.19999999999999987
```

`correlated_values` is how a fit's covariance matrix enters the calculation intact.
`correlation_matrix` returns a NumPy array; `covariance_matrix` returns a nested list —
index it as `[i][j]`, not `[i, j]`.

`correlated_values_norm` takes `[(value, std_dev), ...]` plus a *correlation* matrix
instead of a covariance matrix, which is usually what a paper reports.

## Functions

Ordinary `math` and `numpy` functions have no derivative rule for these objects and
fail, loudly on scalars and inside the ufunc loop on arrays:

```python
import math, numpy as np
from uncertainties import umath, unumpy

math.sqrt(a)   # TypeError: can't convert an affine function ... to float
np.sqrt(a)     # TypeError: loop of ufunc does not support argument 0 of type AffineScalarFunc
umath.sqrt(a)  # 1.00+/-0.10
```

`umath` mirrors `math`: sqrt, exp, log, log10, log1p, expm1, the trigonometric and
hyperbolic functions and their inverses, atan2, hypot, degrees, radians, fabs, erf.

For arrays, `unumpy` provides the wrapped versions plus constructors and accessors:

```python
arr = unumpy.uarray([1.0, 2.0], [0.1, 0.2])
unumpy.sqrt(arr)             # [1.0+/-0.05 1.4142135623730951+/-0.07071067811865475]
unumpy.nominal_values(arr)   # [1. 2.]
unumpy.std_devs(arr)         # [0.1 0.2]
np.mean(arr)                 # 1.50+/-0.11    -- works: object-array reduction
np.sqrt(arr)                 # TypeError      -- fails: ufunc loop
```

The split is worth internalizing: reductions written in terms of Python arithmetic
(`mean`, `sum`, `dot`) work on object arrays, while ufuncs do not. When in doubt use
`unumpy`.

## Formatting

The format spec extends the standard one. `u` counts significant digits *in the
uncertainty*, and the value is rounded to match:

```python
from uncertainties import ufloat
v = ufloat(12.3456, 0.0234)

f"{v:.2u}"    # 12.346+/-0.023
f"{v:.2uS}"   # 12.346(23)          concise notation
f"{v:.1uP}"   # 12.35±0.02          pretty Unicode
f"{v:.2uL}"   # 12.346 \pm 0.023    LaTeX
f"{ufloat(0.00012345, 0.0000023):.2ue}"   # (1.234+/-0.023)e-04
```

This handles the GUM rounding rule for you. `scripts/format_result.py` covers the cases
this does not: an expanded uncertainty with a stated k, the accompanying sentence, and
the warnings about reporting one digit when the leading digit is 1 or 2.

## Where the uncertainty came from

```python
result = a**2 + b
result.derivatives[a]        # 2.0 -- the sensitivity coefficient
result.error_components()    # {variable: contribution} for every input
```

`error_components` is the uncertainty budget, keyed by the original variables. Sorting
it descending tells you which input to improve.

## Fitted parameters

The covariance matrix from a fit is the correlation between parameters, and discarding
it is a routine error:

```python
import numpy as np
from scipy.optimize import curve_fit
from uncertainties import correlated_values

popt, pcov = curve_fit(model, x, y, sigma=sigma, absolute_sigma=True)
slope, intercept = correlated_values(popt, pcov)   # keeps the correlation
```

Taking `np.sqrt(np.diag(pcov))` and building independent ufloats discards it, and for a
straight-line fit the slope-intercept correlation is strongly negative — predictions
near the centroid of the data come out far too uncertain.

`absolute_sigma` decides what `pcov` means, and the default is not what most users
assume:

```python
popt, pcov = curve_fit(f, x, y, sigma=sigma, absolute_sigma=False)  # default
# pcov is rescaled by the reduced chi-square: parameter uncertainties absorb the
# goodness of fit. Relative sigma weights remain; this is not generally an unweighted fit.

popt, pcov = curve_fit(f, x, y, sigma=sigma, absolute_sigma=True)
# pcov reflects the standard uncertainties you supplied.
```

On one synthetic straight-line fit the two give parameter standard deviations of
`[0.0364, 0.2154]` and `[0.0477, 0.2820]` — a 31% difference, with no warning. Pass
`absolute_sigma=True` whenever `sigma` holds real standard uncertainties;
`scripts/audit_units.py` flags the omission as `UNC001`.

## Limits

- **First order only.** For a strongly nonlinear model the reported std_dev is the
  linearized one, and the package cannot tell you that. Cross-check with
  `scripts/propagate_uncertainty.py`, which runs Monte Carlo alongside.
- **No distribution.** A ufloat carries a standard deviation, not a shape. Rectangular
  and normal inputs with the same u are indistinguishable to it.
- **No degrees of freedom.** Coverage factors are your problem; use
  `scripts/uncertainty_budget.py`.
- **`float()` fails**, deliberately, on anything with an uncertainty. Comparison
  operators compare nominal values.
- **Object arrays are slow.** For large arrays, propagate analytically or by Monte Carlo
  rather than element-wise.
