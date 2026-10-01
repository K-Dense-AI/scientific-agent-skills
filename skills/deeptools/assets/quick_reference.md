# deepTools Quick Reference

Targets deepTools 4.0.0. Commands are templates requiring matching assemblies and indexed inputs.
Duplicate filtering below requires upstream duplicate marking.

## Most Common Commands

### BAM to bigWig (normalized)
```bash
bamCoverage --bam input.bam --outFileName output.bw \
    --normalizeUsing RPGC --effectiveGenomeSize 2913022398 \
    --binSize 10 --numberOfProcessors 8
```

### Compare two BAM files
```bash
bamCompare -b1 treatment.bam -b2 control.bam -o ratio.bw \
    --operation log2 --scaleFactorsMethod readCount
```

### Correlation heatmap
```bash
multiBamSummary bins --bamfiles *.bam -o counts.npz
plotCorrelation -in counts.npz --corMethod pearson \
    --whatToPlot heatmap -o correlation.png
```

### Heatmap around TSS
```bash
computeMatrix reference-point -S signal.bw -R genes.bed \
    -b 3000 -a 3000 --referencePoint TSS -o matrix.gz

plotHeatmap -m matrix.gz -o heatmap.png
```

### ChIP enrichment check
```bash
plotFingerprint -b input.bam chip.bam -o fingerprint.png \
    --extendReads 200 --samFlagExclude 1024
```

## Effective Genome Sizes

These are illustrative values from the 4.0.0 tagged source. Rolling upstream tables differ; derive the value for the actual reference and filtering policy (see `references/effective_genome_sizes.md`).

| Organism | Assembly | Size |
|----------|----------|------|
| Human | hg38 | 2913022398 |
| Human | T2T/CHM13CAT_v2 | 3117292070 |
| Mouse | mm39 | 2654621783 |
| Mouse | mm10 | 2652783500 |
| Fly | dm6 | 142573017 |

## Common Normalization Methods

- **RPGC**: 1× genome coverage (requires --effectiveGenomeSize)
- **CPM**: Counts per million (for fixed bins)
- **RPKM**: Reads per kb per million (per output bin, not genes)

## Notes

- `--filterRNAstrand` assumes common dUTP-style reverse-stranded RNA-seq libraries.
- `--ATACshift` uses only properly paired fragments and is equivalent to `--shift 4 -5 5 -4`.

## Typical Workflow

1. **QC**: plotFingerprint, plotCorrelation
2. **Coverage**: bamCoverage with normalization
3. **Comparison**: bamCompare for treatment vs control
4. **Visualization**: computeMatrix → plotHeatmap/plotProfile
