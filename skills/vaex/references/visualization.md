# Visualization without full-data arrays

Vaex can aggregate all eligible rows into a small grid; resolution and range still
hide within-bin detail and excluded observations. A density plot is not a lossless
representation. Sources: [Vaex plotting](https://vaex.io/docs/guides/advanced_plotting.html)
and [Matplotlib API removal](https://matplotlib.org/stable/api/prev_api_changes/api_changes_3.9.0.html).

## Current compatibility and supported names

`df.viz.histogram`, `df.viz.heatmap`, and `df.viz.scatter` are the supported accessor
names. `plot1d`/`plot` are deprecated aliases. Use `what='mean(z)'`, `'std(z)'`,
`'sum(z)'`, or `'count(*)'`; calling `df.z.mean()` first produces a scalar, not a
binned statistic instruction. A 1D histogram uses `.histogram`, not a one-axis heatmap.

**Verified limitation:** core 4.19.0's default heatmap reduction calls removed
`matplotlib.cm.get_cmap`, raising `AttributeError` under Matplotlib 3.11.2. An old
plotting environment may run it, but was not tested here. Use the executed grid
recipe below with current Matplotlib; do not patch global Matplotlib functions silently.
The high-level heatmap also does not accept generic `ax=`, `dpi=`, or `alpha=` kwargs.

## Histogram and bounded scatter

```python
import numpy as np
import vaex
import matplotlib.pyplot as plt

rng = np.random.default_rng(7)
x = rng.normal(size=1000)
y = 0.5 * x + rng.normal(size=1000)
df = vaex.from_arrays(x=x, y=y, z=x + y)
plt.figure(figsize=(6, 4))
df.viz.histogram('x', limits=[-4, 4], shape=32, show=False,
                 xlabel='x (arbitrary units)', ylabel='Count')
plt.savefig('vaex-histogram.png', dpi=120, bbox_inches='tight')
plt.close()
sample = df.sample(n=100, random_state=7)
plt.figure(figsize=(6, 4))
sample.viz.scatter('x', 'y', s=8, alpha=0.6)
plt.xlabel('x (arbitrary units)')
plt.ylabel('y (arbitrary units)')
plt.savefig('vaex-scatter.png', dpi=120, bbox_inches='tight')
plt.close()
```

Always bound rows before conversion: `df[:1000].x.to_numpy()`, not
`df.x.values[:1000]`, which evaluates the full column first. A scatter plot is a
sample; state how it was selected. Higher image DPI does not add information to a grid.

## Count and mean grids with correct coordinates

```python
limits = [[-4., 4.], [-4., 4.]]
shape = (32, 24)  # x bins, y bins
count_task = df.count(binby=['x', 'y'], limits=limits, shape=shape, delay=True)
mean_task = df.mean('z', binby=['x', 'y'], limits=limits, shape=shape, delay=True)
df.execute()
counts, means = count_task.get(), mean_task.get()
in_range = ((df.x >= -4) & (df.x < 4) & (df.y >= -4) & (df.y < 4))
retained = int(df.count(selection=in_range))
assert int(counts.sum()) == retained
x_edges = np.linspace(*limits[0], shape[0] + 1)
y_edges = np.linspace(*limits[1], shape[1] + 1)
fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
count_image = axes[0].pcolormesh(x_edges, y_edges, np.log10(counts.T + 1),
                                 shading='flat', cmap='viridis')
mean_image = axes[1].pcolormesh(x_edges, y_edges, np.ma.masked_where(counts.T == 0, means.T),
                                shading='flat', cmap='coolwarm')
fig.colorbar(count_image, ax=axes[0], label='log10(count + 1)')
fig.colorbar(mean_image, ax=axes[1], label='Mean z (arbitrary units)')
for ax in axes:
    ax.set(xlabel='x (arbitrary units)', ylabel='y (arbitrary units)')
axes[0].set_title(f'Count: {retained}/{len(df)} rows within limits')
axes[1].set_title('Mean z; empty bins masked')
fig.savefig('vaex-grids.png', dpi=120, bbox_inches='tight')
plt.close(fig)
```

Vaex grid order follows `binby`: transpose for plotting rows=y, columns=x.
`pcolormesh` receives edges. For contours/quiver compute centers as
`(edges[:-1] + edges[1:]) / 2`; endpoints are not centers. Supply the same grid/limits
to every layer. Mean vectors show averaged components, not individually observed paths.

`limits='99.7%'` is a percentile range, not a universal three-standard-deviation or
confidence interval rule. Report exclusions; use prespecified/common limits and color
scales for comparisons. Means in sparsely populated bins may be unstable: retain counts
and mask according to a justified count threshold. Show zero counts distinctly from
missing means. Saving PDF/SVG does not make raster heatmap cells infinite-resolution data.

## Notebook interactivity: illustrative only

Optional `vaex-jupyter` 0.9.0 registers `df.widget`; current source exposes:

```python
import vaex.jupyter
histogram_widget = df.widget.histogram('x', limits=[-4, 4])
heatmap_widget = df.widget.heatmap('x', 'y', limits=[[-4, 4], [-4, 4]], shape=64)
selection_widget = df.widget.selection_expression(initial_value='x > 0')
```

These widgets require a functioning Jupyter frontend and its compatible widget
extensions; source verification is not browser interaction testing. The old
`plot_widget`/`scatter_widget` examples are not this accessor's current contract.
For Plotly/other renderers, send only the aggregated grid plus centers/edges and
coverage metadata; do not materialize the entire DataFrame to make a heatmap.
