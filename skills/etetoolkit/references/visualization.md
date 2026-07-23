# ETE 4 Visualization

ETE 4 has two drawing systems:

- **SmartView**: current web-based explorer and adaptive renderer; best for
  interactive work and very large trees
- **Treeview**: optional Qt renderer retained for static PNG, PDF, and SVG

Do not mix their layout or face classes. SmartView classes live under
`ete4.smartview`; Qt classes live under `ete4.treeview`.

## Renderer Decision

Use SmartView when:

- Exploring, searching, collapsing, or editing interactively
- Serving a tree locally or through an SSH tunnel
- Exploring from a long-lived Jupyter kernel through the browser
- Creating a raster PNG screenshot
- Manually downloading the current browser view as SVG or PNG
- Working with a tree too large to draw fully expanded

Use Qt treeview when:

- Programmatic or headless output must be PDF or SVG
- Exact physical dimensions or DPI matter
- Maintaining an existing ETE treeview layout

## Installation

Interactive SmartView is included in the base package:

```bash
uv pip install "ete4==4.4.0"
```

Static SmartView screenshots use Selenium:

```bash
uv pip install "ete4[render-sm]==4.4.0"
```

Qt rendering uses PyQt6:

```bash
uv pip install "ete4[treeview]==4.4.0"
```

## Interactive SmartView

### Python

```python
from pathlib import Path

from ete4 import Tree

with Path("tree.nw").open(encoding="utf-8") as handle:
    tree = Tree(handle, parser=1)

tree.explore()
```

With no `layouts` argument, ETE applies `BASIC_LAYOUT`, which displays leaf
names, branch lengths, and support.

`explore()` returns immediately. A standalone script must keep the process
alive, for example with `input()`, or use `keep_server=True`. The bundled
visualization helper waits and stops the server cleanly.

In Jupyter/IPython, SmartView is still browser-based; the current documentation
does not provide an inline SmartView widget. Keep the kernel alive and open the
served URL.

### Command line

```bash
ete4 explore -t tree.nw --src_tree_format 1
```

Inspect the active release's full options:

```bash
ete4 explore --help
```

The CLI supports basic source-tree selection and parser options. Although ETE
4.4.0 help exposes `--face`, its handler does not apply that argument; use
Python `Layout` objects for customization.

### Control the server

```python
tree.explore(
    host="127.0.0.1",
    port=5000,
    open_browser=False,
)
```

Keep the default loopback binding unless remote access is intentionally
secured. For a remote host, tunnel the loopback port:

```bash
ssh -L 5000:localhost:5000 user@remote-host
```

Then open `http://localhost:5000` locally. Do not expose an unauthenticated
explorer on `0.0.0.0` to an untrusted network.

## SmartView Layouts

A SmartView `Layout` combines:

- `draw_tree(tree)`: tree-wide style and header/legend faces
- `draw_node(node[, collapsed])`: styles and faces for individual nodes
- `name`: GUI identifier
- `cache_size`: memoization control for node drawing

### Circular tree with labels and support

```python
from ete4 import Tree
from ete4.smartview import Layout, PropFace, TextFace

tree = Tree("((A:1,B:1)95:0.2,C:1);", parser="support")


def draw_tree(_tree):
    yield {
        "shape": "circular",
        "node-height-min": 8,
        "content-height-min": 4,
    }
    yield TextFace(
        "Example phylogeny",
        fs_min=8,
        fs_max=22,
        position="header",
    )


def draw_node(node):
    if node.is_leaf:
        yield PropFace(
            "name",
            fs_min=4,
            fs_max=16,
            position="right",
        )
        return

    if node.support is not None:
        yield TextFace(
            f"{node.support:g}",
            fs_min=3,
            fs_max=12,
            style={"fill": "#555"},
            position="top",
        )


layout = Layout(
    "circular labels and support",
    draw_tree=draw_tree,
    draw_node=draw_node,
)

tree.explore(layouts=[layout])
```

### Conditional node styling

Support values may be fractions or percentages. Normalize only after checking
the source's convention:

