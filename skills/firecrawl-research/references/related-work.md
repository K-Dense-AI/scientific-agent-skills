# Related-work expansion

`GET /v2/search/research/papers/{id}/similar` — expand from a seed paper through the citation graph
and semantic neighbourhood, then rank the candidates against a natural-language `intent`.

```bash
uv run --with 'firecrawl-py>=4.41.0' python "$SKILL_PATH/scripts/firecrawl_research.py" \
    related-papers arxiv:1706.03762 --intent "efficient transformer architectures" \
    --mode citers --limit 20
```

`--intent` is required and is what makes this different from a plain "similar papers" button: the
neighbourhood is gathered structurally, then re-ranked against your stated purpose. Write it as the
thing you are trying to find, e.g. `"methods that reduce attention's quadratic cost"`.

## Modes

| `--mode` | Expansion | Use it for |
|---|---|---|
| `similar` (default) | Co-citation and bibliographic-coupling neighbourhood | "What else is in this space?" — sibling work that may not cite the seed at all |
| `citers` | Papers that cite the seed | Follow-on work, replications, critiques, later benchmarks |
| `references` | Papers the seed cites | Foundations, prior methods, the datasets and benchmarks it builds on |

`similar` finds work that shares a citation context without any direct edge to the seed, which is
what surfaces parallel efforts under different terminology. Use `citers` when the question is
temporal ("what happened after this") and `references` when it is genealogical ("what is this built
on").

## Response

```json
{
  "success": true,
  "poolSize": 512,
  "truncated": false,
  "results": [
    {
      "paperId": "7903396323338227254",
      "primaryId": "pmcid:PMC13069301",
      "ids": {"doi": ["10.1016/j.ymthe.2025.12.043"], "pmcid": ["PMC13069301"], "pmid": ["41445188"]},
      "title": "Off-target RNA editing hotspots caused by base editors.",
      "abstract": "Base editors, composed of engineered deaminases fused with Cas proteins ...",
      "score": 0.03279569892473118,
      "signals": {"structural": 0.949}
    }
  ]
}
```

- `poolSize` — how many candidates the structural expansion gathered before ranking.
- `truncated` — whether that pool was capped. When `true`, the ranking saw only part of the
  neighbourhood, so a `--limit` near the pool size is not an exhaustive list of related work.
- `signals` — per-candidate ranking components, `structural` being the citation-graph contribution.

**Scores here are not comparable to `search-papers` scores**, which come from a different ranking
function. The absolute scale is not stable over time either — the same `search-papers` query has
been observed returning a ~0.98 top score and a ~0.03 top score hours apart, unchanged. Order
results within one response by score if you like, but never carry a threshold from one endpoint to
the other, and never hardcode a cutoff: judge relevance from the title, abstract, and `signals`
rather than the number. The `score` in the example above is one captured response, not a
calibration point.

## Strategy

Expansion is only as good as its seed, so establish a seed you have verified before expanding:

1. `search-papers` for candidates, then `read-paper` to confirm one genuinely does what you need.
2. `related-papers --mode references` on that seed to recover the foundations, which gives you the
   vocabulary the field actually uses.
3. Re-run `search-papers` with that vocabulary — this usually retrieves more than expanding further.
4. `related-papers --mode citers` for the current state of the art.

For a survey, expand from two or three seeds chosen to be *different* rather than the top two hits
of one query, and intersect the results: papers that appear in several neighbourhoods are the ones
the field treats as central.

Deduplicate in two passes, because the two problems are different:

1. **The same index record returned by more than one expansion** — collapse on `paperId`, which is
   exact and cheap.
2. **The same work held as more than one record** — a preprint and its published version are
   separate entries with *different* `paperId`s, so step 1 cannot merge them. Compare the `ids`
   object instead and treat entries as the same work when they share a `doi`, `pmid`, or `pmcid`.
   Records that share no identifier need bibliographic matching (normalised title plus first
   author, or title plus year) as a last resort, which is fuzzy — prefer keeping both and saying so
   over silently merging two papers that differ.

Do not deduplicate on title alone: the same work is indexed with punctuation, casing, and trailing
differences between sources, and distinct papers in a series often share a title prefix.

Do not chain expansions more than a step or two without re-verifying. Each hop drifts from the
original intent, and a third-hop result frequently has no substantive relationship to the seed.
