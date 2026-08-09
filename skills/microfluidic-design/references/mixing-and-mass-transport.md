# Mixing and mass transport design

At microfluidic Reynolds numbers there is no turbulence: two streams meeting
in a channel flow side by side and mix only by transverse diffusion. Every
passive mixer is a way of shortening the diffusion path or folding the
interface. Citations in [source-ledger.md](source-ledger.md).

## Diffusivities

See the table in `assets/fluid-and-material-data.md` (small molecules ~5×10⁻¹⁰,
proteins ~5×10⁻¹¹ m²/s). Temperature scaling is Stokes–Einstein:
D ∝ T/µ(T), so water at 37 °C diffuses ~1.35× faster than at 25 °C.
`_common.stokes_einstein_d()` computes D for a sphere of known radius.

## The mixing model the scripts use (stated convention)

Two streams split the channel width w at the inlet (step concentration
profile). With no-flux side walls, the deviation from the mixed state expands
in cosine modes; the k-th mode decays as exp(−(kπ/w)²·D·t). Keeping the
slowest (k = 1) mode and normalising by the initial mean deviation:

    unmixed(t) = (8/π²) · exp(−π² D t / w²)

"90% mixed" means unmixed = 0.1, giving

    t_mix = (w²/π²D) · ln(8/(π²·0.1)) ≈ 0.21 · w²/D
    L_mix = U · t_mix        (straight channel)

Notes on the convention:

- The prefactor 8/π² comes from the L1 norm of the step's slowest mode; other
  papers use variance-based definitions, which shift the constant, not the
  scaling. State the definition when reporting.
- L_mix/w ≈ 0.21·Pe — the linear-in-Pe cost that makes straight-channel mixing
  hopeless at Pe ≳ 10³ (centimetres to metres).
- Vertical (h) mixing is faster than lateral when h < w; the w-based number is
  the conservative, design-relevant one for side-by-side streams.

`mixing_length.py length` implements exactly this and refuses (exit 1) when a
stated length budget cannot be met by a straight channel.

## Mixer selection

| Situation | Mixer | Rule of thumb |
| --- | --- | --- |
| Pe < ~10 | none needed | streams mix within ~w of travel |
| Pe 10–10³, length available | straight or serpentine-in-plane | L ≈ 0.21·Pe·w |
| De > ~1 reachable (fast flow, tight bends) | serpentine **Dean** mixer | secondary vortices fold the interface each bend |
| Pe 10³–10⁶, length constrained | **staggered herringbone** (SHM) | mixing length grows as ln(Pe), not Pe |
| Two streams, one-shot, no features | flow lamination (split-and-recombine) | n splits cut t_mix by n² |

### Staggered herringbone design rules (Stroock 2002)

- Grooves on the channel floor at ~45° to the axis; groove depth ≈ 0.23–0.3 ×
  channel height; groove pitch ≈ ½–1 × channel width.
- Asymmetric arms (≈ 1/3 – 2/3 split) swapped every half-cycle of ~6 grooves.
- Published performance: complete mixing in ~1.5 cm at Pe up to 9×10⁵ in a
  200 µm channel — length ∝ ln(Pe) over Pe = 2×10³–9×10⁵.
- SHM grooves add a second lithography layer; budget the alignment step.

## Gradient generators (Christmas tree, Dertinger 2001)

`mixing_length.py gradient` sizes the tree:

- Two inlets (c = 0, 1) feeding a cascade; after s serpentine-mixing stages
  the (s+1) outlets carry a linear profile c_i = i/s.
- **Each stage must mix completely** — the tool sizes the per-stage serpentine
  for 95% mixed; an under-mixed stage corrupts every downstream branch.
- All branches at a level must carry equal flow: keep their resistances equal
  (same length/width/height) and remember the h³ sensitivity.
- The profile holds only while both inlets run at equal, steady flow.

## H-filter (Brody & Yager 1997)

Two co-flowing streams; small molecules diffuse across, cells/large species
stay. `mixing_length.py h-filter` computes the transferred fraction of each
species from the full mode series:

    f(t) = 1/2 − Σ_{k odd} (4/(kπ)²) · exp(−(kπ/w)²·D·t)

Design targets: residence time t = L/U such that f_fast → ~0.4–0.5 while
f_slow stays ≲ f_fast/2 (the tool's selectivity gate). It is an extraction,
not a filter: yield tops out at 50% per pass into the receiving stream.

## Residence-time distribution caveat

Poiseuille flow means the centreline moves ~2× the mean: a "10 s incubation"
channel delivers 5–20 s depending on streamline (worse with Taylor–Aris
dispersion, see [governing-equations.md](governing-equations.md)). Where
residence uniformity matters, use droplet (segmented) flow — each droplet is a
well-stirred batch reactor with a sharp residence time — or accept and report
the distribution.
