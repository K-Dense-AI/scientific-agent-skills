---
name: microfluidic-design
description: Design microfluidic devices from requirements to fabrication-ready layout - exact rectangular hydraulic resistance and chip-level network solving, wall shear and oxygen budgets for organ-on-chip perfusion, micromixers and gradient generators, droplet generation and single-cell encapsulation, DLD, inertial, acoustic and magnetic separation, electroosmotic flow with Joule-heating limits, capillary, centrifugal (lab-on-CD) and electrowetting (EWOD) platforms, Quake valves, PCR chips, PDMS and thermoplastic and glass design rules, and DXF photomask export. Use when sizing, laying out, or sanity-checking any lab-on-a-chip design. Triggers include "microfluidic", "lab-on-a-chip", "microchannel", "hydraulic resistance", "PDMS", "soft lithography", "organ-on-chip", "wall shear stress", "micromixer", "droplet microfluidics", "T-junction", "flow focusing", "DLD", "inertial focusing", "acoustophoresis", "electroosmotic", "dielectrophoresis", "capillary valve", "electrowetting", "Quake valve", "PCR chip", "photomask".
license: MIT
compatibility: Requires Python 3.10+. Scripts use only the standard library - no numpy, scipy, or network access. All formulas are first-order analytical design relations with cited provenance, not CFD.
allowed-tools: Read Write Edit Bash
metadata:
  version: "1.0"
  skill-author: K-Dense Inc.
  last-reviewed: "2026-08-09"
---

# Microfluidic Design

## When to use

Any time the task is to size, lay out, or sanity-check a microfluidic device:
channel dimensions from flow/shear/residence requirements, chip-level flow
splits, mixers, droplet generators, particle/cell separators, electrokinetic
or acoustic modules, capillary/centrifugal/electrowetting platforms, valves
and pumps, PCR chips, oxygen budgets for cell culture, fabrication-rule
checks, and photomask geometry export.

This skill supports **design decisions for a device being built**. Auditing
units or plausibility in existing analysis code is `uncertainty-and-units`;
full CFD is `fluidsim`; measuring velocity fields is `openpiv`; programming
liquid handlers is `opentrons-integration`/`pylabrobot`; statistical DOE is
`experimental-design`. Deep coverage lives in 14 reference files; the
quantitative rules are executable as 14 bundled CLIs.

## What this skill exists to prevent

1. The circular Hagen-Poiseuille formula applied to a wide rectangular
   channel (~40% class error) - use the exact series.
2. Expecting turbulent mixing at Re < 1; mixing below Pe ~ 10^3 is diffusion
   or a designed mixer, nothing else.
3. Quoting mean shear where the cells feel wall shear tau = 6 mu Q / (w h^2).
4. Ignoring that R scales as h^-3: a +/-10% fabrication height error is a
   -27%/+37% resistance error, which breaks every resistance-ratio design.
5. A DLD gap equal to the critical diameter - D_c is a deflection threshold,
   not a sieve; the gap must pass the largest particle or the array clogs.
6. Running a hydrophobic-drug assay in PDMS, which absorbs the drug.
7. Aspect ratios that collapse (h/w > 5) or sag (w/h > 20) in PDMS.
8. Operating pressure above the bond strength.
9. Treating whole blood as Newtonian in a shear-critical design.
10. EOF designs with no Joule-heating budget.
11. A bulk acoustic resonator in PDMS, which absorbs the wave.
12. Capillary valves designed with static instead of advancing/receding
    contact angles, and burst sequences without margin for angle scatter.
13. EWOD drive voltages past dielectric breakdown chasing saturated angles.
14. "Perfused" cultures that are oxygen-starved because supply Q(C_in-C_min)
    was never compared to demand N_cells x OCR.
15. Quake valves drawn with rectangular flow channels, which never seal.
16. Fabricating a first design without a design-rule check against the
    chosen process.

## Required workflow

1. Capture requirements with [the checklist](assets/design-checklist.md):
   fluids, temperature, flows, shear limits, residence, particles, pressure
   budget, actuation, fabrication process, detection. **Stop if** the fluid
   is non-Newtonian and the deliverable is shear-critical, or a gas with
   Kn > 0.01 - those need models this skill does not implement.
2. Run `dimensionless_numbers.py` at the operating point. **Stop if**
   Re > 2000: every formula downstream assumes laminar flow.
3. Choose the transport/actuation modality for the constraints:

   | Modality | Choose when | Module |
   | --- | --- | --- |
   | Pressure-driven | default; pumps available | `channel_resistance.py` |
   | Capillary | instrument-free, single-use | `capillary_design.py` |
   | Centrifugal | multi-step assay, one spin motor | `centrifugal_design.py` |
   | Electroosmotic | plug flow, no moving parts, CE | `electrokinetics.py` |
   | Electrowetting | discrete droplets, reconfigurable | `digital_microfluidics.py` |
   | Droplet (two-phase) | compartmentalised reactions | `droplet_generator.py` |

