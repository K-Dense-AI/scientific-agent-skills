---
name: research-lookup
description: Look up current research information using parallel-cli search (primary, fast web search), the Parallel Chat API (deep research), or Perplexity sonar-pro-search (academic paper searches). Automatically routes queries to the best backend. Use for finding papers, gathering research data, and verifying scientific information. Note: query text is transmitted to api.parallel.ai (PARALLEL_API_KEY) and, for academic searches, to openrouter.ai (OPENROUTER_API_KEY).
allowed-tools: Read Write Edit Bash
license: MIT license
compatibility: parallel-cli required (primary); PARALLEL_API_KEY and OPENROUTER_API_KEY optional for deep/academic backends
metadata:
    skill-author: K-Dense Inc.
---

# Research Information Lookup

## Overview

This skill provides real-time research information lookup with **intelligent backend routing**:

- **parallel-cli search** (parallel-web skill): **Primary and default backend** for all research queries. Fast, cost-effective web search with academic source prioritization. Uses `parallel-cli search` with `--include-domains` for scholarly sources.
- **Parallel Chat API** (`core` model): Secondary backend for complex, multi-source deep research requiring extended synthesis (60s-5min latency). Use only when explicitly needed.
- **Perplexity sonar-pro-search** (via OpenRouter): Used only for academic-specific paper searches where scholarly database access is critical.

The skill automatically detects query type and routes to the optimal backend.

## When to Use This Skill

Use this skill when you need:

- **Current Research Information**: Latest studies, papers, and findings
- **Literature Verification**: Check facts, statistics, or claims against current research
- **Background Research**: Gather context and supporting evidence for scientific writing
- **Citation Sources**: Find relevant papers and studies to cite
- **Technical Documentation**: Look up specifications, protocols, or methodologies
- **Market/Industry Data**: Current statistics, trends, competitive intelligence
- **Recent Developments**: Emerging trends, breakthroughs, announcements

## Visual Enhancement with Scientific Schematics

**When creating documents with this skill, always consider adding scientific diagrams and schematics to enhance visual communication.**

If your document does not already contain schematics or diagrams:
- Use the **scientific-schematics** skill to generate AI-powered publication-quality diagrams
- Simply describe your desired diagram in natural language

```bash
python scripts/generate_schematic.py "your diagram description" -o figures/output.png
```

---

## Automatic Backend Selection

The skill automatically routes queries to the best backend based on content:

### Routing Logic

```
Query arrives
    |
    +-- Contains academic keywords? (papers, DOI, journal, peer-reviewed, etc.)
    |       YES --> Perplexity sonar-pro-search (academic search mode)
    |
    +-- Needs deep multi-source synthesis? (user says "deep research", "exhaustive")
    |       YES --> Parallel Chat API (core model, 60s-5min)
    |
    +-- Everything else (general research, market data, technical info, analysis)
            --> parallel-cli search (fast, default)
```

### Default: parallel-cli search (parallel-web skill)

**Primary backend for all standard research queries.** Fast, cost-effective, and supports academic source prioritization.

For scientific/technical queries, run two searches to ensure academic coverage:

```bash
# 1. Academic-focused search
parallel-cli search "your research query" -q "keyword1" -q "keyword2" \
  --json --max-results 10 --excerpt-max-chars-total 27000 \
  --include-domains "scholar.google.com,arxiv.org,pubmed.ncbi.nlm.nih.gov,semanticscholar.org,biorxiv.org,medrxiv.org,ncbi.nlm.nih.gov,nature.com,science.org,ieee.org,acm.org,springer.com,wiley.com,cell.com,pnas.org,nih.gov" \
  -o sources/research_<topic>-academic.json

# 2. General search (catches non-academic sources)
parallel-cli search "your research query" -q "keyword1" -q "keyword2" \
  --json --max-results 10 --excerpt-max-chars-total 27000 \
  -o sources/research_<topic>-general.json
```

Options:
- `--after-date YYYY-MM-DD` for time-sensitive queries
- `--include-domains domain1.com,domain2.com` to limit to specific sources

Merge results, leading with academic sources. For non-scientific queries, a single general search is sufficient.

All other queries route here by default, including:

- General research questions
- Market and industry analysis
- Technical information and documentation
- Current events and recent developments
- Comparative analysis
- Statistical data retrieval
- Fact-checking and verification

### Academic Keywords (Routes to Perplexity)

Queries containing these terms are routed to Perplexity for academic-focused search:

