# GUM methodology

The *Guide to the Expression of Uncertainty in Measurement* (JCGM 100:2008, "the GUM")
and its Supplement 1 (JCGM 101:2008, the Monte Carlo method) define how an uncertainty
is evaluated, combined, and reported. This file covers the parts that decide whether a
number is defensible.

## Vocabulary that has to stay straight

| Term | Symbol | Meaning |
| --- | --- | --- |
| Measurand | Y | the quantity intended to be measured |
| Estimate | y | the value obtained for it |
| Standard uncertainty | u(x) | uncertainty of an input, expressed as a standard deviation |
| Combined standard uncertainty | u_c(y) | standard uncertainty of the result |
| Expanded uncertainty | U | k * u_c(y) |
| Coverage factor | k | multiplier chosen for a stated coverage probability |
| Coverage probability | p | probability that the interval contains the measurand |

"Error" and "uncertainty" are not synonyms: error is measured value minus a reference
value; uncertainty characterizes dispersion of values attributed to the measurand.
Accuracy is qualitative. Precision can be quantified by a standard deviation, variance,
or coefficient of variation under specified conditions (VIM 2.15).

## Type A and Type B are methods, not qualities

The distinction is only about *how the uncertainty was evaluated*. Neither is more
reliable than the other, and both produce a standard uncertainty on the same footing.

**Type A** — evaluated from a statistical analysis of repeated observations.

For n independent readings with experimental standard deviation s(q):

```text
u(q_bar) = s(q) / sqrt(n)          degrees of freedom: nu = n - 1
```

The standard uncertainty of the *mean* is what enters the budget when the reported
value is a mean. Using s(q) itself overstates it by sqrt(n); using `numpy.std` without
`ddof=1` understates s(q) itself. Both mistakes are common and neither is visible in
the output.

Pool repeatability only when a common variance model is defensible; the same instrument
does not rule out drift, dependence, or different between-run variation.

**Type B** — evaluated by any other means: a calibration certificate, a manufacturer's
specification, a handbook value, a previous measurement, or documented judgement.

The stated quantity is converted to a standard uncertainty by dividing by a factor that
depends on what the statement means:

| What the source states | Assumed density | Divisor | u |
| --- | --- | --- | --- |
| Expanded uncertainty U with stated factor k | use the source model; not necessarily normal | k | U / k |
| Symmetric 95% interval justified by a large-sample normal model | normal | 1.96 | half-width / 1.96 |
| A standard uncertainty | any assigned density with this SD | 1 | as stated |
| Limits ±a, any value equally likely | rectangular | sqrt(3) | a / sqrt(3) |
| Limits ±a, centre far more likely | triangular | sqrt(6) | a / sqrt(6) |
| Limits ±a, extremes more likely (sinusoidal drift, cyclic error) | arcsine | sqrt(2) | a / sqrt(2) |

A 95% label alone does not identify a divisor: recover the source method, degrees of
freedom, asymmetry, and whether the interval is a confidence, coverage, or prediction
interval. Rectangular is a common model when a specification gives limits and says nothing about the
distribution inside them. Digital resolution of one least significant digit d gives
half-width a = d/2, so u = d / (2 sqrt(3)).

The most frequent Type B error is treating a certificate's expanded uncertainty as a
standard uncertainty: it silently doubles the reported interval.

## Law of propagation of uncertainty

For a model Y = f(X_1, ..., X_N) with uncorrelated inputs (JCGM 100:2008 equation 10):

```text
u_c(y)^2 = sum_i ( df/dx_i )^2 * u(x_i)^2
```

with correlated inputs (equation 13):

```text
u_c(y)^2 = sum_i ( df/dx_i )^2 u(x_i)^2
         + 2 * sum_i sum_{j>i} (df/dx_i)(df/dx_j) u(x_i) u(x_j) r(x_i, x_j)
```

The partial derivatives are the **sensitivity coefficients** c_i. They carry units, and
`c_i * u(x_i)` is the contribution of that input expressed in the units of the result.
Comparing contributions, not raw uncertainties, is what tells you where to spend effort.

Correlation is not exotic. It appears whenever two inputs were calibrated against the
same standard, corrected with the same reference value, measured with the same
instrument, or derived from a common fit. The sign of the covariance contribution is `c_i*c_j*r_ij`, not the sign of `r_ij`
alone. Positive correlation increases uncertainty in a sum and can reduce it in a
difference; negative correlation has the reverse effect. In a difference of two similar quantities
measured the same way, the correlation is the whole point — it is what makes the
difference more precise than either term.

## Degrees of freedom and the coverage factor

k = 2 gives about 95% coverage for an approximately normal output with sufficiently
well-determined standard uncertainty. Large degrees of freedom alone do not make an
output normal. The Welch-Satterthwaite formula (JCGM 100:2008 G.2b)
gives them:

```text
nu_eff = u_c(y)^4 / sum_i ( (c_i u(x_i))^4 / nu_i )
```

Assigning infinite degrees of freedom to Type B components assumes their uncertainty
evaluations are sufficiently reliable. This is not automatic: GUM G.4.2 allows finite
values based on the uncertainty of the uncertainty. Infinite-dof terms drop out of the denominator. A single Type A component
from a handful of readings can pull nu_eff low enough that k rises well above 2:

| nu_eff | k for p = 95% |
| --- | --- |
| 2 | 4.30 |
| 5 | 2.57 |
| 10 | 2.23 |
| 20 | 2.09 |
| 50 | 2.01 |
| infinite | 1.96 |

