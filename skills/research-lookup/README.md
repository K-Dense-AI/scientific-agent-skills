# Research Lookup

Parallel-first evidence compilation for scientific manuscripts. Academic retrieval
targets 60 verified, unique references by default and produces a research packet with
structured study evidence, claim provenance, contradictions, gaps, and section briefs.

`SKILL.md` is the authoritative workflow and safety reference.

## Routing

| Request | Backend |
|---|---|
| Manuscript literature or many academic references | Parallel Search + Extract |
| Fast current-information lookup | Parallel Search |
| Explicit deep/exhaustive report | Parallel Research |
| Explicit OpenAI-compatible synthesis | Parallel Chat |
| Optional alternative/failure fallback | Perplexity through OpenRouter |

A bare query uses Parallel Search. Parallel Chat remains available through
`--force-backend chat`, but automatic routing never selects it. The legacy
`--force-backend parallel` flag remains an alias for explicit Parallel Research.

## Setup

```bash
uv tool install "parallel-web-tools[cli]==0.9.3"
parallel-cli login
parallel-cli auth
```

CLI login may be replaced by `PARALLEL_API_KEY`. `OPENROUTER_API_KEY` is needed only
for explicit Perplexity use or an enabled fallback. Explicit Chat requires
`PARALLEL_API_KEY` in the process environment.
Both direct HTTP backends need `requests`; the CLI uses its own isolated tool
environment. Headless login in 0.9.3 is `parallel-cli login --no-browser`.

## Manuscript packet

```bash
python skills/research-lookup/scripts/research_lookup.py \
  "Evidence for the manuscript research question" \
  --academic \
  --target-references 60 \
  --context-file manuscript-context.json \
  --packet-dir sources/manuscript-research \
  --json
```

The academic workflow runs bounded searches for primary studies, reviews and
meta-analyses, seminal publications, methods/mechanisms, and contradictory evidence.
It deduplicates candidates and verifies the strongest sources in batches with
Parallel Extract.

Packet artifacts include:

- complete packet in JSON and Markdown
- normalized references in JSON and BibTeX
- evidence matrix
- claim-to-source map
- synthesis of consensus, conflicts, patterns, and gaps
- Introduction, Methods-rationale, and Discussion briefs
- coverage diagnostics and reproducible search ledger

The target is not padded. If 60 credible references cannot be verified, the packet
reports the shortfall.
`verified_references` means nonempty excerpts were retrieved by Extract, excluding
flagged retractions. DOI/PMID detection alone does not count. Review identity, claim
support, and correction/retraction status yourself before using the bibliography.

## Preserved compatibility

- reusable `ResearchLookup` class
- `--batch`, `--json`, and `-o/--output`
- explicit backend selection
- per-query error isolation
- DOI/URL citation extraction
- human-readable and structured output
- result fields such as `success`, `query`, `response`, `citations`, `sources`,
  `timestamp`, `backend`, `model`, and `usage`

## Other modes

```bash
# Fast bounded Search
python skills/research-lookup/scripts/research_lookup.py \
  "Latest official guidance" --no-academic

# Explicit Parallel Research
python skills/research-lookup/scripts/research_lookup.py \
  "Comprehensive review of topic" \
  --force-backend research \
  --processor pro

# Explicit Parallel Chat (never automatic)
python skills/research-lookup/scripts/research_lookup.py \
  "Synthesize the strongest evidence" \
  --force-backend chat \
  --chat-model core

# Explicit Perplexity
python skills/research-lookup/scripts/research_lookup.py \
  "Find academic evidence" \
  --force-backend perplexity
```

## Boundaries

This skill compiles external evidence. It does not generate the user's unpublished
Results or guarantee a PRISMA-complete systematic review. Use `literature-review` for
formal database searching, screening, exclusion tracking, and risk-of-bias procedures;
use `scientific-writing` to turn the packet into manuscript prose.

API contracts were reviewed on 2026-09-30 against official schemas, CLI 0.9.3,
and public OpenRouter model metadata. Service examples are illustrative; regression
tests mock paid calls. See [API contracts](references/api-contracts.md).
