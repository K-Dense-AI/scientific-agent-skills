# gnomAD (Genome Aggregation Database) API Reference

## Overview
gnomAD aggregates exome and genome sequencing data to provide allele frequencies
and variant annotations across diverse populations.

## API Type: GraphQL
- **Endpoint**: `https://gnomad.broadinstitute.org/api`
- **Method**: POST with JSON body containing GraphQL query
- **Auth**: None required (public, unauthenticated)
- **Response format**: JSON (`data` wrapper with GraphQL structure)

## Key Queries

### Variant lookup by variant ID
Variant IDs use format: `{chrom}-{pos}-{ref}-{alt}` (GRCh37 or GRCh38).

```
POST https://gnomad.broadinstitute.org/api
Content-Type: application/json

{
  "query": "{ variant(variantId: \"1-55516888-G-A\", dataset: gnomad_r4) { variant_id rsids chrom pos ref alt exome { ac an af } genome { ac an af } } }"
}
```

### Gene lookup
```json
{
  "query": "{ gene(gene_symbol: \"BRCA1\", reference_genome: GRCh38) { gene_id symbol chrom start stop strand } }"
}
```

### Variants in a gene
```json
{
  "query": "{ gene(gene_symbol: \"PCSK9\", reference_genome: GRCh38) { variants(dataset: gnomad_r4) { variant_id consequence rsids exome { ac an af } genome { ac an af } } } }"
}
```

### Variants in a region
```json
{
  "query": "{ region(chrom: \"1\", start: 55505222, stop: 55530526, reference_genome: GRCh38) { variants(dataset: gnomad_r4) { variant_id rsids consequence exome { ac af } genome { ac af } } } }"
}
```

### Transcript lookup
```json
{
  "query": "{ transcript(transcript_id: \"ENST00000357654\", reference_genome: GRCh38) { transcript_id gene_id chrom start stop strand } }"
}
```

## Dataset values
- `gnomad_r4` -- gnomAD v4 (GRCh38, latest major release)
- `gnomad_r3` -- gnomAD v3.1.2 (GRCh38, genomes only)
- `gnomad_r2_1` -- gnomAD v2.1.1 (GRCh37, exomes + genomes)

## Population frequency fields
Within `exome` or `genome` objects, population-specific frequencies are available via
`populations { id ac an af }` where `id` values include: `afr`, `amr`, `asj`, `eas`,
`fin`, `mid`, `nfe`, `oth`, `sas`.

## Response example (variant)
```json
{
  "data": {
    "variant": {
      "variant_id": "1-55516888-G-A",
      "rsids": ["rs11591147"],
      "chrom": "1",
      "pos": 55516888,
      "ref": "G",
      "alt": "A",
      "exome": { "ac": 1234, "an": 250000, "af": 0.004936 },
      "genome": { "ac": 456, "an": 150000, "af": 0.00304 }
    }
  }
}
```

## Rate Limits
- No published rate limits, but aggressive querying will be throttled
- Use reasonable request pacing (~1 req/sec recommended)
- For bulk downloads, use gnomAD's Hail tables on Google Cloud or download VCFs

## Notes
- The GraphQL schema is not versioned separately; it tracks the gnomAD web interface
- Use the browser's network inspector on gnomad.broadinstitute.org to discover
  additional query fields and structures
- Structural variants (SV) have a separate query structure (`structural_variant`)
- Constraint metrics (pLI, LOEUF) are available on gene queries via `gnomad_constraint`