- Paper finding: `find papers`, `find articles`, `research papers on`, `published studies`
- Citations: `cite`, `citation`, `doi`, `pubmed`, `pmid`
- Academic sources: `peer-reviewed`, `journal article`, `scholarly`, `arxiv`, `preprint`
- Review types: `systematic review`, `meta-analysis`, `literature search`
- Paper quality: `foundational papers`, `seminal papers`, `landmark papers`, `highly cited`

### Deep Research (Routes to Parallel Chat API)

Only used when the user explicitly requests deep, exhaustive, or comprehensive research. Much slower and more expensive than parallel-cli search.

### Manual Override

You can force a specific backend:

```bash
# Force parallel-cli search (fast web search)
parallel-cli search "your query" -q "keyword" --json --max-results 10 -o sources/research_<topic>.json

# Force Parallel Deep Research (slow, exhaustive)
python research_lookup.py "your query" --force-backend parallel

# Force Perplexity academic search
python research_lookup.py "your query" --force-backend perplexity
```

---

## Core Capabilities

### 1. General Research Queries (parallel-cli search — DEFAULT)

**Primary backend.** Fast, cost-effective web search with academic source prioritization via the parallel-web skill.

```
Query Examples:
- "Recent advances in CRISPR gene editing 2025"
- "Compare mRNA vaccines vs traditional vaccines for cancer treatment"
- "AI adoption in healthcare industry statistics"
- "Global renewable energy market trends and projections"
- "Explain the mechanism underlying gut microbiome and depression"
```

```bash
# Example: research on CRISPR advances
parallel-cli search "Recent advances in CRISPR gene editing 2025" \
  -q "CRISPR" -q "gene editing" -q "2025" \
  --json --max-results 10 --excerpt-max-chars-total 27000 \
  --include-domains "scholar.google.com,arxiv.org,pubmed.ncbi.nlm.nih.gov,nature.com,science.org,cell.com,pnas.org,nih.gov" \
  -o sources/research_crispr_advances-academic.json

parallel-cli search "Recent advances in CRISPR gene editing 2025" \
  -q "CRISPR" -q "gene editing" \
  --json --max-results 10 --excerpt-max-chars-total 27000 \
  -o sources/research_crispr_advances-general.json
```

**Response includes:**
- Synthesized findings with inline citations from search results
- Academic sources prioritized (peer-reviewed, preprints)
- Specific facts, numbers, and dates
- Sources section listing all referenced URLs grouped by type

### 2. Academic Paper Search (Perplexity sonar-pro-search)

**Used for academic-specific queries.** Prioritizes scholarly databases and peer-reviewed sources. Use when queries specifically ask for papers, citations, or DOIs.

```
Query Examples:
- "Find papers on transformer attention mechanisms in NeurIPS 2024"
- "Foundational papers on quantum error correction"
- "Systematic review of immunotherapy in non-small cell lung cancer"
- "Cite the original BERT paper and its most influential follow-ups"
- "Published studies on CRISPR off-target effects in clinical trials"
```

**Response includes:**
- Summary of key findings from academic literature
- 5-8 high-quality citations with authors, titles, journals, years, DOIs
- Citation counts and venue tier indicators
- Key statistics and methodology highlights
- Research gaps and future directions

### 3. Deep Research (Parallel Chat API — on request only)

**Used only when user explicitly requests deep/exhaustive research.** Provides comprehensive, multi-source synthesis via the Chat API (`core` model). 60s-5min latency.

```
Query Examples:
- "Deep research on the current state of quantum computing error correction"
- "Exhaustive analysis of mRNA vaccine platforms for cancer immunotherapy"
```

### 4. Technical and Methodological Information

Use parallel-cli search (default) for quick lookups:

```bash
parallel-cli search "Western blot protocol for protein detection" \
  -q "western blot" -q "protocol" \
  --json --max-results 10 --excerpt-max-chars-total 27000 \
  -o sources/research_western_blot.json
```

### 5. Statistical and Market Data

Use parallel-cli search (default) for current data:

```bash
parallel-cli search "Global AI market size and growth projections 2025" \
  -q "AI market" -q "statistics" -q "growth" \
  --json --max-results 10 --excerpt-max-chars-total 27000 \
  --after-date 2024-01-01 \
  -o sources/research_ai_market.json
```

---

## Paper Quality and Popularity Prioritization

**CRITICAL**: When searching for papers, ALWAYS prioritize high-quality, influential papers.

### Citation-Based Ranking

| Paper Age | Citation Threshold | Classification |
|-----------|-------------------|----------------|
| 0-3 years | 20+ citations | Noteworthy |
| 0-3 years | 100+ citations | Highly Influential |
| 3-7 years | 100+ citations | Significant |
| 3-7 years | 500+ citations | Landmark Paper |
| 7+ years | 500+ citations | Seminal Work |
| 7+ years | 1000+ citations | Foundational |

