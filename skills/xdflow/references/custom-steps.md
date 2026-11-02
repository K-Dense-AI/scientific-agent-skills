# Custom Steps and Validators

Examples continue from the `data` defined in SKILL.md Step 2. Reviewed against xdflow 0.4.0. Prefer, in
order: a built-in transform (`from xdflow.transforms import ...`), a scikit-learn estimator wrapped with
`SKLearnTransformer` / `SKLearnPredictor`, an `@xdflow.step` function, and only then a `Transform` subclass.

## `@xdflow.step` Functions

The first parameter receives an `xarray.DataArray`; the other parameters become hyperparameters that clone,
tune (`"band_power__band"`), and appear in provenance like a built-in transform's.

```python
import numpy as np
import xarray as xr

import xdflow


@xdflow.step
def window_power(data: xr.DataArray, start=0.2, end=0.8) -> xr.DataArray:
    """Log mean power in a time window, per trial and channel."""
    return np.log((data.sel(time=slice(start, end)) ** 2).mean("time"))


def channel_means(data):
    return data.mean(("trial", "time"))


@xdflow.step(fit=channel_means)  # stateful: fit runs on each training fold only
def recenter(data, state):
    return data - state


features = window_power(start=0.3).transform(data)
```

Rules:

- Return an `xr.DataArray`, or a NumPy array with the same shape as the input (it inherits dims and coords).
- The input is a read-only view: in-place edits (`data *= 2`) raise. `attrs` are shared, so copy nested values
  before changing them.
- A step **without** `fit` must compute each trial from that trial alone. Each call reruns the function on a
  sample of three trials and raises if their output differs, pointing to `fit`. The check samples trials, so
  it catches most cross-trial computations, not all.
- Never read the target coordinate inside a step; the independence check cannot detect it.
- Define step functions at module level so fitted pipelines can be pickled.
- Pass `output_dims=(...)` (and optionally `input_dims=(...)`) to take part in pipeline dimension checks.

## `Transform` Subclasses

Subclass when a step needs selection support, custom dimension logic, or complex fitted state.

```python
from typing import Any

from xdflow import DataContainer, Transform


class PeakToPeakTransform(Transform):
    """Peak-to-peak amplitude over one dimension (stateless)."""

    is_stateful = False
    input_dims = ()
    output_dims = ()

    def __init__(self, dim: str = "time", sel: dict[str, Any] | None = None):
        super().__init__(sel=sel)
        self.dim = dim  # every constructor argument is a public attribute with the same name

    def _transform(self, container: DataContainer, **kwargs) -> DataContainer:
        data = container.data
        if self.dim not in data.dims:
            raise ValueError(f"Dimension '{self.dim}' not found in input dims {data.dims}.")
        return DataContainer(data.max(dim=self.dim) - data.min(dim=self.dim))

    def get_expected_output_dims(self, input_dims: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(d for d in input_dims if d != self.dim)


class ChannelCenterTransform(Transform):
    """Subtract a per-channel mean learned on training trials (stateful)."""

    is_stateful = True
    input_dims = ("trial", "channel", "time")
    output_dims = ("trial", "channel", "time")

    def __init__(self, center_dims: tuple[str, ...] = ("trial", "time"), sel: dict[str, Any] | None = None):
        super().__init__(sel=sel)
        self.center_dims = center_dims
        self._mean = None  # fitted state is private, so clone() returns an unfitted copy

    def _fit(self, container: DataContainer, **kwargs) -> "ChannelCenterTransform":
        self._mean = container.data.mean(dim=list(self.center_dims))
        return self

    def _transform(self, container: DataContainer, **kwargs) -> DataContainer:
        if self._mean is None:
            raise ValueError("ChannelCenterTransform must be fitted before transform().")
        return DataContainer(container.data - self._mean)


ptp = PeakToPeakTransform().transform(data)
assert ptp.data.dims == ("trial", "channel") and "subject" in ptp.data.coords
centered = ChannelCenterTransform().fit_transform(data)
assert ChannelCenterTransform().fit(data).clone()._mean is None
```

Contract:

- Return a new `DataContainer`; never mutate `container.data`.
- Use dimension names, not positional axes. When building a `DataArray` from NumPy output, carry over
  coordinates whose dims survive (`{k: c for k, c in data.coords.items() if set(c.dims) <= set(out_dims)}`).
- Set `is_stateful = True` for anything estimated across trials (means, PCA, filters fitted to data,
  thresholds). Being stateless means each trial's output depends on that trial alone, not merely that the
  class holds no estimator.
- Set `_supports_transform_sel = True` only if output keeps the input's dims, sizes, and dimension coords;
  that enables the inherited `transform_sel` / `transform_drop_sel` write-back.
- Do not override `clone()`; override `_get_clone_kwargs()` if constructor kwargs need special handling.
- Validate required coordinates, attrs (`sfreq`), and units inside the transform and raise clear errors;
  dimension declarations are not a semantic schema.

Tests worth adding for each new transform: output dims and `get_expected_output_dims` agree, trial
coordinates survive, input is unchanged after `transform`, `clone()` is unfitted, `fit_transform` equals
`fit` then `transform` for stateful steps, and missing dims or coords raise.

## Custom Cross-Validators

Only when the split policy itself is new; the base `CrossValidator` already owns scoring, holdout, out-of-fold
collection, compute-once preprocessing, and per-fold refitting. Implement two methods that return **trial
coordinate labels** (not positions):

```python
from collections.abc import Iterator

import numpy as np

from xdflow import CrossValidator


class LeaveLastSessionOutValidator(CrossValidator):
    """Train on earlier sessions of every subject, validate on each subject's last session."""

    def __init__(self, subject_coord: str = "subject", session_coord: str = "session", **kwargs):
        super().__init__(**kwargs)
        self.subject_coord = subject_coord
        self.session_coord = session_coord

    def _split_holdout(self, container: DataContainer) -> tuple[np.ndarray, np.ndarray]:
        return container.data.trial.values, np.array([])  # no holdout

    def _get_splits(self, container: DataContainer, indices_to_split: np.ndarray) -> Iterator[tuple]:
        da = container.data.sel(trial=indices_to_split)
        last = da[self.session_coord].groupby(da[self.subject_coord]).max()
        is_last = da[self.session_coord].values == last.sel({self.subject_coord: da[self.subject_coord]}).values
        yield da.trial.values[~is_last], da.trial.values[is_last]


custom_cv = LeaveLastSessionOutValidator(scoring="accuracy", verbose=False)
```

Validate that the required coordinates exist and index `trial` before splitting, and audit the result with
`xdflow.check_split(data, validator)` after `cross_validate`.
