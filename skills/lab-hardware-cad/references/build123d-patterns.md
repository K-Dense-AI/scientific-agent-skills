# build123d 0.13.0 patterns

An API cookbook for the geometry this skill needs, reviewed against build123d 0.13.0
on Python 3.12 with OCCT 8.0.1. The complete carrier, cage model, exports, selectors,
counterbore and native gauges are exercised in the repository suite. Snippets with
undefined surrounding variables are illustrative fragments to adapt to the model.

## Builder mode or algebra mode

build123d offers two equivalent APIs.

```python
# Builder mode: a context manager collects operations. mode= controls the boolean.
with BuildPart() as ex:
    Box(80.0, 60.0, 10.0)
    Cylinder(radius=11.0, height=10.0, mode=Mode.SUBTRACT)
part = ex.part

# Algebra mode: plain objects and operators.
part = Box(80.0, 60.0, 10.0) - Cylinder(radius=11.0, height=10.0)
```

**Use builder mode for parts in this skill.** Selectors (`ex.edges()`, `ex.faces()`) read naturally
from the builder, which is what you need for fillets and for placing features on found faces.
Algebra mode is a good fit for short, purely constructive shapes.

Do not mix the two styles inside one `build()`.

## The model file contract

`gen.py` imports the module, calls `build()`, and then reads `interfaces()`. Parameters must be
module-level so they can be overridden with `--param`.

```python
"""One-line description of the part.

Process: SLA, tough resin.  Orientation: bore axis vertical.
Interfaces:
  - Rod bores: 30 mm cage system, Thorlabs ER series (cage-system-30mm).
"""
from build123d import *

# --- INTERFACE (fixed; do not tune) ---
rod_spacing_mm = 30.0     # cage-system-30mm
rod_bore_d_mm = 6.4       # rod_diameter 6.0 + 2 x 0.20 SLA free-sliding (fabrication-limits.md)
# --- DESIGN (free) ---
plate_t_mm = 8.9
aperture_d_mm = 25.4


def interfaces() -> list[dict]:
    return [
        {"feature": "cage rod bore spacing", "standard": "cage-system-30mm",
         "dimension": "rod_spacing", "value": rod_spacing_mm, "intent": "match"},
        {"feature": "cage rod bore diameter", "standard": "cage-system-30mm",
         "dimension": "rod_diameter", "value": rod_bore_d_mm,
         "intent": "envelope", "clearance": 0.4},
    ]


def build() -> Part:
    half = rod_spacing_mm / 2
    with BuildPart() as plate:
        Box(rod_spacing_mm + 12.0, rod_spacing_mm + 12.0, plate_t_mm)
        with Locations((half, half), (-half, half), (half, -half), (-half, -half)):
            Hole(radius=rod_bore_d_mm / 2)
        Hole(radius=aperture_d_mm / 2)
    return plate.part
```

## Declaring interfaces

Most lab-hardware interfaces are **internal features** — a pocket, a bore, a slot — and none of
them appear in the part's outer bounding box. So `check.py fit` cannot find them by measuring the
STEP, and hand-copying the number into `--value` reintroduces exactly the transcription error the
skill exists to prevent. Declaring them closes the loop: `gen.py` records the declaration in the
manifest, and `check.py interfaces` verifies every entry.

Each entry needs `standard`, `dimension`, and `value`; `feature`, `intent`, and `clearance` are
optional:

| Key | Meaning |
| --- | --- |
| `standard` | ID from `check.py standards --list` |
| `dimension` | a dimension name inside that standard |
| `value` | the number **this model computed**, in mm |
| `feature` | human label for the check output (default: the dimension name) |
| `intent` | `match` if this part must itself conform; `envelope` if the feature must accept any conforming part (default: `match`) |
| `clearance` | total intended clearance in mm, both sides (default: 0) |

**Write `interfaces()` as a function, and compute derived dimensions inside functions.** A
module-level `INTERFACES = [...]` list is also accepted, but it is evaluated at import — before
`--param` is applied — so any value derived from an overridden parameter is recorded wrong. The same
applies to the geometry: derive inside `build()` or a helper, never at module level.

```python
# Wrong: --param plate_tol_mm=0 silently leaves pocket_l_mm at the old value
pocket_l_mm = plate_l_mm + plate_tol_mm + 2 * pocket_clearance_mm

# Right: recomputed on every call, so overrides land
def pocket_l_mm() -> float:
    return plate_l_mm + plate_tol_mm + 2 * pocket_clearance_mm
```

`gen.py` warns when it sees a static `INTERFACES` list together with `--param`.

## Declaring geometry checks

