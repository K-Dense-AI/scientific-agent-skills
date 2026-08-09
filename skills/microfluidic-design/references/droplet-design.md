# Droplet microfluidics design

Water-in-oil droplets as picolitre reactors: monodisperse, well-stirred, with
sharp residence times. This file covers generator design; downstream
operations get pointers only. Citations in [source-ledger.md](source-ledger.md).

## Regimes: the continuous-phase capillary number decides

Ca = µ_c·U_c/γ, with U_c the continuous-phase mean velocity at the junction
and γ the (surfactant-laden) interfacial tension.

| Regime | Ca (approx.) | Behaviour | Size set by |
| --- | --- | --- | --- |
| Squeezing | ≲ 0.015 | droplet blocks the junction, pressure pinches | geometry + flow ratio |
| Dripping | ~0.015–0.1 | viscous shear pinches before full blocking | Ca and flow ratio |
| Jetting | ≳ 0.1 | a jet extends, breaks by Rayleigh–Plateau | instability — polydisperse |

Boundaries are approximate (De Menech 2008 located squeezing→dripping near
Ca ≈ 0.015 for T-junctions); treat ±50% on the thresholds and map your own
device. `droplet_generator.py` classifies and **fails (exit 1) in jetting** —
there is no monodisperse prediction there.

## T-junction, squeezing (Garstecki 2006)

    L_plug / w = 1 + α · Q_d/Q_c ,   α ≈ 1–1.5 (default 1.1)

- Size is set by *geometry and flow-rate ratio*, nearly independent of γ and
  µ — the robust regime for metering.
- Plug volume: the tool uses the full cross-section body with quarter-round
  end caps (first-order correction; ±10% class).
- Generation frequency f = Q_d/V_droplet; squeezing typically runs 1–10³ Hz.

## Flow-focusing (Anna 2003; Christopher & Anna 2007)

Dripping-regime droplet diameter is of the orifice scale, shrinking with Ca
and with the continuous-phase flow fraction. The bundled scaling

    d ≈ w_orifice · (Q_d/(Q_d+Q_c))^{1/3} · Ca^{−0.2}   (capped at 2·w_orifice)

is an engineering estimate, stated with ±30% uncertainty — flow-focusing sizes
depend on the full junction geometry. Calibrate on your device; treat the
tool's number as the starting grid point. Frequencies reach 10⁴–10⁵ Hz before
jetting.

## Fluid pairs and surfactants

| System | µ_c (mPa·s) | γ with surfactant | Surfactant | Notes |
| --- | --- | --- | --- | --- |
| Water in mineral/silicone oil | 10–70 | ~3–10 mN/m | Span 80, 2–5% w/w | cheap; slowly swells PDMS |
| Water in HFE-7500 | 1.24 | ~1–5 mN/m | PEG–PFPE ("EA"/008-F), 1–2% | biocompatible standard for cell work; no PDMS swelling |
| Water in FC-40 | 4.1 | ~1–5 mN/m | PEG–PFPE | denser oil; droplets float |

- Surfactant is not optional: bare interfaces coalesce at the first pincer or
  incubation step. Kinetics matter too — freshly formed interfaces are not yet
  stabilised (Baret 2012).
- Fluorinated oils dissolve enough O₂/CO₂ for droplet cell culture; mineral
  oil does not.
- PDMS swelling: silicone and mineral oils swell PDMS measurably; fluorinated
  oils essentially none (Lee, Park & Whitesides 2003 ranks solvents).

## Wetting is a hard requirement

The continuous phase must wet the channel. Native PDMS/hydrophobic surfaces →
water-in-oil. Oil-in-water needs hydrophilic walls (plasma + immediate use,
PVA coating, or glass). A junction with mixed wetting makes polydisperse mush;
droplets touching a wall they wet will smear and merge.

## Encapsulation statistics

Cell loading is Poisson: P(k) = λᵏe^(−λ)/k!, λ = c_cells·V_droplet.
`droplet_generator.py --cell-concentration` reports empty/singlet/multiplet
fractions. Single-cell work runs λ ≈ 0.05–0.3, accepting ~75–95% empties;
beating Poisson needs inertial ordering or close-packed loading
(Collins 2015 reviews the options).

## Other design notes

- **Satellites**: pinch-off sheds sub-µm satellite droplets; they contaminate
  sorting gates and fluorescence baselines.
- **Droplet traffic**: a droplet raises the resistance of the channel it
  occupies; trains in loops pick paths dynamically and can oscillate. The
  network solver here is single-phase — do not feed it droplet-laden segments.
- **Pressure vs syringe drive**: pressure control reaches steady generation in
  seconds and is quieter; syringe pumps oscillate at low rates (stepper
  pulsation maps directly onto droplet size).
- **Incubation**: delay lines widen residence-time spread as droplets pass
  each other; deep wide channels with herringbone-like mixing of the carrier
  or on-chip reservoirs are the usual fixes.

## Downstream operations (pointers only)

Pico-injection (electric-field-triggered reagent addition), droplet merging,
dielectrophoretic sorting (FADS), splitting at junctions, ddPCR readout —
all established; all need their own design passes beyond this skill's scope.
