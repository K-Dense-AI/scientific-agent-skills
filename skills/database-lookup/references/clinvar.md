# ClinVar API Reference

## Base URLs
- **NCBI E-utilities**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils`
- **ClinVar web API (VCV)**: `https://www.ncbi.nlm.nih.gov/clinvar`
- **NCBI Variation Services**: `https://api.ncbi.nlm.nih.gov/variation/v0`

## Authentication
- E-utilities: No key required, but **strongly recommended**. Register at https://www.ncbi.nlm.nih.gov/account/ to get an `api_key`.
- Without key: 3 requests/second. With key: 10 requests/second.
- Append `&api_key=YOUR_KEY` to all E-utility requests.

## Rate Limits
- Without API key: 3 req/sec
- With API key: 10 req/sec

## Key Endpoints

### 1. Search ClinVar (esearch)
```
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&term={query}&retmode=json
```
Example — search for BRCA1 pathogenic variants:
```
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&term=BRCA1[gene]+AND+pathogenic[clinical_significance]&retmode=json&retmax=10
```
Returns JSON with `idlist` of ClinVar Variation IDs.

### 2. Fetch ClinVar Records (esummary)
```
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=clinvar&id={id_list}&retmode=json
```
Example:
```
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=clinvar&id=37088,37087&retmode=json
```
Returns JSON with clinical significance, variant name, gene, conditions, review status.

### 3. Full Record (efetch)
```
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=clinvar&id={id}&rettype=vcv&is_variationid&retmode=xml
```
Note: ClinVar efetch returns **XML only** (no JSON for efetch).

### 4. Resolve HGVS/SPDI before searching ClinVar

NCBI Variation Services normalizes variants; it has no `/clinvar` suffix endpoint.
Use `GET https://api.ncbi.nlm.nih.gov/variation/v0/hgvs/{hgvs}/contextuals`,
then `/spdi/{spdi}/rsids`. Search ClinVar with the resolved rsID (or a validated
HGVS expression) using ESearch. An rsID can represent multiple alternate alleles:
compare accession, assembly, position and alleles in the ClinVar record.
SPDI positions are zero-based; HGVS genomic positions are one-based.

### 5. ClinVar VCV/RCV Direct Access
```
GET https://www.ncbi.nlm.nih.gov/clinvar/variation/{variation_id}/?redir=vcv
```
This returns HTML. For programmatic access, use E-utilities or the Variation Services API.

## Useful Search Qualifiers
- `[gene]` — gene symbol (e.g., `BRCA1[gene]`)
- `[clinical_significance]` — pathogenic, likely_pathogenic, benign, uncertain_significance
- `[molecular_consequence]` — missense, nonsense, frameshift, etc.
- `[review_status]` — criteria_provided_single_submitter, reviewed_by_expert_panel, etc.
- `[condition]` — disease name

## Response Format
- esearch/esummary: JSON (with `retmode=json`)
- efetch: XML only for ClinVar
- Variation Services: JSON

## esummary Response Key Fields
```json
{
  "result": {
    "37088": {
      "uid": "37088",
      "title": "NM_003238.6(TGFB2):c.687C>A (p.Cys229Ter)",
      "germline_classification": {
        "description": "Pathogenic",
        "last_evaluated": "2025/09/08 00:00",
        "review_status": "criteria provided, single submitter",
        "fda_recognized_database": "",
        "trait_set": [
          {
            "trait_xrefs": [
              {
                "db_source": "MedGen",
                "db_id": "C3553762"
              },
              {
                "db_source": "MONDO",
                "db_id": "MONDO:0013897"
              },
              {
                "db_source": "OMIM",
                "db_id": "614816"
              }
            ],
            "trait_name": "Loeys-Dietz syndrome 4"
          }
        ]
      },
      "genes": [
        {
          "symbol": "TGFB2",
          "geneid": "7042",
          "strand": "+",
          "source": "submitted"
        }
      ]
    }
  }
}
```

Somatic clinical impact and oncogenicity are separate classifications; inspect
`somatic_clinical_impact` and `oncogenicity` when present. Do not conflate these
with germline classification or discard conflicting submissions.

## Notes
- Combine esearch + esummary for search-then-fetch workflows.
- For bulk downloads, use ClinVar FTP: https://ftp.ncbi.nlm.nih.gov/pub/clinvar/
