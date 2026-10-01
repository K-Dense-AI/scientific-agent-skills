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
| `max_results` | No | 10 | Use slices of at most 2,000; refine searches exceeding 1,000. The manual describes a 30,000-result query limit |
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

**Date range** -- the brackets **must** be percent-encoded as `%5B` / `%5D`:
```
https://export.arxiv.org/api/query?search_query=cat:cs.AI+AND+submittedDate:%5B202401010000+TO+202412312359%5D
```

Passing literal `[` and `]` to `curl` fails before the request is even sent: curl reads them as a
globbing range and exits **3** (`bad range specification`) with no output and no HTTP status to
diagnose. Verified 2026-07-27:

```bash
# exit 3, nothing fetched, no error body to read
curl -s "https://export.arxiv.org/api/query?search_query=submittedDate:[202401010000+TO+202401020000]"

# exit 0, totalResults 35 -- either fix works
curl -s  "https://export.arxiv.org/api/query?search_query=cat:cs.AI+AND+submittedDate:%5B202401010000+TO+202401020000%5D"
curl -sg "https://export.arxiv.org/api/query?search_query=cat:cs.AI+AND+submittedDate:[202401010000+TO+202401020000]"
```

Prefer the encoded form over `curl -g`: it is what the API expects, and it survives being copied
into a fetch tool, a Python client, or a shell that is not curl. Timestamps are `YYYYMMDDHHMM` in
UTC and the range is inclusive on both ends.

## Response Format (Atom XML)

```xml
<feed xmlns="http://www.w3.org/2005/Atom">
  <opensearch:totalResults>1234</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <opensearch:itemsPerPage>10</opensearch:itemsPerPage>

  <entry>
    <id>http://arxiv.org/abs/1706.03762v7</id>   <!-- http, while the links below are https -->
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on...</summary>
    <published>2017-06-12T17:57:34Z</published>
    <updated>2023-08-02T00:00:12Z</updated>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <!-- more authors -->
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <arxiv:primary_category term="cs.CL"/>
    <link rel="alternate" type="text/html" href="https://arxiv.org/abs/1706.03762v7"/>
    <link rel="related" type="application/pdf" title="pdf" href="https://arxiv.org/pdf/1706.03762v7"/>
    <arxiv:comment>15 pages, 5 figures</arxiv:comment>
    <!-- <arxiv:doi> and <arxiv:journal_ref> appear only when the author registered them.
         1706.03762 has neither. -->
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
| `<arxiv:doi>` | The **journal** DOI, and only when the author registered one -- see below |
| `<arxiv:comment>` | Author comments |
| `<arxiv:journal_ref>` | Journal reference, same conditional presence |

### `<arxiv:doi>` is not the arXiv DOI

`<arxiv:doi>` carries the DOI of the *published journal version*
(`10.1103/PhysRevD.50.43`), and it is **absent** for any preprint that was never
published or whose author never registered it. Verified 2026-07-27: `id_list=1706.03762`
("Attention Is All You Need") returns **no** `<arxiv:doi>` element at all.

arXiv also mints its own DOI, conventionally `10.48550/arXiv.{id}`, but **the API never returns it**,
and constructing one is only sometimes a usable key. Verified 2026-07-27 for `1706.03762`:

| Where you send `10.48550/arXiv.1706.03762` | Result |
|---|---|
| `doi.org` | **200** -- it resolves |
| Crossref `/works/10.48550%2FarXiv.1706.03762` | **404** `Resource not found` -- it is a DataCite DOI, not registered with Crossref |
| OpenAlex `/works/doi:10.48550/arXiv.1706.03762` | **404**, and `filter=doi:...` gives `count: 0` |

The OpenAlex miss is not a case problem -- `doi:10.48550/arxiv.2102.05095` and
`doi:10.48550/arXiv.2102.05095` both return 200, so the lookup is case-insensitive and *does* work for
many arXiv preprints. It is that **not every arXiv paper is under a `10.48550` DOI there**:
OpenAlex holds "Attention Is All You Need" as `W2626778328` with DOI `10.65215/2q58a426`, a prefix
arXiv now also uses.

So do not treat a constructed arXiv DOI as an identifier that works everywhere, and do not report a
404 from it as "paper not found". Cross-reference by the **arXiv ID** instead -- Semantic Scholar's
`ARXIV:{id}` prefix (see `references/semantic-scholar.md`) -- or by title search, and fall back to a
constructed DOI only after that fails.

## Parsing Tips

Use `scripts/arxiv_atom.py` rather than re-deriving the parse:

```bash
curl -s "https://export.arxiv.org/api/query?id_list=1706.03762" | python3 scripts/arxiv_atom.py -
```

It emits one JSON record per entry (`arxiv_id`, `version`, `title`, `abstract`, `authors`,
`categories`, `doi`, `pdf_url`, dates) plus the feed's `total_results`, with the namespaces and the
traps below already handled.

If you do parse it yourself: the namespace is `http://www.w3.org/2005/Atom`, with arXiv extensions in
`http://arxiv.org/schemas/atom`. Four things bite:

