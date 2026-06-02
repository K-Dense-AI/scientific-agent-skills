# KEGG REST API

## Base URL
```
https://rest.kegg.jp
```

## Auth
No API key required. Free for academic use. Commercial use requires license.

## Important: KEGG returns tab-delimited text and flat-file format, NOT JSON.

## Key Operations (URL-path-based, no query parameters)

| URL Pattern | Description |
|-------------|-------------|
| `/list/{database}` | List all entries |
| `/list/{database}/{organism}` | List entries for organism |
| `/get/{dbentries}` | Get entry data (flat-file) |
| `/get/{dbentries}/image` | Pathway image (PNG) |
| `/get/{dbentries}/kgml` | Pathway as KGML XML |
| `/find/{database}/{query}` | Search by keyword |
| `/find/{database}/{query}/formula` | Search by molecular formula |
| `/find/{database}/{value}/exact_mass` | Search by exact mass |
| `/link/{target_db}/{source_db}` | Find linked entries between databases |
| `/link/{target_db}/{dbentries}` | Links for specific IDs |
| `/conv/{target_db}/{dbentries}` | Cross-reference ID conversion |
| `/ddi/{dbentries}` | Drug-drug interactions |

## Database Codes

| Code | Database | Example ID |
|------|----------|------------|
| `pathway` | Pathways | `hsa00010` |
| `compound` | Compounds | `C00001` |
| `drug` | Drugs | `D00001` |
| `enzyme` | Enzymes | `ec:1.1.1.1` |
| `genes`/`hsa` | Genes | `hsa:10458` |
| `disease` | Diseases | `H00001` |
| `reaction` | Reactions | `R00001` |
| `ko` | KO orthologs | `K00001` |

## Example Calls

```
# List human pathways
https://rest.kegg.jp/list/pathway/hsa

# Get pathway entry
https://rest.kegg.jp/get/hsa00010

# Search compounds by name
https://rest.kegg.jp/find/compound/aspirin

# Search by molecular formula
https://rest.kegg.jp/find/compound/C9H8O4/formula

# Find pathways for a gene
https://rest.kegg.jp/link/pathway/hsa:10458

# Find diseases for a gene
https://rest.kegg.jp/link/disease/hsa:672

# Convert KEGG to PubChem IDs
https://rest.kegg.jp/conv/pubchem/C00001

# Get multiple entries (max 10, joined with +)
https://rest.kegg.jp/get/C00001+C00002+C00003

# Drug-drug interactions
https://rest.kegg.jp/ddi/D00564+D00110
```

## Response Format
Tab-delimited text for list/find/link/conv. Flat-file text for get. **No JSON support.**

## Rate Limits
No published limits. Keep to a few requests per second. Batch up to 10 IDs per `/get` with `+`. May return HTTP 403 if too many requests.
