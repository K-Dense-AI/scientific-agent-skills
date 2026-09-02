# Paper search, metadata, and passage retrieval

Three endpoints over the same paper index. All return JSON with a top-level `success` flag.

| Task | Script command | REST endpoint |
|---|---|---|
| Search abstracts | `search-papers` | `GET /v2/search/research/papers` |
| Canonical metadata | `inspect-paper` | `GET /v2/search/research/papers/{id}` |
| Passages for a question | `read-paper` | `GET /v2/search/research/papers/{id}?query=...` |

`inspect-paper` and `read-paper` are the same endpoint; adding a `query` switches it from metadata
to passage retrieval.

## Paper identifiers

Every paper has a canonical `paperId` (an opaque numeric string) and a `primaryId` — the preferred
source-scoped id, such as `arxiv:1706.03762`, `pmid:34515826`, or `pmcid:PMC13172344`. The `ids`
object carries every known id for the record, typically `doi`, `pmid`, and `pmcid` as lists.

Either `paperId` or a source id works wherever a paper id is accepted. Prefer `primaryId` when
passing results to a human or another skill: it is stable, recognisable, and resolvable by
`paper-lookup`.

## Search papers

```bash
uv run --with 'firecrawl-py>=4.41.0' python "$SKILL_PATH/scripts/firecrawl_research.py" \
    search-papers "single-cell RNA-seq batch correction benchmarks" --limit 20
```

| Flag | Meaning |
|---|---|
| `--limit` | Number of papers to return (maps to the API's `k`). A ceiling, not a guarantee. |
| `--authors` | Comma-separated author substrings. All must match. |
| `--categories` | Comma-separated category filter, e.g. `cs.LG`, `q-bio.GN`. |
| `--from-date` / `--to-date` | Inclusive `YYYY-MM-DD` bounds on created/updated date. |

Response:

```json
{
  "success": true,
  "partial": false,
  "results": [
    {
      "paperId": "3935048904807925401",
      "primaryId": "pmcid:PMC13172344",
      "ids": {"doi": ["10.1038/s41421-026-00889-2"], "pmcid": ["PMC13172344"], "pmid": ["42129132"]},
      "title": "Decoding the role of chromatin context in the off-target effects of CRISPR gene editing with EGOLD.",
      "abstract": "The frequency of off-targets of CRISPR/Cas9 and derivative base editors ...",
      "score": 0.9796676466573412
    }
  ]
}
```

`partial: true` means the index answered from an incomplete pass — treat the result set as a sample
rather than the ranked top-`k`.

The `score` above is one captured response and is **not a calibration point.** The absolute scale
is not stable: the same query has been observed returning a ~0.98 top score and a ~0.03 top score
hours apart, with a different top paper and no change to the query or filters. Use `score` to order
results inside a single response, and decide relevance from the title, abstract, and passages.
Never hardcode a threshold.

### Query the finding, not the keywords

The ranking is semantic, so a query that describes the result you are looking for outperforms a
keyword list. `"does chromatin accessibility predict base editor off-target rates"` retrieves
better than `"chromatin base editor off-target"`.

### Filters are conjunctive and post-hoc

Filters intersect the semantic candidate pool; they do not widen the search. An author who is real
and published still returns zero results if the query text did not surface their work. Observed on
the query `attention transformer neural network`:

| Filter | Results |
|---|---|
| `--authors Vaswani` | 1 (`arxiv:1706.03762`) |
| `--authors "John Jumper"` | 0 |

Neither outcome says anything about the index's coverage of that author. When a filtered search
comes back empty, drop the filter and re-read the unfiltered results before concluding anything.

## Inspect a paper

```bash
... inspect-paper arxiv:1706.03762
```

Returns `{"success": true, "paper": {...}}`, where `paper` carries `title`, `abstract`, `authors`
(a single comma-joined string, not a list), `categories`, `createdDate`, `updateDate`, `ids`, and
`paperId`. For PubMed-sourced records `categories` holds MeSH terms rather than arXiv-style
subject classes.

## Read paper passages

```bash
... read-paper arxiv:1706.03762 --question "What is the attention mechanism?" --limit 4
```

Returns the `paper` block plus `passages`, each with `text` and a `score`. This is the step that
turns "this paper looks relevant" into "this paper states X on the record", so run it before
citing a paper for a specific claim.

**An empty `passages` array is the failure mode to watch.** The call still returns `success: true`:

```json
{"success": true, "paperId": "1567418496726738663", "query": "...", "passages": [], "paper": {...}}
```

This means the index has metadata but no full text for that paper — common for PubMed records
without an open-access body. The script prints a warning to stderr when it happens. Options:

1. Re-run against a different id for the same work (an arXiv or PMC id may be indexed when the
   PubMed one is not).
2. Fall back to `paper-lookup`, which retrieves JATS full text from PMC and Europe PMC.
3. Report the paper as unverified. Do not present its abstract as if it were passage evidence.

Passage `score` values are retrieval scores on their own scale; use them to order passages within
one call, not to judge whether the paper is relevant.
