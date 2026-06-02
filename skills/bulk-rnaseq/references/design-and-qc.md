# Experimental design and QC

The statistics downstream are only as good as the design and the QC gates. Decide design **before** sequencing; apply QC **before, during, and after** quantification. This is what makes a bulk RNA-seq result defensible.

## Experimental design

### Replication
- Use **biological** replicates (independent samples), not technical (same library re-sequenced). Technical replicates measure machine noise, not biological variability, and don't license generalization.
- **≥3 per group is the practical minimum**; 4–6 is much safer for typical effect sizes. With n=2 you cannot estimate within-group variance reliably and DESeq2's dispersion shrinkage is doing almost all the work.
- More replicates beat more depth for detecting DE. Don't trade replicates for coverage.

### Depth, length, layout
- ~20–30M mapped reads/sample is enough for standard gene-level DE. Push higher (50M+) for lowly expressed genes, novel transcripts, or isoform-level work.
- Paired-end and longer reads help mapping/isoforms but aren't required for gene-level DE; single-end is fine if that's what you have.
- Keep layout, read length, kit, and depth **consistent across all samples** in a comparison.

### Avoid confounding (the design killer)
- A **batch** is anything technical that varies across samples: processing day, sequencing lane/flowcell, kit lot, operator, RNA extraction round.
- If a batch is perfectly aligned with your condition (all treated processed Monday, all controls Tuesday), the biological effect is **mathematically unrecoverable**. No analysis fixes this.
- Defenses: **randomize** sample-to-batch assignment, and **balance** so every batch contains every condition. Record all batch variables in the metadata.

### Design formulas (hand to PyDESeq2)
- Put adjustment variables first, the variable of interest **last**: `~batch + condition`.
- Continuous covariate: `~age + condition` (ensure it's numeric).
- Interaction (does the treatment effect differ by genotype?): `~genotype + condition + genotype:condition`.
- The design matrix must be **full rank** — you can't include a batch that's perfectly confounded with condition; `pydeseq2` will error. Check `pd.crosstab(metadata.condition, metadata.batch)` for empty cells.

## QC gates

### Raw-read QC (FastQC / MultiQC)
- **Per-base quality** — bulk of bases ≥ Q30; some drop at read ends is normal (trimming/soft-clipping handles it).
- **Adapter content** — flagged adapters → trim (Path B step 2; Path A does it automatically).
- **Over-represented sequences** — adapters, rRNA, or highly expressed transcripts. Persistent rRNA suggests poor depletion.
- **GC content** — a bimodal/odd distribution can indicate contamination.
- **Sequence duplication** — high duplication is *expected* in RNA-seq (highly expressed genes); see below.

### Alignment / quantification QC
- **STAR uniquely-mapped %** — typically >70–80% for a good library/reference. Low → wrong/old reference, contamination, or degraded RNA.
- **Salmon mapping rate** (`logs/salmon_quant.log`) — usually >70%. Low → wrong transcriptome, no decoys, or contamination.
- **featureCounts assigned %** — low "assigned" with high "unassigned_NoFeatures" often means **wrong strandedness** (`-s`).
- **rRNA fraction** — high rRNA wastes reads; note it, and consider `--remove_ribo_rna` on Path A.
- Verify **strandedness** matches across tools (see `upstream-manual.md`).

### Don't deduplicate for standard DE
PCR/optical duplicates look alarming but in RNA-seq mostly reflect genuine high expression. Standard gene-level DE (DESeq2) does **not** remove duplicates. Only consider dedup with UMIs (use the UMI, not coordinate dedup).

### Post-quantification QC (before trusting DE)
Always do this on the counts, ideally on variance-stabilized/log values:
- **PCA** — do biological replicates cluster? Does the main axis separate your condition, or a batch? A batch dominating PC1 means you must model it. An obvious outlier may be a swap/failure.
- **Sample-distance heatmap / hierarchical clustering** — confirms grouping and exposes mislabeled or swapped samples.
- If a batch clearly structures the data, add it to the design (`~batch + condition`); if it's unknown, consider surrogate-variable / RUV approaches (out of scope here — note it).

### After DE: p-value histogram
- A well-behaved test gives a roughly **uniform** histogram with a **peak near 0** (the true positives).
- A peak near 1, or a U-shape, signals a problem: misspecified design, unmodeled batch, or filtering issues. Fix the design rather than trusting the gene list.

## Quick gate checklist

```
[ ] >=3 biological replicates per group
[ ] batch recorded and NOT confounded with condition
[ ] raw FastQC reviewed; adapters trimmed
[ ] mapping/assignment rate acceptable; strandedness verified
[ ] PCA + sample-distance heatmap inspected; outliers/swaps resolved
[ ] design formula full-rank, adjustment vars before variable of interest
[ ] p-value histogram sane after DE
[ ] versions pinned (pipeline -r, tools, genome+annotation release)
```
