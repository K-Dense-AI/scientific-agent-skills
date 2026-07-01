# URL Extraction

Extract content from: $ARGUMENTS

## Command

Choose a short, descriptive filename based on the URL or content (e.g., `vespa-docs`, `attention-is-all-you-need`). Use lowercase with hyphens, no spaces.

```bash
python scripts/google_research.py extract "$ARGUMENTS" -o "$FILENAME.md"
```

Options if needed:
- `--objective "focus area"` to focus on specific content (highly recommended for academic papers)

## Academic content handling

When extracting from academic sources (arXiv, PubMed, journal sites, conference proceedings), use `--objective` to target the most valuable sections:

```bash
python scripts/google_research.py extract "$URL" \
  --objective "extract title, authors, publication date, abstract, methodology, key findings, and conclusions" \
  -o "$FILENAME.md"
```

For arXiv papers, prefer the `/abs/` URL (which has structured metadata) over the raw PDF URL when available. The script handles both.

## What the output looks like

The script returns a structured markdown document with:
- Title, authors, publication date (for academic papers)
- Abstract and key findings as prose sections
- A `## Sources` section with the source URL

The output is richer than raw page scraping — it is a structured synthesis of the page content.

## Response format

Present the extracted content to the user. For academic papers, confirm key metadata (title, authors, venue, date) are present before presenting the full extraction.

Keep the content faithful to the source:
- Do not paraphrase or re-summarize the extracted text
- Preserve all facts, names, numbers, dates, quotes
- For academic papers, preserve figure/table captions and key numerical results

After presenting the content, mention the output file path (`$FILENAME.md`) so the user knows it's saved for follow-up questions.
