# Specialized Topics

Geostatistics, optimization, privacy and provenance. Reviewed 2026-10-01. Data-dependent fragments remain illustrative; small numerical functions are exercised by the recipe suite. All Euclidean coordinates below require a suitable metric CRS.

## Geostatistics

### Variogram Analysis

```python
import numpy as np
from scipy.spatial.distance import pdist, squareform
import matplotlib.pyplot as plt

def empirical_variogram(points, values, max_lag=None, n_lags=15):
    """
    Calculate empirical variogram.
    """
    points = np.asarray(points, dtype=float)
    values = np.asarray(values, dtype=float)
    if points.ndim != 2 or values.shape != (len(points),) or len(points) < 2:
        raise ValueError('At least two points with one value each are required')
    if not np.isfinite(points).all() or not np.isfinite(values).all():
        raise ValueError('Inputs must be finite')
    distances = pdist(points)  # unique unordered pairs; no self-pairs
    differences = pdist(values[:, None], metric='sqeuclidean')
    max_lag = distances.max() / 2 if max_lag is None else max_lag
    if not np.isfinite(max_lag) or max_lag <= 0 or n_lags < 1:
        raise ValueError('Positive finite maximum lag and positive lag count required')
    edges = np.linspace(0, max_lag, n_lags + 1)
    centers, semivariance = [], []
    for i, (low, high) in enumerate(zip(edges[:-1], edges[1:])):
        keep = (distances >= low) & ((distances <= high) if i == n_lags - 1 else (distances < high))
        if keep.any():
            centers.append(distances[keep].mean())
            semivariance.append(0.5 * differences[keep].mean())
    return np.asarray(centers), np.asarray(semivariance)

# Fit variogram model
def fit_variogram_model(lags, gammas, model='spherical'):
    """
    Fit theoretical variogram model.
    """
    from scipy.optimize import curve_fit

    def spherical(h, nugget, sill, range_):
        """Spherical model; sill argument is partial sill, total sill=nugget+sill."""
        h = np.asarray(h)
        gamma = np.where(h < range_,
                        nugget + sill * (1.5 * h/range_ - 0.5 * (h/range_)**3),
                        nugget + sill)
        return gamma

    def exponential(h, nugget, sill, range_):
        """Exponential model."""
        return nugget + sill * (1 - np.exp(-3 * h / range_))

    def gaussian(h, nugget, sill, range_):
        """Gaussian model."""
        return nugget + sill * (1 - np.exp(-3 * (h/range_)**2))

    models = {
        'spherical': spherical,
        'exponential': exponential,
        'gaussian': gaussian
    }

    # Fit model
    popt, _ = curve_fit(models[model], lags, gammas,
                        p0=[np.min(gammas), np.max(gammas), np.max(lags)/2],
                        bounds=([0, 0, 1e-12], [np.inf, np.inf, np.inf]))

    return popt, models[model]
```

### Kriging Interpolation

```python
from pykrige.ok import OrdinaryKriging
import numpy as np

def ordinary_kriging(x, y, z, grid_resolution=100):
    """
    Perform ordinary kriging interpolation.
    """
    # Create grid
    gridx = np.linspace(x.min(), x.max(), grid_resolution)
    gridy = np.linspace(y.min(), y.max(), grid_resolution)

    # Fit variogram
    OK = OrdinaryKriging(
        x, y, z,
        variogram_model='spherical',
        verbose=False,
        enable_plotting=False,
        coordinates_type='euclidean',
    )

    # Interpolate
    zinterp, sigmasq = OK.execute('grid', gridx, gridy)

    return zinterp, sigmasq, gridx, gridy

# Cross-validation
def kriging_cross_validation(x, y, z, groups, n_folds=5):
    """
    Perform k-fold cross-validation for kriging.
    """
    from sklearn.model_selection import GroupKFold

    kf = GroupKFold(n_splits=n_folds)
    errors = []

    for train_idx, test_idx in kf.split(z, groups=groups):
        # Train
        OK = OrdinaryKriging(
            x[train_idx], y[train_idx], z[train_idx],
            variogram_model='spherical',
            verbose=False
        )

        # Predict at test locations
        predictions, _ = OK.execute('points',
                                    x[test_idx], y[test_idx])

        # Calculate error
        rmse = np.sqrt(np.mean((predictions - z[test_idx])**2))
        errors.append(rmse)

    return np.mean(errors), np.std(errors)
```

## Spatial Optimization

### Location-allocation: explicit p-median formulation

SLSQP over thresholded fractional variables is not a binary facility solver. For a
small candidate set, use binary open-site variables `y_j` and assignment variables
`x_ij`, minimize `sum(demand_i * cost_ij * x_ij)`, and constrain:

- `sum_j x_ij = 1` for every demand point;
- `x_ij <= y_j`;
- `sum_j y_j = p`;
- all variables in {0,1}.

