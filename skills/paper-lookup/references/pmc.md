# PMC (PubMed Central)

PMC is a **full-text archive** of biomedical and life sciences articles. It is separate from PubMed -- PubMed has citations/abstracts, PMC has full text. Not all PubMed articles are in PMC, and vice versa.

## E-utilities for PMC

### Base URL

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
```

Same E-utilities as PubMed, but with `db=pmc`.

### eSearch -- Search PMC

```
GET /esearch.fcgi?db=pmc&term={query}&retmode=json
```

Same parameters as PubMed eSearch. Returns PMC UIDs (numeric, e.g., `13033346`). You need to prepend "PMC" to get a PMCID (e.g., `PMC13033346`).

### eFetch -- Get Full Text XML

```
GET /efetch.fcgi?db=pmc&id={pmcid}&retmode=xml
```

| rettype | retmode | Returns |
|---------|---------|---------|
| *(omit)* | `xml` | **Full text JATS XML** (body, figures, references) |
| `medline` | `text` | MEDLINE format |

**Example:**
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=7029759&retmode=xml
```

The XML uses JATS (Journal Article Tag Suite) format:
- `<front>` -- journal metadata, article metadata, author info
- `<body>` -- full article text with `<sec>` sections, `<p>` paragraphs, `<fig>` figures
- `<back>` -- `<ref-list>` with all references

Pass numeric IDs only (not "PMC7029759", just "7029759").

## BioC API -- Structured Full Text

An alternative way to get full text in a structured passage format.

### Base URL

```
https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/
```

### Endpoint

```
GET /BioC_{format}/{id}/{encoding}
```

| Parameter | Values |
|-----------|--------|
| `format` | `json` or `xml` |
| `id` | PMID (e.g., `17299597`) or PMCID (e.g., `PMC7029759`) |
| `encoding` | `unicode` or `ascii` |

**Example:**
```
https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/PMC7029759/unicode
```

**Response structure (JSON):**
```json
{
  "source": "PMC",
  "documents": [{
    "id": "PMC7029759",
    "infons": {"license": "...", "doi": "..."},
    "passages": [
      {
        "offset": 0,
        "infons": {"section_type": "TITLE"},
        "text": "Article title..."
      },
      {
        "offset": 42,
        "infons": {"section_type": "ABSTRACT"},
        "text": "Abstract text..."
      },
      {
        "offset": 500,
        "infons": {"section_type": "INTRO"},
        "text": "Introduction text..."
      }
    ]
  }]
}
```

Section types: `TITLE`, `ABSTRACT`, `INTRO`, `METHODS`, `RESULTS`, `DISCUSS`, `CONCL`, `REF`, `SUPPL`, `FIG`, `TABLE`

**Coverage:** ~3 million articles from the PMC Open Access Subset.

## PMC ID Converter API

Converts between PMID, PMCID, DOI, and Manuscript ID.

### Base URL

```
https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/
```

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `ids` | Yes | Up to 200 comma-separated IDs |
| `idtype` | No | `pmcid`, `pmid`, `mid`, `doi` (default: auto-detect) |
| `format` | No | `json`, `xml`, `csv` (default: xml) |
| `tool` | Recommended | Your application name |
| `email` | Recommended | Your contact email |

**Example:**
```
https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/?ids=PMC7029759&format=json
```

**Response:**
```json
{
  "status": "ok",
  "records": [{
    "pmcid": "PMC7029759",
    "pmid": "32117569",
    "doi": "10.12688/f1000research.22211.2"
  }]
}
```

Only returns results for articles that are in PMC. If an article is in PubMed but not PMC, no PMCID will be returned.

## Rate Limits

| Service | Limit |
|---------|-------|
| E-utilities (`db=pmc`) | 3/sec without key, 10/sec with key |
| BioC API | Follow general NCBI policy (3/sec without key) |
| ID Converter | Follow general NCBI policy |

Include `tool` and `email` parameters on E-utility requests. Large batch jobs should run outside peak hours (Mon-Fri 5AM-9PM ET).
