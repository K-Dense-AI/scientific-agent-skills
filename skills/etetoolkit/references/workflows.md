---
title: ETE 4 Workflows
description: Markdown guide to validated tree-analysis patterns with ETE 4.4.0.
---

# ETE 4 Workflows

Complete patterns for common ETE 4.4.0 tasks. Adapt parsers and biological
assumptions to the actual data source.

## Guide Map

- Validate names, branch lengths, and support before analysis
- Preprocess and root an existing tree reproducibly
- Compare rooted or unrooted topologies
- Join metadata without silently dropping records
- Detect evolutionary events or reconcile against a species tree
- Split duplicated gene families
- Query NCBI or GTDB taxonomy
- Batch-process and cache large trees
- Hand off clustering and tree inference to the right upstream tools
- Match trusted topology patterns

The fenced Python snippets are examples within this Markdown guide, not a
single executable program. Run only the section needed for the current task.

## 1. Validate Before Analysis

Name-based operations and tree comparisons become unreliable when labels are
empty or duplicated.

```python
from collections import Counter
from pathlib import Path

from ete4 import Tree


def load_and_validate(path: Path, parser=1) -> Tree:
    with path.open(encoding="utf-8") as handle:
        tree = Tree(handle, parser=parser)

    names = list(tree.leaf_names())
    empty = [leaf.id for leaf in tree.leaves() if not leaf.name]
    duplicate_counts = {
        name: count
        for name, count in Counter(names).items()
        if name and count > 1
    }

    if empty:
        raise ValueError(f"{path}: unnamed leaves at positions {empty[:10]}")
    if duplicate_counts:
        raise ValueError(f"{path}: duplicate leaf names {duplicate_counts}")
    if len(names) < 2:
        raise ValueError(f"{path}: expected at least two leaves")

    return tree


tree = load_and_validate(Path("tree.nw"), parser=1)
```

Also verify that the parsed support and branch-length ranges are plausible for
the program that produced the tree:

```python
supports = [
    node.support
    for node in tree.traverse()
    if not node.is_leaf and node.support is not None
]
distances = [
    node.dist
    for node in tree.traverse()
    if not node.is_root and node.dist is not None
]

if any(distance < 0 for distance in distances):
    raise ValueError("Negative branch length detected")

print("support range:", (min(supports), max(supports)) if supports else None)
print("distance range:", (min(distances), max(distances)) if distances else None)
```

Support may be represented as fractions or percentages. Do not apply a
threshold before checking its scale.

## 2. Reproducible Tree Preprocessing

```python
from pathlib import Path

from ete4 import Tree

input_path = Path("inferred_tree.nw")
output_path = Path("processed_tree.nw")

with input_path.open(encoding="utf-8") as handle:
    tree = Tree(handle, parser="support")

# Keep a known sample set and preserve retained pairwise distances.
keep = ["sample_A", "sample_B", "sample_C", "outgroup"]
missing = sorted(set(keep) - set(tree.leaf_names()))
if missing:
    raise ValueError(f"Requested leaves are absent: {missing}")

tree.prune(keep, preserve_branch_length=True)

# Prefer a biological outgroup when justified.
tree.set_outgroup(tree["outgroup"])

# Stable presentation order only; this does not alter clade membership.
tree.ladderize()

tree.write(
    outfile=str(output_path),
    parser="support",
    props=[],
)
```

Record the original input checksum, ETE version, parser, retained sample set,
rooting rule, and output parser in an analysis manifest.

## 3. Midpoint Rooting

Midpoint rooting is useful when a defensible biological outgroup is not
available, but it assumes the longest leaf-to-leaf path can approximate a
clock-like split.

```python
from ete4 import Tree

tree = Tree("((A:1,B:1):1,(C:2,D:2):1);")
tree.set_midpoint_outgroup()
print(tree.write(props=[]))
```

For auditability:

