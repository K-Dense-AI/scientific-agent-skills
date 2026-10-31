# Censoring-aware evaluation, calibration, and model selection

Verified for scikit-survival 0.28.0 on 2026-10-01. API statements below use
official scikit-survival documentation; interpretation is anchored to the cited
primary methodological literature.

## Keep the targets distinct

- **Discrimination:** can the score order subjects by event risk?
  Harrell C, Uno C, and cumulative/dynamic AUC.
- **Probability prediction error:** how close are predicted survival probabilities
  to observed event-free status after censoring adjustment? Brier score and IBS.
- **Calibration:** do predicted probabilities agree with observed probabilities at
  a specified horizon and population? Requires horizon-specific assessment; Brier
  score is not a pure calibration measure.
- **Cause-specific cumulative incidence:** what is the absolute probability of a
  particular competing cause by time \(t\)? Standard survival metrics are not
  automatically cause-specific CIF metrics.
- **Clinical/decision utility:** do decisions based on predictions improve outcomes
  under defined consequences? None of the metrics above establishes this.

Do not label one aggregate number "model accuracy" without its estimand, horizon,
censoring estimator, and input type.

## Prediction contracts

### Higher-is-riskier scalar

Shape `(n_test,)`. Used by:

- `concordance_index_censored`
- `concordance_index_ipcw`
- `cumulative_dynamic_auc` (same score at each requested time)

Typical source:

```python
risk = estimator.predict(X_test)
```

Confirm direction. Cox and ranking-only SVM predictions are higher-is-riskier.
Predicted survival/log-time outputs are the opposite direction and must not be
silently treated as risk.

### Time-dependent risk

Shape `(n_test, n_times)`. Accepted by `cumulative_dynamic_auc`, where column
`j` is risk at `times[j]`. For a random survival forest:

```python
functions = estimator.predict_cumulative_hazard_function(X_test)
risk_by_time = np.vstack([fn(times) for fn in functions])
```

Cumulative hazard is risk-oriented. Untransformed survival probabilities have the opposite direction and are not valid risk inputs to `cumulative_dynamic_auc`. Numeric shape validation does not detect that semantic error; check output direction explicitly before using a transformed probability or hazard score.

### Survival probability

Shape `(n_test, n_times)`, values in `[0, 1]`, non-increasing across columns.
Used by:

- `brier_score`
- `integrated_brier_score`

```python
functions = estimator.predict_survival_function(X_test)
survival_probability = np.vstack([fn(times) for fn in functions])
```

Metric functions expect the numeric matrix, not a list of unevaluated
`StepFunction` objects and not a 1D risk score.

## Harrell concordance

```python
from sksurv.metrics import concordance_index_censored

harrell_c = concordance_index_censored(
    y_test["event"],
    y_test["time"],
    risk,
)[0]
```

Harrell C is the fraction of comparable pairs whose risk ordering is concordant,
with handling for tied risk and event times. It measures rank discrimination over
the observed follow-up mix.

Important limitations:

- It does not assess probability calibration.
- It does not focus on a prespecified horizon.
- The set of comparable pairs changes under censoring.
- Uno et al. showed the conventional estimator's limiting value can depend on the
  censoring distribution.

There is no universal censoring-percentage cutoff at which Harrell C suddenly
becomes invalid. Report censoring, compare sensitivity to IPCW concordance, and
justify the estimand.

## Uno IPCW concordance

```python
from sksurv.metrics import concordance_index_ipcw

uno_c = concordance_index_ipcw(
    y_train,
    y_test,
    risk,
    tau=tau,
)[0]
```

`survival_train` estimates the censoring distribution. Never pass pooled
train+test outcomes or `y_test` as the training distribution.

`tau` truncates the concordance target. Choose it before seeing model performance
and where the estimated training censoring survival is positive. In 0.28.0 only test event times strictly below `tau` enter its censoring-weight
lookup; later records remain potential comparison partners with zero event weight.
A valid `tau` can therefore avoid a late-event support error for Uno C. This does
not make the same test outcomes valid for AUC or Brier APIs.

The implementation uses Kaplan-Meier censoring weights and assumes censoring is
random/independent of features. If censoring depends on covariates, this marginal
weight model may be inadequate. IPCW is not a generic correction for informative
censoring.

## Cumulative/dynamic AUC

```python
from sksurv.metrics import cumulative_dynamic_auc

auc, mean_auc = cumulative_dynamic_auc(
    y_train,
    y_test,
    risk,   # (n_test,) or (n_test, n_times)
    times,
)
```

At each \(t\), cumulative cases have an observed event by \(t\), while dynamic
controls remain event-free after \(t\). IPCW handles right censoring.

Requirements:

- `times` is one-dimensional, unique, and strictly increasing;
- every value lies within test follow-up;
- training follow-up supports test outcomes and the grid;
- the training censoring survival is positive over the grid and at every test
  event time used by the implementation (AUC weights all test events before
  applying horizons);
