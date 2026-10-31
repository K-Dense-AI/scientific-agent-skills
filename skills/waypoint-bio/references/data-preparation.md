# Preparing data for Waypoint

## Waypoint format

Rows are samples. Two aligned list-columns, plus whatever labels you need.

| Column | Type | Required |
| --- | --- | --- |
| `Taxa` | `list[str]` — full lineage strings | yes |
| `Relative Abundances` | `list[float]` — same length and order as `Taxa` | yes |
| `Split` | `str` — `train` / `validation` / `test` | only when using `split_column` |
| *(any)* | scalar targets and covariates | as needed |

The parquet DataFrame index holds the sample ID and is preserved through `embed`.
The upstream CSV/TSV reader does not restore that index.

Use `.parquet`. Upstream CSV/TSV list parsing checks `dtype == object`, so pandas 3
string columns remain strings and produce degenerate or omitted samples. The bundled coverage
reader parses them correctly; convert to parquet before passing data to the upstream CLI.

```python
import pandas as pd

df = pd.DataFrame(
    {
        "Taxa": [["k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; f__Lactobacillaceae; g__Lactobacillus",
                  "k__Bacteria; p__Bacteroidota; c__Bacteroidia; o__Bacteroidales; f__Bacteroidaceae; g__Bacteroides"]],
        "Relative Abundances": [[0.41, 0.59]],
        "Group": ["Case"],
    },
    index=pd.Index(["sample_001"], name="sample_id"),
)
df.to_parquet("dataset.parquet")
```

## How taxonomy strings are read

`TaxonomicTokenizer` splits each lineage on `;`, strips whitespace, and inspects each segment's
three-character prefix:

| Prefix | Rank |
| --- | --- |
| `s__` | species |
| `g__` | genus |
| `f__` | family |
| `o__` | order |
| `c__` | class |
| `p__` | phylum |
| `k__` | kingdom |

With `taxon_rank: genus` and `fallback_to_higher_rank: true` (the published defaults), each lineage
becomes one token:

1. If a `g__` segment exists, that segment *including the prefix* is the token — `g__Lactobacillus`.
2. Otherwise the **most specific higher rank** present is used — a lineage stopping at
   `f__Lactobacillaceae` tokenises to `f__Lactobacillaceae`.
3. If nothing matches, the token is `<unk>`.

Consequences that bite:

- **Any prefix outside that table is invisible.** QIIME 2 / SILVA / Greengenes2 write the domain as
  `d__Bacteria`; `d__` is not in the table, so such a segment is skipped entirely. A lineage
  truncated at domain becomes `<unk>`. Rewrite `d__` to `k__`.
- **A `s__` species segment does not help by itself.** Species is *more* specific than genus, so
  fallback (which only goes up) cannot use it. A lineage with `s__` but no `g__` tokenises to
  whatever higher rank is present — or `<unk>` if none is. Keep the full lineage, not just the tip.
- **Separator is `;`, not `|`.** A `|`-joined MetaPhlAn lineage is one unsplittable segment. Its
  first three characters are `k__`, so it matches at kingdom rank and the *entire pipe-joined
  string* is returned as a single token — which is not in the vocabulary, so it becomes `<unk>`.
  Verified natively against `TaxonomicTokenizer` 1.0.2 with Transformers 4.57.6:
  `k__Bacteria|p__Firmicutes|g__Lactobacillus` extracts to itself, while the `;`-separated form
  extracts to `g__Lactobacillus`.
- **Bare names never tokenise.** `Lactobacillus` has no prefix. Use `prepare-dataset
  --taxonomy_format genus` to prefix them, accepting the loss of fallback.

## Token ordering and truncation

Samples are encoded as `[BOS] + ordered_token_ids + [EOS]`, padded to `max_length` (512).

Ordering is by **descending abundance z-score** — `(ra - mean) / std` per token, using
`token_std_means.parquet` from the checkpoint. This puts taxa that are unusually abundant *for that
taxon* first, rather than merely abundant. Without that file, ordering falls back to raw descending
abundance.

Truncation keeps at most `max_length - 2` in-vocabulary entries. Discarded entries have lower
ordering scores; this is not evidence they are biologically uninformative. Upstream does not
aggregate repeated genus tokens from different species/lineages. Count encoded entries (including
duplicates) when reporting truncation, and keep rank/aggregation conventions fixed.

`compute_token_std_means` computes moments over observed entries, not across all samples with
absent taxa filled as zeros. Duplicate mapped tokens each contribute an observation. For a new
model, estimate preprocessing statistics on training data only; the upstream `pretrain` command
computes vocabulary/statistics before its random validation split, so that validation loss is not
an independent assessment of preprocessing generalization.

## Out-of-vocabulary taxa

The vocabulary is frozen at pretraining time from the Atlas corpus. During `waypoint embed`, tokens
resolving to `<unk>` are dropped before ordering; during fine-tuning and benchmarking,
`filter_unk_taxa: true` does the same. Neither warns you.

Every Compass dataset carries out-of-vocabulary taxa, and the paper names this the models' key
limitation. Measure it before drawing conclusions:

```bash
python scripts/vocab_coverage.py --model outpost-bio/Waypoint-6m --data dataset.parquet
```

If coverage is poor, the usual causes are, in order: a different taxonomy database (SILVA vs. NCBI
vs. GTDB naming), the `d__` prefix problem, `|` separators, and genuinely novel environments.

## Converting profiler output

