# Valves, on-chip pumps, and flow control

On-chip valving (Quake/pneumatic), on-chip peristaltic pumping, and the
off-chip flow-control dynamics that decide whether the chip sees the flow you
set. Citations in [source-ledger.md](source-ledger.md) (Unger 2000; Thorsen
2002; Studer 2004).

## Quake (pneumatic membrane) valves — Unger 2000

Two-layer PDMS: a control channel crosses a flow channel, separated by a thin
membrane; pressurising the control line deflects the membrane into the flow
channel.

### The non-negotiable rule

**The flow channel must have a rounded profile.** A rectangular flow channel
leaves open corners at any pressure — the valve leaks forever. Rounded
profiles come from reflowed positive photoresist (e.g. AZ 50XT/SPR-220
baked past reflow). `valve_pump_design.py quake --flow-profile rectangular`
exits 1 by design.

### Closing pressure estimate

Small-deflection clamped-plate bending gives the tool's estimate:

    P_close ≈ h_flow · E · t³ / (0.00406 · w_control⁴)

(centre deflection δ = 0.00406·P·w⁴/(E·t³) set equal to the flow height).
Typical numbers — w_c = 100–300 µm, t = 10–30 µm, h_f = 10 µm, E ≈ 1 MPa —
land at 10–80 kPa, matching practice. Honest caveats: deflection ≈ t leaves
the small-deflection regime, E of PDMS spans 0.5–3 MPa with cure ratio and
bake — **calibrate the real closing pressure on a test chip**, and drive at
~1.5× closing. The tool also fails designs whose estimate exceeds what
plasma-bonded PDMS survives (~200 kPa).

Scaling (Studer 2004): closing pressure drops with wider control lines and
thinner membranes; response time (~ms) rises with control-line volume — long
control lines through small tubing are the usual latency culprit.

### Multiplexed large-scale integration — Thorsen 2002

Binary demultiplexer: 2·log₂(N) control lines address N flow lines (the tool
reports the count). This is what made 1000-chamber chips practical; layout
cost is the control-line crossings, so plan the two layers together.

## On-chip peristaltic pumps

Three valves in series actuated in a 6-phase pattern meter

    Q ≈ (displaced volume per stroke) × f_actuation

(`peristaltic`; default displacement 0.5× the valve footprint volume). nL/min
to µL/min, robust against downstream resistance changes (it is a positive-
displacement pump), pulsatile at f. Rate saturates when pneumatic response
(~10 ms) approaches the phase time.

## Off-chip pump selection

| Drive | Controls | Response | Pulsation | Failure mode to design for |
| --- | --- | --- | --- | --- |
| Syringe pump | Q | slow (RC) | stepper steps at low rates | compliance makes "set Q" a lie for ~3τ |
| Pressure controller | p | ms | none | Q = p/R drifts as R fouls — measure or sense Q |
| Gravity head | p | instant | none | head drains; ~1 cm water = 98 Pa |
| On-chip peristaltic | Q | ms–s | at f_act | fabrication complexity |
| Capillary/centrifugal/EOF | — | — | — | see their own references |

## RC dynamics: the part everyone feels but few compute

τ = R_hyd·C_total (`flow-control` computes τ, 95% settling = 3τ, and
pulsation attenuation 1/√(1+(2πfτ)²)).

Compliance sources, roughly in order: air bubbles trapped anywhere (by far
the largest — a 1 µL bubble at 10 kPa contributes ~1e-11 m³/Pa), soft tubing
(silicone/Tygon), the syringe plunger seal, PDMS channel ballooning. A glass
chip fed by PEEK tubing from a pressure controller settles in ms; the same
chip in PDMS on a syringe pump through silicone tubing can take minutes at
nL/min rates.

Design uses, not just nuisances: a deliberate RC (membrane reservoir or
air-cushion) low-pass-filters syringe pulsation; the tool sizes the
attenuation.

## Bubbles: the universal failure mode

A bubble is a compliance bomb and a shear hazard (a moving meniscus strips
adherent cells). Countermeasures that belong in the *design*, not the
protocol: degas media, prime through a bubble trap (a tall-roof chamber the
bubble rises into, or a hydrophobic-membrane vent), avoid unswept dead-end
corners (fillet junctions), keep PDMS pre-soaked/degassed for dead-end
filling, and give every chamber a sweep path. For long cell-culture runs, an
in-line bubble trap upstream of the chip is standard equipment.
