# Counts assembly and handoff to DE + enrichment

The bundled bridge writes `counts.csv` (genes × samples, integer counts),
`metadata_template.csv` (fill in biological design, then save as `metadata.csv`),
and `counts_provenance.json` (input SHA-256 hashes, sample order, import settings).
Keep quantifier logs, tool versions, reference/annotation release and hashes alongside
these files; the sidecar cannot recover provenance absent from the quantification files.

## Choose the count model before import

- Full-length Salmon: aggregate transcripts with `counts_from_abundance="length_scaled_tpm"`,
  then round once for PyDESeq2. No additional transcript-length offset is applied.
- Alternative R workflow: raw estimated counts plus effective lengths through
  `tximport` → `DESeqDataSetFromTximport`. That function also handles bias-corrected
  counts without adding a second length correction. Neither route is universally superior.
- **3′ tagged/counting assays:** do not length-correct; use original counts with an
  assay-appropriate workflow. The bundled Salmon bridge targets full-length bulk data.
- Never submit TPM, FPKM, log counts, VST values, or batch-corrected expression to the
  negative-binomial count model. Library-size normalization is performed by the DE engine.

PyDESeq2 0.5.4 requires non-negative integer counts and has no tximport
average-transcript-length-offset input. Rounding an appropriate estimated-count
matrix is an import step, not a way to turn arbitrary normalized expression into counts.

## Salmon → gene counts (pytximport 0.13.0)

The preferred transcript-to-gene map comes from the exact GTF used to build the
quantification reference. This offline example replaces platform-specific awk syntax:

```python
from pytximport.utils import create_transcript_gene_map_from_annotation

mapping = create_transcript_gene_map_from_annotation(
    "annotation.gtf", source_field="transcript_id", target_field="gene_id",
)
mapping.to_csv("tx2gene.tsv", sep="\t", index=False)
```

A live `create_transcript_gene_map(species="human")` query is not a substitute for
matching the reference release. The helper supports human/mouse and an Ensembl
archive `host`, but no live BioMart query was exercised in this review.

For illustration, the underlying import API is:

```python
from pytximport import tximport

txi = tximport(
    ["quant/s1/quant.sf", "quant/s2/quant.sf"],
    data_type="salmon",
    transcript_gene_map="tx2gene.tsv",
    counts_from_abundance="length_scaled_tpm",
    ignore_transcript_version=False,
    ignore_after_bar=False,
    output_type="anndata",
    return_data=True,
)
counts = txi.to_df().T.round().astype("int64")  # genes × samples
```

Use the bundled CLI for preflight checks, deterministic sample naming and provenance:

```bash
python scripts/build_counts_matrix.py --from salmon \
  --quant-dir quant/ --tx2gene tx2gene.tsv --output-dir counts/
```

The bundled import first aggregates transcript counts, abundances and effective lengths
to genes, then applies gene-level length scaling, then rounds once. Scaling individual
transcripts before aggregation is a different calculation.

It requires unique transcript IDs and the same transcript IDs/order across quant files,
checks every quantified transcript has a map entry, and rejects ambiguous mappings.
If the same release puts transcript versions in the FASTA but not the GTF identifiers,
inspect the mismatch and use `--ignore-transcript-version` explicitly. It strips only
terminal `.N` suffixes and rejects collisions; it does not fix a mismatched annotation.
For GENCODE bar-delimited names, build the Salmon index with `--gencode`.

On nf-core 3.27.0, preserve `*.merged.tx2gene_augmented.tsv`, the mapping actually
used for import. Self-mapped orphan transcripts remain transcript identifiers and
need review before interpreting rows as genes. The local bridge deliberately stops
on missing mappings instead of silently dropping or self-mapping them.

## STAR and featureCounts

STAR `ReadsPerGene.out.tab` starts with four summary rows, then gene ID and three
count columns. The CLI requires a verified `--strandedness`: `unstranded`, `forward`,
or `reverse` selects zero-based column 1, 2, or 3. Gene sets must agree across samples;
a missing row is not evidence for zero expression. Do not mix annotations or silently
merge duplicate sample names after filename cleanup.