4. Size single channels with `channel_resistance.py channel` (forward or
   inverse: flow <-> pressure <-> target shear <-> geometry).
5. Design the modules the requirements call for: mixing/gradients/H-filter,
   droplets, separation (DLD/inertial/acoustic/magnetic/sheath/trap), EOF or
   DEP, valves and pumping, thermal/PCR, oxygen budget. Each tool gates its
   own physics and exits 1 on a design that cannot work.
6. Assemble the chip and solve it with `channel_resistance.py network` on a
   JSON netlist. Re-solve at height x0.9 and x1.1. **Stop if** any segment
   carries droplets - the solver is single-phase; say so in the report.
7. Run `fabrication_check.py` for the chosen process. Exit 1 means redesign,
   not workaround.
8. Optionally export mask geometry with `mask_layout.py` (DXF R12 + SVG).
9. Report against the scientific acceptance gate below.

## Scripts

All are argparse CLIs run from `scripts/`; every formula is pinned by tests.

| Script | Question answered |
| --- | --- |
| `channel_resistance.py` | What geometry gives this flow/pressure/shear, and how does the whole chip split flow? |
| `dimensionless_numbers.py` | Which physics is active at this operating point? |
| `mixing_length.py` | How long to mix, how many gradient stages, what does an H-filter extract? |
| `droplet_generator.py` | What regime, droplet size, rate, and cell-loading statistics? |
| `particle_separation.py` | DLD/inertial/acoustic/magnetic/sheath/trap: does it separate, and in what length? |
| `electrokinetics.py` | EOF flow, voltage, current, Joule heat; DEP sign and trap strength; Debye length? |
| `capillary_design.py` | Does it self-fill, in what time, and do the stop valves hold? |
| `centrifugal_design.py` | Spin pressure, burst rpm, and does the valve sequence fire in order? |
| `digital_microfluidics.py` | Does EWOD actuation move/split droplets within breakdown limits? |
| `valve_pump_design.py` | Quake valve closing pressure, multiplexer lines, pump choice, RC settling? |
| `thermal_design.py` | Heater power, ramp-rate capability, PCR zone lengths? |
| `oxygen_transport.py` | Does supply meet cellular demand (or stay hypoxic when intended)? |
| `fabrication_check.py` | Does the geometry survive the chosen fabrication process? |
| `mask_layout.py` | Mask-ready DXF for channels, junctions, serpentines, DLD arrays |

## Output contract

Data goes to stdout; caveats and provenance go to stderr, so `> out.json`
stays parseable. Every CLI takes `--format table|json` (table default; JSON
is strict). Exit codes: `0` success, `1` a physical-validity or design-rule
gate failed (usable to gate a workflow), `2` bad input.

## Walkthrough 1: organ-on-chip perfusion

Size a 1 mm x 100 um culture chamber for 0.5 Pa wall shear at 37 C:

```bash
cd skills/microfluidic-design/scripts
python3 channel_resistance.py channel --width 1mm --height 100um --length 10mm \
    --fluid culture-medium --temp 37 --target-shear "0.5 Pa"
```

```
resistance_pa_s_per_m3         9.6054e+10
flow_rate_ul_min               66.67
pressure_drop_kpa              0.1067
mean_velocity_m_s              0.01111
transit_time_s                 0.9
reynolds                       2.694
wall_shear_pa                  0.5
approx_error_percent           -0.002656
```

0.5 Pa needs 66.7 uL/min. The stderr caveat reminds you that +/-10% on the
100 um height moves resistance -27%/+37% - state the SU-8 tolerance with the
design. Now the oxygen budget for 5x10^5 cells at OCR 100 amol/cell/s:

```bash
python3 oxygen_transport.py --flow-rate "66.7 uL/min" --cells 5e5 --ocr 100 \
    --chamber-width 1mm --chamber-height 100um --chamber-length 10mm
```

```
demand_mol_s                           5.0000e-11
convective_supply_mol_s                1.6675e-10
predicted_outlet_concentration_mol_m3  0.155
supportable_cells_at_this_flow         1.668e+06
transverse_diffusion_time_s            3.333
residence_time_s                       0.8996
wall_flux_limited                      yes
```

Supply covers demand 3x - but `wall_flux_limited yes` says transit (0.9 s)
beats transverse diffusion (3.3 s): cells on the floor see less than the
average. The fix is a lower chamber or slower flow - which conflicts with the
shear target, so resolve it explicitly (e.g. taller chamber at same shear).
This budget conflict is the actual work of organ-on-chip design. Then solve
the full two-chamber chip and check fabrication:

