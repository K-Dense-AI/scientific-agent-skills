# Reporting rules

A number without its uncertainty and without a statement of what that uncertainty means
cannot be checked, compared, or reused. This file covers what has to accompany a
reported result.

## Round the uncertainty first

JCGM 100:2008 7.2.6. The uncertainty is rounded to one or two significant digits, and
the value is then rounded to that same decimal place — never the other way round, and
never independently.

```text
12.34567 +/- 0.02345    ->    12.346 +/- 0.023
12.34567 +/- 0.1        ->    12.35  +/- 0.10        (two digits, since 1 leads)
1234     +/- 250        ->    1230   +/- 250
```

Two digits are the safe default. One digit is acceptable when the leading digit is 3 or
more; rounding 0.14 to 0.1 changes it by 29%, which is why a leading 1 or 2 should keep
two digits. `scripts/format_result.py` applies the rule and warns on that case.

Trailing zeros in the uncertainty are significant and must be kept: `0.10`, not `0.1`.

## Notations

| Notation | Example | Where it is used |
| --- | --- | --- |
| Plus-minus | 12.346 ± 0.023 mm | prose, tables |
| Concise / parenthetic | 12.346(23) mm | physics, CODATA, high-precision tables |
| Scientific | (9.1093837139 ± 0.0000000028)e-31 kg | very large or small values |
| Concise scientific | 9.1093837139(28)e-31 kg | constants |

In concise notation the digits in parentheses apply to the last digits of the quoted
value, so `12.346(23)` is 12.346 ± 0.023 and `1234(25)` is 1234 ± 25. When the
uncertainty's last significant digit falls left of the decimal point the notation is
ambiguous and the scientific form must be used instead.

## What has to be stated alongside

A bare `±` is ambiguous. Readers cannot tell a standard uncertainty from an expanded
one, a standard deviation from a standard error, or a 95% interval from a 68% one. State:

1. **Which quantity the number is** — combined standard uncertainty u_c, expanded
   uncertainty U, standard deviation of a sample, standard error of a mean, or a
   confidence interval.
2. **The coverage factor k**, when U is reported.
3. **The coverage probability** and how it was arrived at — from a normal assumption or
   from effective degrees of freedom.
4. **The effective degrees of freedom**, when they are small enough to matter (below
   about 30).
5. **The method** — GUM framework, Monte Carlo, or both with the validation outcome.

The two standard forms:

> m = 100.02147 g with a combined standard uncertainty of u_c = 0.35 mg.

> m = (100.02147 ± 0.00079) g, where the number following the symbol ± is the numerical
> value of an expanded uncertainty U = k·u_c with U determined from a combined standard
> uncertainty u_c = 0.35 mg and a coverage factor k = 2.26 based on the t-distribution
> for ν_eff = 9 degrees of freedom, and defines an interval estimated to have a level of
> confidence of 95%.

The second is verbose because it has to be. `scripts/format_result.py --coverage-factor`
formats the supplied values; its stated probability is caller-supplied and not verified.

## SD, SEM, and CI in figures

An error bar is uninterpretable unless the caption says what it is, and the three
common choices differ by more than a factor of two for typical n:

| Bar | Answers | Shrinks with n |
| --- | --- | --- |
| Standard deviation | how much do individual observations scatter | no |
| Standard error of the mean | how precisely is the mean located | yes, as 1/√n |
| 95% confidence interval | plausible range for the population mean | yes |

Choosing SEM because it looks tighter is a misrepresentation when the question is about
spread. Every caption needs the bar's identity, n, and whether n counts biological or
technical replicates. Two SEM bars that do not overlap do not establish a significant
difference, and two 95% CIs that overlap slightly do not establish the absence of one.

## Relative and absolute

State which. A relative standard uncertainty is dimensionless and is written
`u_r(y) = 0.0035` or `0.35%`; multiplying it by the absolute value of the estimate gives the absolute one. Mixing
them in a single budget without conversion is a common arithmetic error — a "1%"
component and a "0.2 mg" component cannot be combined until they are in the same form.

For a product or quotient of independent quantities, relative uncertainties combine in
quadrature; for a sum or difference, absolute ones do. Using the wrong one is the single
most common propagation mistake, and it is why deriving the budget from sensitivity
coefficients rather than from remembered rules is worth the extra step.

## Results near zero or below a detection limit

- An uncertainty larger than the estimate does not invalidate the measurement. Retain
  the estimate and uncertainty; assess compatibility with zero using a justified interval
  and the intended measurement model, not the size of an unspecified error bar.
- Do not substitute zero, LOD, or LOD/2 for a non-detect without saying so; each choice
  biases downstream statistics differently.
- A negative estimate of a non-negative quantity is a legitimate measurement outcome and
  should be reported as measured, not truncated. Truncating biases any subsequent
  average.
- LOD and LOQ need a stated procedure and performance criteria. Multiples such as
  3σ and 10σ of a blank are conventions in some methods, not universal definitions.
- Zero supplied uncertainty is not evidence of exactness; it may mean uncertainty was
  omitted or a first-order derivative vanished.

## Significant figures in intermediate work

Round only at the point of reporting. Carrying rounded intermediates through a
calculation accumulates error that the uncertainty budget does not account for, and it
can shift the final digit. Keep full precision internally; apply
`scripts/format_result.py` at the end.

The same applies to constants: use `scipy.constants`, not a value typed from memory to
four digits.

## Conformity statements

Deciding whether a result passes a specification is a separate step from measuring it,
because the decision depends on the specified acceptance rule and risk. An interval
straddling a limit does not by itself settle conformity. ISO/IEC 17025 requires a documented decision rule; ILAC-G8
describes guard-banded acceptance, where the acceptance limit is pulled inside the
specification limit by a multiple of u_c chosen for the false-accept risk you will
tolerate. Report the rule alongside the verdict.

## Sources

- JCGM 100:2008 (GUM), clause 7 — reporting uncertainty.
- JCGM 101:2008 (GUM Supplement 1), clause 8 — numerical tolerance and validation.
- NIST Technical Note 1297, *Guidelines for Evaluating and Expressing the Uncertainty of
  NIST Measurement Results* — the source of the two standard sentence forms above.
- ISO/IEC 17025:2017 clause 7.8.6 and ILAC-G8:09/2019 — decision rules and guard bands.

Current [ILAC guidance index](https://ilac.org/publications-and-resources/ilac-guidance-series/)
still lists ILAC G8:09/2019 (checked 2026-10-01); use its rule appropriate to the agreed
conformity task. This skill does not certify laboratory accreditation or compliance.
