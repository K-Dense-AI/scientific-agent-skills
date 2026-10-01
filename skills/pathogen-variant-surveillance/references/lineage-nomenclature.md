# Lineage nomenclature

Reviewed 2026-10-01 using current Pango files, official naming/tool documentation, and the live
LAPIS schemas. Labels below illustrate naming structure, never current prevalence or dominance.

## Pango designation versus database assignment

The [Pango designation repository](https://github.com/cov-lineages/pango-designation) is the
source for SARS-CoV-2 designations. Its current `lineage_notes.txt` contains descriptions and
withdrawn/redesignated names marked with `*`; `pango_designation/alias_key.json` resolves aliases.
Do not bake the number of designations or withdrawals into an answer: it changes continuously.

Ordinary alias entries are strings. Repeated expansion follows the alias chain until it reaches
A/B or a recombinant root. Recombinant entries are lists of parental lineage descriptions, not
one dotted ancestral path. Expand an ordinary alias before looking for recombinant ancestry.
A recombinant's descendants still have ordinary parent/child relationships within that lineage.
The live files, not reasoning from the spelling, determine these relationships.

The scripts fetch current files independently and record content SHA-256. Their HTTP ETags are
not Git blob/commit IDs. For archival work, retain both files from one explicit repository
commit; distinguish that historical naming snapshot from a fresh check of designation status.
A source failure must not turn a cached assignment into a claim of current designation.

LAPIS `pangoLineage` and `nextcladePangoLineage` share naming vocabulary but can disagree because
assignment pipelines and datasets differ. A withdrawn name can remain assigned to records.
Indexed membership establishes that a database can query a name, not that Pango still designates
it. `resolve_lineage.py` uses Pango notes as the authority for Pango status, and returns failure
for unverified names. Counts on indexed fields include descendants; the provenance says so.

## Nextstrain, Nextclade and WHO

| Field/system | Meaning |
| --- | --- |
| `pangoLineage` | fine-grained Pango assignment supplied by the dataset |
| `nextcladePangoLineage` | assignment from Nextclade's versioned reference dataset |
| `nextstrainClade` | a broader Nextstrain naming system, with deployment-specific labels |
| `whoClade` | historical WHO-label metadata, often absent; not an authoritative current tracking table |

Do not claim all recombinants always collapse into one Nextstrain label. Inspect actual values,
the current reference dataset, and the question's required resolution. Likewise a null `whoClade`
is not evidence that WHO's tracking system is retired. Consult the current
[WHO tracking page](https://www.who.int/activities/tracking-SARS-CoV-2-variants) for official
labels/classifications; do not invent Greek labels or infer a risk classification from a name.

The instance may expose `nextcladeDatasetVersion`, which should accompany assignment comparisons.
For separately authorized Nextclade analysis, the official CLI uses `nextclade dataset list`,
`nextclade dataset get` and `nextclade run --input-dataset`. Record tool version, dataset name,
tag/version and reference. Refresh for a current naming task; pin for reproducible reruns. Do
not treat a dataset-server root as an inference endpoint or silently replace a study's dataset.
These commands are documentation-reviewed here, not locally executed.
[Official Nextclade usage](https://docs.nextstrain.org/projects/nextclade/en/stable/user/nextclade-cli/usage.html).

## Influenza

| Instance | Reviewed fields | Interpretation |
| --- | --- | --- |
| `h3n2`, `h1n1pdm` | `cladeHA`, `cladeNA` | separate segment-derived clade calls |
| `h5n1` | `clade` | HA clade; no whole-genome genotype field in the reviewed schema |
| `influenza-a` | `subtypeHA`, `subtypeNA` | HA and NA subtype, not whole-genome genotype |

HA and NA labels describe different segments; their differing values alone do not diagnose
reassortment. These analyses need their own phylogenetic context. `unassigned` is a genuine
category. Missing calls are different from it; retain both in denominator accounting.

H5N1 HA clade labels and whole-genome genotypes are different entities. A query for a clade
cannot produce a genotype count, and neither geography nor host can substitute for genotype
assignment. [USDA GenoFLU](https://github.com/USDA-VS/GenoFLU) describes a specialist genotype
workflow for North American H5N1 clade 2.3.4.4b sequences. Its scope and database do not generalize
to every influenza genome. Genotyping is outside these scripts and was not executed in this audit.

## Other reviewed instances

| Instance | Lineage-like fields | Descendant support |
| --- | --- | --- |
| `mpox` | `clade`, `outbreakLineage`, `lineage` | `outbreakLineage` indexed |
| `rsv-a`, `rsv-b` | `lineage`, `subtype` | `lineage` indexed |
| `dengue` | `lineage`, `serotype` | `lineage` indexed |
| `measles` | `genotype` | unindexed |
| `west-nile` | `lineage` | unindexed |
| `cchf` | `lineage_S` | indexed in the 2026-10-01 schema; segment-specific |
| `hmpv` | `lineage` | indexed |
| `ebola-zaire`, `ebola-sudan` | none | counts/date analysis possible; no automatic lineage choice |

Keep original case for non-Pango labels, particularly `Ia`/`Ib` or composite outbreak labels.
`resolve_lineage.py` prints alternate candidate fields. Its automatic choice is a convenience;
select the field that answers the question, and report whether descendants were included.
The [Pathoplexus API guide](https://pathoplexus.org/docs/how-to/search-download-seqs-api) and each
instance's `/sample/databaseConfig` provide deployment-specific field names. A naming field
being indexed does not make it a validated phenotype or transmission history.
