# AlphaGenome model API (`alphagenome.models.dna_client`)

Verified against `alphagenome` 0.9.0. The client is a thin gRPC wrapper: no
weights, no GPU, one API key. The same key serves the Atlas.

## Setup

```bash
uv pip install alphagenome            # PyPI; Python >= 3.10, tested here on 3.12 and 3.13
export ALPHAGENOME_API_KEY=...        # https://deepmind.google.com/science/alphagenome
```

```python
import os
from alphagenome.data import gene_annotation, genome, transcript
from alphagenome.models import dna_client, variant_scorers
from alphagenome.visualization import plot_components

dna_model = dna_client.create(os.environ["ALPHAGENOME_API_KEY"], timeout=30)
```

`alphagenome.colab_utils.get_api_key()` reads `ALPHA_GENOME_API_KEY` (note the
underscore) or a Colab secret of that name. The scripts here accept both.

## Coordinates and inputs

| Object | Convention |
| --- | --- |
| `genome.Interval(chromosome, start, end, strand='.')` | **0-based, half-open** |
| `genome.Variant(chromosome, position, reference_bases, alternate_bases, name='')` | **1-based** position, VCF-style anchored alleles |
| `genome.Variant.from_str("chr22:36201698:A>C")` | adds `chr` if missing; `VariantFormat.GNOMAD` (`22-1024-A-C`), `GTEX` (`chr22_1024_A_C_b38`), `OPEN_TARGETS` (`22_1024_A_C`), `OPEN_TARGETS_BIGQUERY` (`22:1024:A:C`) |
| `variant.reference_interval.resize(width)` | the usual way to build the model window around a variant |
| Human | hg38 (GRCh38.p13) |
| Mouse | mm10 (GRCm38.p6), `organism=dna_client.Organism.MUS_MUSCULUS` |

Supported input widths (`dna_client.SUPPORTED_SEQUENCE_LENGTHS`):

| Name | bp | Use |
| --- | --- | --- |
| `SEQUENCE_LENGTH_16KB` | 16,384 | ISM scans, fast iteration |
| `SEQUENCE_LENGTH_100KB` | 131,072 | |
| `SEQUENCE_LENGTH_500KB` | 524,288 | |
| `SEQUENCE_LENGTH_1MB` | 1,048,576 | default; best accuracy, needed for distal enhancers and contact maps |

Any other width raises. Sequences may contain `N` (pad with `'N'` for short
constructs: `seq.center(dna_client.SEQUENCE_LENGTH_1MB, 'N')`). 2 kb inputs were
removed in 0.5.0.

## Output types (`dna_client.OutputType`)

