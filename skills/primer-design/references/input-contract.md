# Files, coordinates, settings, and result contracts

Use local UTF-8 files. All scripts accept `--help` without contacting a service.
Generated JSON is evidence, not a command file. Keep results outside the skill.

## Template and screening FASTA

- The first whitespace-delimited token after `>` is the record ID. IDs must be unique.
- Sequence is case-normalized. Internal whitespace, digits, gaps, RNA U, and non-IUPAC
  symbols are rejected. Empty records and sequence before a header are rejected.
- Design uses one selected record; `--record` is required with multiple records.
- Design replaces ambiguity with N and excludes it from primers. Screen reference
  ambiguity uses possible-base sets and reports unresolved matching sites.
- Preserve full reference ID/version/source in a separate manifest. A user-written
  FASTA label is not verified evidence of an accession or assembly.
- Local files are hashed. Checksums identify the bytes used; they do not independently
  establish database currency, biological correctness, or adequate coverage.

The example FASTA in `../assets/demo-template.fasta` contains 500 deterministic
synthetic bases generated with Python `random.Random(717)`, choosing A/C/G/T uniformly.
It is reproducible demonstration input with no claimed biological function.

## Primer pair TSV

Required columns: `pair_id`, `forward`, `reverse`.
Optional columns: `forward_tail`, `reverse_tail` (empty means no tail).
Columns are tab-separated; unknown/duplicate columns and malformed rows are errors.

```text
pair_id	forward	reverse	forward_tail	reverse_tail
assay_1	ACGTCAGTACGATCGTACGA	TCGATGCACTGATCGTACGT	GGATCC	GAATTC
```

These illustrative oligos explain the schema; they are not recommended experimental
primers. Pair IDs use letters, digits, underscores, periods, and hyphens and must be
unique. Cores and tails are unambiguous ACGT DNA, written in ordering orientation
5′→3′. Modified bases and degenerate symbols are rejected, not stripped.

The full ordering sequence is `tail + core`. A reverse primer is already reverse-
complemented relative to its target; do not reverse-complement it again for ordering.
For an exact-match product oriented from the forward primer toward the reverse:

```text
final top strand = forward_tail + template_product + reverse_complement(reverse_tail)
```

For mismatched primers, late-cycle products incorporate primer bases; a reference
product hash does not identify that final synthesized molecule. The screen explicitly
names its hash `reference_product_sha256` and does not reconstruct such products.

## Design configuration JSON

Top-level keys are only `sequence_args` and `global_args`, both objects. Template,
record ID, paired-primer task, 0-based indexing, and unambiguous output are controlled
by the adapter. It rejects unsupported tags, including tags for another Primer3 task.

Example (JSON, not skill frontmatter):

```json
{
  "sequence_args": {
    "SEQUENCE_TARGET": [[235, 30]],
    "SEQUENCE_EXCLUDED_REGION": [[80, 5]]
  },
  "global_args": {
    "PRIMER_PRODUCT_SIZE_RANGE": [[90, 180]],
    "PRIMER_NUM_RETURN": 3,
    "PRIMER_SALT_MONOVALENT": 50.0,
    "PRIMER_SALT_DIVALENT": 1.5,
    "PRIMER_DNTP_CONC": 0.6,
    "PRIMER_DNA_CONC": 50.0
  }
}
```

### Sequence constraints supported by the adapter

| Tag | Value and meaning |
| --- | --- |
| `SEQUENCE_TARGET` | List of alternative `[start,length]` regions; a pair must flank at least one, not necessarily all |
| `SEQUENCE_INCLUDED_REGION` | One `[start,length]` design region within the selected template |
| `SEQUENCE_EXCLUDED_REGION` | List of `[start,length]` regions where primer binding is disallowed |
| `SEQUENCE_PRIMER_PAIR_OK_REGION_LIST` | List of `[left_start,left_length,right_start,right_length]`; `[-1,-1]` makes that side unconstrained |
| `SEQUENCE_OVERLAP_JUNCTION_LIST` | Indices of bases immediately left of internal junctions; verify returned overlap against transcript annotation |
| `SEQUENCE_PRIMER` | Fixed forward core in ordering orientation |
| `SEQUENCE_PRIMER_REVCOMP` | Fixed reverse core in ordering orientation |
| `SEQUENCE_QUALITY` | One nonnegative integer score per template base; pair with explicit quality thresholds or weights |

