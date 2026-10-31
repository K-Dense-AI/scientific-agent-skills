# Output and configuration (2.5 model, package 3.0.2)

With `return_backcast=False`, `forecast()` returns `(B,H)` point and `(B,H,10)`
quantile arrays. Index 0 is a separately trained mean; indices 1..9 correspond
to q10..q90. The point is q50 at index 5. The model does not return q05/q95 or
q99 in this interface. Nine quantiles are not a full predictive distribution.

| Band | Slice indices | Nominal coverage |
| --- | --- | --- |
| q10-q90 | 1, 9 | 80% |
| q20-q80 | 2, 8 | 60% |
| q50 | 5 | median, equals point |

A 90% central interval would need q05/q95, not a relabeled decile pair.
Calibration must be evaluated for the data, origin and horizon of interest.
Pointwise nominal coverage does not give simultaneous coverage over a trajectory.

`ForecastConfig` is a frozen dataclass; these are its actual fields:

| Field | Default | Effect |
| --- | --- | --- |
| `max_context` | 0 | Set positive; left padding / last-window truncation, rounded to 32 |
| `max_horizon` | 0 | Set positive; rounded to 128; requested H must not exceed it |
| `normalize_inputs` | False | Optional extra normalization for numerical scale; compare on held-out data |
| `window_size` | 0 | Reserved/unimplemented; leave at 0 |
| `per_core_batch_size` | 1 | Start at 1 and measure before raising |
| `use_continuous_quantile_head` | False | Separate quantile-spread head; supports <=1,024 rounded horizon |
| `force_flip_invariance` | True | Symmetric positive/negative input averaging; increases compute |
| `infer_is_positive` | True | If entire input is nonnegative, clips outputs at zero; domain decision |
| `fix_quantile_crossing` | False | Enforces ordering about the median; does not calibrate coverage |
| `return_backcast` | False | Prepends context backcast; required by XReg |

`quantiles` and `decode_index` belong to the checkpoint definition, **not**
ForecastConfig. Fields such as `stride`, `d_model`, `seed`, `dtype` and
`input_patch_len` are not ForecastConfig arguments. The old diagram showed
unsupported arguments and must not be used as an API reference.

Check all outputs for finite values and shape, test `point == q[...,5]`, and
check `np.diff(q[...,1:], axis=-1) >= 0`. Exclude index 0 from that ordering test.
With backcasts enabled, slice future positions before evaluating accuracy.
TimesFM 3.0 has no mean slot; its median is index 4, see `timesfm3.md`.
