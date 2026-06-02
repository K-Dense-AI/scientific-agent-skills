# Counts assembly and handoff to DE + enrichment

Goal: turn quant output into the two files the **`pydeseq2`** skill wants, then rank/threshold the DE result for the **`pathway-enrichment`** skill.

- `counts.csv` — a **gene × sample** matrix of **integers** (raw or length-scaled counts; never TPM/FPKM).
- `metadata.csv` — one row per sample (index = sample IDs matching the count columns), columns describing the design (`condition`, `batch`, …).

`scripts/build_counts_matrix.py` produces both. This file explains what it does and the nuances you must get right.

## Orientation (don't trip on this)

PyDESeq2 ultimately needs **samples × genes**. By convention this skill writes `counts.csv` as **genes × samples** (matches Salmon/STAR/featureCounts and nf-core outputs), and the `pydeseq2` skill's loader transposes with `.T`. Keep `counts.csv` genes × samples and let the DE step transpose — don't transpose twice.

## Salmon → gene counts (pytximport)

Salmon is transcript-level; sum to genes with `pytximport` (the Python port of tximport). Use `counts_from_abundance="length_scaled_tpm"` — the correct choice for gene-level DE (corrects for differential transcript-length/usage across samples and yields counts you can feed directly).

```python
from pytximport import tximport

quant_files = ["quant/s1/quant.sf", "quant/s2/quant.sf", "quant/s3/quant.sf"]
txi = tximport(
    quant_files,
    data_type="salmon",
    transcript_gene_map="tx2gene.tsv",          # columns: transcript_id, gene_id
    counts_from_abundance="length_scaled_tpm",
    output_type="xarray",
    ignore_transcript_version=True,              # drops the .N Ensembl version suffix
)
# txi holds gene x sample estimated counts; round to integers for PyDESeq2 (see below).
```

The bundled `scripts/build_counts_matrix.py --from salmon --quant-dir quant/ --tx2gene tx2gene.tsv` wraps this, names columns by sample directory, rounds, and writes `counts.csv` + `metadata_template.csv`.

### Getting a tx2gene map

A two-column transcript_id → gene_id table. Options:
- `pytximport.utils.create_transcript_gene_map(species="human")` (or `human`/`mouse` etc.).
- From the annotation GTF (authoritative — matches your quant reference):

```bash
awk -F'\t' '$3=="transcript"{ match($9,/transcript_id "([^"]+)"/,t); match($9,/gene_id "([^"]+)"/,g); print t[1]"\t"g[1] }' \
  annotation.gtf | sort -u | sed '1i transcript_id\tgene_id' > tx2gene.tsv
```

- nf-core/rnaseq writes the tx2gene it actually used into its output — reuse that on Path A.

## STAR → gene counts (ReadsPerGene)

Each `*.ReadsPerGene.out.tab` has 4 columns: gene_id, unstranded, forward-strand, reverse-strand. Skip STAR's first 4 summary rows (`N_unmapped`, …) and pick the column matching your strandedness (col index 1/2/3 → unstranded/forward/reverse). `scripts/build_counts_matrix.py --from star --quant-dir star/ --strandedness reverse` does this across all samples. These are already integers.

## featureCounts → gene counts

`featureCounts` writes one matrix with a header comment line, then columns: `Geneid, Chr, Start, End, Strand, Length, <bam1>, <bam2>, …`. Keep `Geneid` + the per-BAM count columns, rename columns to sample IDs. `scripts/build_counts_matrix.py --from featurecounts --counts-file counts/featurecounts.txt` handles it. Already integers.

## The estimated-count / integer nuance

PyDESeq2 requires **integer** counts. STAR and featureCounts give integers already. Salmon/RSEM give **estimated** (fractional) counts.

- **What this skill does:** use `length_scaled_tpm` and **round to the nearest integer**. With length-scaled counts the library-size and transcript-length information is already folded into the values, so rounding and treating them as counts is a well-established, defensible approximation for gene-level DE.
- **The "proper" R route** (`tximport` → `DESeqDataSetFromTximport`) instead imports raw counts plus a per-gene **average-transcript-length offset**, letting DESeq2 model length internally. PyDESeq2 does not accept that offset, so the length-scaled-and-round approach is the standard Python equivalent and is what tools like nf-core surface for downstream use.
- Either way: **never** feed TPM/FPKM to DESeq2 — those are normalized and break the count model.

## Gene-ID mapping (do this before enrichment)

DESeq2 output is typically keyed by **Ensembl gene IDs** (e.g. `ENSG00000141510`), often with a version suffix (`.17`). Enrichr/MSigDB/g:Profiler libraries expect **gene symbols** (human UPPERCASE). Mapping mismatch is the #1 cause of "nothing is enriched".

- Strip version suffixes: `ids.str.replace(r"\.\d+$", "", regex=True)`.
- Map Ensembl → symbol with the `gget` skill (`gget info`), `database-lookup`, `pybiomart`, or `mygene`. On Path A, the nf-core `gene_name` column already gives symbols — keep it alongside `gene_id`.
- Keep mapping for *enrichment input*; you can keep Ensembl IDs through DE and map only the final gene lists.

## DE → enrichment recipe

After the `pydeseq2` skill produces `deseq2_results.csv` (columns include `log2FoldChange`, `pvalue`, `padj`, `stat`):

- **GSEA (preranked)** — use the **full** ranked gene list, ranked by the Wald `stat` (sign = direction, magnitude = evidence; more stable than ranking by log2FoldChange). Don't threshold first.
- **ORA** — use the **thresholded** hit list: `padj < 0.05`, optionally also `|log2FoldChange| > 1`; consider running up- and down-regulated sets separately.

The `pathway-enrichment` skill's `scripts/run_enrichment.py` reads a DESeq2 results CSV directly:

```bash
# GSEA straight from the DE table (auto-builds the rank from `stat`)
python ../pathway-enrichment/scripts/run_enrichment.py gsea \
  --deseq2 deseq2_results.csv --organism human --outdir enrichment/ --seed 123

# ORA from a symbol hit list
python ../pathway-enrichment/scripts/run_enrichment.py ora \
  --genes sig_symbols.txt --organism human --outdir enrichment/
```

Make sure the IDs in `deseq2_results.csv` / `sig_symbols.txt` are symbols (or map them first). Then visualize with the `scientific-visualization` skill.
