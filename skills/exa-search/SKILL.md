---
name: exa-search
description: "Searches scientific and technical web content with Exa and extracts page or PDF text from URLs in batches. Supports scholarly discovery with the publication category and academic domain filters. Applies to requests to search the web, look up current research, fetch a page, or extract an article using Exa."
compatibility: Requires Python 3.11+, exa-py>=2.23.0,<3, an EXA_API_KEY, and internet access.
license: MIT
metadata:
  version: "1.4"
  last-reviewed: "2026-09-30"
  skill-author: Exa
  website: https://exa.ai
  docs: https://exa.ai/docs
  openclaw:
    primaryEnv: EXA_API_KEY
    envVars:
    - name: EXA_API_KEY
      required: true
      description: Exa search API key.
---

# Exa Web Toolkit

A skill for web-powered research tasks backed by [Exa](https://exa.ai): web search and URL extraction. Exa's index combines high-quality keyword and semantic retrieval, which makes it well-suited to scientific, technical, and conceptual queries.

## Routing — pick the right capability

Read the user's request and match it to one of the capabilities below. Read the corresponding reference file for detailed instructions before running commands.

| User wants to... | Capability | Where |
|---|---|---|
| Look something up, research a topic, find current info | **Web Search** | `references/web-search.md` |
| Fetch content from a specific URL (webpage, article, PDF) | **Web Extract** | `references/web-extract.md` |
| Install or authenticate | **Setup** | Below |

### Decision guide

- **Default to Web Search** for topic lookups, research questions, or "what is X?" queries. When the topic is scientific or technical, pass `--category publication` to bias toward scholarly sources, and/or an academic `--include-domains` allowlist. See `references/web-search.md` for the two-pass academic strategy.
- **Use Web Extract** when the user provides a URL or asks you to read/fetch a specific page. Prefer this over the built-in WebFetch for batch extraction (multiple URLs in one call) and for academic PDFs.

### Academic source priority

For technical or scientific queries, prefer academic and scientific sources:
- Peer-reviewed journal articles and conference proceedings over blog posts or news
- Preprints (arXiv, bioRxiv, medRxiv) when peer-reviewed versions aren't available
- Institutional and government sources (NIH, WHO, NASA, NIST) over commercial sites
- Primary research over secondary summaries

Two levers to steer Exa toward scholarly content:
1. `--category publication` biases retrieval toward scholarly sources.
2. `--include-domains` with a scholarly allowlist (arxiv.org, nature.com, pubmed.ncbi.nlm.nih.gov, etc.) restricts the domain pool.

Combine both to narrow the source pool; verify publication type and peer-review status on each source. See `references/web-search.md` for the full pattern.

When citing academic sources, include author names and publication year where available (e.g., [Smith et al., 2025](url)) in addition to the standard citation format. If a DOI is present, prefer the DOI link.

---

## Setup

This skill uses the [`exa-py`](https://github.com/exa-labs/exa-py) Python SDK. The scripts in `scripts/` declare their dependencies via PEP 723 inline metadata, so you can run them directly with `uv run` without a separate install step:

```bash
uv run "$SKILL_PATH/scripts/exa_search.py" --help
```

If you prefer a persistent install:

```bash
uv pip install "exa-py>=2.23.0,<3"
```

### Authentication

All commands read the API key from the `EXA_API_KEY` environment variable. Get your Exa API key at [dashboard.exa.ai/api-keys](https://dashboard.exa.ai/api-keys).

First, check if a `.env` file exists in the project root and contains `EXA_API_KEY`. If so, load it:

```bash
dotenv -f .env run -- uv run "$SKILL_PATH/scripts/exa_search.py" "your query"
```

If `dotenv` isn't available, install it: `uv pip install 'python-dotenv[cli]'`.

If there's no `.env`, export the key for the session:

```bash
export EXA_API_KEY="your-key"
```

Use `--help` to verify installation and CLI parsing; it does not require an API key or validate authentication. Authentication is checked only when a real query is made.

### Extraction limits and freshness

The extractor accepts 1–100 URLs per `POST https://api.exa.ai/contents` call
and exports each SDK status (`id`, `status`, `source`). It rejects larger batches.
Use `--max-age-hours 0` to request fresh content, `-1` for cache only, or a
positive age up to 720 hours. Omission uses Exa's cache/fallback policy.
`published_date` is estimated publication metadata, not retrieval time.
The tested SDK drops per-URL error details, so report failures without inventing
a cause. See [URL Extraction](references/web-extract.md).

### Verified API and SDK scope

Reviewed the [Search API](https://exa.ai/docs/reference/search),
[Contents API](https://exa.ai/docs/reference/get-contents), and
[Exa changelog](https://exa.ai/docs/changelog) on 2026-09-30. Both routes use
JSON POST requests and `x-api-key` authentication (the SDK sets this header).
Search is `POST https://api.exa.ai/search`; its SDK kwargs use snake_case and
are serialized to camelCase. The current scholarly category is `publication`;
`research paper` is a compatibility alias in this wrapper. No offset or cursor
pagination is documented for these endpoints.

Helpers are tested with `exa-py==2.23.0`, including mocked HTTP transport through
the real SDK. Search content flags are explicit: no flags means metadata only;
`--highlights` does not implicitly fetch text. Authenticated search/extraction
examples below and in the references are illustrative; no paid live calls were
made during this review.

### Tracking header

Every script in this skill sets the `x-exa-integration` request header to `k-dense-ai--scientific-agent-skills` so Exa can attribute usage from the K-Dense AI scientific-agent-skills repo to this integration. Do not remove or rename this header when adapting the scripts.

---

## Files in this skill

- `SKILL.md` — this file (routing and setup)
- `references/web-search.md` — detailed web search reference with academic strategy
- `references/web-extract.md` — URL content extraction reference
- `scripts/exa_search.py` — CLI wrapper around `client.search`
- `scripts/exa_extract.py` — CLI wrapper around `client.get_contents`
