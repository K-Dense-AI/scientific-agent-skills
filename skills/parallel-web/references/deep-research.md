# Deep Research

Research topic: $ARGUMENTS

## When to use (vs web search)

ONLY use this capability when the user explicitly requests deep/exhaustive research. Deep research takes 5–20 minutes and is significantly more expensive than web search. For normal "research X" requests, quick lookups, or fact-checking, use **web search** instead.

## Command

Choose a descriptive filename based on the topic (e.g., `mrna-vaccine-platforms-2026`, `gut-microbiome-depression`). Use lowercase with hyphens, no spaces.

```bash
python scripts/google_research.py research "$ARGUMENTS" -o "$FILENAME.md" --timeout 1800
```

Important:
- Use `--timeout 1800` (30 minutes) — academic queries regularly take 15+ minutes.
- The command is **synchronous**: it handles polling internally. Do not run a separate poll step unless the command times out (see below).
- The script prints `interaction_id` and progress to stderr. Note the `interaction_id` — you will need it if the command times out.
- For scientific or technical queries, prepend context to steer toward scholarly sources. For example, instead of `"effects of sleep deprivation"`, use `"peer-reviewed research and clinical studies on the effects of sleep deprivation"`.

## If the command times out

If the command exits with a timeout error, it will print the `interaction_id` and a recovery command. Wait a few minutes, then poll:

```bash
python scripts/google_research.py poll "$INTERACTION_ID" -o "$FILENAME.md"
```

Tell the user the research is still running server-side, and re-run `poll` again if it hasn't completed yet.

## What the output looks like

The script writes a comprehensive markdown report to `$FILENAME.md` and prints it to stdout. The report contains:
- Full narrative with inline `[[N]](url)` citations
- A `## Sources` section (often 50–100+ entries for deep queries)

There is no separate `.json` metadata file or executive summary — the markdown is the complete deliverable.

## Response format

**After the command completes:**

1. **Assess source quality** from the `## Sources` section and the narrative text. Since URLs are grounding redirects rather than direct publisher links, assess quality from source titles and in-text mentions (e.g., "Nature", "PubMed", "PMC", "arXiv"). Count roughly how many are peer-reviewed journals/preprints vs. news/blog. Flag to the user if academic coverage is thin and offer a follow-up targeted web search.

2. Tell the user the report file path: `$FILENAME.md`

3. Ask if the user wants to review the full report. **Do NOT read the file into context unless the user asks** — reports are often 5,000–10,000+ words and will flood the context window.

4. Note the `interaction_id` from stderr for potential follow-up queries (visible in stderr output as `[research] interaction_id=...`).
