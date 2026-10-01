# ICH Q2(R2) — Structure and Recommended Data

Research basis: **2026-09-30**, read from the ICH Harmonised Guideline *Validation of Analytical
Procedures Q2(R2)*, Final Version adopted 1 November 2023, with the error correction dated
30 November 2023. ICH licenses its documents for reuse with acknowledgement, so requirements are
summarised here directly. Confirm the current text and your region's implementation date at
<https://database.ich.org/sites/default/files/ICH_Q2%28R2%29_Guideline_2023_1130.pdf>.

## Document history that matters

| Version | Date | Note |
| --- | --- | --- |
| Q2A | Oct 1994 | Text |
| Q2B | Nov 1996 | Methodology |
| Q2(R1) | Nov 2005 | Q2B merged into the parent guideline |
| Q2(R2) | 1 Nov 2023 | Complete revision, aligned with the new Q14 |
| Q2(R2) correction | 30 Nov 2023 | Table 5 reportable-range linearity formulae; Tables 6–11 |

If a protocol cites "ICH Q2(R1)" or lists characteristics in the R1 order, it is working from the
superseded structure. The error correction is easy to miss and applies to the dissolution example
and to Annex 2 Tables 6–11.

## The restructure

Q2(R1) presented a flat list. Q2(R2) groups methodology under section 3 by performance
characteristic:

```
3.1  Specificity/Selectivity
       3.1.1 General considerations (absence of interference, orthogonal comparison,
             technology-inherent justification)
3.2  Range                                    <-- parent characteristic
       3.2.2 Response
               3.2.2.1 Linear response        <-- what R1 called "linearity"
               3.2.2.2 Non-linear response
               3.2.2.3 Multivariate calibration
       3.2.3 Validation of lower range limits <-- what R1 called LOD and LOQ
3.3  Accuracy and Precision
       3.3.1 Accuracy
       3.3.2 Precision (repeatability, intermediate precision, reproducibility)
       3.3.3 Combined approaches for accuracy and precision   <-- new
3.4  Robustness  --> largely a development activity, see ICH Q14
```

Section 2 carries the general considerations, including two concepts absent from R1: **reportable
range** (2.3) and **considerations for multivariate analytical procedures** (2.5).

## Table 1 — which tests for which measured attribute

Table 1 identifies tests normally conducted by measured quality attribute. It allows justified
alternatives; the table is not an unconditional legal requirement.

| Characteristic | Identity | Impurity: quantitative | Impurity: limit test | Assay (content/potency) |
| --- | --- | --- | --- | --- |
| Specificity test | yes | yes | yes | yes |
| Response (calibration model) | no | yes | no | yes |
| Lower range limit | no | QL† | DL | no |
| Accuracy test | no | yes | no | yes |
| Repeatability test | no | yes | no | yes |
| Intermediate precision test | no | yes‡ | no | yes‡ |

† In some complex cases DL may also be evaluated.
‡ Not required independently where reproducibility has been performed and intermediate precision
can be derived from that dataset.

Further notes from Table 1: other quantitative measurements follow the impurity scheme when the
range limit is close to DL/QL, and the assay scheme when it is not. Some characteristics may be
substituted by technology-inherent justification for physicochemical properties. Lack of specificity
in one procedure should be compensated by one or more supporting procedures unless justified.

## Table 2 — reportable range examples

The reportable range derives from the specification and must include the upper and lower
specification or reporting limits. Other ranges are acceptable if justified; at low amounts a wider
upper range may be more practical.

| Use | Low end | High end |
| --- | --- | --- |
| Assay of a product | 80% of declared content, or 80% of the lower specification limit | 120% of declared content, or 120% of the upper specification limit |
| Potency | lowest specification limit −20% | highest specification limit +20% |
| Content uniformity | 70% of declared content | 130% of declared content |
| Dissolution, IR, one point | Q − 45% of the lowest strength specification | 130% of declared content of the highest strength |
| Dissolution, IR, multi-point | lower limit as justified, or QL | 130% of declared content of the highest strength |
| Dissolution, modified release | lower limit as justified, or QL | 130% of declared content of the highest strength |
| Impurity | reporting threshold | 120% of the specification limit |
| Purity (area %) | 80% of the lower specification limit | upper specification limit, or 100% |

