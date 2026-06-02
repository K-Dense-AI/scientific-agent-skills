# cuxfilter Reference

cuxfilter is a GPU-accelerated cross-filtering dashboard library from the NVIDIA RAPIDS ecosystem. It enables interactive, multi-chart exploratory data analysis dashboards from Jupyter notebooks in just a few lines of Python. All filtering, groupby, and aggregation operations happen on the GPU via cuDF, with only the visualization results sent to the browser.

> **Full documentation:** https://docs.rapids.ai/api/cuxfilter/stable/
> **Version (stable):** 26.02.00
> **Repository:** https://github.com/rapidsai/cuxfilter

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [Core Concepts](#core-concepts)
3. [DataFrame: Loading Data](#dataframe-loading-data)
4. [Charts](#charts)
5. [Widgets](#widgets)
6. [Dashboard Creation](#dashboard-creation)
7. [Layouts](#layouts)
8. [Themes](#themes)
9. [Dashboard Display and Export](#dashboard-display-and-export)
10. [Graph Visualization](#graph-visualization)
11. [Multi-GPU with Dask-cuDF](#multi-gpu-with-dask-cudf)
12. [Interoperability](#interoperability)
13. [Performance Tips](#performance-tips)
14. [Common Patterns](#common-patterns)

---

## Installation and Setup

Always use `uv add` (never `pip install` or `conda install`) in all install instructions, docstrings, comments, and error messages.

```bash
uv add --extra-index-url=https://pypi.nvidia.com cuxfilter-cu12   # For CUDA 12.x
```

cuxfilter depends on cuDF, so `cudf-cu12` will be pulled in automatically.

**Platform:** Linux and WSL2 only (no native macOS or Windows).
**Requires:** NVIDIA GPU with CUDA 12.x support.

Verify:
```python
import cuxfilter
import cudf

df = cudf.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
cux_df = cuxfilter.DataFrame.from_dataframe(df)
print(cux_df.data.head())  # Should print GPU dataframe
```

---

## Core Concepts

cuxfilter has five main modules:

1. **`cuxfilter.DataFrame`** — Wraps a cuDF DataFrame for dashboard use. Entry point for creating dashboards.
2. **`cuxfilter.DashBoard`** — The interactive dashboard object. Created from a DataFrame with charts.
3. **`cuxfilter.charts`** — Chart factory functions (bar, scatter, line, heatmap, choropleth, graph, widgets).
4. **`cuxfilter.layouts`** — Preset and custom layout configurations for chart arrangement.
5. **`cuxfilter.themes`** — Visual themes for dashboards (default, dark, rapids, rapids_dark).

The workflow is always: **Load data → Create charts → Build dashboard → Display**.

---

## DataFrame: Loading Data

The `cuxfilter.DataFrame` is the starting point. It wraps a cuDF or dask_cudf DataFrame.

### From a cuDF DataFrame (most common)
```python
import cudf
import cuxfilter

cudf_df = cudf.DataFrame({
    "x": [0, 1, 2, 3, 4],
    "y": [10.0, 11.0, 12.0, 13.0, 14.0],
    "category": ["A", "B", "A", "B", "A"]
})
cux_df = cuxfilter.DataFrame.from_dataframe(cudf_df)
```

### From an Arrow file on disk
```python
cux_df = cuxfilter.DataFrame.from_arrow("data/my_dataset.arrow")
```

### From a graph (nodes + edges)
```python
import cugraph

edges = cudf.DataFrame({"source": [0, 1, 2], "target": [1, 2, 3], "weight": [1.0, 2.0, 3.0]})
G = cugraph.Graph()
G.from_cudf_edgelist(edges, destination="target")
cux_df = cuxfilter.DataFrame.load_graph((G.nodes(), G.edges()))
```

Or directly from cuDF DataFrames:
```python
nodes = cudf.DataFrame({"vertex": [0, 1, 2, 3], "x": [0, 1, 2, 3], "y": [4, 4, 2, 6], "attr": [0, 1, 1, 1]})
edges = cudf.DataFrame({"source": [0, 1, 2], "target": [1, 2, 3], "weight": [1.0, 2.0, 3.0]})
cux_df = cuxfilter.DataFrame.load_graph((nodes, edges))
```

### Accessing the underlying data
```python
cux_df.data  # The cuDF DataFrame
cux_df.data["new_col"] = cux_df.data["x"] * 2  # Add columns before creating dashboard
```

---

## Charts

All chart functions are accessed via `cuxfilter.charts`. They use the top-level shorthand — you do NOT need to import submodules like `cuxfilter.charts.bokeh` or `cuxfilter.charts.datashader` directly.

### Bar Chart (Bokeh)
```python
chart = cuxfilter.charts.bar(
    x="column_name",           # Required: x-axis column
    y=None,                    # Optional: y-axis column (defaults to count)
    data_points=None,          # Number of bins (None = nunique)
    add_interaction=True,      # Enable cross-filtering interaction
    aggregate_fn="count",      # 'count' or 'mean'
    step_size=None,            # Step size for range slider
    title="",                  # Chart title
    autoscaling=True,          # Auto-scale y-axis on data update
)
```

### Line Chart (Bokeh)
```python
chart = cuxfilter.charts.line(
    x="x_col",
    y="y_col",
    data_points=100,
    add_interaction=True,
)
```

### Scatter Plot (Datashader — handles millions of points)
```python
chart = cuxfilter.charts.scatter(
    x="x_col",
    y="y_col",
    aggregate_col=None,              # Column for color aggregation
    aggregate_fn="count",            # 'count', 'mean', 'max', 'min'
    color_palette=None,              # Bokeh palette or list of hex colors
    point_size=15,
    pixel_shade_type="eq_hist",      # 'eq_hist', 'linear', 'log', 'cbrt'
    pixel_density=0.5,               # [0, 1], higher = denser
    pixel_spread="dynspread",        # 'dynspread' or 'spread'
    tile_provider=None,              # Map tile (e.g., "CartoLight" for geo data)
    title="",
    unselected_alpha=0.2,            # Transparency of unselected points
)
```

### Heatmap (Datashader)
```python
chart = cuxfilter.charts.heatmap(
    x="x_col",
    y="y_col",
    aggregate_col="value_col",
    aggregate_fn="mean",             # 'count', 'mean', 'max', 'min'
    color_palette=None,
    point_size=10,
    point_shape="rect_vertical",     # 'circle', 'square', 'rect_vertical', 'rect_horizontal'
    title="",
)
```

### Stacked Lines (Datashader)
```python
chart = cuxfilter.charts.stacked_lines(
    x="time_col",
    y=["series_a", "series_b", "series_c"],   # List of y columns
    colors=["red", "green", "blue"],
)
```

### Choropleth (Deck.gl — 2D and 3D maps)
```python
chart = cuxfilter.charts.choropleth(
    x="zip_code",
    color_column="metric_col",
    color_aggregate_fn="mean",         # 'count', 'mean', 'sum', 'min', 'max', 'std'
    elevation_column="value_col",      # Set for 3D choropleth, omit for 2D
    elevation_factor=0.00001,
    elevation_aggregate_fn="sum",
    geoJSONSource="https://url/to/geojson",
    geo_color_palette=None,            # Default: Inferno256
    nan_color="#d3d3d3",
    tooltip=True,
    tooltip_include_cols=["zip_code", "metric_col"],
    title="",
)
```

### Graph (Datashader — node-link diagrams)
```python
chart = cuxfilter.charts.datashader.graph(
    node_x="x",                  # Default "x"
    node_y="y",                  # Default "y"
    node_id="vertex",            # Default "vertex"
    edge_source="source",        # Default "source"
    edge_target="target",        # Default "target"
    node_aggregate_col=None,
    node_color_palette=None,
    edge_color_palette=["#000000"],
    node_point_size=15,
    node_pixel_shade_type="eq_hist",
    edge_render_type="direct",   # 'direct' or 'curved' (curved is experimental)
    edge_transparency=0,         # [0, 1]
    tile_provider=None,
    title="",
    unselected_alpha=0.2,
)
```

---

## Widgets

Widgets provide interactive filtering controls, typically placed in the sidebar.

### Range Slider
```python
widget = cuxfilter.charts.range_slider("numeric_col", step_size=1)
```

### Date Range Slider
```python
widget = cuxfilter.charts.date_range_slider("datetime_col")
```

### Float Slider
```python
widget = cuxfilter.charts.float_slider("float_col", step_size=0.5)
```

### Int Slider
```python
widget = cuxfilter.charts.int_slider("int_col", step_size=1)
```

### Dropdown
```python
widget = cuxfilter.charts.drop_down("category_col")
```

### Multi-Select
```python
widget = cuxfilter.charts.multi_select("category_col")
```

### Number (KPI indicator)
```python
widget = cuxfilter.charts.number(
    expression="column_name",                # Or a computed expression like "(x + y) / 2"
    aggregate_fn="mean",                     # 'count', 'mean', 'min', 'max', 'sum', 'std'
    title="Average Value",
    format="{value:.2f}",                    # Python format string
    colors=[(33, "green"), (66, "gold"), (100, "red")],  # Threshold coloring
    font_size="18pt",
)
```

### Card (Markdown content)
```python
import panel as pn
widget = cuxfilter.charts.card(pn.pane.Markdown("## My Dashboard\nSome description text"))
```

---

## Dashboard Creation

Create a dashboard by calling `.dashboard()` on a cuxfilter DataFrame:

```python
# Define charts and widgets
chart1 = cuxfilter.charts.scatter(x="x_col", y="y_col")
chart2 = cuxfilter.charts.bar("category_col")
sidebar_widget = cuxfilter.charts.range_slider("value_col")
number_widget = cuxfilter.charts.number(expression="value_col", aggregate_fn="mean", title="Mean Value")

# Build dashboard
d = cux_df.dashboard(
    charts=[chart1, chart2],               # Main area charts
    sidebar=[sidebar_widget, number_widget],  # Sidebar widgets
    layout=cuxfilter.layouts.feature_and_base,
    theme=cuxfilter.themes.rapids_dark,
    title="My Dashboard",
    data_size_widget=True,                 # Show current data count
)
```

### Adding charts after creation
```python
new_chart = cuxfilter.charts.line("x_col", "y_col")
d.add_charts(charts=[new_chart])
# or
d.add_charts(sidebar=[cuxfilter.charts.card(pn.pane.Markdown("# Note"))])
```

---

## Layouts

### Preset Layouts

| Layout | Description | Charts |
|--------|-------------|--------|
| `layouts.single_feature` | One chart fills the page | 1 |
| `layouts.feature_and_base` | Large chart on top, smaller below (66/33 split) | 2 |
| `layouts.double_feature` | Two charts side-by-side | 2 |
| `layouts.left_feature_right_double` | One large left, two stacked right | 3 |
| `layouts.triple_feature` | Three charts in a row | 3 |
| `layouts.feature_and_double_base` | One large top, two below | 3 |
| `layouts.two_by_two` | 2x2 grid | 4 |
| `layouts.feature_and_triple_base` | One large top, three below | 4 |
| `layouts.feature_and_quad_base` | One large top, four below | 5 |
| `layouts.feature_and_five_edge` | One large center, five around | 6 |
| `layouts.two_by_three` | 2x3 grid | 6 |
| `layouts.double_feature_quad_base` | Two large top, four below | 6 |
| `layouts.three_by_three` | 3x3 grid | 9 |

### Custom Layouts with `layout_array`

Use `layout_array` for full control. It's a list-of-lists where each inner list is a row, and numbers refer to chart indices (1-based):

```python
# Chart 1 takes top-left 2x2 area, charts 2 and 3 on the right
d = cux_df.dashboard(
    charts_list,
    layout_array=[[1, 1, 2, 2], [1, 1, 3, 4]],
    theme=cuxfilter.themes.rapids_dark,
)
```

Rules:
- Each number maps to a chart (1 = first chart, 2 = second, etc.)
- Repeating a number across cells makes that chart span those cells
- The array is auto-scaled to fit the screen

---

## Themes

Four built-in themes:

| Theme | Description |
|-------|-------------|
| `cuxfilter.themes.default` | Light theme (default) |
| `cuxfilter.themes.dark` | Dark theme |
| `cuxfilter.themes.rapids` | RAPIDS-branded light theme |
| `cuxfilter.themes.rapids_dark` | RAPIDS-branded dark theme |

```python
d = cux_df.dashboard(charts, theme=cuxfilter.themes.rapids_dark)
```

---

## Dashboard Display and Export

### Display inline in a notebook
```python
d.app(sidebar_width=280, width=1200, height=800)
```

### Display as a separate web app (opens new browser tab)
```python
d.show()
# or with custom URL/port
d.show(notebook_url="http://localhost:8888", port=8050)
```

### JupyterHub deployment
```python
d.show(service_proxy="jupyterhub")
```

### Stop the server
```python
d.stop()
```

### Export filtered data
After interacting with the dashboard (selecting ranges, filtering), export the current filtered DataFrame:

```python
filtered_df = d.export()  # Returns cuDF DataFrame matching current filter state
# Also prints the query string, e.g.: "2 <= key <= 4"
```

### Access dashboard charts
```python
d.charts  # Dictionary of chart objects
```

---

## Graph Visualization

cuxfilter integrates with cuGraph for interactive graph visualization:

```python
import cuxfilter
import cudf
import cugraph

# Create graph
edges = cudf.DataFrame({
    "source": [0, 0, 1, 1, 2],
    "target": [1, 2, 2, 3, 3]
})
G = cugraph.Graph()
G.from_cudf_edgelist(edges, destination="target")

# Load into cuxfilter (needs node positions — use force_atlas2 or similar layout)
positions = cugraph.force_atlas2(G)
nodes = positions.rename(columns={"vertex": "vertex", "x": "x", "y": "y"})

cux_df = cuxfilter.DataFrame.load_graph((nodes, G.edges()))

# Create graph chart
chart = cuxfilter.charts.datashader.graph(
    node_pixel_shade_type="linear",
    unselected_alpha=0.2,
)

d = cux_df.dashboard([chart], layout=cuxfilter.layouts.single_feature)
d.app()
```

---

## Multi-GPU with Dask-cuDF

cuxfilter works seamlessly with `dask_cudf.DataFrame` — just pass it in place of a cuDF DataFrame:

```python
import dask_cudf

ddf = dask_cudf.read_parquet("large_dataset/*.parquet")
cux_df = cuxfilter.DataFrame.from_dataframe(ddf)

# Everything else is the same
chart = cuxfilter.charts.scatter(x="x", y="y")
d = cux_df.dashboard([chart])
d.app()
```

Use dask_cudf when:
- Data doesn't fit in a single GPU's memory
- You want to distribute across multiple GPUs
- Processing many files at once

**Supported chart types with dask_cudf:**
- bokeh: bar, line
- datashader: scatter, line, stacked_lines, heatmap, graph (limited edge rendering)
- panel_widgets: all widgets
- deckgl: choropleth (2D and 3D)

---

## Interoperability

cuxfilter sits at the visualization layer of the RAPIDS ecosystem:

- **cuDF** — The data layer. cuxfilter.DataFrame wraps cuDF DataFrames.
- **cuGraph** — Graph analytics. Use `cuxfilter.DataFrame.load_graph()` to visualize cuGraph results.
- **cuML** — Run cuML, then visualize results (e.g., UMAP embeddings, cluster assignments) with cuxfilter.
- **HoloViz ecosystem** — Built on Panel, Bokeh, Datashader, and HoloViews.
- **Deck.gl** — WebGL-powered choropleth maps.

### Typical RAPIDS + cuxfilter pipeline
```python
import cudf
import cuml
import cuxfilter

# Load and preprocess with cuDF
df = cudf.read_parquet("data.parquet")
df = df.dropna().reset_index(drop=True)

# Run ML with cuML (e.g., UMAP for dimensionality reduction)
from cuml.manifold import UMAP
umap = UMAP(n_components=2)
embedding = umap.fit_transform(df[["feature1", "feature2", "feature3"]])
df["umap_x"] = embedding[:, 0]
df["umap_y"] = embedding[:, 1]

# Visualize with cuxfilter
cux_df = cuxfilter.DataFrame.from_dataframe(df)
scatter = cuxfilter.charts.scatter(
    x="umap_x", y="umap_y",
    aggregate_col="cluster_label",
    aggregate_fn="mean",
    pixel_shade_type="linear",
)
bar = cuxfilter.charts.bar("cluster_label")
d = cux_df.dashboard([scatter, bar], layout=cuxfilter.layouts.feature_and_base)
d.app()
```

---

## Performance Tips

1. **Keep data on GPU.** Load with `cudf.read_parquet()` or `cudf.read_csv()`, then wrap with `cuxfilter.DataFrame.from_dataframe()`. Avoid converting to/from pandas.

2. **Use appropriate chart types for data size:**
   - < 10K points: Bokeh charts (bar, line) work well
   - 10K–100M+ points: Datashader charts (scatter, heatmap) handle large datasets efficiently via server-side rasterization

3. **Limit data_points for bar charts.** For columns with many unique values, set `data_points` to bin them (e.g., `bar("col", data_points=50)`).

4. **Use `float32` when possible.** GPU operations are faster with 32-bit floats. Cast before loading: `df["col"] = df["col"].astype("float32")`.

5. **Pre-compute derived columns** before creating the dashboard, not inside chart callbacks.

6. **Use `layout_array`** for complex dashboards to control exactly where each chart appears.

7. **Increase `timeout`** for datashader charts if zooming feels laggy on very large datasets.

---

## Common Patterns

### Exploratory data analysis dashboard
```python
import cudf
import cuxfilter

df = cudf.read_parquet("dataset.parquet")
cux_df = cuxfilter.DataFrame.from_dataframe(df)

# Overview charts
scatter = cuxfilter.charts.scatter(x="feature1", y="feature2", pixel_shade_type="linear")
hist1 = cuxfilter.charts.bar("feature1", data_points=50)
hist2 = cuxfilter.charts.bar("category")

# Sidebar filters
slider = cuxfilter.charts.range_slider("value_col")
dropdown = cuxfilter.charts.drop_down("category")
kpi = cuxfilter.charts.number(expression="value_col", aggregate_fn="mean", title="Mean Value")

d = cux_df.dashboard(
    [scatter, hist1, hist2],
    sidebar=[slider, dropdown, kpi],
    layout=cuxfilter.layouts.feature_and_double_base,
    theme=cuxfilter.themes.rapids_dark,
    title="Data Explorer",
)
d.app()
```

### Geospatial dashboard with scatter on map tiles
```python
chart = cuxfilter.charts.scatter(
    x="longitude",
    y="latitude",
    aggregate_col="value",
    aggregate_fn="mean",
    color_palette=["#3182bd", "#6baed6", "#ff0068"],
    tile_provider="CartoLight",
    pixel_shade_type="linear",
    title="Geo Scatter",
)
```

### Time series dashboard
```python
line_chart = cuxfilter.charts.line("timestamp", "metric")
bar_chart = cuxfilter.charts.bar("hour_of_day")
date_slider = cuxfilter.charts.date_range_slider("timestamp")

d = cux_df.dashboard(
    [line_chart, bar_chart],
    sidebar=[date_slider],
    layout=cuxfilter.layouts.feature_and_base,
)
```

### Export filtered subset for further analysis
```python
# After user interacts with dashboard, export current selection
d.app()
# ... user filters data in the dashboard ...
filtered = d.export()  # cuDF DataFrame of currently visible/selected data
# Continue analysis with cuDF, cuML, etc.
```
