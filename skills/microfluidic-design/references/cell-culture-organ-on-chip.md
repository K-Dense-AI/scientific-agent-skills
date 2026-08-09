# Cell culture and organ-on-chip design

Perfused culture adds three budgets on top of ordinary microfluidics: wall
shear the cells feel, oxygen/nutrient supply vs consumption, and material
biocompatibility over days. Citations in [source-ledger.md](source-ledger.md)
(Huh 2010; Toepke & Beebe 2006; Regehr 2009; Berthier 2012).

## Wall shear stress targets

τ_wall = 6µQ/(wh²) — use `channel_resistance.py channel --target-shear` to
size for these (and remember it is the *wall* value, not the mean):

| Cell type / context | τ (Pa) | Note |
| --- | --- | --- |
| Arterial endothelium | 1–2 | alignment/atheroprotective phenotype |
| Venous endothelium | 0.1–0.6 | |
| Lymphatic/capillary models | 0.01–0.1 | |
| Epithelium (gut, lung apical) | 0.001–0.02 | often < mPa; media exchange, not shear |
| Hepatocytes | < 0.05 direct | shear-sensitive: shield behind barriers or membranes |
| MSC/osteoblast mechanobiology | 0.1–2 | stimulus, not tolerance |
| Kidney proximal tubule | 0.1–0.5 | |

1 dyn/cm² = 0.1 Pa. Tolerances are phenotype-relevant: ±20% shear across the
culture area is a common spec — check the shear *profile* across wide
chambers (side walls run lower), and re-check at ±10% height variation.

## Oxygen: the budget that silently fails

`oxygen_transport.py` implements: supply = Q·(C_in − C_min) [+ PDMS
permeation], demand = N_cells·OCR.

- Air-saturated medium at 37 °C: ~0.2 mol/m³. Physoxia targets: 5% O₂ ≈
  0.05 mol/m³ (many tissues), liver zonation 0.02–0.09.
- OCR spans 1–400 amol/cell/s (hepatocytes 300–900): **the least certain
  input — measure it** (Seahorse or literature for your line).
- Example: 10⁵ hepatocytes × 400 amol/s = 4×10⁻¹¹ mol/s needs ≥ 16 µL/min of
  air-saturated medium if the outlet may not drop below 0.05 — often more
  than shear allows → conflict resolved by PDMS-roof permeation, oxygenator
  segments, or lower cell number. The tool exposes exactly this arithmetic.
- Transverse check: cells on the floor see the wall concentration; the tool
  compares h²/D against residence and flags wall-flux limitation.
- **Hypoxia by design** is the reverse budget: it *fails on a PDMS roof*
  (ambient O₂ re-enters through ~2.7×10⁻¹³ mol/(m·s·Pa) permeability) — use
  glass/COC and control the feed gas.

## Nutrient depletion and media exchange (same arithmetic)

Glucose (5–25 mol/m³ in media, consumption ~10–100 amol/cell/s) usually
outlasts oxygen; lactate accumulation limits static intervals. Rule of
thumb: media volume-exchanges per day ≥ the flask-equivalent (0.2–0.4
mL/cm²/day scaled to chip area) — then check shear again; the two budgets
fight, and the standard resolutions are wider/taller chambers or shear
shields.

## Membrane co-culture (the Huh 2010 lung-on-chip pattern)

Two channels separated by a porous membrane; epithelium on top, endothelium
below.

- Membrane: track-etched PET/PC (0.4–8 µm pores) or spin-cast porous PDMS
  (~10 µm thick, 7–10 µm pores in the original). 0.4–1 µm pores for barrier
  assays; 3–8 µm when transmigration is part of the model.
- ECM coating (collagen I/IV, fibronectin, Matrigel) per cell type; both
  faces if both are seeded.
- TEER electrodes integrate naturally across the membrane (see
  [sensing-and-detection.md](sensing-and-detection.md)).
- Cyclic stretch: vacuum side-channels flanking the culture lane strain the
  membrane (~5–15% at 0.2–1 Hz in the lung chip); stretchability is a PDMS
  exclusive — none of the rigid thermoplastics do this.

## Spheroids and organoids on chip (pointers)

U-bottom microwell arrays (sedimentation loading), hanging-drop networks, and
trap arrays (`particle_separation.py trap` scales to spheroid traps with the
same bypass-ratio rule). Size spheroids ≤ ~200 µm radius or budget the
diffusion-limited core explicitly (the O₂ tool's arithmetic applied at the
spheroid scale: R²·OCR_volumetric/(6·D·C_surface) ≥ 1 means a hypoxic core).

## Material biocompatibility: the PDMS caveats

Three distinct, documented problems — decide *before* choosing PDMS:

1. **Small hydrophobic molecule absorption** (Toepke & Beebe 2006): PDMS bulk
   soaks up drugs/dyes with logP ≳ ~2 — dose–response curves shift by orders
   of magnitude. Countermeasures: thermoplastic or glass devices, parylene/
   sol-gel coatings, or measured effective concentrations.
2. **Uncrosslinked oligomer leaching** (Regehr 2009): PDMS oligomers enter
   the medium and cell membranes; mitigate by thorough cure and solvent
   extraction of the cured part.
3. **Vapour permeability**: evaporation through the bulk concentrates the
   medium in static µL volumes (also the reason on-chip reservoirs and
   humidified incubation are standard).

Berthier, Young & Beebe (2012) is the standard argument for moving from PDMS
to polystyrene/COC when a model matures — culture-vessel-equivalent surface
chemistry and no absorption, at the price of losing stretch and gas supply
through the roof.

## Sterility and practicalities

Autoclave: PDMS, glass, PC yes; PMMA no (Tg ~105 °C), COC grade-dependent —
EtO or UV+70% ethanol for thermoplastics (ethanol crazes PMMA: rinse fast).
Plan sterile fluidic connection (luer/barb assemblies autoclaved as a set),
bubble traps before the chip (a meniscus passing over a monolayer strips it),
and CO₂ buffering: PDMS-roofed chips equilibrate with incubator CO₂; sealed
thermoplastic chips need HEPES-buffered media.
