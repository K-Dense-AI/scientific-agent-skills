# Resources, decks, state, and serialization

Verified against **PyLabRobot 0.2.2** on **2026-10-01**.

## Resource model

PyLabRobot represents a workcell as a resource tree. Typical nodes are:

- `LiquidHandler` / `Deck`
- carriers, adapters, sites, and modules
- `Plate`, `TipRack`, reservoirs, tube racks, and `Trash`
- `Well`, `TipSpot`, and `Tip`

Every resource has a unique name, dimensions in millimetres, an optional
location relative to its parent, and parent/child relationships. Names are how
`Deck.get_resource(name)` resolves nested resources, so duplicates are unsafe.

```python
from pylabrobot.resources import Coordinate, Resource

resource = Resource(
    name="fixture",
    size_x=100.0,
    size_y=50.0,
    size_z=20.0,
)
parent.assign_child_resource(
    resource,
    location=Coordinate(x=10.0, y=20.0, z=0.0),
)
```

The coordinate origin and usable envelope depend on the parent/deck definition.
Do not copy coordinates across robots, carriers, adapters, or labware revisions.

## Use stable built-in definitions

Stable 0.2.2 exports vendor/model resource factories. The Hamilton getting
started tutorial uses:

```python
from pylabrobot.resources import (
    cor_96_wellplate_360uL_Fb,
    PLT_CAR_L5AC_A00,
    TIP_CAR_480_A00,
    hamilton_96_tiprack_1000uL_filter,
)
from pylabrobot.resources.hamilton import STARLetDeck
```

Names are case-sensitive. Old examples such as `Cos_96_DW_1mL` may not identify
the intended current factory. Search the installed 0.2.2 resource namespace or
stable resource docs and verify manufacturer, catalog number, dimensions,
bottom geometry, capacity, lid/adapter, and revision.

Carrier sites are commonly assigned before the carrier is placed on the deck:

```python
tip_carrier = TIP_CAR_480_A00(name="tip_carrier")
tip_carrier[0] = tips = hamilton_96_tiprack_1000uL_filter(name="tips")

plate_carrier = PLT_CAR_L5AC_A00(name="plate_carrier")
plate_carrier[0] = plate = cor_96_wellplate_360uL_Fb(name="plate")

deck = STARLetDeck()
deck.assign_child_resource(tip_carrier, rails=3)
deck.assign_child_resource(plate_carrier, rails=15)
```

Rail placement is Hamilton-specific. Other decks use their own sites,
coordinates, fixtures, and constraints.

## Plates, wells, tip racks, and tips

Stable accessors include:

```python
well = plate.get_well("A1")
wells = plate.get_wells(["A1", "B1"])
selected_wells = plate["A1"]  # list[Well], even for one identifier
tip_spot = tips.get_item("A1")
selected_tip_spots = tips["A1"]  # list[TipSpot]
tip = tip_spot.get_tip()
```

Relevant stable constructors/attributes include:

- `Well(..., max_volume=..., height_volume_data=...)`
- `Tip(has_filter, total_tip_length, maximal_volume, fitting_depth, ...)`
- `TipRack(..., with_tips=True)`
- `TipSpot(..., make_tip=...)`

`Tip.maximal_volume` is only one compatibility dimension. Also validate fitting,
length, filter, head/tool, pickup/drop geometry, rack model, and vendor support.

Well capacity is geometric bookkeeping. Usable aspiration volume is smaller
when dead volume, well shape, tilt, liquid properties, required immersion, or
assay constraints apply. `height_volume_data` supports interpolation for
definitions that provide it; it is not a sensor and is only as accurate as the
definition/calibration.

## Coordinate and collision checks

For every resource, verify:

1. Dimensions and units (`mm`).
2. Location relative to the correct parent and absolute location on the deck.
3. Orientation/rotation, lid, adapter, nesting, and stacking height.
4. Static overlap with neighboring resources.
5. Dynamic envelopes for channels, tips, grippers, arms, doors, trays, buckets,
   cables, tubing, and manually handled items.
6. Manufacturing tolerance, calibration, teaching, and clearance margin.

Hamilton deck assignment performs collision checks and exposes an
`ignore_collision` escape hatch. Do not set `ignore_collision=True` to make a
layout pass. Resolve the definition or placement and repeat physical review.
Generic resource assignment alone is not a complete collision or motion check.
Released 0.2.2 takes `rails=`; the newer documentation may use `track=`, which
is not a keyword in this release.

The bundled checker provides an independent deterministic screen:

```bash
python3 skills/pylabrobot/scripts/check_deck_geometry.py \
  --input tests/pylabrobot/fixtures/protocol_manifest.json
```

