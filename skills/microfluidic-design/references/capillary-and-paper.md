# Capillary and paper microfluidics: pumping without pumps

Surface tension as the power supply: self-filling circuits, stop valves,
timed sequences — instrument-free devices. Citations in
[source-ledger.md](source-ledger.md) (Washburn 1921; Zimmermann & Delamarche
2007; Martinez 2007).

## Young–Laplace in a rectangular channel

Driving pressure of the meniscus (positive fills), per-wall contact angles:

    Δp = γ [ (cosθ_top + cosθ_bottom)/h + (cosθ_left + cosθ_right)/w ]

(`capillary_design.py pressure`). h is the small dimension, so the lid
dominates: a hydrophilic channel with a native-PDMS lid can refuse to fill.
Scale: γ = 72 mN/m, h = 50 µm, all-θ = 30° → Δp ≈ +3.1 kPa; all-θ = 110° →
−1.5 kPa barrier.

**Advancing vs receding**: filling is governed by advancing angles (higher),
emptying and bubble pinning by receding (lower). Design stop valves with the
advancing angle and drainage with the receding one. Plasma-treated PDMS
recovers hydrophobicity over hours–days — capillary circuits built on fresh
plasma treatment have a shelf life unless coated (PVA) or stored under water.

## Stop / burst valves

Two mechanisms, same math:

- **Hydrophobic patch**: a printed/patterned hydrophobic stripe creates a
  negative-Δp barrier.
- **Geometric (sudden expansion)**: the meniscus pins at an abrupt widening;
  the effective barrier follows from the expansion angle added to θ.

The valve holds while upstream pressure < barrier; `pressure
--applied-pressure` reports the burst margin and exits 1 when the intended
stop valve bursts. Trigger valves (two menisci meeting) release without any
pressure change — the basis of capillary sequencing logic.

## Washburn filling dynamics

Rectangular channel, same θ on all walls (`capillary_design.py filling`):

    L²(t) = Δp_cap · h² · (1 − 0.63 h/w) · t / (6µ)

(the classic tube form is L² = γ r cosθ·t/2µ). Front position ∝ √t: filling
slows as the wetted length grows — a 4× longer channel takes 16× longer to
fill. The √t law is also the metering principle of timed capillary steps.

## Autonomous capillary circuits (Zimmermann & Delamarche 2007)

A complete instrument-free device = loading pad → channel network → **capillary
pump** (the downstream structure whose fine features set the working pressure)
→ vent.

- Pump pressure: p ≈ 2γcosθ/r_smallest of the pump's post/tree structure —
  hundreds of Pa to a few kPa.
- **Flow rate is set by the pump pressure against the upstream resistance**:
  Q = p_pump/R_network (`capillary_design.py pump`). Keep the pump's own
  resistance ≪ network resistance so the designed R controls Q.
- Pump volume = assay volume budget; posts keep the wetted front advancing
  smoothly (no big-pore jumps).
- Everything is single-use and time-programmed: series pumps with different
  pore sizes give multi-rate profiles.

## Degas-driven flow (Hosokawa 2004)

Evacuate a PDMS device (vacuum desiccator, minutes); after venting, air
dissolves back into the bulk PDMS and drags liquid in — no surface treatment
needed, works with hydrophobic PDMS. Flow rate decays over ~minutes and
depends on PDMS volume and degassing history: fine for loading dead-end
chambers (digital PCR chips), wrong for controlled perfusion.

## Paper microfluidics / lateral flow (Martinez 2007; Yetisen 2013)

Porous media obey Washburn with r = effective pore radius (nitrocellulose:
capillary speeds ~1–4 cm within the first minute, grade-dependent).

- µPAD patterning: wax printing melted through the paper defines hydrophobic
  walls; channel width below ~300 µm is unreliable after wax spreading.
- Lateral-flow architecture: sample pad → conjugate pad → membrane with test/
  control lines → absorbent (wick) pad; the wick is the capillary pump, and
  membrane grade sets the assay's incubation-equivalent transit time.
- Design levers are geometric: widening/narrowing segments retime arrival;
  a 2D fan slows the front (√t in the fan's radial coordinate).

## Centrifugal microfluidics

Spinning-disc capillary valves and sequencing share this file's physics but
have [their own reference](centrifugal-and-digital.md) — burst conditions
there are the Young–Laplace barrier against ρω²r̄Δr.
