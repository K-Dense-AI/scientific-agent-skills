# cBioPortal API

## Base URL
```
https://www.cbioportal.org/api
```

## Auth
No authentication for the public instance. Private/institutional instances (e.g. `genie.cbioportal.org`) require a data access token via `Authorization: Bearer <token>` header.

## Common Headers
```
Accept: application/json
Content-Type: application/json
```

## Common Query Parameters

Most list endpoints support these:

| Parameter | Type | Description | Default |
|---|---|---|---|
| `projection` | string | Detail level: `ID`, `SUMMARY`, `DETAILED`, `META` | `SUMMARY` |
| `pageNumber` | int | Zero-based page index | `0` |
| `pageSize` | int | Results per page | `10000000` |
| `sortBy` | string | Property to sort by | varies |
| `direction` | string | `ASC` or `DESC` | `ASC` |

## Key Endpoints

### Studies

| Method | Endpoint | Description |
|---|---|---|
| GET | `/studies` | List all cancer studies |
| GET | `/studies/{studyId}` | Get a single study |
| POST | `/studies/fetch` | Fetch multiple studies by ID |

Example:
```
GET https://www.cbioportal.org/api/studies?projection=SUMMARY&pageSize=10
GET https://www.cbioportal.org/api/studies/brca_tcga
```

Response fields: `studyId`, `name`, `description`, `cancerTypeId`, `pmid`, `citation`, `allSampleCount`, `referenceGenome`, `publicStudy`, `importDate`

### Cancer Types

| Method | Endpoint | Description |
|---|---|---|
| GET | `/cancer-types` | List all cancer types |
| GET | `/cancer-types/{cancerTypeId}` | Get one cancer type |

Response fields: `cancerTypeId`, `name`, `shortName`, `dedicatedColor`, `parent`

### Genes

| Method | Endpoint | Description |
|---|---|---|
| GET | `/genes` | List all genes (paginated) |
| GET | `/genes/{geneId}` | Gene by Hugo symbol or Entrez ID |
| GET | `/genes/{geneId}/aliases` | Gene aliases |
| POST | `/genes/fetch` | Fetch multiple genes |

Example:
```
GET https://www.cbioportal.org/api/genes/TP53
```
Response: `{"entrezGeneId": 7157, "hugoGeneSymbol": "TP53", "type": "protein-coding"}`

### Molecular Profiles

| Method | Endpoint | Description |
|---|---|---|
| GET | `/molecular-profiles` | All profiles across all studies |
| GET | `/studies/{studyId}/molecular-profiles` | Profiles in a study |
| GET | `/molecular-profiles/{molecularProfileId}` | Single profile |

Profile types (`molecularAlterationType`): `MUTATION_EXTENDED`, `COPY_NUMBER_ALTERATION`, `MRNA_EXPRESSION`, `PROTEIN_LEVEL`, `METHYLATION`

Example:
```
GET https://www.cbioportal.org/api/studies/brca_tcga/molecular-profiles
```

### Mutations

| Method | Endpoint | Description |
|---|---|---|
| GET | `/molecular-profiles/{profileId}/mutations` | Mutations in a profile |
| POST | `/molecular-profiles/{profileId}/mutations/fetch` | Filtered mutation query |
| POST | `/mutations/fetch` | Multi-profile mutation fetch |

Parameters for GET:
| Parameter | Type | Description |
|---|---|---|
| `sampleListId` | string | Sample list to query (e.g. `brca_tcga_all`) |
| `entrezGeneId` | int | Filter by gene |
| `projection` | string | `SUMMARY`, `DETAILED`, `ID`, `META` |

Example — TP53 mutations in TCGA breast cancer:
```
GET https://www.cbioportal.org/api/molecular-profiles/brca_tcga_mutations/mutations?sampleListId=brca_tcga_all&entrezGeneId=7157&projection=DETAILED
```

POST body for multi-gene fetch:
```json
{
  "sampleListId": "brca_tcga_all",
  "entrezGeneIds": [7157, 672]
}
```