`SEQUENCE_OVERLAP_JUNCTION_LIST` uses the index of the base immediately **before**
the junction with this adapter's `PRIMER_FIRST_BASE_INDEX=0`. A junction between
bases at indices 99 and 100 is supplied as **99**. Use the minimum 5′/3′ overlap controls and verify the returned
binding interval, not just the command's exit status.

### Global controls supported by the adapter

- Candidate count (`PRIMER_NUM_RETURN`, 1–100).
- Primer size: `PRIMER_MIN_SIZE`, `PRIMER_OPT_SIZE`, `PRIMER_MAX_SIZE`; adapter range
  15–36 nt, ordered minimum ≤ optimum ≤ maximum.
- Tm: `PRIMER_MIN_TM`, `PRIMER_OPT_TM`, `PRIMER_MAX_TM`, `PRIMER_PAIR_MAX_DIFF_TM`.
- GC: `PRIMER_MIN_GC`, `PRIMER_OPT_GC_PERCENT`, `PRIMER_MAX_GC`, `PRIMER_GC_CLAMP`,
  `PRIMER_MAX_END_GC`; `PRIMER_MAX_POLY_X`, `PRIMER_MAX_END_STABILITY`.
- Thermodynamic structure limits: `PRIMER_MAX_SELF_ANY_TH`, `PRIMER_MAX_SELF_END_TH`,
  `PRIMER_MAX_HAIRPIN_TH`, `PRIMER_PAIR_MAX_COMPL_ANY_TH`, `PRIMER_PAIR_MAX_COMPL_END_TH`.
- Chemistry: `PRIMER_SALT_MONOVALENT`, `PRIMER_SALT_DIVALENT`, `PRIMER_DNTP_CONC`,
  `PRIMER_DNA_CONC`. Salt/dNTP units are mM; DNA concentration is nM.
- Core Tm model: `PRIMER_TM_FORMULA` is 0 Breslauer or 1 SantaLucia; salt correction
  `PRIMER_SALT_CORRECTIONS` is 0 Schildkraut, 1 SantaLucia, or 2 Owczarzy. Match these
  to `check_thermodynamics.py --tm-method` and `--salt-corrections-method` respectively.
  Defaults are SantaLucia for both. Structure calculations use libprimer3 defaults.
- `PRIMER_PRODUCT_SIZE_RANGE`: nonempty list of `[minimum,maximum]` inclusive ranges.
  Multiple ranges retain Primer3's preference ordering; no global optimum is implied.
- Junction overlap: `PRIMER_MIN_5_PRIME_OVERLAP_OF_JUNCTION` and
  `PRIMER_MIN_3_PRIME_OVERLAP_OF_JUNCTION`.
- Optional ranking weights: `PRIMER_WT_TM_GT`, `PRIMER_WT_TM_LT`, `PRIMER_WT_SIZE_GT`,
  `PRIMER_WT_SIZE_LT`, `PRIMER_PAIR_WT_DIFF_TM`, `PRIMER_PAIR_WT_PR_PENALTY`.
- Quality controls: `PRIMER_MIN_QUALITY`, `PRIMER_MIN_END_QUALITY`,
  `PRIMER_QUALITY_RANGE_MIN`, `PRIMER_QUALITY_RANGE_MAX`, `PRIMER_WT_SEQ_QUAL`,
  `PRIMER_WT_END_QUAL`; supply `SEQUENCE_QUALITY` and meaningful assay-specific values.
- `PRIMER_MAX_NS_ACCEPTED` must remain zero.

To cover multiple intervals with one product, provide their enclosing interval as
one `SEQUENCE_TARGET`, then verify both binding sites lie outside that interval.
Several separate targets do not request one primer pair per target.

All numeric inputs must be finite. For an unimplemented native tag or another task,
use the official Primer3 interface explicitly and retain the same coordinate,
provenance, and validation discipline. Do not disguise it as tested adapter behavior.

## BED masking

