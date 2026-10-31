# ENCODE (Encyclopedia of DNA Elements)

## Base URL
```
https://www.encodeproject.org
```

## Auth
No auth required. Append `?format=json` or set `Accept: application/json`.

## Portal data objects and search support JSON; file download URLs return file content.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/search/?type=Experiment&format=json` | Search experiments |
| `/experiments/{accession}/?format=json` | Specific experiment |
| `/files/{accession}/?format=json` | File metadata |
| `/biosamples/{accession}/?format=json` | Biosample info |
| `/annotations/?format=json` | Search annotations |

## Search Parameters
- `type` — Experiment, File, Biosample, Annotation, etc.
- `assay_title` — ChIP-seq, RNA-seq, ATAC-seq, etc.
- `target.label` — target protein (e.g. CTCF, H3K27ac)
- `biosample_ontology.term_name` — cell type
- `limit` — results per page
- `field` — specific fields to return

## Example Calls
```
# ChIP-seq experiments for CTCF
https://www.encodeproject.org/search/?type=Experiment&assay_title=ChIP-seq&target.label=CTCF&format=json&limit=5

# Specific experiment
https://www.encodeproject.org/experiments/ENCSR000AAA/?format=json

# Files for an experiment
https://www.encodeproject.org/search/?type=File&dataset=/experiments/ENCSR000AAA/&format=json
```

## Response Format
JSON-LD. Search: `@graph` array + `total` + `facets`. Use `frame=object` or `frame=embedded` to control depth.

## Rate Limits
No published limits. Use `limit=` and `field=` to reduce payload.

Search pagination uses `limit` and `from`; verify `@graph` length against `total`. Preserve file assembly, output_type, status and audit flags before selecting a download. Public reads need no key, while restricted/unreleased objects require authorized access.