```python
from ete4 import Tree
from ete4.smartview import Layout, PropFace

tree = Tree("((A:1,B:1)95:0.2,C:1);", parser="support")


def support_fraction(value):
    if value is None:
        return None
    return value / 100 if value > 1 else value


def draw_node(node):
    if node.is_leaf:
        yield PropFace("name", position="right")

    support = support_fraction(node.support)
    if support is None:
        color = "#888"
    elif support >= 0.9:
        color = "#1b7837"
    elif support >= 0.7:
        color = "#e08214"
    else:
        color = "#b2182b"

    yield {
        "dot": {
            "shape": "circle",
            "radius": 5,
            "fill": color,
        }
    }


layout = Layout("support colors", draw_node=draw_node)
tree.explore(layouts=[layout])
```

### Tree style keys

Common tree-wide keys:

- `shape`: `"rectangular"` or `"circular"`
- `radius`: circular layout radius
- `angle-start`, `angle-end`, `angle-span`: circular extent
- `node-height-min`: collapse threshold in pixels
- `content-height-min`: minimum height before faces appear
- `collapsed`: collapsed-node style
- `show-popup-props`, `hide-popup-props`: property disclosure
- `is-leaf-fn`: dynamic terminal-node rule
- `box`, `dot`, `hz-line`, `vt-line`: default CSS-like styles

Example:

```python
tree_style = {
    "shape": "circular",
    "angle-start": -180,
    "angle-span": 180,
    "node-height-min": 10,
    "collapsed": {
        "shape": "outline",
        "fill-opacity": 0.6,
    },
    "show-popup-props": ["name", "dist", "support", "group"],
}

layout = Layout("semicircle", draw_tree=tree_style)
tree.explore(layouts=[layout])
```

Limit popup properties when nodes contain sensitive or irrelevant metadata.

## SmartView Faces

Common classes from `ete4.smartview`:

- `TextFace`: literal text
- `PropFace`: one node property with optional formatting
- `EvalTextFace`: expression-derived text
- `CircleFace`, `RectFace`, `BoxFace`: shapes
- `ImageFace`: image
- `SeqFace`: molecular sequence
- `LegendFace`: legend

Positions include `top`, `bottom`, `left`, `right`, and `aligned`; tree-level
text can also use `header`.

### Aligned metadata columns

```python
from ete4.smartview import Layout, PropFace


def draw_node(node):
    if not node.is_leaf:
        return
    yield PropFace("name", position="aligned", column=0)
    yield PropFace("host", position="aligned", column=1)
    yield PropFace("location", position="aligned", column=2)


layout = Layout("sample metadata", draw_node=draw_node)
tree.explore(layouts=[layout])
```

### Collapsed-node behavior

For a special collapsed representation, accept a second argument:

```python
from ete4.smartview import Layout, TextFace


def draw_node(node, collapsed):
    if node.name != "large_clade":
        return
    text = "large_clade (collapsed)" if collapsed else "large_clade"
    return TextFace(text, position="right")


layout = Layout("collapsed label", draw_node=draw_node)
tree.explore(layouts=[layout])
```

Use collapse thresholds instead of trying to render every face for tens of
thousands of leaves.

## SmartView Static PNG

```python
from ete4 import Tree
from ete4.smartview import Layout, PropFace

tree = Tree("((A:1,B:1),C:1);")


def draw_node(node):
    if node.is_leaf:
        return PropFace("name", position="right")


layout = Layout("leaf labels", draw_node=draw_node)
tree.render_sm(
    "tree.png",
    layouts=[layout],
    w=1200,
    h=800,
)
```

In ETE 4.4.0, `render_sm()` captures PNG screenshot data. Give the output a
`.png` suffix. Supplying `.svg` or `.pdf` does not convert the screenshot to a
vector format.

Static SmartView rendering needs a browser usable by Selenium. If browser
discovery fails, install a compatible Chrome/Chromium browser or use Qt
treeview.

The interactive SmartView browser can download its current view as SVG or PNG
and export Newick. That browser action is distinct from `render_sm()`, which is
PNG-only and has no PDF mode.

## Qt Treeview for PNG/PDF/SVG

Treeview classes are not top-level ETE 4 imports.

