# Centrifugal (lab-on-CD) and digital (EWOD) microfluidics

Two platform families that replace external pumps with a spin motor or an
electrode array. Citations in [source-ledger.md](source-ledger.md) (Madou
2006; Ducrée 2007; Cho & Fair 2003; Mugele & Baret 2005).

## Centrifugal: lab-on-a-disc

### The pressure source

A liquid column between radii r₁ and r₂ on a disc spinning at ω:

    Δp = ρ ω² · r̄ · Δr ,   r̄ = (r₁+r₂)/2, Δr = r₂−r₁

(`centrifugal_design.py pressure`). Scale: water, 3000 rpm, column from 20 to
30 mm radius → ≈ 24.6 kPa. Pressure rises with the *square* of spin speed and
linearly with radial position — the two design axes of the whole platform.

### Capillary burst valves

A hydrophobic constriction or sudden expansion holds until centrifugal
pressure beats its Young–Laplace barrier p_b:

    ω_burst = √( p_b / (ρ r̄ Δr) )

(`burst`, forward and inverse). Barriers of 0.5–5 kPa give burst speeds
conveniently inside 500–5000 rpm.

### Spin-programmed sequencing

The assay script is a spin profile: ramp up → valve 1 bursts (metering) →
spin down/up → valve 2 (mixing) → valve 3 (waste). `sequence` checks that
burst speeds ascend in the intended order with a margin (default 1.1×),
because contact-angle scatter of ±5–10° moves real burst speeds ~±10–20%
— measure on a test disc (Ducrée 2007).

Design levers per valve: barrier pressure (geometry/coating) *and radial
position* — moving a valve outward raises its driving pressure at fixed ω,
lowering its burst speed. Late events go outward or get stronger barriers.

### Other disc elements (pointers)

- **Siphon valves**: prime by capillarity at low spin (crest inside r_liquid),
  transfer when spun up — the standard "release inward" element; needs a
  hydrophilic channel.
- **Coriolis switching** at high spin routes flow left/right at a Y.
- Metering chambers, aliquoting trees, and sedimentation (plasma from whole
  blood in ~1 min at ~3000 rpm — the platform's signature strength; the RBC
  sediment interface radius sets the decant geometry).
- Everything is single-shot and radially ordered: layout is a radial Gantt
  chart — sample moves only outward (except siphons), so budget radius like a
  resource.

## Digital microfluidics: electrowetting on dielectric (EWOD)

Discrete droplets (nL–µL) stepped over an electrode array under a grounded
top plate; no channels at all.

### Lippmann–Young actuation

    cosθ(V) = cosθ₀ + ε₀ε_r V² / (2 t γ)

(`digital_microfluidics.py actuation`; the added term is the electrowetting
number). θ₀ ≈ 115° on the fluoropolymer topcoat; γ ≈ 40 mN/m against a
silicone-oil filler (72 mN/m in air).

Two hard limits the tool enforces:

- **Contact-angle saturation** (~60–80° floor, mechanism still debated —
  Mugele & Baret 2005): more voltage past saturation buys no more force.
- **Dielectric breakdown**: V must stay under `margin × t × E_bd`
  (default 30% of breakdown; Parylene C E_bd ≈ 2.7 MV/cm). Charging and
  breakdown, not saturation, are what kill devices — exit 1.

Motion needs the wetting-force difference to clear contact-angle hysteresis
(~2–10°; the oil filler lowers it, which is one of two reasons every serious
EWOD device runs under oil — the other is evaporation).

### Droplet operations (Cho & Fair 2003)

`ops` computes the unit volume (pitch² × gap) and flags feasibility:

- **Transport**: works broadly; droplet must overlap the next electrode
  (droplet diameter ≳ 1.2× pitch is comfortable).
- **Split / dispense-from-reservoir**: need a *small gap-to-pitch ratio* —
  ≤ ~0.1 is the standard design point; the neck cannot pinch in a tall gap.
- **Merge**: trivially easy — which cuts both ways (unintended merging).
- Dispensing reproducibility ~±2–5% with feedback (impedance sensing on the
  same electrodes), worse open-loop.

### Platform notes

AC drive (~1 kHz) mitigates dielectric charging and hysteresis vs DC.
Biofouling: proteins adsorb on the hydrophobic coat and pin droplets —
oil filler plus pluronic additives is the standard countermeasure. Thermal
cycling on-array (PCR) and magnetic-bead washes (hold beads, move droplet)
are the workhorse assay patterns.