`interfaces()` compares declared numbers against the standards database; it never touches the
solid. `checks()` is its measured counterpart: a list of **go/no-go gauges** evaluated by boolean
intersection against the part `build()` actually produced. `gen.py` runs them on every
generation and fails the build if one fails; `check.py geometry` re-runs them against an
exported STEP.

The principle: **every geometric requirement in the request maps to one entry.** Something must
pass through (a screw, a beam, a probe) → a `clear` region. Something must fit into a void (a
plate into a pocket) → a `clear` box the size of the mating part at maximum material condition.
Something must remain (a ridge, a ledge, a screw seat) → a `material` region. A stated size
limit → a `bbox_*` bound. These are exactly the errors `is_valid`, the bounding box, and a
declared-number check cannot see.

```python
def checks() -> list[dict]:
    top = plate_t_mm / 2
    return [
        # a clear region: no material may intrude (screw shafts, through the part)
        {"feature": "M6 screws pass all four bores",
         "clear": {"cylinder": 6.0, "axis": "z", "at": bolt_xy()}},
        # a keep-out with an explicit span (a beam corridor along x at height z)
        {"feature": "beam clear at 15 mm above the bench",
         "clear": {"cylinder": 5.0, "axis": "x", "at": [(0.0, 15.0)]}},
        # a gauge part that must drop into a pocket: the mating part at MMC
        {"feature": "SLAS plate at MMC drops into the pocket",
         "clear": {"box": (128.26, 85.98, pocket_depth_mm()),
                   "at": [(0.0, 0.0, floor_t_mm + pocket_depth_mm() / 2)]}},
        # a counterbore that really is a counterbore: recess open, seat present.
        # The second entry is what catches a recess that punched through.
        {"feature": "counterbore recess open at the top",
         "clear": {"cylinder": cbore_d_mm - 0.2, "axis": "z", "at": bolt_xy(),
                   "span": (top - cbore_depth_mm + 0.1, top + 0.1)}},
        {"feature": "screw seat present below the recess",
         "material": {"cylinder": cbore_d_mm - 0.2, "axis": "z", "at": bolt_xy(),
                      "span": (-top + 0.1, top - cbore_depth_mm - 0.1)},
         "min_mm3": 50.0},
        # a user-stated hard limit, measured from the solid
        {"feature": "clears the objective turret", "bbox_z": {"max": 15.0}},
    ]
```

Semantics:

| Key | Meaning |
| --- | --- |
| `clear` / `material` | region that must contain no material / must contain material |
| `{"cylinder": DIA, "axis": "x"\|"y"\|"z", "at": [(a, b), ...], "span": (lo, hi)}` | `at` is 2D in the plane perpendicular to the axis — axis `z`: (x, y); axis `x`: (y, z); axis `y`: (x, z). Omit `span` to run through the whole part |
| `{"box": (dx, dy, dz), "at": [(x, y, z), ...]}` | axis-aligned box gauges centred at each position |
| `tol_mm3` / `min_mm3` | pass thresholds per position (both default 0.01); choose from the feature volume, not blindly |
| `bbox_x`…`bbox_z`, `bbox_min/mid/max` | `{"min": mm, "max": mm}` bounds on the measured bounding box |

A `material` gauge asserts only that its overlap exceeds `min_mm3`, not that the
whole region is filled. Set a requirement-based minimum; 0.01 mm³ alone does not
prove a full ridge or screw seat. Empty positions and non-finite inputs are rejected.

Size the gauges from the same named constants as the geometry **only when the requirement is
relational** (the recess sits above the seat). When the requirement is absolute — a mating part's
MMC, a user's height limit, a beam position — write the gauge from the requirement's own numbers,
so a wrong parameter cannot shrink the gauge to match the wrong geometry.

For a one-off question without editing the model, `check.py probe` runs a single gauge from the
command line, and `check.py bores` prints a census of every cylindrical face (diameter, axis,
position, span, sweep) to reconcile against the model's intent.

## Positioning

`Locations` places the objects created inside it. It is the workhorse for bolt patterns.

```python
with Locations((10.0, 0.0), (-10.0, 0.0)):        # two positions on the current plane
    Hole(radius=3.3)

with Locations((0.0, 0.0, floor_t_mm)):           # offset in z
    Box(10.0, 10.0, 5.0, mode=Mode.SUBTRACT)

with GridLocations(9.0, 9.0, 12, 8):              # x spacing, y spacing, x count, y count
    Hole(radius=1.5)
```

`GridLocations` centres the grid on the origin. A microplate well grid is dimensioned from the
plate corner instead, so compute absolute positions and pass them to `Locations`:

