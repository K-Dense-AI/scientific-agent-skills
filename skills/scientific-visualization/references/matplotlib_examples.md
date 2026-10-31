# Current Matplotlib, Seaborn, and Plotly Patterns

Verified 2026-10-01 against Matplotlib 3.11.2, Seaborn 0.13.2, Plotly 7.1.0, Kaleido 1.4.0, Pillow 12.3.0, and pypdf 6.19.0. Source IDs resolve in `sources.md`.

Run examples from the skill directory with pinned direct dependencies:

```bash
uv run --isolated --no-project --python 3.13 \
  --with "matplotlib==3.11.2" \
  --with "seaborn==0.13.2" \
  --with "plotly==7.1.0" \
  --with "kaleido==1.4.0" \
  --with "pillow==12.3.0" \
  --with "pypdf==6.19.0" \
  python your_figure.py
```

These pins are a dated direct-dependency snapshot, not a lock of all transitive artifacts. Keep a lock in the consuming project for exact replay. The snippets share imports/variables: supply your scientific `frame`, `x`, and `y`. They were exercised with synthetic fixtures; they do not validate an analysis of your data.

Start `your_figure.py` with this bootstrap when running from the skill directory:

```python
from pathlib import Path
import sys

skill_root = Path.cwd()
sys.path[:0] = [str(skill_root / "scripts"), str(skill_root / "assets")]
Path("outputs").mkdir(exist_ok=True)
```

## Rendering and hardcopy backends

Matplotlib separates interactive display backends from hardcopy renderers. The current built-ins include PDF (`pdf`), PS (`ps`, `eps`), SVG (`svg`), PGF (`pgf`, `pdf` through TeX), and optional Cairo (`png`, `ps`, `pdf`, `svg`); Agg is the common raster renderer [MPL-BACKENDS]. JPEG, TIFF, and WebP saving uses Pillow through the raster path.

Available output depends on the active backend/build:

```python
supported = fig.canvas.get_supported_filetypes()
print(supported)
```

`Figure.savefig(..., backend="cairo")` or `backend="pgf"` can select another renderer, but Matplotlib documents the default as normally sufficient [MPL-SAVE]. PGF requires a working TeX setup; Cairo requires pycairo or cairocffi. Inspect output because a vector container can still contain rasterized artists.

## Scoped style and exact dimensions

Prefer temporary style contexts to global state:

```python
import matplotlib.pyplot as plt

from style_presets import style_context

with style_context("default", palette_name="okabe_ito_on_white"):
    fig, ax = plt.subplots(
        figsize=(89 / 25.4, 60 / 25.4),
        layout="constrained",
    )
    ax.plot([0, 1, 2], [1, 3, 2], marker="o", label="Observed")
    ax.set(xlabel="Time (hours)", ylabel="Response (unit)")
    ax.legend()
```

`layout="constrained"` handles labels, legends, nested layouts, and colorbars more flexibly than `tight_layout`; calling `tight_layout()` turns constrained layout off [MPL-LAYOUT].

If exact page dimensions matter, do not export with `bbox_inches="tight"`; it recalculates the bounding box and changes the physical output size [MPL-SAVE].

You can also use the bundled parseable style:

```python
from pathlib import Path
import matplotlib.pyplot as plt

skill_root = Path(".")  # run from the skill directory
with plt.style.context(skill_root / "assets" / "publication.mplstyle"):
    fig, ax = plt.subplots(layout="constrained")
```

## Preserve raw observations and define uncertainty

```python
import numpy as np
import matplotlib.pyplot as plt

rng = np.random.default_rng(20260723)
groups = {
    "Control": rng.normal(0.0, 1.0, 24),
    "Treatment": rng.normal(0.7, 1.1, 24),
}

fig, ax = plt.subplots(figsize=(3.5, 2.8), layout="constrained")
for position, (label, values) in enumerate(groups.items()):
    jitter = rng.uniform(-0.08, 0.08, len(values))
    ax.scatter(
        position + jitter,
        values,
        alpha=0.65,
        label=label,
    )
    mean = values.mean()
    sem = values.std(ddof=1) / np.sqrt(len(values))
    ax.errorbar(position, mean, yerr=sem, color="black", capsize=3)

ax.set(
    xticks=range(len(groups)),
    xticklabels=list(groups),
    ylabel="Response (unit)",
)
```

