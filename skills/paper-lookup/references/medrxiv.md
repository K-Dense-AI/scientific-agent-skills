# medRxiv API

medRxiv is a preprint server for health sciences. The API is identical to bioRxiv's API -- same endpoints, same response format -- just use `medrxiv` as the server parameter.

**Important:** Like bioRxiv, there is **no keyword search**. Use Semantic Scholar, OpenAlex, or PubMed for keyword searches of medRxiv content.

## Base URL

```
https://api.biorxiv.org
```

(Same base URL as bioRxiv -- the server is specified in the path.)

## Authentication

None required. Fully public API.

## Key Endpoints

### 1. Content Detail -- Browse by date range

```
GET /details/medrxiv/{interval}/{cursor}/{format}
```

| Parameter | Values | Description |
|-----------|--------|-------------|
| `interval` | `YYYY-MM-DD/YYYY-MM-DD` | Date range (inclusive) |
| | `N` (integer) | N most recent preprints |
| | `Nd` (integer + "d") | Last N days |
| `cursor` | Integer (default `0`) | Pagination offset (100 per page) |
| `format` | `json` (default), `xml` | Response format |

Optional: `?category=cardiovascular%20medicine` (use URL-encoding for spaces)

**Examples:**
```
https://api.biorxiv.org/details/medrxiv/2024-01-01/2024-01-31/0
https://api.biorxiv.org/details/medrxiv/5
https://api.biorxiv.org/details/medrxiv/10d
```

### 2. Content Detail -- DOI lookup

```
GET /details/medrxiv/{doi}/na/{format}
```

**Example:**
```
https://api.biorxiv.org/details/medrxiv/10.1101/2021.04.29.21256344/na/json
```

### 3. Published Article Links

```
GET /pubs/medrxiv/{interval}/{cursor}
GET /pubs/medrxiv/{doi}/na
```

Links preprints to their published journal versions. Accepts both preprint DOI and published DOI.

## Response Format

Same as bioRxiv:

```json
{
  "messages": [{
    "status": "ok",
    "count": 100,
    "total": "502",
    "cursor": 0
  }],
  "collection": [{
    "title": "Paper title...",
    "authors": "Surname, A.; Surname, B.",
    "author_corresponding": "Full Name",
    "author_corresponding_institution": "Institution",
    "doi": "10.1101/2021.04.29.21256344",
    "date": "2021-05-03",
    "version": "1",
    "type": "PUBLISHAHEADOFPRINT",
    "license": "cc_by_nc_nd",
    "category": "cardiovascular medicine",
    "abstract": "Full abstract text...",
    "published": "10.1371/journal.pone.0256482",
    "server": "medRxiv"
  }]
}
```

## Pagination

100 results per page. Use `cursor` parameter to paginate.

## Rate Limits

No documented rate limits. No authentication required.

## Categories

`addiction-medicine`, `allergy-and-immunology`, `anesthesia`, `cardiovascular-medicine`, `dentistry-and-oral-medicine`, `dermatology`, `emergency-medicine`, `endocrinology`, `epidemiology`, `forensic-medicine`, `gastroenterology`, `genetic-and-genomic-medicine`, `geriatric-medicine`, `health-economics`, `health-informatics`, `health-policy`, `health-systems-and-quality-improvement`, `hematology`, `hiv-aids`, `infectious-diseases`, `intensive-care-and-critical-care-medicine`, `medical-education`, `medical-ethics`, `nephrology`, `neurology`, `nursing`, `nutrition`, `obstetrics-and-gynecology`, `occupational-and-environmental-health`, `oncology`, `ophthalmology`, `orthopedics`, `otolaryngology`, `pain-medicine`, `palliative-medicine`, `pathology`, `pediatrics`, `pharmacology-and-therapeutics`, `primary-care-research`, `psychiatry-and-clinical-psychology`, `public-and-global-health`, `radiology-and-imaging`, `rehabilitation-medicine-and-physical-therapy`, `respiratory-medicine`, `rheumatology`, `sexual-and-reproductive-health`, `sports-medicine`, `surgery`, `toxicology`, `transplantation`, `urology`
