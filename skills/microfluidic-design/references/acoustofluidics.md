# Acoustofluidic design: bulk and surface acoustic wave manipulation

Gentle, label-free particle manipulation by ultrasound standing waves.
Primary sources: the Bruus acoustofluidics tutorial series (Lab Chip 2011–12),
Laurell (2007), Settnes & Bruus (2012) — see
[source-ledger.md](source-ledger.md).

## Half-wave bulk resonator (BAW) — the workhorse

A channel of width w in a hard material driven at

    f = c_medium / (2w)

holds a pressure standing wave with a node at the centre. Water, w = 375 µm →
f ≈ 2.0 MHz (`particle_separation.py acoustic` computes this and everything
below).

**Material rule**: BAW needs acoustically hard walls (silicon, glass) to
reflect the wave. **PDMS absorbs ultrasound** — a PDMS BAW resonator simply
heats. With PDMS chips use SAW (below).

## Which way particles move: the contrast factor

Gor'kov potential coefficients for a small sphere (a ≪ λ) in a standing wave:

    f₁ = 1 − κ_p/κ_m         (monopole, compressibility)
    f₂ = 2(ρ̃ − 1)/(2ρ̃ + 1)   (dipole, density),  ρ̃ = ρ_p/ρ_m
    Φ  = f₁/3 + f₂/2

κ = 1/(ρc²). Φ > 0 → node (channel centre): cells, polystyrene, most rigid
particles. Φ < 0 → antinode (walls): lipids, bubbles, oils — the basis of
lipid/cell separation in blood processing. Polystyrene in water: Φ ≈ 0.22
(pinned in the tests).

## Radiation force and migration time

Peak axial radiation force in a 1D standing wave of energy density E_ac:

    F_max = 4π Φ k a³ E_ac ,   k = π/w

Balancing against Stokes drag and integrating wall→node (5%→95% of λ/4):

    t_mig = 3µ / (4Φ k² a² E_ac) · ln[tan(k·y₁)/tan(k·y₀)]

The a² scaling is the separation mechanism *and* the failure mode: half the
diameter, 4× the migration time. The tool gates t_mig against the residence
time L/(Q/wh) and exits 1 when the particle cannot traverse in time.

## Energy density is measured, not predicted

E_ac (typical 1–100 J/m³) depends on transducer coupling, bonding, resonator
Q — it cannot be derived from drive voltage. Calibrate by tracking a known
bead's migration (Bruus tutorial method) and re-derive E_ac; the tool's
default 10 J/m³ is a planning placeholder. Also budget transducer heating:
temperature drifts the resonance; production systems regulate temperature or
track the resonance.

## Design procedure (BAW separator)

1. Choose w from the frequency window of available transducers (1–10 MHz →
   w ≈ 75–750 µm in water).
2. Compute Φ for target and background particles; a separation needs either
   opposite signs or a usable t_mig contrast (∝ 1/a²Φ).
3. Set flow so the *target* migrates fully (t_mig < t_res) and the background
   does not (or exits by a different outlet fraction).
4. Sheath-load the sample at the walls (acoustic prefocusing or hydrodynamic
   sheath) so all particles start at the same place — otherwise the outlet
   split is blurry.
5. Split outlets: centre stream (focused) vs side streams; trifurcation
   ratios follow the resistance rules (`channel_resistance.py network`).

## SAW devices (pointer-level)

Interdigitated transducers (IDTs) on a piezoelectric substrate (LiNbO₃)
launch surface waves that refract into the fluid at the Rayleigh angle.

- **Standing SAW (SSAW)**: two opposing IDTs make a standing wave in a PDMS
  channel bonded to the substrate — the PDMS-compatible route (Ding 2012).
  Node spacing λ_SAW/2 with λ_SAW = c_substrate/f (c ≈ 3990 m/s on LiNbO₃).
- **Travelling SAW**: acoustic streaming and radiation for pumping, mixing,
  droplet actuation, atomisation.
- Design is dominated by IDT engineering (finger pitch sets f) and alignment
  of the channel to the standing-wave pattern.

## Beyond the formulas

Acoustic streaming (Rayleigh vortices at ~λ-scale) competes with radiation
force for particles below ~1–2 µm at MHz frequencies — sub-µm separation
needs streaming-suppressing geometries. Cell viability under acoustophoresis
is excellent at separation powers (repeatedly verified in the Lund
literature), one reason it is favoured for sensitive cells.
