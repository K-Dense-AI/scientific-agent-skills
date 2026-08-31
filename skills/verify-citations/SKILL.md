---
name: verify-citations
description: Verify citations and references in scientific documents against live sources. Checks that cited papers actually exist, that DOIs resolve, and that cited claims match what the source actually says. This skill should be used when you need to fact-check a manuscript before submission, validate references in a research report, or ensure cited evidence supports the claims being made.
allowed-tools: Read Write Edit Bash WebSearch WebFetch
license: MIT License
compatibility: Requires network access to api.stipple.sh. Free anonymous tier available (no API key needed).
metadata:
  version: "1.0"
  skill-author: Sketchjar
tags: [citations, verification, fact-checking, evidence, scientific-writing, peer-review]
---

# Verify Citations

Verify that citations in a scientific document actually resolve and support the claims they're attached to. Returns a verification coverage score, per-citation resolution status, recomputed arithmetic, and unsupported-claim detection.

## Why this matters for scientific workflows

LLM-generated manuscripts and AI-assisted literature reviews cite papers that look plausible but don't exist. Decimal shifts corrupt stated figures. Unsupported claims survive peer review when reviewers can't check every citation. This skill runs a systematic verification pass before submission or review.

## How it works

Uses the [Stipple API](https://www.stipple.sh) to verify a document's citations against live sources. The API checks that each citation resolves, that cited claims match what the source actually says, and that all arithmetic in the document is correct.

## Usage

### Verify a manuscript

```bash
curl -X POST https://www.stipple.sh/v1/verify-references \
  -F "file=@manuscript.pdf" \
  -H "Authorization: Bearer $STIPPLE_API_KEY"
```

### Deep verification (cross-checks against live web sources)

```bash
curl -X POST "https://www.stipple.sh/v1/verify-references?deep=true" \
  -F "file=@manuscript.pdf"
```

### Verify pasted text (no file upload)

```bash
curl -X POST https://www.stipple.sh/v1/verify-references \
  -H "Content-Type: application/json" \
  -d '{"text": "As reported by Smith et al. (2023), mRNA vaccine efficacy was 94.1%..."}'
```

## Interpreting results

| Field | What it tells you |
|---|---|
| `verification_coverage` | Percentage of claims verified (e.g. "78%") |
| `citations[]` | Per-citation: resolved and matching, resolved but mismatched, or unresolvable |
| `arithmetic[]` | Recomputed figures vs stated figures (catches decimal shifts, wrong sums) |
| `unsupported_claims[]` | Claims with no citation at all |

## Example output

```
Verification coverage: 82%

Citations: 41/50 resolve and match
  [+] "CRISPR-Cas9 editing efficiency" — matches Nature Biotechnology 2023
  [-] "mRNA vaccine efficacy 94.1%" — source states 94.6%, decimal shifted

Arithmetic: 18/19 recompute correctly
  [x] Total adverse events — stated 12.3%, actual 21.0% (denominator error)

Unsupported claims: 3
  [!] "First demonstration of in-vivo base editing in primates" — no citation
```

## Important caveats

- Reports **verification coverage**, not a truth verdict — unverified ≠ false
- `confidence` on extracted values is the model's self-report, not calibrated accuracy
- Deep verification is slower but resolves citations against live web sources
- Free anonymous tier: shared weekly allowance. Get a free key at [stipple.sh](https://www.stipple.sh) for your own metering

## Pairs with

- `citation-management` skill — manage and format your references after verification
- `verify-document` (in [stipple-agent-skills](https://github.com/Sketchjar/stipple-agent-skills)) — check document authenticity before trusting extracted values

## License

MIT
