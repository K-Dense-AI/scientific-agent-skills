# COSMIC (Catalogue of Somatic Mutations in Cancer)

## Base URL
```
https://cancer.sanger.ac.uk/cosmic/api/v1/
```

## Auth
**Registration required.** Free academic account or paid commercial license.

Login to get JWT token:
```
POST /auth/login
Content-Type: application/json
{"email": "you@example.com", "password": "yourpassword"}
```
Pass token as: `Authorization: Bearer <token>`

## Key Endpoints

### Search mutations by gene
```
GET /mutations/search?q={gene_symbol}&page=1&page_size=5
```

### Get gene information
```
GET /genes/{gene_symbol}
```
Example: `/genes/BRAF`

Response includes: gene_symbol, gene_name, chromosome, cancer_census (bool), tier, mutation_count, sample_count

### Get specific mutation by COSMIC ID
```
GET /mutations/{cosmic_mutation_id}
```
Example: `/mutations/COSV56056643`

Response includes: gene, cds_mutation, aa_mutation, mutation_type, fathmm_prediction, genomic_coordinates, tissue_distribution

### Cancer Gene Census
```
GET /cancer-gene-census?tier=1&page_size=10
```

### Mutations by tissue/histology
```
GET /mutations/distribution/{gene_symbol}
```

## Rate Limits
Not officially published. Bulk data requires SFTP download (licensed).

## Important
- COSMIC requires authentication for all API calls
- Commercial use requires a paid license
- Bulk data access via SFTP is preferred over API for large queries
- API structure may change across COSMIC versions
