# Visualization (pymoo 0.6.2)

Plot finite feasible objective arrays after checking for `result.F is None`.
Plots show approximations and trade-offs; visual proximity does not prove
convergence. A 2D projection can conceal dominance relationships in higher
objective dimensions. All objectives supplied to the optimizer are minimized;
label any sign reversal back to physical units explicitly.

The snippets below share synthetic data and were rendered with Matplotlib's Agg
backend. Replace `F` only after validating the candidate set and common bounds.

```python
import numpy as np
F = np.array([[0.0, 1.0, 0.6], [0.5, 0.5, 0.3], [1.0, 0.0, 0.1]])
bounds = [np.zeros(3), np.ones(3)]
labels = ["Cost", "Mass", "Error"]
```

## Scatter and parallel coordinates

```python
from pymoo.visualization.scatter import Scatter
from pymoo.visualization.pcp import PCP

scatter = Scatter(title="Candidate objectives", labels=labels, legend=True)
scatter.add(F, label="Candidates", color="blue", alpha=0.6)
scatter.save("candidates.png", dpi=150)

pcp = PCP(bounds=bounds, labels=labels, normalize_each_axis=True)
pcp.add(F, color="blue", alpha=0.5)
pcp.save("parallel_coordinates.png", dpi=150)
```

Scatter uses 2D or 3D according to input columns, and pairwise panels for more
than three objectives. Legends default to False: request `legend=True`. Use
`plot_type="line"` when connecting a sorted analytic front; do not connect across
a disconnected front. PCP normalization changes the visual scale, not the data's
scientific meaning. Use shared fixed bounds when comparing runs.

## Heatmap

```python
from pymoo.visualization.heatmap import Heatmap
heatmap = Heatmap(bounds=bounds, labels=labels, cmap="Blues",
                  order_by_objectives=0, reverse=True)
heatmap.add(F)
heatmap.save("objective_values.png", dpi=150)
```

Rows are solutions and columns are objectives. Cell color represents a normalized
**objective value**, not a binned solution density. There is no `bins` constructor
parameter. Only one matrix may be added to a Heatmap; stack comparable candidate
matrices first and retain source labels. `reverse=True` makes lower values darker
under the default Blues colormap. For actual density, use a separately defined
histogram with a documented binning rule.

## Petal, radar, Radviz, and star coordinates

```python
from pymoo.visualization.petal import Petal
from pymoo.visualization.radar import Radar
from pymoo.visualization.radviz import Radviz
from pymoo.visualization.star_coordinate import StarCoordinate

petal = Petal(bounds=bounds, labels=labels, reverse=True)
petal.add(F[:2])
petal.save("petal.png", dpi=150)
radar = Radar(bounds=bounds, labels=labels)
radar.add(F[:2])
radar.save("radar.png", dpi=150)
Radviz(bounds=bounds, labels=labels).add(F).save("radviz.png", dpi=150)
StarCoordinate(bounds=bounds, labels=labels).add(F).save("star.png", dpi=150)
```

Petal requires explicit bounds. Its `reverse` flag reverses all normalized
objectives, not a separate arbitrary direction per objective; make any mixed
orientation transform explicitly. Petal creates panels rather than overlaid
polygons for multiple solutions. Set positive spans or resolve constant columns
before interpreting radial or normalized views. Radviz/star projection positions
are descriptive; their clusters and distances do not certify Pareto quality.

## Convergence and animation

Use callback traces for scalar time/evaluation/indicator histories. If the
optimization used `save_history=True`, each `result.history` item is an algorithm
snapshot. Valid indices run from 0 to `len(result.history)-1`, not through
`result.algorithm.n_gen`.

```python
# Context-dependent: result is a completed MOO run with save_history=True.
plot = Scatter(title="Approximation over generations", legend=True)
indices = np.unique(np.linspace(0, len(result.history) - 1, 4, dtype=int))
for index in indices:
    entry = result.history[index]
    feasible = entry.opt.get("FEAS").ravel()
    if feasible.any():
        plot.add(entry.opt.get("F")[feasible], alpha=0.4,
                 label=f"Generation {entry.n_gen}")
plot.save("convergence.png", dpi=150)
```

For animations upstream uses optional `pyrecorder.recorder.Recorder` with
`pyrecorder.writers.video.Video`, recording plots inside the writer context.
There is no `pymoo.visualization.video.Video(result.algorithm)` interface.
Follow the [video guide](https://pymoo.org/visualization/video.html) and validate the
selected writer/codec on the target machine. Video encoding and interactive
streaming were not executed in this refresh; static plots were.

Sources reviewed 2026-10-01: [visualization](https://pymoo.org/visualization/index.html),
[Heatmap](https://pymoo.org/visualization/heatmap.html),
[Petal](https://pymoo.org/visualization/petal.html), and released plotting source.
