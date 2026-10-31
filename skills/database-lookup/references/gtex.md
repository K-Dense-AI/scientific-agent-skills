# GTEx (Genotype-Tissue Expression) API Reference

## Overview
GTEx catalogs gene expression levels across human tissues from postmortem donors,
enabling study of tissue-specific gene regulation and eQTLs.

## Base URL
`https://gtexportal.org/api/v2`

## Auth
None required (public, unauthenticated).

## Response Format
JSON. Most endpoints return paginated results with structure:
```json
{
  "data": [ ... ],
  "paging_info": {
    "numberOfPages": 10,
    "page": 0,
    "maxItemsPerPage": 250
  }
}
```

## Pagination Parameters (common to most endpoints)
- `page` -- 0-indexed page number (default: 0)
- `itemsPerPage` -- results per page (default: 250; current schema maximum: 100000, use small pages)

## Key Endpoints

### Gene expression (median by tissue)
```
GET /expression/medianGeneExpression?gencodeId=ENSG00000139618.14&datasetId=gtex_v8
```
Parameters:
- `gencodeId` -- Versioned Ensembl gene ID (required)
- `datasetId` -- `gtex_v8` (explicit historical selection; defaults vary by endpoint)
- `tissueSiteDetailId` -- filter to specific tissue (optional)

Returns median TPM per tissue for the gene.

### Highly expressed genes for a tissue
```
GET /expression/topExpressedGene?tissueSiteDetailId=Liver&datasetId=gtex_v8
```

### Single-tissue eQTLs
```
GET /association/singleTissueEqtl?gencodeId=ENSG00000139618.14&tissueSiteDetailId=Whole_Blood&datasetId=gtex_v8
```
Parameters:
- `gencodeId` -- Versioned Ensembl gene ID (optional filter)
- `tissueSiteDetailId` -- tissue ID (optional filter)
- `datasetId` -- `gtex_v8` (explicit historical selection; defaults vary by endpoint)

### Multi-tissue eQTLs
```
GET /association/metasoft?gencodeId=ENSG00000139618.14&datasetId=gtex_v8
```

### Gene search
```
GET /reference/gene?geneId=BRCA2&gencodeVersion=v26&genomeBuild=GRCh38/hg38
```
Parameters:
- `geneId` -- gene symbol or Ensembl ID
- `gencodeVersion` -- `v26` for GTEx v8
- `genomeBuild` -- `GRCh38/hg38`

### List tissues
```
GET /dataset/tissueSiteDetail?datasetId=gtex_v8
```
Returns all tissue site detail IDs, names, colors, sample counts.

### Exon expression
```
GET /expression/medianExonExpression?gencodeId=ENSG00000139618.14&datasetId=gtex_v8
```

### Transcript expression
```
GET /expression/medianTranscriptExpression?gencodeId=ENSG00000139618.14&datasetId=gtex_v8
```

### Top expressed genes in a tissue
```
GET /expression/topExpressedGene?tissueSiteDetailId=Brain_Cortex&datasetId=gtex_v8&filterMtGene=true
```

### Dynamic eQTL query for a gene–variant–tissue combination
```
GET /association/dyneqtl?variantId=chr1_1000000_A_G_b38&gencodeId=ENSG00000139618.14&tissueSiteDetailId=Whole_Blood&datasetId=gtex_v8
```

## Tissue ID examples
Use the underscore-separated names exactly:
- `Whole_Blood`, `Liver`, `Brain_Cortex`, `Heart_Left_Ventricle`
- `Muscle_Skeletal`, `Adipose_Subcutaneous`, `Lung`, `Skin_Sun_Exposed_Lower_leg`

## Example response (median gene expression)
```json
{
  "data": [
    {
      "datasetId": "gtex_v8",
      "gencodeId": "ENSG00000139618.14",
      "geneSymbol": "BRCA2",
      "median": 4.523,
      "tissueSiteDetailId": "Whole_Blood",
      "unit": "TPM"
    },
    {
      "datasetId": "gtex_v8",
      "gencodeId": "ENSG00000139618.14",
      "geneSymbol": "BRCA2",
      "median": 12.87,
      "tissueSiteDetailId": "Testis",
      "unit": "TPM"
    }
  ],
  "paging_info": { "numberOfPages": 1, "page": 0, "maxItemsPerPage": 250 }
}
```

## Rate Limits
- No published rate limits
- Reasonable request pacing recommended (~1-2 req/sec)
- For bulk analysis, download full datasets from the GTEx Portal downloads page

## Notes
- These examples intentionally pin the historical GTEx v8 dataset. Current expression and single-tissue eQTL endpoints default to `gtex_v10`, while metasoft/dyneqtl default to v8. Specify the dataset and resolve gene IDs using its compatible GENCODE release; do not mix gene versions across datasets.
- Gene IDs must be versioned GENCODE IDs (e.g., ENSG00000139618.14)
- Use the gene search endpoint to resolve symbols to versioned GENCODE IDs
- `gencodeVersion=v26` corresponds to GTEx v8

Official schema: https://gtexportal.org/api/v2/openapi.json
