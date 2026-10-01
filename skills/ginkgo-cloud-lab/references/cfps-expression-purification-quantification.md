# Cell Free Protein Expression, Purification, and Quantification

**URL:** https://cloud.ginkgo.bio/protocols/cfps-expression-purification-quantification
**Service terms:** https://cloud.ginkgo.bio/terms/cfps-expression-purification
**Reviewed:** 2026-09-30; prices and turnaround below are catalog estimates.
**Status:** Ginkgo Certified
**Price:** $159/sample
**Turnaround:** up to 12 days
**Throughput:** Up to 88 constructs per run (1 column reserved for controls), 96-well format

## Overview

End-to-end automated cell-free expression, Strep-tag purification, and quantification of StrepII-tagged proteins, combining A280 yield with LabChip purity/size assessment. CFPS products are purified with magnetic beads on the Agilent Bravo, quantified by A280 on the BMG PHERAstar, then characterized on the Revvity LabChip. The catalog describes an 8-hour expression step while terms describe reactions typically completed within 20 hours; confirm the run-specific incubation rather than treating either as fixed.

## Input

- **DNA Input:** Linear DNA sequence (`.xlsx` template)
- **Tag Orientation:** N-terminal or C-terminal fusion (validated with C-terminal tags; success is protein-dependent)
- **Format:** Up to 88 constructs per run, 1 column of wells for controls

## Output

- **Expression Confirmation:** Verification of the target protein at the expected molecular weight
- **Baseline Titer:** Initial quantitative yield measurement (mg/L)
- **Initial Purity:** Percentage of target protein vs. impurities, delivered with virtual gel images
- **Purified concentration:** A280 eluate concentration in mg/mL with annotated CE-SDS data, QC report, and raw CSV files; do not conflate eluate concentration with reaction titer.

## Automated Workflow

### Phase 1 - CFPS Reaction Setup & Incubation

1. Retrieve plates from storage (HRB TundraStore)
2. Stamp DNA templates into CFPS reaction mix (Agilent Bravo 96)
3. Seal plate (Agilent PlateLoc)
4. Incubate shaking at 29-30 deg C (Thermo Cytomat)

### Phase 2 - Mag Bead Purification & Quantification

1. Dispense reagents and load samples (Biotek / Agilent)
2. Bind sample to beads (Bravo Shaker)
3. Wash beads (Agilent Bravo 96)
4. Elute purified protein (Agilent Bravo 96)
5. Transfer eluate to read plate (Agilent Bravo 96)
6. Read A280 & fluorescence (BMG PHERAstar)

### Phase 3 - LabChip Purity and Size Assessment

1. LabChip assessment (Revvity LabChip)
2. Seal plate (Agilent PlateLoc)
3. Store at 4 deg C (HRB TundraStore)

## Ordering

- **Number of Proteins:** configurable
- **Number of Replicates:** configurable
- **File Upload:** CSV, Excel, FASTA, TXT, PDF, ZIP
- **Additional Details:** free-text field for special requirements

## Use Cases

- Purified yield plus purity/size profiling in one cell-free run
- Characterizing constructs before scale-up production
- Comparing titer and purity across sequence variants
