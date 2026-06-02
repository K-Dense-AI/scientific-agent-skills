# arXiv API

arXiv is a preprint server for physics, mathematics, computer science, quantitative biology, quantitative finance, statistics, electrical engineering, and economics.

**Important:** The arXiv API returns **Atom XML**, not JSON. There is no JSON option.

## Base URL

```
https://export.arxiv.org/api/query
```

## Authentication

None required. Fully public.

## Query Parameters

```
GET https://export.arxiv.org/api/query?search_query={query}&start={n}&max_results={n}
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `search_query` | Yes* | -- | Search using field prefixes + boolean operators |
| `id_list` | Yes* | -- | Comma-separated arXiv IDs (e.g., `2103.15348,2005.14165`) |
| `start` | No | 0 | Pagination offset (0-based) |
| `max_results` | No | 10 | Results per request (max 2000; absolute max 30000) |
| `sortBy` | No | `relevance` | `relevance`, `lastUpdatedDate`, `submittedDate` |
| `sortOrder` | No | `descending` | `ascending` or `descending` |

*At least one of `search_query` or `id_list` must be provided. They can be combined (intersection).

## Search Field Prefixes

| Prefix | Searches |
|--------|----------|
| `ti:` | Title |
| `au:` | Author |
| `abs:` | Abstract |
| `co:` | Comment |
| `jr:` | Journal reference |
| `cat:` | Subject category |
| `rn:` | Report number |
| `all:` | All fields |

## Boolean Operators

- `AND` -- both conditions
- `OR` -- either condition
- `ANDNOT` -- exclude
- Parentheses for grouping (URL-encode as `%28` / `%29`)
- Quoted phrases (URL-encode as `%22`)

## Example Queries

**Search all fields:**
```
https://export.arxiv.org/api/query?search_query=all:transformer+attention&max_results=5
```

**Author + category:**
```
https://export.arxiv.org/api/query?search_query=au:hinton+AND+cat:cs.LG&max_results=10
```

**Title search:**
```
https://export.arxiv.org/api/query?search_query=ti:%22attention+is+all+you+need%22
```

**By ID:**
```
https://export.arxiv.org/api/query?id_list=2103.15348
```

**Multiple IDs:**
```
https://export.arxiv.org/api/query?id_list=2103.15348,2005.14165,1706.03762
```

**Date range:**
```
https://export.arxiv.org/api/query?search_query=cat:cs.AI+AND+submittedDate:[202401010000+TO+202412312359]
```

## Response Format (Atom XML)

```xml
<feed xmlns="http://www.w3.org/2005/Atom">
  <opensearch:totalResults>1234</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <opensearch:itemsPerPage>10</opensearch:itemsPerPage>

  <entry>
    <id>http://arxiv.org/abs/1706.03762v7</id>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on...</summary>
    <published>2017-06-12T17:57:34Z</published>
    <updated>2023-08-02T00:00:12Z</updated>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <!-- more authors -->
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <arxiv:primary_category term="cs.CL"/>
    <link rel="alternate" href="http://arxiv.org/abs/1706.03762v7"/>
    <link rel="related" type="application/pdf" href="http://arxiv.org/pdf/1706.03762v7"/>
    <arxiv:doi>10.48550/arXiv.1706.03762</arxiv:doi>
    <arxiv:comment>15 pages, 5 figures</arxiv:comment>
    <arxiv:journal_ref>Advances in Neural Information Processing Systems 30 (NIPS 2017)</arxiv:journal_ref>
  </entry>
</feed>
```

### Key XML elements per entry

| Element | Description |
|---------|-------------|
| `<id>` | arXiv URL: `http://arxiv.org/abs/{id}` |
| `<title>` | Paper title |
| `<summary>` | Abstract |
| `<published>` | Original submission date (ISO 8601) |
| `<updated>` | Date of latest version |
| `<author><name>` | One per author |
| `<category term="...">` | Subject categories |
| `<arxiv:primary_category>` | Primary classification |
| `<link rel="alternate">` | Abstract page URL |
| `<link rel="related" title="pdf">` | PDF URL |
| `<arxiv:doi>` | DOI (when available) |
| `<arxiv:comment>` | Author comments |
| `<arxiv:journal_ref>` | Journal reference |

## Parsing Tips

Since arXiv returns XML, you'll need to parse it. With `curl`, you can pipe the output and extract what you need. The XML namespace is `http://www.w3.org/2005/Atom` with arXiv extensions in `http://arxiv.org/schemas/atom`.

For practical extraction, the key data is in `<entry>` elements. Each entry's `<id>` contains the arXiv ID in the URL path.

## Common Categories

| Category | Field |
|----------|-------|
| `cs.AI` | Artificial Intelligence |
| `cs.CL` | Computation and Language (NLP) |
| `cs.CV` | Computer Vision |
| `cs.LG` | Machine Learning |
| `stat.ML` | Machine Learning (Statistics) |
| `q-bio` | Quantitative Biology |
| `physics` | Physics (all subcategories) |
| `math` | Mathematics (all subcategories) |
| `econ` | Economics |
| `eess` | Electrical Engineering and Systems Science |

Full list: https://arxiv.org/category_taxonomy

## Rate Limits

- **1 request every 3 seconds** (hard limit)
- Single connection at a time
- Search results are cached daily -- same query won't show new results within 24 hours
- For bulk data, use the OAI-PMH interface instead
