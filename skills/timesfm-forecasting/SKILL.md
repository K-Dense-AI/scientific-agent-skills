---
name: timesfm-forecasting
description: Performs zero-shot time-series forecasting with Google's TimesFM, including regular-grid CSV preparation, quantile forecasts, XReg covariates, and held-out evaluation. Uses the Apache-licensed TimesFM 2.5 checkpoint by default and documents the distinct TimesFM 3.0 multivariate API and weight-license requirements.
allowed-tools: Read Write Edit Bash
license: Apache-2.0 license
compatibility: Requires Python 3.10+ and timesfm 3.0.2 with PyTorch; CSV tooling also needs NumPy and pandas. Network access and cache space are needed for initial Hugging Face checkpoint download. Optional XReg needs JAX and scikit-learn; current JAX requires Python 3.12+.
metadata:
  version: "3.0"
  skill-author: Clayton Young / Superior Byte Works, LLC (@borealBytes)
  last-reviewed: "2026-10-01"
  tested-package: "timesfm 3.0.2"
---

# TimesFM Forecasting

## Choose the model/API first

The **Python package version is 3.0.2**; checkpoint versions are separate.

| Checkpoint | Interface | Quantile output | Usage terms |
| --- | --- | --- | --- |
| 2.5, 200M | `timesfm.TimesFM_2p5_200M_torch`, `compile`, `forecast` | mean + 9 deciles, median index 5 | Apache-2.0 weights; bundled CLI default |
| 3.0, about 330M | `timesfm3.TimesFM3Forecaster`, `predict` / `predict_batch` | 9 deciles, median index 4 | Downloaded weights restricted to non-commercial, non-production use |

