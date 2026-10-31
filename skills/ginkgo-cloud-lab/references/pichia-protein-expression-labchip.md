# Pichia Protein Expression Validation (LabChip)

**URL:** https://cloud.ginkgo.bio/protocols/pichia-protein-expression-labchip
**Service terms:** https://cloud.ginkgo.bio/terms/pichia-protein-expression-validation
**Reviewed:** 2026-09-30; prices and turnaround below are catalog estimates.
**Status:** Ginkgo Certified
**Price:** $89/sample
**Turnaround:** up to 4 weeks
**Throughput:** Up to 96 constructs per run

## Overview

End-to-end automated workflow using Ginkgo's proprietary *Pichia pastoris* strains to express and characterize secreted proteins. Strains progress through three sequential preculture and production fermentation stages (multi-stage fed-batch-style growth). Secreted protein expression is quantified by size and purity via microfluidic capillary electrophoresis (LabChip). Useful for targets that express better in a eukaryotic secretion system than in E. coli or cell-free.

## Input

- **Sequence input:** AA or DNA in CSV per service terms, with known expression constraints. The page labels its template `.xlsx`, but its download URL ends in `.csv`; inspect the downloaded format rather than renaming the extension.

## Output

- **Expression Confirmation:** Verification of the target protein at the expected molecular weight
- **Yield estimate:** Reference-standard estimate (ug/mL) above the detection limit; absolute yield is not guaranteed
- **Initial Purity:** Percentage of target protein vs. impurities, delivered with virtual gel images
- Results reported as protein size (kDa), purity (%), and relative concentration, with growth/QC context; use these for comparative expression ranking

## Automated Workflow

1. **Transformation** using 384-well plates
2. **Multi-stage fermentation** (three sequential preculture and production stages, fed-batch-style growth)
3. **Supernatant harvest** by high-speed centrifugation
4. **Quantification Prep** - dispense PBS diluent (BioTek MultiFlo), seal (Agilent PlateLoc), store at 4 deg C (HRB TundraStore)
5. **LabChip protein quantification** (size, purity, relative concentration)

## Ordering

- **Number of Proteins:** configurable
- **Number of Replicates:** configurable
- **File Upload:** CSV, Excel, FASTA, TXT, PDF, ZIP
- **Additional Details:** free-text field for special requirements

## Use Cases

- Expressing secreted/eukaryotic proteins that are difficult in E. coli or cell-free
- Validating expressibility in *Pichia pastoris* before scale-up
- Size/purity profiling of secreted targets
