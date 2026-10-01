# Structural PK models and identifiability

## Parameters and units

Clearance/volume parameterization is convenient for interpretation: CL and Q are volume/time,
V is volume, and ka is 1/time. Microconstants (CL/V, Q/V) and exponential coefficients can also
be valid estimation parameterizations; none guarantees identifiability. Physiological plausibility
and covariate relationships depend on the drug, population and estimand.

`_models.disposition()` constructs a linear mammillary rate matrix and obtains exponential
components by eigendecomposition. The library supports any number of peripheral compartments;
the individual fitting CLI offers one through three. Positive finite CL, volumes and Q are required.

For an IV dose D, the central concentration is `D*sum(coef_i*exp(lambda_i*t))`.
The infusion response convolves this with a finite constant input; oral first-order input adds ka
and F. At `ka=-lambda_i`, evaluate the removable limit `t*exp(lambda_i*t)` within the convolution.
The library includes that branch. Analytical checks include:

```
AUC_iv(0,inf) = D/CL
Vss = Vcentral + sum(Vperipheral)
MRT_iv_bolus = Vss/CL
AUC_ss(0,tau) = D/CL
```

Multicompartment accumulation depends on the metric. The terminal half-life alone does not give
the peak, trough or interval-AUC accumulation ratio. Closed-form metrics in the simulation CLI
are restricted to IV bolus; oral or infusion inputs require their actual input model.

## Oral and nonlinear models

Oral data alone generally identify apparent CL/F and V/F. For a one-compartment first-order model,
interchanging absorption and elimination rates with an adjusted apparent volume can reproduce the
same curve. A slow observed terminal phase can therefore reflect absorption. Do not interpret Vz/F
as an independently identified physiological volume without supporting absorption information.

The transit helper convolves a gamma-shaped input with disposition on a numerical grid. It uses
`lgamma` to avoid factorial overflow; this does not make the convolution exact. Check grid/horizon
sensitivity for narrow absorption distributions. An additional post-transit ka is not implemented
and is rejected. Lag and transit can both be justified in some models, but require data that identify
their distinct roles.

Michaelis-Menten elimination uses `Vmax*C/(Km+C)`: Vmax is amount/time, Km concentration.
At low C its approximate clearance is Vmax/Km. Superposition does not hold. Nonlinear dose
proportionality has other possible causes (bioavailability, binding, absorption, assay), so it does
not by itself identify a saturable elimination mechanism.

The ODE library splits at dose starts and infusion boundaries and checks solver success. Select
tolerances by sensitivity of the requested exposure/effect output, not by a solver-success flag.
[SciPy solve_ivp documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html).

## Fitting and model choice

`fit_compartmental.py` performs separate individual fits on log-positive parameters. Fixed observed
weights are supported. Prediction-dependent weights are rejected because the implemented WLS
objective lacks the variance-normalization term of their likelihood. Observed 1/y² weights can
strongly bias noisy low concentrations; justify the residual model.

Inspect dose/time accuracy, residual dependence, multiple starts, boundary estimates, sensitivity
rank and parameter profiles. Local Gauss-Newton covariance is not a profile likelihood; singular
information does not support finite uncertainty. AIC/BIC comparisons require identical records and
weight conventions. Extra-compartment parameters lie on boundaries under the simpler model, so the
nominal F comparison is exploratory. Residual runs do not uniquely diagnose the cause of misfit.
[SciPy least_squares documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html).

For NONMEM translation, choose and verify the ADVAN/TRANS combination in the installed vendor
manual, including compartment numbering, F, scaling and input. ADVAN16/17 address delay equations;
they are not interchangeable with ordinary ODE ADVANs. No NONMEM execution was performed here.
[ICON NONMEM platform](https://www.iconplc.com/solutions/technologies/nonmem).
