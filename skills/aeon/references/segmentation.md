# Time Series Segmentation

Aeon provides algorithms to partition time series into regions with distinct characteristics, identifying change points and boundaries.

## Segmentation Algorithms

### Binary Segmentation
- `BinSegmenter` - Recursive binary segmentation
  - Iteratively splits series at most significant change points
  - Parameters: `n_cps`, `model`, `min_size`, `jump` (requires ruptures)
  - **Use when**: Known number of segments, hierarchical structure

### Classification-Based
- `ClaSPSegmenter` - Classification Score Profile
  - Uses classification performance to identify boundaries
  - Discovers segments where classification distinguishes neighbors
  - **Use when**: Segments have different temporal patterns

### Fast Pattern-Based
- `FLUSSSegmenter` - Fast Low-cost Unipotent Semantic Segmentation
  - Efficient semantic segmentation using arc crossings
  - Based on matrix profile
  - **Use when**: Large time series, need speed and pattern discovery

### Information Theory
- `InformationGainSegmenter` - Information gain maximization
  - Finds boundaries maximizing information gain
  - **Use when**: Statistical differences between segments

### Gaussian Modeling
- `GreedyGaussianSegmenter` - Greedy Gaussian approximation
  - Models segments as Gaussian distributions
  - Incrementally adds change points
  - **Use when**: Segments follow Gaussian distributions

### Hierarchical Agglomerative
- `EAggloSegmenter` - Bottom-up merging approach
  - Estimates change points via agglomeration
  - **Use when**: Want hierarchical segmentation structure

### Hidden Markov Models
- `HMMSegmenter` - HMM with Viterbi decoding
  - Probabilistic state-based segmentation
  - **Use when**: Segments represent hidden states

### Dimensionality-Based
- `HidalgoSegmenter` - Heterogeneous Intrinsic Dimensionality Algorithm
  - Detects changes in local dimensionality
  - **Use when**: Dimensionality shifts between segments

### Baseline
- `RandomSegmenter` - Random change point generation
  - **Use when**: Need null hypothesis baseline

## Quick Start

```python
from aeon.segmentation import ClaSPSegmenter
import numpy as np

# Create time series with regime changes
y = np.concatenate([
    np.sin(np.linspace(0, 10, 100)),      # Segment 1
    np.cos(np.linspace(0, 10, 100)),      # Segment 2
    np.sin(2 * np.linspace(0, 10, 100))   # Segment 3
])

# Segment the series
segmenter = ClaSPSegmenter(period_length=20, n_cps=2)
change_points = segmenter.fit_predict(y)

print(f"Detected change points: {change_points}")
```

## Output Format

Output depends on the estimator. ClaSPSegmenter and BinSegmenter return change-point locations; HMMSegmenter and InformationGainSegmenter return a dense state/segment label per timepoint. In this API `returns_dense=True` denotes boundary locations and `False` denotes per-timepoint labels. Check the concrete estimator and convert label changes before calling boundary metrics:

```python
# Dense labels to boundaries (when labels is a label per timepoint):
change_points = np.flatnonzero(np.diff(labels) != 0) + 1
# e.g. change_points = [100, 200]
# This divides series into: [0:100], [100:200], [200:end]
```

## Algorithm Selection

- **Speed priority**: FLUSSSegmenter, BinSegmenter
- **Accuracy priority**: ClaSPSegmenter, HMMSegmenter
- **Known segment count**: BinSegmenter(n_cps=number_of_segments - 1)
- **Chosen boundary budget**: ClaSPSegmenter uses n_cps; InformationGainSegmenter uses k_max. Defaults do not infer an unconstrained number of regimes
- **Pattern changes**: FLUSSSegmenter, ClaSPSegmenter
- **Statistical changes**: InformationGainSegmenter, GreedyGaussianSegmenter
- **State transitions**: HMMSegmenter

The snippets using domain variables are illustrative templates; the synthetic ClaSP, information-gain, and HMM examples were exercised on aeon 1.6.

## Common Use Cases

### Regime Change Detection
Identify when time series behavior fundamentally changes:

```python
from aeon.segmentation import InformationGainSegmenter

segmenter = InformationGainSegmenter(k_max=3)
# Positive multivariate channels; single-channel entropy is uninformative.
sensor_channels = np.random.default_rng(42).uniform(0.1, 1, (2, 100))
labels = segmenter.fit_predict(sensor_channels, axis=1)
change_points = np.flatnonzero(np.diff(labels) != 0) + 1
```

### Activity Segmentation
Segment sensor data into activities:

```python
from aeon.segmentation import ClaSPSegmenter

segmenter = ClaSPSegmenter(period_length=20, n_cps=2)
boundaries = segmenter.fit_predict(sensor_magnitude)  # one univariate series
```

### Seasonal Boundary Detection
Decode a two-state example with known emission and transition probabilities. HMMSegmenter does not learn those parameters from observations:

```python
from aeon.segmentation import HMMSegmenter
from scipy.stats import norm

segmenter = HMMSegmenter(
    emission_funcs=[(norm.pdf, {"loc": 0, "scale": 0.5}),
                    (norm.pdf, {"loc": 5, "scale": 0.5})],
    transition_prob_mat=np.array([[0.95, 0.05], [0.05, 0.95]]),
)
observations = np.array([0.1, -0.1, 0.2, 4.9, 5.1, 5.0])
segments = segmenter.fit_predict(observations)
```

## Evaluation Metrics

Use segmentation quality metrics:

```python
from aeon.benchmarking.metrics.segmentation import (
    count_error,
    hausdorff_error
)

# Count error: difference in number of change points
count_err = count_error(y_true, y_pred)

# Hausdorff: maximum distance between predicted and true points
hausdorff_err = hausdorff_error(y_true, y_pred)
```

## Best Practices

1. **Normalize data**: Ensures change detection not dominated by scale
2. **Choose appropriate metric**: Different algorithms optimize different criteria
3. **Validate segments**: Visualize to verify meaningful boundaries
4. **Handle noise**: Consider smoothing before segmentation
5. **Domain knowledge**: Use expected segment count if known
6. **Parameter tuning**: Adjust sensitivity parameters (thresholds, penalties)

## Visualization

```python
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 4))
plt.plot(y, label='Time Series')
for cp in change_points:
    plt.axvline(cp, color='r', linestyle='--', label='Change Point')
plt.legend()
plt.show()
```

Sources: [segmentation API](https://www.aeon-toolkit.org/en/stable/api_reference/segmentation.html), [release source](https://github.com/aeon-toolkit/aeon/tree/v1.6.0/aeon/segmentation).
