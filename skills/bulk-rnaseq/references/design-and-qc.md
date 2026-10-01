# Experimental design and QC

The statistics downstream are only as good as the design and the QC gates. Decide design **before** sequencing; apply QC **before, during, and after** quantification. This is what makes a bulk RNA-seq result defensible.

## Experimental design

### Replication
- Use **biological** replicates (independent samples), not technical (same library re-sequenced). Technical replicates measure machine noise, not biological variability, and don't license generalization.
- **≥3 per group is a planning starting point**, not a power guarantee; choose sample size from expected dispersion, effect sizes and the intended contrast. Two per group can be fitted but give fragile inference. The bundled validator uses a conservative policy of at least two per group and recommends three; this is not a universal DESeq2 mathematical requirement.
- Once adequate depth is reached, biological replication often adds more power than deeper sequencing. Evaluate the tradeoff for the assay and target genes.

### Depth, length, layout
- ~20–30M mapped reads/sample is a rough planning example for many mammalian gene-level studies, not a QC cutoff. Push higher (50M+) for lowly expressed genes, novel transcripts, or isoform-level work.
- Paired-end and longer reads help mapping/isoforms but aren't required for gene-level DE; single-end is fine if that's what you have.
- Keep layout, read length, kit, and depth **consistent across all samples** in a comparison.

### Avoid confounding (the design killer)
- A **batch** is anything technical that varies across samples: processing day, sequencing lane/flowcell, kit lot, operator, RNA extraction round.
- If a batch is perfectly aligned with your condition (all treated processed Monday, all controls Tuesday), the biological effect is **mathematically unrecoverable**. No analysis fixes this.
- Defenses: **randomize** sample-to-batch assignment, and **balance** so every batch contains every condition. Record all batch variables in the metadata.

### Design formulas (hand to PyDESeq2)
- A conventional additive design is: `~batch + condition`.
- Continuous covariate: `~age + condition` (ensure it's numeric).
- Interaction (does the treatment effect differ by genotype?): `~genotype + condition + genotype:condition`.
- The design matrix must be **full rank** with positive residual degrees of freedom. A crosstab is an initial diagnostic, not proof of estimability; check the complete encoded matrix including subjects, interactions and covariates. Do not discard a confounded batch and then claim an isolated treatment effect. Set reference levels and an explicit contrast: column order alone does not specify the scientific comparison.

## QC gates

The ranges below are investigation triggers, not universal pass/fail limits. Interpret them
against organism, library protocol, RNA integrity, reference and study-wide distributions.

### Raw-read QC (FastQC / MultiQC)
- **Per-base quality** — bulk of bases ≥ Q30; some drop at read ends is normal (trimming/soft-clipping handles it).
- **Adapter content** — flagged adapters → trim (Path B step 2; Path A does it automatically).
- **Over-represented sequences** — adapters, rRNA, or highly expressed transcripts. Persistent rRNA suggests poor depletion.
- **GC content** — a bimodal/odd distribution can indicate contamination.
- **Sequence duplication** — high duplication is *expected* in RNA-seq (highly expressed genes); see below.

### Alignment / quantification QC
- **STAR uniquely-mapped %** — typically >70–80% for a good library/reference. Low → wrong/old reference, contamination, or degraded RNA.
- **Salmon mapping rate** (`logs/salmon_quant.log`) — usually >70%. Low → investigate reference mismatch, contamination, read quality and library type. Decoys improve assignment specificity and can reduce transcript mapping; their absence is not a simple explanation for a low rate.
- **featureCounts assigned %** — low "assigned" with high "unassigned_NoFeatures" often means **wrong strandedness** (`-s`).
- **rRNA fraction** — high rRNA wastes reads; note it, and consider `--remove_ribo_rna` on Path A.
- Verify **strandedness** matches across tools (see `upstream-manual.md`).

### Don't deduplicate for standard DE
PCR/optical duplicates look alarming but in RNA-seq mostly reflect genuine high expression. Standard gene-level DE (DESeq2) does **not** remove duplicates. Only consider dedup with UMIs (use the UMI, not coordinate dedup).

### Post-quantification QC (before trusting DE)
Always do this on the counts, ideally on variance-stabilized/log values:
- **PCA** — do biological replicates cluster? Does the main axis separate your condition, or a batch? A technical batch dominating PC1 warrants checking design and data quality; include it only when estimable and scientifically justified. An obvious outlier may be a swap/failure.
- **Sample-distance heatmap / hierarchical clustering** — confirms grouping and exposes mislabeled or swapped samples.
- If a batch clearly structures the data, add it to the design (`~batch + condition`); if it's unknown, consider surrogate-variable / RUV approaches (out of scope here — note it).

### After DE: p-value histogram
- Under a calibrated continuous null, null p-values are uniform; real signal may add a peak near zero. Discrete low-count tests and filtering can change the appearance, so interpret the histogram with model diagnostics.
- A peak near one or a U-shape is not by itself proof of a broken design. Inspect count distributions, outliers, filtering and covariates. Do not tune the model or exclude samples simply to obtain the desired histogram or more discoveries.

## Quick gate checklist

```
[ ] >=3 biological replicates per group
[ ] batch recorded and NOT confounded with condition
[ ] raw FastQC reviewed; adapters trimmed
[ ] mapping/assignment rate acceptable; strandedness verified
[ ] PCA + sample-distance heatmap inspected; outliers/swaps resolved
[ ] design full-rank, residual degrees of freedom positive, contrast explicit
[ ] p-value histogram sane after DE
[ ] versions pinned (pipeline -r, tools, genome+annotation release)
```

Official statistical reference: [DESeq2 vignette](https://bioconductor.org/packages/release/bioc/vignettes/DESeq2/inst/doc/DESeq2.html), including design rank, contrasts and transformed-count QC.