Caption the error bars as mean ± one SEM and state `n=24` independent observations per group. If independence is false, use an analysis and interval that respects the design.

## Missing data and no silent interpolation

```python
import numpy as np

time = np.arange(8)
signal = np.array([1.0, 1.4, np.nan, np.nan, 2.1, 2.0, 2.4, 2.7])

fig, ax = plt.subplots(layout="constrained")
ax.plot(time, signal, marker="o", label="Observed")  # gaps remain gaps
ax.scatter(
    [2, 3], [0.04, 0.04], transform=ax.get_xaxis_transform(),
    marker="x", color="0.35", label="Missing (axis strip)",
)
ax.set(xlabel="Time (days)", ylabel="Signal (unit)")
ax.legend()
```

If a model estimates the missing interval, plot the model separately with its uncertainty and identify it as modeled, not observed.

## Log axes and explicit nonpositive policy

```python
import numpy as np
import matplotlib.pyplot as plt

concentration = np.array([0.1, 1.0, 10.0, 100.0])
response = np.array([0.4, 0.9, 2.1, 4.3])

fig, ax = plt.subplots(layout="constrained")
ax.plot(concentration, response, marker="o")
ax.set_xscale("log", base=10)
ax.set(xlabel="Concentration (µM; log10 axis)", ylabel="Response (unit)")
```

Do not silently omit zeros or negatives. State the measurement-domain rule or use another representation.

## Centered heatmap and missing-value color

```python
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

values = np.array([
    [-2.0, -0.5, 0.1],
    [-1.1, np.nan, 1.8],
    [-0.2, 0.7, 3.0],
])
norm = mpl.colors.TwoSlopeNorm(vmin=-2, vcenter=0, vmax=3)
cmap = mpl.colormaps["RdBu_r"].with_extremes(bad="#777777")

fig, ax = plt.subplots(layout="constrained")
image = ax.imshow(values, norm=norm, cmap=cmap, interpolation="nearest")
colorbar = fig.colorbar(image, ax=ax)
colorbar.set_label("Change from baseline (unit)")
ax.set(xlabel="Sample", ylabel="Feature")
```

`TwoSlopeNorm` gives each side of the center a different linear mapping. Use `CenteredNorm` when symmetric treatment around a center is appropriate, `LogNorm` for strictly positive orders of magnitude, and `BoundaryNorm` for declared classes [MPL-NORM].

## Multi-panel layout

```python
import matplotlib.pyplot as plt

fig = plt.figure(figsize=(7.0, 4.0), layout="constrained")
subfigures = fig.subfigures(1, 2, width_ratios=[2, 1])
left_axes = subfigures[0].subplots(2, 1, sharex=True)
right_ax = subfigures[1].subplots()

for label, ax in zip("ABC", [*left_axes, right_ax]):
    ax.text(
        -0.12,
        1.05,
        label,
        transform=ax.transAxes,
        fontweight="bold",
        va="top",
    )
```

`GridSpec`, subgrids, `subplot_mosaic`, and subfigures all work with constrained layout [MPL-LAYOUT] [MPL-GRIDSPEC].

## Selective rasterization in vector output

Dense point clouds can make PDF/SVG huge. Rasterize only the dense artist:

```python
fig, ax = plt.subplots(layout="constrained")
ax.scatter(x, y, s=2, alpha=0.25, rasterized=True)
ax.set(xlabel="Predictor (unit)", ylabel="Outcome (unit)")

from figure_export import export_figure

report = export_figure(
    fig,
    "outputs/figure1",
    formats=["pdf", "png"],
    dpi=600,  # controls PNG and rasterized artists embedded in PDF
    provenance={
        "raw_data": "data/observations.csv",
        "transformations": ["rows filtered by predeclared QC flag"],
        "uncertainty": "none displayed",
        "missing_data": "retained as gaps",
    },
    write_manifest=True,
)
```

The exporter:

- refuses implicit overwrite;
- preserves page dimensions by default;
- passes DPI to vector backends for embedded raster artists;
- writes TIFF with LZW compression;
- can keep TrueType text editable in PDF/PS;
- can write an explicit provenance manifest.

It does not inspect data truth or certify submission compliance.

## Raster image export and inspection

```python
report = export_figure(
    fig,
    "outputs/microscopy_panel",
    formats=["tiff"],
    tiff_rgb=True,  # remove alpha only after verifying every rendered pixel is opaque
    dpi=300,
    facecolor="white",
    overwrite=False,
)
```

