# Dataset resolution: how to find the right `dataset_id` (QTD######)

The eQTL Catalogue identifies each (study × tissue × condition × quantification method) tuple with a `dataset_id` like `QTD000429`. The skill takes a `dataset_id` as input. This reference documents how to resolve a human-readable description (study, tissue, quant method) or an Open Targets `studyId` into the canonical `QTD######`.

## The metadata REST endpoint

`https://www.ebi.ac.uk/eqtl/api/v2/datasets/` returns one JSON record per dataset with these fields:

| Field | Example | Notes |
|---|---|---|
| `dataset_id` | `QTD000429` | the canonical id; pass this to the skill |
| `study_id` | `QTS000024` | per-study group; one study has multiple datasets (different tissues / conditions / quant methods) |
| `study_label` | `Quach_2016` | human-readable; spelling can change between releases (verify with a live fetch before relying) |
| `tissue_label` | `monocyte` | tissue name |
| `tissue_id` | `CL_0002057` | Cell Ontology id |
| `condition_label` | `Influenza_6h` | study-specific stimulation / treatment label; `naive` for unstimulated |
| `sample_group` | `monocyte_IAV` | study × condition shorthand; combines tissue + treatment |
| `quant_method` | `ge` | one of: `ge`, `tx`, `txrev`, `exon`, `leafcutter`, `microarray` (see `quant_methods.md`) |
| `sample_size` | `198` | n samples in the (study × condition × tissue) cell |

The `/datasets/` endpoint accepts query parameters to filter: `study_label`, `quant_method`, `tissue_label`, `condition_label`, `size` (page size), `start` (offset for pagination).

## Resolving by human description

The most common path: a researcher knows *roughly* what they want (e.g., "GTEx whole-blood gene-expression eQTLs") and needs the `dataset_id` to pass to this skill.

```python
import requests

# All GTEx whole-blood gene-expression datasets:
r = requests.get(
    "https://www.ebi.ac.uk/eqtl/api/v2/datasets",
    params={
        "study_label": "GTEx",
        "tissue_label": "blood",
        "quant_method": "ge",
        "size": 10,
    },
    timeout=30,
)
for d in r.json():
    print(d["dataset_id"], d["study_label"], d["tissue_label"], d["condition_label"], d["quant_method"])
# QTD000356 GTEx blood naive ge   <-- this one
```

Then pass `QTD000356` to the skill.

If multiple matches exist (different conditions under the same tissue), the agent should surface the choices to the user, expand each via the user-friendly enum-expansion convention, and ask which one they want.

## Resolving from an Open Targets `studyId`

Open Targets uses a slug convention for QTL studies it pulls from eQTL Catalogue:

```
<study>_<quant>_<sample_group>_<ensg>
```

Example: `quach_2016_ge_monocyte_iav_ensg00000115808`. The trailing `_ensg00000115808` is the Ensembl gene id and is NOT part of the dataset key; the dataset is `(study, quant, sample_group)` = `(quach_2016, ge, monocyte_iav)`.

To resolve:

1. Parse the OT slug, dropping the `_ensg########` suffix.
2. Lower-case the remainder; map underscore-separated tokens to `(study, quant, sample_group)`.
3. Fetch the metadata endpoint with `study_label` (case-insensitively matched against eQTL Catalogue's `study_label`, which is typically Title-cased like `Quach_2016`).
4. Filter the returned datasets by `quant_method` and `sample_group`.
5. The result is a unique `dataset_id`.

```python
ot_study = "quach_2016_ge_monocyte_iav_ensg00000115808"

# Drop ENSG suffix
parts = ot_study.split("_")
ensg_idx = next(i for i, p in enumerate(parts) if p.startswith("ensg"))
study_quant_sample = "_".join(parts[:ensg_idx])
# → "quach_2016_ge_monocyte_iav"

# Find the boundaries: the convention is study label first, then quant method, then sample_group.
# eQTL Catalogue's quant_method values are a fixed enum: {ge, tx, txrev, exon, leafcutter, microarray}.
# Search for any of these in the slug to split.
QUANT_METHODS = {"ge", "tx", "txrev", "exon", "leafcutter", "microarray"}
quant_idx = next(i for i, p in enumerate(parts[:ensg_idx]) if p in QUANT_METHODS)
study_label = "_".join(parts[:quant_idx]).title()        # "Quach_2016"
quant_method = parts[quant_idx]                          # "ge"
sample_group = "_".join(parts[quant_idx+1:ensg_idx])     # "monocyte_iav"

# Fetch
r = requests.get(
    "https://www.ebi.ac.uk/eqtl/api/v2/datasets",
    params={"study_label": study_label, "quant_method": quant_method, "size": 50},
    timeout=30,
)
matches = [d for d in r.json() if d.get("sample_group") == sample_group]
assert len(matches) == 1, f"expected 1 match, got {len(matches)}"
dataset_id = matches[0]["dataset_id"]                    # "QTD000429"
```

## Caveats

- **`study_label` casing can drift between releases.** `quach_2016` (lowercase, from OT slug) maps to `Quach_2016` (Title-cased, eQTL Catalogue convention). Always Title-case before querying.
- **`sample_group` is study-specific.** It combines tissue + condition with study-specific delimiters. The `monocyte_iav` from Quach maps to `monocyte_IAV` in eQTL Catalogue (preserving case in the suffix). When resolving, fetch the candidate datasets and string-compare case-insensitively.
- **Multiple `dataset_id`s per (study × tissue) when conditions differ.** For example, Quach 2016 has `monocyte_naive` (QTD000425), `monocyte_IAV` (QTD000429), `monocyte_LPS` (QTD000433), `monocyte_R848` (QTD000437). Always disambiguate by `condition_label` before passing to the skill.
- **Microarray-era studies live under different `quant_method` values.** The slug `_ge_` indicates RNA-seq gene expression; older microarray-based studies use `_microarray_`. Treat them as distinct quantifications.
- **The `study_id` (QTS######) is NOT the same as `dataset_id` (QTD######).** Many older code samples use `study_id` to navigate the FTP path (`spot/eQTL/sumstats/<QTS>/<QTD>/<QTD>.all.tsv.gz`); both are needed for FTP fetches but only `dataset_id` is the canonical "which dataset" key.

## See also

- `quant_methods.md`: the 6 quantification methods and what `molecular_trait_id` means for each.
- `cis_window_biology.md`: the strand-aware ±1 Mb cis-window applied during nominal-pass eQTL discovery.
- eQTL Catalogue website: `https://www.ebi.ac.uk/eqtl/Studies/` (per-study citation table; required for license attribution).
- Kerimov N. et al. 2021. *A compendium of uniformly processed human gene expression and splicing quantitative trait loci.* Nat Genet 53:1290.