```python
tree = Tree("((A:1,B:1):1,(C:2,D:2):1);")
candidate = tree.get_midpoint_outgroup()
candidate_id = candidate.id
tree.set_outgroup(candidate)
print("midpoint candidate:", candidate_id)
```

Do not describe midpoint rooting as evidence for the direction of evolution.

## 4. Compare Two Trees

```python
from collections import Counter
from pathlib import Path

from ete4 import Tree


def load(path: Path, parser=1) -> Tree:
    with path.open(encoding="utf-8") as handle:
        return Tree(handle, parser=parser)


def assert_unique_leaf_names(tree: Tree, label: str) -> None:
    counts = Counter(tree.leaf_names())
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    if duplicates:
        raise ValueError(f"{label} has duplicate leaves: {duplicates}")


tree_a = load(Path("method_a.nw"))
tree_b = load(Path("method_b.nw"))
assert_unique_leaf_names(tree_a, "method_a")
assert_unique_leaf_names(tree_b, "method_b")

(
    rf,
    max_rf,
    common,
    edges_a,
    edges_b,
    discarded_a,
    discarded_b,
) = tree_a.robinson_foulds(
    tree_b,
    unrooted_trees=True,
)

print(
    {
        "rf": rf,
        "max_rf": max_rf,
        "normalized_rf": rf / max_rf if max_rf else 0.0,
        "common_leaf_count": len(common),
        "discarded_edges_a": len(discarded_a),
        "discarded_edges_b": len(discarded_b),
    }
)
```

Checklist:

- Rooted and unrooted RF answer different questions.
- ETE compares the intersection when leaf sets differ; report its size.
- Duplicate labels violate the usual tip-identity assumption.
- Support filtering and polytomy expansion materially change results.
- A high RF distance does not explain which biological split is preferable.

For a higher-level result:

```python
summary = tree_a.compare(tree_b, unrooted=True)
print(summary["rf"], summary["max_rf"], summary["norm_rf"])
```

Keep labels unique. Do not use `Tree.compare(has_duplications=True)` in ETE
4.4.0; upstream marks that TreeKO branch as likely broken. The packaged
`ete4 compare` CLI also fails because it still passes the removed `format=`
keyword, so use the methods above or `scripts/tree_operations.py compare`.

## 5. Annotate a Tree from a Metadata Table

Keep parsing and schema validation explicit.

```python
import csv
from pathlib import Path

from ete4 import Tree

tree = Tree("((sample_1,sample_2),sample_3);")

metadata: dict[str, dict[str, str]] = {}
with Path("metadata.tsv").open(encoding="utf-8", newline="") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    required = {"sample", "host", "location"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError(f"metadata.tsv must contain columns {sorted(required)}")
    for row in reader:
        sample = row["sample"].strip()
        if not sample or sample in metadata:
            raise ValueError(f"Empty or duplicate metadata key: {sample!r}")
        metadata[sample] = {
            "host": row["host"].strip(),
            "location": row["location"].strip(),
        }

unmatched_tree = []
for leaf in tree.leaves():
    values = metadata.get(leaf.name)
    if values is None:
        unmatched_tree.append(leaf.name)
        continue
    leaf.add_props(**values)

unmatched_metadata = sorted(set(metadata) - set(tree.leaf_names()))
if unmatched_tree or unmatched_metadata:
    raise ValueError(
        f"Unmatched tree leaves={unmatched_tree}; "
        f"unmatched metadata rows={unmatched_metadata}"
    )

tree.write(
    outfile="annotated.nhx",
    props=["host", "location"],
)
```

Use an explicit `props` list when exporting. `props=None` writes every
available property and may disclose internal annotations unintentionally.

## 6. Species-Overlap Event Detection

