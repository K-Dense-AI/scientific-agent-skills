# E. coli Protein Expression with HiBiT Quantification

**URL:** https://cloud.ginkgo.bio/protocols/ecoli-protein-expression-hibit
**Service terms:** https://cloud.ginkgo.bio/terms/ecoli-hibit
**Reviewed:** 2026-09-30; prices and turnaround below are catalog estimates.
**Status:** Ginkgo Certified
**Price:** $79/sample
**Turnaround:** up to 3 weeks
**Throughput:** Up to 384 constructs per run

The catalog says up to 3 weeks, while service terms state 15-20 business days from
DNA submission. Confirm scheduling in the accepted order.

## Overview

Fully automated, end-to-end workflow for expressing and quantifying HiBiT-tagged proteins in E. coli. Heat shock transformation is followed by inoculation into lactose-based autoinduction media for target protein expression, then cell pelleting, detergent-based lysis, and HiBiT-based quantification. Results are reported as both raw and standard curve-normalized values, enabling quantitative comparison across up to 384 constructs per run.

## Input

- **Sequence input:** Protein or DNA in CSV, with HiBiT tag/linker and expression notes. The current page links a CFPS-named `.xlsx` file; verify that its fields cover this E. coli service before uploading.
- **HiBiT tag orientation:** N-terminal or C-terminal fusion (default GGGS linker if unspecified)

## Output

- **OD600 growth confirmation:** Per-well absorbance readings confirming bacterial growth prior to pelleting
- **HiBiT luminescence values:** Per-well bcRLU from BMG PHERAstar; preserve the supplied background-correction convention
- **Normalized expression estimate:** Semi-quantitative expression normalized to an on-plate HiBiT standard curve
- **QC report:** PDF with per-construct results, process control outcomes, and pass/fail status; raw CSV available

## Automated Workflow

1. **Transformation** (heat shock)
2. **Autoinduction expression** in lactose-based media
3. **Cell pelleting**
4. **Detergent-based lysis**
5. **HiBiT detection & luminescence read** (BMG PHERAstar)

## Ordering

- **Number of Proteins:** configurable
- **Number of Replicates:** configurable
- **File Upload:** CSV, Excel, FASTA, TXT, PDF, ZIP
- **Additional Details:** free-text field for special requirements

## Use Cases

- Very high-throughput expressibility screening in E. coli (up to 384 constructs)
- Relative expression comparison across large construct sets
- Early triage before His-tag purification tiers
