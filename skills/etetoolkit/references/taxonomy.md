# NCBI and GTDB Taxonomy with ETE 4

ETE 4.4.0 provides local SQLite-backed interfaces for:

- **NCBI Taxonomy** through `NCBITaxa`
- **Genome Taxonomy Database (GTDB)** through `GTDBTaxa`

Both can translate identifiers, retrieve ranks and lineages, find descendants,
construct minimal connecting topologies, and annotate `PhyloTree` objects.

## Storage and First Use

The official tutorial's approximate **600 MB NCBI** and **72 MB GTDB** figures
should be treated as local first-use footprint estimates, not compressed
network download sizes. Archives vary by release and can be much smaller.

Parsed databases are stored under `~/.local/share/ete/` by default. Allow space
for the downloaded archive, parsed SQLite database, traversal cache, and
temporary conversion files. Do not create or refresh a database unexpectedly
in a constrained or offline job.

No API key or credential is required.

## Constructors

```python
from ete4 import GTDBTaxa, NCBITaxa

ncbi = NCBITaxa(
    dbfile=None,
    taxdump_file=None,
    memory=False,
    update=True,
)

gtdb = GTDBTaxa(
    dbfile=None,
    taxdump_file=None,
    memory=False,
)
```

Important controls:

- `dbfile`: explicit parsed SQLite path
- `taxdump_file`: local taxonomy archive used to create/update a database
- `memory=True`: load the database into memory for repeated queries
- `update=False` on `NCBITaxa`: disable the constructor's schema-update path

When the database is absent, construction creates/downloads it. An existing
database is not refreshed to newer taxonomy content merely because
`update=True`; call `update_taxonomy_database()` explicitly when a content
refresh is intended.

For a reproducible or offline analysis, provide an explicit `dbfile` and use
the same file across runs.

## Explicit Updates

Latest NCBI taxonomy:

```python
from ete4 import NCBITaxa

ncbi = NCBITaxa(update=False)
ncbi.update_taxonomy_database()
```

Latest GTDB taxonomy:

```python
from ete4 import GTDBTaxa

gtdb = GTDBTaxa()
gtdb.update_taxonomy_database()
```

From an already acquired local archive:

```python
ncbi.update_taxonomy_database("taxdump.tar.gz")
gtdb.update_taxonomy_database("gtdb_taxdump.tar.gz")
```

For production provenance, record:

- Source database (NCBI or GTDB)
- Acquisition date and upstream release when available
- Archive and parsed-database checksums
- ETE version
- Any filtering or rank limit

Do not replace a shared database in the middle of a multi-step analysis.

### ETE 4.4.0 updater caveats

- NCBI refreshes download the official taxdump and verify its MD5 sidecar.
- GTDB refreshes use ETE's converted NCBI-like dump, not a direct GTDB
  database file.
- The ETE 4.4.0 GTDB freshness check requests an MD5 sidecar that is absent
  from the current ETE-data location, so a nominal update can redownload data
  instead of reporting it current.
- Taxonomy conversion creates temporary files in the process working
  directory. Run updates in a controlled, writable workspace and remove
  leftovers if an interrupted update fails.

## NCBI Translation

### Scientific names to TaxIDs

```python
from ete4 import NCBITaxa

ncbi = NCBITaxa()
queries = ["Homo sapiens", "Pan troglodytes", "Mus musculus"]
name_to_taxids = ncbi.get_name_translator(queries)

for query in queries:
    candidates = name_to_taxids.get(query, [])
    if not candidates:
        print("unresolved:", query)
    elif len(candidates) > 1:
        print("ambiguous:", query, candidates)
    else:
        print(query, candidates[0])
```

The translator returns a list because a name can map to multiple taxonomy
records. Do not blindly select index zero without checking ambiguity.

### TaxIDs to names

```python
taxid_to_name = ncbi.get_taxid_translator([9606, 9598, 10090])
print(taxid_to_name)
```

### Ranks and lineage

```python
taxid = 9606
lineage = ncbi.get_lineage(taxid)
names = ncbi.get_taxid_translator(lineage)
ranks = ncbi.get_rank(lineage)

for ancestor in lineage:
    print(ancestor, names.get(ancestor), ranks.get(ancestor, "no rank"))
```

Use `.get()` because not every taxonomy node is guaranteed to have every
requested annotation.

## Descendant Taxa

```python
descendants = ncbi.get_descendant_taxa("Homo")
print(ncbi.translate_to_names(descendants))
```

Collapse below the species level:

```python
species = ncbi.get_descendant_taxa(
    "Homo",
    collapse_subspecies=True,
)
```

Return an ETE tree:

```python
tree = ncbi.get_descendant_taxa(
    "Homo",
    collapse_subspecies=True,
    return_tree=True,
)
print(tree.to_str(props=["sci_name", "taxid", "rank"]))
```

Large internal taxa can have many descendants. Estimate scope before
materializing or printing the complete result.

## NCBI Topology

