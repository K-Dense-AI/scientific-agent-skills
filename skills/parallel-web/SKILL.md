---
name: parallel-web
description: "All-in-one web toolkit powered by Google Deep Research (Vertex AI), with a strong emphasis on academic and scientific sources. Use this skill whenever the user needs to search the web, fetch/extract URL content, or run deep research reports. Covers: web search (fast lookups, research, current info — prioritizing peer-reviewed papers, preprints, and scholarly databases), URL extraction (fetching pages, articles, academic PDFs), and deep research (exhaustive multi-source reports grounded in academic literature). Also handles status checks and result retrieval by interaction ID. Use this skill for ANY web-related task — even if the user doesn't mention 'search' or 'web' explicitly. If they want to look something up, fetch a page, investigate a topic, find academic papers, check citations, or review scientific literature, this is the skill to use."
compatibility: Requires google-genai (pip) and Vertex AI access.
required_environment_variables: [{"name": "GOOGLE_CLOUD_PROJECT", "prompt": "GCP project ID for Vertex AI.", "required_for": "full functionality"}, {"name": "GOOGLE_APPLICATION_CREDENTIALS", "prompt": "Path to Vertex service-account JSON (or use ADC).", "required_for": "full functionality"}]
metadata: {"version": "2.0", "author": "K-Dense, Inc.", "openclaw": {"primaryEnv": "GOOGLE_CLOUD_PROJECT", "envVars": [{"name": "GOOGLE_CLOUD_PROJECT", "required": true, "description": "GCP project ID."}, {"name": "GOOGLE_APPLICATION_CREDENTIALS", "required": false, "description": "Service-account JSON path. Not needed if using ADC."}]}}
---

# Google Deep Research Web Toolkit

A unified skill for all web-powered tasks: searching, extracting, and researching — with academic and scientific sources as the default priority. Powered by Google Deep Research via Vertex AI.

## Routing — pick the right capability

Read the user's request and match it to one of the capabilities below. For web search, extract, and deep research, read the corresponding reference file for detailed instructions.

| User wants to... | Capability | Where |
|---|---|---|
| Look something up, research a topic, find current info | **Web Search** | `references/web-search.md` |
| Fetch content from a specific URL (webpage, article, PDF) | **Web Extract** | `references/web-extract.md` |
| Get an exhaustive, multi-source report (user says "deep research", "exhaustive", "comprehensive") | **Deep Research** | `references/deep-research.md` |
| Retrieve a research report by interaction ID (poll after timeout) | **Poll** | Below |
| Install dependencies or verify auth | **Setup** | Below |

### Decision guide

- **Default to Web Search** for a single lookup, research question, or "what is X?" query. It's fast and cost-effective.
- **Use Web Extract** when the user provides a URL or asks you to read/fetch a specific page. Particularly useful for academic PDFs, preprint servers, and journal articles.
- **Use Deep Research only** when the user explicitly asks for deep, exhaustive, or comprehensive research. It takes **15–30 minutes** — never default to it.
- Data enrichment (batch CSV/entity lookups) is **not available** in this skill version — there is no `enrich` command in `google_research.py`. Tell the user batch enrichment is unsupported for now. For small lists (roughly &lt;10 rows), use **web search** per entity; for large tables, ask the user to narrow the scope or split the task.

### Academic source priority

Across all capabilities, prefer academic and scientific sources when the query is technical or scientific in nature:
- Peer-reviewed journal articles and conference proceedings over blog posts or news articles
- Preprints (arXiv, bioRxiv, medRxiv) when peer-reviewed versions aren't available
- Institutional and government sources (NIH, WHO, NASA, NIST) over commercial sites
- Primary research over secondary summaries

When citing academic sources, include author names and publication year where available in addition to the standard citation format.

### Google source mix (important)

Unlike research-curated pipelines, **Google Deep Research may return mixed sources** — peer-reviewed journals alongside supplement retailers, health blogs, news sites, and product pages. This is expected API behavior, not a script error.

When presenting Google output to the user:

1. **Always include a Source Quality assessment** (see capability-specific reference files for templates).
2. **Do not treat all sources as equal evidence** — distinguish peer-reviewed / preprint / clinical-registry sources from commercial or blog sources.
3. **Flag thin academic coverage** — if roughly less than half of cited sources are academic or institutional, tell the user and note which claims rely mainly on non-academic sources.
4. **Prefer evidence from academic sources** when summarizing clinical or mechanistic claims.

URLs in Google output are often **grounding redirect wrappers** (`vertexaisearch.cloud.google.com/grounding-api-redirect/...`). Assess source type from the **citation title and domain name** shown in the `## Sources` list, not from the redirect URL string itself.

## Setup

If `google-genai` is not installed, install it:

```bash
uv pip install google-genai
# or: pip install google-genai
```

Verify auth. The script needs `GOOGLE_CLOUD_PROJECT` and either `GOOGLE_APPLICATION_CREDENTIALS` (service-account JSON path) or Application Default Credentials (ADC via `gcloud auth application-default login`).

Check if a `.env` file exists in the project root containing `GOOGLE_CLOUD_PROJECT` and `GOOGLE_APPLICATION_CREDENTIALS`. If so, load it before running:

```bash
dotenv -f .env run python scripts/google_research.py search "test" --fast
```

If `dotenv` isn't available: `pip install python-dotenv[cli]` or `uv pip install python-dotenv[cli]`.

If env vars are already in the environment, run directly:

```bash
python scripts/google_research.py search "test" --fast
```

---

## Poll a research result by interaction ID

Deep research uses a **two-step flow** (see `references/deep-research.md`):

1. `research "$QUERY" --no-wait` — starts the job and prints `interaction_id` to stderr (seconds).
2. `poll "$INTERACTION_ID" -o "$FILENAME.md" --timeout 1800` — waits for the report.

If poll times out, research is **still running server-side**. Wait 2–3 minutes and re-run the same `poll` command. Total time may reach 30–60 minutes.

```bash
python scripts/google_research.py poll "$INTERACTION_ID" -o "$FILENAME.md" --timeout 1800
```

Report the file path and offer to read the file if the user wants to review the results.
