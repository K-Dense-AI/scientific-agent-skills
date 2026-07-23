# Opentrons Protocol API v2 Quick Reference

Verified against `opentrons==9.1.1` and the official documentation on
2026-07-23. This is a curated authoring reference, not a replacement for the
[ProtocolContext API reference](https://docs.opentrons.com/python-api/reference/protocols/)
and its linked class references.

## Version Baseline

| Robot | Supported API range on current software | Recommended maximum for new robot-specific protocols |
| --- | --- | --- |
| Flex | 2.15–2.29 | 2.29 |
| OT-2 | 2.0–2.28 | 2.28 |

API versions are independent of the installed Python package and robot software.
Choose the lowest API level that includes every required feature. A protocol
specifying a higher level than the robot supports will fail analysis.

```python
metadata = {
    "protocolName": "Example",
    "author": "Your Name",
    "description": "Purpose and scope.",
}
requirements = {"robotType": "Flex", "apiLevel": "2.29"}
```

Rules:

- Flex always requires `requirements`.
- `requirements` is recommended for OT-2 protocols using API 2.15+.
- Put `apiLevel` in exactly one place. When using `requirements`, remove it from
  `metadata`.
- `run(protocol: protocol_api.ProtocolContext)` is the required entry point.

## Features Added After API 2.19

| API | High-value additions |
| --- | --- |
| 2.20 | CSV runtime parameters; liquid presence detection; row, single, and partial-column nozzle layouts |
| 2.21 | `AbsorbanceReaderContext` and `absorbanceReaderV1` |
| 2.22 | `Labware.load_liquid()`, `load_liquid_by_well()`, and `load_empty()`; robot motor control |
| 2.23 | `Well.meniscus()`; labware lids and lid moves |
| 2.24 | Liquid classes; advanced liquid-class complex commands; absolute flow-rate options |
| 2.25 | `FlexStackerContext`; `flexStackerModuleV1`; `flex_96channel_200` |
| 2.26 | Liquid-class support for `flex_96channel_200` |
| 2.27 | Concurrent module actions; dynamic aspirate, dispense, and mix; `capture_image()`; explicit liquid-class tips |
| 2.28 | Flex 20 µL tips; partial-tip return; thermocycler ramp rate; empty tip-rack tracking |
| 2.29 | Protocol step grouping |

See
[Versioning](https://docs.opentrons.com/python-api/versioning/) for complete
behavior changes and robot-software mappings.

## Pipette Load Names

### Flex

| Pipette | Nominal range | Load name |
| --- | ---: | --- |
| 1-Channel 50 µL | 1–50 µL | `flex_1channel_50` |
| 1-Channel 1000 µL | 5–1000 µL | `flex_1channel_1000` |
| 8-Channel 50 µL | 1–50 µL | `flex_8channel_50` |
| 8-Channel 1000 µL | 5–1000 µL | `flex_8channel_1000` |
| 96-Channel 200 µL | 1–200 µL | `flex_96channel_200` |
| 96-Channel 1000 µL | 5–1000 µL | `flex_96channel_1000` |

The 96-channel pipette occupies both mounts. From API 2.16 onward its `mount`
argument is optional.

### OT-2 GEN2

| Pipette | Nominal range | Load name |
| --- | ---: | --- |
| P20 single | 1–20 µL | `p20_single_gen2` |
| P20 multi | 1–20 µL | `p20_multi_gen2` |
| P300 single | 20–300 µL | `p300_single_gen2` |
| P300 multi | 20–300 µL | `p300_multi_gen2` |
| P1000 single | 100–1000 µL | `p1000_single_gen2` |

GEN1 OT-2 pipettes have different load names. Check
[Loading Pipettes](https://docs.opentrons.com/python-api/pipettes/loading/)
instead of guessing.

## Flex Tip Compatibility

| Pipette family | Compatible Flex tip-rack capacities |
| --- | --- |
| `flex_1channel_50`, `flex_8channel_50` | 20 µL, 50 µL |
| `flex_96channel_200` | 20 µL, 50 µL, 200 µL |
| `flex_1channel_1000`, `flex_8channel_1000`, `flex_96channel_1000` | 50 µL, 200 µL, 1000 µL |

Filter-tip load names insert `_filtertiprack_`, for example
`opentrons_flex_96_filtertiprack_200ul`.

Full-rack pickup by a Flex 96-channel pipette requires the Flex tip-rack
adapter. Partial pickup by that pipette must use a rack directly on the deck,
without the adapter.

## ProtocolContext

### Hardware and deck

```python
labware = protocol.load_labware(load_name, location, label=None)
adapter = protocol.load_adapter(load_name, location)
module = protocol.load_module(module_name, location=None)
pipette = protocol.load_instrument(
    instrument_name,
    mount,
    tip_racks=[tiprack],
)
trash = protocol.load_trash_bin("A3")  # Flex, API 2.16+
chute = protocol.load_waste_chute()     # Flex, fixed at D3
```

Useful methods:

- `load_labware_from_definition(definition, location, label=None)`
- `move_labware(labware, new_location, use_gripper=...)`
- `load_lid_stack(load_name, location, quantity)`
- `move_lid(source_location, new_location, use_gripper=...)`
- `define_liquid(name, description=None, display_color=None)`
- `get_liquid_class(name, version=None)` — API 2.24+
- `define_liquid_class(name, properties, display_name)` — API 2.24+

### Execution and organization

- `comment(msg)` — adds analysis-time text to the run log.
- `pause(msg=None)` — waits for the operator to resume in the App/touchscreen.
- `delay(seconds=0, minutes=0, msg=None)` — blocking delay.
- `home()` — homes robot axes.
- `is_simulating()` — identify local or App analysis.
- `group_steps(name, description=None)` — context manager, API 2.29.
- `create_and_start_step_group(name, description=None)` — returns a group whose
  `end_group()` method closes it, API 2.29.
- `capture_image()` — captures from the built-in camera, API 2.27.

Step groups only organize source and visualization; they do not change
execution.

## InstrumentContext

### Tips

```python
pipette.pick_up_tip()
pipette.drop_tip()
pipette.return_tip()
pipette.reset_tipracks()
```

In API 2.28+, `tiprack.set_empty()` can mark a rack empty so returned tips may be
tracked there. Only return tips when the protocol's contamination policy allows
it.

### Building-block commands

```python
pipette.aspirate(volume, source)
pipette.dispense(volume, destination, push_out=5)
pipette.air_gap(volume)
pipette.blow_out(destination.top())
pipette.touch_tip(destination)
pipette.mix(repetitions, volume, destination)
pipette.move_to(destination.top())
```

Use `rate=` as a multiplier of the pipette's configured flow rate, or supported
absolute flow-rate arguments when the API level provides them. Do not supply
both forms for the same action.

API 2.27 adds `end_location` and `movement_delay` to aspirate and dispense, plus
`dynamic_mix()` for start-to-end movement during repeated aspiration and
dispensing.

### Complex commands

```python
pipette.transfer(volume, source, destination, new_tip="always")
pipette.distribute(volume, source, destinations, new_tip="once")
pipette.consolidate(volume, sources, destination, new_tip="always")
```

Common options include:

- `new_tip`: `"always"`, `"once"`, or `"never"`; newer API levels add
  additional policies for some commands.
- `mix_before=(repetitions, volume)`
- `mix_after=(repetitions, volume)`
- `touch_tip=True`
- `blow_out=True`
- `blowout_location=...`
- `disposal_volume=...`
- `trash_location=...`

Supported options differ by command and API level. Check the exact signature in
the
[Instrument API reference](https://docs.opentrons.com/python-api/reference/instruments/)
before using uncommon options.

### Liquid-class commands, Flex only

```python
water = protocol.get_liquid_class("water")

pipette.transfer_with_liquid_class(
    liquid_class=water,
    volume=50,
    source=reservoir["A1"],
    dest=plate["A1"],
    new_tip="always",
    trash_location=trash,
)
```

Related methods are `distribute_with_liquid_class()` and
`consolidate_with_liquid_class()`. Opentrons-verified classes include water,
80% ethanol, and 50% glycerol. Compatibility depends on the exact Flex pipette
and tip combination.

## Labware and Wells

### Accessors

```python
plate["A1"]
plate.wells()
plate.wells_by_name()
plate.rows()
plate.rows_by_name()
plate.columns()
plate.columns_by_name()
```

Labware iteration is generally column-major. Use named wells or explicit lists
when order is safety-critical.

### Locations

```python
well.top(z=-1)
well.bottom(z=2)
well.center()
well.meniscus(z=0, target="start")  # API 2.23+
```

`meniscus()` depends on declared or measured liquid volume. Validate liquid
height behavior on hardware before relying on it for low-volume aspiration.

### Liquid setup visualization, API 2.22+

```python
buffer = protocol.define_liquid(
    name="Buffer",
    description="Assay buffer",
    display_color="#1F77B4",
)

reservoir.load_liquid(
    wells=["A1"],
    volume=10_000,
    liquid=buffer,
)

plate.load_liquid_by_well(
    volumes={"A1": 50, "B1": 50},
    liquid=buffer,
)

plate.load_empty(wells=["A2", "B2"])
```

`Well.load_liquid()` is deprecated for API 2.22+ protocols.

## Runtime Parameters

Define parameters outside `run()`:

```python
def add_parameters(parameters: protocol_api.ParameterContext) -> None:
    parameters.add_int(
        variable_name="sample_count",
        display_name="Sample count",
        default=8,
        minimum=1,
        maximum=96,
    )
    parameters.add_bool(
        variable_name="dry_run",
        display_name="Dry run",
        default=False,
    )
```

Read them during execution:

```python
sample_count = protocol.params.sample_count
dry_run = protocol.params.dry_run
```

Methods:

- `add_bool(...)`
- `add_int(...)`
- `add_float(...)`
- `add_str(...)`
- `add_csv_file(...)` — API 2.20+, no default, at most one CSV parameter per
  run.

Parameter display names are limited to 30 characters and descriptions to 100
characters. Numeric parameters require either a min/max range or fixed choices.

## Liquid Presence and Height

Flex pressure-sensing pipettes support:

- `detect_liquid_presence(well)`
- `require_liquid_presence(well)`
- `measure_liquid_height(well)`
- `liquid_presence_detection=True` in `load_instrument()`
- Runtime toggling with `pipette.liquid_presence_detection`

Detection requires a fresh, dry, empty tip. It can add substantial run time,
and not every channel on a multi-channel pipette contains a pressure sensor.

## Partial Nozzle Layouts

```python
from opentrons.protocol_api import ALL, COLUMN

pipette.configure_nozzle_layout(
    style=COLUMN,
    start="A12",
    tip_racks=[partial_tip_rack],
)

# Restore full-rack pickup later.
pipette.configure_nozzle_layout(
    style=ALL,
    tip_racks=[full_tip_rack],
)
```

Available constants include `ALL`, `COLUMN`, `ROW`, `SINGLE`, and
`PARTIAL_COLUMN`, subject to pipette and API support. An incorrect target well
can place nozzles outside the labware and cause a physical crash. Follow the
deck-edge and tip-rack-adapter rules in
[Partial Tip Pickup](https://docs.opentrons.com/python-api/pipettes/partial-tip-pickup/).

## Module Load Names

| Module | Load name | Minimum API |
| --- | --- | ---: |
| Temperature Module GEN1 | `temperature module` | 2.0 |
| Temperature Module GEN2 | `temperature module gen2` | 2.3 |
| Thermocycler GEN1 | `thermocycler module` | 2.0 |
| Thermocycler GEN2 | `thermocyclerModuleV2` | 2.13 |
| Heater-Shaker GEN1 | `heaterShakerModuleV1` | 2.13 |
| Magnetic Block GEN1 | `magneticBlockV1` | 2.15 |
| Absorbance Plate Reader | `absorbanceReaderV1` | 2.21 |
| Flex Stacker | `flexStackerModuleV1` | 2.25 |

Module availability also depends on robot model and physical generation. See
`modules_and_deck.md` before choosing a load name.

## Simulation Entrypoints

```bash
# Flex API 2.29
uv run --with "opentrons==9.1.1" opentrons_simulate protocol.py

# OT-2 API 2.28 compatibility simulation
uv run --with "opentrons==9.0.0" opentrons_simulate protocol.py
```

Python integrations may use `opentrons.simulate.simulate()` with an opened
protocol file. `opentrons==9.1.1` rejects OT-2 protocols after the release-line
split, so complete OT-2 validation in the current OT-2 App. Do not use
`opentrons_execute` from a workstation as a substitute for App analysis and
controlled robot operation.