```python
taxids = [9606, 9598, 10090, 7707, 8782]
tree = ncbi.get_topology(
    taxids,
    intermediate_nodes=False,
    collapse_subspecies=False,
    annotate=True,
)
print(tree.to_str(props=["sci_name", "rank", "taxid"]))
```

Retain every intermediate taxonomy node:

```python
tree = ncbi.get_topology(
    [2, 33208],
    intermediate_nodes=True,
    annotate=True,
)
```

Taxonomy topology is a classification hierarchy. Do not treat branch lengths
or omitted intermediate ranks as a molecular phylogeny.

## GTDB Queries

GTDB identifiers are strings such as:

- `d__Bacteria`
- `p__Firmicutes_B`
- `f__Korarchaeaceae`
- `GB_GCA_020833055.1`
- `RS_GCF_000019605.1`

Do not pass them to `NCBITaxa`, and do not pass NCBI numeric TaxIDs to
`GTDBTaxa`.

### Descendants

```python
from ete4 import GTDBTaxa

gtdb = GTDBTaxa()
descendants = gtdb.get_descendant_taxa("f__Thorarchaeaceae")
print(descendants)
```

### GTDB topology

```python
queries = [
    "p__Huberarchaeota",
    "o__Peptococcales",
    "f__Korarchaeaceae",
]

tree = gtdb.get_topology(
    queries,
    intermediate_nodes=True,
    collapse_subspecies=True,
    annotate=True,
)
print(tree.to_str(props=["sci_name", "rank"]))
```

GTDB and NCBI classifications can disagree because they use different data,
release cycles, nomenclature, and taxonomic frameworks. State which one was
used rather than combining labels without a mapping policy.

## Annotate a PhyloTree with NCBI

### Leaf names are TaxIDs

```python
from ete4 import PhyloTree

tree = PhyloTree("((9606,9598),10090);")
taxid_to_name, taxid_to_lineage, taxid_to_rank = tree.annotate_ncbi_taxa(
    taxid_attr="name",
)

print(tree.to_str(props=["name", "sci_name", "taxid", "rank"]))
```

### Extract TaxIDs from compound names

```python
tree = PhyloTree(
    "((9606|protA,9598|protA),10090|protB);",
    sp_naming_function=lambda name: name.split("|", 1)[0],
)

tree.annotate_ncbi_taxa(taxid_attr="species")
```

### Explicit custom property

```python
tree = PhyloTree("((protA,protB),protC);")

taxids = {
    "protA": 9606,
    "protB": 9598,
    "protC": 10090,
}
for leaf in tree.leaves():
    leaf.add_prop("ncbi_taxid", taxids[leaf.name])

tree.annotate_ncbi_taxa(taxid_attr="ncbi_taxid")
```

Prefer an explicit mapping when names are not stable taxonomy identifiers.

## Annotate a PhyloTree with GTDB

```python
from ete4 import PhyloTree

tree = PhyloTree(
    "((GB_GCA_020833055.1|protA,GB_GCA_003344655.1|protB),"
    "RS_GCF_000019605.1|protC);",
    sp_naming_function=lambda name: name.split("|", 1)[0],
)

tree.annotate_gtdb_taxa(taxid_attr="species")
print(tree.to_str(props=["name", "sci_name", "rank"]))
```

The annotation methods infer internal-node taxonomy from descendants when
possible and return the translators they used. Preserve those mappings when
the analysis needs an auditable record.

## Cache and Offline Pattern

Prepare the database in a controlled networked step:

```python
from ete4 import NCBITaxa

db_path = "taxonomy/ncbi_taxa.sqlite"
ncbi = NCBITaxa(dbfile=db_path, update=False)
ncbi.update_taxonomy_database("taxonomy/taxdump.tar.gz")
```

Use the pinned database without constructor schema updates in analysis jobs:

```python
ncbi = NCBITaxa(
    dbfile="taxonomy/ncbi_taxa.sqlite",
    update=False,
)
```

For a read-only container or cluster job, mount the database at an explicit
path. Avoid relying on an unwritable home-directory default.

## Validation Checklist

Before using taxonomy annotations:

1. Confirm whether identifiers are NCBI or GTDB.
2. Detect unresolved and multiply resolved names.
3. Check that accession prefixes and release conventions match the GTDB
   snapshot.
4. Record database provenance and checksum.
5. Distinguish classification topology from inferred sequence phylogeny.
6. Review rank and scientific-name changes when updating a database.
7. Export only the annotation properties required downstream.

## Upstream References

- Taxonomy tutorial:
  https://etetoolkit.github.io/ete/tutorial/tutorial_taxonomy.html
- Taxonomy API:
  https://etetoolkit.github.io/ete/reference/reference_taxonomy.html
- ETE data repository: https://github.com/etetoolkit/ete-data
- NCBI Taxonomy: https://www.ncbi.nlm.nih.gov/taxonomy
- GTDB: https://gtdb.ecogenomic.org/
