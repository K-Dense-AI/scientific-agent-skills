# Optomechanical mounts and breadboard hardware

Parts that bolt to an optical table, join a cage system, hold an optic or a sample in a beam path,
or carry a camera or objective.

Verified dimensions are in `assets/standards.json`:

```bash
python scripts/check.py standards --show optical-breadboard-metric
python scripts/check.py standards --show cage-system-30mm
python scripts/check.py standards --show sm1-lens-tube-thread
```

## Ask which system before you model anything

**Metric and imperial optical hardware are not interchangeable, and the difference is small enough
to look like a rounding error and large enough to prevent assembly.**

| | Metric | Imperial |
| --- | --- | --- |
| Grid pitch | 25.0 mm | 25.4 mm (1 inch) |
| Tapped hole | M6 x 1.0 | 1/4-20 UNC |
| Typical border | 12.5 mm | 12.7 mm |

Over four pitches (five hole centres) the grids differ by **1.6 mm** — far more than any clearance hole absorbs.
There is no way to infer which the user has from the request. Ask. If the answer is unavailable,
model the mounting features as **slots along the bolt line** rather than round holes, which
tolerates both, and say that is what you did and why.

## Mounting to the table

- Use **clearance holes, not tapped holes**, in the part. The table is tapped; the part is
  clearanced. For M6 use 6.6 mm is a common normal-clearance planning value. Add the calibrated process
  allowance and confirm the actual screw drawing; printed holes may come out undersize.
- **Counterbore for the screw head** if the part surface must stay clear: roughly 11 mm diameter
  for an M6 socket head cap screw, 11.2 mm for 1/4-20.
- **Never rely on more than two holes to locate a part.** Grid tolerance plus print tolerance means
  a rigid four-hole pattern will bind. Round hole + slot is the standard fix: one hole locates, the
  slot takes up the error.
- Printed parts are compliant. For anything where pointing stability matters, a printed mount is a
  prototyping aid, not a final part — thermal drift and creep in polymer are large compared with
  optical alignment tolerances. Say so when recommending one.

## Posts and pedestals

Common conventions, which vary by vendor — **confirm against the catalogue before use**:

- Imperial posts are Ø1/2 inch (12.7 mm), typically tapped 8-32 at one end with a 1/4-20 stud or
  clearance at the other.
- Metric posts are Ø12 mm, typically tapped M4 with an M6 interface to the table.
- A post-holder plus post is height-adjustable but adds a compliant joint; a pedestal or a
  solid machined riser is stiffer.

**Beam height** is a project-wide constant, not a per-part choice. Every mount on the table must
put its optic at the same height. Common conventions are 3 inches (76.2 mm) or 100 mm, but this is
a lab-by-lab choice. Ask for the number, define it once as `beam_height_mm`, and derive every
mount's optic centre from it.

## 30 mm cage system

The dominant convention for small free-space assemblies:

- **Rod spacing 30.0 mm** on a square, centred on the optical axis.
- **Rods Ø6 mm** (ER series).
- Standard cage plates are 0.35 inch (8.9 mm) thick.

For a custom cage plate: place four bores on a 30 mm square, put the aperture at the **centroid**
of those four bores, and bore them for a free-sliding fit **at your process's clearance**
(fabrication-limits.md): about 6.2 mm CNC, 6.4 mm SLA, 6.8 mm FDM. A 6.1 mm bore may work after reaming, but is not
a reliable uncalibrated printed fit; printed bores may come out undersize, and four bores on a common square over-constrain each
other, so tighter is not better here. A cage plate that binds on the rods is worse than useless
because it transmits stress into the whole assembly.

Cage plates stack along the rods, so a custom plate's thickness directly consumes optical path
length. Budget it.

## Lens tube threads (SM series)

**SM1 is a 1.035 inch-40 thread**, which holds Ø1 inch (25.4 mm) optics. That is a **0.635 mm
pitch**.

**Do not print SM threads.** A 0.635 mm pitch is at or below the practical resolution of FDM and
marginal on desktop SLA; a printed SM1 thread will either not engage or will gall and shed
particles into the beam path. Instead:

- bore a clearance hole and use a purchased SM1 adapter or retaining ring, or
- design for a threaded metal insert, or
- clamp the optic directly with a retaining flange and screws.

If the design truly requires a printed thread, say explicitly that it needs test printing and is
likely to fail.

## Holding an optic

- **Never clamp an optic on its clear aperture.** Contact only the outer annulus of the face or the
  edge. Define `clear_aperture_mm` as a named parameter and confirm in the snapshot that nothing
  intrudes on it.
- Three-point support can reduce constraint, but support geometry, preload and contact
  stress still matter. Neither three points nor a continuous annular seat guarantees
  freedom from deformation or stress birefringence; validate the mounting load.
- Leave clearance for thermal expansion. A metal-in-polymer mount that is a press fit at 20 °C can
  crack or bind across a temperature swing.
- Retaining forces should be light and distributed. A single set screw pressing on glass is a way
  to chip glass.

## Stray light and scatter

Geometry is not the whole design here, and a STEP file cannot show any of this:

- Printed surfaces scatter strongly. Any surface that sees the beam should be baffled, angled away
  from the optical axis, or treated.
- **Black does not mean non-reflective.** Black resin and black filament are often quite specular.
  Specify a genuinely absorbing surface treatment where it matters.
- Thread and layer lines act as diffraction structures near a focus.
- For fluorescence work, printed material near the sample can autofluoresce into the detection
  path.

Flag these to the user; do not silently assume a printed enclosure is light-tight.

## Checks to run

```bash
python scripts/gen.py mount_model.py --outdir out/
python scripts/check.py facts out/mount.step
python scripts/check.py interfaces out/mount.manifest.json
python scripts/snapshot.py out/mount.step --out out/mount.png
```

Declare the grid pitch, rod spacing, and bore diameters in the model's `interfaces()` against
`optical-breadboard-metric`, `optical-breadboard-imperial`, or `cage-system-30mm`, so the check
catches a 25.0-for-25.4 substitution rather than leaving it to a reader.

The interface check compares declared dimensions, not hole positions. Use cylindrical
`clear` gauges at requirement-derived coordinates to test the actual bolt pattern.
Compute the model from `grid_pitch_mm`, then also confirm the visible layout:

1. All mounting holes are present and pass fully through.
2. The optic aperture is centred where you intended, and unobstructed.
3. Counterbores are on the accessible face.
4. Nothing intrudes into the clear aperture or the beam path.

## Sources

- Thorlabs imperial and metric threading — <https://www.thorlabs.com/imperial-and-metric-threading>
- Thorlabs standard 30 mm cage plates — <https://www.thorlabs.com/standard-30-mm-cage-plates>
- Thorlabs SM1 lens tube compatible cage plates — <https://www.thorlabs.com/sm1-lens-tube-compatible-cage-plates>
- Post dimensions, beam heights, and vendor-specific thread conventions in this file are common
  conventions rather than published standards. Confirm against the catalogue.