```python
from ete4 import PhyloTree

gene_tree = PhyloTree(
    "((Hsa|gene1,Ptr|gene1),(Hsa|gene2,Mmu|gene1));",
    sp_naming_function=lambda name: name.split("|", 1)[0],
)

events = gene_tree.get_descendant_evol_events(sos_thr=0.0)
for event in events:
    relationship = {
        "S": "orthology",
        "D": "paralogy",
    }[event.etype]
    print(
        relationship,
        sorted(event.in_seqs),
        sorted(event.out_seqs),
    )

for node in gene_tree.traverse():
    event_type = node.props.get("evoltype")
    if event_type:
        print(node.id, event_type)
```

Interpretation limits:

- The gene tree must be rooted and fully bifurcating.
- Pass the species naming function explicitly; ETE 4.4.0 defaults it to `None`.
- Results depend on the topology and the species naming function.
- A single shared species triggers duplication at `sos_thr=0.0`.
- Gene loss, incomplete lineage sorting, horizontal transfer, and tree error
  can violate a simple species-overlap interpretation.
- Keep inferred events separate from curated orthology evidence.

## 7. Gene-Tree/Species-Tree Reconciliation

```python
from ete4 import PhyloTree

gene_newick = (
    "((Dme_001,Dme_002),"
    "(((Cfa_001,Mms_001),((Hsa_001,Ptr_001),Mmu_001)),"
    "(Ptr_002,(Hsa_002,Mmu_002))));"
)
species_newick = "((((Hsa,Ptr),Mmu),(Mms,Cfa)),Dme);"

species_from_gene = lambda name: name.split("_", 1)[0]

gene_tree = PhyloTree(
    gene_newick,
    sp_naming_function=species_from_gene,
)
species_tree = PhyloTree(
    species_newick,
    sp_naming_function=lambda name: name,
)

gene_species = {leaf.species for leaf in gene_tree.leaves()}
species_tree_tips = set(species_tree.leaf_names())
missing = sorted(gene_species - species_tree_tips)
if missing:
    raise ValueError(f"Species absent from species tree: {missing}")

reconciled_tree, events = gene_tree.reconcile(species_tree)

for event in events:
    if event.etype == "S":
        print("orthology", event.inparalogs, event.orthologs)
    elif event.etype == "D":
        print("paralogy", event.inparalogs, event.outparalogs)

reconciled_tree.write(
    outfile="reconciled.nhx",
    props=["evoltype"],
)
```

Reconciliation assumes the species tree and species mapping are correct. State
the species-tree source and treatment of uncertain branches.

## 8. Split Duplicated Gene Families

```python
from pathlib import Path

from ete4 import PhyloTree

tree = PhyloTree(
    "((Human_1,Chimp_1),(Human_2,(Chimp_2,Mouse_1)));",
    sp_naming_function=lambda name: name.split("_", 1)[0],
)

output_dir = Path("subfamilies")
output_dir.mkdir(parents=True, exist_ok=True)

for index, subtree in enumerate(tree.split_by_dups(), start=1):
    subtree.write(
        outfile=str(output_dir / f"subfamily_{index:03d}.nw"),
        props=[],
    )
```

For TreeKO-style enumeration, `get_speciation_trees()` can generate very many
topologies. Consider `newick_only=True`, monitor output size, and define a
scientifically justified limit before materializing results.

```python
tree_count, duplication_count, newicks = tree.get_speciation_trees(
    newick_only=True,
)
for newick in newicks:
    process(newick)
```

## 9. NCBI and GTDB Taxonomy

NCBI topology:

```python
from ete4 import NCBITaxa

ncbi = NCBITaxa()
taxids = [9606, 9598, 10090]
tree = ncbi.get_topology(taxids, intermediate_nodes=False, annotate=True)
print(tree.to_str(props=["sci_name", "rank", "taxid"]))
```

GTDB topology:

```python
from ete4 import GTDBTaxa

gtdb = GTDBTaxa()
taxa = ["p__Huberarchaeota", "o__Peptococcales", "f__Korarchaeaceae"]
tree = gtdb.get_topology(taxa, intermediate_nodes=True, annotate=True)
print(tree.to_str(props=["sci_name", "rank"]))
```