Upstream identifies 3.0 as the latest model. This skill retains 2.5 as its default
local workflow because its Apache-licensed weights have different usage terms.
For 3.0 multivariate targets, past-only covariates or Apple MLX, read
[references/timesfm3.md](references/timesfm3.md) before adapting code. Authorized
Google Cloud services have separate terms; a Cloud entitlement does not change
the license of downloaded weights. See the [upstream license notice](https://github.com/google-research/timesfm#license-notice-for-pretrained-weights).

Use TimesFM for forecasting an ordered temporal target without task-specific
model training. It is not a causal effect estimator, clinical detector, or
physics-based climate model. Zero-shot describes fitting; it does not establish
absence of benchmark overlap in pretraining or good accuracy in a new domain.

## Workflow

1. Establish cadence, units, forecast origin, horizon, known-at-origin covariates,
   evaluation cutoffs and a naive/seasonal-naive baseline.
2. Validate a sorted, unique, regular time grid. Do not `dropna()` internal gaps:
   that changes temporal spacing. Reject nonfinite inputs, or explicitly impute
   inside each training history. Never fill using held-out future targets.
3. Run `python scripts/check_system.py` before downloading/loading weights.
   Its available-RAM and cache-volume thresholds are heuristics, not a guarantee
   against OOM. Start with batch size 1; measure actual peak usage.
4. Load the chosen checkpoint with a recorded immutable revision. For 2.5,
   compile explicit positive context/horizon settings; zero does **not** mean
   “use the maximum.” Keep patch-rounded context + horizon <=16,384 and horizon
   <=1,024 when using the continuous quantile head.
5. Forecast, validate shapes/finite values/quantile ordering and export the
   forecast origin, frequency, configuration and checkpoint revision.
6. Evaluate across rolling origins with preprocessing fitted independently per
   origin. Report accuracy, interval coverage and interval width by horizon;
   label quantile intervals **nominal** until calibrated on relevant data.

## Installation

Run in a separate environment. The commands below target the reviewed release.
Shell extras and version constraints must be quoted, particularly in zsh.

```bash
uv venv .venv-timesfm
uv pip install --python .venv-timesfm/bin/python "timesfm[torch]==3.0.2" numpy pandas
.venv-timesfm/bin/python scripts/check_system.py
```

Use the current [PyTorch installation selector](https://pytorch.org/get-started/locally/)
for a CUDA wheel matching the host. The 2.5 loader in this release chooses
`cuda:0` if CUDA exists, otherwise CPU; detecting MPS does **not** enable MPS
inference. Do not use `model.to(...)` on the wrapper as if it were an `nn.Module`.
For CPU-only XReg, install `jax` and `scikit-learn` alongside the PyTorch profile;
the upstream `[xreg]` extra requests `jax[cuda]`, which is not appropriate for macOS.
Flax is a separate optional backend; it is not required by the bundled scripts.

```python
from importlib.metadata import version
import timesfm
print(version("timesfm"))  # package has no guaranteed timesfm.__version__
assert hasattr(timesfm, "TimesFM_2p5_200M_torch")
```

## TimesFM 2.5 quick start

The checkpoint-load examples are illustrative: validation of this refresh used
native package code with tiny random models and controlled decode fixtures,
without downloading pretrained weights. That verifies mechanics, not accuracy.

```python
import numpy as np
import timesfm

model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
    "google/timesfm-2.5-200m-pytorch",
    revision="1d952420fba87f3c6dee4f240de0f1a0fbc790e3",
    torch_compile=False,  # avoid compilation startup during an initial smoke run
)
model.compile(timesfm.ForecastConfig(
    max_context=512, max_horizon=128, per_core_batch_size=1,
    normalize_inputs=True, use_continuous_quantile_head=True,
    force_flip_invariance=True, infer_is_positive=False,
    fix_quantile_crossing=True,
))
histories = [np.sin(np.linspace(0, 20, 200)).astype(np.float32)]
# 2.5 may append dummy series to its input list during batching; pass a fresh list.
point, q = model.forecast(horizon=24, inputs=list(histories))
assert point.shape == (1, 24) and q.shape == (1, 24, 10)
assert np.isfinite(q).all() and np.all(np.diff(q[..., 1:], axis=-1) >= 0)
assert np.allclose(point, q[..., 5])
lower_80, upper_80 = q[..., 1], q[..., 9]  # q10-q90: nominal 80% PI
lower_60, upper_60 = q[..., 2], q[..., 8]  # q20-q80: nominal 60% PI
```

Set `infer_is_positive=True` only for a target domain that is truly nonnegative.
A positive observed window does not establish that temperature anomalies,
returns or residuals cannot become negative. Monotonic quantiles and a
continuous quantile head do not establish interval calibration.

## CSV helper

```bash
python scripts/forecast_csv.py monthly_sales.csv \
  --date-col date --freq MS --value-cols sales,revenue \
  --horizon 12 --batch-size 1 --nonnegative --output forecasts.csv
```

`forecast_csv.py` validates before loading, sorts dates, rejects duplicate
headers/dates, checks the complete regular grid and preserves missing positions.
Missing values fail by default; `--missing interpolate` fills only internal gaps,
never leading/trailing values. Without `--date-col`, row order is assumed to be
the regular grid and output uses steps. Numeric IDs must be excluded using
`--value-cols`. `--max-context` controls history truncation; `--horizon` is limited
to 1..1,024 for this quantile-head workflow.

Outputs retain `forecast`, `median`, `lower_80`, `upper_80`, `lower_60`, `upper_60`.
A `.metadata.json` sidecar records origin, cadence, model revision and config.
Old skill releases mislabeled q10-q90/q20-q80 as 90%/80%; migrate old outer
`*_90` to `*_80` and old inner `*_80` to `*_60` simultaneously. Old generated
example forecasts were removed because their mapping/provenance was invalid.

## Covariates and anomaly screening

For 2.5 XReg, compile `return_backcast=True`, retain targets and covariates on
identical grids and provide dynamic covariates over context **and** horizon.
`"xreg + timesfm"` fits regression on targets, then forecasts regression residuals.
`"timesfm + xreg"` forecasts first, then fits regression on backcast residuals.
The latter needs more than one input patch (32 observations). In package 3.0.2,
the implementation returns **lists of combined point and quantile forecasts**;
an inherited docstring incorrectly describes the second return as XReg-only.
See [references/api_reference.md](references/api_reference.md) for the complete call.

Quantile exceedances may screen for unusual observations, but even calibrated
80% intervals exclude about 20% of ordinary observations marginally. They do
not supply anomaly probabilities, familywise control or validated alarm severity.
Retrospective detrended Z scores also differ from prospective anomaly detection.

## References and examples

- [API reference](references/api_reference.md): 2.5 loader, compile, forecast and XReg contracts.
- [Output/config](references/output_and_config.md): all real ForecastConfig fields and interval indexing.
- [Data preparation](references/data_preparation.md): grid, missingness, covariate timing and format recipes.
- [Workflows](references/workflows.md): held-out and rolling-origin validation, baseline comparisons.
- [System requirements](references/system_requirements.md): resource checks and backend requirements.
- [Performance tuning](references/performance_tuning.md): measured batch/context tuning.
- [Examples and validation](references/examples_and_validation.md): example commands and testing scope.
- [TimesFM 3.0](references/timesfm3.md): multivariate API, 9-decile layout and usage boundary.

Primary review sources: [official source](https://github.com/google-research/timesfm),
[3.0.2 distribution](https://pypi.org/project/timesfm/3.0.2/),
[2.5 model card](https://huggingface.co/google/timesfm-2.5-200m-pytorch),
[3.0 model card](https://huggingface.co/google/timesfm-3.0-pytorch).
