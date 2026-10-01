# E. coli Minibinder Expression with His-tag Purification and Yield via A280

**URL:** https://cloud.ginkgo.bio/protocols/ecoli-minibinder-expression-histag-a280
**Service terms:** https://cloud.ginkgo.bio/terms/ecoli-minibinder-histag-a280
**Reviewed:** 2026-09-30; prices and turnaround below are catalog estimates.
**Status:** Ginkgo Certified
**Price:** $199/sample
**Turnaround:** up to 3 weeks
**Throughput:** Up to 96 constructs in parallel

## Overview

Fully automated, end-to-end service that takes designed minibinder candidates from heat shock transformation through bacterial expression, cell lysis, magnetic His-tag (IMAC) bead purification, and quantitative yield measurement by A280 absorbance - built to screen binder designs before scale-up. Instruments include the Agilent Bravo 96/384, BioTek MultiFlo, Inheco and Cytomat incubators, and a Spark plate reader.

## Input

- **Minibinder input:** AA or DNA sequence in CSV as specified by the intake text; the download is an E. coli `.xlsx` template. Inspect the current template and retain the requested fields when exporting.
- **His-tag orientation:** N-terminal or C-terminal fusion; linker sequence (default GGGS if unspecified)
- **Known expression notes:** Disulfide bonds, cofactor requirements, toxicity concerns, or PTM needs

## Output

- **Yield Quantification:** A280 per well, converted to protein concentration (mg/mL) via the protein's molar extinction coefficient
- **Expression Confirmation:** Fluorescence signal relative to controls
- **OD culture growth data** reported per construct
- **Assay Quality Metrics:** Per-run quality summary with plate-level controls
- QC-flagged PDF results report plus downloadable raw CSV files

## Automated Workflow

Four phases coordinated across automated instruments:

### Phase 1 - Transformation & Heat Shock Recovery

1. Pre-chill ATC (Inheco ATC 384)
2. Heat shock & cycle (Inheco ATC 384)
3. Add LB recovery media (Agilent Bravo 384)
4. Recovery incubation (Inheco)

### Phase 2 - Culture Growth & Harvest

### Phase 3 - Cell Lysis & Clarification

### Phase 4 - His-tag Purification & A280 Yield

1. Dispense PBS (BioTek MultiFlo)
2. Load sample onto beads (Agilent Bravo 96)
3. Binding incubation (Bioshake)
4. Wash beads (Agilent Bravo 96)
5. Elute protein (Agilent Bravo 96)
6. Read A280 (Agilent Bravo 96 + Spark)

## Ordering

- **Number of Proteins:** configurable
- **Number of Replicates:** configurable
- **File Upload:** CSV, Excel, FASTA, TXT, PDF, ZIP
- **Additional Details:** free-text field for special requirements

## Use Cases

- Screening designed minibinder/binder candidates in E. coli before scale-up
- Parallel yield comparison across up to 96 binder designs
- Producing His-tagged binders for downstream characterization
