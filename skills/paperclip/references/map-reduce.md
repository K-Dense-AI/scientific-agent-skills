# map, reduce, results, and figure analysis

`map` runs an LLM reader over each document in a result set, in parallel. `reduce` synthesizes those
per-document answers into one output. Together they are how you answer a question that spans papers
without reading each one yourself.

Flags below come from `paperclip map --help` and `paperclip reduce --help` at 0.7.14–0.7.15. The
`quick-reader` map and the `table` reduce strategy were executed live against a three-paper result
set; the other workers and the resume/cancel paths are transcribed from `--help` and not exercised.

Examples omit the auth prefix. Every real invocation needs it:
`[ -f .env ] && { set -a; . ./.env; set +a; }; paperclip <command>`.

Two verified defects to know before you start — details in their sections below:

1. **`--strategy table` returns prose, not a table**, with or without `--columns`.
2. **`reduce` output embeds truncated document ids.** They do not resolve, so a citation URL built
   from them is broken.

## The pipeline

```bash
paperclip search -s pmc "lipid nanoparticle mRNA delivery" -n 10    # → s_abc123
paperclip filter --from s_abc123 "in vivo delivery with quantified efficiency"
paperclip map    --from s_abc123 "What delivery vector, target cell type, and transfection efficiency were reported?"
paperclip reduce --from m_def456 --strategy table "Compare vector, cell type, and efficiency"
```

Result ids: `s_*` from `search`/`filter`/`grep`, `m_*` from `map`, `r_*` for the artifact `reduce`
emits (`Artifact ID: r_36626b45`). `reduce` defaults to the most recent map if `--from` is omitted,
but pass it explicitly — it is cheap insurance against picking up an unrelated run.

A completed map prints a progress bar, a per-paper preview **truncated to roughly one line each**, and
a `Full results: /.gxl/map_<id>.txt` pointer:

```text
  [######..............]  1/3 papers  run m_4b4632df  [2s]
Map complete: 3/3 tasks succeeded in 3571ms
Results ID: m_4b4632df
Full results: /.gxl/map_m_4b4632df.txt

  [success] Piperazine-derived lipid nanoparticles deliver mRNA to immune cells in  (PMC9376583)
    Based on the paper, here are the details ... * **Delivery Vector:** Piperazine-derived lipi
```

**That `/.gxl/` path cannot be read** — `cat` on it returns "No such file" even though `ls /.gxl/`
lists it. To see the untruncated per-paper answers, use `results`:

```bash
paperclip results m_4b4632df                       # full output, with real document ids
paperclip results m_4b4632df --save map.csv        # or export it
```

## `map`

```text
map --from RESULTS_ID [OPTIONS] "query"

  --from ID              Result id from a previous search (required)
  --worker NAME          quick-reader (default) | eligibility-screen | exhaustive-extraction
  --output_schema JSON   Structured output schema
  --claim-schema JSON    JSON Schema each exhaustive claim must satisfy
  --repo NAME            Shared repo receiving validated exhaustive claims
  --resume MAP_ID        Continue pending work; never reruns successful papers
  --retry-failed         With --resume, also retry failed papers
  --cancel MAP_ID        Durably request cancellation; pending work will not start
  -n, --limit N          Limit number of papers processed
  --offset N             Skip the first N papers
  -j, --max-concurrent N Concurrent extraction subagents (default 100, server hard cap 256)
```

### Workers

| Worker | Use for |
|---|---|
| `quick-reader` (default) | Ordinary extraction and per-paper Q&A |
| `eligibility-screen` | Single-turn structured screening of a full paper against inclusion criteria — the screening step of a systematic review |
| `exhaustive-extraction` | Multi-turn Claude tool worker that inspects methods, results, tables, figures, and supplements. Slow and thorough; for quantitative extraction |

### Writing the map query

This is where map runs succeed or fail.

- **Enumerate every field you want.** The worker returns what you asked for and nothing else.
- **Name the section** when you know it: "From the Methods section, extract the cell line, passage
  number, and transfection reagent."
- **Ask for the absent case explicitly:** "If the paper does not report a sample size, say
  'not reported'." Otherwise you cannot distinguish a gap from a miss.
- Bad: `"Summarize this paper."`
- Good: `"What delivery vector was used, what cell type was targeted, and what transfection efficiency was reported? State 'not reported' for any field the paper omits."`

### Sizing

Keep `quick-reader` runs to **3–10 papers** for interactive work — one LLM call per paper. For larger
runs, prefer a single `map` with a higher `-j` over several overlapping map requests; the server caps
concurrency at 256 and per-user limits may be lower.

After a map completes, use its output to organize the answer. Verify source lines for material
quantitative claims and direct quotations before citing them; inspect only the relevant passages
or supplements rather than repeating the entire extraction. Map output is an LLM summary, so the
source-line citation contract still applies.

### Structured output

```bash
paperclip map --worker eligibility-screen \
  --output_schema '{"decision":"yes|no|uncertain","reason":"string"}' \
  --from s_abc123 "Apply the protocol eligibility criteria"
```

```bash
paperclip map --worker exhaustive-extraction \
  --repo review \
  --claim-schema '{"type":"object","required":["type"],"properties":{"type":{"type":"string"}}}' \
  --from s_yes "Extract all requested claims"
```

