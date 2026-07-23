---
name: etetoolkit
description: Analyze, manipulate, compare, annotate, and visualize phylogenetic or other hierarchical trees with ETE 4. Use for Newick/Nexus tree I/O, topology edits and pattern matching, Robinson-Foulds comparisons, gene-tree evolutionary events and reconciliation, NCBI/GTDB taxonomy, SmartView exploration, and publication rendering. Do not use it to infer trees from raw sequences; align sequences and infer a tree first.
license: GPL-3.0-or-later
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Python
compatibility: Bundled scripts require Python 3.10+ and ete4 4.4.0 (upstream ete4 supports Python >=3.7). Taxonomy setup and SmartView exploration need network access; static SmartView PNG rendering needs ete4[render-sm], and Qt PDF/SVG rendering needs ete4[treeview].
metadata:
  version: "2.0"
  skill-author: K-Dense Inc.
---

# ETE Toolkit 4

## Scope

Use ETE 4 to work with an existing tree:

- Read Newick/Nexus, then inspect, annotate, transform, root, prune, and write
  Newick trees
- Compare topologies and calculate phylogenetic distances
- Find repeated subtree topologies with `TreePattern`
- Analyze gene trees with `PhyloTree`
- Query local NCBI or GTDB taxonomy databases
- Explore large trees interactively with SmartView
- Render PNG with SmartView or PNG/PDF/SVG with the optional Qt treeview

ETE does not replace sequence alignment or phylogenetic inference software. For
raw sequences, first use MAFFT or another aligner and IQ-TREE 2, FastTree, or
another inference tool; then load the resulting tree into ETE.

## Current Target

This skill targets **ETE 4.4.0**, released September 3, 2025 and verified as the
current PyPI release on July 23, 2026.

Use `https://etetoolkit.github.io/ete/` for ETE 4 documentation. The
`etetoolkit.org/docs/latest` pages are legacy ETE 3 documentation despite the
URL name.

Do not silently translate these examples back to ETE 3:

- Package and import: `ete4`, not `ete3`
- File input: pass an open file object; use strings for Newick text and do not
  rely on path-string heuristics retained in ETE 4.4.0
- Newick selection: `parser=`, not `format=`
- Node metadata: `props`, `add_prop()`, and `add_props()`
- Iteration: `leaves()`, `descendants()`, and related methods return iterators
- Predicates: `node.is_leaf` and `node.is_root` are properties, not methods
- Node lookup: `tree["name"]`, not `tree & "name"`

For porting older code, load
[`references/migration-ete3-to-ete4.md`](references/migration-ete3-to-ete4.md).

## Installation

Install the pinned base package:

```bash
uv pip install "ete4==4.4.0"
```

Add only the visualization extra required by the workflow:

```bash
# SmartView static PNG screenshots
uv pip install "ete4[render-sm]==4.4.0"

# Legacy Qt renderer for PNG, PDF, and SVG
uv pip install "ete4[treeview]==4.4.0"
```

Confirm the active environment:

```bash
uv run --with "ete4==4.4.0" python -c "import ete4; print(ete4.__version__)"
```

No credentials are required. NCBI and GTDB workflows download public taxonomy
data and can consume substantial disk space; see
[`references/taxonomy.md`](references/taxonomy.md) before the first update.

## Quick Start

```python
from pathlib import Path

from ete4 import Tree

# Use an open file object for files; reserve strings for Newick text.
with Path("tree.nw").open(encoding="utf-8") as handle:
    tree = Tree(handle, parser=1)  # parser 1: internal node names

print(tree.to_str(props=["name", "dist"], compact=True))
print("Leaves:", list(tree.leaf_names()))

# Search and annotate.
focal = tree["species1"]
focal.add_props(host="human", status="focal")

# Keep selected tips while preserving pairwise branch-length distances.
tree.prune(
    ["species1", "species2", "species3"],
    preserve_branch_length=True,
)

# Root and serialize explicitly.
tree.set_midpoint_outgroup()
tree.write(
    outfile="processed.nw",
    parser=1,
    props=["host", "status"],
)
```

Choose the parser deliberately. A parser mismatch is the most common cause of
`NewickError`, lost internal labels, or support values being read as names.
See [`references/api_reference.md`](references/api_reference.md).

## Core Workflows

### Inspect and transform a tree

```python
from ete4 import Tree

tree = Tree("((A:1,B:1)CladeAB:0.4,C:2)Root;", parser=1)

for node in tree.traverse("preorder"):
    label = node.name if node.name is not None else node.id
    print(label, node.level, node.is_leaf, node.dist)

tree["A"].add_prop("group", "case")
tree["B"].add_prop("group", "control")

mrca = tree.common_ancestor("A", "B")
print(mrca.name)

tree.write(
    outfile="annotated.nhx",
    parser=1,
    props=["group"],
    format_root_node=True,
)
```

Node names need not be unique. `tree["A"]` returns the first match; use
`list(tree.search_nodes(name="A"))` and validate the count when duplicates are
possible.

### Compare two topologies

```python
from ete4 import Tree

tree_a = Tree("((A,B),(C,D));")
tree_b = Tree("((A,C),(B,D));")

(
    rf,
    max_rf,
    common_leaves,
    edges_a,
    edges_b,
    discarded_a,
    discarded_b,
) = tree_a.robinson_foulds(tree_b)

normalized_rf = rf / max_rf if max_rf else 0.0
print(rf, max_rf, normalized_rf, sorted(common_leaves))
```

RF comparison uses shared leaf labels and requires meaningful, preferably
unique names. Decide explicitly whether rooted or unrooted comparison is
scientifically appropriate.

### Detect duplication and speciation events

