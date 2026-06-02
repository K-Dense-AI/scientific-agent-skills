# PubMed (NCBI E-utilities)

PubMed provides citations, abstracts, and metadata for 37M+ biomedical and life science articles. It does NOT contain full text -- for that, use PMC.

## Base URL

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
```

## Authentication

- **API key optional** but recommended. Without: 3 req/sec. With: 10 req/sec.
- Pass as: `&api_key=YOUR_KEY`
- Also include `&tool=your_app_name&email=your@email.com` on all requests.

## Key Endpoints

### 1. eSearch -- Search and get PMIDs

```
GET /esearch.fcgi?db=pubmed&term={query}&retmode=json
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `db` | Yes | -- | `pubmed` |
| `term` | Yes | -- | Search query. Supports PubMed syntax: field tags `[AU]`, `[TI]`, `[TA]`, `[MH]` (MeSH), boolean AND/OR/NOT |
| `retmax` | No | 20 | Max PMIDs returned (max 10,000) |
| `retstart` | No | 0 | Pagination offset |
| `retmode` | No | `xml` | `json` or `xml` |
| `rettype` | No | `uilist` | `uilist` (IDs) or `count` (count only) |
| `sort` | No | `relevance` | `relevance`, `pub_date`, `Author`, `JournalName` |
| `datetype` | No | -- | `pdat` (publication), `mdat` (modification), `edat` (entrez) |
| `mindate` / `maxdate` | No | -- | Date range `YYYY/MM/DD` |
| `reldate` | No | -- | Items from last N days |
| `usehistory` | No | -- | `y` to store on History Server for large result sets |

**Example:**
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=CRISPR+gene+therapy&retmode=json&retmax=5&sort=pub_date
```

**Response:**
```json
{
  "esearchresult": {
    "count": "224107",
    "retmax": "5",
    "retstart": "0",
    "idlist": ["39984857", "39984678", "39984543", "39984210", "39983901"]
  }
}
```

### 2. eSummary -- Get document summaries

```
GET /esummary.fcgi?db=pubmed&id={pmids}&retmode=json
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `db` | Yes | `pubmed` |
| `id` | Yes | Comma-separated PMIDs (max 10,000) |
| `retmode` | No | `json` or `xml` |

**Example:**
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=39984857,39984678&retmode=json
```

**Response fields:** `uid`, `pubdate`, `source` (journal), `authors`, `title`, `volume`, `issue`, `pages`, `fulljournalname`, `elocationid` (DOI), `articleids` (PMC, DOI, etc.), `pubtype`, `pmcrefcount`

### 3. eFetch -- Retrieve full records (abstracts, MEDLINE)

```
GET /efetch.fcgi?db=pubmed&id={pmids}&rettype={type}&retmode={mode}
```

| rettype | retmode | Returns |
|---------|---------|---------|
| *(omit)* | `xml` | Full PubMed XML (citation + abstract) |
| `medline` | `text` | MEDLINE format |
| `abstract` | `text` | Plain text abstract |
| `uilist` | `text` | PMID list |

**Example -- get abstracts as XML:**
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=39984857&retmode=xml
```

The XML contains `<PubmedArticle>` with `<MedlineCitation>` (title, abstract, MeSH terms, authors) and `<PubmedData>` (article IDs, publication history).

### 4. eLink -- Find related articles

```
GET /elink.fcgi?dbfrom=pubmed&db=pubmed&id={pmid}&cmd=neighbor_score&retmode=json
```

Returns related PMIDs with relevance scores.

## Search Syntax Tips

- **Field tags:** `aspirin[TI]` (title), `Smith J[AU]` (author), `Nature[TA]` (journal), `neoplasms[MH]` (MeSH heading)
- **Boolean:** `CRISPR AND (therapy OR treatment)`
- **Date range:** `2020/01/01:2024/12/31[PDAT]`
- **Publication type:** `review[PT]`, `clinical trial[PT]`
- **Organism:** `humans[MH]`, `mice[MH]`

## Rate Limits

- **3 requests/second** without API key
- **10 requests/second** with API key
- Include `tool` and `email` parameters on every request
- Large batch jobs should run outside peak hours (Mon-Fri 5AM-9PM ET)

## Error Format

```json
{"error": "API rate limit exceeded", "count": "11"}
```

HTTP 400 for bad requests, 429 for rate limiting.