It checks deck bounds and pairwise axis-aligned box overlap. It intentionally
does not claim to model rotation, motion, lids, tubing, cables, tolerances, or
vendor firmware paths.

## Tip and volume state

```python
from pylabrobot.resources import set_tip_tracking, set_volume_tracking

set_tip_tracking(True)
set_volume_tracking(True)

tips.fill()
tips.get_item("A1").tracker.has_tip
plate.get_well("A1").tracker.set_volume(200.0)
plate.get_well("A1").tracker.get_used_volume()
plate.get_well("A1").tracker.get_free_volume()
```

Trackers model expected software state and operation history. They do not
physically detect tips, liquid, liquid identity, clogs, seals, lids, or
misloaded labware. Reconcile tracker state against a trusted preparation record
and the physical deck before any live run.

Keep these separate:

- maximum geometric well volume;
- declared initial volume;
- minimum dead/residual volume;
- transfer amount;
- maximum tip volume and currently held tip volume;
- destination headspace;
- physical liquid-level detection, if a particular backend supports it.

## Definition and state serialization

Verified 0.2.2 methods include:

```python
resource.save("deck.json", indent=2)
loaded = Resource.load_from_json_file("deck.json")

state = resource.serialize_all_state()
resource.load_all_state(state)
resource.save_state_to_file("state.json", indent=2)
resource.load_state_from_file("state.json")
```

Only deserialize an allowlisted **resource-only** tree. Machine serialization
also contains a backend and may reconstruct it; `allow_marshal=False` is not a
ban on hardware backend construction. Never load an unreviewed `LiquidHandler`
or device node while claiming an offline resource import.

`Resource.serialize()` stores a definition; `serialize_state()` and
`serialize_all_state()` store tracker/resource state. Keep definition and state
with protocol version, PyLabRobot version, checksums, device/deck identity, and
preparation metadata.

Treat serialized files as untrusted input:

- accept only bounded UTF-8 JSON from an approved local path;
- reject duplicate/unknown keys and non-finite values;
- never load arbitrary Python, pickle, plugins, or user-selected classes;
- keep `Resource.deserialize(..., allow_marshal=False)` at its safe default;
- validate names, resource types, dimensions, locations, capacities, and state
  against an allowlist before constructing a workcell;
- do not let a saved state replace physical deck reconciliation.

The bundled tools do not deserialize PyLabRobot classes. They use a small,
strict manifest schema:

- `assets/protocol-manifest.schema.json`
- `tests/pylabrobot/fixtures/protocol_manifest.json`

The Python validator adds bounds and cross-field checks beyond the documentation
schema:

```bash
python3 skills/pylabrobot/scripts/validate_manifest.py \
  --input tests/pylabrobot/fixtures/protocol_manifest.json
```

Inputs must remain under the current working directory, be regular non-symlink
files, use the expected extension, stay under 2 MB, and have at most 64 JSON
nesting levels. Every transferred-to well needs an explicit starting volume,
including `0.0` for an intentionally empty destination. The validator never
assumes an undeclared destination is empty.

## Custom labware

Do not invent a `Plate` or `Well` from nominal SBS footprint alone. Obtain and
review:

- exact manufacturer/catalog/revision;
- external dimensions, skirt and flange, nesting/stacking, lid and adapter;
- well centres, pitch, top/bottom geometry, depth, material thickness, and
  height/volume behavior;
- robot-specific pickup, gripping, carrier/site, and clearance data;
- empirical calibration and acceptance results.

Use upstream's current resource-definition contributor tooling and tests. Keep
custom definitions versioned and independently reviewed before commissioning.

## Sources

Checked **2026-10-01**:

- [Hosted resource management](https://docs.pylabrobot.org/stable/resources/introduction.html)
  and [hosted resources API](https://docs.pylabrobot.org/stable/api/pylabrobot.resources.html)
  — development resource guide; release signatures verified from the wheel.
- [Hosted Hamilton tutorial](https://docs.pylabrobot.org/stable/user_guide/00_liquid-handling/hamilton-star/basic.html)
  — verified factories, carrier sites, rails, and deck summary.
- [Hosted tracker guide](https://docs.pylabrobot.org/stable/user_guide/machine-agnostic-features/using-trackers.html)
  — tip/volume state and errors.
- [released 0.2.2 resources source](https://pypi.org/project/PyLabRobot/0.2.2/#files)
  — constructor, serialization, tracker, and collision signatures; released
  2026-07-30.
- [Release review](review.md) — `height_volume_data` remains supported;
  `Plate.stacking_z_height` and `plate_type` round-trip in 0.2.2 even though the
  changelog lists stacking under `Unreleased`. Native tests confirm bare-plate
  stacking height and resource/state round trips.