`--repo` plus `--claim-schema` routes validated claims straight into a repo — the machinery behind the
`paperclip-meta-analysis` workflow. Only reach for it when the user asked for a verified corpus.

### Long runs

```bash
paperclip map --resume m_abc123                  # continue; successful papers are not redone
paperclip map --resume m_abc123 --retry-failed   # also retry failures
paperclip map --cancel m_abc123                  # stop pending work
```

Resume is durable, so a large extraction that hits a timeout is recoverable — resume it rather than
restarting.

## `reduce`

```text
reduce --from MAP_ID [OPTIONS] "question"

  --from ID           Map result id (m_*); defaults to the most recent map
  --strategy STR      summarize (default) | table | themes | consensus | bullet_points | extract
  --columns COL,...   Comma-separated columns for the table strategy
```

| Strategy | Produces |
|---|---|
| `summarize` | Integrated narrative across papers |
| `table` | **Returns prose, not a table** — see below |
| `themes` | Recurring topics and groupings |
| `consensus` | Where papers agree and disagree — the right choice for contested findings |
| `bullet_points` | Condensed list |
| `extract` | Just the extracted values, minimal prose |

### `--strategy table` does not produce a table

Verified on both 0.7.14 and 0.7.15, with and without `--columns`: the output is multi-paragraph prose
either way. If you need a comparison table, take `paperclip results m_<id>` and build it yourself.

```bash
paperclip reduce --from m_def456 --strategy table \
  --columns "paper,vector,cell type,efficiency,n" \
  "Compare delivery approaches"

paperclip reduce --from m_def456 --strategy consensus \
  "Do these studies agree on whether LNP delivery reaches hematopoietic stem cells in vivo?"
```

`reduce` synthesizes what `map` returned; it does not re-read the papers. If a field is missing from
the reduce output, it was missing from the map — fix the map query and rerun.

### Reduce embeds citation markers with broken ids

Reduce prose carries inline pins like:

```text
... cholesterol, DMG-PEG2000, and DOPE or DSPC {{"document_id": "PMC12388", "line": 5}}
```

**Those document ids are truncated to eight characters and do not resolve.** The paper above is
`PMC12388858`; `PMC12388` returns `cat: PMC paper not found`. Same for `PMC93765` (really
`PMC9376583`) and `PMC11843` (really `PMC11843327`). A citation URL built from a reduce marker is a
dead link.

Use the marker only as a hint about *where* to look. Take real ids from `search`, `results`, or
`meta.json`, then open the cited line and confirm it before citing:

```bash
paperclip results m_4b4632df                                  # real ids
paperclip head -50 /papers/PMC12388858/content.lines
```

**Reduce output is not citable on its own.** Before quoting a number in your answer, open the paper it
came from and read the line, then cite that line. Map and reduce are LLM summarizers, and the citation
contract requires text you have actually seen.

## `results`

```bash
paperclip results --list                      # recent ids with the command that made each one
paperclip results s_4a2b61f6                  # view a saved result set
paperclip results s_4a2b61f6 --save out.csv   # export to CSV
paperclip results m_def456 --save map.txt     # export to TXT
```

`--list` output looks like:

```text
Recent results (20):

  s_3b1a8db3  search -s papers 'somatic hypermutation' -n 2   2026-07-28 01:00
  s_a5590fe3  grep -l SLC30A8 /papers/                        2026-07-28 00:58
```

Useful when you lost an id, or want to compare a fresh search against an earlier one.

## `ask-image`

```text
ask-image PATH "question"
ask-image --list                 # figures in the current directory (requires cd into a paper)

  --fn describe       Describe the figure
  --fn extract-data   Extract data from the figure
```

**Always `ls` first.** Figure filenames come from the publisher, not a `fig1.jpg` convention, and a
guessed name fails with `Error: Image not found`.

```bash
paperclip ls /papers/PMC10945750/figures/
# pnas.2307796121fig01.gif  pnas.2307796121fig01.jpg

paperclip ask-image /papers/PMC10945750/figures/pnas.2307796121fig01.jpg \
  "What is on each axis, which conditions are compared, and what is the reported effect size?"
paperclip ask-image /papers/PMC10945750/figures/pnas.2307796121fig01.jpg --fn extract-data
```

`--list` is documented as an alternative, but it requires a `cd` into the paper directory and `cd`
does not persist between invocations — use `ls` instead.

Vision extraction from a plot is an estimate. If a number matters, find it in the text or the
supplements and cite that instead:

```bash
paperclip ls /papers/PMC10945750/supplements/
paperclip head -40 /papers/PMC10945750/supplements/<file>
```

## Cost and failure notes

- One LLM call per paper for `quick-reader`; `exhaustive-extraction` is multi-turn and much heavier.
- `filter` before `map` when your search returned more than ~10 results — it is cheaper to discard
  irrelevant papers first.
- `map` on a `grep` result id works: grep returns `s_*` ids like search does.
- If papers fail mid-run, `--resume --retry-failed` rather than starting over.
- An empty per-paper answer usually means the query named a field the paper does not report, not that
  the reader failed. Ask for an explicit "not reported" to tell the two apart.