Then inspect:

```bash
uv run --isolated --no-project --python 3.13 \
  --with "pillow==12.3.0" \
  python scripts/image_metadata.py outputs/microscopy_panel.tiff \
  --format tiff --mode RGB --min-dpi 300 --target-width-mm 85 \
  --alpha-policy forbid
```

Effective DPI is pixel width divided by final width in inches. Changing only the TIFF DPI tag does not create detail.

## Seaborn 0.13.2

Seaborn remains built on Matplotlib. Use axes-level functions for custom multi-panel layouts and figure-level functions for automatic faceting [SEABORN-FAQ].

```python
import seaborn as sns
import matplotlib.pyplot as plt

from color_palettes import OKABE_ITO_ON_WHITE
from style_presets import style_context

sns.set_theme(style="ticks", context="paper", palette=OKABE_ITO_ON_WHITE)
with style_context("default", palette_name="okabe_ito_on_white"):
    fig, ax = plt.subplots(figsize=(3.5, 2.8), layout="constrained")
    sns.lineplot(
        data=frame,
        x="time",
        y="response",
        hue="treatment",
        style="treatment",
        markers=True,
        errorbar=("ci", 95),
        n_boot=5000,
        seed=20260723,
        ax=ax,
    )
    ax.set(xlabel="Time (hours)", ylabel="Response (unit)")
```

Seaborn line plots can drop rows with missing values and join the remaining points. Use the explicit Matplotlib gap example above when gaps carry scientific meaning.

Current `errorbar` choices include `"sd"`, `"se"`, `"pi"`, `"ci"`, tuples, callables, or `None`. The old `ci=` interface is not the current general API [SEABORN-ERROR].

For categorical axes whose numeric/datetime values must retain their real spacing, use supported functions with `native_scale=True`. Do not assume every categorical plot uses native coordinates by default.

## Plotly 7.1 and Kaleido 1.4

Interactive HTML (the supplied `fig` here is a Plotly figure):

```python
fig.write_html(
    "outputs/exploration.html",
    include_plotlyjs=True,  # self-contained, larger file
    full_html=True,
    config={"modeBarButtonsToRemove": ["shareChart"]},
)
```

Static image:

```python
fig.write_image(
    "outputs/figure.svg",
    width=700,
    height=450,
    scale=1,
)
```

Batch export is faster with Kaleido v1:

```python
import plotly.io as pio

pio.write_images(
    fig=[figure_a, figure_b],
    file=["outputs/a.pdf", "outputs/b.pdf"],
)
```

Current facts [PLOTLY-STATIC] [PLOTLY-7] [KALEIDO]:

- Kaleido v1 requires a compatible Chrome/Chromium installation; Chrome is no longer bundled.
- Plotly `write_image` supports PNG, JPEG, WebP, SVG, and PDF.
- EPS was supported only by Kaleido versions earlier than 1.0.
- `engine=` and Orca are removed in Plotly 7. Kaleido <1 is unsupported.
- `plotly.io.kaleido.scope` is removed; use `plotly.io.defaults`. MathJax must be version 3 or 4.
- Width/height are logical pixels and `scale` multiplies output pixels; `scale=3` is **not inherently “300 DPI.”**
- WebGL traces embed raster content inside vector exports.
- Fully offline MathJax/topojson use requires local resources; do not assume a network-independent export when a figure references external assets.

Plotly 7 adds a Share Chart modebar button; remove it when a local deliverable should not offer upload/sharing. Embedding Plotly.js does not package externally referenced tiles, images, MathJax, or topojson.

An interactive HTML file does not replace a static fallback, caption, alt text, keyboard review, or accessible data table.

## Font and transparency checks

Matplotlib 3.11.2 defaults PDF/PS to Type 3 and SVG text to paths. The bundled presets instead use PDF/PS Type 42 and leave SVG text as text [MPL-STYLE]. Verify the actual PDF:

```bash
uv run --isolated --no-project --python 3.13 \
  --with "pypdf==6.19.0" \
  python scripts/image_metadata.py outputs/figure1.pdf
```

SVG text is not an embedded font; its appearance depends on the renderer’s installed fonts. If portability matters more than editable/searchable text, use paths and retain an editable source separately.

Use opaque white submission output unless transparency is explicitly required. Transparent artists blend with the destination and can change apparent contrast [MPL-SAVE].