`--mask-bed` reads tab-separated `record_id start end` (extra BED columns are allowed).
Intervals are 0-based, half-open. Every record must occur in the input template FASTA;
every interval must fit its record. Exclusions for the selected record are combined
with configuration exclusions. A BED interval `[start,end)` becomes Primer3's
`[start,end-start]`.

For example, VCF POS 101 on a whole-chromosome template describes a single base at
BED `[100,101)`, **after confirming assembly, contig, and REF**. For an extracted
locus, subtract its genomic offset and transform strand where needed. Indels and
multiallelic loci need deliberate affected-interval definitions, not a universal
POS-only conversion. See [design-workflows.md](design-workflows.md).

## Expected product TSV

Exactly four columns: `pair_id`, `record_id`, `start`, `end`. Multiple rows may specify
multiple acceptable products for one pair. Match actual reference IDs; no record-name
allowlist or fuzzy coordinate matching is performed.

- Linear interval: `0 <= start < end <= record_length`.
- Circular interval: `0 <= start < record_length`, `start < end <= start+record_length`.
  Example: on a 500-base circular record, `[450,550)` describes a 100-base product.
- An expected product matches its exact outer interval and mixed primer roles (F/R
  or R/F). Same-primer products are flagged separately even at the same coordinates.
- Empty/missing expected targets produce an inventory, not a specificity clearance.
- Design export coordinates belong to the design FASTA. Translate them explicitly
  when switching reference; genomic and transcript coordinates are not interchangeable.

## Reports, flags, and exit codes

`design_primers.py` emits pairs, product/core/order sequences, binding/product
intervals, lengths, core Tm, penalties, engine explanations, effective input settings,
and SHA-256/version provenance. Empty results return `no_candidates`, not fake primers.

`check_thermodynamics.py` emits per-oligo core/full structures and per-interaction
directional results. `--multiplex` enumerates all unordered oligo pairs, not just
F/R. A requested panel exceeding `--max-interactions` errors before partial output.
Long full oligos return `unsupported_length`; no full-oligo assessment is implied.
Core Tm at/below absolute zero or nonfinite Tm is an error, even if Primer3 returned
a numeric value. Check chemistry units and model suitability before rerunning.

`screen_specificity.py` emits hits and products for each pair, expected/missing
products, status, limitations, settings, reference/pair/expected hashes, and executable
provenance. Binding hit indices are relative to the primer in 5′→3′ orientation;
explicit `*_from_three_prime_1based` fields count back from its 3′ end. Ambiguous bases
carry mismatch lower/upper bounds. A possible base match is not a confirmed match.

All product lengths include binding cores. `length_with_tails` adds the applicable
tails for that product's two primer roles. Product-size search bounds refer to the
reference product before tails. Only nonoverlapping inward-facing sites are modeled.

BLAST is never exhaustive. `complete_within_model=false` and `exhaustive=false`
remain false even when `discovery_completed=true`. Inspect `issues` and per-pair
statuses as well as top-level status. Aggregate status selects the most limiting
state and does not erase other pairs' findings.

For specificity `--multiplex`, the report includes original pairs and generated
cross-pair combinations, with `cross_pair` flags and source oligo identities. The
engine searches unique annealing cores once. With N input pairs, there are
`2*N*(N-1)` cross-pair oligo combinations, checked against `--max-panel-combinations`
before expansion. Same-primer products remain in the original pair inventory.
Every generated cross product is unintended in this mode; no-product cross
combinations receive the scoped no-off-target status. Expected TSV rows may name
only original pairs. Intentional shared-primer panels require explicit standalone
pair definitions and a reviewed set of acceptable products.

| Tool | Exit 0 | Exit 1 | Exit 2 |
| --- | --- | --- | --- |
| Design | Candidates produced | No candidates | Invalid input/engine failure |
| Thermodynamics | Supported calculations completed | Long full oligos remain unassessed | Invalid input/engine failure/cap |
| Specificity | Computation completed; read biological status | Not used | Incomplete search, uncertain matching sites, invalid input, or engine failure |

An observed off-target can accompany a successful exit 0. Missing intended products
also require action even when computation succeeds. Specificity failures write an
`incomplete` report where possible. Invalid design/thermodynamic inputs return an
error without creating a new report; do not reuse a stale output from an earlier run.
Output paths cannot overwrite input files; use distinct filenames for each analysis.
