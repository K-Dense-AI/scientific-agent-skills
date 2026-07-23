# ETE 4 API Reference

This is a task-oriented reference for **ETE 4.4.0**. It was checked against the
official ETE 4 documentation and an installed `ete4==4.4.0` package on
July 23, 2026. Use the upstream API reference for less common parameters.

## Imports and Public Classes

```python
from ete4 import (
    EvolTree,
    GTDBTaxa,
    NCBITaxa,
    PhyloTree,
    SeqGroup,
    Tree,
)
```

Frequently used classes:

- `Tree`: general rooted or unrooted tree data structure
- `PhyloTree`: `Tree` subclass with species, alignment, event, and
  reconciliation methods
- `NCBITaxa`: local NCBI taxonomy database interface
- `GTDBTaxa`: local Genome Taxonomy Database interface
- `SeqGroup`: sequence/alignment container
- `EvolTree`: evolutionary-model support, including external PAML workflows

`ClusterTree` is not exported by ETE 4.4.0. Do not port ETE 3 clustering
examples by changing only the import. Use a normal `Tree` for dendrogram
topology and calculate matrix/cluster statistics with a maintained numerical
library.

## Constructing and Parsing Trees

### Empty node or node properties

```python
from ete4 import Tree

empty = Tree()
root = Tree({"name": "root", "dist": 0.0, "study": "trial-7"})
```

ETE 4 nodes do not automatically have a non-null name, distance, or support.
`node.name`, `node.dist`, and `node.support` can therefore be `None`.

### Newick string

```python
tree = Tree("((A:1,B:2)CladeAB:0.5,C:3)Root;", parser=1)
```

Use Python strings for Newick text. ETE 4.4.0 retains a path-like string
heuristic internally, but the documented and reproducible file form is an open
file object; do not depend on the heuristic.

### Newick file

```python
from pathlib import Path

with Path("tree.nw").open(encoding="utf-8") as handle:
    tree = Tree(handle, parser=1)
```

Pass an open text file object. This distinction removes the ETE 3 ambiguity
between file names and Newick strings.

### Common Newick parsers

- `parser="support"` or `parser=0`: flexible branch lengths; internal field is
  support
- `parser="name"` or `parser=1`: flexible branch lengths; internal field is a
  name
- `parser=8`: all node names, no branch lengths required
- `parser=9`: leaf names only
- `parser=100`: topology only

Other numeric parsers encode stricter combinations of names and branch
lengths. Prefer the parser that matches the actual producer's Newick schema.
Inspect a round trip before processing a large collection:

```python
tree = Tree("((A:1,B:1)95:0.2,C:1);", parser="support")
assert tree.write(parser="support", props=[]) == "((A:1,B:1)95:0.2,C:1);"
```

### Nexus files

ETE's Nexus parser returns a dictionary of tree names to `Tree` objects and
applies any Nexus translation table:

```python
from pathlib import Path

from ete4.parser import nexus

with Path("trees.nex").open(encoding="utf-8") as handle:
    trees = nexus.load(handle, parser=9)

for tree_name, tree in trees.items():
    print(tree_name, list(tree.leaf_names()))
```

Use the parser expected by the Newick strings inside the Nexus `TREES` block.
The current Nexus module is a reader; serialize processed trees explicitly as
Newick unless another library is responsible for writing Nexus.

## Node Structure and Properties

Core structural attributes:

```python
node.up           # parent or None
node.children     # child list
node.root         # absolute root
node.is_leaf      # bool property
node.is_root      # bool property
node.level        # edges between node and root
node.id           # positional tuple, such as (0, 1, 0)
```

Biological or user metadata belongs in `props`:

```python
node.add_prop("habitat", "marine")
node.add_props(sample_count=12, qc_pass=True)

habitat = node.get_prop("habitat", "unknown")
same_value = node.props.get("habitat", "unknown")

node.del_prop("qc_pass")
```

`name`, `dist`, and `support` are special property-backed conveniences:

```python
assert node.name == node.props.get("name")
```

Use `add_prop()` rather than assigning arbitrary Python attributes if the value
must participate in search, serialization, or visualization.

## Traversal and Navigation

ETE 4's collection-like methods return iterators.

```python
# Includes the current node.
for node in tree.traverse("preorder"):
    ...

# Excludes the current node.
for node in tree.descendants("postorder"):
    ...

for leaf in tree.leaves():
    ...

leaves = list(tree.leaves())
names = list(tree.leaf_names())
ancestors = list(node.ancestors())
```

Valid traversal strategies are `"levelorder"` (default), `"preorder"`, and
`"postorder"`.

### Dynamic leaf criteria

```python
def stop_at_named_clade(node):
    return node.name in {"Mammalia", "Aves"}

for visible_node in tree.traverse(is_leaf_fn=stop_at_named_clade):
    ...
```

