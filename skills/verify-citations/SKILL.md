---
name: verify-citations
description: Audit the references of a scientific manuscript against live bibliographic databases before submission or review. Detects hallucinated references that resolve nowhere, flags retracted or withdrawn papers via Crossref and OpenAlex, catches metadata mismatches (wrong year, wrong authors, garbled titles) that signal LLM-mangled citations, and renders a per-citation markdown audit report with a shared verdict taxonomy. This skill should be used when fact-checking a manuscript's bibliography, checking citations for retraction, auditing AI-generated references, or preparing a camera-ready reference list.
allowed-tools: Read Write Edit Bash WebFetch
license: MIT License
compatibility: Python 3.9+. Network access needed for api.crossref.org, export.arxiv.org, eutils.ncbi.nlm.nih.gov, and api.openalex.org (all keyless; CROSSREF_EMAIL/OPENALEX_EMAIL enable polite pools). Report generation is offline.
metadata:
  version: "1.0"
  skill-author: Prajwal Rawoorkar
---

# Verify Citations

Audit a manuscript's references against live sources and report, per citation,
whether the work exists, whether the stated details match it, and whether it
has been retracted.

LLM-assisted writing has made two failure modes common: references that look
plausible but do not exist, and references that point at a real paper while
stating the wrong year, authors, or title. Both survive casual proofreading.
This skill runs a systematic pass instead: parse the reference list, resolve
every entry against Crossref/arXiv/PubMed, compare stated metadata with the
canonical record, check retraction status, and render an audit report.

This complements `citation-management` (which finds, formats, and generates
references); this skill audits an existing list.

## When to Use

Use this skill when:
- Fact-checking a manuscript's bibliography before submission
- Auditing references in AI-generated or AI-assisted text
- Checking whether any cited work has been retracted or withdrawn
- Verifying that cited metadata (authors, year, venue) matches reality
- Producing an audit trail of citation quality for co-authors or reviewers

## Workflow

### 1. Parse the reference list

Extract a structured reference list from markdown, LaTeX, or BibTeX:

```bash
python scripts/parse_references.py manuscript.md --output refs.json
python scripts/parse_references.py manuscript.tex --in-text --output refs.json
python scripts/parse_references.py references.bib --output refs.json
```

The parser is permissive: an entry survives on any identifier (DOI, arXiv ID,
PMID) or title it can recover. `--in-text` additionally extracts checkable
citation sentences (those carrying statistics or quoted phrases) for manual
claim inspection.

### 2. Verify the references

Resolve every entry and assign a verdict:

```bash
python scripts/verify_references.py refs.json --output verification.json
```

Resolution order per entry: DOI -> Crossref, arXiv ID -> arXiv Atom API, PMID
-> PubMed E-utilities, then Crossref bibliographic search for title-only
entries (best title similarity wins, threshold 0.85). Set
`CROSSREF_EMAIL`/`OPENALEX_EMAIL` to join provider polite pools.

Verdicts (shared taxonomy, see `references/verdicts.md`):

| Verdict | Meaning |
|---|---|
| `verified` | resolved; stated metadata matches the source |
| `metadata-mismatch` | resolved, but stated details disagree -- wrong year, wrong first author, or a garbled title |
| `retracted` | the work has been retracted or withdrawn |
| `not-found` | no provider knows the work -- prime hallucination suspect |
| `unresolved` | network/API error prevented checking |
| `skipped` | nothing checkable (no identifier, no title) |

The retraction check runs inside this pass when Crossref supplies
`update-to`/`updated-by` metadata.

### 3. Standalone retraction sweep (optional)

Check an existing DOI list or .bib file for retractions without full
verification:

```bash
python scripts/check_retractions.py references.bib --output retractions.json
python scripts/check_retractions.py --doi 10.1038/s41586-021-03819-2
```

Crossref is the primary source (official retraction notices); OpenAlex
`is_retracted` is the fallback.

### 4. Render the audit report

```bash
python scripts/generate_report.py verification.json --output audit.md --title "Manuscript v3 citation audit"
```

The report lists flagged references worst-first (retracted -> metadata
mismatch -> not found), with the stated-vs-resolved details and mismatch
reasons for each, then the full reference table for the record.

## Worked example

Given a manuscript with a hallucinated reference and a year typo:

```
[1] Vaswani, A. et al. (2017). Attention Is All You Need. NeurIPS.
[2] Zhang, L. (2023). Scaling laws for reward model overoptimization. NeurIPS.  <- wrong author/year
[3] Smith, J. (2022). Quantum leverage in protein folding. Nature.  <- does not exist
```

`verify_references.py` reports `[1] verified`, `[2] metadata-mismatch`
(resolved author Gao, resolved year 2022 via Crossref search), `[3] not-found`
-- and `generate_report.py` renders the actionable audit.

## Interpreting results

- **Verdicts are evidence, not judgement.** `not-found` on genuinely obscure
  documents (theses, datasets, grey literature) can be a false positive;
  hand-verify flagged items before removing them.
- **`metadata-mismatch` is the high-signal verdict** for LLM-written text:
  the cited work is real, but the manuscript describes a different one.
- Title-only matching uses a similarity threshold; short titles increase
  false-match risk, so prefer entries that carry a DOI.

## Important caveats

- Crossref, arXiv, and PubMed cover published/preprint literature; they will
  not find textbooks, websites, software, or most grey literature. Entries
  without DOI/arXiv/PMID and a title fall back to search or are skipped.
- Rate limits: the scripts pause 1s between provider calls by default
  (`--pause`); polite-pool emails raise the anonymous ceilings considerably.
- In-text claim verification (does the source support the sentence?) is a
  reading task for the agent: use `--in-text` output as the checklist, fetch
  the source abstract, and compare the claim against it.

## Pairs with

- `citation-management` -- format and fix the references this skill flags
- `paper-lookup` -- fetch abstracts/full text for claim-level verification
- `peer-review` -- fold this audit into a structured review pass

## References

- `references/verdicts.md` -- full verdict taxonomy and interpretation
- `references/api-endpoints.md` -- provider endpoints, limits, and polite pools

## License

MIT