- each horizon has at least one observed case and a later control;
- risk has shape `(n_test,)` or `(n_test, n_times)`;
- higher values mean higher event risk.

The returned `mean_auc` is not the arithmetic mean. It integrates
\(\widehat{AUC}(t)\) over the time range, weighted by the estimated survival
function.

The cumulative/dynamic definition is one time-dependent ROC estimand. State it;
other incident/dynamic or competing-risk definitions answer different questions.

## Brier score

```python
from sksurv.metrics import brier_score, integrated_brier_score

returned_times, brier = brier_score(
    y_train,
    y_test,
    survival_probability,
    times,
)
ibs = integrated_brier_score(
    y_train,
    y_test,
    survival_probability,
    times,
)
```

The time-dependent Brier score is an IPC-weighted squared error between predicted
survival probability and event-free status at \(t\). Lower is better.

Requirements:

- predictions are survival probabilities, not risk scores;
- prediction shape is `(n_test, n_times)`;
- time and training-support rules match the IPCW setting;
- the marginal Kaplan-Meier censoring estimator's independence assumption is
  plausible.

IBS in 0.28.0 equals `np.trapezoid(brier, times) / (times[-1] - times[0])`.
It is the normalized trapezoidal integral over the supplied interval. It depends on the chosen interval; IBS values from different
time ranges are not directly comparable.

Compare against useful reference predictions such as a training-derived
Kaplan-Meier survival curve. Do not estimate the reference curve on test outcomes.

## Calibration

Brier score responds to both discrimination and calibration. A good Brier score
does not prove that predicted 20% risk corresponds to 20% observed risk in every
horizon or subgroup.

For a prespecified horizon:

1. fit and tune the model without the calibration-evaluation rows;
2. obtain event probability `1 - S(t | x)` on independent validation rows;
3. compare predictions with a censoring-aware observed probability estimate;
4. inspect calibration-in-the-large, slope/shape, uncertainty, and sample support;
5. repeat only for prespecified horizons/subgroups or account for multiplicity.

scikit-survival 0.28 does not expose a dedicated calibration-curve API. Do not use
`sklearn.calibration.calibration_curve` naively on censored binary labels. If an
external method is used, document its censoring assumptions and train/validation
separation.

Any recalibration layer is another learned model. Fit it on a calibration split or
inner resampling, then assess on independent data.

## Safe time-grid construction

A conservative grid for jointly computing AUC, Uno C, and Brier metrics:

```python
import numpy as np
from sksurv.nonparametric import CensoringDistributionEstimator

test_time = y_test["time"]
train_time = y_train["time"]

lower = np.quantile(test_time, 0.10)
upper = min(
    np.quantile(test_time, 0.80),
    np.nextafter(train_time.max(), -np.inf),
)
times = np.linspace(lower, upper, 50)

if not (test_time.min() < times[0] < times[-1] < test_time.max()):
    raise ValueError("grid is outside test follow-up")
if not test_time.max() < train_time.max():
    raise ValueError("test follow-up exceeds training support")

censoring = CensoringDistributionEstimator().fit(y_train)
if np.any(censoring.predict_proba(times) <= 0):
    raise ValueError("training censoring survival reaches zero on grid")
censoring.predict_ipcw(y_test)  # AUC needs positive support at all test event times
if not np.any(y_test["event"] & (test_time <= times[0])):
    raise ValueError("AUC has no observed cases at the first horizon")
```

This strict maximum-follow-up check is a helper policy, not an exact universal API
restriction. Native Brier metrics also query censoring survival at all test times;
zero weights may be suppressed by the implementation, so a successful call alone
is not evidence of valid support. Never silently drop long-followed test subjects
to obtain a score: define administrative truncation and recode late events as
censored under a prespecified estimand if that is scientifically intended.

Quantiles are an operational example, not a scientific default. Prefer
prespecified meaningful horizons, then verify fold support. Do not select a grid
because it maximizes a metric.

The bundled evaluator rejects unsupported grids and shape/type confusion:

```bash
python skills/scikit-survival/scripts/evaluate_survival_metrics.py \
  --input predictions.npz \
  --output metrics-summary.json
```

Its NPZ contract is:

- `train_event`, `train_time`
- `test_event`, `test_time`
- `times`
- `risk`
- optional `survival`

Archives are loaded with `allow_pickle=False`, with compressed-file and total
expanded-member bounds. The evaluator requires at least two horizons for the
combined workflow; native AUC and Brier permit a single horizon, whereas IBS does not.

## Scorer wrappers and model selection

Survival estimators' default `.score()` is Harrell concordance and handles their
own prediction direction. Discrimination wrappers below call raw `.predict()`;
they do not reverse time-oriented IPCRidge, SVM-regression, or AFT-boosting output. For other targets,
scikit-survival provides estimator wrappers:

- `as_concordance_index_ipcw_scorer(estimator, tau=None, tied_tol=...)`
- `as_cumulative_dynamic_auc_scorer(estimator, times, tied_tol=...)`
- `as_integrated_brier_score_scorer(estimator, times)`

