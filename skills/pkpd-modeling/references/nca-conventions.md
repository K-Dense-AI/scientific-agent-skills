# NCA conventions and reproducibility

## Define the estimand before integration

Record dose, analyte, matrix, actual times, concentration units, assay/LLOQ and dose history.
AUC(0-t), AUC(0-inf) after a single dose, and AUC(0-tau) at steady state are different quantities.
The helper integrates from the first retained sample and does not extrapolate to time zero.
For an IV bolus this omits early exposure if C0 was not sampled or independently estimated.

| Decision | Bundled implementation | Report |
| --- | --- | --- |
| Trapezoids | Linear, linear-up/log-down, or log for any positive unequal endpoints | Rule and zero/equal-endpoint fallback |
| BLQ | Global zero, half-LLOQ, or missing | Location-dependent preprocessing, if applied |
| Missing values | Blank concentration is treated as BLQ | Remove truly missing samples before analysis |
| Lambda_z | At least three positive non-BLQ post-Tmax points; negative slope | Selected times, count, adjusted R², span in half-lives |
| Tail | Observed and predicted Clast alternatives | Which AUCinf drove CL/F and Vz/F |
| Partial AUC | Interpolate only inside sampled bounds | Prespecified boundaries and interpolation rule |

The log-down AUC segment is `dt*(C1-C2)/log(C1/C2)`. Equal endpoints require the linear limit.
AUMC uses integration of t*C, not the trapezoidal rule on transformed log concentrations.
Sorting is explicit: NumPy's `trapezoid` integrates in the supplied order and does not sort.
[NumPy documentation](https://numpy.org/doc/stable/reference/generated/numpy.trapezoid.html).

## Terminal phase

Automatic selection begins with the last three eligible points and extends backwards only when
adjusted R² improves by more than 0.0001. This differs from Phoenix Best Fit, which favors a longer
window within its tolerance of the best score. Tmax exclusion here applies even to IV bolus.
Use a manual window when scientifically justified; it still needs three declining post-Tmax points.
A predicted Clast is evaluated at the last quantifiable time, even if the selected window ends earlier.
[Phoenix 8.4 guide](https://onlinehelp.certara.com/phoenix/8.4/responsive_html5_%21MasterPage%21/WinNonlin_Guide.pdf).

A good regression can reflect absorption-limited decline, distribution or assay artifacts rather
than elimination. Plot the fit. Screening flags (20% extrapolated AUC, adjusted R² below 0.8,
span below two half-lives) are not universal exclusion criteria. State any exclusion rule prospectively.

## Parameter identities and route

- `t_half=log(2)/lambda_z`; `AUCinf=AUClast+Clast/lambda_z`.
- Single-dose `CL=D/AUCinf` for IV, `CL/F=D/AUCinf` for extravascular input.
- `Vz=CL/lambda_z` differs from `Vss=CL*MRT`.
- IV infusion MRT needs correction for mean input time (duration/2 for constant infusion).
- Oral MRT contains mean absorption time; it cannot directly determine Vss.
- At demonstrated steady state, `CLss(/F)=D/AUCtau` and `Cavg=AUCtau/tau`.

With `--tau`, provide exactly one sampled interval including its boundaries. The helper withholds
single-dose AUCinf/CL/Vz/Vss and explicitly records the steady-state assumption. It does not test
whether the patient or simulated system has actually reached steady state. BLQ substitution and
unmeasured early exposure remain sensitivity analyses, not biological measurements.