```bash
python3 channel_resistance.py network --netlist ../assets/example-network.json
python3 fabrication_check.py --process pdms-softlith \
    --netlist ../assets/example-network.json --operating-pressure "50 kPa"
```

```
[channels]
channel    from   to      resistance_pa_s_per_m3  flow_ul_min  dp_kpa  velocity_mm_s  wall_shear_pa  reynolds
feed       inlet  split   1.0298e+11              449.4        0.7713  149.8          6.741          33.29
chamber_a  split  merge   9.6054e+10              285.7        0.4573  47.61          2.143          11.54
chamber_b  split  merge   1.6761e+11              163.7        0.4573  45.48          2.047          10.4
drain      merge  outlet  1.0298e+11              449.4        0.7713  149.8          6.741          33.29
```

Mass conserves (285.7 + 163.7 = 449.4) because the solver enforces Kirchhoff;
what you are checking is whether the *shear split* between chambers matches
the intent. See [cell-culture-organ-on-chip.md](references/cell-culture-organ-on-chip.md)
for shear targets by cell type and the PDMS absorption caveats.

## Walkthrough 2: droplet single-cell encapsulation

50 um-class droplets in HFE-7500 + fluorosurfactant at a 40 um flow-focusing
orifice, loading 3x10^6 cells/mL:

```bash
python3 droplet_generator.py --geometry flow-focusing --width 100um --height 50um \
    --orifice 40um --continuous-flow "8 uL/min" --dispersed-flow "1.5 uL/min" \
    --interfacial-tension "2 mN/m" --fluid hfe-7500 --cell-concentration "3e6 1/mL"
```

```
capillary_number         0.01653
regime                   dripping
droplet_diameter_um      49.11
droplet_volume_pl        62.02
uncertainty              +/-30% -- calibrate against your own device
generation_frequency_hz  403.1

[poisson]
lambda_cells_per_droplet  empty_fraction  single_cell_fraction  multiplet_fraction
0.1861                    0.8302          0.1545                0.0153
```

Dripping regime (Ca between ~0.015 and ~0.1), ~400 Hz, and Poisson loading at
lambda 0.19: 15% singlets, 83% empties, 1.5% multiplets - the standard
single-cell operating point. The tool exits 1 in the jetting regime, where no
monodisperse prediction exists. Surfactant and wetting requirements come from
[droplet-design.md](references/droplet-design.md); pushing Ca above ~0.1 or
skipping surfactant are the two classic failure modes.

## Walkthrough 3: separation and mixing

DLD array to deflect 5 um particles (largest object 15 um), with a sharper
cutoff at eps = 0.05:

```bash
python3 particle_separation.py dld --critical-diameter 5um \
    --row-shift-fraction 0.05 --max-particle 15um
```

```
gap_um                    15.04
row_shift_fraction        0.05
critical_diameter_um      5
array_period_rows         20
tilt_angle_deg            2.862
recommended_min_depth_um  30
```

The Davis rule gives a 15 um gap - which almost equals the largest particle;
the tool exits 1 if the gap does not exceed it, because that is a clogged
array, not a separator. Now the mixing reality check for a reagent step:

```bash
python3 mixing_length.py length --width 200um --height 50um --flow-rate "2 uL/min" \
    --diffusivity small-molecule --available-length 15mm
```

```
peclet                 1333
mixing_length_mm       56.54
recommendation         straight channel does not fit; use a staggered-herringbone
                       mixer (grooves ~0.3x channel height, mixing length grows
                       as ln Pe -- Stroock 2002) or a serpentine Dean mixer ...
```

Exit code 1: 56 mm of diffusive mixing does not fit in 15 mm. The answer is a
herringbone mixer (design rules in
[mixing-and-mass-transport.md](references/mixing-and-mass-transport.md)), not
a longer chip.

## Walkthrough 4: instrument-free and portable modules

A capillary stop valve on a hydrophobic patch (theta_adv = 118 deg), holding
against 1.2 kPa upstream:

```bash
python3 capillary_design.py pressure --width 150um --height 50um \
    --theta-top 118 --applied-pressure "1.2 kPa"
```

```
capillary_pressure_kpa  -1.803
behaviour               barrier / stop valve (hydrophobic or geometric)
burst_margin            1.502
```

A 1.5x burst margin. On a centrifugal disc, the same physics sequences steps
by spin speed - and the margin gate catches a real layout error:

