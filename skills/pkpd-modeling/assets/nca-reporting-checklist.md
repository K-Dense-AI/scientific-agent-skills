# NCA reporting checklist

Record the applicable conventions and provenance below. The bundled helper uses one global BLQ
rule, so location-dependent handling requires documented preprocessing.

## The four conventions that change the answer

- [ ] **Trapezoidal rule**: linear / linear-up-log-down / log-linear
- [ ] **BLQ handling**, stated separately for each position:
  - leading (before the first quantifiable sample): [ zero / excluded ]
  - embedded: [ zero / LLOQ÷2 / excluded ]
  - trailing: [ excluded / other ]
- [ ] **Lambda_z selection**: the rule, the minimum number of points, whether Tmax was excluded, and
      the window and point count actually used **for each subject**
- [ ] **AUCinf basis**: observed Clast or predicted Clast

## Data

- [ ] Analyte, matrix, assay, LLOQ, and the bioanalytical validation report reference
- [ ] Actual elapsed times used, not nominal — and nominal times used only for grouping
- [ ] Dose actually administered per subject, including any deviations
- [ ] Records excluded, with the reason, and confirmation the criteria were set before unblinding
- [ ] Deviations in sampling time above [ ]% of the nominal time, and how they were handled

## Parameters reported

- [ ] Cmax and Tmax as **observed** values, never interpolated
- [ ] AUClast, AUCinf (both observed- and predicted-based, or one with the basis stated)
- [ ] % AUC extrapolated, per subject
- [ ] lambda_z, t½, and the number of points and time span of the terminal fit, per subject
- [ ] CL or CL/F, Vz or Vz/F — with `/F` used for every extravascular route
- [ ] Vss **only** for intravenous data
- [ ] At steady state: AUC(0-tau), Cavg, Cmin, PTF%, accumulation ratio — and **not** AUCinf
- [ ] Partial AUCs, if pre-specified, with their intervals

## Terminal-phase quality, per subject

- [ ] Adjusted r-squared of the lambda_z regression
- [ ] Span ratio (window duration ÷ t½); below 2 is a screening flag, not a universal exclusion
- [ ] % AUC extrapolated; above 20% is a screening flag, not a universal exclusion
- [ ] Number of points in the fit; flag below 3
- [ ] Subjects for whom lambda_z was not estimable, and how they were handled in the summary

## Summary statistics

- [ ] Exposure metrics (AUC, Cmax) as **geometric mean and geometric CV%**
- [ ] Tmax as **median and range**
- [ ] Arithmetic mean, SD and CV% where relevant to the estimand, with the summary basis stated
- [ ] n for each parameter, since it differs when lambda_z fails for some subjects

## Presentation

- [ ] Individual concentration-time profiles on both linear and semi-logarithmic axes
- [ ] Mean profiles with a stated rule for handling BLQ in the mean
- [ ] A table of individual parameters, not only summary statistics

## Method and provenance

- [ ] Software and version
- [ ] Units for every parameter, and confirmation that dose and concentration units are consistent
- [ ] Whether the analysis was pre-specified, and the reference to the plan
- [ ] Any deviation from the plan, with its reason

## The traps this checklist exists to catch

1. Reporting AUCinf from a truncated steady-state profile.
2. Interpolating Cmax, or reporting a mean Tmax.
3. Quoting Vz as if it were Vss, or reporting Vss from oral data.
4. Applying one BLQ rule to the test arm and another to the reference.
5. Using a summary basis that does not match the estimand or comparing incompatible summaries.
6. Summarising across subjects without saying that lambda_z failed for some of them.
7. Omitting the lambda_z window, which makes the half-life unreproducible.