```python
from ete4 import Tree
from ete4.treeview import NodeStyle, TextFace, TreeStyle

tree = Tree("((A:1,B:1)95:0.2,C:1);", parser="support")

for node in tree.traverse():
    style = NodeStyle()
    style["size"] = 6 if node.is_leaf else 4
    style["fgcolor"] = "navy" if node.is_leaf else "gray"
    node.set_style(style)

tree_style = TreeStyle()
tree_style.show_leaf_name = True
tree_style.show_branch_support = True
tree_style.show_scale = True
tree_style.title.add_face(
    TextFace("Example phylogeny", fsize=18, bold=True),
    column=0,
)

tree.render(
    "tree.svg",
    w=180,
    units="mm",
    tree_style=tree_style,
)
tree.render(
    "tree.pdf",
    w=180,
    units="mm",
    tree_style=tree_style,
)
tree.render(
    "tree.png",
    w=2400,
    units="px",
    dpi=300,
    tree_style=tree_style,
)
```

Qt treeview still uses `TreeStyle`, `NodeStyle`, and Qt face classes, but ETE 4
predicates remain properties:

```python
if node.is_leaf:
    ...
```

not:

```python
if node.is_leaf():
    ...
```

### Circular Qt output

```python
tree_style = TreeStyle()
tree_style.mode = "c"
tree_style.arc_start = -180
tree_style.arc_span = 180
tree.render("semicircle.svg", tree_style=tree_style)
```

### Headless Qt

On a headless Linux host, a common first attempt is:

```bash
QT_QPA_PLATFORM=offscreen python render_tree.py
```

If the platform plugin or required shared libraries are unavailable, use
SmartView PNG, a container with the Qt runtime, or render on a workstation.

## Bundled Visualization Script

Interactive SmartView:

```bash
uv run --with "ete4==4.4.0" python scripts/quick_visualize.py \
  tree.nw --parser 1
```

SmartView PNG:

```bash
uv run --with "ete4[render-sm]==4.4.0" python scripts/quick_visualize.py \
  tree.nw tree.png \
  --parser support \
  --mode circular \
  --show-support \
  --color-by-support \
  --title "Maximum-likelihood tree"
```

Qt SVG or PDF:

```bash
uv run --with "ete4[treeview]==4.4.0" python scripts/quick_visualize.py \
  tree.nw tree.svg \
  --parser 1 \
  --engine treeview \
  --mode rectangular \
  --title "Species tree"
```

The script's `auto` engine chooses SmartView for interactive use and PNG,
and Qt treeview for PDF/SVG.

## Publication Checklist

- Prefer SVG/PDF for line art that will be resized or edited.
- Use explicit physical width for journal figures.
- Check support scale before mapping colors or labels.
- Use a colorblind-safe palette and do not rely on color alone.
- Keep tip labels legible at final print size.
- State rooting, branch-length units, and support statistic in the caption.
- Export only intended node properties.
- Test the exact artifact, not just the interactive explorer.

## Troubleshooting

### `ImportError` for SmartView static rendering

```bash
uv pip install "ete4[render-sm]==4.4.0"
```

### `ImportError` for Qt classes

Use:

```python
from ete4.treeview import NodeStyle, TreeStyle
```

after:

```bash
uv pip install "ete4[treeview]==4.4.0"
```

### Tree renders without expected names or support

The likely cause is the parser. Re-read using `parser="name"` or
`parser="support"` as appropriate and inspect:

```python
print(tree.to_str(props=["name", "dist", "support"], compact=True))
```

### Large tree appears collapsed

SmartView adaptively collapses branches below `node-height-min`. Zoom in or
lower the threshold in a layout.

## Upstream References

- SmartView tutorial:
  https://etetoolkit.github.io/ete/tutorial/tutorial_smartview.html
- SmartView API:
  https://etetoolkit.github.io/ete/reference/reference_smartview.html
- Qt treeview tutorial:
  https://etetoolkit.github.io/ete/tutorial/tutorial_treeview.html
- Qt treeview API:
  https://etetoolkit.github.io/ete/reference/reference_treeview.html
- ETE Gallery: https://github.com/etetoolkit/ete-gallery
