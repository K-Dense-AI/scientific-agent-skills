# Core Workflows and Tool Categories

Complete command sequences for ChIP-seq quality control, full ChIP-seq analysis, RNA-seq
coverage, and ATAC-seq analysis, then the tool categories: BAM/bigWig processing, quality
control, and visualization.

## Core Workflows

deepTools workflows typically follow this pattern: **QC → Normalization → Comparison/Visualization**

### ChIP-seq Quality Control Workflow

When users request ChIP-seq QC or quality assessment:

1. **Generate workflow script** using `scripts/workflow_generator.py chipseq_qc`
2. **Key QC steps**:
   - Sample correlation (multiBamSummary + plotCorrelation)
   - PCA analysis (plotPCA)
   - Coverage assessment (plotCoverage)
   - Fragment size validation (bamPEFragmentSize)
   - ChIP enrichment strength (plotFingerprint)

**Interpreting results:**
- **Correlation**: Replicates should cluster together with a correlation pattern appropriate to the assay; no universal 0.9 cutoff
- **Fingerprint**: Strong ChIP shows steep rise; flat diagonal indicates poor enrichment
- **Coverage**: Assess if sequencing depth is adequate for analysis

Full workflow details in `references/workflows.md` → "ChIP-seq Quality Control Workflow"

### ChIP-seq Complete Analysis Workflow

For full ChIP-seq analysis from BAM to visualizations:

1. **Generate coverage tracks** with normalization (bamCoverage)
2. **Create comparison tracks** (bamCompare for log2 ratio)
3. **Compute signal matrices** around features (computeMatrix)
4. **Generate visualizations** (plotHeatmap, plotProfile)
5. **Enrichment analysis** at peaks (plotEnrichment)

Use `scripts/workflow_generator.py chipseq_analysis` to generate template.

Complete command sequences in `references/workflows.md` → "ChIP-seq Analysis Workflow"

### RNA-seq Coverage Workflow

For strand-specific RNA-seq coverage tracks:

Use bamCoverage with `--filterRNAstrand` to separate forward and reverse strands.

**Important:** NEVER use `--extendReads` for RNA-seq (would extend over splice junctions).

**Strand note:** `--filterRNAstrand` assumes common dUTP/NSR/NNSR reverse-stranded library preparation. For libraries where read 1 follows the RNA strand, forward/reverse output is inverted; use SAM flag filters when library chemistry differs.

Use CPM or per-bin RPKM for coverage; neither provides annotation-aware gene quantification.

Template available: `scripts/workflow_generator.py rnaseq_coverage`

Details in `references/workflows.md` → "RNA-seq Coverage Workflow"

### ATAC-seq Analysis Workflow

For an ATAC-seq workflow that needs shifted alignments (do not shift already corrected inputs):

1. **Shift reads** using alignmentSieve with `--ATACshift`
2. **Sort and index** the shifted BAM, then generate alignment coverage with bamCoverage (not insertion counts)
3. **Analyze fragment sizes** (expect nucleosome ladder pattern)
4. **Visualize at peaks** if available

Template: `scripts/workflow_generator.py atacseq`

Full workflow in `references/workflows.md` → "ATAC-seq Workflow"

## Tool Categories and Common Tasks

### BAM/bigWig Processing

**Convert BAM to normalized coverage:**
```bash
bamCoverage --bam input.bam --outFileName output.bw \
    --normalizeUsing RPGC --effectiveGenomeSize 2913022398 \
    --binSize 10 --numberOfProcessors 8
```

**Compare two samples (log2 ratio):**
```bash
bamCompare -b1 treatment.bam -b2 control.bam -o ratio.bw \
    --operation log2 --scaleFactorsMethod readCount
```

**Key tools:** bamCoverage, bamCompare, multiBamSummary, multiBigwigSummary, correctGCBias, alignmentSieve

Complete reference: `references/tools_reference.md` → "BAM and bigWig File Processing Tools"

### Quality Control

**Check ChIP enrichment:**
```bash
plotFingerprint -b input.bam chip.bam -o fingerprint.png \
    --extendReads 200 --samFlagExclude 1024
```

**Sample correlation:**
```bash
multiBamSummary bins --bamfiles *.bam -o counts.npz
plotCorrelation -in counts.npz --corMethod pearson \
    --whatToPlot heatmap -o correlation.png
```

**Key tools:** plotFingerprint, plotCoverage, plotCorrelation, plotPCA, bamPEFragmentSize

Complete reference: `references/tools_reference.md` → "Quality Control Tools"

### Visualization

**Create heatmap around TSS:**
```bash
# Compute matrix
computeMatrix reference-point -S signal.bw -R genes.bed \
    -b 3000 -a 3000 --referencePoint TSS -o matrix.gz

# Generate heatmap
plotHeatmap -m matrix.gz -o heatmap.png \
    --colorMap RdBu --kmeans 3
```

**Create profile plot:**
```bash
plotProfile -m matrix.gz -o profile.png \
    --plotType lines --colors blue red
```

**Key tools:** computeMatrix, plotHeatmap, plotProfile, plotEnrichment

Complete reference: `references/tools_reference.md` → "Visualization Tools"
