---
name: paper-lookup
description: Search 10 academic paper databases via REST APIs for research papers, preprints, and scholarly articles. Covers PubMed, PMC (full text), bioRxiv, medRxiv, arXiv, OpenAlex, Crossref, Semantic Scholar, CORE, Unpaywall. Use when searching for papers, citations, DOI/PMID lookups, abstracts, full text, open access, preprints, citation graphs, author search, or any scholarly literature query. Triggers on mentions of any supported database or requests like "find papers on X" or "look up this DOI".
metadata:
  version: "1.0"
  skill-author: K-Dense Inc.
---

# Paper Lookup

You have access to 10 academic paper databases through their REST APIs. Your job is to figure out which database(s) best serve the user's query, call them, and return the results.

## Core Workflow

1. **Understand the query** -- What is the user looking for? A specific paper by DOI? Papers on a topic? An author's publications? Open access PDFs? Full text? This determines which database(s) to hit.

2. **Select database(s)** -- Use the database selection guide below. Many queries benefit from hitting multiple databases -- for example, searching PubMed for papers and then checking Unpaywall for open access copies.

3. **Read the reference file** -- Each database has a reference file in `references/` with endpoint details, query formats, and example calls. Read the relevant file(s) before making API calls.

4. **Make the API call(s)** -- See the **Making API Calls** section below for which HTTP fetch tool to use on your platform.

5. **Return results** -- Always return:
   - The **raw JSON** (or parsed XML for arXiv) response from each database
   - A **list of databases queried** with the specific endpoints used
   - If a query returned no results, say so explicitly rather than omitting it

## Database Selection Guide

Match the user's intent to the right database(s).

### By Use Case

| User is asking about... | Primary database(s) | Also consider |
|---|---|---|
| Papers on a biomedical topic | PubMed | Semantic Scholar, OpenAlex |
| Full text of a biomedical article | PMC | CORE |
| Biology preprints | bioRxiv | Semantic Scholar, OpenAlex |
| Health/medical preprints | medRxiv | Semantic Scholar, OpenAlex |
| Physics, math, or CS preprints | arXiv | Semantic Scholar, OpenAlex |
| Papers across all fields | OpenAlex | Semantic Scholar, Crossref |
| A specific paper by DOI | Crossref | Unpaywall, Semantic Scholar |
| Open access PDF for a paper | Unpaywall | CORE, PMC |
| Citation graph (who cites whom) | Semantic Scholar | OpenAlex |
| Author's publications | Semantic Scholar | OpenAlex |
| Paper recommendations | Semantic Scholar | -- |
| Full text (any field) | CORE | PMC (biomedical only) |
| Journal/publisher metadata | Crossref | OpenAlex |
| Funder information | Crossref | OpenAlex |
| Convert between PMID/PMCID/DOI | PMC (ID Converter) | Crossref |
| Recent preprints by date | bioRxiv, medRxiv | arXiv |

### Cross-Database Queries

| User is asking about... | Databases to query |
|---|---|
| Everything about a paper (metadata + citations + OA) | Crossref + Semantic Scholar + Unpaywall |
| Comprehensive literature search | PubMed + OpenAlex + Semantic Scholar |
| Find and read a paper | PubMed (find) + Unpaywall (OA link) + PMC or CORE (full text) |
| Preprint and its published version | bioRxiv/medRxiv + Crossref |
| Author overview with citation metrics | Semantic Scholar + OpenAlex |

When a query spans multiple needs (e.g., "find papers about CRISPR and get me the PDFs"), query the relevant databases in parallel.

## Common Identifier Formats

Different databases use different identifier systems. If a query fails, the identifier format may be wrong.

| Identifier | Format | Example | Used by |
|---|---|---|---|
| DOI | `10.xxxx/xxxxx` | `10.1038/nature12373` | All databases |
| PMID | Integer | `34567890` | PubMed, PMC, Semantic Scholar |
| PMCID | `PMC` + digits | `PMC7029759` | PMC, Europe PMC |
| arXiv ID | `YYMM.NNNNN` | `2103.15348` | arXiv, Semantic Scholar |
| OpenAlex ID | `W` + digits | `W2741809807` | OpenAlex |
| Semantic Scholar ID | 40-char hex | `649def34f8be...` | Semantic Scholar |
| ORCID | `0000-XXXX-XXXX-XXXX` | `0000-0001-6187-6610` | OpenAlex, Crossref |
| ISSN | `XXXX-XXXX` | `0028-0836` | Crossref, OpenAlex |

**Cross-referencing IDs:** Semantic Scholar accepts DOI, PMID, PMCID, and arXiv ID via prefixes (e.g., `DOI:10.1038/nature12373`, `PMID:34567890`, `ARXIV:2103.15348`). OpenAlex accepts DOI and PMID via prefixes (`doi:10.1038/...`, `pmid:34567890`). Use the PMC ID Converter to translate between PMID, PMCID, and DOI.

## API Keys and Access

Most of these databases are fully open. A few benefit from API keys for higher rate limits.

### Databases requiring or benefiting from API keys

