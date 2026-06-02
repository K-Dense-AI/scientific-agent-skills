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
- `itemsPerPage` -- results per page (default: 250, max: 250)

## Key Endpoints

### Gene expression (median by tissue)
```
GET /expression/medianGeneExpression?gencodeId=ENSG00000139618.17&datasetId=gtex_v8
```
Parameters:
- `gencodeId` -- Versioned Ensembl gene ID (required)
- `datasetId` -- `gtex_v8` (required)
- `tissueSiteDetailId` -- filter to specific tissue (optional)

Returns median TPM per tissue for the gene.

### Gene expression (all, for a tissue)
```
GET /expression/medianGeneExpression?tissueSiteDetailId=Liver&datasetId=gtex_v8
```

### Single-tissue eQTLs
```
GET /association/singleTissueEqtl?gencodeId=ENSG00000139618.17&tissueSiteDetailId=Whole_Blood&datasetId=gtex_v8
```
Parameters:
- `gencodeId` -- Versioned Ensembl gene ID (required)
- `tissueSiteDetailId` -- tissue ID (required)
- `datasetId` -- `gtex_v8` (required)

### Multi-tissue eQTLs
```
GET /association/multiTissueEqtl?gencodeId=ENSG00000139618.17&datasetId=gtex_v8
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
GET /expression/medianExonExpression?gencodeId=ENSG00000139618.17&datasetId=gtex_v8
```

### Transcript expression
```
GET /expression/medianTranscriptExpression?gencodeId=ENSG00000139618.17&datasetId=gtex_v8
```

### Top expressed genes in a tissue
```
GET /expression/topExpressedGene?tissueSiteDetailId=Brain_Cortex&datasetId=gtex_v8&filterMtGene=true
```

### Variant by location (dyadic)
```
GET /association/dyneqtl?variantId=chr1_1000000_A_G_b38&gencodeId=ENSG00000139618.17&tissueSiteDetailId=Whole_Blood&datasetId=gtex_v8
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
      "gencodeId": "ENSG00000139618.17",
      "geneSymbol": "BRCA2",
      "median": 4.523,
      "tissueSiteDetailId": "Whole_Blood",
      "unit": "TPM"
    },
    {
      "datasetId": "gtex_v8",
      "gencodeId": "ENSG00000139618.17",
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
- GTEx v8 is the primary dataset; always specify `datasetId=gtex_v8`
- Gene IDs must be versioned GENCODE IDs (e.g., ENSG00000139618.17)
- Use the gene search endpoint to resolve symbols to versioned GENCODE IDs
- `gencodeVersion=v26` corresponds to GTEx v8
