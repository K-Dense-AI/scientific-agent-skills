# Governing equations for pressure-driven microfluidic design

All formulas assume steady, incompressible, Newtonian, laminar flow in rigid
channels. Sources: Bruus, *Theoretical Microfluidics* (2008); Squires & Quake
(2005); Stone, Stroock & Ajdari (2004) — full citations in
[source-ledger.md](source-ledger.md).

## When the assumptions hold

- **Laminar**: Re = ρUD_h/µ < ~2000. Microchannels almost always sit at
  Re 10⁻³–10²; turbulence is essentially unreachable, which is why mixing is
  hard and why every formula here is usable at all.
- **Newtonian**: water, buffers, oils, plasma — yes. Whole blood, polymer
  solutions, cell-dense suspensions — no. `_common.py` deliberately makes the
  `whole-blood` preset noisy.
- **Rigid**: PDMS channels balloon measurably above ~10 kPa (see compliance,
  below).
- **Continuum**: for gases check Kn = λ/L_min; slip corrections start at
  Kn ≈ 0.01 (air: λ ≈ 68 nm at 1 atm).

## Hydraulic resistance

Definition: Δp = R_hyd · Q — the design-level Ohm's law.

### Rectangular channel (exact)

For width w ≥ height h (swap if needed; the solution is symmetric):

    R_hyd = 12 µ L / (h³ w) × [1 − (192 h)/(π⁵ w) Σ_{n=1,3,5,…} n⁻⁵ tanh(nπw/2h)]⁻¹

(Bruus 2008, eq. 3.53 rearranged.) The series converges as n⁻⁵; the bundled
`rect_resistance()` uses 101 odd terms, far beyond double precision.

Worked check (pinned in the test suite): a **square** channel (w = h) gives

    R_hyd ≈ 28.45 µ L / h⁴

### Common approximation and its error

    R_hyd ≈ 12 µ L / [w h³ (1 − 0.63 h/w)]

| h/w | error vs exact |
| --- | --- |
| 0.1 | < 0.01% |
| 0.3 | ~0.03% |
| 0.5 | ~0.15% |
| 1.0 | ~13% (the 0.63 form is not built for squares) |

`channel_resistance.py` prints both and the % difference so the report can
state the bound. Never use the **circular** Hagen–Poiseuille formula with an
"equivalent diameter" for wide rectangles — that is a ~40% class error.

### Other cross-sections

- Circle, radius r: R = 8µL/(πr⁴)
- Parallel plates (w ≫ h): R = 12µL/(wh³)
- Shallow isotropic etch (semi-elliptical, glass): within ~10% of the
  parallel-plate value at the same area for w ≫ d; treat exactly only with FEM.

### The h³ (and h⁴) sensitivity

R ∝ h⁻³ for wide channels: a ±10% height error moves resistance −27%/+37%.
SU-8 spin thickness commonly varies ±5–10% across a wafer. Any resistance-
ratio-based design (splitters, traps, gradient trees) should be checked at
h × 0.9 and h × 1.1 — the checklist in `assets/design-checklist.md` demands it.

## The electrical analogy and networks

| Hydraulic | Electrical |
| --- | --- |
| Pressure p | Voltage V |
| Flow rate Q | Current I |
| R_hyd | Resistance R |
| Compliance C = dV_stored/dp | Capacitance C |

Series resistances add; parallel conductances add. `channel_resistance.py
network` assembles the nodal conductance matrix from a JSON netlist and solves
it exactly (Gaussian elimination) — Kirchhoff at every node, one pressure
reference required.

**Compliance and transients.** A syringe pump feeding a chip through soft
tubing forms an RC circuit: τ = R_hyd·C. PDMS channels themselves add
C ≈ dV/dp from wall bulging (scales with L·w²/E·(w/h) for wide channels — soft
walls, big channels, big compliance). Consequences:

- flow at the chip lags a setpoint change by ~3τ (95% settling);
- stopping the pump does not stop the flow (stored volume discharges);
- pump pulsation is low-pass filtered with attenuation 1/√(1+(2πfτ)²) —
  `valve_pump_design.py flow-control` computes both numbers.

## Velocity, shear, transit

- Mean velocity U = Q/(wh); peak (centreline) velocity from the exact series
  (Bruus 2008 eq. 3.48): ratio u_max/U runs from 1.5 (parallel plates) to
  ~2.1 (square).
- **Wall shear stress**, centre of the wide wall: τ = 6µQ/(wh²) — the
  parallel-plate result, adequate for h/w ≤ 0.3 and an upper bound beyond.
  This τ (at the wall) is the number cells feel; the *mean* shear rate is
  lower — quoting the wrong one is a standing error in organ-on-chip papers.
- Transit (residence) time t = L/U for a plug; the *distribution* is broad in
  Poiseuille flow (see Taylor–Aris below).
- Entrance length: Le ≈ [0.6/(1+0.035·Re) + 0.056·Re]·D_h. At Re < 1 this is
  under one D_h — profiles develop almost instantly; at Re ~ 100 it reaches
  ~6 D_h and junction losses start to matter.

## Dimensionless numbers with design thresholds

| Number | Definition | Design reading |
| --- | --- | --- |
| Re = ρUD_h/µ | inertia/viscous | < 1 Stokes; 20–150 inertial focusing band; > 2000 stop |
| Pe = Uw/D | advection/diffusion | > 10³: straight-channel mixing impractical |
| Ca = µU/γ | viscous/interfacial | droplet regimes: ≲0.015 squeeze, ≲0.1 drip, above jet |
| We = ρU²D_h/γ | inertia/interfacial | > 1: inertial breakup possible |
| Wo = (D_h/2)√(2πfρ/µ) | pulsatile | < 1: quasi-steady Poiseuille follows the pulse |
| De = Re√(D_h/2R_c) | curved channels | > 1: Dean vortices usable (mixers, spirals) |
| Bo = Δρ·g·w²/γ | gravity/interfacial | < 1: density mismatch tolerable in droplets |
| Kn = λ/L | gas rarefaction | > 0.01: slip corrections needed |
| Re_p = Re·(a/D_h)² | particle inertia | ≳ 0.1: inertial migration active |

`dimensionless_numbers.py` computes all of these with one-line readings.

## Taylor–Aris dispersion

A solute plug in Poiseuille flow spreads with effective axial diffusivity

    D_eff = D (1 + Pe²/210)   (circular tube; rectangular prefactors differ by O(1))

(Taylor 1953; Aris 1956). At Pe = 100, D_eff ≈ 49·D: axial dispersion, not
molecular diffusion, sets the width of injected sample plugs and the
residence-time distribution in long channels. Sharp-pulse assays and
sequential-reagent protocols must budget for it.

## Inertial lift (used by `particle_separation.py inertial`)

Near-wall shear-gradient and wall-repulsion lift on a particle of diameter a
in a channel of relevant dimension H (Di Carlo 2007, 2009):

    F_L = f_L · ρ · U_max² · a⁴ / H²

with f_L ≈ 0.05 near the wall (≈ 0.5 near the centreline) for Re < 100.
Balancing lateral migration u_L = F_L/(3πµa) against transit gives the
focusing length

    L_f = π µ H² / (ρ U_max a² f_L)

Feasibility gate: a/D_h ≥ 0.07, channel Re ~ 10–300. Below the gate the lift
never beats diffusion and drag within a practical chip length.

## What this file does not cover

Two-phase pressure drop (droplet trains raise apparent resistance),
non-Newtonian rheology, elastic-wall FSI, and anything requiring the full
Navier–Stokes solution — those need CFD (`fluidsim` skill) or experiment.
