# Map, reduce, saved results, and figure analysis

Reviewed against 0.7.92 CLI/SDK source, native results help, and the current
[core reference](https://paperclip.gxl.ai/skills/full_skill.md) and
[map documentation](https://paperclip.gxl.ai/docs). No LLM reader or authenticated extraction was
executed during this review. Examples below are illustrative and use placeholder result IDs.

## Small extraction pipeline

```bash
paperclip search -s pmc "lipid nanoparticle mRNA delivery" -n 5
paperclip filter --from s_ID "in vivo delivery with quantified efficiency"
paperclip map --from s_ID "Report vector, target cell type, efficiency, sample size, and supporting lines. State 'not reported' for absent fields."
paperclip results m_ID --save map.txt
paperclip reduce --from m_ID --strategy table --columns "paper,vector,cell type,efficiency,n" "Compare delivery approaches"
```

Substitute actual returned `s_`/`m_` IDs. `filter` modifies the saved cohort in place; export the
original if the screening trail matters. Pass `--from` explicitly to reduce instead of relying on
whatever the service considers the most recent map. Reader output can be truncated in the terminal;
retrieve full per-paper answers with `results`, not only a printed `/.gxl/` scratch pointer.

Start with 3–10 documents and explicit fields. Ask for absent values so a missing answer is not
silently converted into zero or a negative finding. Specify units, denominator, population, time
point, and outcome definition when comparing quantitative results. Record failures separately from
successfully read papers that did not report a field.

## Strict output schema

Current `--output-schema` accepts **Draft 2020-12 JSON Schema**, including for the default quick
reader. The old `--output_schema` spelling and informal field maps are deprecated aliases.

```bash
paperclip map --from s_ID \
  --output-schema '{"type":"object","required":["effect","unit","evidence_lines"],"additionalProperties":false,"properties":{"effect":{"type":["number","null"]},"unit":{"type":["string","null"]},"evidence_lines":{"type":"array","items":{"type":"string"}}}}' \
  "Extract the primary reported effect, its unit, and exact supporting L-number ranges. Use null and an empty evidence list when absent."
```

The service requires one JSON value per paper, validates it, gives invalid output one correction
attempt, and fails the paper if the correction still violates the schema. Citation fields are not
automatically inserted: define them explicitly and verify their values against the source. A schema
can validate shape and types while still accepting a scientifically wrong measurement.

## Workers and recovery

The 0.7.92 client accepts `quick-reader`, `eligibility-screen`, `scorecard-verifier`,
`scorecard-verifier-fast`, `structured-extraction`, and `exhaustive-extraction`. A valid name does not
prove that a particular server/account enables every worker. Use the relevant current routine for
specialized workflow setup; do not substitute one worker for another solely because it accepts JSON.

- Default `quick-reader`: bounded per-paper questions; supports `--output-schema`.
- `eligibility-screen`: screening against explicit inclusion/exclusion criteria.
- `structured-extraction`: requires a nonempty `--output-schema`, rejects `--claim-schema` and
  `--repo`, and does not persist directly to a repo.
- `exhaustive-extraction`: new runs require `--claim-schema JSON` and `--repo NAME` or an active repo.
  Use it only for an authorized verified collection and follow its routine's schema.

Inspect deployed `map --help` for worker-specific concurrency, limit, and offset controls. The old
blanket recommendation of concurrency 100/cap 256 has not been verified against the current server;
start with a small cohort rather than applying those historical values.

```bash
paperclip map --resume m_ID
paperclip map --resume m_ID --retry-failed
paperclip map --cancel m_ID
```

The client validates one resume ID. `--retry-failed` is a flag and requires `--resume`; it does not
take its own map ID. Resume a known durable run and inspect final successes/failures instead of
blindly launching overlapping work. Cancellation is a mutation and does not necessarily undo work
already completed or billed. Dataset-bound workflows can require additional bindings from their
saved run; retain those identifiers.

For a **persistent Paperclip dataset**, read `paperclip routines show paperclip-data-extraction`
and current `paperclip extraction --help` first. Ordinary map results are not a dataset checkpoint;
the routine's writes, verification, and readback steps must complete before reporting persistence.
Do not create a remote grid just because the user requested a table in an answer.

## Reduce and evidence

Supported documented strategies are `summarize`, `table`, `themes`, `consensus`, `bullet_points`, and
`extract`. `--columns` requests comma-separated table columns. These are generation instructions,
not guaranteed formatting or scientific validation. If output is prose, construct the requested
table from the per-paper results. If an important field is absent, inspect the map and source
rather than assuming the reducer reread all papers.

Old 0.7.14–0.7.15 runs produced prose for `table` and truncated document IDs inside citation markers.
Those are historical observations, not reverified defects in 0.7.92. Independently of version:

1. Resolve the complete document ID from structured search/saved results or metadata.
2. Read the cited passage in `content.lines`.
3. Check that the number, units, population, and comparison match the claim.
4. Cite the actual Paperclip URL and `L` range. LLM summaries alone are not primary evidence.

Read only the passages needed to validate material quantitative claims and quotations; there is no
need to repeat an entire extraction simply to produce a final table.

## Results and figure analysis

```bash
paperclip results --list
paperclip results s_ID --save search.csv
paperclip results m_ID --save map.txt
paperclip results s_ID --sample 10 --seed 42
```

Search metadata, map answers, and portable cohort bundles are different output formats. Inspect the
saved data rather than assuming one universal CSV header or that a preview contains every answer.
`--sample` selects at most 100 saved papers and records/reuses a seed; it does not retrieve more
papers from the corpus.

```bash
paperclip ls /papers/PMC10945750/figures/
paperclip ask-image /papers/PMC10945750/figures/pnas.2307796121fig01.jpg \
  "What are the axes, conditions, and uncertainty bars?"
paperclip ask-image /papers/PMC10945750/figures/pnas.2307796121fig01.jpg --fn extract-data
paperclip ls /papers/PMC10945750/supplements/
```

Use the actual publisher filename returned by `ls`; do not guess `fig1.jpg`. Vision extraction from
a plot is an estimate. Prefer numerical text or deposited tables when precision matters, and
identify digitized values explicitly. Inspect supplementary format before choosing a reader.
`cat` text redirection and SDK `pull()` are not proof of a valid local binary image download.
