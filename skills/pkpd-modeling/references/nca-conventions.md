# Non-compartmental analysis: conventions that change the answer

NCA is arithmetic on a concentration-time curve. What makes two analyses of the same data disagree
is never the arithmetic — it is the four conventions below, which are frequently left unstated.

## 1. Which trapezoidal rule

| Rule | Segment AUC | When |
| --- | --- | --- |
| Linear | `(C1+C2)/2 * dt` | Rising phase; sparse data; regulatory default for some agencies on ascending segments |
| Linear-up / log-down | linear while rising, log while falling | The usual default for a drug with log-linear decline |
| Log-linear | `(C1-C2)/k`, `k = ln(C1/C2)/dt` | Whole curve; fails on any rising or flat segment |

Linear trapezoid **overestimates** AUC on a convex declining curve, because the chord lies above
the exponential. The error grows with the sampling interval, so a sparse late-phase schedule biases
AUC upward under the linear rule and the two rules can differ by several percent.

Under log-down, the AUMC segment is

```
AUMC = (t1*C1 - t2*C2)/k + (C1 - C2)/k^2      with k = ln(C1/C2)/(t2 - t1)
```

which is not what you get by applying the AUC substitution naively.

## 2. How lambda_z was selected

The bundled helper fits `ln C` on time over the last three quantifiable points, extends
the window backwards, and retains a longer window only when adjusted r-squared improves
by more than 0.0001. This differs from Phoenix Best Fit, which favors the longer window
when it is within 0.0001 of the maximum adjusted r-squared. Document which convention
was used when comparing software outputs.

- Neither plain nor adjusted r-squared is monotonic as observations are added. Inspect
  the terminal fit and its sampling window rather than relying on either statistic alone.
- Points at or before Tmax are never eligible. Including Tmax fits the tail of absorption, which
  biases lambda_z upward and therefore half-life, Vz and AUCinf downward.
- Trailing BLQ samples are excluded from the regression, not set to zero — a zero cannot be
  log-transformed and a half-LLOQ substitution in the tail flattens the slope.

Reportability criteria, all conventions rather than regulation, and all worth pre-specifying:

| Diagnostic | Usual threshold | What it means when it fails |
| --- | --- | --- |
| Points in the window | ≥ 3 | The slope is an interpolation between two points |
| Adjusted r-squared | ≥ 0.80 (sometimes 0.85) | The terminal phase is not log-linear, or is noise |
| Span ratio: window duration / t½ | ≥ 2 | The true terminal phase may not have been reached |
| % AUC extrapolated | ≤ 20% | AUCinf is driven by the fit, not by data |

A profile can pass all four and still be wrong if sampling stopped during a distribution phase: the
"terminal" slope is then the beta phase of a drug whose gamma phase was never observed, and Vz and
t½ are both underestimated. Only the sampling duration relative to the true terminal half-life
fixes this, and NCA cannot detect it.

## 3. What happened to BLQ values

| Rule | Effect |
| --- | --- |
| Set to zero | Standard for leading BLQ before the first quantifiable sample |
| LLOQ/2 | Common for embedded BLQ; biases AUC upward slightly and t½ downward |
| Treated as missing | Standard for trailing BLQ; avoids fabricating a tail |

The usual regulatory-acceptable combination is: leading BLQ = 0, embedded BLQ = 0 or LLOQ/2 with
the choice stated, trailing BLQ excluded. Whatever you choose, apply it identically to every
profile and to every treatment arm — a rule applied to the test formulation and not the reference
biases the ratio directly.

## 4. Observed or predicted Clast

```
AUCinf_obs  = AUClast + Clast_observed  / lambda_z
AUCinf_pred = AUClast + Clast_predicted / lambda_z     (Clast_predicted from the lambda_z fit)
```

They differ whenever the last observation sits off the fitted line, which is exactly when the last
observation is noisy. `_pred` is more stable; `_obs` is more common. Report which.

## Parameter definitions

| Parameter | Definition | Notes |
| --- | --- | --- |
| Cmax, Tmax | Highest observed concentration and its time | **Observed values, never interpolated.** Tmax is summarised as median and range, not mean and SD |
| AUClast | AUC to the last quantifiable concentration | The only exposure metric that involves no extrapolation |
| AUCinf | AUClast + Clast/lambda_z | |
| AUMCinf | AUMClast + tlast·Clast/λz + Clast/λz² | |
| MRT | AUMCinf/AUCinf | Subtract Tinf/2 for a zero-order infusion |
| CL or CL/F | Dose/AUCinf | Apparent (`/F`) for any extravascular route |
| Vz or Vz/F | Dose/(λz · AUCinf) | Terminal-phase volume; depends on λz and inherits its error |
| Vss | CL · MRT | **Intravenous only.** Vss from extravascular data is not defined, because MRT then includes mean absorption time |
| AUC(0-tau) | AUC over one dosing interval at steady state | The reportable exposure metric at steady state |
| Cavg | AUC(0-tau)/tau | |
| PTF% | 100·(Cmax − Cmin)/Cavg | Peak-trough fluctuation |
| Swing | (Cmax − Cmin)/Cmin | More sensitive than PTF to a low trough |
| Rac | AUC(0-tau),ss / AUC(0-tau),first dose | Observed accumulation; compare with 1/(1 − e^(−λz·tau)) |

**Vz versus Vss.** Vz is a terminal-phase parameter and is systematically larger than Vss for a
multi-compartment drug. They are not alternative estimates of the same thing, and a covariate model
built on one does not transfer to the other.

## Steady state

Do not compute AUCinf from a truncated steady-state profile. The `nca.py` extrapolation finding
fires on exactly this, because the tail beyond tau is not observed and the extrapolated area is a
fiction. Report AUC(0-tau).

Attainment of steady state should be demonstrated, not assumed — by trough concentrations across at
least three consecutive intervals showing no trend, not by counting half-lives, because the half
life you would count with is the one you are trying to estimate.

## Urinary data

- `Ae` — cumulative amount excreted unchanged; `fe = Ae(0-inf)/Dose`
- `CLr = Ae(0-t)/AUC(0-t)` over the **same** interval; mismatching the intervals is the standard error
- `CLnr = CL − CLr`

Incomplete collection biases `fe` and `CLr` downward and is not detectable from the data alone.

## Sparse sampling

With one or two samples per subject, per-subject NCA is not possible. The Bailer method and its
Nedelman-Jia extension estimate a mean AUC and its standard error across a batch design. Do not
average per-subject AUCs computed from single points; do not run the destructive-sampling data
through an individual NCA and summarise the result.

## Reporting

State, for every NCA: the trapezoidal rule; the BLQ rule at each position; the lambda_z selection
rule with the window and number of points per subject; whether AUCinf is observed- or
predicted-based; and the exclusion criteria applied, decided before unblinding. Summarise exposure
metrics as geometric mean with geometric CV%, and Tmax as median with range.
