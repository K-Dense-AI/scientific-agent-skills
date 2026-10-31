# Cell Free Protein Expression with HiBiT Quantification

**URL:** https://cloud.ginkgo.bio/protocols/cell-free-protein-expression-hibit
**Service terms:** https://cloud.ginkgo.bio/terms/cfps-hibit
**Reviewed:** 2026-09-30; prices and turnaround below are catalog estimates.
**Status:** Ginkgo Certified
**Price:** $39/sample
**Turnaround:** up to 11 days
**Throughput:** 384-well format

## Overview

Fastest path from a sequence to a protein yield metric. Uses a proprietary reconstituted E. coli transcription-translation (CFPS) system; reactions complete in 4-16 hours and can yield up to 3 mg/mL of target protein. Expressed proteins are quantified directly from the crude reaction mixture (no purification) using the Promega Nano-Glo HiBiT Lytic Detection System. Designed for early-stage screening, novel construct evaluation, and rapid, data-driven triage before committing to optimization or purification.

## Input

- **Sequence input:** The protocol page links a CFPS `.xlsx` template for linear DNA; service terms describe protein or DNA in CSV. Confirm the downloaded schema and synthesis format (linear DNA or clonal plasmid).
- **HiBiT Tag Orientation:** N-terminal or C-terminal fusion
- **Linker Sequence:** If unspecified, Ginkgo uses a standard GGGS linker

## Output

- **Expression Detection:** Confirmation of target protein expression via background-subtracted luminescence (bcRLU) relative to controls
- **Relative Yield Quantification:** Target protein concentration (reported in nM), interpolated from a standard curve
- **Assay Quality Metrics:** Z-prime scores, replicate CV%, and matrix-effect controls

## Automated Workflow

### Phase 1 - CFPS Reaction Setup & Incubation

1. Stamp DNA templates into CFPS reaction mix
2. Seal and incubate (4-16 h)

### Phase 2 - Detection Prep

1. Spin down plates
2. Transfer samples and standards (Echo)
3. Dispense PBS/buffer and prepare the HiBiT assay plate (MultiFlo / Bravo 384)

### Phase 3 - Detection & Quantification

1. Incubate (ambistore)
2. Luminescence read (BMG PHERAstar)
3. Seal & store (Agilent PlateLoc)

## Ordering

- **Number of Proteins:** configurable
- **Number of Replicates:** configurable
- **File Upload:** CSV, Excel, FASTA, TXT, PDF, ZIP
- **Additional Details:** free-text field for special requirements

## Use Cases

- High-throughput expressibility screening without purification
- Rapid relative-yield comparison across construct variants
- Early triage before A280/LabChip purification tiers
