# Liquid Handling Guide

Choose commands from the physical behavior the assay needs, not from which call
is shortest to write. Every command still depends on correct liquid volumes,
labware geometry, pipette range, tips, and contamination controls.

## Command Layers

### Building-block commands

Use when aspiration and dispensing need independent control:

```python
pipette.pick_up_tip()
pipette.aspirate(50, source.bottom(z=1), flow_rate=25)
protocol.delay(seconds=1)
pipette.dispense(50, destination.bottom(z=2), flow_rate=20, push_out=5)
pipette.blow_out(destination.top(z=-1))
pipette.drop_tip()
```

Advantages:

- Explicit position and order.
- Independent flow rates and delays.
- Fine control for viscous, volatile, foaming, low-volume, or bead workflows.

Costs:

- The author owns tip state and volume state.
- More opportunities to aspirate with no tip, overfill the pipette, or leave
  residual volume.

### Standard complex commands

Use for conventional source-to-destination mappings:

```python
pipette.transfer(
    volume=50,
    source=source_plate.wells()[:8],
    dest=destination_plate.wells()[:8],
    new_tip="always",
    mix_after=(3, 30),
)
```

- `transfer()`: one or more source-to-destination transfers.
- `distribute()`: one source to many destinations, normally with an excess
  disposal volume.
- `consolidate()`: many sources into one destination.

Inspect the simulation run log. Complex commands expand into many building
blocks, and their expansion changes with parameters and API level.

### Liquid-class complex commands, Flex API 2.24+

Use an Opentrons-verified class when the pipette/tip combination is supported
and the liquid resembles the verified model:

```python
viscous = protocol.get_liquid_class("glycerol_50")

pipette.transfer_with_liquid_class(
    liquid_class=viscous,
    volume=50,
    source=reservoir["A1"],
    dest=plate["A1"],
    new_tip="always",
    trash_location=trash,
)
```

Related methods:

- `distribute_with_liquid_class()`
- `consolidate_with_liquid_class()`

Verified classes include water, 80% ethanol, and 50% glycerol. A liquid class
controls multiple coupled properties such as flow rate, submerge and retract
behavior, delays, air gaps, positions, and push-out. Do not casually override
one property without testing the full result.

Opentrons-verified liquid classes are for supported Flex pipette and tip
combinations, not OT-2 pipettes.

## Source and Destination Mapping

Complex commands accept a single well or a sequence. Make the intended mapping
explicit:

- One source, one destination: one transfer.
- One source, many destinations: repeated transfers or a distribution.
- Many sources, one destination: repeated transfers or a consolidation.
- Equal-length source and destination lists: pairwise transfers.

Do not assume row-major ordering:

```python
# Explicit sample order is easier to audit.
sample_wells = [plate[name] for name in ("A1", "B1", "C1", "D1")]
```

For multi-channel pipettes, the referenced well anchors the pipette's primary
channel:

- A full 8-channel pipette normally targets an entire column by referencing its
  A-row well.
- A full 96-channel pipette addresses an entire 96-well rack or plate.
- A partial-column layout has a different primary channel; follow the layout
  documentation rather than reusing full-column assumptions.

## Tip Policy

`new_tip` is a contamination decision.

| Policy | Typical use | Primary risk |
| --- | --- | --- |
| `"always"` | Independent samples, controls, or source-destination pairs | Higher tip consumption |
| `"once"` | Reagent distribution within one contamination domain | Returning a contaminated tip to a shared source |
| `"never"` | Explicit surrounding `pick_up_tip()` and `drop_tip()` | Hidden or invalid tip state |

For a shared reagent:

- Aspirating repeatedly from the same source with one tip may be acceptable only
  if the tip never contacts incompatible destination liquid.
- A submerged dispense can wet the exterior or interior of the tip.
- Touch tip, mix, or bottom-contact dispense increases contamination risk.
- Controls and samples generally require separate tips.

Calculate tips for every conditional path. Multi-channel operations consume
sets, not individual command calls.

## Flow Rate, Position, and Delays

### Relative and absolute rates

`rate=` multiplies the configured flow rate:

```python
pipette.aspirate(50, source, rate=0.5)
```

Supported modern APIs also accept absolute flow-rate arguments:

```python
pipette.aspirate(50, source, flow_rate=25)
```

Use one form per action. Absolute units are µL/s. Establish values through
liquid-specific testing rather than copying another pipette's settings.

### Positions

```python
source.bottom(z=1)
source.top(z=-2)
destination.center()
```

- Bottom aspiration reduces residual volume but increases collision and pellet
  disturbance risk.
- Top or near-top dispensing can reduce contact contamination but may splash.
- Side offsets can reduce foaming but require known well geometry.
- `touch_tip()` can be unsafe in large wells and reservoirs; API 2.28+ rejects
  certain large-space uses.

### Air gaps and push out

Air gaps can reduce dripping but occupy pipette capacity:

```python
pipette.aspirate(80, source)
pipette.air_gap(10)
pipette.dispense(90, destination)
```

The total liquid plus air must fit the pipette. Use `push_out` to move the
plunger a small extra amount after dispensing:

```python
pipette.dispense(80, destination, push_out=5)
```

Use blowout for a larger purge. Avoid blowing into liquid when aerosols,
bubbles, or cross-contamination matter.

## Mixing

Standard mixing:

```python
pipette.mix(
    repetitions=5,
    volume=40,
    location=plate["A1"].bottom(z=1),
    aspirate_flow_rate=20,
    dispense_flow_rate=30,
    final_push_out=5,
)
```

