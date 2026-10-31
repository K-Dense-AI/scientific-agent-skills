# TimesFM 3.0: distinct API and output layout

Reviewed package 3.0.2 against the [released distribution](https://pypi.org/project/timesfm/3.0.2/)
and [official source](https://github.com/google-research/timesfm/tree/e51928e27119cb17bebc005be2696b75e0a9e688/src/timesfm3).
The 3.0 checkpoint adds joint multivariate targets and native covariates. Its
weights use the [TimesFM Non-Commercial License](https://huggingface.co/google/timesfm-3.0-pytorch/blob/main/LICENSE):
downloaded/self-hosted weights are restricted to non-commercial, non-production
use. Authorized Google Cloud use has separate service terms. The code remains
Apache-2.0; do not confuse that code license with the weight license.

## PyTorch

Illustrative pretrained load; a tiny random model's native CPU save/load/predict
was tested, not the downloaded 330M checkpoint or its predictive performance.

```python
import numpy as np
from timesfm3 import TimesFM3Forecaster

forecaster = TimesFM3Forecaster.from_pretrained(
    "google/timesfm-3.0-pytorch",
    revision="43046b85ec22d584a13f8098c2ed39c889e129c2",
    device="cpu", per_core_batch_size=1,
)
history = np.sin(np.linspace(0, 20, 128)).astype(np.float32)
out = forecaster.predict(history, horizon=24, return_quantiles=True)
assert out.forecast.shape == (24,)
assert out.quantiles.shape == (24, 9)
assert np.allclose(out.forecast, out.quantiles[:, 4])
lower_80, upper_80 = out.quantiles[:, 0], out.quantiles[:, 8]
```

There is no 2.5-style `compile(ForecastConfig)` step. `TimesFM3Evaluator(ModelConfig(...))`
is another public wrapper; prefer the forecaster interface shown here for local
array inference. Hub options include `revision`, `cache_dir`, `force_download`,
`local_files_only` and `token`; cache/download semantics follow Hugging Face Hub.
Never print credentials. A local `save_pretrained` directory is also accepted.

## Multivariate targets and covariates

```python
T, H = 128, 24
rng = np.random.default_rng(7)
target = rng.normal(size=(2, T)).astype(np.float32)
past_only = rng.normal(size=(1, T)).astype(np.float32)
# Illustrative planned feature; in real evaluation all H values must be known at origin.
past_future = np.sin(np.arange(T + H) / 7)[None, :].astype(np.float32)
out = forecaster.predict(
    target, horizon=H,
    past_only_covariates=past_only,
    past_future_covariates=past_future,
    return_quantiles=True,
    make_positive=False, sort_quantiles=True,
    use_symmetric_averaging=False, use_znorm=False, padding_mode="none",
)
assert out.forecast.shape == (2, H)
assert out.quantiles.shape == (2, H, 9)
```

Targets use `(target_variates, time)`; covariates use `(feature_channels, time)`.
Past-only time length is T; past-future length is T+H. All channels share the
same regular grid. Validate finite values, nonempty targets, positive H, lengths
and known-at-origin availability yourself; permissive interpolation is not a
missingness model. Covariates are numerical arrays; this is not the 2.5 static/
categorical XReg dictionary API.

`predict_batch(contexts=[...], horizon=H, ...)` yields `ForecastOutput` objects.
Parallel optional lists are `past_only_covariates`, `past_future_covariates` and
`ts_ids`. All contexts in a batch must have the same number of target variates;
keep 1D/2D conventions consistent. `return_quantiles=False` yields `quantiles=None`.
Default output contains q10..q90 only, so median is index 4 and there is no mean
slot. Sorting quantiles enforces order, not calibration.

The context cap is 15,360 with the official 32-point patch; older points are
truncated. Horizon is rounded internally to 64-point patches and sliced back
on output. `padding_mode="none"` avoids inventing future feature values; `"edge"`
extends covariates for internal patch padding. `make_positive=False` is the
default; enable it only if the target domain cannot be negative.

## MLX / Apple silicon

Upstream package 3.0.2 offers `timesfm[mlx]` (MLX >=0.32):
`from timesfm3.mlx import TimesFM3Forecaster`, with corresponding `from_pretrained`,
`predict` and `predict_batch`. This is separate from the 2.5 torch wrapper's CPU
fallback on Apple hardware. MLX mechanics/performance were source-reviewed but
not executed in this refresh. Do not extrapolate published hardware benchmarks
to the user's context length, horizon or memory budget.
