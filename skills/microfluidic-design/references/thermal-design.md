# Thermal design: heaters, transients, and PCR chips

On-chip temperature control for PCR, isothermal amplification (LAMP/RPA),
enzyme kinetics, and thermal gradients. Citations in
[source-ledger.md](source-ledger.md) (Kopp 1998 for flow-through PCR).

## Material thermal properties

See `assets/fluid-and-material-data.md`. The controlling contrast: PDMS/COC
k ≈ 0.13–0.16 W/m·K (insulators), glass 1.1, silicon 149. Substrate choice
*is* the thermal design.

## Steady heater sizing (`thermal_design.py heater`)

1D conduction from a heated zone through the substrate to a sink/ambient:

    P = k · A · ΔT / t_sub

plus, when fluid flows through the zone, the advective load

    P_fluid = Q · ρc_p · ΔT   (water: 69.7 mW per µL/min per 1000 K·— i.e.
                               ~2 mW per µL/min per 30 K)

Estimates only (factor ~2): lateral spreading and natural convection
(~10 W/m²·K) are unmodelled. Two design rules the tool prints:

- supply ≥ 2× the estimate and close the loop on a *measured* on-chip
  temperature (RTD trace or thermistor), never on heater power;
- for zone uniformity, the heater should overhang the zone by ~2× the
  substrate thickness on every side.

## Transients (`thermal_design.py transient`)

The layer of thickness t between heater and fluid responds on

    τ ≈ t² / α ,   α = k/(ρc_p)

Glass 700 µm: τ ≈ 0.8 s → ramps of ~30 K/0.8 s ≈ 37 K/s at best; PDMS 2 mm:
τ ≈ 35 s — cycling a static PDMS chamber from the outside is hopeless, which
is exactly why flow-through PCR exists. The tool gates a required ramp rate
against ΔT/τ.

Thin-film heaters *on* the fluid-facing surface (Pt/ITO traces) bypass the
substrate lag and reach 10²–10³ K/s in µL volumes — at the cost of cleanroom
metallisation.

## PCR chip architectures

| Architecture | Principle | Strength | Weakness |
| --- | --- | --- | --- |
| Static chamber cycler | one chamber, cycled thermally | simple fluidics | ramp-limited by τ |
| **Continuous-flow serpentine** (Kopp 1998) | fluid snakes across 3 fixed-T zones | ramp = transit between zones (ms–s); throughput | cycle count frozen in the layout |
| Oscillatory/shuttle | plug shuttled between zones | flexible cycles, small volume | control complexity |
| Digital PCR partitions | thousands of droplets/chambers, then cycle | absolute quantification | needs partitioning front-end |

### Continuous-flow sizing (`thermal_design.py pcr`)

Zone length per step = U × t_residence at the design flow; the tool sums
denaturation/annealing/extension per cycle, multiplies by cycle count, and
gates one cycle against the chip-length budget. Defaults (5/15/30 s) are
conservative bench times — fast chemistries run 1/5/10 s or less, which is
the main lever when the serpentine does not fit.

Layout notes: keep 1–2 mm of low-k material or an air gap between zones so
they do not short thermally; route the serpentine so each pass crosses zones
in the right order (denature → anneal → extend); watch Taylor–Aris dispersion
if amplicon plugs must stay separate, or run droplets (each droplet is a
clean PCR reactor — droplet PCR merges this file with
[droplet-design.md](droplet-design.md)).

## Evaporation and bubbles at temperature

At 95 °C everything outgasses and evaporates: pressurise the chip (~100–200
kPa backpressure raises the boiling point and keeps air dissolved), use
mineral-oil overlays on open chambers, and remember PDMS is water-vapour
permeable — a static PDMS PCR chamber loses volume percent-per-minute at
denaturation temperatures unless saturated or sealed (see the PDMS caveats in
[cell-culture-organ-on-chip.md](cell-culture-organ-on-chip.md), same physics).

## Temperature-gradient devices (pointer)

A hot and a cold rail across a thin substrate give a linear lateral gradient:
melting-curve analysis and thermal gradient focusing live here; design is the
same conduction arithmetic with two sinks.