### Venue Quality Tiers

**Tier 1 - Premier Venues** (Always prefer):
- **General Science**: Nature, Science, Cell, PNAS
- **Medicine**: NEJM, Lancet, JAMA, BMJ
- **Field-Specific**: Nature Medicine, Nature Biotechnology, Nature Methods
- **Top CS/AI**: NeurIPS, ICML, ICLR, ACL, CVPR

**Tier 2 - High-Impact Specialized** (Strong preference):
- Journals with Impact Factor > 10
- Top conferences in subfields (EMNLP, NAACL, ECCV, MICCAI)

**Tier 3 - Respected Specialized** (Include when relevant):
- Journals with Impact Factor 5-10

---

## Technical Integration

### Prerequisites

```bash
# Primary backend (parallel-cli) - REQUIRED
# Install parallel-cli if not already available:
curl -fsSL https://parallel.ai/install.sh | bash
# Or: uv tool install "parallel-web-tools[cli]"

# Authenticate:
parallel-cli auth
# Or: export PARALLEL_API_KEY="your_parallel_api_key"
```

### Environment Variables

```bash
# Primary backend (parallel-cli search) - REQUIRED
export PARALLEL_API_KEY="your_parallel_api_key"

# Deep research backend (Parallel Chat API) - optional, for deep research only
# Uses the same PARALLEL_API_KEY

# Academic search backend (Perplexity) - optional, for academic paper queries
export OPENROUTER_API_KEY="your_openrouter_api_key"
```

### API Specifications

**parallel-cli search (PRIMARY):**
- Command: `parallel-cli search` with `--json` output
- Latency: 2-10 seconds (fast)
- Output: JSON with title, URL, publish_date, excerpts
- Academic domains: Use `--include-domains` for scholarly sources
- Saves results: `-o filename.json` for follow-up and reproducibility

**Parallel Chat API (deep research only):**
- Endpoint: `https://api.parallel.ai` (OpenAI SDK compatible)
- Model: `core` (60s-5min latency, complex multi-source synthesis)
- Output: Markdown text with inline citations
- Citations: Research basis with URLs, reasoning, and confidence levels
- Rate limits: 300 req/min
- Python package: `openai`

**Perplexity sonar-pro-search (academic only):**
- Model: `perplexity/sonar-pro-search` (via OpenRouter)
- Search mode: Academic (prioritizes peer-reviewed sources)
- Search context: High (comprehensive research)
- Response time: 5-15 seconds

### Command-Line Usage

```bash
# Fast web search via parallel-cli (DEFAULT — recommended) — ALWAYS save to sources/
parallel-cli search "your query" -q "keyword1" -q "keyword2" \
  --json --max-results 10 --excerpt-max-chars-total 27000 \
  -o sources/research_<topic>.json

# Academic-focused search via parallel-cli — ALWAYS save to sources/
parallel-cli search "your query" -q "keyword1" \
  --json --max-results 10 --excerpt-max-chars-total 27000 \
  --include-domains "scholar.google.com,arxiv.org,pubmed.ncbi.nlm.nih.gov,semanticscholar.org,biorxiv.org,medrxiv.org,nature.com,science.org,cell.com,pnas.org,nih.gov" \
  -o sources/research_<topic>-academic.json

# Time-sensitive search via parallel-cli
parallel-cli search "your query" -q "keyword" \
  --json --max-results 10 --after-date 2024-01-01 \
  -o sources/research_<topic>.json

# Extract full content from a specific URL (use parallel-web extract)
parallel-cli extract "https://example.com/paper" --json

# Force Parallel Deep Research (slow, exhaustive) — via research_lookup.py
python research_lookup.py "your query" --force-backend parallel -o sources/research_<topic>.md

# Force Perplexity academic search — via research_lookup.py
python research_lookup.py "your query" --force-backend perplexity -o sources/papers_<topic>.md

# Auto-routed via research_lookup.py (legacy) — ALWAYS save to sources/
python research_lookup.py "your query" -o sources/research_YYYYMMDD_HHMMSS_<topic>.md

# Batch queries via research_lookup.py — ALWAYS save to sources/
python research_lookup.py --batch "query 1" "query 2" "query 3" -o sources/batch_research_<topic>.md
```

---

## MANDATORY: Save All Results to Sources Folder

**Every research-lookup result MUST be saved to the project's `sources/` folder.**

This is non-negotiable. Research results are expensive to obtain and critical for reproducibility.

