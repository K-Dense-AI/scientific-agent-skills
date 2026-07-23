# Migrating ETE 3 Code to ETE 4

ETE 4 is a breaking API revision, not an import-only upgrade. This guide targets
ETE 4.4.0 and summarizes the official migration guide plus behavior verified
against the installed release.

## Release Baseline

- ETE 4.0.0 and 4.1.1 were released March 28, 2025.
- ETE 4.1.1 marked ETE 4 as out of beta and available on PyPI.
- ETE 4.4.0 was released September 3, 2025.
- Package name and primary import are `ete4`.

Install side by side only when a legacy project genuinely requires ETE 3:

```bash
uv pip install "ete4==4.4.0"
```

Do not leave both APIs implicit in one code path. Name compatibility boundaries
and test them separately.

## Import Changes

ETE 3:

```python
from ete3 import NCBITaxa, PhyloTree, Tree
```

ETE 4:

```python
from ete4 import GTDBTaxa, NCBITaxa, PhyloTree, Tree
```

ETE 3 exposed equivalent `TreeNode` and `Tree` classes. ETE 4 uses `Tree`.

Qt visualization imports moved:

```python
# ETE 3
from ete3 import NodeStyle, TextFace, TreeStyle

# ETE 4
from ete4.treeview import NodeStyle, TextFace, TreeStyle
```

Current web visualization uses:

```python
from ete4.smartview import Layout, PropFace, TextFace
```

SmartView and treeview `TextFace` classes are different types.

## Construction and File Input

### File path ambiguity was removed

ETE 3:

```python
tree = Tree("tree.nw", format=1)
```

ETE 4:

```python
from pathlib import Path

with Path("tree.nw").open(encoding="utf-8") as handle:
    tree = Tree(handle, parser=1)
```

Use strings for Newick text and pass an open file object for file input. ETE
4.4.0 still contains a path-like string heuristic internally, but relying on it
conflicts with the documented contract and makes input behavior ambiguous.

### New nodes with properties

ETE 3:

```python
tree = Tree(name="root", dist=0, support=1)
```

ETE 4:

```python
tree = Tree({"name": "root", "dist": 0, "support": 1})
```

ETE 4 accepts arbitrary initial properties through the dictionary.

## Property Model

ETE 3 required name, distance, and support defaults. In ETE 4 these properties
can be absent, and their convenience accessors can return `None`.

ETE 3:

```python
node.add_feature("habitat", "marine")
node.add_features(group="case", score=0.8)
print(node.features)
```

ETE 4:

```python
node.add_prop("habitat", "marine")
node.add_props(group="case", score=0.8)
print(node.props)
```

General argument renames:

- `feature` / `features` → `prop` / `props`
- `attribute` / `attributes` → `prop` / `props`
- `property` / `properties` → `prop` / `props`

Replace `hasattr(node, "x")` tests for custom metadata with:

```python
if "x" in node.props:
    value = node.props["x"]
```

## Lookup, Predicates, and Relatives

| ETE 3 | ETE 4 |
|---|---|
| `tree & "A"` | `tree["A"]` |
| `tree.get_tree_root()` | `tree.root` |
| `node.is_leaf()` | `node.is_leaf` |
| `node.is_root()` | `node.is_root` |
| `tree.get_common_ancestor(a, b)` | `tree.common_ancestor(a, b)` |
| `node.get_ancestors()` | `node.ancestors()` |
| `tree.get_leaves_by_name("A")` | `tree.search_leaves_by_name("A")` |

ETE 4 also supports positional IDs:

```python
node = tree[0, 1, 0]
print(node.id, node.level)
```

Name lookup returns the first match in both practical patterns. Validate
uniqueness when names are identifiers.

## Iterator Renames

| ETE 3 | ETE 4 |
|---|---|
| `get_leaves()` / `iter_leaves()` | `leaves()` |
| `get_descendants()` / `iter_descendants()` | `descendants()` |
| `get_edges()` / `iter_edges()` | `edges()` |
| `get_leaf_names()` | `leaf_names()` |
| `get_ancestors()` | `ancestors()` |

ETE 4 returns iterators:

```python
leaves = list(tree.leaves())
names = list(tree.leaf_names())
```

Do not call `len(tree.leaves())` or index the result without first creating a
list.

## Text and Newick I/O

### Parser rename

ETE 3:

