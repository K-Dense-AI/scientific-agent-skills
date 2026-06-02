# NCBI GEO (Gene Expression Omnibus) via E-utilities

## Base URLs

| Purpose | URL |
|---|---|
| E-utilities | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` |
| GEO direct query | `https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi` |

## Important: The database name is `gds`

The Entrez database for GEO is `gds` (not `geo`). It contains all GEO record types: GDS datasets, GSE series, GPL platforms, GSM samples. Filter by type using `[ETYP]` in the search term.

## Key Endpoints

### eSearch — Search GEO

```
GET /esearch.fcgi?db=gds&term={query}&retmode=json&retmax={n}
```

Parameters:
- `db=gds` (required)
- `term` — search query with field tags
- `retmax` — max results (default 20)
- `retstart` — offset for pagination
- `retmode=json` — get JSON response
- `usehistory=y` — store results server-side for large queries
- `api_key` — NCBI API key (optional, raises rate limit)

#### Entry type filters (`[ETYP]`)
- `gds[ETYP]` — curated GEO DataSets
- `gse[ETYP]` — GEO Series (most common, use this by default)
- `gpl[ETYP]` — platforms
- `gsm[ETYP]` — samples

#### Other field tags
- `[Organism]` — e.g. `"Homo sapiens"[Organism]`
- `[PDAT]` — publication date
- `[Title]` — title search
- Boolean: `AND`, `OR`, `NOT` (uppercase)

Example — cancer GSE series in human:
```
/esearch.fcgi?db=gds&term=cancer+AND+gse[ETYP]+AND+"Homo+sapiens"[Organism]&retmax=10&retmode=json
```

Response:
```json
{
  "esearchresult": {
    "count": "15432",
    "retmax": "10",
    "idlist": ["200012345", "200067890"],
    "querytranslation": "cancer AND gse[ETYP]"
  }
}
```

The IDs returned are numeric UIDs (not accession numbers). For GSE records: UID = 200000000 + GSE_number.

### eSummary — Get metadata for UIDs

```
GET /esummary.fcgi?db=gds&id={uid_list}&retmode=json
```

Key response fields per record:
- `Accession` — e.g. "GSE12345"
- `title`, `summary`
- `taxon` — organism
- `entrytype` — "GDS", "GSE", "GPL", "GSM"
- `gdstype` — e.g. "Expression profiling by array"
- `n_samples` — sample count
- `pubmedids` — linked PubMed IDs
- `PDAT` — publication date
- `Samples` — array of sample objects
- `FTPLink` — data download path

Example:
```
/esummary.fcgi?db=gds&id=200012345&retmode=json
```

### GEO Direct Query — Full records by accession

```
GET https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}&form={format}&view={detail}
```

Parameters:
- `acc` — GEO accession (GSE12345, GDS1234, GPL570, GSM12345)
- `targ` — `self`, `gsm` (samples), `gpl` (platform), `gse` (series)
- `form` — `text` (SOFT format), `xml` (MINiML), `html`
- `view` — `quick`, `brief`, `full`, `data`

Example — series metadata in SOFT:
```
acc.cgi?acc=GSE53757&targ=self&form=text&view=brief
```

Note: acc.cgi does not return JSON. Use eSearch + eSummary for JSON results. Use acc.cgi when you need full SOFT/MINiML records.

### eLink — Cross-reference with other NCBI databases

```
GET /elink.fcgi?dbfrom=gds&db=pubmed&id={uid}&retmode=json
```

## Practical Workflow

For most queries, use this two-step approach:

1. **eSearch** to find UIDs matching the query
2. **eSummary** to get metadata for those UIDs

This gives you JSON throughout.

## Important Notes

- GDS records are mostly frozen — NCBI stopped curating new GDS. Use `gse[ETYP]` for comprehensive results.
- eFetch has limited support for the `gds` database. Use eSummary for metadata or acc.cgi for full records.
- URL-encode spaces as `+` and quotes as `%22`.

## Rate Limits

- **Without API key**: 3 requests/second
- **With API key**: 10 requests/second (free registration at ncbi.nlm.nih.gov/account/settings)
- Include `&email=user@example.com` as a courtesy
- For large result sets, use the History server (`usehistory=y` then pass `WebEnv` and `query_key` to eSummary)
