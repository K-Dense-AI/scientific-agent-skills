---
name: zhengming-skill-fabric
description: >-
  Meta-orchestrator that turns a large collection of Agent Skills into a composable,
  evidence-traceable pipeline instead of isolated tools. Use it when you have many
  skills installed but they do not talk to each other: it adds intent routing,
  multi-skill composition, a unified evidence ledger, local-first execution with an
  opt-in cloud-upgrade gate, a fail-closed sandbox, and a self-evolution hook.
  Authored by chenhz01; full methodology and one-click scripts at
  https://github.com/chenhz01/ai-agent-skill-breakthrough.
metadata:
  version: "1.0"
  skill-author: chenhz01
---

# Zhengming Skill Fabric — Meta-Orchestrator

> A pile of strong skills is still a pile. Fabric adds the connective tissue:
> route them, compose them, trace every claim, gate the cloud, roll back safely,
> and let the system evolve itself.

## When to Use

- You installed a large skill collection (e.g. this repository, K-Dense-AI/scientific-agent-skills)
  but find the skills act as disconnected islands.
- A task needs **two or more** skills chained together (research chain, data chain, doc chain).
- You need **provenance**: every claim must trace back to a source, and AI-generated artifacts
  must be clearly labeled as non-measurement evidence.
- You want local-first execution with cloud only as an explicit, labeled upgrade.

## Architecture (six layers)

```
user intent ─▶ [1 intent router] ─▶ [2 skill registry] ─▶ [3 composition engine]
                                                          │
                          ┌───────────────────────────────┤
                          ▼                               ▼
                   [4 local-first sandbox]        [5 cloud-upgrade gate]
                      (fail-closed)                  (label ai_generated)
                          │                               │
                          └──────────▶ [6 unified evidence ledger] ◀──┐
                                        │                            │
                                    feedback│                        │ promote
                                        ▼                            ▼
                                [self-evolution engine] ─────▶ registry update
```

## Intent Router (Layer 1)

Compile each skill's `use-when` into an intent table. Single intent → dispatch directly
(local-first). Compound intent → trigger the composition engine.

| Intent | Primary skill | Local? | Note |
|---|---|---|---|
| Architecture / flow / state-machine diagram | archify | ✅ | deterministic, SHA-256 delivery |
| Markdown + Mermaid docs | markdown-mermaid-writing | ✅ | text-is-truth |
| Paper / DOI / citation graph | paper-lookup | ✅ | 11 APIs, reproducible provenance |
| Systematic literature review (PRISMA) | literature-review | ❌ cloud | needs web access |
| Citation management / BibTeX | citation-management | ✅ | — |
| Evidence-traceable writing | scientific-writing | ✅ | E/C/N/M/O/R ledger |
| Evaluate claims / bias / GRADE | scientific-critical-thinking | ✅ | — |
| Hypothesis from observation | hypothesis-generation | ✅ | — |
| Web semantic search | exa-search | ❌ cloud | needs API key |
| Deep research / monitoring | parallel-web | ❌ cloud | needs API key |
| Statistics | statistical-analysis | ✅ | — |
| Units / uncertainty | uncertainty-and-units | ✅ | GUM + Monte Carlo |
| DataFrames / EDA | polars / exploratory-data-analysis | ✅ | fail-closed |
| Publication-grade figures | scientific-visualization | ✅ | honesty guardrails |
| Word / PPT / Excel / PDF | docx / pptx / xlsx / pdf | ✅ | — |
| Scenario simulation | what-if-oracle | ✅ | 0·IF·1 principle |
| Market report / TAM | market-research-reports | ✅ | claim/source ledger |
| Propose new skills from behavior | autoskill | ⚠️ | repurpose runtime traces |

## Composition Engine (Layer 3)

Each pipeline defines an "upstream artifact schema → downstream consumption contract"
and is chained by the engine using handoff contracts.

- **Research chain**: `paper-lookup` (provenance) → `citation-management` (BibTeX) →
  `literature-review` → `scientific-writing` (E/C/N/M/O/R) → `docx`/`pptx` + `scientific-slides`
- **Data chain**: `polars` (ETL) → `exploratory-data-analysis` (audit) →
  `statistical-analysis` (test) → `scientific-visualization` (figure);
  `uncertainty-and-units` auto-intervenes at input boundaries and figure annotations
- **Doc chain**: `markitdown` (→md) → `docx`/`pdf`/`xlsx`/`pptx`;
  `archify` (diagram) + `markdown-mermaid-writing` (IR)
- **Meta chain**: runtime-trace → `autoskill` (repurposed) → self-evolution gate → registry promote

## Unified Evidence Ledger (Layer 6, shared schema)

All skills write to one ledger, replacing each skill's isolated ledger
(writing's E/C/N/M/O/R, market's claim/source, archify's SHA-256).

```json
{
  "ledger_id": "fabric-run-<timestamp>",
  "entries": [
    {
      "id": "E1",
      "type": "source | transform | claim | artifact | decision",
      "content": "summary text",
      "source_ref": "E0 | DOI | file:<sha256> | url",
      "confidence": 0.0,
      "method": "skill-name@version",
      "local": true,
      "ai_generated": false,
      "sha256": "…",
      "timestamp": "ISO8601"
    }
  ]
}
```

Rules: ① downstream reads only upstream `source_ref`, never rebuilds it;
② `ai_generated=true` entries are force-labeled "non-measurement evidence";
③ every `claim` must trace back to a `source`.

## Local-first / Cloud-upgrade (Layer 4–5)

- Default: everything runs on local skills (data + document + analysis skills).
- Cloud skills are invoked **only** when the task explicitly needs cloud capability
  (semantic search, AI image generation, GPU) **and** the user permits it; the ledger
  then marks `ai_generated=true` + "non-measurement evidence".
- Sensitive data (personal files, private context) is **never** sent to the cloud.

## Safety Sandbox (fail-closed)

- Unknown skill / unknown intent → refuse and report, do not guess.
- Bounded IO: do not auto-fetch URLs, do not follow symlinks, do not cross `--root`.
- Writes / external actions (send mail, publish, delete) → human-accountability gate.

## Self-evolution Hook

Absorbs `autoskill`'s observe→cluster→match→synthesize, but **repurposes the data
source to runtime execution-trace logs** (not screen recording), with an auto-promote gate:

1. Record each orchestration: intent → skill → artifact → result.
2. Cluster repeated patterns, match against registry embeddings.
3. Synthesize reuse / compose / novel proposals.
4. Proposals enter an auto-promote gate (human confirmation) before writing to the registry.

## Circuit Breakers

- Any skill fails → roll back locally to the previous ledger snapshot; do not pollute global state.
- Cloud timeout / rate-limit → degrade to a local equivalent skill, or explicitly tell the user
  "capability unavailable".
- Ledger contains an untraceable claim → mark the whole pipeline "insufficient evidence",
  do not deliver assertions.

## References

- [methodology.md](references/methodology.md) — the full "learn → surpass → break through → use"
  loop, honest inventory, parallel-capability-audit SOP, and the simplify/isolate playbook.
- Standalone home with the one-click `switch-science.ps1` script and bilingual README:
  **https://github.com/chenhz01/ai-agent-skill-breakthrough**
