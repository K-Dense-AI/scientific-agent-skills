# Praxis — Plot Types Reference

## 2D Plots

### Line
```python
plot_data(x, y, kind="line")
plot_data(x, y, kind="line", marker="o", linestyle="--")
```

### Scatter
```python
plot_data(x, y, kind="scatter")
plot_data(x, y, kind="scatter", marker="s", s=30)
```

### Bar (vertical)
```python
plot_data(categories, values, kind="bar")
plot_data(x, y, kind="bar", width=0.5)
```

### Bar (horizontal)
```python
plot_data(categories, values, kind="bar_h")
```

### Step
```python
plot_data(x, y, kind="step")
plot_data(x, y, kind="step", where="pre")  # pre, mid, post
```

### Area
```python
plot_data(x, y, kind="area")
plot_data(x, y, kind="area", alpha=0.3)
```

### Error bars
```python
plot_data(x, y, kind="errorbar", yerr=y_err)
plot_data(x, y, kind="errorbar", xerr=x_err, yerr=y_err, capsize=4)
```

### Fill between
```python
plot_data(x, y, kind="fill_between", y2=y_lower)
```

### Histogram
```python
plot_data(None, values, kind="histogram", bins=30)
```

## Contour and Heatmap

### Filled contour
```python
plot_contour(X, Y, Z, kind="filled", levels=20, cmap="viridis")
```

### Line contour
```python
plot_contour(X, Y, Z, kind="line", levels=10)
```

### Heatmap
```python
plot_contour(x, y, Z, kind="heatmap", cmap="plasma")
```

## Multi-Dataset Overlay

```python
overlay_plots([
    {"x": x1, "y": y1, "label": "Sample A", "kind": "line"},
    {"x": x2, "y": y2, "label": "Sample B", "kind": "line"},
    {"x": x3, "y": y3, "label": "Sample C", "kind": "scatter"},
], xlabel="2θ (°)", ylabel="Intensity (a.u.)")
```

## Subplot Grid

```python
fig, axes = create_subplots(2, 2, figsize=(7, 6))
plot_data(x, y, fig=fig, ax=axes[0, 0], title="Panel (a)")
```

## Specialised Plots

### Nyquist (impedance)
```python
from techniques.impedance import plot_nyquist
plot_nyquist(data, fit=fit_result)
```

### Bode (impedance)
```python
from techniques.impedance import plot_bode
plot_bode(data, fit=fit_result)
```

## Common Options

| Option | Values | Default |
|--------|--------|---------|
| `palette` | `"okabe_ito"`, `"tol_bright"`, `"tol_muted"` | `"default"` (Okabe-Ito) |
| `log_x`, `log_y` | `True`/`False` | `False` |
| `invert_x`, `invert_y` | `True`/`False` | `False` |
| `grid` | `True`/`False` | `False` |
| `xlim`, `ylim` | `(min, max)` tuple | auto |
| `figsize` | `(width, height)` in inches | varies by style |
| `legend` | `True`/`False` | `True` |