If the dominant component came from five readings, reporting k = 2 understates the
interval by about a quarter. The formula assumes uncorrelated inputs; with correlation
the independent-input formula must not be used without a justified extension or
reformulation in terms of independent sources.

## When the GUM framework is not applicable

The framework linearizes f about the estimates. That is fine when the model is close to
linear across the input uncertainties, and wrong when it is not. Specifically, it
breaks down when:

- the model is significantly nonlinear over ±2u of an input — squares, reciprocals,
  ratios of comparable quantities, exponentials;
- a single non-normal component dominates, so the output is not approximately normal
  and k from a t-distribution does not deliver the claimed coverage;
- the output distribution is asymmetric, which the symmetric interval y ± U cannot
  represent;
- an input's relative uncertainty is large (above roughly 20-30%), where the second-order
  terms the expansion drops are no longer negligible;
- the model has a bound the interval crosses — a variance, a concentration, or a
  squared quantity whose GUM interval extends below zero.

## Monte Carlo propagation (JCGM 101:2008)

The supplement propagates the input distributions rather than their standard
deviations. The procedure is:

1. assign a probability density to each input, not merely a standard uncertainty;
2. draw M samples from the joint density, respecting any correlation;
3. evaluate the model for each draw;
4. take the mean as the estimate and the standard deviation as u_c;
5. take a coverage interval from the sorted output.

Two intervals are defined and they differ for an asymmetric output. The
**probabilistically symmetric** interval cuts (1-p)/2 from each tail. The **shortest**
interval is the narrowest one containing the fraction p; it can be useful for skewed unimodal outputs. State which interval is used. Equal-tail
and shortest intervals need not agree for symmetric multimodal distributions, and a
shortest interval need not be unique. A single interval can obscure separated modes.

M = 10^6 is the usual starting point for a 95% interval; JCGM 101 also defines an
adaptive procedure that keeps drawing until the results are stable to within the
numerical tolerance below. A fixed trial count does not guarantee endpoint accuracy; assess stabilization of the
mean, SD, and endpoints against the requested numerical tolerance.

## Comparing intervals without overstating validation

JCGM 101 clause 8 is the reason to run both methods rather than choosing one. Write u(y)
from the stabilized Monte Carlo result to n_dig significant digits (1 or 2) as c × 10^L. The numerical
tolerance is half of that last digit:

```text
delta = 0.5 * 10^L
```

Compare the endpoints of the two coverage intervals:

```text
d_low  = | (y - U)      - y_low_MC  |
d_high = | (y + U)      - y_high_MC |
```

With Monte Carlo numerically stabilized to delta/5 (clause 8.2), endpoint agreement
supports the GUM interval for this model, PDF assignment, probability, and interval
type. Disagreement can reflect nonlinearity or a poor output-distribution approximation.
It does not by itself establish which measurement model or input PDFs are appropriate.

`scripts/propagate_uncertainty.py` runs a fixed number of trials and reports only an
endpoint-agreement diagnostic; `gum_framework_validated` is null. It does not implement
the adaptive stabilization procedure. Finite dof alter the GUM factor but not the MC
input PDFs, so their difference may reflect different distributional assumptions.
Neither numerical agreement nor propagation mechanics proves metrological traceability,
empirical coverage, or correctness of the measurement model. Two useful examples:

**Rectangular inputs, linear model.** A model dominated by rectangular contributions
can fail interval agreement even though it is perfectly linear: the true output distribution is
closer to trapezoidal than normal, and k = 1.96 over-covers. The GUM value and u_c are
right; the interval is too wide.

**Nonlinear model.** For y = x^2 with x = 1.0 ± 0.5, the framework gives y = 1.0,
u_c = 1.0, and a 95% interval of [-0.96, 2.96] — an interval that is partly negative
for a squared quantity. Monte Carlo gives a mean of 1.25, u_c = 1.06, and a shortest
95% interval of [0, 3.32]. The GUM interval includes values the model cannot produce.

## Order of operations

1. Write the measurement model explicitly, including every correction, even those whose
   value is zero. A correction with an estimated value of zero still has an uncertainty,
   and leaving it out of the model leaves its uncertainty out of the budget.
2. Assign each input an estimate, a standard uncertainty, a distribution, and degrees of
   freedom.
3. Identify correlations before combining anything.
4. Compute sensitivity coefficients and the budget.
5. Combine, and check the linearization against Monte Carlo.
6. Choose k from nu_eff, not by habit.
7. Round the uncertainty first, then the value (see `reporting-rules.md`).

## Recurring defects

- Reporting a standard deviation of readings as the uncertainty of their mean.
- Dividing a certificate's expanded uncertainty by nothing, or by 2 when the certificate
  states a different k.
- Omitting a correction from the model because its value is negligible, thereby omitting
  its uncertainty too.
- Combining relative and absolute uncertainties without converting.
- Treating resolution and repeatability as independent when the resolution is what
  limits the repeatability — double counting.
- Quoting k = 2 with an effective degrees of freedom below 10.
- Applying the framework to a strongly nonlinear model and never checking.
- Propagating uncertainty through a fitted model without using the fit's covariance
  matrix, which discards the correlation between the fitted parameters.

## Current primary guidance

Reviewed 2026-10-01: [BIPM JCGM publications](https://www.bipm.org/en/committees/jc/jcgm/publications),
[JCGM 100](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf),
[JCGM 101](https://www.bipm.org/documents/20126/2071204/JCGM_101_2008_E.pdf),
and [VIM precision](https://jcgm.bipm.org/vim/en/2.15.html).
