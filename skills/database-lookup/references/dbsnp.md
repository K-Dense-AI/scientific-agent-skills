# dbSNP API Reference

## Overview
SNP and variant data. Accessible via two APIs: NCBI E-utilities (`db=snp`) for search/metadata, and the NCBI Variation Services REST API for detailed variant annotations.

## Base URLs
```
E-utilities:  https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
Variation API: https://api.ncbi.nlm.nih.gov/variation/v0/
```

## Authentication
- **E-utilities**: API key recommended (`&api_key=KEY`). 3 req/sec without, 10 req/sec with key.
- **Variation API**: No auth required. Rate limits apply (undocumented; be respectful, ~1-2 req/sec).

---

## E-utilities Endpoints (db=snp)

### 1. ESearch -- Search SNPs
```
GET esearch.fcgi?db=snp&term=QUERY&retmax=N&retmode=json
```

**Example -- search SNPs in BRCA1 gene:**
```
GET esearch.fcgi?db=snp&term=BRCA1[Gene Name] AND homo sapiens[Organism]&retmax=5&retmode=json
```
Response:
```json
{
  "esearchresult": {
    "count": "12847",
    "idlist": ["80357713", "80357508", ...]
  }
}
```
Note: IDs returned are rs numbers without the "rs" prefix.

### 2. ESummary -- SNP summaries
```
GET esummary.fcgi?db=snp&id=IDS&retmode=json
```

**Example -- get summary for rs334 (sickle cell variant):**
```
GET esummary.fcgi?db=snp&id=334&retmode=json
```
Response includes: `snp_id`, `chr`, `chrpos`, `genes`, `clinical_significance`, `global_mafs`, `docsum`.

### 3. EFetch -- Fetch SNP details (XML only)
```
GET efetch.fcgi?db=snp&id=IDS&rettype=json&retmode=text
```
Note: EFetch for dbSNP returns JSON with `rettype=json`. Also supports XML with `retmode=xml`.

---

## Variation Services API

### 1. Lookup variant by rsID
```
GET /variation/v0/refsnp/{rsid}
```

**Example:**
```
GET https://api.ncbi.nlm.nih.gov/variation/v0/refsnp/334
```
Response (JSON, abbreviated):
```json
{
  "refsnp_id": "334",
  "create_date": "2000/09/19",
  "primary_snapshot_data": {
    "placements_with_allele": [...],
    "allele_annotations": [...],
    "support": [...]
  },
  "present_obs_movements": [
    {
      "component_ids": [{"type": "clinvar", "value": "..."}],
      "observation": {
        "seq_id": "NC_000011.10",
        "position": 5227002,
        "deleted_sequence": "T",
        "inserted_sequence": "A"
      }
    }
  ]
}
```

### 2. Lookup variant by SPDI notation
```
GET /variation/v0/spdi/{spdi}/rsids
```
SPDI format: `SeqID:Position:Deletion:Insertion`

**Example:**
```
GET https://api.ncbi.nlm.nih.gov/variation/v0/spdi/NC_000011.10:5227002:T:A/rsids
```

### 3. Lookup variant by HGVS
```
GET /variation/v0/hgvs/{hgvs}/contextuals
```

**Example:**
```
GET https://api.ncbi.nlm.nih.gov/variation/v0/hgvs/NC_000011.10:g.5227003T>A/contextuals
```

### 4. Batch rsID lookup (POST)
```
POST /variation/v0/refsnp/batch
Content-Type: application/json

{"refsnp_ids": ["334", "1805007", "7412"]}
```

## Common E-utilities Search Patterns
```
# By rs number
term=334[RS ID]

# Clinical significance
term=pathogenic[Clinical Significance] AND BRCA1[Gene Name]

# By chromosome position (GRCh38)
term=11[Chromosome] AND 5227002:5227002[Base Position]

# By variant type
term=missense[Function Class] AND TP53[Gene Name]

# By global minor allele frequency
term=0.01:0.05[Global MAF]
```

## Rate Limits
- E-utilities: 3 req/sec (no key), 10 req/sec (with key)
- Variation Services API: No published limit; recommend 1-2 req/sec