- **The feed has its own `<link>`.** Before the first `<entry>` there is a `<link
  type="application/atom+xml">` pointing back at the query. Selecting "the first `<link>`" yields the
  query URL, not a paper. Match on `rel`/`type`: the abstract page is `rel="alternate"
  type="text/html"`, the PDF is `rel="related" type="application/pdf" title="pdf"`.
- **The URL schemes are inconsistent within a single response.** Verified 2026-07-27 on
  `id_list=1706.03762`: the entry's `<id>` is `http://arxiv.org/abs/1706.03762v7`, while the
  `<link href>` values for the *same* pages are `https://arxiv.org/abs/...` and
  `https://arxiv.org/pdf/...`, and the feed-level `<id>` is `https://arxiv.org/api/...`. Never
  string-match on the scheme. Take the complete path after `/abs/`; legacy IDs such as `hep-th/9901001v1` contain a slash.
- **The ID carries a version suffix.** `1706.03762v7`, not `1706.03762`. Strip the trailing `vN`
  before comparing against a DOI, a Semantic Scholar `ARXIV:` lookup, or a user-supplied ID.
- **`<title>` and `<summary>` arrive hard-wrapped**, with newlines and runs of spaces mid-sentence.
  Collapse whitespace before display or comparison.

## Failure Modes

None of these are HTTP errors. All verified 2026-07-27.

**An unknown field prefix is silently rewritten to `all:`.** `search_query=badfield:xyz` does not
fail -- arXiv reinterprets it and runs `all:badfield:xyz`, returning plausible hits for a query you
did not ask for. The feed's own `<title>` echoes the query *as executed*:

```xml
<title>arXiv Query: search_query=all:badfield:xyz&amp;id_list=&amp;start=0&amp;max_results=1</title>
```

So a typo in a prefix (`author:` instead of `au:`, `abstract:` instead of `abs:`) degrades a targeted
search into a full-text one with no warning. Use only the prefixes in the table above, and check the
feed `<title>` against the query you sent before trusting the results.

**A malformed parameter returns an error dressed as a result.** `start=notanumber` returns HTTP
**200**, `<opensearch:totalResults>1</opensearch:totalResults>`, and one `<entry>`:

```xml
<entry><title>Error</title><summary>start must be an integer</summary></entry>
```

An agent that reads `totalResults` as 1 and takes `entry[0]` reports a paper titled "Error". Check
for `<title>Error</title>` before treating any entry as a paper. (Omitting both `search_query` and
`id_list` does return HTTP 400, with the same Error entry.)

**Throttling is not XML.** Exceed the rate limit and arXiv replies with the bare plain-text body
`Rate exceeded.` -- 14 bytes, no feed, no Atom envelope. It arrives with HTTP **429**, and under
sustained throttling the connection is dropped outright (curl reports `HTTP=000`). Since `curl -s`
without `-f` prints the body whatever the status, a pipeline that goes straight to a parser sees a
syntax error at line 1 column 0, which reads like a corrupt response rather than a pacing problem.
Check the status and the raw bytes before concluding the API is broken; the fix is to wait, not to
retry harder.

This is easy to trigger -- the limit is one request per **three** seconds -- and **malformed requests
are penalized harder than valid ones**: observed 2026-07-27, valid queries were being served
normally while a repeated `start=notanumber` request stayed throttled for over 30 minutes. Do not
retry a request that arXiv rejected; fix it first.

**A genuine no-match is quiet and correct:** `totalResults` 0 and zero `<entry>` elements. An
unknown arXiv ID in `id_list` behaves the same way -- `id_list=9999.99999` gives `totalResults` 0, no
entry, no error. Report that as "not found in arXiv", not as a failed request.

`scripts/arxiv_atom.py` exits non-zero on the Error entry and reports the echoed query, so a
rewritten prefix surfaces instead of passing silently.

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

- **At least 3 seconds between requests**, per the API usage guidance
- Single connection at a time
- Search results are cached daily -- same query won't show new results within 24 hours
- For bulk data, use the OAI-PMH interface instead

## Official sources reviewed 2026-09-30

- https://info.arxiv.org/help/api/user-manual.html
- https://info.arxiv.org/help/api/tou.html
