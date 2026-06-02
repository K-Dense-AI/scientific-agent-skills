# GWAS Catalog (EBI)

## Base URL
```
https://www.ebi.ac.uk/gwas/rest/api
```

## Auth
No API key required.

## Note: Responses use HAL+JSON format with `_links` and `_embedded` keys.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/studies/{accession}` | Single study (e.g. GCST001633) |
| `/studies/search/findByPubmedId?pubmedId={id}` | Studies by PubMed ID |
| `/singleNucleotidePolymorphisms/{rsId}` | SNP details |
| `/singleNucleotidePolymorphisms/{rsId}/associations` | Associations for a SNP |
| `/singleNucleotidePolymorphisms/search/findByRsId?rsId={rsId}` | Search by rsID |
| `/associations` | List associations |
| `/associations/{id}` | Single association |
| `/efoTraits` | List EFO traits |
| `/efoTraits/search/findByEfoTrait?trait={name}` | Search traits |

## Pagination
`?page=0&size=20` (zero-indexed, max ~500)

## Example Calls
```
# Get a study
https://www.ebi.ac.uk/gwas/rest/api/studies/GCST001633

# Associations for a SNP
https://www.ebi.ac.uk/gwas/rest/api/singleNucleotidePolymorphisms/rs7329174/associations

# Search traits
https://www.ebi.ac.uk/gwas/rest/api/efoTraits/search/findByEfoTrait?trait=diabetes&page=0&size=5
```

## Response Format
HAL+JSON. Results in `_embedded.studies[]` or `_embedded.associations[]`. Key fields: `pvalue`, `riskFrequency`, `orPerCopyNum`, `betaNum`.

## Rate Limits
No published limit. Bulk data via FTP at ftp.ebi.ac.uk/pub/databases/gwas/
