# Minibinder Expression with Strep-tag Purification and Yield via A280

**URL:** https://cloud.ginkgo.bio/protocols/minibinder-strep-tag-a280
**Service terms:** https://cloud.ginkgo.bio/terms/minibinder-strep-tag-a280
**Reviewed:** 2026-09-30; prices and turnaround below are catalog estimates.
**Status:** Ginkgo Certified
**Price:** $149/sample
**Turnaround:** up to 11 days
**Throughput:** Up to 88 constructs per run (1 column reserved for controls), 96-well format

## Overview

Automated cell-free expression of StrepII-tagged minibinders in 100 uL reactions, typically for 20 hours, followed by magnetic bead purification and A280 eluate quantification. The catalog also mentions LabChip, but the service terms list A280 yield and reporting without a LabChip deliverable. Confirm purity/size measurements separately; this service does not measure binding affinity.

## Input

- **DNA Input:** Linear DNA sequence
- **Tag Orientation:** N-terminal or C-terminal fusion (validated with C-terminal tags; success is protein-dependent)
- **Format:** Up to 88 constructs per run, 1 column of wells for controls

## Output

- **Yield Quantification:** A280 per well, converted to protein concentration (mg/mL) via the protein's molar extinction coefficient
- **Expression Confirmation:** Fluorescence signal relative to controls
- **Assay Quality Metrics:** Per-run quality summary with plate-level controls

## Automated Workflow

1. Express the tagged construct in CFPS.
2. Capture on Strep-tag affinity magnetic beads, wash, and elute.
3. Quantify purified eluate by A280 and review plate controls.

The catalog's instrument diagram instead shows CFPS, dilution, and LabChip without
the purification step. Use the confirmed service scope above for planning and ask
Ginkgo to resolve this diagram inconsistency before execution.

## Ordering

- **Number of Proteins:** configurable
- **Number of Replicates:** configurable
- **File Upload:** CSV, Excel, FASTA, TXT, PDF, ZIP
- **Additional Details:** free-text field for special requirements

## Use Cases

- Screening designed minibinder/binder candidates before scale-up
- Rapid purified-yield comparison across binder designs
- Cell-free triage of de novo designed proteins
