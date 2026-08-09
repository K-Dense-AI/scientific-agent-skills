# Microfluidic design requirements checklist

Fill this in **before** sizing anything. Every blank left open here becomes a
redesign later. Bracketed fields are decisions to record, not suggestions.

## 1. Purpose and sample

- [ ] One-sentence function of the device: [ ]
- [ ] Working fluid(s): [ ] — Newtonian? [yes/no]. If whole blood or another
  non-Newtonian fluid AND any requirement below is shear-critical, stop:
  this skill's formulas do not cover it.
- [ ] Operating temperature: [ ] °C (viscosity changes ~2%/°C for water)
- [ ] Particles/cells present: type [ ], size range [ ] µm, largest object
  the device must pass [ ] µm
- [ ] Sample volume available: [ ] µL; is dead volume critical? [yes/no]

## 2. Quantitative requirements

- [ ] Flow rate(s): [ ] µL/min, tolerance [ ]%
- [ ] Wall shear stress limit or target (cells): [ ] Pa
- [ ] Residence/transit time: [ ] s, tolerance [ ]%
- [ ] Mixing requirement: species [ ], to [ ]% mixed
- [ ] Droplets: target diameter [ ] µm, CV [ ]%, rate [ ] Hz
- [ ] Separation: what from what [ ], critical size [ ] µm, purity [ ]%,
  throughput [ ] µL/min
- [ ] Oxygen/nutrient demand: cell number [ ], OCR [ ] amol/cell/s
- [ ] Pressure budget: max pressure anywhere in the system [ ] kPa

## 3. Actuation and instrumentation

- [ ] Available drive: [syringe pump / pressure controller / gravity /
  spin motor / high-voltage supply / none (capillary)]
- [ ] Portability constraint: [benchtop / handheld / instrument-free]
- [ ] Detection: [microscopy / fluorescence / electrochemical / impedance /
  none] — does it constrain material optics or autofluorescence?

## 4. Fabrication reality

- [ ] Available process: [pdms-softlith / thermoplastic-emboss /
  injection-molding / glass-wet-etch / sla-3dprint / outsourced]
- [ ] Minimum feature the process guarantees: [ ] µm
- [ ] Height(s) available (e.g. SU-8 recipe set): [ ] µm
- [ ] Expected height tolerance: [ ]% (resistance error ≈ 3× height error)
- [ ] Bonding method and typical strength: [ ]
- [ ] Small hydrophobic molecules in the assay (drugs, dyes)? [yes/no] —
  if yes and the material is PDMS, justify or change material.
- [ ] Sterilization needed? [autoclave / EtO / UV / none]

## 5. Pre-fabrication review (sign off each line)

- [ ] Re < 2000 everywhere at the operating point (`dimensionless_numbers.py`)
- [ ] Network solved; flows and shears within spec at ±10% height variation
      (`channel_resistance.py network`, re-run with heights × 0.9 and × 1.1)
- [ ] Every module gate passed (mixing budget, droplet regime, separation,
      Joule ΔT, burst margins, O₂ budget — the relevant scripts exit 0)
- [ ] `fabrication_check.py` exits 0 for the chosen process
- [ ] Ports match available punches/tubing; layout exported and reviewed
      (`mask_layout.py`, check polarity and the POSTS layer)
- [ ] Operating pressure < bond strength with ≥ 2× margin
- [ ] Every constant used is either measured locally or traceable to
      `references/source-ledger.md`
