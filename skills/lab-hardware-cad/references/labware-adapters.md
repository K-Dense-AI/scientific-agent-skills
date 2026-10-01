# Labware adapters, holders, and racks

Parts that receive standard consumables: microplates, cuvettes, tubes, slides, dishes.

The governing principle: **where a published standard exists, design to the standard; where it
does not, require a measurement.** Microplate footprints are standardised. Well geometry, skirt
profiles, tube dimensions, and lid fits are not.

Verified dimensions live in `assets/standards.json`. Query them rather than copying numbers:

```bash
python scripts/check.py standards --show slas-microplate-footprint
```

## Microplates (ANSI/SLAS 1-4)

The four dimensions references below are the R2012 PDFs currently linked by SLAS.
They are subsets of the specification; read the relevant section and drawing for datum rules.

| Document | Governs | Key numbers |
| --- | --- | --- |
| ANSI/SLAS 1-2004 | Footprint | 127.76 x 85.48 mm ±0.50 overall, ±0.25 near corners; corner radius 3.18 ±1.6 mm |
| ANSI/SLAS 2-2004 | Height | 14.35 ±0.25 mm at perimeter wells; ±0.76 mm overall |
| ANSI/SLAS 3-2004 | Bottom outside flange | Short 2.41, medium 6.10, tall 7.62 mm, each ±0.38 |
| ANSI/SLAS 4-2004 | Well positions | 96-well: 9.0 mm pitch, A1 at 14.38 mm from left, 11.24 mm from top |

### Designing a plate pocket

Three traps, in the order people fall into them.

**1. Use the tolerance for the full interface.** The ±0.25 mm band applies only
within 12.7 mm of the corners. A continuous pocket needs the ±0.50 mm overall band.
The standard covers the base footprint; obtain the vendor body/draft envelope for a deep pocket.
Size to the maximum envelope, then add clearance and your process allowance. A plate at the top of tolerance is
127.76 + 0.50 = 128.26 mm. A pocket cut at 127.76 + clearance can bind on conforming plates. Compute:

```python
plate_l_mm = 127.76      # ANSI/SLAS 1-2004 nominal
plate_tol_mm = 0.50      # ANSI/SLAS 1-2004
fit_clearance_mm = 0.40  # per side; FDM, see fabrication-limits.md
pocket_l_mm = plate_l_mm + plate_tol_mm + 2 * fit_clearance_mm   # 129.06
```

**2. The corner radius tolerance is enormous — and it bounds the pocket radius from above,
not below.** 3.18 ±1.6 mm means a real plate corner is anywhere from 1.58 to 4.78 mm. Get the
direction right: a plate corner is **convex**, a pocket fillet is **concave material bulging
inward**, so a *sharp* internal pocket corner always clears a rounded plate — the unused corner is
empty space. It is a pocket fillet *larger* than the plate's corner radius that binds: the bulge
occupies space the plate needs. Sizing the fillet to the plate's maximum corner radius is
therefore exactly backwards — it binds every plate except those at the top of the corner
tolerance.

The safe options, best first:

- **Corner relief** (a small slot or bore cut past each corner) — always clears, prints and mills
  cleanly, and is the standard fix.
- **Fillet no larger than the plate's minimum corner radius** (1.58 mm for SLAS plates) — clears
  every conforming plate in every position.
- A larger fillet only if `R ≤ r_min + ~3.4 × per-side clearance` — the geometry only recovers the
  intrusion when the plate stays roughly centred, so treat this as a last resort and say so.

```python
with BuildPart() as pocket:
    # ... pocket geometry ...
    # relief bores just outside each pocket corner: clears any conforming corner radius
    with Locations(*corner_relief_centres()):
        Hole(radius=2.0)
```

**3. Height depends on the flange, not just the plate.** ANSI/SLAS 3 includes three uniform flange
heights, plus interrupted short flanges and dual-height variants. A carrier that grips the flange must be told which one. Ask; do not assume medium.

### Well grid

For a part that must reach individual wells — a magnet block, a lid with access holes, a light
guide — lay out from the plate's outline corner, not from the plate centre:

```python
a1_x_mm, a1_y_mm, pitch_mm = 14.38, 11.24, 9.0   # ANSI/SLAS 4-2004, 96-well
locations = [
    (a1_x_mm + pitch_mm * col, a1_y_mm + pitch_mm * row)
    for row in range(8) for col in range(12)
]
```

The standard's positional tolerance is a **0.70 mm diameter zone** around each nominal centre, not
a ±0.70 mm band. A feature that must clear every well needs at least 0.35 mm of radial margin on
top of your own process tolerance.

Directly verified in ANSI/SLAS 4 sections 4.2 and 4.3: 384-well pitch is 4.5 mm,
A1 offsets (12.13, 8.99) mm, position zone diameter 0.70 mm; 1536-well pitch is
2.25 mm, A1 offsets (11.005, 7.865) mm, position zone diameter 0.50 mm. Datum edges
are the near-corner zones, not a bowed side midpoint. These basic coordinates do
not imply zero manufacturing tolerance.

### What the standards do not fix

Well diameter, well depth, well bottom shape (flat, round, conical), skirt height, lid geometry,
optical bottom thickness, and deep-well plate height. All vary by manufacturer and product line.
If the part touches any of these, get the vendor drawing or measure it.

## Cuvettes

A common 10 mm path-length rectangular cuvette has a **12.5 x 12.5 mm external
footprint and 45 mm body height**, as illustrated by Hellma's catalogue. This is not
a universal standard. No shared ±0.1 mm envelope tolerance or uniform wall thickness
is established here; the database marks those nominal dimensions unverified for fit.

