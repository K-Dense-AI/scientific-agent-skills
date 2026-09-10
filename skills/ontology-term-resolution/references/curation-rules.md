# Curation rules

How to choose among candidates, and what to do when the honest answer is "no term".

## The decision procedure

Run it per string. Stop at the first step that gives a defensible answer.

1. **Exact label match in the expected ontology, from its defining ontology.** Accept.
2. **Exact synonym match.** Accept, but record the primary label, not the synonym. Metadata files
   should carry the ontology's own label so they diff cleanly against the ontology release.
3. **Exact match, wrong ontology.** Usually a category error in the source column, not a naming
   problem — `hepatocyte` in a tissue field means the column mixes tissue and cell type. Fix the
   column, do not force a match.
4. **Partial match only.** Do not accept silently. Either:
   - normalise the input and retry (see below), or
   - present the top candidates with their labels and let a human choose, or
   - mark it unresolved.
5. **Nothing.** Mark unresolved and say so. An unresolved row is a correct output.

`resolve_terms.py` implements steps 1–4's search side and labels every hit `exact_label`,
`exact_synonym`, or `partial`. The judgement about whether a `partial` is acceptable is yours;
the tool will not make it for you.

## Normalisations worth retrying

Cheap rewrites that convert a `partial` into an `exact_label`, in rough order of yield:

- Drop qualifiers the source added: `liver (donor)`, `Liver - left lobe [FFPE]`.
- Expand lab shorthand: `PBMC` → `peripheral blood mononuclear cell`, `WT` → the actual genotype,
  `M`/`F` → `male`/`female`.
- Reverse an inverted phrase: `ventricle, left` → `left ventricle`, `cortex, kidney` → `kidney
  cortex`.
- Singularise: `hepatocytes` → `hepatocyte`. Ontology labels are singular.
- Anglicise or Americanise: ontology labels vary; try both `oesophagus` and `esophagus`.
- Strip species prefixes: `human liver` → `liver` (species belongs in a separate NCBITaxon field).

Do **not** normalise away hyphens, Greek letters, digits, or capitalised gene symbols — `CD4-positive`
and `alpha-beta T cell` mean what they say, and `normalize_label()` deliberately folds only case and
whitespace.

When plain search keeps failing on lab shorthand, run `map_terms.py` with `--ontology` set
(see `companion-apis.md`). ZOOMA matches against how curators previously mapped that exact
string, which is a different and often better signal than lexical search. Every HIGH/GOOD
CURIE still goes through `validate_terms.py` before it is written down.

## What "unresolved" should look like

Never invent an ID to fill a cell. An unresolved row carries the original string, an empty ID, and
the reason. Downstream that is a visible gap; an invented `UBERON:0002108` is a silent error that
survives review because it looks exactly like a real ID.

If a concept genuinely has no term and the project depends on it, the route is a new-term request
to the ontology (GitHub issue on the ontology's tracker, with a definition and a reference), not a
locally minted identifier.

## Auditing an existing metadata table

The high-yield checks, in order:

1. **Every ID exists.** `validate_terms.py --input table.tsv`.
2. **No obsolete IDs.** Obsolete terms carry `term_replaced_by` often enough that the fix is
   mechanical — but apply replacements deliberately, since a replacement can be broader or
   narrower than the original.
3. **Labels match IDs.** Supply the label column. Mismatches are where copy-paste drift and
   hallucinated IDs surface: the ID is real, the label is real, and they describe different things.
4. **Right ontology per column.** `--expect-ontology`.
5. **Right branch per column.** `--branch`, remembering it does not exclude cell types from
   anatomy (`ontology-registry.md`).

`--strict` turns warnings into failures, which is the right setting for a CI gate. Warnings are
`matched_synonym` (label is a synonym rather than the primary label), `imported_only` (the home
ontology no longer asserts this ID), and `not_a_class`.

## Obsolete terms

Obsoletion is not deletion — the ID keeps resolving, and its label is usually prefixed
`obsolete_`. That prefix is a useful smell in any metadata file:

```
EFO:0001067  obsolete_parasitic infection  ->  replaced by MONDO:0005135
```

Some obsolete terms have no replacement, only a `consider` annotation or nothing at all. Then the
term must be re-curated by hand; there is no automatic answer.

## Cross-ontology mapping

OxO is retired and returns HTML with HTTP 200. Two workable routes:

- **Term cross-references.** `term_detail(curie)["annotation"]["database_cross_reference"]` lists
  equivalents — `UBERON:0002107` carries `MESH:D008099`, `NCIT:C12392`, `FMA:7197`, `UMLS:C0023884`,
  and more.
- **SSSOM mapping sets** published by Monarch and the OBO community, when provenance and mapping
  predicates (`skos:exactMatch` vs `closeMatch`) matter.

Cross-references are asserted by curators at varying confidence and are not all `exactMatch`.
Treat a single xref as a lead, not a proof, when the mapping drives analysis rather than display.

```python
from ols_client import term_detail
xrefs = (term_detail("UBERON:0002107") or {}).get("annotation", {}).get(
    "database_cross_reference", []
)
```

## Reporting

When you hand back resolved terms, give the ID *and* the label, and say how each was matched. A
table of bare IDs cannot be reviewed — no reader can tell `UBERON:0002107` from `UBERON:0002108`
by eye, which is precisely why invented IDs survive review.
