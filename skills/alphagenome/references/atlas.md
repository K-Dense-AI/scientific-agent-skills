# AlphaGenome Atlas: data model, scorers, AVI, and access

Verified against `alphagenome` 0.9.0 (released 2026-09-08, the first version
with `alphagenome.atlas`), the Atlas technical report (Cheng, Taylor,
Nicolaisen, Pan, Bycroft, Perino, Ward, *et al.*, "AlphaGenome Atlas: in silico
mutagenesis of the entire human genome improves prioritization and
interpretation of non-coding variants", 2026 preprint), and DeepMind's own
Atlas agent skills in `google-deepmind/science-skills`. Anything marked
*unverified* could not be checked without an API key.

## What is in the Atlas

| Item | Value |
| --- | --- |
| Genome build | GRCh38 / hg38 only. Gene annotations: GENCODE v46. |
| Variants | Every possible SNV at every non-`N` reference base (about 9 billion). Over 100 million observed indels (gnomAD v4.1, UK Biobank, All of Us) were scored for the paper, but the public API is currently limited to SNVs; indel expansion is promised "upon final publication". |
| Model | The distilled AlphaGenome model, 1 Mb input centred on a 128 bp scoring window (so a variant sits within 64 bp of the centre; the paper shows this does not change scores). |
| Per-variant content | Raw scores for every track of 19 recommended scorer configurations (about 27,000 scalars per variant, about 15,000 without the `_ACTIVE` scorers), the AVI score with its quantile, 18 SHAP feature attributions, and motif instances. |
| Motifs | 2,601 motifs (94 main TF labels, 122 zinc-finger labels, 464 composite patterns) and about 253 billion motif instances. Browsable on the portal; bulk download promised. |
| Size | About 1 PB. |

### Index key semantics

Each record is keyed by `chromosome:position:alt` on GRCh38. The REF allele is
implied by the reference and is **not** part of the key, so:

- a variant written with REF and ALT swapped (for example minor-allele-first
  from a GWAS table) is a **lookup miss**, not an error;
- non-reference to non-reference substitutions do not exist;
- positions where the reference is `N` were never scored;
- GRCh37 coordinates return wrong-but-plausible answers. Lift over first.

Check REF against the reference FASTA before trusting any Atlas result
(`genomic-coordinates` has `normalize_variant.py` and `check_contigs.py`).

## The scorers (Table S1 of the report)

`requested_scorers=` takes these names. Track counts are for human; the
`_ACTIVE` names are the natural spelling of the "(Active)" rows but were not
verified against a live `scorer_metadata()` call.

| Name | Scorer class | Parameters | Biosamples | Tracks | Signed | Obs axis |
| --- | --- | --- | --- | --- | --- | --- |
| `ATAC` | CenterMaskScorer | width 501, DIFF_LOG2_SUM | 167 | 167 | yes | variant |
| `DNASE` | CenterMaskScorer | width 501, DIFF_LOG2_SUM | 305 | 305 | yes | variant |
| `CHIP_TF` | CenterMaskScorer | width 501, DIFF_LOG2_SUM | 163 | 1,617 | yes | variant |
| `CHIP_HISTONE` | CenterMaskScorer | width 2001, DIFF_LOG2_SUM | 219 | 1,116 | yes | variant |
| `CAGE` | CenterMaskScorer | width 501, DIFF_LOG2_SUM | 264 | 546 | yes | variant |
| `PROCAP` | CenterMaskScorer | width 501, DIFF_LOG2_SUM | 6 | 12 | yes | variant |
| `RNA_SEQ` | GeneMaskLFCScorer | log fold change over exons | 285 | 371 | yes | variant x gene |
| `POLYADENYLATION` | PolyadenylationScorer | max log-fold change of isoform ratio | 285 | 371 | no | variant x gene |
| `SPLICE_SITES` | GeneMaskSplicingScorer | SPLICE_SITES, width None | - | 2 (donor, acceptor) | no | variant x gene |
| `SPLICE_SITE_USAGE` | GeneMaskSplicingScorer | SPLICE_SITE_USAGE, width None | 282 | 367 | no | variant x gene |
| `SPLICE_JUNCTIONS` | SpliceJunctionScorer | | 282 | 367 | no | variant x junction |
| `CONTACT_MAPS` | ContactMapScorer | | 12 | 28 | no | variant |
| `*_ACTIVE` (ATAC, DNASE, CHIP_TF, CHIP_HISTONE, CAGE, PROCAP, RNA_SEQ) | same widths, ACTIVE_SUM / GeneMaskActiveScorer | absolute activity of the stronger allele, not a difference | as above | as above | no | as above |
| `AVI_SCORE` | composite | one score per variant | - | 1 | no | variant |
| `AVI_SCORE_FEATURE_IMPORTANCE` | SHAP | 18 attribution values | - | 18 | yes | variant |

"Signed" scorers can go negative (ALT lowers the signal). For unsigned scorers
the direction is not meaningful; only magnitude ranks.

The whole catalogue is 9,440 tracks. `python scripts/atlas_query.py tracks
--scorer RNA_SEQ --query liver` shows the metadata for any of them.

## AlphaGenome Variant Impact (AVI)

AVI is a small neural network trained on **proxy labels**: gnomAD v4.1 variants
with a group-maximum filtering allele frequency above 0.001 are "proxy benign"
(about 2e7), below 0.001 "proxy impactful" (about 1e8). It therefore learns to
rank variants by how strongly negative selection appears to act on them, using
18 features:

| Group | Features (`var['name']` keys) |
| --- | --- |
| AlphaGenome, max absolute effect across all tracks and genes | `MAX_ABS_ATAC`, `MAX_ABS_DNASE`, `MAX_ABS_CHIP_TF`, `MAX_ABS_CHIP_HISTONE`, `MAX_ABS_CAGE`, `MAX_ABS_PROCAP`, `MAX_ABS_RNA_SEQ`, `MAX_ABS_POLYADENYLATION`, `MAX_ABS_CONTACT_MAPS` |
| AlphaGenome splicing (sites + usage + junctions/5, each max over genes) | `MERGED_SPLICING` |
| Protein | `ALPHAMISSENSE` (0 when there is no AlphaMissense prediction) |
| Conservation | `CACTUS_241_WAY` (Zoonomia phyloP, range -20 to 8.9), `PHASTCONS_470_WAY` |
| VEP loss-of-function indicators | `PROTEIN_TERMINATION` (stop gained or frameshift), `START_LOST`, `STOP_LOST` |
| Indel type | `IS_INSERTION`, `IS_DELETION` |

The 18 SHAP values (expected-gradients approximation, reference = all features
zero) **sum to the raw AVI score**, so the attribution tells you which modality
drives a high score: splicing, a TF-binding change, conservation alone, or a
coding consequence via AlphaMissense.

### Raw, quantile, Phred

The Atlas returns the raw score in `X` and a **cumulative quantile** against all
genome-wide SNVs in `layers['quantiles']`. Convert as DeepMind's tools do:

```text
tail  = 1 - cdf_quantile            # fraction of SNVs scoring at least this high
phred = -10 * log10(tail)           # 10 = top 10 %, 20 = top 1 %, 30 = top 0.1 %, 40 = top 0.01 %
top % = 10 ** (-phred / 10) * 100
```

Indel Phred scores are placed on the SNV quantile curve. The report's guidance:
AVI is applicable to coding and non-coding variants, but **use region- or
application-aware thresholds and prefer ranking over hard cut-offs**. Pathogenic
regulatory variants land in lower AVI bins than pathogenic protein-truncating or
splice-motif variants, so one genome-wide cut-off under-calls regulatory hits.

### Benchmarks and case studies (report, for context only)

State-of-the-art on ClinVar non-coding, saturation genome editing, and TraitGym
style benchmarks against CADD, GPN-Star, and AlphaMissense after removing
training-set overlap; resolution of an epileptic-encephalopathy case in the
GREGoR cohort via a *DNM1* variant missed by prior tools; a 22 % increase in
detectable rare non-coding associations for circulating proteins in UK Biobank.

## Client API (`alphagenome.atlas.atlas`)

```python
from alphagenome.atlas import atlas
from alphagenome.data import genome

client = atlas.create(api_key, timeout=30)          # gRPC to gdmscience.googleapis.com:443

client.scorer_metadata()   # -> {name: ScorerMetadata(name, is_signed, track_metadata: DataFrame)}

client.query_variant(
    genome.Variant.from_str("chr22:36201698:A>C"),  # 1-based position
    requested_scorers=["AVI_SCORE", "AVI_SCORE_FEATURE_IMPORTANCE", "RNA_SEQ"],
    ontology_terms=None,      # e.g. ["UBERON:0001157", "CL:0000084"]; strings or OntologyTerm
    gene_ids=None,            # Ensembl IDs, gene-centric scorers only
    gene_names=None,          # symbols, gene-centric scorers only
)                              # -> {scorer_name: AnnData}

client.query_variants([...], requested_scorers=[...], progress_bar=True, max_workers=10)
client.query_interval(genome.Interval("chr11", 5225726, 5226575), requested_scorers=[...])
```

- `genome.Interval` is **0-based half-open**; `genome.Variant.position` is
  **1-based**. `Variant.from_str` also accepts gnomAD (`22-1024-A-C`), GTEx
  (`chr22_1024_A_C_b38`), and Open Targets spellings via `VariantFormat`.
- `query_interval` splits the window into 32 bp chunks, walks the pagination,
  and returns every SNV in it (3 per base). A 1 kb window is 3,000 variants and
  takes a few seconds; DeepMind's tool refuses windows above 1,000 bp by
  default, and so does `scripts/atlas_query.py` (`--max-window`).
- `query_variants` re-raises the first failed lookup; `scripts/atlas_query.py`
  queries one variant at a time so a single miss becomes an `error` cell.
- Each AnnData: `X` = raw scores (obs x tracks, `float32`), `obs['variant']` =
  `genome.Variant`, plus `gene_id`, `gene_name`, `strand`, `junction_Start`,
  `junction_End` for gene-centric scorers; `var` = track metadata (`name`,
  `strand`, `ontology_curie`, `biosample_name`, `biosample_type`, assay title,
  `gtex_tissue`, `transcription_factor`, `histone_mark` where applicable);
  `layers['quantiles']` when the server sent calibrated quantiles.
- `AVI_SCORE`: `X` shape (n, 1). `AVI_SCORE_FEATURE_IMPORTANCE`: `X` shape
  (n, 18), `var['name']` = the feature keys above.
- An `ontology_terms` filter is ignored for scorers whose tracks have no
  ontology metadata (the filter string is built that way), so `SPLICE_SITES`
  and the AVI scorers still come back.

### Errors

`atlas.handle_rpc_error` maps gRPC status to Python exceptions:

| gRPC status | Python | Typical cause |
| --- | --- | --- |
| `INVALID_ARGUMENT`, `NOT_FOUND` | `ValueError` | bad key ("API key not valid"), unknown scorer name, variant not in the Atlas (indel, `N` base, wrong REF) |
| `UNAUTHENTICATED`, `PERMISSION_DENIED` | `PermissionError` | key without Atlas access, terms not accepted |
| `DEADLINE_EXCEEDED` | `TimeoutError` | 60 s per-call timeout |
| `OUT_OF_RANGE` | `IndexError` | interval past the contig end |
| `RESOURCE_EXHAUSTED`, `UNAVAILABLE` | retried by the channel: 5 attempts, exponential back-off 1 s to 60 s | quota or transient outage |

An invalid key surfaces as `ValueError`, not `PermissionError` (checked live
with a dummy key on 2026-09-13).

## Access tiers and terms

From the report's Data Availability section and the AlphaGenome terms:

| Data | Access | Route |
| --- | --- | --- |
| AVI scores, all hg38 SNVs | **permissive** licence, commercial use allowed | static download (Tabix) at https://alphagenome.google/downloads |
| AVI scores | non-commercial | API (`AVI_SCORE`) |
| AVI feature attributions | non-commercial | static download (Tabix) and API (`AVI_SCORE_FEATURE_IMPORTANCE`) |
| Splicing scores | non-commercial | static download (Tabix) and API |
| All other raw Atlas track scores | non-commercial | **API only** |
| Motif compendium and instances | browse on the portal; bulk download promised | portal |
| Commercial API access | "coming soon" via Google Cloud Model Garden | - |

Model and Atlas outputs are for research and theoretical modelling, may not be
used to train other machine-learning models, and are not for diagnostic
procedures or medical decision-making. The website is free for non-commercial
use. Query rates are demand-dependent and unpublished; the docs say the Atlas
"will typically have a larger query rate" than on-demand model predictions.

## The portal

`https://deepmind.google.com/science/alphagenome/atlas` (also reachable as
`https://alphagenome.google/atlas`). Query parameters, from DeepMind's link
builder:

| Parameter | Meaning |
| --- | --- |
| `q` | variant `chr:pos:ref>alt` (1-based), interval `chr:start-end` (1-based closed), gene symbol, or Ensembl gene ID. **rsIDs are not accepted.** |
| `m` | view: `variant`, `locus`, `entity` (gene), `motifs` |
| `i` | viewport interval, needed before motif instances render |
| `f` | filters: `BIOSAMPLE_NAME:K562`, `BIOSAMPLE_TYPE:...` (AND), `SCORER_MODALITY:RNA-seq`, `ASSAY_TRANSCRIPTOR_FACTOR:GATA1`, `ASSAY_HISTONE_MARK:H3K27ac` (OR within the assay group), `GENE_NAME:HBB` |
| `lItems` | layout: `avi`, `section:RNA_SEQ`, `section:DNASE`, `section:CHIP_TF`, ..., `pinned:<track key>` |
| `scores`, `md`, `tpRenames`, `tpLegendTitle` | the `/atlas/track-predictions` REF-vs-ALT comparison page |

Because RNA-seq and DNase tracks carry no TF code, a filter made only of TF
predicates hides them; add `SCORER_MODALITY:RNA-seq,SCORER_MODALITY:DNase`
alongside (`scripts/atlas_link.py` does this automatically).

## Bulk files and annotations

- GENCODE v46 GTF as Feather, the annotation behind both Atlas and model gene
  scores: `https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather`
  (about 318 MB, roughly 4 GB RAM in pandas; column names are capitalised:
  `Feature`, `Start`, `End`, `Strand`). Load with `pd.read_feather` and use
  `alphagenome.data.gene_annotation` helpers (`filter_to_mane_select_transcript`,
  `get_gene_interval`, `extract_tss`) so gene models match the scores.
- AVI Tabix downloads: https://alphagenome.google/downloads (not inspected here).

## Citing

Cite both the Atlas report (above) and the model paper: Avsec Ž. *et al.*,
"Advancing regulatory variant effect prediction with AlphaGenome", *Nature*
649, 1206-1218 (2026), doi:10.1038/s41586-025-10014-0. Software:
https://github.com/google-deepmind/alphagenome (Apache-2.0 client; the model
weights and outputs carry separate terms).
