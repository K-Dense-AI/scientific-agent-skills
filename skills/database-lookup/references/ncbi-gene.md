# NCBI Gene (E-utilities)

## Base URL
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
```

## Auth
API key optional but recommended. Without key: 3 req/sec. With key: 10 req/sec.
Free key from: https://www.ncbi.nlm.nih.gov/account/settings/
Pass as: `&api_key=YOUR_KEY`

## Key Endpoints

### eSearch — Search for gene IDs
```
GET /esearch.fcgi?db=gene&term={query}&retmode=json&retmax={n}
```

Parameters:
- `db=gene` (required)
- `term` — search query (e.g. `BRCA1[gene]+AND+human[orgn]`)
- `retmode=json`
- `retmax` — max results (default 20)
- `retstart` — pagination offset

Example:
```
/esearch.fcgi?db=gene&term=BRCA1[gene]+AND+human[orgn]&retmode=json&retmax=5
```

### eSummary — Get gene metadata
```
GET /esummary.fcgi?db=gene&id={gene_ids}&retmode=json
```

Key response fields: `name`, `description`, `chromosome`, `maplocation`, `otheraliases`, `nomenclaturesymbol`, `organism`

Example:
```
/esummary.fcgi?db=gene&id=672&retmode=json
```

### eFetch — Full gene records (XML/text only, no JSON)
```
GET /efetch.fcgi?db=gene&id={gene_ids}&rettype=gene_table&retmode=text
```

### eLink — Cross-database links (gene to PubMed, OMIM, sequences)
```
GET /elink.fcgi?dbfrom=gene&db={target_db}&id={gene_id}&retmode=json
```

Target databases include `pubmed`, `omim`, `nuccore`, and `protein`; discover supported links with EInfo. BioSystems is retired; use current KEGG/Reactome resources for pathways.

Example — gene to PubMed:
```
/elink.fcgi?dbfrom=gene&db=pubmed&id=672&retmode=json
```

## Rate Limits
- Without API key: 3 requests/second
- With API key: 10 requests/second
- For bulk: use `usehistory=y` with eSearch, then retrieve via `query_key` and `WebEnv`
