# URL Extraction

Extract content from: $ARGUMENTS

## Command

Choose a short, descriptive filename based on the URL or content (e.g., `alphafold-paper`, `nature-editorial`). Use lowercase with hyphens, no spaces.

```bash
uv run --with exa-py python "$SKILL_PATH/scripts/exa_extract.py" "$ARGUMENTS" \
  --text \
  -o "$FILENAME.json"
```

You can pass multiple URLs as positional arguments — the script batches them in a single `/contents` call, which is faster and cheaper than looping.

Content modes:

- `--text` (default if nothing else is passed) returns full-text content
- `--highlights` returns extracted passages instead of full text

## Academic content handling

When extracting from academic sources (arXiv, PubMed, journal sites, conference proceedings), use `--text` to get the full paper text:

```bash
uv run --with exa-py python "$SKILL_PATH/scripts/exa_extract.py" "$URL" \
  --text \
  -o "$FILENAME.json"
```

For arXiv, either the `/abs/` page URL or the raw PDF URL works. Prefer `/abs/` when available — it has cleaner metadata (title, authors, published date) attached to the result.

## Response format

Return content as:

**[Page Title](URL)**

For academic papers, include structured metadata when available:
- **Authors:** list of authors (from the `author` field)
- **Published:** from `published_date`

Then the extracted content, with these rules:
- Keep content verbatim — do not paraphrase or summarize
- Parse lists exhaustively — extract EVERY numbered/bulleted item
- Strip only obvious noise: nav menus, footers, ads
- Preserve all facts, names, numbers, dates, quotes
- For academic papers, preserve figure/table captions and references

**Partial-result handling** — when batching multiple URLs, one or more may fail (paywall, robots.txt, timeout). Report which URLs extracted successfully and which failed, rather than silently dropping failures.

After the response, mention the output file path (`$FILENAME.json`) so the user knows it's available for follow-up questions.
