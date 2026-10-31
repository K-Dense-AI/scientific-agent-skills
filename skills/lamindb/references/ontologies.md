# Bionty ontology management

Targets Bionty 2.5.0 with LaminDB 2.10.0. Install/mount `bionty` when creating the
instance (`lamin init --modules bionty`). Public source discovery/downloads need
network access; local registry operations can run offline after records exist.

## Registries and source provenance

Bionty exposes Gene, Protein, Organism, CellMarker, CellType, CellLine, Tissue,
Disease, Phenotype, Pathway, ExperimentalFactor, DevelopmentalStage, and
Ethnicity registries. Available source releases depend on the Source catalogue;
inspect it rather than assuming every registry has one universal ontology.
Common examples include Ensembl genes, CL cell types, Uberon tissues, and Mondo
or DOID diseases. There is no `bt.Drug` registry in this release. Perturbation
compounds belong to the separately documented `pertdb` module.

```python
import lamindb as ln
import bionty as bt

bt.Source.filter(entity="bionty.CellType").to_dataframe(limit=None)
source = bt.Source.get(entity="bionty.CellType", currently_used=True)
# Record source.uid, name, version, organism, url and md5 where available.
```

For reproducibility select and retain an explicit Source UID after reviewing the
available catalogue; `currently_used` is mutable configuration, not a permanent
release pin. Importing a whole ontology writes many records to the active instance:

```python
# Network/registry-writing examples, not executed during this refresh.
bt.CellType.import_source(source=source)
t_cell = bt.CellType.from_source(ontology_id="CL:0000084", source=source)
if t_cell is None or isinstance(t_cell, list):
    raise ValueError("Expected one unambiguous T-cell record")
t_cell.save()
```

`from_source()` returns an unsaved record, a list for ambiguity, or `None` if no
match. `import_source(source=...)` expects a **Source record**, not `"mondo"` or
`"doid"`. For Disease, first filter `bt.Source` by `entity="bionty.Disease"`,
name, and version, select one Source, then pass that object.

## Validate and standardize without losing unmatched values

For known local labels:

```python
values = ["T cell", "B cell"]
standardized = bt.CellType.standardize(values, field=bt.CellType.name)
valid = bt.CellType.validate(standardized, field=bt.CellType.name)
if not valid.all():
    unresolved = [value for value, ok in zip(standardized, valid) if not ok]
    raise ValueError(f"Unresolved cell types: {unresolved}")
records = bt.CellType.from_values(standardized, field=bt.CellType.name)
records.save()
# Only link after all source values have passed the intended validation.
# artifact.cell_types.add(*records)
```

`validate()` returns a boolean array. `standardize()` returns values, retaining
unresolved inputs when it cannot map them; it is not proof of validity.
`from_values()` can search local records/synonyms and public sources and omit
unmatched terms. Its returned `SQLRecordList` can contain unsaved records; call
`.save()` before relation linking. A shorter result must not silently discard
observations from the dataset. For source-exact validation use the selected
`source` and `strict_source=True` where required by the study.

Public lookup (`bt.CellType.lookup(public=True)`) is for discovery. Exact
ontology IDs provide stronger identity than display names; review homonyms,
obsolete terms, and one-to-many mappings before replacing annotations. Keep the
original labels and an explicit mapping artifact when harmonizing studies.

## Organisms and gene identifiers

```python
human = bt.Organism.get(name="human")  # must already be registered
bt.Gene.filter(organism=human).search("CD8").to_dataframe()
valid = bt.Gene.validate(
    ["ENSG00000141510"], field=bt.Gene.ensembl_gene_id, organism=human
)
```

`Gene.search(..., organism="human")` is not a supported signature. Filter first
and search the QuerySet. `Gene.validate/from_values/import_source` do support
an organism argument. Gene symbols are organism-specific and can be ambiguous;
prefer stable IDs, record their release and any version-suffix conversion.
Bionty registration does not establish orthology; cross-species mapping requires
an explicitly sourced orthology resource.

## Hierarchies and custom terms

A small offline pattern, also covered by regression tests:

```python
parent = bt.CellType(name="Example parent cell").save()
child = bt.CellType(name="Example child cell").save()
child.parents.add(parent)
child.add_synonym("Example alias")
assert list(bt.CellType.standardize(["Example alias"])) == ["Example child cell"]

child.parents.to_dataframe()         # direct parents
child.query_parents().to_dataframe() # recursive ancestry, all branches
parent.children.to_dataframe()       # direct children
parent.query_children().to_dataframe()
```

Ontology graphs can have multiple parents. Following only `.parents.first()`
drops valid ancestry. Custom terms should not receive fabricated ontology IDs.
Do not assert biologically narrower/broader concepts as synonyms without review.
`add_synonym()` imports IPython in this release; include it in environments using
that helper. `view_parents()` additionally needs Graphviz for rendering.

To query a parent and its descendants, include the parent itself explicitly:

```python
terms = [parent, *parent.query_children()]
ln.Artifact.filter(cell_types__in=terms).distinct().to_dataframe()
```

Use a schema-backed curator for DataFrame/AnnData annotation when column-level
provenance matters; direct `artifact.cell_types.add(...)` alone records labels
but does not validate the table's contents.

Sources: [ontology guide](https://docs.lamin.ai/manage-ontologies),
[Bionty API](https://docs.lamin.ai/bionty),
[Bionty source](https://github.com/laminlabs/bionty),
[released curation implementation](https://github.com/laminlabs/lamindb/blob/2.10.0/lamindb/models/can_curate.py).
