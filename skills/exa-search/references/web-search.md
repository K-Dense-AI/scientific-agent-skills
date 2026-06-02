# Web Search

Search the web for: $ARGUMENTS

## Command

Choose a short, descriptive filename based on the query (e.g., `ai-chip-news`, `crispr-off-target`). Use lowercase with hyphens, no spaces.

```bash
uv run --with exa-py python "$SKILL_PATH/scripts/exa_search.py" "$ARGUMENTS" \
  --text --highlights \
  -o "$FILENAME.json"
```

`$SKILL_PATH` is the path to this skill directory. The `-o` flag saves the full results to a JSON file so follow-up questions can reuse them without re-querying.

**Search type selection** — `--type` controls retrieval mode:

| Mode | When to use |
|---|---|
| `auto` (default) | Exa's general-purpose search. Use this unless you have a reason not to. |
| `fast` | Lowest latency. Use for simple lookups where speed matters more than nuance. |
| `deep` | Slowest but highest quality. Use for hard, conceptual, or exhaustive research queries where recall matters more than latency. |

**Content modes** — add any combination:

- `--text` returns full-text content per result
- `--highlights` returns the most relevant passages (good signal-to-noise, lower token cost than full text)

Default to `--highlights` for broad searches (cheaper, more skimmable). Add `--text` only when you need to quote or extract in detail.

**Filtering options** — Exa supports rich filtering via the SDK:

- `--start-published-date YYYY-MM-DD` / `--end-published-date YYYY-MM-DD` for time-sensitive queries
- `--include-domains domain1.com,domain2.com` to restrict to an allowlist
- `--exclude-domains spam.com,low-quality.com` to drop a blocklist
- `--category "research paper"` to bias toward scholarly content (also: `company`, `news`, `github`, `personal site`, `financial report`, `people`)
- `--user-location US` for locale-specific results

## Academic source strategy

For scientific or technical queries, Exa has two strong levers:

### 1. Use `--category "research paper"`

```bash
uv run --with exa-py python "$SKILL_PATH/scripts/exa_search.py" "$ARGUMENTS" \
  --category "research paper" \
  --text --highlights \
  -o "$FILENAME-academic.json"
```

This biases retrieval toward papers indexed as scholarly content (journals, preprint servers, conference proceedings) rather than blogs or news coverage.

### 2. Restrict to scholarly domains

For stricter academic filtering, combine the category with an explicit domain allowlist:

```bash
uv run --with exa-py python "$SKILL_PATH/scripts/exa_search.py" "$ARGUMENTS" \
  --category "research paper" \
  --include-domains "arxiv.org,biorxiv.org,medrxiv.org,pubmed.ncbi.nlm.nih.gov,nature.com,science.org" \
  --text --highlights \
  -o "$FILENAME-academic.json"
```

### Two-pass pattern for comprehensive coverage

Run **both** an academic-focused search and an unrestricted one, then merge with academic sources first:

1. Academic pass: `--category "research paper"` with the scholarly domain allowlist above.
2. General pass: the standard command without `--category` or `--include-domains`, to catch relevant non-academic sources (news coverage, lab blogs, institutional pages).

Merge results, leading with academic sources. If the query is clearly non-scientific, skip the academic pass.

**When to use the two-search pattern:** Any query involving scientific claims, medical information, research findings, technical mechanisms, statistical data, or anything where primary literature would be more reliable than secondary reporting.

## Parsing results

Parse the JSON output. Each result includes:

- `title`, `url`, `published_date`, `author`
- `score` — Exa's relevance score for the query
- `text` (if `--text`), `highlights` + `highlight_scores` (if `--highlights`)

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

This Sources section is mandatory. Do not omit it. If no academic sources were found, note that and explain why (e.g., the topic is too recent, not yet studied, or inherently non-academic).

After the Sources section, mention the output file path (`$FILENAME.json`) so the user knows it's available for follow-up questions.
