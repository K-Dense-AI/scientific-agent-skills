# Sensing and detection integration

Design rules for building the readout into the chip: impedance/Coulter
counting, electrochemical electrodes, optical detection, and TEER. Citations
in [source-ledger.md](source-ledger.md) (Gawad 2001; Sun & Morgan 2010).

## Impedance / Coulter counting

A particle transiting a sensing aperture displaces conducting fluid; the
resistance pulse scales with the *volume fraction*:

    ΔR/R ≈ (d_particle/D_aperture)³ × shape factor (~1.5 spheres)

Design rules that follow directly:

- **Aperture sizing**: d/D ≈ 0.2–0.8. Below ~0.05 the pulse drowns in noise
  (a 1 µm particle needs a ≲ 5–10 µm aperture); near 1 the aperture clogs.
  One aperture cannot span RBCs and bacteria — dual apertures or
  frequency-multiplexed electrodes.
- **Coincidence limit**: one particle in the sensing zone at a time —
  concentration ≲ 0.1/(sensing volume). A 30×30×30 µm zone → ≲ ~4×10⁶/mL;
  dilute blood accordingly.
- **Throughput**: transit time ~10–100 µs sets the bandwidth; count rates to
  ~10³–10⁴/s per aperture.
- Microfabricated version (Gawad 2001): coplanar or facing electrode pairs in
  a channel; AC multi-frequency drive reads size (low f) and membrane/
  cytoplasm properties (MHz) simultaneously — impedance cytometry (Sun &
  Morgan 2010). Differential electrode pairs cancel drift.
- Sheath or inertial prefocusing (this skill's tools) tightens pulse CVs by
  forcing one trajectory through the non-uniform field.

## Electrochemical electrodes on chip

- **Materials/process**: sputtered Pt/Au (Ti adhesion) on glass, patterned by
  lift-off — fabricate on the flat lid, not inside PDMS. Screen-printed
  carbon for disposables.
- **iR drop**: in low-conductivity media, place the reference/counter close
  to the working electrode; in a channel the resistance between electrodes is
  the same R_hyd arithmetic with σ replacing 1/µ scaling — long thin channels
  between electrodes are ohmic dividers.
- **Pseudo-reference drift**: a bare Pt/Ag wire drifts tens of mV; Ag/AgCl
  ink helps but chlorides foul — recalibrate per run or integrate a true
  reference well.
- **Bubbles**: any electrolysis at the working potential nucleates bubbles in
  channels (see the bubble section of
  [valves-pumps-flow-control.md](valves-pumps-flow-control.md)); stay inside
  the water window and vent near electrodes.
- O₂ sensing alternative: optical phosphorescence spots (PtOEP/PdOEP beads)
  read through transparent lids — no analyte consumption, no bubbles.

## TEER (barrier integrity) in membrane devices

Four-electrode measurement across the membrane of a two-channel device (see
[cell-culture-organ-on-chip.md](cell-culture-organ-on-chip.md)): drive pair +
sense pair, one of each per channel. Chip TEER values are not directly
comparable to Transwell numbers — normalise by the *culture area the current
actually crosses*, and report the geometry. Electrode placement dominates the
measured value in thin channels because medium resistance is in series;
subtract a cell-free blank of the same chip.

## Optical detection

- **Interrogation volume**: fluorescence signal ∝ dye amount in the confocal/
  excitation volume; a 100 µm-deep channel at 10 µM fluorescein is bright, a
  10 µm channel at 10 nM is photon-starved — budget S/N from
  (depth × concentration × dwell time).
- **Path length**: absorbance scales with it (Beer–Lambert); 50 µm channels
  lose 200× vs a 1 cm cuvette — absorbance on-chip needs folded light paths
  (Z-cells) or waveguides.
- **Material autofluorescence**: glass < COC ≈ PDMS ≪ PMMA (UV-blue); PDMS
  scatters more after plasma aging. For 488/530 nm work all are fine; for
  UV/deep-blue assays use glass/quartz.
- Thick device floors defeat high-NA objectives: keep the imaging side at
  #1.5 coverslip thickness (~170 µm) — a standard spin in organ-on-chip
  layouts (imaging window in the layout, not an afterthought).
- Droplet/flow cytometry rates: a PMT + focused laser reads ~10⁴–10⁵
  events/s — match to droplet generation frequency, and keep inter-droplet
  spacing > beam waist.

## Integration order of operations

Sensors constrain layers and materials early: metal electrodes want a glass
lid and change the bonding process (plasma bonding over patterned metal needs
care at step edges); optical windows pin device orientation; TEER wiring
crosses layers. Put the readout in the requirements checklist
(`assets/design-checklist.md` §3) before geometry is frozen, not after.