See `taxonomy.md` before downloading, updating, or annotating production data.

## 10. Batch Processing

```python
from pathlib import Path

from ete4 import Tree

input_dir = Path("trees")
output_dir = Path("processed")
output_dir.mkdir(parents=True, exist_ok=True)

for input_path in sorted(input_dir.glob("*.nw")):
    with input_path.open(encoding="utf-8") as handle:
        tree = Tree(handle, parser="support")

    names = list(tree.leaf_names())
    if len(names) != len(set(names)):
        raise ValueError(f"{input_path}: duplicate leaf names")

    tree.set_midpoint_outgroup()
    tree.ladderize()

    output_path = output_dir / input_path.name
    tree.write(
        outfile=str(output_path),
        parser="support",
        props=[],
    )
```

Do not catch and discard parse exceptions in a batch. Fail with the source
path, or record failures in a structured report and return a nonzero status.

## 11. Large Trees

Prefer generators:

```python
for leaf in tree.leaves():
    process(leaf)
```

Materialize only when indexing, sorting, or repeated traversal requires it:

```python
leaves = list(tree.leaves())
```

Cache descendant content for repeated clade calculations:

```python
leaf_cache = tree.get_cached_content(prop="name")
for node in tree.traverse("postorder"):
    descendant_names = leaf_cache[node]
    summarize(node, descendant_names)
```

Use SmartView for adaptive exploration. Static rendering of every label on a
very large tree is usually unreadable and expensive; use collapsed-node layouts
or render selected subtrees.

## 12. Clustering Dendrograms

ETE 4.4.0 does not export ETE 3's `ClusterTree`. For a clustering workflow:

1. Compute linkage and validation metrics with SciPy or another maintained
   clustering package.
2. Convert the resulting hierarchy to Newick or construct an ETE `Tree`.
3. Store cluster labels or statistics as node properties.
4. Use SmartView layouts to display those properties.

Do not claim that ETE 4 calculated silhouette, Dunn, or matrix-linked
`ClusterTree` metrics unless another library actually performed those steps.

## 13. End-to-End Phylogenomic Handoff

A defensible division of labor is:

1. Perform sequence quality control outside ETE.
2. Align sequences with MAFFT or a domain-appropriate aligner.
3. Infer topology/support with IQ-TREE 2, FastTree, or another explicit method.
4. Load the inferred Newick into ETE with the correct parser.
5. Validate tip identity and support scale.
6. Root, prune, annotate, compare, or reconcile in ETE.
7. Render and export with explicit properties.
8. Report both inference-tool settings and ETE transformation settings.

ETE manipulates and interprets the supplied topology; it does not make upstream
model choice, alignment quality, or sampling bias disappear.

## 14. Match Repeated Topologies

Use a topology-only `TreePattern` when the structural pattern is easier to
state as a small tree:

```python
from ete4 import Tree
from ete4.treematcher import TreePattern

tree = Tree("((K,((A,B),C),D),(E,F));")
pattern = TreePattern("(,,)", safer=True)

for match in pattern.search(tree):
    print("three-child node:", match.id, match.name)
```

The matcher tries child permutations, so sibling order does not prevent a
topological match. Expression-bearing patterns are executable conditions:
never construct them from user input, imported data, model output, or other
untrusted text. Prefer topology-only patterns or explicit traversal predicates
for dynamic criteria.

## Upstream References

- Tree tutorial: https://etetoolkit.github.io/ete/tutorial/tutorial_trees.html
- Phylogenetic tutorial: https://etetoolkit.github.io/ete/tutorial/tutorial_phylogeny.html
- Taxonomy tutorial: https://etetoolkit.github.io/ete/tutorial/tutorial_taxonomy.html
- Tree matcher tutorial:
  https://etetoolkit.github.io/ete/tutorial/tutorial_treematcher.html
- Tree API: https://etetoolkit.github.io/ete/reference/reference_tree.html