| Database | Env Variable | Required? | Registration |
|---|---|---|---|
| NCBI (PubMed, PMC) | `NCBI_API_KEY` | No (3 req/s without, 10 with) | https://www.ncbi.nlm.nih.gov/account/settings/ |
| CORE | `CORE_API_KEY` | Yes for full text | https://core.ac.uk/services/api |
| Semantic Scholar | `S2_API_KEY` | No (shared pool without) | https://www.semanticscholar.org/product/api#api-key-form |
| OpenAlex | `OPENALEX_API_KEY` | Recommended | https://openalex.org/settings/api |

### Fully open databases (no key needed)

| Database | Notes |
|---|---|
| bioRxiv / medRxiv | No auth, no documented rate limits |
| arXiv | No auth, max 1 request per 3 seconds |
| Crossref | No auth; add `mailto` param for polite pool (2x rate limit) |
| Unpaywall | No auth; requires `email` parameter |

### Loading API keys

1. **Check the environment first** -- the key may already be exported (e.g., `$NCBI_API_KEY`).
2. **Fall back to `.env`** -- check `.env` in the current working directory.
3. **Proceed without** -- most APIs still work at lower rate limits. Tell the user which key is missing and how to get one.

## Making API Calls

Use your environment's HTTP fetch tool to call REST endpoints:

| Platform | HTTP Fetch Tool | Fallback |
|---|---|---|
| Claude Code | `WebFetch` | `curl` via Bash |
| Gemini CLI | `web_fetch` | `curl` via shell |
| Windsurf | `read_url_content` | `curl` via terminal |
| Cursor | No dedicated fetch tool | `curl` via `run_terminal_cmd` |
| Codex CLI | No dedicated fetch tool | `curl` via `shell` |
| Cline | No dedicated fetch tool | `curl` via `execute_command` |

If the fetch tool fails, fall back to `curl` via whatever shell tool is available.

### Special cases

- **arXiv returns Atom XML**, not JSON. Parse it or use `curl` and extract the relevant fields. Consider piping through a simple parser if available.
- **PMC eFetch returns JATS XML** for full text. This is expected -- full text articles are in XML format.
- **Crossref and Unpaywall** benefit from including a `mailto` parameter or email for the polite/fast pool.

### Request guidelines

- For **NCBI APIs** (PubMed, PMC): max 3 req/sec without key, 10 with key. Make requests sequentially.
- For **arXiv**: max 1 request every 3 seconds. Be patient.
- For **Crossref**: 5 req/sec (public), 10 req/sec (polite pool with `mailto`).
- For other APIs with no strict limits, you can query multiple databases in parallel.
- If you get HTTP 429 (rate limit), wait briefly and retry once.

### Error recovery

1. **Check the identifier format** -- use the Common Identifier Formats table. A PMID won't work in arXiv, an arXiv ID won't work in PubMed directly.
2. **Try alternative identifiers** -- if a DOI fails in one database, try the title or PMID instead.
3. **Try a different database** -- if PubMed returns nothing for a CS paper, try Semantic Scholar or OpenAlex.
4. **Report the failure** -- tell the user which database failed, the error, and what you tried instead.

## Output Format

Structure your response like this:

```
## Databases Queried
- **PubMed** -- esearch + esummary for "CRISPR gene therapy"
- **Unpaywall** -- DOI lookup for 10.1038/...

## Results

### PubMed
[raw JSON response or formatted results]

### Unpaywall
[raw JSON response]
```

If results are very large, present the most relevant portion and note that more data is available. But default to showing the full raw JSON -- the user asked for it.

## Available Databases

Read the relevant reference file before making any API call.

### Biomedical Literature
| Database | Reference File | What it covers |
|---|---|---|
| PubMed | `references/pubmed.md` | 37M+ biomedical citations, abstracts, MeSH terms |
| PMC | `references/pmc.md` | 10M+ full-text biomedical articles (JATS XML), ID conversion |

### Preprint Servers
| Database | Reference File | What it covers |
|---|---|---|
| bioRxiv | `references/biorxiv.md` | Biology preprints (browse by date/DOI, no keyword search) |
| medRxiv | `references/medrxiv.md` | Health sciences preprints (browse by date/DOI, no keyword search) |
| arXiv | `references/arxiv.md` | Physics, math, CS, biology, economics preprints (keyword search, Atom XML) |

### Multidisciplinary Indexes
| Database | Reference File | What it covers |
|---|---|---|
| OpenAlex | `references/openalex.md` | 250M+ works, authors, institutions, topics, citation data |
| Crossref | `references/crossref.md` | 150M+ DOI metadata, journals, funders, references |
| Semantic Scholar | `references/semantic-scholar.md` | 200M+ papers, citation graphs, AI-generated TLDRs, recommendations |

### Open Access & Full Text
| Database | Reference File | What it covers |
|---|---|---|
| CORE | `references/core.md` | 37M+ full texts from OA repositories worldwide |
| Unpaywall | `references/unpaywall.md` | OA status and PDF links for any DOI |
