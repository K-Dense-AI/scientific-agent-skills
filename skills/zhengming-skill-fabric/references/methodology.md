# Methodology — Learn → Surpass → Break through → Use

> How to turn a large open-source Agent Skills collection from "installed but idle"
> into "actually used, and surpassed". Authored / practiced by **chenhz01**,
> executed with Zhengming (AI scientist). Full repo with scripts and bilingual README:
> **https://github.com/chenhz01/ai-agent-skill-breakthrough**

This document is the reasoning behind the `zhengming-skill-fabric` skill. It is
portable — no local paths, runs on any Agent Skills setup.

---

## 0. Honest inventory first

Before doing anything, count what you actually use.

- Install a collection (e.g. K-Dense-AI/scientific-agent-skills, 163 skills).
- Truthfully record how many you have **run in a real task**. Typically ≤ 7 of 163.
- Conclusion: **installed ≠ used.** The bottleneck is not more skills — it is the
  lack of glue between them.

## 1. Learn (extract capability DNA)

Do not read 163 SKILL.md files into one context. Split into 3–4 clusters by function,
dispatch one isolated subagent per cluster to read and return a structured summary
(table of name / purpose / capability-DNA / use-when / local-runnable / gaps). Only
the summary returns to your context.

Cross-validated consensus on the 35 universal skills revealed one collective gap:
**they are islands** — no router, no composition protocol, no shared provenance,
hard dependency on external APIs.

## 2. Surpass (find the collective gap)

Aggregate the cluster summaries. The gap that survives cross-validation is the real
one. For the scientific collection it was: *no orchestration layer*. That is the
target — not building a 164th isolated skill, but the connective tissue.

## 3. Break through (build the orchestration layer)

Build the meta-orchestrator (see `../SKILL.md`): intent router + composition engine +
unified evidence ledger + local-first sandbox + cloud-upgrade gate + self-evolution
hook. This is the "surpass" artifact: it makes the existing 163 skills more capable
*together* than any single one.

## 4. Use (actually run it)

Wake up ≥ 4 skills in one real pipeline and ship an artifact:

- `archify` → render an architecture diagram (deterministic, SHA-256).
- `what-if-oracle` → scenario simulation of adoption.
- `scientific-critical-thinking` → audit the design.
- `scientific-writing` → its evidence ledger schema is internalized into the fabric.
- `markdown-mermaid-writing` → express the research chain.

## 5. Simplify / isolate (keep context lean)

163 installed ≈ 500 MB and a heavy context window. Keep a small resident set and
isolate the rest:

| Location | Contents | Context cost |
|---|---|---|
| `skills/` (resident) | ~35 universal skills | low (daily) |
| `skills-science/` (isolated) | ~129 research skills (full backup) | 0 (not loaded) |

Provide a one-click reversible mount: `on` restores the 129 (heavier context),
`off` returns to the 35 (default). See `switch-science.ps1` in the standalone repo.

### Isolate playbook (real pitfalls)

- Use **Junction**, not SymbolicLink (symlinks need elevation and fail for normal users).
- To unmount, `rmdir` the junction — it deletes only the link, not the target source.
- Delete links by **exact name match against the isolate directory**; `Test-Path` on a
  dangling directory link returns a false positive.
- Always run the script with an execution-policy bypass; otherwise it silently does nothing.

## 6. Why this belongs upstream

A collection of 163 skills is most valuable when agents can **compose** them with
provenance. `zhengming-skill-fabric` is contributed back so others can route, compose,
and trace their skills instead of letting them sit idle. Credit and the full
reproducible setup live at **https://github.com/chenhz01/ai-agent-skill-breakthrough**.
