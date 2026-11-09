# Reusable output contract

## Reader-facing report

Use the user's language and scale to the request.

1. **Decision and queue:** operational question, explicit assumptions, search date/bounds; ordered papers with action, exact focus, project use, limitations, and sources. Include substantive deferral/exclusion reasons.
2. **Intellectual map:** historical transitions and competing branches needed to interpret current results. Cite the downstream relationship behind influence claims. Use a small claim graph when useful.
3. **Evidence synthesis:** proposition-level convergence, supporting papers vs evidence families/confirmed independent tests, coverage diversity, supported/conditional/unknown claims, and strongest counterevidence. Separate observation, author interpretation, analyst inference.
4. **Tensions and project position:** classifications, alternatives, separating tests, gap-killing outcomes; project assumptions and next decision. “No established contradiction” is valid.
5. **Coverage:** sources/queries actually used, actual counts, failures, omitted branches, stop reason, and conclusions most vulnerable to missing evidence.

Graph: solid edges for source-supported relations, dashed for analyst hypotheses. `A --bounds--> B` means A limits B's generality. A citation is not a support relation.

## Files and updates

Normal saved runs: `report.md`, `evidence.json`, `search-log.md`. Log screened exclusions and failed searches too. Keep output outside the installed skill; do not implicitly overwrite prior runs.

Updates preserve stable IDs, original dates and version-specific evidence, append changed evidence, and identify changed conclusions/priorities. Retain superseded results with their original locators; do not transplant an old locator into a new version silently.

## evidence.json v1

Empty lists are valid. Use explicit unknowns instead of invention. Descriptive fields are nonempty strings unless explicitly typed otherwise below; this includes `scope`, `comparison`, `resolution_search`, and the four `test` fields. The checker validates structure and provenance constraints, not source truth or recall.

```json
{
  "schema_version": 1,
  "context": {
    "question": "Operational research question",
    "decision": "Decision informed by this map",
    "target_setting": "Known conditions and explicit unknowns",
    "mode": "scout",
    "as_of": "2026-10-31",
    "bounds": "Sources, years, access and budget",
    "stop_reason": "Budget or observed marginal decision change"
  },
  "papers": [], "claims": [], "propositions": [], "edges": [], "tensions": [],
  "reading_queue": [], "searches": []
}
```

Each **paper**: `id`, `title`, `url` (primary URL or `local:` URI for supplied file), `version` (possibly `unknown`), `access` (`fulltext`, `excerpt`, `abstract`, `metadata`, `unavailable`), `evidence_family` (shared-study ID or `unknown`). Access means actually inspected. Add verified status/date, aliases and retrieval dates when available. Different models/datasets alone do not prove independence.

Each **claim**:

- `id`, `paper_id`, `statement`, `kind` (`empirical`, `theoretical`, `interpretive`), `scope` (conditions and unknowns).
- `evidence`: `locator`, `observation`, `authors_interpretation`, `analyst_inference`. Observation is a paraphrase/result, not just a citation.
- `assessment`: `strength` (`supported`, `provisional`, `unsupported`), `reason`, `limitation`. Supported means this scoped claim is backed by inspected primary content. Abstract/metadata-only records cannot be supported. Excerpts support only inspected regions.
- `uses`: list of `role` (SKILL.md vocabulary), `decision`, `transfer_assumption` objects.
- Optional `evidence_family` overrides the paper's default for this result. Use it when one paper contains separate experiments or reuses another paper's results. Reused results retain their originating family; one paper can contain more than one evidence contribution.

Each **edge**: `id`, `source`/`target` claim IDs; `relation` (`supports`, `contradicts`, `bounds`, `depends_on`, `imports`, `supersedes`); `status` (`source_supported`, `hypothesis`); `evidence_claims` (IDs supporting the relation); `rationale`; `independence` (`independent`, `shared`, `unknown`). Source-supported relations require inspected evidence. Shared families cannot be independent; different IDs alone do not establish independence. A source-supported contradiction also requires a `comparable_conflict` tension for that pair.

Each **tension**: `id`, `claim_ids` (at least two), `classification` (contradictions.md), `comparison` (aligned/different/unknown conditions), `explanation`, `resolution_search` (checked sources or explicitly not checked). For consequential unresolved questions include `alternatives` (at least two) and `test`: `variable`, `controls`, `predictions` (distinct outcomes), `gap_killer`. Required for `comparable_conflict`; also for scope-mismatch/inconclusive frontiers. Mark proposed frontiers with `frontier_candidate: true`; this is not a novelty verdict.

Each **reading_queue** item: `paper_id`, `action` (SKILL.md vocabulary), `focus`, `reason` explaining decision impact. List order is priority. Include deferrals/exclusions here or in the screening log for large pools.

Each **proposition**: `id`, `statement`, `scope`, `supporting_claim_ids`, `counter_claim_ids`, `candidate_claim_ids` (all lists of claim IDs); `synthesis` (`convergent`, `conditional`, `contested`, `insufficient`); `independent_evidence_count` (nonnegative integer or null); `independence_assessment`, `coverage`, and `justification` (strings). Supporting/counter lists contain inspected, supported scoped claims; abstract-only leads belong in candidate lists. Counts of supporting papers and known families can be derived from claim → paper links, but independent count requires a reasoned check, not merely unique family IDs. Use null when unresolved. Include at least the propositions bearing on the research decision; empty is appropriate only without extractable claims.

Before assigning proposition support/counter IDs, check their logical relationship at the stated scope. A claim's own `supported` assessment does not automatically support a broader proposition. Local negative effects can be candidate evidence for a universal failure claim; they do not establish it. An in-scope positive case can counter that universal claim. Explain partial/indirect relevance in candidate evidence rather than counting it as direct support.

`independent_evidence_count` counts confirmed mutually independent supporting evidence contributions, including an originating study. It is not the number of external replications beyond that study: one known originating result can be count 1 while having zero external replications. Use null if dependence prevents determining the count; explain uncertainty. Optional `independent_replication_count` may record the separate latter quantity.

Each **search**: `channel`, `query`, `source`, `date`, `outcome`, `kept_ids` (paper IDs). Failures/zero usable results are outcomes. Offline runs explicitly state no live search and log supplied-corpus review; never fabricate executed queries.

The checker exits nonzero for structural/provenance contradictions and emits separate cautions. Fix bookkeeping; downgrade unsupported strength/status rather than inventing evidence. Manually compare source locations before reliance.