### Saving Rules

| Backend | `-o` Flag Target | Filename Pattern |
|---------|-----------------|------------------|
| parallel-cli search (default) | `sources/research_<topic>.json` | `research_<brief_topic>.json` or `research_<brief_topic>-academic.json` |
| Parallel Deep Research | `sources/research_<topic>.md` | `research_YYYYMMDD_HHMMSS_<brief_topic>.md` |
| Perplexity (academic) | `sources/papers_<topic>.md` | `papers_YYYYMMDD_HHMMSS_<brief_topic>.md` |
| Batch queries | `sources/batch_<topic>.md` | `batch_research_YYYYMMDD_HHMMSS_<brief_topic>.md` |

### How to Save

**CRITICAL: Every search MUST save results to the `sources/` folder using the `-o` flag.**

**CRITICAL: Saved files MUST preserve all citations, source URLs, and DOIs.**

```bash
# parallel-cli search (DEFAULT) — save JSON to sources/
parallel-cli search "Recent advances in CRISPR gene editing 2025" \
  -q "CRISPR" -q "gene editing" \
  --json --max-results 10 --excerpt-max-chars-total 27000 \
  --include-domains "scholar.google.com,arxiv.org,pubmed.ncbi.nlm.nih.gov,nature.com,science.org,cell.com,pnas.org,nih.gov" \
  -o sources/research_crispr_advances-academic.json

parallel-cli search "Recent advances in CRISPR gene editing 2025" \
  -q "CRISPR" -q "gene editing" \
  --json --max-results 10 --excerpt-max-chars-total 27000 \
  -o sources/research_crispr_advances-general.json

# Academic paper search via Perplexity — save to sources/
python research_lookup.py "Find papers on transformer attention mechanisms in NeurIPS 2024" \
  -o sources/papers_20250217_143500_transformer_attention.md

# Deep research via Parallel Chat API — save to sources/
python research_lookup.py "AI regulation landscape" --force-backend parallel \
  -o sources/research_20250217_144000_ai_regulation.md

# Batch queries — save to sources/
python research_lookup.py --batch "mRNA vaccines efficacy" "mRNA vaccines safety" \
  -o sources/batch_research_20250217_144500_mrna_vaccines.md
```

### Citation Preservation in Saved Files

Each output format preserves citations differently:

| Format | Citations Included | When to Use |
|--------|-------------------|-------------|
| parallel-cli JSON (default) | Full result objects: `title`, `url`, `publish_date`, `excerpts` | Standard use — structured, parseable, fast |
| Text (research_lookup.py) | `Sources (N):` section with `[title] (date) + URL` + `Additional References (N):` with DOIs and academic URLs | Deep research / Perplexity — human-readable |
| JSON (`--json` via research_lookup.py) | Full citation objects: `url`, `title`, `date`, `snippet`, `doi`, `type` | When you need maximum citation metadata from deep research |

**For parallel-cli search**, saved JSON files include: full search results with title, URL, publish date, and content excerpts for each result.
**For Parallel Chat API backend**, saved files include: research report + Sources list (title, URL) + Additional References (DOIs, academic URLs).
**For Perplexity backend**, saved files include: academic summary + Sources list (title, date, URL, snippet) + Additional References (DOIs, academic URLs).

**Use `--json` when you need to:**
- Parse citation metadata programmatically
- Preserve full DOI and URL data for BibTeX generation
- Maintain the structured citation objects for cross-referencing

### Why Save Everything

1. **Reproducibility**: Every citation and claim can be traced back to its raw research source
2. **Context Window Recovery**: If context is compacted, saved results can be re-read without re-querying
3. **Audit Trail**: The `sources/` folder documents exactly how all research information was gathered
4. **Reuse Across Sections**: Multiple sections can reference the same saved research without duplicate queries
5. **Cost Efficiency**: Check `sources/` for existing results before making new API calls
6. **Peer Review Support**: Reviewers can verify the research backing every citation

### Before Making a New Query, Check Sources First

Before calling `research_lookup.py`, check if a relevant result already exists:

```bash
ls sources/  # Check existing saved results
```

If a prior lookup covers the same topic, re-read the saved file instead of making a new API call.

### Logging

When saving research results, always log:

```
[HH:MM:SS] SAVED: Research lookup to sources/research_20250217_143000_crispr_advances.md (3,800 words, 8 citations)
[HH:MM:SS] SAVED: Paper search to sources/papers_20250217_143500_transformer_attention.md (6 papers found)
```

---

## Integration with Scientific Writing

This skill enhances scientific writing by providing:

