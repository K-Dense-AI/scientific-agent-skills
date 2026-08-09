# Electrokinetics: EOF, electrophoresis, DEP, and the heat they generate

Citations in [source-ledger.md](source-ledger.md) — chiefly Probstein, Kirby
(2010), Morgan & Green, Pethig (2010).

## Electroosmotic flow (EOF)

A charged wall + thin electric double layer + tangential field E drives the
Helmholtz–Smoluchowski slip velocity:

    u_eof = ε₀ ε_r ζ E / µ

(`electrokinetics.py eof`; magnitude, direction set by ζ's sign — glass at
neutral pH is negative, so flow runs toward the cathode).

Design properties:

- **Plug profile**: no shear dispersion — the reason CE resolution is high.
  Valid when the Debye length is ≪ channel (thin-EDL; check `debye`).
- Flow rate Q = u_eof·w·h is *independent of channel length* at fixed E, but
  the voltage to hold E scales with length: 100 V/cm over 3 cm is 300 V.
- ζ values are surface- and buffer-dependent (table in
  `assets/fluid-and-material-data.md`): glass ≈ −90 mV, PDMS ≈ −68 mV at
  ~pH 7, 1 mM. A hybrid glass/PDMS channel has non-uniform ζ → recirculation.
- ζ collapses with ionic strength (∝ ~1/√I) and with adsorbed protein;
  dynamic coatings (PEO, PVA) or covalent PEG suppress EOF when it is
  unwanted.

## Joule heating — the EOF budget that gets skipped

Volumetric heating q = σE². The tool's estimate ΔT ≈ σE²·wh/(2k_substrate) is
a 1D conduction scaling (factor 2–3 honest); it gates at
`--max-temp-rise` (default 5 K). Consequences of ignoring it: bubbles,
viscosity (hence mobility) gradients, sample denaturation, runaway at
constant-voltage drive.

Design levers, in order: lower σ (dilute buffer — but ζ and cells care),
lower E, thinner/shallower channels (better surface/volume), glass or silicon
instead of PDMS (k: 1.1 / 149 vs 0.16 W/m·K).

Electrode practicalities: electrolysis at DC generates bubbles and pH drift
at the reservoirs — keep electrodes in large reservoirs away from channels,
or use salt bridges.

## Electrophoresis (brief)

Particle/molecule drift u_ep = µ_ep·E adds to (or opposes) EOF; observed
mobility is the sum. Small-molecule/protein separations are the domain of CE
methods development, not chip sizing — this skill only budgets the field,
current, and heat with the same `eof` tool.

## Dielectrophoresis (DEP)

A polarisable particle in a *non-uniform* field feels

    F_DEP = 2π ε_m ε₀ a³ Re[CM] ∇|E|²

with the Clausius–Mossotti factor CM = (ε_p* − ε_m*)/(ε_p* + 2ε_m*),
ε* = ε − jσ/ω. Re[CM] ∈ [−0.5, 1] (`electrokinetics.py dep` computes it from
the complex permittivities).

- **Sign**: Re[CM] > 0 → positive DEP, toward field maxima (electrode edges);
  < 0 → negative DEP, toward minima (gaps, cages). Low frequency is
  conductivity-dominated, high frequency permittivity-dominated; the
  crossover frequency is the classic label-free discriminator (viable vs
  non-viable cells differ in membrane conductivity).
- **Physiological buffers (σ ≈ 1.6 S/m) force negative DEP for cells** and
  cook them by Joule heating at trapping fields; low-σ isotonic buffers
  (sucrose/dextrose) enable pDEP but stress cells — viability-check.
- ∇|E|² is set by electrode geometry, decaying over ~the electrode gap;
  reachable values 10¹²–10¹⁷ V²/m³. Compute it for the actual geometry (FEM)
  — the tool takes it as input and checks trap-vs-drag against the flow.

## Debye length and nanochannels

    λ_D ≈ 0.304 nm / √I(M)    (1:1 electrolyte, 25 °C; Kirby 2010)

1 mM → ~10 nm; 100 mM → ~1 nm. When 2λ_D approaches the smallest channel
dimension (overlap, `debye` warns at >10%), bulk electroneutrality fails:
ion-permselectivity, concentration polarisation (ICP), and nonlinear
current–voltage behaviour appear. That regime (nanofluidic preconcentration,
ICP desalting) is beyond these design formulas — the tool only tells you that
you are entering it.

## AC electrokinetics beyond DEP (pointers)

AC electroosmosis and electrothermal flow stir fluid near electrodes below
~100 kHz in conductive media; induced-charge EO around polarisable posts.
These matter as *artifacts* in DEP devices as much as actuators — Morgan &
Green treat them fully.