featureCounts starts with a command comment followed by `Geneid, Chr, Start, End,
Strand, Length` and one column per BAM. The bridge accepts non-negative integer
counts, rejects duplicate sample/gene IDs, and rejects fractional output from
`--fraction` instead of truncating it. Preserve whether paired reads were counted
as fragments (`-p --countReadPairs`). Neither importer infers experimental design.

Raw duplicate column labels are rejected before pandas can rename them, including
Salmon tables, transcript maps, featureCounts, samplesheets and metadata. Resolve
the ambiguity in the source instead of choosing one renamed column.

All-zero genes are removed during export. Samples with no counts stop the export.

## Orientation, metadata, design and contrast

PyDESeq2 consumes **samples × genes**. Transpose exactly once and reorder metadata
by sample ID, never by its incidental row position:

```python
import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats

counts = pd.read_csv("counts.csv", index_col=0).T
metadata = pd.read_csv("metadata.csv", index_col=0)
assert counts.index.is_unique and counts.columns.is_unique and metadata.index.is_unique
assert set(metadata.index) == set(counts.index)
metadata = metadata.loc[counts.index]
assert metadata["condition"].notna().all()
assert not metadata["condition"].isin(["", "CHANGE_ME"]).any()

# Include batch only when recorded, non-missing and estimable.
dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", n_cpus=1)
dds.deseq2()
stats = DeseqStats(dds, contrast=["condition", "treated", "control"], alpha=0.05, n_cpus=1)
stats.summary()
stats.results_df.to_csv("deseq2_results.csv")
```

The positive log2 fold change above means **treated / control**. For paired samples,
consider `~subject + condition`; for a measured crossed batch, `~batch + condition`.
Check full matrix rank and positive residual degrees of freedom before fitting.
Interactions change the meaning of main effects; use explicit simple effects or a
proper numeric contrast, with the downstream skill. Technical lanes are not replicates.

The current Python APIs and an explicit contrast were exercised on small synthetic
data; the example paths and biological labels must be replaced for a real study.

## DE → enrichment

- Preranked GSEA uses all eligible tested genes with finite signed Wald statistics,
  not only significant genes. Resolve duplicate mapped identifiers before ranking;
  record any policy for one-to-many or many-to-one mappings and tied scores.
- ORA uses a prespecified hit rule (for example `padj < 0.05`), separate up/down lists
  when relevant, and the tested, detectable, mapped gene universe as background.
- Use IDs accepted by the chosen organism/library release. Many GMT/Enrichr libraries
  use symbols; g:Profiler also accepts Ensembl IDs. Do not force human capitalization
  onto another species. Retain Ensembl IDs through DE and map only enrichment inputs.

Illustrative handoffs (network enrichment was not executed in this review):

```bash
python ../pathway-enrichment/scripts/run_enrichment.py gsea \
  --deseq2 deseq2_results.csv --organism human --outdir enrichment/ --seed 123

python ../pathway-enrichment/scripts/run_enrichment.py ora \
  --genes sig_symbols.txt --background tested_symbols.txt \
  --organism human --outdir enrichment/
```

## Official sources reviewed

- [pytximport API](https://pytximport.complextissue.com/en/stable/autoapi/pytximport/index.html)
  and [GTF helper](https://pytximport.complextissue.com/en/stable/autoapi/pytximport/utils/index.html).
- [tximport count/offset choices and 3′ caveat](https://bioconductor.org/packages/release/bioc/vignettes/tximport/inst/doc/tximport.html).
- [PyDESeq2 0.5.4 dataset](https://pydeseq2.readthedocs.io/en/stable/api/docstrings/pydeseq2.dds.DeseqDataSet.html)
  and [contrast API](https://pydeseq2.readthedocs.io/en/stable/api/docstrings/pydeseq2.ds.DeseqStats.html).
- [nf-core/rnaseq 3.27.0 output contract](https://nf-co.re/rnaseq/3.27.0/docs/output).