```python
tree = Tree(newick, format=1)
newick = tree.write(format=1)
```

ETE 4:

```python
tree = Tree(newick, parser=1)
newick = tree.write(parser=1)
```

Named parser aliases include `"name"` and `"support"`.

### ASCII rename

ETE 3:

```python
print(tree.get_ascii(show_internal=True))
```

ETE 4:

```python
print(tree.to_str(show_internal=True, props=["name", "dist"]))
```

### Extended-property semantics

ETE 3 `features=[]` meant all available features. In ETE 4:

```python
tree.write(props=[])                  # no extended properties
tree.write(props=["species", "host"]) # selected properties
tree.write(props=None)                # all available properties
```

This reversal is important. Use an explicit selected list for external output.

Use keyword arguments with `write()`. Its first positional argument is
`outfile` in ETE 4, not the ETE 3 feature selection.

### Custom formatters

ETE 3:

```python
newick = tree.write(
    format=1,
    dist_formatter="%0.1f",
    name_formatter="TEST-%s",
)
```

ETE 4:

```python
from ete4.parser import newick

parser = newick.make_parser(
    1,
    dist="%0.1f",
    name="TEST-%s",
)
text = tree.write(parser=parser)
```

## Distances and Topology

| ETE 3 | ETE 4 |
|---|---|
| `A.get_distance(B)` | `tree.get_distance(A, B)` |
| `topology_only=True` | `topological=True` |
| `convert_to_ultrametric()` | `to_ultrametric()` |
| `resolve_polytomy(recursive=True)` | `resolve_polytomy(descendants=True)` |

ETE 4 adds a direct midpoint convenience:

```python
tree.set_midpoint_outgroup()
```

The older two-step pattern remains valid:

```python
midpoint = tree.get_midpoint_outgroup()
tree.set_outgroup(midpoint)
```

ETE 4.4.0 adds `distance_matrix()`, which supersedes
`cophenetic_matrix()` for new code.

## Random Tree Generation

ETE 3:

```python
tree.populate(
    size,
    names_library=names,
    random_branches=True,
    dist_range=(0, 1),
)
```

ETE 4:

```python
import random

tree.populate(
    size,
    names=names,
    model="yule",
    dist_fn=random.random,
    support_fn=lambda: 1,
)
```

Set the random seed when generated topology or distances must be reproducible.

## Robinson-Foulds Unpacking

ETE 4.4.0 returns seven values:

```python
(
    rf,
    max_rf,
    common,
    edges_self,
    edges_other,
    discarded_self,
    discarded_other,
) = tree.robinson_foulds(other)
```

ETE 3 examples that unpack only five values must be updated.

Argument names also use `prop_t1` and `prop_t2` rather than feature-oriented
names.

## PhyloTree Changes and Traps

The central ETE 3 methods remain, but use ETE 4 property and iterator syntax:

```python
from ete4 import PhyloTree

tree = PhyloTree(
    "((Hsa|g1,Ptr|g1),Mmu|g1);",
    sp_naming_function=lambda name: name.split("|", 1)[0],
)

events = tree.get_descendant_evol_events(sos_thr=0.0)
for leaf in tree.leaves():
    print(leaf.name, leaf.species)
```

Pass `sp_naming_function` explicitly for species-aware methods. The current
source defaults it to `None`, despite older documentation describing an
automatic first-three-character rule. Species-overlap event detection also
requires a rooted, fully bifurcating gene tree.

Do not pass a species tree to `get_descendant_evol_events()`. In ETE 4.4.0 its
signature accepts only `sos_thr`. Use reconciliation:

```python
reconciled_tree, events = gene_tree.reconcile(species_tree)
```

After event detection, inspect:

```python
node.props.get("evoltype")
```

rather than relying on ETE 3 feature helpers.

## Taxonomy Changes

ETE 3 examples commonly refer to:

```text
~/.etetoolkit/taxa.sqlite
```

ETE 4 stores taxonomy data under:

```text
~/.local/share/ete/
```

The current documentation's approximately 600 MB NCBI and 72 MB GTDB figures
are better treated as local first-use footprint estimates, not compressed
network download sizes. Archive sizes vary by release and can be much smaller;
allow extra space for parsed SQLite and temporary conversion files.

ETE 4 adds first-class GTDB support:

```python
from ete4 import GTDBTaxa
```

