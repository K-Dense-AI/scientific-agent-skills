# TimesFM 2.5 API in package 3.0.2

Reviewed 2026-10-01 against the released wheel and identical official source at
[commit e51928e](https://github.com/google-research/timesfm/tree/e51928e27119cb17bebc005be2696b75e0a9e688/src/timesfm).
This profile is separate from the `timesfm3` namespace.

## Loader

```python
model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
    "google/timesfm-2.5-200m-pytorch",  # or a local safetensors directory
    revision="1d952420fba87f3c6dee4f240de0f1a0fbc790e3",
    cache_dir=None,
    force_download=False,
    local_files_only=False,
    torch_compile=False,
)
```

The public method is inherited from `PyTorchModelHubMixin`; `revision`, `cache_dir`,
`force_download`, `local_files_only` and `token` are Hub arguments. Never print tokens.
The checkpoint uses `model.safetensors`; the old claim that it requires
`torch_model.ckpt` came from using the incompatible v1 loader. Loader default
`torch_compile=True` is distinct from the mandatory `model.compile(ForecastConfig)`.
The wrapper has no documented device parameter: the inner module chooses CUDA:0
if available, otherwise CPU. Public weights need no account token for normal
public downloads. Hub failures, permissions and local cache misses still propagate.

## Compile and forecast

`compile(forecast_config, **kwargs)` constructs a decode callable. Context is
rounded up to a multiple of 32; horizon to a multiple of 128. Use positive explicit
values, ideally already rounded: zero is not a sentinel for the model maximum.
Rounded context + horizon cannot exceed 16,384. The continuous quantile head
rejects rounded horizons over 1,024. Invalid configurations can raise `ValueError`.

`forecast(horizon: int, inputs: list[np.ndarray])` needs compilation first. With
`return_backcast=False`, output is `(point, q)`, shapes `(B,H)` and `(B,H,10)`.
Point equals `q[...,5]`; `q[...,0]` is the separately trained mean output, not a
decile. With `return_backcast=True`, outputs prepend a backcast of length
`max_context - 32` (including padded context positions). Slice the last H for
future-only results; a backcast is not a held-out accuracy measurement.

The implementation copies each array, strips leading NaNs and uses `np.interp`
for other NaNs (including last-value extension at the trailing edge). All-NaN
and empty inputs are not a reliable scientific input contract: validate and
reject them yourself. Internal gaps must retain positions, and interpolation
must never span a train/test cutoff. The batching implementation appends padding
series to the supplied list; pass `list(histories)` if retaining it for reuse.

## XReg

Native CPU regression requires JAX and scikit-learn, even with the torch backend.
On CPU/macOS use `uv pip install jax scikit-learn`; upstream `timesfm[xreg]`
requests CUDA JAX. Current JAX 0.11.2 requires Python >=3.12.

Illustrative checkpoint example (shape/return behavior tested without weights):

```python
import numpy as np
import timesfm

# model is the loaded 2.5 wrapper, histories is an ordered list of target arrays.
H = 12
model.compile(timesfm.ForecastConfig(
    max_context=512, max_horizon=128, per_core_batch_size=1,
    normalize_inputs=True, use_continuous_quantile_head=True,
    infer_is_positive=False, fix_quantile_crossing=True, return_backcast=True,
))
# Prices and holiday schedules must be known at this forecast origin.
# Each dynamic array i has len(histories[i]) + H entries.
point_list, quantile_list = model.forecast_with_covariates(
    inputs=list(histories),
    dynamic_numerical_covariates={"price": price_arrays},
    dynamic_categorical_covariates={"holiday": holiday_arrays},
    static_numerical_covariates={"floor_area": store_areas},
    static_categorical_covariates={"region": region_labels},
    xreg_mode="xreg + timesfm",
    normalize_xreg_target_per_input=True,
    ridge=1.0, max_rows_per_col=0, force_on_cpu=True,
)
assert len(point_list) == len(histories)
assert quantile_list[0].shape == (H, 10)
```

| Argument | Contract |
| --- | --- |
| `inputs` | One finite target context per series; keep its exact origin/length |
| `dynamic_numerical_covariates` | Name -> list of numeric context+future arrays |
| `dynamic_categorical_covariates` | Name -> list of context+future categories; int or string |
| `static_numerical_covariates` | Name -> one numeric value per series |
| `static_categorical_covariates` | Name -> one category per series |
| `xreg_mode` | `"xreg + timesfm"` (default) or `"timesfm + xreg"` |
| `normalize_xreg_target_per_input` | Default True; target scaling per series |
| `ridge` | Default 0.0; positive values regularize the pooled regression |
| `max_rows_per_col` | Default 0; positive value may subsample regression rows |
| `force_on_cpu` | Default False; controls regression device, not TimesFM device |

Both modes require `return_backcast=True`. `xreg + timesfm` fits regression
on target contexts then TimesFM on residuals. `timesfm + xreg` obtains backcasts
then fits their residuals; require context >32 and avoid contexts longer than
the compiled context in that mode so residual lengths remain aligned.
Horizon is inferred from the first dynamic covariate's length minus context;
all features must agree. With only static covariates it uses the **compiled,
patch-rounded** max_horizon, so do not assume the unrounded requested value.

The 3.0.2 implementation returns `(list[point array], list[quantile array])`,
**not** `(combined forecast, regression forecast)` despite its stale docstring.
Validate shapes, finiteness and ordered deciles after the regression shift.
Future realized weather/prices are leakage unless those values were known at
origin. Covariate scenarios condition the prediction; their own uncertainty and
regression estimation uncertainty are not automatically covered by model bands.

## Other checkpoints

The supported Flax class is `timesfm.TimesFM_2p5_200M_flax` with
`google/timesfm-2.5-200m-flax`. This refresh did not execute Flax/TPU/CUDA.
Legacy 1.0/2.0 use package 1.3.0 and a different `TimesFmHparams` API; they are
not drop-in checkpoint IDs for these helpers. Transformers and MLX adapters
also have separate configurations and outputs; do not transplant indices blindly.
