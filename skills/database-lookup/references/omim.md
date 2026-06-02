# OMIM (Online Mendelian Inheritance in Man) API Reference

## Base URL
```
https://api.omim.org/api
```

## Authentication
**API key REQUIRED.** Request at https://omim.org/api (free for academic/non-commercial use).
- Pass as query parameter: `?apiKey=YOUR_API_KEY`
- All requests require the key; unauthenticated requests are rejected.

## Rate Limits
Not publicly documented in detail. Reasonable usage expected per terms of service.

## Response Format
JSON (with `&format=json`) or XML (default). Always append `&format=json` for JSON responses.

## Key Endpoints

### 1. Entry Lookup (by MIM number)
```
GET https://api.omim.org/api/entry?mimNumber={mim_number}&apiKey={key}&format=json
```
Example:
```
GET https://api.omim.org/api/entry?mimNumber=141900&apiKey=YOUR_KEY&format=json
```
Returns entry with title, text, gene map, allelic variants, references.

### 2. Entry with Specific Includes
```
GET https://api.omim.org/api/entry?mimNumber=141900&include=text&include=allelicVariantList&include=geneMap&apiKey={key}&format=json
```
Include options: `text`, `clinicalSynopsis`, `geneMap`, `allelicVariantList`, `referenceList`, `existFlags`, `externalLinks`.

### 3. Search Entries
```
GET https://api.omim.org/api/entry/search?search={query}&apiKey={key}&format=json
```
Example — search for "Marfan syndrome":
```
GET https://api.omim.org/api/entry/search?search=marfan+syndrome&apiKey=YOUR_KEY&format=json&start=0&limit=10
```

### 4. Search with Filters
```
GET https://api.omim.org/api/entry/search?search={query}&filter=gene&apiKey={key}&format=json
```
Filter options: `gene`, `phenotype`, `clinical_synopsis`, etc.

### 5. Gene Map Lookup
```
GET https://api.omim.org/api/geneMap?chromosome={chrom}&apiKey={key}&format=json
```
Example:
```
GET https://api.omim.org/api/geneMap?chromosome=17&apiKey=YOUR_KEY&format=json&start=0&limit=10
```

### 6. Gene Map Search
```
GET https://api.omim.org/api/geneMap/search?search={query}&apiKey={key}&format=json
```

### 7. Clinical Synopsis Search
```
GET https://api.omim.org/api/clinicalSynopsis/search?search={query}&apiKey={key}&format=json
```

## Response Structure
```json
{
  "omim": {
    "version": "1.0",
    "entryList": [
      {
        "entry": {
          "mimNumber": 141900,
          "status": "live",
          "titles": {
            "preferredTitle": "HEMOGLOBIN S; HBS",
            "alternativeTitles": "SICKLE CELL ANEMIA"
          },
          "textSectionList": [...],
          "geneMap": {
            "chromosome": "11",
            "cytoLocation": "11p15.4",
            "geneSymbols": "HBB"
          }
        }
      }
    ]
  }
}
```

## Pagination
Use `start` and `limit` query parameters:
```
&start=0&limit=20
```

## MIM Number Types
- **Asterisk (*)**: Gene
- **Plus (+)**: Gene with known phenotype
- **Number sign (#)**: Phenotype (molecular basis known)
- **Percent (%)**: Phenotype (molecular basis unknown)
- **Null**: Other entry types

## Notes
- OMIM data is copyrighted; API access is free for academic use but requires registration.
- The API does not support bulk downloads; use OMIM downloads page with separate agreement.
- Cross-reference MIM numbers with ClinVar, NCBI Gene, and HPO for integrated disease analysis.