Choose a mix volume below the available liquid volume and pipette maximum.
Account for pellets, beads, cells, foaming, and plate seals.

API 2.27 adds dynamic mixing:

```python
well = plate["A1"]
pipette.dynamic_mix(
    aspirate_start_location=well.bottom(z=1),
    aspirate_end_location=well.bottom(z=4),
    dispense_start_location=well.bottom(z=4),
    dispense_end_location=well.bottom(z=1),
    repetitions=3,
    volume=50,
)
```

Dynamic movement is geometry-sensitive. Simulate, inspect the path, and dry-run
with the exact labware before using it on samples.

## Dynamic Aspiration and Dispensing

API 2.27 can move between two locations during one plunger action:

```python
pipette.aspirate(
    volume=100,
    location=well.bottom(z=1),
    end_location=well.bottom(z=5),
    movement_delay=1,
)
```

This can follow a changing meniscus or sweep through a liquid column. It does
not automatically prove that the declared liquid volume or geometry is
correct.

## Liquid Definitions and Meniscus

Declare setup volumes with labware-level methods:

```python
buffer = protocol.define_liquid(
    name="Buffer",
    description="Assay buffer",
    display_color="#1F77B4",
)
reservoir.load_liquid(
    wells=["A1"],
    volume=12_000,
    liquid=buffer,
)
```

API 2.23 adds `well.meniscus()`:

```python
start_surface = reservoir["A1"].meniscus(z=-1, target="start")
end_surface = reservoir["A1"].meniscus(z=-1, target="end")
```

The calculated surface depends on liquid volume and labware geometry. With
dynamic aspiration or dispensing, `target="start"` and `target="end"` can
represent the expected surface at either end of the operation.

Do not rely on meniscus targeting until declared volumes, well geometry, and
liquid-level behavior have been checked on the robot.

## Liquid Presence Detection

Flex pressure sensors support three explicit operations:

```python
present = pipette.detect_liquid_presence(reservoir["A1"])
pipette.require_liquid_presence(reservoir["A1"])
height = pipette.measure_liquid_height(reservoir["A1"])
```

Or enable a check before every aspiration:

```python
pipette = protocol.load_instrument(
    "flex_1channel_1000",
    "left",
    tip_racks=[tips],
    liquid_presence_detection=True,
)
```

Operational constraints:

- Use a fresh, dry, empty tip.
- Detection can add 5–50 seconds per check depending on well depth and volume.
- An 8-channel pipette has pressure sensors only on channels 1 and 8.
- A 96-channel pipette has pressure sensors only on channels 1 and 96.
- A wet tip can defeat absence detection.
- Detection is not a substitute for source-volume planning.

Use explicit checks at critical sources when global detection would add too
much time.

## Partial Tip Pickup

Supported layouts:

| Pipette | Layout | Minimum API |
| --- | --- | ---: |
| Flex 96-channel | column | 2.16 |
| Flex 96-channel | row, single | 2.20 |
| Flex 8-channel | single, partial column | 2.20 |
| OT-2 multi-channel | single, partial column | 2.20 |

```python
from opentrons.protocol_api import ALL, COLUMN

pipette.configure_nozzle_layout(
    style=COLUMN,
    start="A12",
    tip_racks=[partial_rack],
)

# Partial-column operations...

pipette.configure_nozzle_layout(
    style=ALL,
    tip_racks=[full_rack],
)
```

Critical rules:

- `configure_nozzle_layout()` resets `pipette.tip_racks`.
- Use separate rack variables for full and partial pickup.
- Full-rack Flex 96-channel pickup requires an adapter.
- Partial Flex 96-channel pickup must not use the adapter.
- Never pass a pickup or well location that leaves active nozzles hanging
  outside the rack or labware.
- Deck-edge reach depends on layout and starting nozzle.
- Prefer the 96-channel pipette's column-12 nozzles for column pickup when deck
  reach allows.
- Simulate and perform a tip-only dry run before first physical use.

See the official
[Partial Tip Pickup guide](https://docs.opentrons.com/python-api/pipettes/partial-tip-pickup/)
for layout-specific target-well rules.

## Serial Dilution Pattern

For a full 96-well plate and an 8-channel pipette:

1. Preload stock in column 1.
2. Add diluent to columns 2–12.
3. Transfer from column 1 to 2, mix, then 2 to 3, and so on.
4. Use a fresh tip set at each dilution step unless the validated method says
   otherwise.
5. Remove one transfer volume from column 12 if equal final volumes are needed.

Referencing A-row wells addresses full columns:

```python
pipette.transfer(
    100,
    source=plate.rows()[0][0:11],
    dest=plate.rows()[0][1:12],
    mix_after=(3, 50),
    new_tip="always",
)
```

Verify that the tip budget covers 11 serial steps plus diluent addition and
final-volume removal.

## Final Liquid-Handling Review

- Every volume is within pipette and tip range.
- Air plus liquid never exceeds capacity.
- Sources include dead volume and disposal volume.
- Destinations remain below capacity at every intermediate step.
- Mix volume is physically available.
- Positions do not contact the well bottom or pellet.
- Tip policy matches contamination boundaries.
- Multi-channel well references match the active nozzle layout.
- Liquid sensing uses fresh, dry tips.
- Simulation expansion matches the intended command order.
- Liquid-specific behavior has been checked in a dry run.
