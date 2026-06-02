---
name: parallel-web
description: "All-in-one web toolkit powered by parallel-cli, with a strong emphasis on academic and scientific sources. Use this skill whenever the user needs to search the web, fetch/extract URL content, enrich data with web-sourced fields, or run deep research reports. Covers: web search (fast lookups, research, current info — prioritizing peer-reviewed papers, preprints, and scholarly databases), URL extraction (fetching pages, articles, academic PDFs), bulk data enrichment (adding fields to CSV/lists from the web), and deep research (exhaustive multi-source reports grounded in academic literature). Also handles setup, status checks, and result retrieval. Use this skill for ANY web-related task — even if the user doesn't mention 'parallel' or 'web' explicitly. If they want to look something up, fetch a page, enrich a dataset, investigate a topic, find academic papers, check citations, or review scientific literature, this is the skill to use."
compatibility: Requires parallel-cli and internet access.
metadata:
  version: "1.0"
  author: K-Dense, Inc.
---

# Parallel Web Toolkit

A unified skill for all web-powered tasks: searching, extracting, enriching, and researching — with academic and scientific sources as the default priority.

## Routing — pick the right capability

Read the user's request and match it to one of the capabilities below. For web search, extract, enrichment, and deep research, read the corresponding reference file for detailed instructions.

| User wants to... | Capability | Where |
|---|---|---|
| Look something up, research a topic, find current info | **Web Search** | `references/web-search.md` |
| Fetch content from a specific URL (webpage, article, PDF) | **Web Extract** | `references/web-extract.md` |
| Add web-sourced fields to a list of companies/people/products | **Data Enrichment** | `references/data-enrichment.md` |
| Get an exhaustive, multi-source report (user says "deep research", "exhaustive", "comprehensive") | **Deep Research** | `references/deep-research.md` |
| Install or authenticate parallel-cli | **Setup** | Below |
| Check status of a running research/enrichment task | **Status** | Below |
| Retrieve completed research results by run ID | **Result** | Below |

### Decision guide

- **Default to Web Search** for a single lookup, research question, or "what is X?" query. It's fast and cost-effective. When the query touches a scientific or technical topic, include academic domains (see `references/web-search.md`) to surface peer-reviewed and preprint sources alongside general results.
- **Use Web Extract** when the user provides a URL or asks you to read/fetch a specific page. Prefer this over the built-in WebFetch tool. Particularly useful for extracting full text from academic PDFs, preprint servers, and journal articles.
- **Use Data Enrichment** when the user has **multiple entities** (a CSV, a list of companies/people/products, or even a short inline list) and wants to find or add the same kind of information for each one. The key signal is a repeated lookup across a set of items — e.g., "find the CEO for each of these companies" or "get the founding year for Apple, Stripe, and Anthropic." Even if the user doesn't say "enrich," use `parallel-cli enrich` whenever the task is the same query applied to multiple entities. Do NOT use Web Search in a loop for this — the enrichment pipeline handles batching, parallelism, and structured output automatically.
- **Use Deep Research only** when the user explicitly asks for deep, exhaustive, or comprehensive research. It is 10-100x slower and more expensive than Web Search — never default to it. Deep research is especially valuable for literature reviews and multi-paper synthesis.
- If `parallel-cli` is not found when running any command, follow the Setup section below.

### Academic source priority

Across all capabilities, prefer academic and scientific sources when the query is technical or scientific in nature. This means:
- Peer-reviewed journal articles and conference proceedings over blog posts or news articles
- Preprints (arXiv, bioRxiv, medRxiv) when peer-reviewed versions aren't available
- Institutional and government sources (NIH, WHO, NASA, NIST) over commercial sites
- Primary research over secondary summaries

When citing academic sources, include author names and publication year where available (e.g., [Smith et al., 2025](url)) in addition to the standard citation format. If a DOI is present, prefer the DOI link.

## Context chaining

Several capabilities support multi-turn context via `interaction_id`. When a research or enrichment task completes, it returns an `interaction_id`. If the user asks a follow-up question related to that task, pass `--previous-interaction-id` to carry context forward automatically. This avoids restating what was already found.

---

## Setup

If `parallel-cli` is not installed, install and authenticate:

```bash
curl -fsSL https://parallel.ai/install.sh | bash
```

If unable to install that way, use uv instead:

```bash
uv tool install "parallel-web-tools[cli]"
```

Then authenticate. First, check if a `.env` file exists in the project root and contains `PARALLEL_API_KEY`. If so, load it with `dotenv`:

```bash
dotenv -f .env run parallel-cli auth
```

If `dotenv` isn't available, install it with `pip install python-dotenv[cli]` or `uv pip install python-dotenv[cli]`.

If there's no `.env` file or it doesn't contain the key, fall back to interactive login:

```bash
parallel-cli login
```

Or set the key manually: `export PARALLEL_API_KEY="your-key"`

Verify with:

```bash
parallel-cli auth
```

If `parallel-cli` is not found after install, add `~/.local/bin` to PATH.

## Check task status

```bash
parallel-cli research status "$RUN_ID" --json
```

Report the current status to the user (running, completed, failed, etc.).

## Get completed result

```bash
parallel-cli research poll "$RUN_ID" --json
```

Present results in a clear, organized format.