1. **Literature Review Support**: Gather current research for introduction and discussion — **save to `sources/`**
2. **Methods Validation**: Verify protocols against current standards — **save to `sources/`**
3. **Results Contextualization**: Compare findings with recent similar studies — **save to `sources/`**
4. **Discussion Enhancement**: Support arguments with latest evidence — **save to `sources/`**
5. **Citation Management**: Provide properly formatted citations — **save to `sources/`**

## Complementary Tools

| Task | Tool |
|------|------|
| General web search (fast) | `parallel-cli search` (built into this skill) |
| Academic-focused web search | `parallel-cli search --include-domains` (built into this skill) |
| URL content extraction | `parallel-cli extract` (parallel-web skill) |
| Deep research (exhaustive) | `research-lookup` via Parallel Chat API or `parallel-web` deep research |
| Academic paper search | `research-lookup` (auto-routes to Perplexity) |
| Google Scholar search | `citation-management` skill |
| PubMed search | `citation-management` skill |
| DOI to BibTeX | `citation-management` skill |
| Metadata verification | `parallel-cli extract` (parallel-web skill) |

---

## Error Handling and Limitations

**Known Limitations:**
- parallel-cli search: Requires `parallel-cli` to be installed and authenticated
- Parallel Chat API (core model): Complex queries may take up to 5 minutes
- Perplexity: Information cutoff, may not access full text behind paywalls
- All backends: Cannot access proprietary or restricted databases

**Fallback Behavior:**
- If `parallel-cli` is not found, install with `curl -fsSL https://parallel.ai/install.sh | bash` or `uv tool install "parallel-web-tools[cli]"`
- If parallel-cli search returns insufficient results, fall back to Perplexity or Parallel Chat API
- If the selected backend's API key is missing, tries the other backend
- If all backends fail, returns structured error response
- Rephrase queries for better results if initial response is insufficient

---

## Usage Examples

### Example 1: General Research (Routes to parallel-cli search)

**Query**: "Recent advances in transformer attention mechanisms 2025"

**Backend**: parallel-cli search (default, fast)

**Commands**:
```bash
parallel-cli search "Recent advances in transformer attention mechanisms 2025" \
  -q "transformer" -q "attention" -q "2025" \
  --json --max-results 10 --excerpt-max-chars-total 27000 \
  --include-domains "arxiv.org,semanticscholar.org,nature.com,science.org,ieee.org,acm.org" \
  -o sources/research_transformer_attention-academic.json

parallel-cli search "Recent advances in transformer attention mechanisms 2025" \
  -q "transformer" -q "attention" \
  --json --max-results 10 --excerpt-max-chars-total 27000 \
  -o sources/research_transformer_attention-general.json
```

**Response**: Synthesized findings with inline citations from academic and general sources, covering recent papers, key innovations, and performance benchmarks.

### Example 2: Academic Paper Search (Routes to Perplexity)

**Query**: "Find papers on CRISPR off-target effects in clinical trials"

**Backend**: Perplexity sonar-pro-search (academic mode)

**Response**: Curated list of 5-8 high-impact papers with full citations, DOIs, citation counts, and venue tier indicators.

### Example 3: Comparative Analysis (Routes to parallel-cli search)

**Query**: "Compare and contrast mRNA vaccines vs traditional vaccines for cancer treatment"

**Backend**: parallel-cli search (default, fast)

**Response**: Synthesized comparison from multiple web sources with inline citations, structured analysis, and evidence quality notes.

### Example 4: Market Data (Routes to parallel-cli search)

**Query**: "Global AI adoption in healthcare statistics 2025"

**Backend**: parallel-cli search (default, fast)

```bash
parallel-cli search "Global AI adoption in healthcare statistics 2025" \
  -q "AI healthcare" -q "adoption statistics" \
  --json --max-results 10 --excerpt-max-chars-total 27000 \
  --after-date 2024-01-01 \
  -o sources/research_ai_healthcare_adoption.json
```

**Response**: Current market data, adoption rates, growth projections, and regional analysis with source citations.

---

## Summary

This skill serves as the primary research interface with intelligent tri-backend routing:

- **parallel-cli search** (default): Fast, cost-effective web search with academic source prioritization via the parallel-web skill
- **Parallel Chat API** (`core` model): Deep, exhaustive multi-source synthesis (on explicit request only)
- **Perplexity sonar-pro-search**: Academic-specific paper searches only
- **Automatic routing**: Detects query type and routes to the optimal backend
- **Manual override**: Force any backend when needed
- **Academic prioritization**: Two-search pattern ensures scholarly sources surface for scientific queries