```python
a1_x_mm, a1_y_mm, pitch_mm = 14.38, 11.24, 9.0    # slas-well-positions-96
origin_x = -plate_l_mm / 2
origin_y = plate_w_mm / 2
wells = [
    (origin_x + a1_x_mm + pitch_mm * col, origin_y - a1_y_mm - pitch_mm * row)
    for row in range(8) for col in range(12)
]
with Locations(*wells):
    Hole(radius=well_clear_d_mm / 2)
```

## Alignment

By default objects are centred on the origin. `align` moves the datum, which is usually what you
want for a pocket that starts at a floor:

```python
Box(x, y, z, align=(Align.CENTER, Align.CENTER, Align.MIN))   # sits on z = 0
Box(x, y, z, align=(Align.MIN, Align.MIN, Align.MIN))         # corner at the origin
```

Getting this wrong is the classic "pocket cut through the floor" bug, and it is exactly what the
snapshot catches.

## Holes

`Hole` cuts through the whole part; `CounterBoreHole` and `CounterSinkHole` add a head recess.

**`CounterBoreHole` cuts downward from the workplane it is placed on, with the recess at that
plane.** On a centred `Box` the default workplane is the mid-height of the part, so a 2-tuple
location buries the screw seat inside the plate — or, on a thin plate, lets the recess swallow the
top entirely, leaving a straight bore the screw head falls through. Place it on the **top face**
(or give the location an explicit z at the top):

```python
with BuildPart() as plate:
    Box(60.0, 60.0, 10.0)                              # spans z = -5 .. +5
    top = plate.faces().sort_by(Axis.Z)[-1]
    with Locations(top):
        with Locations((20.0, 20.0)):
            CounterBoreHole(radius=6.6 / 2, counter_bore_radius=11.0 / 2,
                            counter_bore_depth=6.5)
```

Size `counter_bore_depth` from the **screw head height**, not from habit: an M6 socket head cap
screw head is 6.0 mm tall, a 1/4-20 head 6.35 mm (`screw_head_height` in the breadboard
standards). A 4 mm counterbore leaves either head 2 mm proud — do not call that flush. After
generating, confirm in the snapshot (or a section) that the recess is at the top face and the
seat ledge exists; both failure modes here pass `is_valid` and the bounding box untouched.

Remember that printed holes come out undersize — see `references/fabrication-limits.md`.

## Selectors

Selectors find edges and faces to fillet, chamfer, or build on. The three you need:

```python
part.edges().filter_by(Axis.Z)              # keep edges parallel to Z (the vertical corners)
part.edges().group_by(Axis.Z)[-1]           # the group with the highest Z (the top edges)
part.faces().sort_by(Axis.Z)[-1]            # the single highest face
part.edges().filter_by(GeomType.CIRCLE)     # only circular edges
```

`filter_by` keeps everything matching. `group_by` partitions into lists ordered by the key, so
`[-1]` is the last group and `[0]` the first. `sort_by` orders individual items.

```python
with BuildPart() as ex:
    Box(80.0, 60.0, 10.0)
    chamfer(ex.edges().group_by(Axis.Z)[-1], length=4.0)   # chamfer the top face edges
    fillet(ex.edges().filter_by(Axis.Z), radius=5.0)       # round the vertical corners
```

**These broad selectors are only safe on a part that is still a plain box.** Once the part has
pockets, bores, notches, or micro-relief, `filter_by(Axis.Z)` and `group_by(Axis.Z)[-1]` also
select the edges of those features, and the fillet either throws a kernel error
(`Failed creating a fillet`, `BRep_API: command not done`) or — worse — succeeds and silently eats
a wall or a 0.3 mm ridge. Both happen in practice. So:

- Fillet or chamfer the **outer body before adding internal features**, or filter the selection
  down deliberately (by position, length, or `GeomType`) so only the intended edges remain.
- Bound the radius with `part.max_fillet(edges)` when the nearby geometry is tight — it returns
  the largest radius the kernel can actually build on that edge set.
- Make every fillet/chamfer radius a named parameter, and on a kernel failure back the value off
  rather than fighting the selector.
- Then check the snapshot: a consumed feature is obvious in the picture and invisible in
  `is_valid`.

## Sketch then extrude

For a profile that is not a primitive, sketch it and extrude:

```python
with BuildPart() as bracket:
    with BuildSketch() as profile:
        Rectangle(40.0, 20.0)
        with Locations((15.0, 0.0)):
            Circle(radius=4.0, mode=Mode.SUBTRACT)
    extrude(amount=6.0)
```

This is also the route to a laser-cut DXF: the sketch is the cut profile.

## Exports

`gen.py` handles these, but for reference:

```python
export_step(part, "part.step", unit=Unit.MM)                 # authoritative
export_stl(part, "part.stl", tolerance=1e-3, angular_tolerance=0.1)

# 2D profile for laser cutting. section() is a module-level operation, NOT a
# method on the shape -- part.section(...) raises AttributeError.
from build123d.exporters import ColorIndex   # NOT exported by `from build123d import *`

profile = section(part, Plane.XY.offset(z_mm), mode=Mode.PRIVATE)
profile = profile.moved(Location((0, 0, -z_mm)))   # back to z = 0, or the DXF writer
                                                   # warns about a non-planar shape
exporter = ExportDXF(unit=Unit.MM)
exporter.add_layer("CUT", color=ColorIndex.RED)    # laser shops key power/speed to layers
exporter.add_shape(profile, layer="CUT")
exporter.write("part.dxf")
```

Prefer a section strictly inside the material. A section coincident with an outer face
can be ambiguous or omit features; do not assume `z = 0` intersects the desired profile. `gen.py --dxf` defaults to the part's mid-height and takes `--dxf-z`
to override.

STEP preserves exact BREP geometry; STL is a triangulated approximation. **Always keep STEP as the
source of truth** and regenerate meshes from it, never the reverse.

The STL exporter's `angular_tolerance` is in **radians** (0.1 ≈ 5.7°), although
most modeling rotations use degrees. STL carries no unit metadata; this skill
exports/imports its mesh coordinates as mm. `import_stl` returns a triangulated
Face in 0.13.0, not a watertight BREP solid: use STEP for volume, gauges and fit.

## Measuring in code

Useful for asserting an interface inside the model itself:

```python
bbox = part.bounding_box()
print(bbox.size.X, bbox.size.Y, bbox.size.Z)
print(part.volume, part.area)
print(part.is_valid)          # a property in 0.13.0, not a method
print(part.center(CenterOf.MASS))
```

`is_valid` being a property rather than a method is a real difference from older releases and from
some documentation. Access it without parentheses.

## Things that bite

- **`is_valid` is a property.** `part.is_valid()` raises `TypeError: 'bool' object is not callable`.
- **`section()` is a module-level operation, not a method.** `part.section(Plane.XY)` raises
  `AttributeError`. Call `section(part, plane, mode=Mode.PRIVATE)`.
- **`intersect()` returns a `ShapeList`** with no `.volume`; the `&` operator returns a shape/part that
  has one. `check.py clearance` handles both.
- **Never name a script `inspect.py`** in a directory that lands on `sys.path`. It shadows the
  standard library `inspect` module, which breaks `typing_extensions` and therefore build123d
  itself. This is why the bundled script is `check.py`.
- **Builder objects are not parts.** Return `builder.part`, not the builder.
- **`Mode.SUBTRACT` needs an existing body.** Subtracting from an empty context does nothing
  silently.
- **A swept or extruded profile is centred on its path/plane unless you align it.** Sweeping a
  `Rectangle(w, h)` along a path on a surface leaves half the profile below the surface — a
  "0.3 mm ridge" that is really 0.15 mm proud. Pass `align=` (and an explicit `x_dir` on the
  profile plane) so the profile sits where you think it does, then measure the result.
- **`Curve` has no `.length`.** Sum the edges instead: `sum(e.length for e in curve.edges())`.
- **The boolean of touching or disjoint solids is empty, not an error.** Depending on the path you
  get `None`, an empty `Compound`, or a `ShapeList` with no `.volume` — guard before reading
  `.volume` in any interference check.
- **`ColorIndex` and `LineType` live in `build123d.exporters`**, not in the top-level namespace;
  `from build123d import *` does not bring them in, and `add_layer(color=1)` fails.
- The OpenCascade kernel raises assorted exception types. Catch broadly around boolean operations
  and report the failure rather than letting a traceback escape.

## Sources

- build123d documentation — <https://build123d.readthedocs.io/en/stable/>
- Introductory examples (builder vs algebra, selectors, fillets) —
  <https://build123d.readthedocs.io/en/stable/introductory_examples.html>
- Import/export reference — <https://build123d.readthedocs.io/en/stable/import_export.html>

- OpenCascade cylindrical surface parameter bounds — <https://occt3d.com/dev/doc/refman/html/class_b_rep_adaptor___surface.html>
- build123d 0.13.0 release — <https://github.com/gumyr/build123d/releases/tag/v0.13.0>

`bores` reports cylindrical UV bounds. For irregularly trimmed faces the parameter
rectangle may contain gaps; a 360° bound does not prove an uninterrupted bore or
distinguish a bore from a boss. Use sections or clear gauges for that claim.