This presents selected internal nodes as terminal during that operation
without changing the topology.

## Search and Lookup

```python
first_a = tree["A"]
by_position = tree[0, 1, 0]

all_a = list(tree.search_nodes(name="A"))
long_branches = [n for n in tree.traverse() if (n.dist or 0) > 1]
leaf_a = next(tree.search_leaves_by_name("A"))

mrca = tree.common_ancestor("A", "B")
mrca_from_list = tree.common_ancestor(["A", "B"])
```

Name lookup returns the first match. Validate uniqueness when names are
identifiers:

```python
from collections import Counter

leaf_names = list(tree.leaf_names())
duplicates = sorted(name for name, count in Counter(leaf_names).items() if count > 1)
if duplicates:
    raise ValueError(f"Duplicate leaf names: {duplicates}")
```

## Topology Modification

### Add and remove nodes

```python
child = tree.add_child(name="A", dist=0.5)
sister = child.add_sister(name="B", dist=0.7)

subtree = child.detach()  # remove child plus all descendants
tree.add_child(subtree)   # attach it elsewhere

internal.delete(preserve_branch_length=True)  # remove node, retain children
```

`detach()` cuts a complete subtree. `delete()` eliminates only the selected
node and reconnects its children.

### Prune

```python
tree.prune(
    ["A", "B", "C"],
    preserve_branch_length=True,
)
```

`preserve_branch_length=True` transfers deleted branch lengths so distances
among retained nodes remain unchanged.

### Root and unroot

```python
tree.set_outgroup(tree["Outgroup"])
tree.set_midpoint_outgroup()
tree.unroot()
```

For inspection without immediately modifying the tree:

```python
midpoint_node = tree.get_midpoint_outgroup()
tree.set_outgroup(midpoint_node)
```

### Other operations

```python
tree.resolve_polytomy(descendants=True)
tree.ladderize()
tree.to_ultrametric(topological=False)
tree.standardize(delete_orphan=True, preserve_branch_length=True)
```

Polytomy resolution is arbitrary. Never report the generated branching order
as biological evidence.

## Distances and Cached Content

```python
a = tree["A"]
b = tree["B"]

branch_distance = tree.get_distance(a, b)
edge_distance = tree.get_distance(a, b, topological=True)

farthest_leaf, distance = tree.get_farthest_leaf()
closest_leaf, distance = tree.get_closest_leaf()
```

ETE 4.4 adds `distance_matrix()` and supersedes the older
`cophenetic_matrix()` for new code:

```python
matrix = tree.distance_matrix(squared=True)
```

For repeated descendant lookups:

```python
node_to_leaf_names = tree.get_cached_content(prop="name")
for node in tree.traverse():
    names_below = node_to_leaf_names[node]
```

## Monophyly

```python
is_mono, clade_type, extra = tree.check_monophyly(
    values={"A", "B", "C"},
    prop="name",
    unrooted=False,
)

for clade in tree.get_monophyletic(values={"case"}, prop="group"):
    print(clade.id)
```

Interpret `"monophyletic"`, `"paraphyletic"`, and `"polyphyletic"` in the
context of the tree's rooting.

## Newick and Text Output

### Newick

```python
# No extended NHX properties.
plain_newick = tree.write(parser=1, props=[])

# Selected properties in NHX fields.
annotated_newick = tree.write(parser=1, props=["species", "group"])

# All available properties. Use only when that disclosure is intentional.
all_properties = tree.write(parser=1, props=None)

tree.write(
    outfile="tree.nw",
    parser=1,
    props=["group"],
    format_root_node=True,
)
```

Important `props` behavior:

- `props=[]` or the default empty tuple: write no extended properties
- `props=["x", "y"]`: write selected properties
- `props=None`: write all available properties

Use an explicit list in shared or external output so internal metadata is not
exported accidentally.

Also use keyword arguments. The first positional argument of `write()` is
`outfile` in ETE 4, whereas older ETE 3 code may have treated its first
positional argument as a feature selection.

### Terminal representation

```python
print(tree)
print(tree.to_str(props=["name", "dist", "support"], compact=True))
```

`to_str()` replaces ETE 3's `get_ascii()`.

## Copying

```python
exact = tree.copy()                    # cpickle; recommended full copy
topology = tree.copy("newick")         # fast; standard Newick fields
text_props = tree.copy("newick-extended")
deep = tree.copy("deepcopy")           # slowest; complex Python objects
```

The extended-Newick path converts custom values to text and is not a
type-preserving clone.

## Tree Comparison

### Raw Robinson-Foulds result

```python
(
    rf,
    max_rf,
    common_leaves,
    edges_self,
    edges_other,
    discarded_self,
    discarded_other,
) = tree.robinson_foulds(
    other,
    prop_t1="name",
    prop_t2="name",
    unrooted_trees=False,
)
```

ETE 4 returns seven values. Older examples that unpack five values are wrong.

