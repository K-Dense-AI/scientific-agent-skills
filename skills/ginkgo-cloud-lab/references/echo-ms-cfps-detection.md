# Echo-MS Detection of Molecules from an Enzymatic Reaction (Cell Free)

**URL:** https://cloud.ginkgo.bio/protocols/echo-ms-cfps-detection
**Service terms:** https://cloud.ginkgo.bio/terms/echo-ms-cfps-detection
**Reviewed:** 2026-09-30; prices and turnaround below are catalog estimates.
**Status:** Beta
**Price:** $44/sample
**Turnaround:** up to 13 days

## Overview

Fastest path from a protein sequence to a functional, quantitative readout on enzyme activity. Using a proprietary reconstituted E. coli transcription-translation (CFPS) system, Ginkgo expresses your enzyme of interest in 4-16 hours. A substrate or product is then added directly to the well and substrate conversion is measured by acoustic ejection mass spectrometry (Echo-MS), delivering a go/no-go signal without protein purification. Enzyme expression and Echo-MS are performed using the baseline Cell Free Protein Synthesis Master Mix.

To run this protocol, the relevant analyte/method must first be onboarded (see [echo-ms-method-onboarding.md](echo-ms-method-onboarding.md)).

## Input

- Enzyme DNA or AA sequence; contact Ginkgo for DNA sequences longer than 1800 bp
- Analyte CAS ID and expected substrate concentration
- Reaction timing/temperature constraints and per-well buffer, substrate, and cofactor conditions

## Output

- **Method summary**
- **Peak table** (substrate depletion and/or product formation)

## Automated Workflow

### Phase 1 - CFPS Expression

1. Express enzyme in CFPS master mix (4-16 h)

### Phase 2 - Enzymatic Reaction

1. Dispense molecule, buffers, reagents (Agilent Bravo 96)
2. Incubate under reaction conditions (Inheco)

### Phase 3 - Dilution and Echo-MS Detection

1. Prepare a standard curve in diluted CFPS matrix
2. Dilute reaction wells
3. Measure substrate/product by Echo-MS; interpret within the onboarded matrix and detection limits

## Ordering

- **Number of Samples:** configurable ($44/sample)
- **File Upload:** CSV, Excel, FASTA, TXT, PDF, ZIP
- **Additional Details:** free-text field for special requirements

## Use Cases

- Go/no-go enzyme activity screening without purification
- Detecting substrate depletion / product formation for biocatalysis
- High-throughput functional triage of enzyme variants
