# Web Search

Search the web for: $ARGUMENTS

## Command

Choose a short, descriptive filename based on the query (e.g., `ai-chip-news`, `react-vs-vue`). Use lowercase with hyphens, no spaces.

```bash
parallel-cli search "$ARGUMENTS" -q "<keyword1>" -q "<keyword2>" --json --max-results 10 --excerpt-max-chars-total 27000 -o "$FILENAME.json"
```

The first argument is the **objective** — a natural language description of what you're looking for. It replaces multiple keyword searches with a single call for broad or complex queries. Add `-q` flags for specific keyword queries to supplement the objective. The `-o` flag saves the full results to a JSON file for follow-up questions.

Options if needed:
- `--after-date YYYY-MM-DD` for time-sensitive queries
- `--include-domains domain1.com,domain2.com` to limit to specific sources

## Academic source strategy

For scientific or technical queries, run **two searches** to ensure academic sources surface alongside general results:

1. **Academic-focused search** — append `--include-domains` with scholarly domains:
   ```bash
   parallel-cli search "$ARGUMENTS" -q "<keyword1>" --json --max-results 10 --excerpt-max-chars-total 27000 --include-domains "scholar.google.com,arxiv.org,pubmed.ncbi.nlm.nih.gov,semanticscholar.org,biorxiv.org,medrxiv.org,ncbi.nlm.nih.gov,nature.com,science.org,ieee.org,acm.org,springer.com,wiley.com,cell.com,pnas.org,nih.gov" -o "$FILENAME-academic.json"
   ```

2. **General search** — the standard command without domain restrictions, to catch relevant non-academic sources.

Merge results, leading with academic sources. If only one search is practical (e.g., clearly non-scientific query), skip the academic-focused search.

**When to use the two-search pattern:** Any query involving scientific claims, medical information, research findings, technical mechanisms, statistical data, or anything where primary literature would be more reliable than secondary reporting.

## Parsing results

Do not set `max_output_tokens` on the command execution — the output is already bounded by `--max-results` and `--excerpt-max-chars-total`. Capping output tokens will truncate the JSON and break parsing.

Parse the JSON from stdout. For each result, extract:
- title, url, publish_date
- Useful content from excerpts (skip navigation noise like menus, footers, "Skip to content")

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