```python
from ete4 import PhyloTree

gene_tree = PhyloTree(
    "((Hsa|g1,Ptr|g1),(Hsa|g2,Mmu|g1));",
    sp_naming_function=lambda name: name.split("|", 1)[0],
)

for event in gene_tree.get_descendant_evol_events(sos_thr=0.0):
    relationship = "speciation/orthology" if event.etype == "S" else "duplication/paralogy"
    print(relationship, sorted(event.in_seqs), sorted(event.out_seqs))
```

Species-overlap calls are inferences from the supplied topology and naming
function, not independent evidence of orthology. Pass the naming function
explicitly, and use a rooted, fully bifurcating gene tree. For strict
reconciliation, use a curated species tree and
`gene_tree.reconcile(species_tree)`.

### Query taxonomy

```python
from ete4 import NCBITaxa

ncbi = NCBITaxa()
names = ["Homo sapiens", "Pan troglodytes", "Mus musculus"]
name_to_taxids = ncbi.get_name_translator(names)

missing = [name for name in names if name not in name_to_taxids]
if missing:
    raise ValueError(f"Names not resolved by NCBI taxonomy: {missing}")

taxids = [name_to_taxids[name][0] for name in names]
taxonomy_tree = ncbi.get_topology(taxids)
print(taxonomy_tree.to_str(props=["sci_name", "rank"]))
```

ETE 4 also provides `GTDBTaxa` for genome-centric bacterial and archaeal
taxonomy. Do not mix NCBI numeric TaxIDs and GTDB string identifiers.

### Visualize

Interactive SmartView:

```python
from ete4 import Tree

tree = Tree("((A:1,B:1)90:0.2,C:1);", parser="support")
tree.explore()
```

Static SmartView screenshot:

```python
tree.render_sm("tree.png", w=1200, h=800)
```

`render_sm()` produces PNG screenshot data; use the Qt treeview renderer when
the deliverable must be vector PDF or SVG. Load
[`references/visualization.md`](references/visualization.md) for layouts,
faces, remote exploration, and renderer selection.

## Bundled Scripts

Run from this skill directory. The commands below use a pinned, isolated ETE 4
runtime through `uv run --with`.

### Tree operations

```bash
uv run --with "ete4==4.4.0" python scripts/tree_operations.py \
  stats tree.nw --parser 1
uv run --with "ete4==4.4.0" python scripts/tree_operations.py \
  ascii tree.nw --parser 1 --props name,dist
uv run --with "ete4==4.4.0" python scripts/tree_operations.py \
  convert tree.nw output.nw \
  --input-parser 1 --output-parser 1
uv run --with "ete4==4.4.0" python scripts/tree_operations.py \
  reroot tree.nw rooted.nw \
  --parser 1 --midpoint
uv run --with "ete4==4.4.0" python scripts/tree_operations.py \
  prune tree.nw pruned.nw \
  --parser 1 --keep species1 species2 species3
uv run --with "ete4==4.4.0" python scripts/tree_operations.py \
  compare tree_a.nw tree_b.nw
```

Use `--keep-file taxa.txt` instead of `--keep ...` for one taxon per line.
The script refuses ambiguous or missing requested names rather than silently
producing a partial tree.

### Visualization

```bash
# Interactive SmartView
uv run --with "ete4==4.4.0" python scripts/quick_visualize.py \
  tree.nw --parser 1

# SmartView PNG (requires ete4[render-sm])
uv run --with "ete4[render-sm]==4.4.0" python scripts/quick_visualize.py \
  tree.nw tree.png \
  --parser support --mode circular --show-support --color-by-support

# Vector output via Qt treeview (requires ete4[treeview])
uv run --with "ete4[treeview]==4.4.0" python scripts/quick_visualize.py \
  tree.nw tree.svg \
  --parser 1 --engine treeview --title "Species phylogeny"
```

## Quality and Interpretation Checks

Before reporting a result:

1. Confirm the parser preserves the intended internal names, support, and
   branch lengths.
2. Check for empty and duplicate leaf names before name-based lookup or RF
   comparison.
3. State whether the tree is treated as rooted or unrooted.
4. Preserve branch lengths when pruning only if retained pairwise distances
   should remain unchanged.
5. Treat arbitrary polytomy resolution as a display/algorithmic convenience,
   not evolutionary evidence.
6. Record ETE version, parser, rooting method, pruning set, and taxonomy
   database snapshot in reproducible analyses.
7. Prefer iterators for large trees and `get_cached_content()` for repeated
   descendant-content queries.

## Reference Map

Load only the reference needed for the task:

- [`references/api_reference.md`](references/api_reference.md) — ETE 4 core
  classes, parsers, properties, traversal, I/O, topology, and comparison
- [`references/workflows.md`](references/workflows.md) — complete analysis
  patterns, validation, reconciliation, batching, and large-tree work
- [`references/visualization.md`](references/visualization.md) — SmartView,
  layouts/faces, PNG screenshots, and Qt vector rendering
- [`references/taxonomy.md`](references/taxonomy.md) — NCBI and GTDB setup,
  translation, topology, annotation, and reproducibility
- [`references/migration-ete3-to-ete4.md`](references/migration-ete3-to-ete4.md)
  — breaking API changes and porting checklist

## Authoritative Upstream Sources

- Documentation: https://etetoolkit.github.io/ete/
- ETE 3 to ETE 4 migration: https://etetoolkit.github.io/ete/3to4.html
- Releases: https://github.com/etetoolkit/ete/releases
- PyPI: https://pypi.org/project/ete4/
- Source: https://github.com/etetoolkit/ete
- Visualization gallery: https://github.com/etetoolkit/ete-gallery