Design notes:

- Holders should be generous or compliant. Because no document fixes the tolerance, a 0.1 mm
  interference fit designed against nominal will fail on some suppliers' cuvettes.
- Semi-micro and micro cuvettes keep the 12.5 mm external footprint but change internal geometry
  and often height. Confirm the exact external envelope, cap and optical-window height; a common
  footprint alone does not establish interchangeability.
- Cuvettes are usually held with a spring or leaf on one face so the two optical faces register
  against fixed datums. Copy that: locate on two adjacent faces, preload from the opposite corner.
  A four-sided pocket with clearance lets the cuvette rotate and shifts the path length.
- **Never print the optical path.** Printed surfaces scatter. The cuvette provides the optical
  faces; the holder provides position only, and must not obstruct the beam window.

## Tubes

Tube dimensions are **not standardised** and differ measurably between suppliers, and often
between product lines from the same supplier. Approximate outside diameters near the tube rim:

| Tube | Approximate OD | Note |
| --- | --- | --- |
| 0.2 mL PCR | 6 mm | Often supplied in strips or as a 96-format plate |
| 1.5 mL microcentrifuge | 11 mm | Rim is wider than the body; the body tapers |
| 2.0 mL microcentrifuge | 11 mm | Same rim as 1.5 mL, taller body |
| 15 mL conical | 17 mm | Cap is wider than the tube |
| 50 mL conical | 30 mm | Cap is wider than the tube |

**Treat every number in this table as a starting point for a first article, not a design input.**
Ask the user for the supplier and catalogue number, or ask them to measure with calipers. Then
design a rack that holds the tube by the **rim or the cap**, which is dimensionally stable, rather
than by the tapered body, which is not.

For a rack, the useful pattern is a through-hole sized to the body plus clearance and a counterbore
that catches the rim, so the tube hangs rather than bottoms out.

## Microscope slides and coverslips

Slide sizes include approximately **75 x 25 mm and 76 x 26 mm**, with thickness
near 1 mm. ISO 8037-1:1986 is the slide dimensions reference; do not equate the two
commercial sizes. For example, BRAND labels its ISO 8037-1 slides approximately
76 x 26 mm. Use the actual product drawing. Coverslips also need both lateral size
and thickness: common #1 and #1.5 ranges are about 0.13-0.17 and 0.16-0.19 mm,
but use the manufacturer's specified range and the objective's correction setting.

Objective working distance is unforgiving. A holder that adds even 0.2 mm under the slide can put
the sample outside a high-NA objective's working distance. Design slide holders so the slide
registers directly against the stage datum, with the holder clamping from above.

## Petri dishes and stage inserts

Standard dish outside diameters are approximately 35, 60, 90, and 100 mm, but the flange profile
and lid fit vary. Dishes are also slightly out of round. Locate on three points rather than a
continuous circular pocket: a three-point nest is insensitive to ovality, a close-fitting bore is
not.

For stage inserts, the interface that matters is the **microscope stage opening**, which is
instrument-specific and must be measured. Many stages accept a standard SLAS-footprint insert;
confirm before assuming it.

## Checks to run

Declare the pocket in the model's `interfaces()` and let the check read it:

```bash
python scripts/gen.py carrier_model.py --outdir out/
python scripts/check.py interfaces out/carrier.manifest.json
```

**Do not point `check.py fit` at the carrier's STEP.** `fit` measures the outer bounding box, which
for a carrier is the outside of its walls — 6 mm larger than the pocket here — so it fails against
the plate footprint no matter how correct the pocket is. The dimension that matters is internal, so
it has to be declared, not measured from the envelope.

To check the number by hand instead:

```bash
python scripts/check.py fit --standard slas-microplate-footprint \
  --intent envelope --clearance 0.8 --value footprint_length=129.06
```

`--intent envelope` checks one-sided against maximum material condition, and `--clearance` is the
total intended clearance: 0.40 mm per side is 0.80 mm. Passing means the pocket is the size you
intended, not that the plate fits — only a test print shows that.

Then always run `snapshot.py` and confirm the pocket is on the face you meant.

## Sources

- ANSI/SLAS 1-2004 (R2012) Footprint Dimensions — <https://www.slas.org/SLAS/assets/File/public/standards/ANSI_SLAS_1-2004_FootprintDimensions.pdf>
- ANSI/SLAS 2-2004 (R2012) Height Dimensions — <https://www.slas.org/SLAS/assets/File/public/standards/ANSI_SLAS_2-2004_HeightDimensions.pdf>
- ANSI/SLAS 3-2004 (R2012) Bottom Outside Flange Dimensions — <https://www.slas.org/SLAS/assets/File/public/standards/ANSI_SLAS_3-2004_BottomOutsideFlangeDimensions.pdf>
- ANSI/SLAS 4-2004 (R2012) Well Positions — <https://www.slas.org/SLAS/assets/File/public/standards/ANSI_SLAS_4-2004_WellPositions.pdf>
- SLAS microplate standards overview — <https://www.slas.org/education/ansi-slas-microplate-standards/>

- Hellma 2025 cuvette catalogue — <https://www.hellma.com/fileadmin/fos/Website/Broschueren_Flyer_Handhabung/Hellma_Analytics/Englisch/Hellma_Kuevettenkatalog_EN_2025_gross.pdf>
- BRAND slide dimensions — <https://shop.brand.de/en/microscope-slides-white-height-1-mm-p162.html>
- ISO 8037-1:1986 catalogue — <https://www.iso.org/standard/15048.html>