Where assay and impurity run as a single test with one standard, linearity must be shown both at the
impurity reporting level and up to 120% of the assay specification limit.

**Reportable range vs working range.** The reportable range is the interval of *reported results*.
A working range is what is presented to the instrument, and may differ because of dilution or other
sample preparation. They can be identical. Mathematical calculation normally links the two.

## Recommended data, by characteristic

**Specificity (3.1).** Demonstrate absence of relevant interference, or compare against an
orthogonal procedure, or justify from the technology. For a stability-indicating claim (2.4),
include samples containing relevant degradation products: spiked with target analytes and known
interferences, stressed physically and chemically, and aged or stress-stored product samples.

**Response — linear (3.2.2.1).** Evaluate across the range. **A minimum of five concentrations,
appropriately distributed, is recommended.** Report the plot, the correlation coefficient or
coefficient of determination, the y-intercept, the slope, and *an analysis of the deviation of the
actual data points from the regression line* — for a linear response, assess the impact of any
non-random pattern in the residual plot. Data may be transformed (for example logarithmically) if
necessary. Other approaches require justification.

**Response — non-linear (3.2.2.2).** Some procedures are legitimately non-linear; immunoassays and
cell-based assays commonly give an S-shaped curve, typically modelled with four- or five-parameter
logistic functions. For these, **linearity of the concentration–response relationship is not
required.** Assess the model by non-linear regression, and evaluate whether results are proportional
to the true values across the range.

**Response — multivariate (3.2.2.3).** Algorithms may be linear or non-linear. Accuracy depends on
the distribution of calibration samples across the range and on the reference procedure's error.
Assess how the residuals change across the calibration range, graphically.

**Lower range limits (3.2.3).** Four approaches:

| Approach | DL | QL |
| --- | --- | --- |
| Visual evaluation (3.2.3.1) | lowest reliably detected | lowest reliably quantitated |
| Signal-to-noise (3.2.3.2) | S/N 3:1 generally acceptable | S/N at least 10:1 |
| SD of response and slope (3.2.3.3) | 3.3σ / S | 10σ / S |
| Accuracy and precision at the limit (3.2.3.4) | — | validated directly, not estimated |

σ may come from the SD of blank responses, the residual SD of the regression line, or the SD of
y-intercepts of regression lines. S is the calibration slope. Signal-to-noise applies only where
there is baseline noise, and the noise region should sit around where the peak would appear.

Reporting (3.2.3.5): give the limit **and the approach used**. An estimated limit should then be
validated by analysing a suitable number of samples at or near it. **For impurity tests the QL must
be at or below the reporting threshold.** Where the QL is well below the reporting limit — roughly
ten times lower — the confirmatory validation may be omitted with justification.

**Accuracy (3.3.1).** Establish across the reportable range under regular test conditions, including
the sample matrix and the described preparation steps. Three routes: comparison against a reference
material of known purity, a spiking study into matrix, or comparison against an orthogonal
procedure. Accuracy can be inferred once precision, response within the range, and specificity are
established.

Recommended data (3.3.1.4): an appropriate number of determinations and levels across the reportable
range — **for example 3 concentrations × 3 replicates of the full procedure.** Report as mean percent
recovery of a known added amount, or as the difference between the mean and the accepted true value,
**together with an appropriate 100(1−α)% confidence interval** or justified alternative interval. The
observed interval should be compatible with the accuracy criterion. For impurities, state whether
the determination is weight/weight or area percent. For quantitative multivariate procedures use
RMSEP, compared against an acceptable RMSEC.

**Precision (3.3.2).** Use authentic homogeneous samples, or artificially prepared ones if
unavailable.

