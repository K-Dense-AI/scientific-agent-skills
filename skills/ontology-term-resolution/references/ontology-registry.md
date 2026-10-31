# Ontology registry

Which ontology owns which kind of term, what OLS calls it, and a branch root to constrain against.
Branch IDs/labels below were rechecked through public OLS on 2026-10-01. These are
starting points, not a substitute for the target schema's ontology/release constraints.

## Prefix to OLS ontology id

The OLS ontology id is almost always the lowercased CURIE prefix. Note the exceptions.

| CURIE prefix | OLS id | Covers |
| --- | --- | --- |
| `UBERON` | `uberon` | Anatomy, tissues, organs, body fluids (cross-species) |
| `CL` | `cl` | Cell types |
| `CLO` | `clo` | Cell lines |
| `MONDO` | `mondo` | Diseases (the merged disease ontology; prefer over DOID/NCIT) |
| `DOID` | `doid` | Human Disease Ontology (largely subsumed by MONDO) |
| `HP` | `hp` | Human phenotypic abnormalities — **id is `hp`, not `hpo`**. `HPO` is a Bioregistry synonym; Identifiers.org rejects `HPO:…` |
| `EFO` | `efo` | Experimental factors, assays, platforms, cell lines |
| `CHEBI` | `chebi` | Chemical entities, drugs, metabolites |
| `NCBITaxon` | `ncbitaxon` | Organisms |
| `GO` | `go` | Biological process, molecular function, cellular component |
| `OBI` | `obi` | Assays, devices, protocols, study design |
| `PATO` | `pato` | Qualities — sex, colour, magnitude, `normal` |
| `SO` | `so` | Sequence features |
| `HsapDv` | `hsapdv` | Human developmental stages |
| `MmusDv` | `mmusdv` | Mouse developmental stages |
| `ENVO` | `envo` | Environmental materials and biomes |
| `FOODON` | `foodon` | Food |
| `NCIT` | `ncit` | NCI Thesaurus (clinical/oncology breadth) |
| `MS` | `ms` | Mass spectrometry instruments and methods |
| `BAO` | `bao` | BioAssay descriptions |
| `Orphanet` | **`ordo`** | Rare diseases — id is `ordo`, prefix in CURIEs is `Orphanet`, and OLS reports `preferredPrefix: ORDO` |

For **Cellosaurus** cell-line identity and contamination information, use the
[official Cellosaurus API documentation](https://api.cellosaurus.org/) when OLS does not
carry the needed record. Check service coverage rather than assuming every scientific
vocabulary or accession is an OLS class.

## Branch roots for constraint checks

Pass these to `--branch` to assert a term is the right *kind* of thing.

| Root | Label | Use for |
| --- | --- | --- |
| `UBERON:0001062` | anatomical entity | any anatomy |
| `UBERON:0000465` | material anatomical entity | tissues and organs |
| `CL:0000000` | cell | cell types |
| `MONDO:0700096` | human disease | human disease fields |
| `HP:0000118` | Phenotypic abnormality | phenotype fields |
| `CHEBI:24431` | chemical entity | compounds |
| `NCBITaxon:1` | root | organisms |
| `OBI:0000070` | assay | assay fields |
| `PATO:0000001` | quality | qualities including sex |
| `GO:0008150` | biological_process | GO BP only |
| `GO:0003674` | molecular_function | GO MF only |
| `GO:0005575` | cellular_component | GO CC only |
| `EFO:0000001` | experimental factor | EFO breadth |
| `SO:0000110` | sequence_feature | sequence features |
| `HsapDv:0000001` | life cycle | human developmental stage |
| `MmusDv:0000001` | life cycle | mouse developmental stage |
| `ENVO:00010483` | environmental material | environmental samples |
| `CLO:0000031` | cell line | cell lines |
| `NCIT:C7057` | Disease, Disorder or Finding | NCIT disease subtree |
| `DOID:4` | disease | DOID subtree |

`MONDO:0000001` (`disease`) now resolves by `obo_id`; `MONDO:0700096` is the narrower
human-disease root. Neither is a universal root for nonhuman studies.

A branch check does not substitute for a prefix check. CARO places `cell` under
`anatomical structure`, so cell types pass an anatomy branch test. Constrain both.

## Choosing between overlapping ontologies

- **Disease: MONDO.** It is the merge target for DOID, Orphanet, OMIM, and NCIT disease terms, and
  it carries cross-references back to all of them. Use DOID or NCIT only when a downstream
  consumer demands that namespace.
- **Disease vs phenotype.** MONDO for the diagnosis (`asthma`), HP for the observed abnormality
  (`Wheezing`). Metadata fields usually want one or the other, not either.
- **Tissue vs cell type.** UBERON for the sample's anatomical origin, CL for what the cells are.
  `liver` is UBERON, `hepatocyte` is CL — even though a search for `hepatocyte` restricted to
  `uberon` will return the CL term as an imported copy.
- **Assay: EFO first, OBI second.** Genomics platforms and library strategies are richer in EFO;
  OBI is better for general laboratory assay classes.
- **Chemicals: ChEBI** for anything with a structure. Drug products by trade name belong in
  a drug vocabulary (RxNorm, DrugBank), not ChEBI.
- **Sex: PATO** (`PATO:0000384` male, `PATO:0000383` female) when required by the target
  schema. Preserve distinctions among phenotypic sex, chromosomal sex and gender; do not
  infer one from another or guess from ambiguous codes.
- **"Normal" / healthy control:** some schemas explicitly permit `PATO:0000461` (`normal`)
  for a documented non-diseased state. It is not a filler for missing disease data. A control
  arm, untreated sample, or unknown diagnosis is not sufficient evidence of health.

## Common metadata fields and their expected ontology

These are common choices; both field names and permitted ontologies can change by archive:

| Concept | Ontology |
| --- | --- |
| tissue / organ / anatomical site | UBERON |
| cell type | CL |
| cell line | CLO, or Cellosaurus for identity and contamination status |
| disease | MONDO; schema-specific normal/missing values |
| phenotype | HP |
| organism | NCBITaxon |
| assay / platform | EFO |
| developmental stage | HsapDv, MmusDv |
| sex | PATO |
| chemical / treatment compound | ChEBI |
| environmental material | ENVO |

Submission schemas — CELLxGENE, HCA, ENA/BioSamples checklists, ISA-Tab configurations — pin both
the field names and the permitted ontologies, and they revise them. Read the schema version the
submission targets rather than relying on this table or on memory. A currently valid OLS term can fail a schema
pinned to an older release or restricted subset. For example, consult the current
[CELLxGENE schema source](https://github.com/chanzuckerberg/single-cell-curation/tree/main/schema)
and the specific version used by the submission.