| Type | Signal | Resolution | Human tracks |
| --- | --- | --- | --- |
| `ATAC`, `DNASE` | chromatin accessibility | 1 bp | 167 / 305 |
| `CHIP_TF` | TF binding ChIP-seq | 1 bp | 1,617 |
| `CHIP_HISTONE` | histone marks | 128 bp | 1,116 |
| `CAGE`, `PROCAP` | transcription initiation (5' ends) | 1 bp | 546 / 12 (PROCAP human only) |
| `RNA_SEQ` | stranded coverage | 1 bp | 667 |
| `SPLICE_SITES` | donor/acceptor probability | 1 bp | 2 (strand-merged) |
| `SPLICE_SITE_USAGE` | fraction of transcripts using each site | 1 bp | 734 |
| `SPLICE_JUNCTIONS` | split-read counts per junction | junction | 734 |
| `CONTACT_MAPS` | 3D contact probability | 2,048 bp bins | 28 |

5,563 human tracks in total. Every track row carries `name`, `strand`,
`ontology_curie`, `biosample_name`, `biosample_type`, plus `gtex_tissue`
(RNA_SEQ, SPLICE_*), `transcription_factor` (CHIP_TF), `histone_mark`
(CHIP_HISTONE). Discover them with:

```python
meta = dna_model.output_metadata(dna_client.Organism.HOMO_SAPIENS)
df = meta.concatenate()                      # every output type in one DataFrame
df[df.biosample_name.str.contains("liver", case=False)][["output_type", "name", "ontology_curie", "biosample_name"]]
```

or `python scripts/score_variants.py --list-tracks --query liver -o tracks.tsv`.

Ontology terms are CURIEs: `UBERON:0002048` (lung), `UBERON:0001157` (colon,
transverse), `UBERON:0001114` (right liver lobe), `CL:0000084` (T cell),
`CL:0000236` (B cell), `EFO:0002067` (K562), `CLO:...` for cell lines.
Passing `ontology_terms=None` returns every track. The `ontology-term-resolution`
skill turns free text into validated CURIEs; then confirm the term exists in
`output_metadata`, because the model only has tracks for its training biosamples.

## Predictions

```python
interval = genome.Interval("chr22", 36_201_698 - 2**19, 36_201_698 + 2**19)   # 1 Mb

out = dna_model.predict_interval(
    interval=interval,
    requested_outputs=[dna_client.OutputType.RNA_SEQ, dna_client.OutputType.DNASE],
    ontology_terms=["UBERON:0001157"],
)
out.rna_seq.values.shape          # (1048576, n_tracks)  float32
out.rna_seq.metadata              # track DataFrame
out.rna_seq.interval, out.rna_seq.resolution

variant = genome.Variant.from_str("chr22:36201698:A>C")
vo = dna_model.predict_variant(
    interval=variant.reference_interval.resize(dna_client.SEQUENCE_LENGTH_1MB),
    variant=variant,
    requested_outputs=[dna_client.OutputType.RNA_SEQ],
    ontology_terms=["UBERON:0001157"],
)
vo.reference.rna_seq, vo.alternate.rna_seq     # TrackData for REF and ALT haplotypes

out = dna_model.predict_sequence(sequence="ACGT...", requested_outputs=[...], ontology_terms=[...])
```

`predict_variants` / `predict_intervals` / `predict_sequences` take lists and run
in parallel (`max_workers`, default 5). `TrackData` supports
`filter_to_positive_strand()`, `select_tracks_by_name()`, `slice_by_interval()`,
`resize()`, `change_resolution()`, `reverse_complement()`, and NumPy-style
`tdata[interval, mask]` indexing.

## Variant scoring

```python
scorers = list(variant_scorers.RECOMMENDED_VARIANT_SCORERS.values())    # 19 configurations
adatas = dna_model.score_variant(interval, variant, variant_scorers=scorers)   # list[AnnData], one per scorer
df = variant_scorers.tidy_scores(adatas, match_gene_strand=True)          # long DataFrame
df[["variant_id", "output_type", "variant_scorer", "gene_name", "biosample_name",
    "ontology_curie", "raw_score", "quantile_score"]]

# many variants, same window size
adatas = dna_model.score_variants(
    [v.reference_interval.resize(dna_client.SEQUENCE_LENGTH_1MB) for v in variants],
    variants, scorers, organism=dna_client.Organism.HOMO_SAPIENS, max_workers=5)
df = variant_scorers.tidy_scores(adatas)
```

`score_variant` has **no** `ontology_terms` argument: filter `df` on
`ontology_curie` or `biosample_name` afterwards (or on `adata.var`). At most 20
scorers per request, no duplicates. `merge_stranded_gene_tracks=True`
(default) merges + and - RNA-seq tracks for gene-centric scorers.

### Recommended scorers (`RECOMMENDED_VARIANT_SCORERS`)

| Key | Class | Configuration | Meaning of `raw_score` |
| --- | --- | --- | --- |
| `ATAC`, `DNASE`, `CHIP_TF`, `CAGE`, `PROCAP` | `CenterMaskScorer` | width 501, `DIFF_LOG2_SUM` | log2(sum ALT + 1) - log2(sum REF + 1) over the 501 bp around the variant |
| `CHIP_HISTONE` | `CenterMaskScorer` | width 2001, `DIFF_LOG2_SUM` | same, 2 kb window |
| `RNA_SEQ` | `GeneMaskLFCScorer` | | log2 fold change of exon coverage per gene overlapping the window (-1 = halved) |
| `RNA_SEQ_ACTIVE` | `GeneMaskActiveScorer` | | log activity of the more active allele; **not** a difference |
| `SPLICE_SITES`, `SPLICE_SITE_USAGE` | `GeneMaskSplicingScorer` | width None | max change in site probability / usage within the gene |
| `SPLICE_JUNCTIONS` | `SpliceJunctionScorer` | | change in junction counts, per junction |
| `POLYADENYLATION` | `PolyadenylationScorer` | | max log fold change in poly(A) isoform ratio; human only |
| `CONTACT_MAPS` | `ContactMapScorer` | | change in contact probability |
| `*_ACTIVE` (ATAC, DNASE, CHIP_TF, CHIP_HISTONE, CAGE, PROCAP) | `CenterMaskScorer` | `ACTIVE_SUM` | activity of the stronger allele |

Custom configurations: `CenterMaskScorer(requested_output, width in {None, 501,
2001, 10001, 100001, 200001}, aggregation_type in {DIFF_MEAN, DIFF_SUM,
DIFF_SUM_LOG2, DIFF_LOG2_SUM, L2_DIFF, L2_DIFF_LOG1P, ACTIVE_MEAN, ACTIVE_SUM})`
and `GeneMaskSplicingScorer(..., width in {None, 101, 1001, 10001})`.

`quantile_score` is the rank of `raw_score` against a background of common
variants (gnomAD v3 MAF > 0.01) for that scorer and track, signed like the raw
score and saturating at about +/-0.99999. Use it to judge unusualness, the raw
score to judge magnitude, and never one without the other
(`references/interpretation.md`).

## In silico mutagenesis

```python
window = genome.Interval("chr20", 3_753_000, 3_753_400).resize(dna_client.SEQUENCE_LENGTH_16KB)
ism_interval = window.resize(256)                      # mutate the central 256 bp (3 x 256 variants)
scorer = variant_scorers.CenterMaskScorer(
    requested_output=dna_client.OutputType.DNASE, width=501,
    aggregation_type=variant_scorers.AggregationType.DIFF_MEAN)
scores = dna_model.score_ism_variants(interval=window, ism_interval=ism_interval,
                                      variant_scorers=[scorer], interval_variant=None)
# scores: list (per variant) of list (per scorer) of AnnData
from alphagenome.interpretation import ism
matrix = ism.ism_matrix([s[0].X[0, track_index] for s in scores], variants=[s[0].uns["variant"] for s in scores])
plot_components.plot([plot_components.SeqLogo(matrix, scores=..., ylabel="ISM")], interval=ism_interval)
```

`interval_variant=` runs the scan on the ALT haplotype. The client chunks ISM
requests to 10 bp per call; a 256 bp scan is about 26 requests. For an hg38 SNV
window the Atlas already holds the answer (`atlas_query.py avi --interval`), so
reserve live ISM for mouse, non-reference backgrounds, or custom scorers.

## Gene annotation and plots

```python
import pandas as pd
gtf = pd.read_feather("https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather")
gtf = gene_annotation.filter_protein_coding(gtf)
gtf = gene_annotation.filter_to_mane_select_transcript(gtf)   # or filter_to_longest_transcript
interval = gene_annotation.get_gene_interval(gtf, gene_symbol="HBB").resize(dna_client.SEQUENCE_LENGTH_1MB)
transcripts = transcript.TranscriptExtractor(gtf).extract(interval)

plot_components.plot(
    [
        plot_components.TranscriptAnnotation(transcripts),
        plot_components.OverlaidTracks({"REF": vo.reference.rna_seq, "ALT": vo.alternate.rna_seq},
                                       colors={"REF": "dimgrey", "ALT": "red"}),
    ],
    interval=variant.reference_interval.resize(20_000),
    annotations=[plot_components.VariantAnnotation([variant])],
)
```

Components: `Tracks`, `OverlaidTracks`, `ContactMaps`, `ContactMapsDiff`,
`TranscriptAnnotation`, `SeqLogo`, `Sashimi` (splice junctions; filter by
strand yourself, it has no `strand` argument), with `IntervalAnnotation` and
`VariantAnnotation` overlays. The Feather GTF uses capitalised column names
(`Feature`, `Start`, `End`, `Strand`). Mouse annotations: GENCODE vM23 at the
same bucket path with `mm10`.

## Errors, retries, quota

`dna_client` wraps calls in `retry_rpc` (retries on `RESOURCE_EXHAUSTED` and
`UNAVAILABLE`). gRPC errors surface as `grpc.RpcError`; `error.code()` tells you
whether it is a bad key (`UNAUTHENTICATED` / `INVALID_ARGUMENT`), a quota stop
(`RESOURCE_EXHAUSTED`), or a bad argument. Quotas are per key and unpublished;
the API is free for non-commercial use, and DeepMind states outputs may not be
used to train other ML models. Commercial use goes through Google Cloud Model
Garden.

## Official material

- Docs: https://www.alphagenomedocs.com/ (quick start, essential commands,
  batch variant scoring, splicing variant scoring, PSI derivation, haplotype
  workaround, tissue ontology mapping, visualisation tour, FAQ).
- Code: https://github.com/google-deepmind/alphagenome (client) and
  https://github.com/google-deepmind/alphagenome_research (model code).
- DeepMind agent skills with worked variant reports:
  https://github.com/google-deepmind/science-skills (Apache-2.0).
- Paper: Avsec Ž. *et al.*, *Nature* 649, 1206-1218 (2026),
  doi:10.1038/s41586-025-10014-0.