### Summary dictionary

```python
result = tree.compare(
    other,
    ref_tree_attr="name",
    source_tree_attr="name",
    unrooted=False,
)

print(result["rf"], result["max_rf"], result["norm_rf"])
```

Comparison is only meaningful if the selected property has the intended
identity semantics. Report filtering by common leaves, support thresholds,
rooting, polytomy expansion, and duplication handling.

For unique tip labels, prefer `Tree.robinson_foulds()` or the normal
`Tree.compare()` path. Do not rely on `Tree.compare(has_duplications=True)` in
ETE 4.4.0: upstream source marks that TreeKO branch as likely broken. The
packaged `ete4 compare` CLI also still passes the removed `format=` constructor
argument and fails at runtime; use the Python methods or the bundled
`scripts/tree_operations.py compare` command.

## PhyloTree

Constructor:

```python
from ete4 import PhyloTree

tree = PhyloTree(
    "((Hsa|g1,Ptr|g1),Mmu|g1);",
    alignment=None,
    alg_format="fasta",
    sp_naming_function=lambda name: name.split("|", 1)[0],
    parser=None,
)
```

Always provide `sp_naming_function` when species-aware methods are needed. The
ETE 4.4.0 source default is `None`; older documentation that implies an
automatic first-three-character rule is not reliable.

Alignment:

```python
tree.link_to_alignment("alignment.fasta", alg_format="fasta")
for leaf in tree.leaves():
    print(leaf.name, leaf.sequence)
```

Species handling:

```python
tree.set_species_naming_function(lambda name: name.split("|", 1)[0])
species = {leaf.species for leaf in tree.leaves()}
```

Evolutionary events:

```python
events = tree.get_descendant_evol_events(sos_thr=0.0)
for event in events:
    print(event.etype, event.in_seqs, event.out_seqs)
```

Species-overlap event detection expects a rooted, fully bifurcating gene tree.
It annotates `node.props["evoltype"]`; it does not restore ETE 3's `dup`
feature.

Reconciliation:

```python
reconciled_tree, events = gene_tree.reconcile(species_tree)
```

Gene-family operations:

```python
tree_count, duplication_count, speciation_trees = tree.get_speciation_trees(
    autodetect_duplications=True,
    newick_only=False,
    prop="species",
)
for speciation_tree in speciation_trees:
    process(speciation_tree)

subfamilies = tree.split_by_dups(autodetect_duplications=True)
collapsed_copy = tree.collapse_lineage_specific_expansions(return_copy=True)
```

Species overlap and reconciliation answer different questions. Species overlap
uses label overlap between child clades; reconciliation requires a species
tree and can infer losses.

## TreePattern

ETE 4 can search for repeated subtree shapes:

```python
from ete4 import Tree
from ete4.treematcher import TreePattern

tree = Tree("((K,((A,B),C),D),(E,F));")
three_way_split = TreePattern("(,,)", safer=True)

matches = list(three_way_split.search(tree))
print([node.id for node in matches])
```

Child order is not significant during topology matching. `TreePattern` also
supports Python conditions embedded in pattern nodes, but those conditions
must be static, trusted code. Never construct an expression-bearing pattern
from user input, file content, model output, or other untrusted text; use
topology-only patterns or ordinary Python traversal predicates instead.

## Visualization Entry Points

```python
tree.explore()                              # SmartView browser
tree.render_sm("tree.png", w=1200, h=800) # SmartView PNG screenshot
tree.render("tree.svg")                    # Qt treeview extra
```

For custom imports and renderer requirements, see `visualization.md`.

## Error Handling

Catch narrow exceptions at an application boundary and retain context:

```python
from pathlib import Path

from ete4 import Tree

path = Path("tree.nw")
try:
    with path.open(encoding="utf-8") as handle:
        tree = Tree(handle, parser=1)
except (OSError, ValueError) as exc:
    raise RuntimeError(f"Could not parse {path} with parser 1") from exc
```

Do not use a bare `except:` around parsing or topology edits; it hides schema
mistakes and missing-node errors.

## Upstream References

- Tree tutorial: https://etetoolkit.github.io/ete/tutorial/tutorial_trees.html
- Tree API: https://etetoolkit.github.io/ete/reference/reference_tree.html
- PhyloTree tutorial: https://etetoolkit.github.io/ete/tutorial/tutorial_phylogeny.html
- PhyloTree API: https://etetoolkit.github.io/ete/reference/reference_phylo.html
- Parsers: https://etetoolkit.github.io/ete/reference/reference_parsers.html
- Tree matcher tutorial:
  https://etetoolkit.github.io/ete/tutorial/tutorial_treematcher.html
- Tree matcher API:
  https://etetoolkit.github.io/ete/reference/reference_treematcher.html
- Migration: https://etetoolkit.github.io/ete/3to4.html