Use `scipy.optimize.milp` with `integrality=1`, `Bounds(0, 1)` and explicit
`LinearConstraint` objects, then require solver success and verify feasibility,
objective and chosen site count. Costs may be network travel times, not straight-line
distance; unreachable pairs must be prohibited. Weighted demand needs explicit units.
KMeans/snapping is a heuristic and can select duplicate sites.

### Routing optimization

For a small connected undirected road graph, build a shortest-path metric closure
before a TSP heuristic. `G[current][candidate]` assumes a direct edge and fails on
ordinary sparse road graphs. NetworkX `traveling_salesman_problem(G, nodes=stops,
weight='length', cycle=True)` computes a closure and expands the tour back onto
original graph paths. Report it as approximate; repeated intermediate nodes are
normal. Directed routing needs strong reachability and a compatible heuristic.

Vehicle routing additionally constrains capacity, depot starts/ends, customer demand,
service time, time windows and fleet. Cluster-first routes that never inspect a
`capacity` argument are not a capacity-constrained VRP solution. Use an appropriate
routing optimizer and verify each route against the constraints afterward.

## Ethics and Privacy

### Privacy-preserving geospatial analysis

Independent metre-scale noise added directly to longitude/latitude is dimensionally
wrong and does not establish a privacy guarantee. Define protected units, adjacency,
release mechanism, sensitivity and composition before claiming differential privacy.
Use a reviewed mechanism appropriate to location data and a threat model; geographic
projection/extent and side information matter. For descriptive maps, aggregate to
justified cells and suppress sparse groups, while reporting that aggregation alone
does not prove anonymity.

Line simplification is not k-anonymity: it does not create k indistinguishable people
or protect sensitive places. Audit re-identification risk and consent/access controls;
preserve sensitive raw trajectories separately from permitted outputs.

### Data Provenance

```python
# Track geospatial data lineage
import pandas as pd

class DataLineage:
    def __init__(self):
        self.history = []

    def record_transformation(self, input_data, operation, output_data, params):
        """Record data transformation."""
        record = {
            'timestamp': pd.Timestamp.now(),
            'input': input_data,
            'operation': operation,
            'output': output_data,
            'parameters': params
        }
        self.history.append(record)

    def get_lineage(self, data_id):
        """Traverse recorded edges without infinite recursion on cycles."""
        lineage, seen, pending = [], set(), [data_id]
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            for record in self.history:
                if record['output'] == current:
                    lineage.append(record)
                    pending.append(record['input'])
        return lineage
```

## Best Practices

### Reproducible Research

```python
# Use environment.yml for dependencies
# environment.yml:
"""
name: geomaster
dependencies:
  - python=3.13
  - geopandas
  - rasterio
  - scikit-learn
  - pip
  - pip:
    - torchgeo
"""

# Capture session info
def capture_environment():
    """Capture software and data versions."""
    import platform
    import geopandas as gpd
    import rasterio
    import numpy as np
    import pandas as pd

    info = {
        'os': platform.platform(),
        'python': platform.python_version(),
        'geopandas': gpd.__version__,
        'rasterio': rasterio.__version__,
        'numpy': np.__version__,
        'pandas': pd.__version__,
        'timestamp': pd.Timestamp.now()
    }

    return info

# Save with output
import json
with open('processing_info.json', 'w') as f:
    json.dump(capture_environment(), f, indent=2, default=str)
```

### Code Organization

```python
# Project structure
"""
project/
├── data/
│   ├── raw/
│   ├── processed/
│   └── external/
├── notebooks/
├── src/
│   ├── __init__.py
│   ├── data_loading.py
│   ├── preprocessing.py
│   ├── analysis.py
│   └── visualization.py
├── tests/
├── config.yaml
└── README.md
"""

# Configuration management
import yaml

with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Access parameters
crs = config['projection']['output_crs']
resolution = config['data']['resolution']
```

### Performance Optimization

```python
# Memory profiling
import memory_profiler

@memory_profiler.profile
def process_large_dataset(data_path):
    """Profile memory usage."""
    data = load_data(data_path)
    result = process(data)
    return result

# Vectorization vs loops
# BAD: Iterating rows
for idx, row in gdf.iterrows():
    gdf.loc[idx, 'buffer'] = row.geometry.buffer(100)

# GOOD: Vectorized
gdf['buffer'] = gdf.geometry.buffer(100)

# Chunked processing
def process_in_chunks(gdf, func, chunk_size=1000):
    """Process GeoDataFrame in chunks."""
    results = []
    for i in range(0, len(gdf), chunk_size):
        chunk = gdf.iloc[i:i+chunk_size]
        result = func(chunk)
        results.append(result)
    return pd.concat(results)
```

For more code examples, see [code-examples.md](code-examples.md).

Sources: [SciPy MILP](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html), [PyKrige](https://geostat-framework.readthedocs.io/projects/pykrige/en/stable/generated/pykrige.ok.OrdinaryKriging.html), [NetworkX TSP](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.approximation.traveling_salesman.traveling_salesman_problem.html), [GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html).
