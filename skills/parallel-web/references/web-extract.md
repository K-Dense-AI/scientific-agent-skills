# URL Extraction

Extract content from: $ARGUMENTS

## Command

Choose a short, descriptive filename based on the URL or content (e.g., `vespa-docs`, `react-hooks-api`). Use lowercase with hyphens, no spaces.

```bash
parallel-cli extract "$ARGUMENTS" --json -o "$FILENAME.json"
```

Options if needed:
- `--objective "focus area"` to focus on specific content

## Academic content handling

When extracting from academic sources (arXiv, PubMed, journal sites, conference proceedings), use `--objective` to focus on the most valuable sections:

```bash
parallel-cli extract "$URL" --json --objective "extract abstract, methodology, key findings, and conclusions" -o "$FILENAME.json"
```

For arXiv papers, prefer the `/abs/` URL (which has structured metadata) over the raw PDF URL when available. If the user provides a PDF link, extract it directly — parallel-cli handles PDFs.

## Response format

Return content as:

**[Page Title](URL)**

For academic papers, include structured metadata when available:
- **Authors:** list of authors
- **Published:** date and venue/journal
- **DOI:** if available
- **Abstract:** the paper's abstract

Then the extracted content verbatim, with these rules:
- Keep content verbatim - do not paraphrase or summarize
- Parse lists exhaustively - extract EVERY numbered/bulleted item
- Strip only obvious noise: nav menus, footers, ads
- Preserve all facts, names, numbers, dates, quotes
- For academic papers, preserve figure/table captions and references

After the response, mention the output file path (`$FILENAME.json`) so the user knows it's available for follow-up questions.
