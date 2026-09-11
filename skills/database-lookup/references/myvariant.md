# MyVariant.info

A cached bundle of annotations (CADD, dbNSFP, ClinVar snippets, dbSNP)
keyed by **hg19** genomic HGVS. Use it as a "what else is already stored?"
pass, then confirm any score you will write at the live source — Ensembl
VEP with `CADD=1` (`ensembl.md` §6), not this cache.

Docs: https://docs.myvariant.info/en/latest/
All figures verified 2026-09-10.

## Endpoints

```
GET https://myvariant.info/v1/query?q={rsID or text}
GET https://myvariant.info/v1/variant/{hg19_id}
```

`/variant/` ids look like `chr17:g.7578406C>G`. That is hg19. A GRCh38
`g.` string on this endpoint 404s.

## Verified calls

```
GET /v1/query?q=rs28934578
```

HTTP 200. First hit:

| Field | Value |
| --- | --- |
| `_id` | `chr17:g.7578406C>G` |
| `cadd.phred` | **35** |
| `hg19.start` | 7578406 |

Live CADD via VEP (`CADD=1`) for GRCh38 `17:7675088 C>G` the same day was
**29.4**. If you report 35 as "the CADD score," you are reporting a cache.

```
GET /v1/variant/chr17:g.7674220G>A
GET /v1/variant/chr17:g.7674220G>A?assembly=hg38
GET /v1/variant/chr17:g.7577538G>A
```

All HTTP 404. `assembly=hg38` does not make a GRCh38 `g.` id valid here.
Query by rsID, then use the returned `_id` if you need `/variant/`.

## Traps

- Default genome for `_id` is hg19. Write that down.
- Cached `cadd.phred` is not live CADD v1.7. Treat a gap of ≥ 0.5 PHRED
  as "this is not the score to write."
- ClinVar fields here are a snippet. For a clinical assertion go to
  `clinvar.md`.
- Last call, not first. Do not start an annotation here and skip VEP.
