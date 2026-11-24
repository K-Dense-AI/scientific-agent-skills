# GWAS Catalog (EBI)

## Base URL
```
https://www.ebi.ac.uk/gwas/rest/api/v2
```

The legacy v1 API (`/gwas/rest/api/...` without `/v2`, including every
`/search/findBy...` finder) returns HTTP 410 Gone. Calls below were checked on
2026-11-24; counts are observations from that date, not guarantees.

## Auth
No API key required.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/studies/{accession_id}` | Single study (e.g. GCST001633) |
| `/studies?pubmed_id={id}` | Studies from one publication |
| `/studies/{accession_id}/ancestries` | Discovery/replication ancestry records |
| `/associations?rs_id={rsId}` | Associations for a variant |
| `/associations?accession_id={GCST}` | Associations reported by one study |
| `/associations?efo_id={id}` | Associations mapped to a trait term |
| `/associations/{association_id}` | Single association |
| `/single-nucleotide-polymorphisms/{rsId}` | Variant details (GRCh38 location, MAF, consequence) |
| `/single-nucleotide-polymorphisms?chromosome={c}&bp_start={s}&bp_end={e}` | Catalog variants in a region |
| `/efo-traits?efo_trait={text}` | Trait search by label |
| `/efo-traits/{efo_id}` | Single trait term (e.g. MONDO_0005148) |
| `/publications/{pubmed_id}` | Publication metadata and author list |
| `/genes/{gene_name}` | Gene record |

Filters are query parameters in snake_case: `pubmed_id`, `accession_id`,
`rs_id`, `efo_id`, `efo_trait`, `mapped_gene`, `extended_geneset`,
`show_child_trait`, `full_pvalue_set`. The full parameter list per endpoint is
in the OpenAPI spec at `https://www.ebi.ac.uk/gwas/rest/api/v2/reference/api-docs`.

## Pagination and sorting
`?page=0&size=20` (zero-indexed, default 20, maximum 500; `size=501` returns
HTTP 400). Read `page.totalElements` and follow `_links.next.href` until it is
absent. Sort with `sort={field}&direction=asc|desc`; the Spring-style
`sort=p_value,asc` returns HTTP 400.

## Example Calls
```
# Get a study
https://www.ebi.ac.uk/gwas/rest/api/v2/studies/GCST001633

# Associations for a SNP
https://www.ebi.ac.uk/gwas/rest/api/v2/associations?rs_id=rs7329174

# Search traits
https://www.ebi.ac.uk/gwas/rest/api/v2/efo-traits?efo_trait=type%202%20diabetes%20mellitus&size=5

# Strongest associations for a trait term
https://www.ebi.ac.uk/gwas/rest/api/v2/associations?efo_id=MONDO_0005148&sort=p_value&direction=asc&size=20
```

## Response Format
Collections are under `_embedded.studies[]`, `_embedded.associations[]`,
`_embedded.snps[]`, `_embedded.efo_traits[]` or `_embedded.publications[]`.
Association fields: `p_value`, `pvalue_mantissa`, `pvalue_exponent`,
`or_value`/`or_per_copy_num` (present only when an odds ratio was reported),
`beta`, `ci_lower`, `ci_upper`, `risk_frequency`, `snp_effect_allele`,
`snp_allele[].effect_allele`, `efo_traits[]`, `accession_id`, `pubmed_id`,
`locations`, `mapped_genes`. The v1 fields `pvalue`, `riskFrequency`,
`orPerCopyNum` and `betaNum` no longer exist.

## Traps
- `p_value` underflows to `0.0` for very small p-values, so sorting by it
  cannot rank those rows. Use `pvalue_mantissa` and `pvalue_exponent`:
  rs7903146-T in GCST90492734 has `p_value: 0.0`, mantissa 3, exponent -1315.
- `beta` is a string that carries the direction in words (`"0.0211 unit
  decrease"`) or `"-"` when absent. `risk_frequency` is also a string.
- The effect allele can be unknown: `snp_effect_allele` such as `rs7903146-?`
  (19 of 353 rs7903146 associations). Do not harmonise those rows.
- `efo_trait=` matches labels partially (`type 2 diabetes mellitus` also
  returns `age of onset of type 2 diabetes mellitus`). Use `efo_id` for
  exact trait queries.
- `show_child_trait=true` adds descendant-term annotations; the default is
  direct annotations only. The migration guide spells it `show_child_traits`,
  which the server ignores without error. Compare `totalElements` with and
  without it when completeness matters: asthma (MONDO_0004979) gave 3,236 and
  4,134 associations.
- `mapped_gene` defaults to `extended_geneset=false` (mapped plus nearest
  up/downstream genes, as on the website). Set `extended_geneset=true` to
  reproduce the broader v1 gene set.
- Documented rate limit: 15 requests per second; calls above it are slowed.

## Bulk data
Full summary statistics are not served by this API; check
`full_summary_stats_available` on the study and download from
https://ftp.ebi.ac.uk/pub/databases/gwas/.

Docs: https://www.ebi.ac.uk/gwas/rest/api/v2/docs.
Migration from v1: https://www.ebi.ac.uk/gwas/docs/news/rest-api-v2-migration-guide/.