- *Repeatability (3.3.2.1)*: **a minimum of 9 determinations covering the reportable range** (for
  example 3 concentrations × 3 replicates), **or a minimum of 6 determinations at 100% of the test
  concentration.**
- *Intermediate precision (3.3.2.2)*: establish the effects of random events — typically different
  days, environmental conditions, analysts, and equipment. **Studying these effects individually is
  not necessary**, and design of experiments is encouraged. The extent should be justified from
  development understanding and risk assessment (ICH Q14).
- *Reproducibility (3.3.2.3)*: an inter-laboratory trial. **Usually not required for a regulatory
  submission**, but consider it for pharmacopoeial standardisation or multi-site procedures.

Recommended data (3.3.2.4): report the standard deviation, the relative standard deviation, and an
appropriate 100(1−α)% confidence interval.

**Combined accuracy and precision (3.3.3).** Instead of separate criteria, assess total impact
against a single combined criterion, using a prediction interval, a tolerance interval, or a
confidence interval. Report the combined value, describe the approach, and supply the individual
results as supplemental information where they help justify suitability.

**Robustness (3.4).** Deliberate variation of procedure parameters, plus stability of sample
preparations and reagents over the duration of the procedure. Considered during development; may be
submitted as development data case-by-case or made available on request. See ICH Q14 section 5.

## Lifecycle, transfer, and prior knowledge

Section 2.1 permits suitable development data (ICH Q14) to form part of the validation data, and
allows abbreviated validation testing for an established platform procedure used for a new purpose,
with scientific justification. A validation protocol must exist before the study, stating the
intended purpose, the characteristics to be validated, and the associated criteria; where prior
knowledge is used, justify it. Results are summarised in a validation report.

The experimental design should reflect the number of replicates used in routine analysis to generate
a reportable result, unless a different number is justified.

Section 2.2 covers change: partial or full revalidation may be needed, decided on science and risk,
and scoped to the characteristics the change affects. **Transfer** to another laboratory calls for
partial or full revalidation and/or comparative analysis of representative samples; not performing
transfer experiments requires justification. **Co-validation** across multiple sites can demonstrate
the criteria are met and can simultaneously satisfy transfer at the participating sites.

## Annex 2 — illustrative technique examples

Non-mandatory worked examples, useful as a starting point for the robustness parameter list:

| Table | Technique |
| --- | --- |
| 3 | Quantitative separation techniques (HPLC, GC, CE) for impurities or assay, and relative-area quantitation |
| 4 | Elemental impurities by ICP-OES or ICP-MS |
| 5 | Dissolution with HPLC as product performance test (corrected 30 Nov 2023) |
| 6 | Quantitative ¹H-NMR for assay of a drug substance |
| 7 | Biological assays |
| 8 | Quantitative PCR |
| 9 | Particle size measurement |
| 10 | NIR analytical procedure |
| 11 | Quantitative LC/MS |

From Table 3, a detail worth carrying forward: **relative response factors.** Where the analyte
responds differently from the reference material, calculate the RRF from the appropriate ratio of
responses under final procedure conditions and document it. **The illustrative Table 3 recommends correction when RRF is outside 0.8–1.2.** Where an impurity is overestimated, omitting the correction may be
acceptable.

## Multivariate procedures (2.5)

Results come from a model relating many input variables to the property of interest. Validate in two
phases:

1. **Model development** — calibration plus internal testing. Test data may be a separate set or
   part of the calibration set used rotationally, and are used to estimate performance and tune
   parameters such as the number of PLS latent variables. See ICH Q14.
2. **Model validation** — an independent validation set. For identification libraries, analyse
   challenge samples *not* represented in the library to demonstrate discriminative ability.

Samples need reference values or categories, normally from a validated or pharmacopoeial reference
procedure whose performance **equals or exceeds** the expected performance of the multivariate
procedure. Reference measurement and multivariate data collection should be on the same samples
within a period short enough to assure sample and measurement stability. Describe any correlation or
unit conversion, and any assumptions.
