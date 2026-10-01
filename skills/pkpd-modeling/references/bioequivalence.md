# Bioequivalence: design before arithmetic

## Conventional average BE

Log-transform each prespecified positive PK metric and estimate the test/reference contrast under
the actual design. Back-transform the 90% confidence interval. Conventional 80–125% limits are
not universal; select metric, design, region and product-specific guidance before analyzing data.

The helper supports complete two-period RT/TR crossover and independent parallel observations.
Crossover requires exactly one T and one R per subject, correct period/sequence labels and both
sequences. It accounts for sequence in the within-subject contrasts. Parallel analysis requires one
value per subject. Neither path handles missing-period replicate data, carryover, multiple groups,
adaptive designs or repeated independent-looking values.

## Reference scaling

Replicate BE needs a design-specific statistical model. Period/sequence-adjusted reference
variance and treatment-contrast uncertainty cannot generally be obtained by pooling each subject's
raw replicate variance or averaging repeats. The CLI therefore rejects replicate analysis and
reference scaling; it must not output a regulatory pass from those shortcuts.

FDA's May 2026 guidance replaces the 2001 statistical guidance. Appendix G supplies HVD models:
`sWR >= 0.294`, a reference-scaled upper-bound criterion and an 80–125% point-estimate constraint.
In its scalar bound, `x=estimate²-SE²` and the negative variance term's bound uses the **0.95**
chi-square quantile. The retained `rsabe_bound` helper only combines externally justified scalar
inputs; it cannot fit the required design or determine applicability. FDA NTI analysis is distinct;
`--nti` merely changes this CLI's conventional limits.
[FDA statistical guidance](https://www.fda.gov/media/163638/download).

EMA widening for eligible highly variable Cmax uses `exp(±0.760*sWR)`, capped at CVwR 50%, with
80–125% point-estimate constraints and prespecified clinical justification. It is not generic
permission to widen AUC or NTI limits. ABEL and FDA RSABE are different procedures. The scalar
`abel_limits` is arithmetic only; use a qualified design-specific implementation.
[EMA BE guideline](https://www.ema.europa.eu/en/documents/scientific-guideline/guideline-investigation-bioequivalence-rev1_en.pdf).

## Planning

Power depends on GMR, within-subject CV, allocation, design, dropout and analysis assumptions.
The bundled calculation integrates over estimated variance using a finite quantile grid. It is a
numerical approximation, not an exact Owen-Q implementation. With balanced 2x2, CV 30%, GMR 0.95
and target power 80%, it returns N=40 evaluable participants in synthetic checks. Probe sensitivity,
then independently check the intended design using [PowerTOST](https://cran.r-project.org/web/packages/PowerTOST/vignettes/vignette.html).

## Current harmonization boundary

ICH M13A concerns immediate-release solid oral products; EU implementation began 25  January 2025.
Regional provisions for replicate and NTI studies still require attention. M13B is now EMA Step 5,
adopted  September 2026 with effect  March 2027; it concerns additional-strength biowaivers, not HVD
statistics. M13C remains under development. See [regulatory guidance](regulatory-guidance.md).
