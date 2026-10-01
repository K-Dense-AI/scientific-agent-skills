# Echo-MS Method Onboarding

**URL:** https://cloud.ginkgo.bio/protocols/echo-ms-method-onboarding
**Service terms:** https://cloud.ginkgo.bio/terms/echo-ms-onboarding
**Reviewed:** 2026-09-30; prices and turnaround below are catalog estimates.
**Status:** Ginkgo Certified
**Price:** $799/molecule
**Turnaround:** up to 3 weeks

## Overview

Echo-MS is an open-access, high-throughput mass spectrometry platform that eliminates the chromatography step. An acoustic liquid handler (Labcyte/Beckman Echo) ejects nanoliter droplets directly from a source plate into an open-port sampling interface connected to a mass spectrometer. Without a column to equilibrate, cycle times drop to 1-5 seconds per sample, enabling analysis of a full 384-well plate in ~2 hours (with replicates). Best suited for relative quantitation, screening, and titer assays where throughput matters more than chromatographic resolution.

This protocol onboards your analyte for future experiments: MS conditions (spray voltage, curtain gas, ion source settings) and ejection parameters (volume, interval, carrier solvent) are optimized, and a simple sample-prep protocol is established. Onboard a method here before running [echo-ms-cfps-detection.md](echo-ms-cfps-detection.md).

The terms scope this to relative quantitation in the CFPS matrix, not absolute
quantitation or analytes requiring chromatographic separation. A calibration curve
does not establish selectivity for unresolved interferents or a different matrix.

## Input

(Download Template)

- Molecule CAS ID
- Expected reaction and conversion amount
- Expected concentrations of substrates
- Reaction conditions (time sensitivities, buffers, pure/lysate)

## Output

For each molecule of interest:

- Echo-MS method and calibration curve in the Cell Free Protein Expression Matrix
- LOD + LOQ in the Cell Free Protein Expression Matrix
- Validation run and report
- Recommended next steps (e.g., sample-prep optimization) if method development was not successful

## Automated Workflow

### Phase 1 - In Silico Triage & Procurement

1. Intake and triage (Nebula Core)
2. Standard procurement (Nebula Core)

### Phase 2 - Method Development with CFPS Matrix

1. Establish standard solutions (Nebula Core)
2. Optimize MRM transitions (SciEx TripleQuad 6500+ / EchoMS)
3. Optimize EchoMS parameters (SciEx TripleQuad 6500+ / EchoMS)
4. Matrix validation (SciEx TripleQuad 6500+ / EchoMS)

## Ordering

- **Number of Molecules:** configurable ($799/molecule)
- **File Upload:** CSV, Excel, FASTA, TXT, PDF, ZIP
- **Additional Details:** free-text field for special requirements

## Use Cases

- Onboarding a small molecule/analyte for high-throughput Echo-MS screening
- Establishing calibration curves, LOD/LOQ in the CFPS matrix
- Prerequisite for Echo-MS enzymatic detection runs
