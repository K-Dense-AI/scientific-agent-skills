# Particle and cell manipulation design

Label-free hydrodynamic methods (DLD, inertial, sheath, traps) plus
magnetophoresis; acoustics has [its own file](acoustofluidics.md) and
electrokinetic DEP lives in [electrokinetics.md](electrokinetics.md).
Citations in [source-ledger.md](source-ledger.md).

## Choosing a technique

| Technique | Size range | Throughput | Label-free | Dense samples (blood) | Notes |
| --- | --- | --- | --- | --- | --- |
| DLD | 0.1–30 µm | µL–mL/min | yes | diluted | sharpest size cutoff |
| Inertial (straight/spiral) | 2–30 µm | mL/min | yes | diluted 10–100× | highest throughput |
| Acoustophoresis | 1–20 µm | 10–100 µL/min | yes | moderate | gentle; density/compressibility contrast |
| Sheath focusing | any | any | yes | yes | positions, does not separate |
| Hydrodynamic traps | one cell/trap | n/a | yes | no | arrays for imaging |
| Magnetophoresis | bead-bound | µL–mL/min | no (labels) | yes | specificity from the label |
| DEP | 1–20 µm | low | yes | low-σ buffer needed | frequency-tunable |
| Viscoelastic focusing | 0.1–10 µm | µL/min | yes | polymer additive | pointer only |

## Deterministic lateral displacement (Huang 2004; Inglis 2006; Davis 2006)

Array of posts, each row laterally shifted by fraction ε of the pitch.
Particles above the critical diameter D_c "bump" along the post axis;
smaller ones zigzag with the flow.

**The design rule** (Davis 2006 empirical fit, used by
`particle_separation.py dld`):

    D_c = 1.4 · g · ε^0.48

with g the clear gap and ε the row-shift fraction (= 1/N for period N).
Validity: circular posts, ε ≈ 0.01–0.1.

Design procedure:

1. Put D_c between the two populations (e.g. 2× apart in size → D_c at the
   geometric mean).
2. Choose ε (smaller ε → sharper cutoff, longer array); get g from the rule.
3. **Check g > largest particle in the sample** — D_c is a deflection
   threshold, not a sieve; the tool exits 1 on this because it is the classic
   clogging mistake.
4. Depth ≥ ~2× the largest particle so nothing wedges against the roof.
5. Array length: bumped particles walk at angle θ = atan(ε); the array must be
   long enough for the lateral walk to clear the outlet splitter:
   L ≥ Δy_needed/ε.
6. Triangular posts lower D_c for the same gap (Loutherback 2010) — useful
   when clogging forces a bigger gap.

Practicalities: diluted blood (1:5–1:20) for cell work, BSA or pluronic
passivation against fouling, and mind diffusion for D_c < ~1 µm (the cutoff
blurs as Pe drops).

## Inertial focusing (Di Carlo 2007, 2009)

At Re ~ 10–300, shear-gradient and wall lift push particles to equilibrium
positions (~0.6× half-width from the centre; a rectangular channel has 2–4
positions, fewer at higher aspect ratio).

Gates and sizing (`particle_separation.py inertial`):

- **a/D_h ≥ 0.07** or focusing effectively never completes (hard exit 1).
- Particle Reynolds Re_p = Re·(a/D_h)² ≳ 0.1 for meaningful migration.
- Focusing length L_f = πµH²/(ρU_max·a²·f_L), f_L ≈ 0.05 near walls (0.5 near
  centre); the tool uses the conservative 0.05.

**Spirals**: Dean vortices (De = Re√(D_h/2R_c)) add a size-dependent drag
that differentiates equilibrium positions — bigger particles sit nearer the
inner wall. The tool reports De, the empirical Dean velocity
U_D ≈ 1.8×10⁻⁴·De^1.63 (SI), and the lift/Dean-drag ratio; design so that
ratio ~ O(1–10) for the target particle and ≪ 1 for the waste stream.
Order-of-magnitude only — spiral sorters are tuned empirically.

## Hydrodynamic sheath focusing

Two sheath streams pinch the sample to width

    w_f ≈ w · Q_sample/(Q_sample + Q_sheath)

(`particle_separation.py sheath`). 2D only: vertical focusing needs extra
geometry (chevrons/grooves) or a second junction. Flow-ratio, not absolute
rate, sets the width — so both pumps must be stable *relative to each other*.

## Single-cell hydrodynamic traps (Tan & Takeuchi 2007)

A trap pocket on a main channel, with a bypass loop. Design rule
(`particle_separation.py trap`): the **bypass path must have higher
resistance than the trap path** (R_bypass/R_trap > 1, margin 1.5–3× in
practice), so the streamline enters the trap. An occupied trap is plugged by
its cell, diverting flow to the bypass — the array self-loads. Keep trap
constriction ~0.5× cell diameter, and shear at the trap below the cell's
tolerance (check with `channel_resistance.py channel --target-shear`).

## Magnetophoresis (Pamme 2006)

Bead velocity from force balance with Stokes drag:

    v = Δχ · V_bead · (B·∇B) / (µ₀ · 3πµd)

(`particle_separation.py magnetic`). Δχ for superparamagnetic beads ~0.1–1
(SI, bead-volume basis — data sheet); B·∇B near an NdFeB magnet edge
10–1000 T²/m, decaying over ~the magnet's smallest dimension. Design the
crossing time (w/v) shorter than residence, same pattern as acoustophoresis.
Specificity comes entirely from the bead label chemistry.

## Viscoelastic focusing (pointer)

Dilute polymer (e.g. PEO) in the carrier focuses particles to the centreline
at arbitrarily low Re, including sub-µm sizes. Requires additive
compatibility with the assay; not covered by this skill's tools.