Correct pattern:

```python
from sklearn.model_selection import GridSearchCV
from sksurv.metrics import as_integrated_brier_score_scorer

wrapped = as_integrated_brier_score_scorer(
    estimator,
    times=inner_times,
)
search = GridSearchCV(
    wrapped,
    {"estimator__model__max_depth": [1, 2, 4]},
    cv=inner_splits,
)
search.fit(X_outer_train, y_outer_train)
```

The wrapper:

- is the estimator supplied to `GridSearchCV`;
- stores its fitted estimator in `estimator_`;
- exposes nested parameters under `estimator__...`;
- fits metric state, including training survival information, from each fit fold;
- negates IBS so larger wrapper score remains better.

Do not write `scoring=as_integrated_brier_score_scorer(times)`; the constructor
requires an estimator.

## Nested CV protocol

For tuned performance:

```text
for each outer split:
    outer_train, outer_valid
    for each inner split within outer_train:
        fit preprocessing + model + censoring-dependent scorer state
        select hyperparameters
    refit selected pipeline on all outer_train
    evaluate once on outer_valid using outer_train censoring distribution
aggregate outer scores and uncertainty
```

Every fold needs its own valid `tau`/time grid. A single global grid derived from
all outcome times leaks outer-validation support information and may fail when an
outer training fold has shorter follow-up.

After protocol evaluation, tune on all development data and evaluate once on an
untouched final test set. Do not report the best inner-CV score as generalization
performance.

## Competing risks

If events have causes:

- all-event risk combines causes and is not cause-specific discrimination;
- treating other causes as censored defines a cause-specific hazard analysis;
- a cause-specific CIF is an absolute probability accounting for all causes;
- standard Brier/AUC functions here are documented for right-censored
  single-event outcomes, not a complete competing-risk prediction evaluation.

State event coding and use methods designed for the cause-specific estimand. See
`competing-risks.md`.

## Reporting checklist

- split and nesting protocol;
- event/censoring counts per evaluation set;
- metric definition and score direction;
- `tau` and exact time grid/range;
- source of censoring weights;
- prediction shape and whether values are risks or survival probabilities;
- uncertainty across independent outer folds or bootstrap resamples;
- calibration assessment separate from discrimination;
- handling of competing causes;
- no claim of clinical utility from metrics alone.

## Primary methodological literature

- Harrell FE Jr, Califf RM, Pryor DB, Lee KL, Rosati RA. "Evaluating the
  yield of medical tests." *JAMA* (1982).
  [doi:10.1001/jama.1982.03320430047030](https://doi.org/10.1001/jama.1982.03320430047030)
- Uno H, Cai T, Pencina MJ, D'Agostino RB, Wei LJ. "On the C-statistics for
  evaluating overall adequacy of risk prediction procedures with censored
  survival data." *Statistics in Medicine* (2011).
  [doi:10.1002/sim.4154](https://doi.org/10.1002/sim.4154)
- Heagerty PJ, Lumley T, Pepe MS. "Time-dependent ROC curves for censored
  survival data and a diagnostic marker." *Biometrics* (2000).
  [doi:10.1111/j.0006-341X.2000.00337.x](https://doi.org/10.1111/j.0006-341X.2000.00337.x)
- Heagerty PJ, Zheng Y. "Survival model predictive accuracy and ROC curves."
  *Biometrics* (2005).
  [doi:10.1111/j.0006-341X.2005.030814.x](https://doi.org/10.1111/j.0006-341X.2005.030814.x)
- Graf E, Schmoor C, Sauerbrei W, Schumacher M. "Assessment and comparison
  of prognostic classification schemes for survival data."
  *Statistics in Medicine* (1999).
  [doi:10.1002/(SICI)1097-0258(19990915/30)18:17/18%3C2529::AID-SIM274%3E3.0.CO;2-5](https://doi.org/10.1002/%28SICI%291097-0258%2819990915/30%2918%3A17/18%3C2529%3A%3AAID-SIM274%3E3.0.CO%3B2-5)
- Gerds TA, Schumacher M. "Consistent estimation of the expected Brier score
  in general survival models with right-censored event times."
  *Biometrical Journal* (2006).
  [doi:10.1002/bimj.200610301](https://doi.org/10.1002/bimj.200610301)

## Official API sources

Checked 2026-10-01:

- [Evaluation user guide](https://scikit-survival.readthedocs.io/en/stable/user_guide/evaluating-survival-models.html)
- [Metrics API index](https://scikit-survival.readthedocs.io/en/stable/api/metrics.html)
- [IPCW concordance API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.metrics.concordance_index_ipcw.html)
- [Cumulative/dynamic AUC API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.metrics.cumulative_dynamic_auc.html)
- [Brier score API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.metrics.brier_score.html)
- [Integrated Brier score API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.metrics.integrated_brier_score.html)
- [IPCW scorer wrapper API](https://scikit-survival.readthedocs.io/en/stable/api/generated/sksurv.metrics.as_concordance_index_ipcw_scorer.html)
