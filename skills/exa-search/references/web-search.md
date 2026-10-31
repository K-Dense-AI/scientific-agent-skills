# Web Search

Search the web for: $ARGUMENTS

## Command

Choose a short, descriptive filename based on the query (e.g., `ai-chip-news`, `crispr-off-target`). Use lowercase with hyphens, no spaces.

```bash
uv run "$SKILL_PATH/scripts/exa_search.py" "$ARGUMENTS" \
  --text --highlights \
  -o "$FILENAME.json"
```

`$SKILL_PATH` is the path to this skill directory. The `-o` flag saves the full results to a JSON file so follow-up questions can reuse them without re-querying.

**Search type selection** — `--type` controls retrieval mode:

| Mode | When to use |
|---|---|
| `auto` (default) | Exa's general-purpose search. Use this unless you have a reason not to. |
| `fast` | Low-latency interactive search. |
| `instant` | Minimum response time, trading some depth for speed. |
| `deep-lite` | Lightweight research with lower latency than deep. |
| `deep` | Multi-step research for complex queries. |
| `deep-reasoning` | Higher-effort reasoning for complex analysis. |

**Content modes** — add any combination:

- `--text` returns full-text content per result
- `--highlights` returns the most relevant passages (good signal-to-noise, lower token cost than full text)

Default to `--highlights` for broad searches (less text to process). Add `--text` only when you need to quote or extract in detail.

**Filtering options** — Exa supports rich filtering via the SDK:

- `--start-published-date 2026-01-01T00:00:00Z` / `--end-published-date 2026-10-01T00:00:00Z` for ISO 8601 publication-date bounds
- `--include-domains domain1.com,domain2.com` to restrict to an allowlist
- `--exclude-domains spam.com,low-quality.com` to drop a blocklist
- `--category publication` to bias toward scholarly content (also: `company`, `news`, `personal site`, `financial report`, `people`; other strings are category hints)
- `--user-location US` for locale-specific results

`--num-results` accepts 1–100 (individual modes may impose lower limits). There
is no documented offset/cursor pagination; reformulate a query or partition by
supported filters when more coverage is needed. Neither method establishes an
exhaustive literature search. `company` and `people` reject publication-date and
exclude-domain filters; the wrapper catches these combinations before calling.
Use `--include-domains github.com` instead of the deprecated `github` category.
Domain filters also support paths and wildcard subdomains. No content flag
means metadata only, despite the SDK's default text retrieval.

## Academic source strategy

For scientific or technical queries, Exa has two strong levers:

### 1. Use `--category publication`

```bash
uv run "$SKILL_PATH/scripts/exa_search.py" "$ARGUMENTS" \
  --category publication \
  --text --highlights \
  -o "$FILENAME-academic.json"
```

This selects the current scholarly-publication category (papers, preprints, and journal articles). Verify peer review, publication metadata, and relevance on the source; the category does not establish evidence quality.

### 2. Restrict to scholarly domains

For stricter academic filtering, combine the category with an explicit domain allowlist:

```bash
uv run "$SKILL_PATH/scripts/exa_search.py" "$ARGUMENTS" \
  --category publication \
  --include-domains "arxiv.org,biorxiv.org,medrxiv.org,pubmed.ncbi.nlm.nih.gov,nature.com,science.org" \
  --text --highlights \
  -o "$FILENAME-academic.json"
```

### Two-pass pattern for comprehensive coverage

Run **both** an academic-focused search and an unrestricted one, then merge with academic sources first:

1. Academic pass: `--category publication` with the scholarly domain allowlist above.
2. General pass: the standard command without `--category` or `--include-domains`, to catch relevant non-academic sources (news coverage, lab blogs, institutional pages).

Merge results, leading with academic sources. If the query is clearly non-scientific, skip the academic pass.

**When to use the two-search pattern:** Any query involving scientific claims, medical information, research findings, technical mechanisms, statistical data, or anything where primary literature would be more reliable than secondary reporting.

## Parsing results

Parse the JSON output. Each result includes:

- `title`, `url`, `published_date`, `author`
- `text` (if `--text`) and `highlights` (if `--highlights`)
- Legacy compatibility fields `score`, `highlight_scores`, and top-level
  `autoprompt_string` may be null/empty; never require them or infer evidence
  quality from a retrieval score. Exa's changelog says `highlightScores` was
  removed in May 2026 although the generated reference still lists it.

Missing author/date/text metadata is normal. The wrapper exports a selected
subset of the SDK response, not raw API JSON or structured publication entities.

**Snippet fallback** — any combination of content fields may be present. Cascade through them: prefer `highlights` (tight, pre-selected passages), fall back to a truncated slice of `text`. Never assume exactly one is present.

## Response format

**CRITICAL: Every claim must have an inline citation.** Use markdown links pulling only from the JSON output. Never invent or guess URLs.

For academic sources, use author-year citation style where metadata is available:
- Academic: [Smith et al., 2025](url) or [Smith & Jones, 2024](url)
- Non-academic: [Source Title](url)

Synthesize a response that:
- Leads with findings from peer-reviewed or preprint sources when available
- Clearly distinguishes between claims backed by primary research vs. secondary reporting
- Includes specific facts, names, numbers, dates
- Cites every fact inline — do not leave any claim uncited
- Organizes by theme if multiple topics
- Notes the evidence quality (e.g., "a randomized controlled trial found..." vs. "a blog post reports...")

**End with a Sources section** listing every URL referenced, grouped by type:

```
Sources:

Academic / Peer-reviewed:
- [Smith et al., 2025 — Title of Paper](https://doi.org/...) (Nature, 2025)
- [Jones & Lee, 2024 — Title of Paper](https://arxiv.org/...) (arXiv preprint)

Other:
- [Source Title](https://example.com/article) (Feb 2026)
```

This Sources section is mandatory. Do not omit it. If no academic sources were found, report the search coverage and filters used; do not infer that the topic has not been studied.

After the Sources section, mention the output file path (`$FILENAME.json`) so the user knows it's available for follow-up questions.

Verified against the [Search API](https://exa.ai/docs/reference/search) and [changelog](https://exa.ai/docs/changelog) on 2026-09-30; authenticated commands are illustrative.