```bash
python3 centrifugal_design.py sequence --valve meter,1.6kPa,18mm,22mm \
    --valve mix,2.4kPa,24mm,28mm --valve read,3.5kPa,30mm,34mm
```

```
[valves]
valve  burst_rpm
meter  1353
mix    1453
read   1581
```

Exit 1: mix bursts only 1.07x above meter, inside contact-angle scatter -
move `mix` outward or raise its barrier until every step clears the 1.1x
margin. Finally, EWOD actuation for a droplet step on 1 um Parylene C:

```bash
python3 digital_microfluidics.py actuation --voltage 60V --dielectric-thickness 1um
```

```
contact_angle_actuated_deg  70
saturation_limited          yes
droplet_moves               yes
breakdown_voltage_v         270
max_safe_voltage_v          81
```

60 V moves the droplet with margin; the tool exits 1 above 30% of breakdown
or when hysteresis wins. Platform design rules:
[capillary-and-paper.md](references/capillary-and-paper.md),
[centrifugal-and-digital.md](references/centrifugal-and-digital.md).

## Scientific acceptance gate

A design is reportable only when all of these hold:

- Laminar flow confirmed at the operating point (Re < 2000; the relevant
  tool exited 0), with the modality-specific gates passed: mixing-length
  budget, droplet regime, separation migration vs residence, Joule
  temperature rise, burst/sequence margins, EWOD breakdown margin, thermal
  ramp feasibility, oxygen margin.
- Rectangular resistances computed with the exact series, or the
  approximation error explicitly bounded.
- The network re-solved at height x0.9 and x1.1 with requirements still met,
  or the height tolerance stated as a risk.
- `fabrication_check.py` exits 0 for the named process, and the operating
  pressure clears bond strength with >= 2x margin.
- Every constant used is either measured locally or traceable to
  [source-ledger.md](references/source-ledger.md); rule-of-thumb thresholds
  are labelled as typical values that local process limits override.

These tools produce **first-order analytical design estimates**. They do not
replace CFD for junction details, two-phase dynamics, or elastic-wall
coupling, and no script output constitutes experimental validation: a
fabricated device is characterised, not assumed. Never present a passing
gate as evidence that a physical chip works.

## References

- [governing-equations.md](references/governing-equations.md) - exact resistance, networks, shear, dimensionless numbers, dispersion, inertial lift
- [mixing-and-mass-transport.md](references/mixing-and-mass-transport.md) - mixing model, herringbone/Dean rules, gradient trees, H-filter
- [droplet-design.md](references/droplet-design.md) - regimes, scaling laws, fluid pairs, surfactants, wetting
- [particle-and-cell-manipulation.md](references/particle-and-cell-manipulation.md) - DLD, inertial, sheath, traps, magnetic, technique selection
- [electrokinetics.md](references/electrokinetics.md) - EOF, DEP, Joule heating, Debye length
- [acoustofluidics.md](references/acoustofluidics.md) - BAW/SAW resonators, contrast factor, energy-density calibration
- [capillary-and-paper.md](references/capillary-and-paper.md) - stop valves, Washburn, capillary pumps, paper/lateral flow
- [centrifugal-and-digital.md](references/centrifugal-and-digital.md) - lab-on-CD sequencing; EWOD actuation and droplet ops
- [valves-pumps-flow-control.md](references/valves-pumps-flow-control.md) - Quake valves, multiplexing, pump selection, RC dynamics, bubbles
- [thermal-design.md](references/thermal-design.md) - heaters, transients, PCR architectures
- [cell-culture-organ-on-chip.md](references/cell-culture-organ-on-chip.md) - shear targets, oxygen, membranes, PDMS caveats
- [sensing-and-detection.md](references/sensing-and-detection.md) - impedance cytometry, electrodes, TEER, optics
- [fabrication-methods.md](references/fabrication-methods.md) - process design rules, materials, interconnects, standards
- [source-ledger.md](references/source-ledger.md) - provenance for every claim

Assets: [design-checklist.md](assets/design-checklist.md),
[example-network.json](assets/example-network.json),
[fluid-and-material-data.md](assets/fluid-and-material-data.md).

## Dated upstream basis

Formulas and thresholds encode the primary sources listed with dates in
[source-ledger.md](references/source-ledger.md) (Bruus 2008; Squires & Quake
2005; Stroock 2002; Garstecki 2006; De Menech 2008; Davis 2006; Di Carlo
2007/2009; Unger 2000; Thorsen 2002; Cho & Fair 2003; Madou 2006; Kopp 1998;
Huh 2010; Toepke & Beebe 2006, among others), reviewed 2026-08-09. Property
values are typical design estimates; the tools tell you which inputs to
measure. Regime boundaries and process limits are presented as approximate
and device-dependent throughout.
