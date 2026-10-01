# MyVariant.info

Public annotation aggregation service: `https://myvariant.info/v1`.
[Annotation contract](https://docs.myvariant.info/en/latest/doc/variant_annotation_service.html)
and [query contract](https://docs.myvariant.info/en/latest/doc/variant_query_service.html).

```text
GET /query?q=rs28934578&fields=cadd.phred,dbsnp.rsid&size=5
GET /variant/chr17:g.7578406C%3EG?fields=cadd.phred,dbsnp.rsid
```

`/variant/{id}` uses HGVS genomic identifiers on hg19 as documented. A returned
`hg38` coordinate field does not change the input identifier convention.
An rsID can produce multiple alternate-allele hits; compare alleles and assembly
before selecting a hit. `fields` supports comma-separated fields and dot paths.
Batch POST `/variant` accepts at most 1,000 `ids`; larger inputs can be omitted.
Query results use `hits`, `total`, and pagination parameters `size`/`from`.

Scores are aggregated from particular source releases. Record source and model
versions, genome assembly, alleles, transcript and retrieval date. A difference
between a stored CADD score and an Ensembl VEP score may reflect a release,
assembly or model difference; there is no justified universal PHRED threshold
for declaring a score stale. For clinical classifications, retrieve the full
ClinVar record, review status, condition and conflicting submissions.
