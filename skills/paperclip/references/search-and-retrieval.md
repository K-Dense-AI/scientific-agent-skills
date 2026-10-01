# Search, retrieval, and query craft

Reviewed on 2026-09-30 against the 0.7.92 CLI/SDK, the
[core reference](https://paperclip.gxl.ai/skills/full_skill.md),
[protein reference](https://paperclip.gxl.ai/skills/skills/proteins.md), and
[web docs](https://paperclip.gxl.ai/docs). Retrieval examples are illustrative: no paid or
authenticated searches were executed for this review. Load credentials as described in
[installation.md](installation.md).

## Choose a source explicitly

| Source | Scope |
|---|---|
| `pmc` | PMC full-text papers |
| `arxiv`, `biorxiv`, `medrxiv` | Corresponding preprint corpora |
| `papers` | The four paper corpora combined |
| `abstracts` | Title/abstract-grain retrieval across scholarly corpora; not a full-text promise |
| `fda` | Regulatory search; use a regional source/path to disambiguate |
| `fda/jp`, `fda/eu`, `/fda/us` | PMDA, EMA/EPAR, and US FDA |
| `trials` | Trial registries; `trials/us`, `trials/eu`, `trials/jp`, `trials/cn` narrow geography |
| `proteins` | Unified UniProt/PDB/ChEMBL records; `uniprot`, `pdb`, `chembl` are aliases in the client |
| `clipboard` | The user's documents; `clipboard/FOLDER` scopes to a folder |
| `geo` | GEO Series (documented CLI source; not listed in the current v1 JSON search enum) |
| `patents` | Patent records; load `paperclip skill patents` first |

The `abstracts` CLI source and the public `/api/v1/search` default have different published coverage
wording. Choose a source explicitly and report the selected interface; do not label all abstract
results as OpenAlex or assume coverage equals PMC. Counts in upstream documents disagree and change,
so use a dated catalogue or query result when a corpus count matters.

```bash
paperclip search -s pmc,biorxiv "protein design" -n 5
paperclip search "pembrolizumab" /fda/us -n 5
paperclip search "breast cancer" /trials/us -n 5
```

Match the task to paper evidence, trial registration, regulatory material, or structured protein
records. Infer that choice from a clear user request; clarify only when the intended output remains
ambiguous. Regional paths `/trials/...` and `/clinicaltrials/...` are aliases in current docs.

## Search options

| Option | Contract |
|---|---|
| `-n/--limit N` | Requested hit count, not a corpus census or a pagination cursor |
| `-e/--exact` | Exact-phrase search |
| `--year YYYY` | Publication-year filter; validate returned metadata |
| `--since WINDOW` | Recency strings such as `30d`, `6m`, `1y`; support depends on source |
| `--sort relevance\|date` | Ordering |
| `--author`, `--journal` | Metadata narrowing; source coverage varies |
| `--ranking hybrid\|bm25\|vector\|analogical` | Retrieval mode |
| `--min-embedding-similarity FLOAT` | Floor on the vector leg |
| `--min-bm25-score FLOAT` | Floor on the lexical leg |
| `--corpus` | Full-corpus discovery even when scoped to a repo |

The SDK and vendor core reference disagree on arXiv `--since` support; use `--year` for arXiv,
medRxiv, and abstracts unless current server help confirms the needed recency behavior. Do not
assume an arbitrary date string or a filter unsupported by a source is applied.

The relevance floors **do have CLI equivalents**. For hybrid mode, each applies only to its own
retrieval leg: use both to bound both legs, or pair one with its matching ranking. Floors do not
expand the requested candidate set. They are unsupported with regex/analogical modes; a vector
floor is incompatible with date sorting. These restrictions are documented in the 0.7.92 SDK.

```bash
paperclip search -s pmc --ranking hybrid \
  --min-embedding-similarity 0.7 --min-bm25-score 5 \
  "protein design" -n 5
```

`hybrid` is a good discovery default; `bm25` fits exact terminology and gene symbols, `vector` fits
varying vocabulary, and `analogical` fits cross-domain method transfer. Write one or two sentences
about the method/problem for analogical search, or use an identified reference paper's abstract:

```bash
paperclip search -s arxiv --ranking analogical \
  "I need to approximate an expensive leave-one-out computation cheaply by exploiting low-rank structure in my parameter space" -n 10
```

Upstream describes stable search prefixes through `-n 100` for unchanged query, filters, and index;
requests above 100 can expand the candidate pool and reorder earlier results. This is not pagination
or a cross-date reproducibility guarantee. Save exact queries, source filters, returned IDs, and date.

## Structured results and cohort preservation

Search previews and generated summaries are triage, not paper quotations. In 0.7.92 SDK,
`result.papers`, `result.count`, and `result.result_id` expose structured results and hydrate missing
hit data from saved results when possible. A failed hydration can leave incomplete data: check
requested versus returned count and reported truncation. See [python-sdk.md](python-sdk.md).

```bash
paperclip results --list
paperclip results s_ID --save search.csv
paperclip results s_ID --export-bundle cohort/
paperclip results s_ID --sample 20 --seed 42
```

CSV exports and bundle formats depend on result kind; do not assume every map export has the search
metadata header. Cohort paging retrieves the **saved cohort**, not additional corpus search hits.
The CLI supports `--save-as NAME` aliases on result-producing commands; their scope is session-bound,
so record the durable result ID for another session.

```bash
paperclip filter --from s_ID --require 3 "in vivo delivery with quantitative outcomes"
```

`filter` is an LLM pass that overwrites the cohort in place. If too few survive, rerun a broader
search for a fresh ID; a second filter cannot recover discarded rows. For deterministic quality
filters, consult current `refine --help` and preserve both input and output cohort IDs.

## Exact metadata lookup

```bash
paperclip lookup doi 10.1073/pnas.2307796121
paperclip lookup pmc PMC7194329
paperclip lookup pmid 32943797
paperclip lookup arxiv 2403.03507
paperclip lookup author "James Zou" -n 10
```

Current docs list `doi`, `title`, `author`, `abstract`, `source`, `date`/`month_year`, `pmc`, `pmid`,
`journal`, `publisher`, `type`, `keywords`, `category`, `license`, `year`, `volume`, `issue`, `issn`;
the core reference also lists `arxiv`. Many metadata fields are PMC-specific. Do not turn an empty
field match into a claim that the paper does not exist. The public HTTP lookup's narrower typed
contract is documented separately in [python-sdk.md](python-sdk.md).

## Full-text grep and scan

```bash
paperclip grep -l "SLC30A8" /papers/
paperclip grep -n -C 3 "lipid nanoparticle" /papers/PMC10945750/content.lines
paperclip grep -i -e "off-target" -e "offtarget" /papers/PMC10945750/content.lines
paperclip grep --from s_ID "IC50"
paperclip scan -i -C 3 /papers/PMC10945750/content.lines "IC50" "EC50" "dose"
```

`-n` means line numbers; `-m N` bounds matches. Corpus scans are parallel and time-bounded, so a limit
or timeout can change returned membership/order. `--exhaustive` allows more scan time, not guaranteed
completeness. The current guide says corpus `grep -c` counts documents exactly only through 500 bitmap
candidates, then approximately; file `grep -c` counts matching lines. Do not report a corpus estimate
as an exact prevalence count.

Boolean search and grep use different semantics: `search --bool --ranking bm25` uses analyzed phrase
operands; `grep --bool` uses regex predicates over whole documents. Do not interchange them in a
review protocol without validating the intended matching behavior.

## Metadata SQL

```bash
paperclip sql "SELECT source, COUNT(*) AS n FROM documents GROUP BY source"
paperclip sql "SELECT pub_year AS year, COUNT(*) AS n FROM documents WHERE title ILIKE '%CRISPR%' GROUP BY pub_year ORDER BY year DESC LIMIT 10"
```

The current core reference documents `SELECT` on `documents`, 15-second server timeout and a
200-row cap. Its columns are `id`, `title`, `doi`, `authors`, `source`, `abstract_text`, `pub_date`,
`pub_year`, `journal_title`, `article_type`, `pmid`, `keywords`, and `categories`.
Source-specific missing fields may be NULL. Use explicit aliases and inspect actual returned columns.

This metadata SQL route does not search paper bodies. `abstract_text ILIKE '%X%'` misses a term
found only in Methods or supplementary material. The web docs expose lower-level `document_id`,
`content_blocks`, and `figures` in an **export** context; do not assume those names or joins are
interchangeable with ordinary `sql`. Current docs differ on some column naming, so check server help
before introducing a new query rather than claiming automatic normalization.

### Protein SQL

```bash
paperclip skill proteins
paperclip sql -s proteins "SELECT COUNT(*) FROM uniprot_v.proteins"
paperclip sql -s proteins "SELECT * FROM pdb_v.structures_by_accession WHERE accession='P00533' LIMIT 10"
paperclip cat /proteins/P04637/meta.json
```

The current domain reference exposes `uniprot_v.proteins`, `uniprot_v.features`,
`pdb_v.structures_by_accession`, `chembl_v.bioactivities_by_accession`, and
`chembl_v.drugs_by_accession`. Check that reference for exact column names, enum values, join
cardinality, and accession mapping before writing a biological query. An accession-based join is
not a guarantee of one row per protein or of directly comparable bioactivity assays.