`waypoint prepare-dataset` reads a plain abundance matrix whose labels are already `;`-separated
lineages. `scripts/profiler_to_waypoint.py` handles the formats it cannot.

### MetaPhlAn

Merged tables from `merge_metaphlan_tables.py`: rows are clades with `|`-separated lineages, columns
are samples, values are **percentages**, and the table is cumulative — every rank appears as its own
row.

```bash
python scripts/profiler_to_waypoint.py \
    --input merged_abundance_table.txt --format metaphlan \
    --rank species --output dataset.parquet
```

The converter drops `#` comment lines and the `NCBI_tax_id` / `clade_taxid` column, keeps only rows
whose deepest rank equals `--rank` (default `species`, which avoids double-counting parents),
rewrites `|` to `; `, and renormalises each sample to sum to 1. Strain/SGB rows ending below species (`t__`) are excluded before normalization, preventing
double-counting their species parents. A profile containing only SGB rows is unsupported by this
rank-selection mode; aggregate with the profiler's documented taxonomy mapping first.

### Kraken2 / Bracken

Kraken2 reports are per-sample and encode the hierarchy as two-space indentation, with no lineage
string. Pass one report per sample:

```bash
python scripts/profiler_to_waypoint.py \
    --input reports/*.kreport --format kraken \
    --rank species --output dataset.parquet
```

The converter walks the indentation to rebuild each lineage, maps Kraken rank codes to prefixes
(`D`/`K` → `k__`, `P` → `p__`, `C` → `c__`, `O` → `o__`, `F` → `f__`, `G` → `g__`, `S` → `s__`),
skips sub-ranks (`D1`, `S1`, …) and unclassified rows, takes clade-level read counts at the target
rank, and normalises. Sample IDs come from the filenames. Both the 6-column and the 8-column
(`--report-minimizer-data`) layouts are handled.

Bracken's own `.bracken` output carries no lineage at all — use the Kraken-style report Bracken
writes with `-w` (`-o` selects the tabular abundance file). Verify that the report was actually
produced: the reviewed current Bracken shell script's explicit `-w` branch prints the underlying
Python command instead of executing it. If affected, run its documented `est_abundance.py`
interface with `--out-report`, then use the report at the same estimated rank.

### QIIME 2 / biom TSV

The converter reads TSV, not `.qza` or binary BIOM. Export the feature table, convert BIOM to TSV,
and join taxonomy by feature ID first; a normal QIIME feature-table export contains feature IDs,
not lineages. If taxonomy is already present as BIOM observation metadata, `biom convert` with
`--to-tsv --header-key taxonomy` includes it. Pass that column explicitly (or supply `#OTU ID`
rows already labelled by lineage):

```bash
python scripts/profiler_to_waypoint.py \
    --input feature-table.tsv --format qiime2 \
    --taxonomy-column taxonomy --output dataset.parquet
```

The converter strips the `# Constructed from biom file` banner, uses the taxonomy column as the
lineage, rewrites `d__` to `k__`, and normalises counts to relative abundances. Features whose
taxonomy is `Unassigned` are dropped.

### MGnify

For MGnify-style taxonomy matrices with a `taxonomy` first column, `;`-separated lineages and
only numeric sample columns, use `waypoint prepare-dataset --orientation taxa_as_rows`. This
describes the bundled example layout, not every MGnify export or pipeline. Inspect the actual
header, taxonomy database and rank; adapt any extra metadata columns before conversion.

### Anything else

If you already have a sample × taxa table with lineage labels, use `--format generic`, which applies
only the separator and prefix normalisation:

```bash
python scripts/profiler_to_waypoint.py \
    --input my_table.tsv --format generic --orientation taxa_as_rows \
    --output dataset.parquet
```

## Attaching labels

Either merge them at conversion time —

```bash
waypoint prepare-dataset --input matrix.tsv --metadata labels.csv --output dataset.parquet
python scripts/profiler_to_waypoint.py --input ... --metadata labels.csv --output dataset.parquet
```

— where `labels.csv` is indexed by sample ID, or join afterwards in pandas. Sample IDs must match
exactly. These are left joins: unmatched samples remain with missing labels. The bundled helper
warns about unmatched IDs and rejects duplicate IDs; upstream may omit missing targets in
`finetune`. Check sample counts and missingness explicitly before splitting. Parquet metadata
must preserve a sample-ID index. The bundled converter rejects non-finite/negative abundances
and malformed numeric cells; zeros/missing numeric cells are treated as absent taxa.

`--min-abundance` filters after normalization without renormalizing the retained values. Record
the retained mass; do not describe the filtered lists as summing to one unless you explicitly
renormalize and record that additional transformation.

## Splits

`waypoint finetune` defaults to a random 80/10/10 split. Add a `Split` column and set
`split_column: Split` in the config whenever samples are not independent:

- longitudinal cohorts (the Roswall infant data is exactly this shape),
- technical or biological replicates,
- multiple communities derived from one donor,
- multiple drugs applied to the same starting community.

Grouping by subject or study when you build `Split` is the difference between a generalisation
estimate and a memorisation estimate.

## Format sources reviewed 2026-10-01

- [MetaPhlAn 4 formats](https://github.com/biobakery/MetaPhlAn/wiki/MetaPhlAn-4).
- [Kraken 2 report columns and rank codes](https://github.com/DerrickWood/kraken2/wiki/Manual).
- [Bracken command implementation](https://github.com/jenniferlu717/Bracken/blob/master/bracken).
- [BIOM conversion and taxonomy metadata](https://biom-format.org/documentation/biom_conversion.html).
