# GitHub history search

`GET /v2/search/research/github` — searches GitHub issues, pull requests, discussions, and
repository READMEs. It is the bridge from "the paper says it does X" to "here is what happened when
people implemented X".

```bash
uv run --with 'firecrawl-py>=4.41.0' python "$SKILL_PATH/scripts/firecrawl_research.py" \
    search-github "scanpy leiden clustering resolution" --limit 10
```

```json
{
  "success": true,
  "results": [
    {
      "repo": "scverse/scanpy",
      "url": "https://github.com/scverse/scanpy/issues/350",
      "pageType": "issue",
      "number": 350,
      "title": "Clustering with leidenalg · Issue #350 · scverse/scanpy - GitHub",
      "snippet": "introduces an extra collapsed network refinement step ...",
      "license": null
    }
  ]
}
```

Only `repo`, `url`, `title`, `snippet`, and `license` are always present. **`pageType` and `number`
appear only on thread-style hits** (issues, pull requests, discussions) and are absent on README and
repository hits — verified: of five results for `scanpy leiden clustering resolution`, three carried
`pageType`/`number` and two did not. Index into them defensively (`result.get("pageType")`), because
a direct subscript raises on the first README hit. Matched markdown content is included when
available.

Use it for:

- **Why a documented API behaves unexpectedly** — the maintainer's answer is usually in an issue,
  not the docs.
- **Known failure modes and parameter guidance** for a scientific package, straight from the people
  who hit them.
- **Whether a published method has a working reference implementation**, and what the authors
  changed after publication.
- **Design rationale** for a default value the paper does not justify.

Two cautions. Results include third-party repositories that merely mention the term, so check
`repo` before treating a hit as authoritative — an answer in `scverse/scanpy` carries weight that
the same text in an unrelated tutorial repository does not. And issue threads are a snapshot of a
discussion, not a conclusion: a comment describing a bug may predate its fix by years, so check the
state of the referenced repository before reporting the behaviour as current.
