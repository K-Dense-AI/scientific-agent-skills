# Cell Free Protein Expression with Strep-tag Purification and Yield via A280

**URL:** https://cloud.ginkgo.bio/protocols/cfps-strep-tag-purification-a280
**Service terms:** https://cloud.ginkgo.bio/terms/cfps-strep-tag-a280
**Reviewed:** 2026-09-30; prices and turnaround below are catalog estimates.
**Status:** Ginkgo Certified
**Price:** $149/sample
**Turnaround:** up to 11 days
**Throughput:** Up to 88 constructs per run (1 column reserved for controls), 96-well format

## Overview

End-to-end automated expression and purification of StrepII-tagged proteins in 100 uL CFPS reactions, followed by StreptactinXT magnetic bead purification and A280 quantification. The catalog mentions 20-hour expression and LabChip, but the service terms describe typical 4-16-hour reactions and promise A280 yield/reporting without a LabChip deliverable. Confirm incubation and readout scope in the order; choose the [A280 + LabChip tier](cfps-expression-purification-quantification.md) when purity/size data are required.

## Input

- **DNA Input:** Linear DNA sequence
- **Tag Orientation:** N-terminal or C-terminal Strep-II tag fusion (validated with C-terminal tags; success is protein-dependent)
- **Format:** Up to 88 constructs per run, 1 column of wells for controls

## Output

- **Yield Quantification:** A280 per well, converted to protein concentration (mg/mL) via the protein's molar extinction coefficient
- **Expression Confirmation:** Fluorescence signal relative to controls
- **Assay Quality Metrics:** Per-run quality summary with plate-level controls

## Automated Workflow

### Phase 1 - CFPS Reaction Setup

1. Stamp DNA into CFPS mix (Agilent Bravo 96)
2. Incubate (Cytomat / Inheco)

### Phase 2 - Mag Bead Purification

1. Dispense reagents and load samples (Biotek / Agilent)
2. Bind sample to beads (Bravo Shaker)
3. Wash beads (Agilent Bravo 96)
4. Elute purified protein (Agilent Bravo 96)

### Phase 3 - Detection & Quantification

1. Transfer eluate to read plate (Agilent Bravo 96)
2. Read A280 & fluorescence (BMG PHERAstar)

## Ordering

- **Number of Proteins:** configurable
- **Number of Replicates:** configurable
- **File Upload:** CSV, Excel, FASTA, TXT, PDF, ZIP
- **Additional Details:** free-text field for special requirements

## Use Cases

- Purified-protein yield quantification from cell-free expression
- Screening Strep-tagged constructs before scale-up
- Comparing purified concentration across sequence variants