Response fields: `entrezGeneId`, `sampleId`, `patientId`, `proteinChange`, `mutationType`, `mutationStatus`, `chr`, `startPosition`, `endPosition`, `referenceAllele`, `variantAllele`, `variantType`, `ncbiBuild`, `tumorAltCount`, `tumorRefCount`

### Copy Number Alterations

| Method | Endpoint | Description |
|---|---|---|
| GET | `/molecular-profiles/{profileId}/discrete-copy-number` | CNA data |
| POST | `/molecular-profiles/{profileId}/discrete-copy-number/fetch` | Filtered CNA query |
| POST | `/discrete-copy-number/fetch` | Multi-profile CNA fetch |

### Molecular Data (expression, methylation)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/molecular-profiles/{profileId}/molecular-data` | Expression/methylation data |
| POST | `/molecular-data/fetch` | Multi-profile molecular data fetch |

### Clinical Data

| Method | Endpoint | Description |
|---|---|---|
| GET | `/studies/{studyId}/clinical-data` | Clinical data for a study |
| POST | `/clinical-data/fetch` | Multi-study clinical data |
| GET | `/studies/{studyId}/clinical-attributes` | Available clinical attributes |

Parameters for GET:
| Parameter | Type | Description |
|---|---|---|
| `clinicalDataType` | string | `PATIENT` or `SAMPLE` |
| `attributeId` | string | e.g. `OS_STATUS`, `OS_MONTHS`, `CANCER_TYPE` |

Example:
```
GET https://www.cbioportal.org/api/studies/brca_tcga/clinical-data?clinicalDataType=PATIENT&attributeId=OS_STATUS&projection=SUMMARY
```

### Patients & Samples

| Method | Endpoint | Description |
|---|---|---|
| GET | `/studies/{studyId}/patients` | Patients in a study |
| GET | `/studies/{studyId}/samples` | Samples in a study |
| POST | `/patients/fetch` | Multi-study patient fetch |
| POST | `/samples/fetch` | Multi-study sample fetch |

### Sample Lists

| Method | Endpoint | Description |
|---|---|---|
| GET | `/studies/{studyId}/sample-lists` | Predefined sample groups |
| GET | `/sample-lists/{sampleListId}` | Single sample list |

### Gene Panels

| Method | Endpoint | Description |
|---|---|---|
| GET | `/gene-panels` | All gene panels |
| GET | `/gene-panels/{genePanelId}` | Panel details with gene list |
| POST | `/gene-panel-data/fetch` | Which panels cover which samples |

### Treatments

| Method | Endpoint | Description |
|---|---|---|
| POST | `/treatments/patient` | Patient-level treatment data |
| POST | `/treatments/sample` | Sample-level treatment data |

### System

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Server health check |
| GET | `/info` | Portal version, DB schema version |

## Typical Workflow

1. **Find studies**: `GET /studies` — browse available cancer studies, get `studyId` values
2. **Get molecular profiles**: `GET /studies/{studyId}/molecular-profiles` — find profile IDs (e.g. `brca_tcga_mutations`, `brca_tcga_gistic`)
3. **Get sample lists**: `GET /studies/{studyId}/sample-lists` — find sample list IDs (e.g. `brca_tcga_all`, `brca_tcga_sequenced`)
4. **Query data**: Use the profile ID and sample list ID to fetch mutations, CNA, expression, or clinical data

## Rate Limits

No published rate limits. Be courteous — avoid hammering with many concurrent requests. For bulk data needs, cBioPortal offers downloadable datasets at https://docs.cbioportal.org/downloads/.

## Tips

- **Study IDs** follow a pattern: `{cancer_type}_{source}` (e.g. `brca_tcga`, `luad_tcga`, `prad_mskcc_2017`)
- **Molecular profile IDs** extend the study ID: `{studyId}_mutations`, `{studyId}_gistic`, `{studyId}_rna_seq_v2_mrna`
- Use `projection=DETAILED` to get the richest response including nested objects
- POST `/fetch` endpoints are for batch queries across multiple studies, genes, or samples — they're the most flexible way to query
- Gene lookup accepts both Hugo symbols (`TP53`) and Entrez IDs (`7157`)
- The Swagger UI at https://www.cbioportal.org/api/swagger-ui/index.html documents every endpoint interactively
