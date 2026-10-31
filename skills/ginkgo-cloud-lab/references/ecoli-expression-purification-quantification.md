# E. coli Protein Expression, Purification, and Quantification

**URL:** https://cloud.ginkgo.bio/protocols/ecoli-expression-purification-quantification
**Service terms:** https://cloud.ginkgo.bio/terms/ecoli-expression-purification-quantification
**Reviewed:** 2026-09-30; prices and turnaround below are catalog estimates.
**Status:** Ginkgo Certified
**Price:** $209/sample
**Turnaround:** up to 3 weeks
**Throughput:** Up to 96 constructs in parallel

The catalog says up to 3 weeks, while service terms state 15-20 business days from
DNA submission. Confirm scheduling in the accepted order.

## Overview

Fully automated, end-to-end service that takes DNA constructs from heat shock transformation through bacterial expression, cell lysis, magnetic His-tag (IMAC) bead purification, quantitative yield measurement by A280 absorbance, and LabChip-based purity and size assessment - all in a single unattended workflow. Instruments include the Agilent Bravo 96/384, BioTek MultiFlo, Inheco and Cytomat incubators, a Spark plate reader, and the Revvity LabChip.

## Input

- **Protein designs:** AA or DNA sequence submitted in CSV format
- **His-tag orientation:** N-terminal or C-terminal fusion; linker sequence (default GGGS if unspecified)
- **Known expression notes:** Disulfide bonds, cofactor requirements, toxicity concerns, or PTM needs

## Output

- **Yield Quantification:** A280 per well, converted to protein concentration (mg/mL) via the protein's molar extinction coefficient
- **Expression Confirmation:** Fluorescence signal relative to controls
- **Purity & Size Assessment:** LabChip-based purity percentage and apparent molecular weight per construct, with virtual gel images
- **OD culture growth data** reported per construct
- **Assay Quality Metrics:** Per-run quality summary with plate-level controls
- QC-flagged PDF results report plus downloadable raw CSV files

## Automated Workflow

Five phases coordinated across automated instruments:

1. **Transformation with LB recovery** (heat shock)
2. **Culture growth and harvest**
3. **Cell lysis**
4. **Magnetic bead IMAC purification with A280 yield readout** (BioTek MultiFlo, Agilent Bravo 96, Bioshake, Spark)
5. **LabChip purity / size assessment** (Revvity LabChip)

## Ordering

- **Number of Proteins:** configurable
- **Number of Replicates:** configurable
- **File Upload:** CSV, Excel, FASTA, TXT, PDF, ZIP
- **Additional Details:** free-text field for special requirements

## Use Cases

- Bacterial expression with purified yield plus purity/size profiling in one run
- Characterizing up to 96 constructs before scale-up
- Producing and QC-ing His-tagged protein for downstream work
