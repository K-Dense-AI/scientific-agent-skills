# Web Search

Search the web for: $ARGUMENTS

## Command

Choose a short, descriptive filename based on the query (e.g., `ai-chip-news`, `react-vs-vue`). Use lowercase with hyphens, no spaces.

```bash
python scripts/google_research.py search "$ARGUMENTS" --fast -o "$FILENAME.md"
```

`--fast` uses `gemini-2.5-flash + google_search` for a ~10s synthesized response. This is the default and recommended mode for all search queries.

Options if needed:
- `--timeout N` to extend the timeout (default 600s; rarely needed with `--fast`)

## What the output looks like

The script writes a pre-synthesized markdown report directly to `$FILENAME.md` and prints the same content to stdout. The output already contains:
- Inline citations in `[[N]](url)` format
- A `## Sources` section listing all referenced URLs with titles

**Do not re-parse or re-synthesize the output.** Present it as-is — the synthesis and citation linking are already done.

## Academic source strategy

For scientific or technical queries, append academic context to the query string to improve source targeting:

```bash
python scripts/google_research.py search "peer-reviewed research on $ARGUMENTS" --fast -o "$FILENAME.md"
```

You do not need to run two separate searches. Google's search synthesis already blends academic and general sources; biasing the query string is sufficient.

## Response format

1. Present the synthesized markdown output to the user directly. Keep all inline citations intact.

2. **Assess source quality from the `## Sources` section and narrative text** — since URLs are grounding redirects rather than direct publisher links, check whether the source titles and in-text references mention peer-reviewed journals, preprints, or institutional bodies (e.g., "Nature", "PubMed", "arXiv", "NIH", "WHO"). Note the evidence quality to the user:
   - If academic/institutional sources are clearly present: note this briefly
   - If coverage appears primarily non-academic: flag it and offer to run a query that explicitly targets scholarly sources

3. End by mentioning the output file path (`$FILENAME.md`) so the user knows it's available for follow-up questions.

**Sources section is already included** in the script output. Do not generate a second one. If you want to highlight specific sources by type (academic vs. general), quote from the existing `## Sources` list rather than inventing new entries.
