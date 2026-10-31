# Cell Free Protein Expression Optimization

**URL:** https://cloud.ginkgo.bio/protocols/cell-free-protein-expression-optimization
**Service terms:** https://cloud.ginkgo.bio/terms/cfps-optimization
**Reviewed:** 2026-09-30; prices and turnaround below are catalog estimates.
**Status:** Ginkgo Certified
**Price:** $199/sample
**Turnaround:** up to 11 days

## Overview

Design of Experiment (DoE) approach to expressing protein targets in a proprietary reconstituted E. coli transcription-translation system. Each construct is evaluated in up to 24 reaction conditions per protein, including target-specific additives such as chaperones, disulfide-bond enhancers, and cofactors. Designed for difficult-to-express proteins including membrane proteins and targets with disulfide or cofactor requirements.

## Input

- **Sequence:** The protocol page currently links a CFPS `.xlsx` template for linear DNA; service terms request protein or DNA in FASTA. Confirm the current intake format before submitting.
- Specify replicates, linear DNA versus clonal plasmid synthesis, known expression difficulties, and desired additives.

## Output

- **Comparative Yield:** Titer data mapped across all tested variables (lysates, temps, additives)
- **Purity Profiling:** Target protein vs. background impurities to find highest quality yield
- **Best tested conditions:** Compare electropherograms and yield across the submitted matrix; this identifies candidates among the tested conditions, not a global optimum.

## Automated Workflow

### Phase 1 - Reagent Prep

1. Retrieve plates from 4 deg C
2. Thaw at room temperature
3. PBS backfill

### Phase 2 - CFPS Reaction Setup & Incubation

1. Retrieve plates from 4 deg C
2. Dispense lysate
3. QC plate read
4. Incubate (shaking or static, condition-dependent)

### Phase 3 - Quantification Prep & Read

1. Dispense PBS
2. Unseal plate
3. LabChip quantification
4. Seal plate
5. Store at 4 deg C

## Protocol Parameters

- Payloads & Reagents
- Bravo Stamp
- HiG Centrifuge
- Incubation & Storage

## Optimization Variables

The DoE matrix can span up to 24 conditions per protein, varying:

- **Lysate composition** (different E. coli extract formulations)
- **Temperature** (incubation temperature profiles)
- **Additives:**
  - Chaperones (for folding-challenged targets)
  - Disulfide-bond enhancers (for targets requiring disulfide bridges)
  - Cofactors (metal ions, coenzymes, prosthetic groups)
  - Other target-specific supplements

## Ordering

- **Number of Proteins:** configurable
- **Number of Replicates:** configurable
- **File Upload:** CSV, Excel, FASTA, TXT, PDF, ZIP
- **Additional Details:** free-text field for special requirements

## Use Cases

- Optimizing expression of difficult-to-express proteins
- Membrane protein expression screening
- Identifying optimal conditions for disulfide-bonded proteins
- Cofactor-dependent protein expression
- Systematic exploration of expression parameter space
- Finding the best formulation before scaling up production