NCBI numeric TaxIDs and GTDB string identifiers are not interchangeable.

## Visualization Migration

### Preferred ETE 4 SmartView

```python
from ete4 import Tree

tree = Tree("((A,B),C);")
tree.explore()
tree.render_sm("tree.png")
```

Custom SmartView:

```python
from ete4.smartview import Layout, PropFace


def draw_node(node):
    if node.is_leaf:
        return PropFace("name", position="right")


layout = Layout("labels", draw_node=draw_node)
tree.explore(layouts=[layout])
```

SmartView style dictionaries and faces are not compatible with `TreeStyle` or
`NodeStyle`.

### Retained Qt treeview

ETE 3:

```python
from ete3 import NodeStyle, TreeStyle
```

ETE 4:

```python
from ete4.treeview import NodeStyle, TreeStyle
```

Install:

```bash
uv pip install "ete4[treeview]==4.4.0"
```

Qt treeview remains the option for vector PDF/SVG. SmartView's `render_sm()` in
ETE 4.4.0 creates PNG screenshot data.

## Clustering

ETE 3:

```python
from ete3 import ClusterTree
```

ETE 4.4.0:

```text
ImportError: cannot import name 'ClusterTree' from 'ete4'
```

Do not document `ClusterTree`, linked matrix profiles, silhouette, or Dunn
methods as ETE 4 capabilities. Use a maintained clustering library for those
calculations and a normal ETE `Tree` for topology display.

## Command-Line Caveat

The `ete4 compare` command shipped in ETE 4.4.0 still calls `Tree(...,
format=...)` internally and fails with the removed keyword. Use
`Tree.robinson_foulds()`, `Tree.compare()` for unique labels, or this skill's
`scripts/tree_operations.py compare` helper. Avoid the duplication-aware
`Tree.compare(has_duplications=True)` path as well; upstream source labels that
branch as likely broken.

## Porting Example

ETE 3:

```python
from ete3 import Tree

tree = Tree("tree.nw", format=1)
node = tree & "A"
node.add_feature("group", "case")

for leaf in tree.iter_leaves():
    if leaf.is_leaf():
        print(leaf.name)

tree.write(
    outfile="out.nhx",
    format=1,
    features=["group"],
)
```

ETE 4:

```python
from pathlib import Path

from ete4 import Tree

with Path("tree.nw").open(encoding="utf-8") as handle:
    tree = Tree(handle, parser=1)

node = tree["A"]
node.add_prop("group", "case")

for leaf in tree.leaves():
    if leaf.is_leaf:
        print(leaf.name)

tree.write(
    outfile="out.nhx",
    parser=1,
    props=["group"],
)
```

## Mechanical Porting Checklist

Search legacy code for:

```text
from ete3
TreeNode
format=
features=
feature=
attributes=
attribute=
add_feature
add_features
.features
get_ascii
get_tree_root
get_common_ancestor
get_leaves
iter_leaves
get_descendants
iter_descendants
get_leaf_names
get_leaves_by_name
convert_to_ultrametric
topology_only
is_leaf()
is_root()
 & "
ClusterTree
TreeStyle
NodeStyle
```

Then:

1. Replace each symbol using this guide.
2. Review every Newick read/write parser.
3. Convert iterator consumers deliberately.
4. Validate property export semantics.
5. Separate SmartView and treeview layouts.
6. Remove or redesign `ClusterTree` workflows.
7. Test representative trees with names, support, branch lengths, NHX
   properties, duplicate tips, and polytomies.
8. Compare scientific outputs, not just successful execution.

## Verification Snippet

```python
import ete4
from ete4 import Tree

assert ete4.__version__ == "4.4.0"

tree = Tree("((A:1,B:1)95:0.2,C:1);", parser="support")
assert list(tree.leaf_names()) == ["A", "B", "C"]
assert tree["A"].is_leaf

round_trip = tree.write(parser="support", props=[])
assert round_trip == "((A:1,B:1)95:0.2,C:1);"
```

## Upstream References

- Current migration guide: https://etetoolkit.github.io/ete/3to4.html
- Migration wiki: https://github.com/etetoolkit/ete/wiki/3to4
- ETE 4 release notes: https://github.com/etetoolkit/ete/releases
- ETE 4 documentation: https://etetoolkit.github.io/ete/
- ETE 4 PyPI: https://pypi.org/project/ete4/
