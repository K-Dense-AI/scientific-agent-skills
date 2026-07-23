# Modules and Deck Guide

Module compatibility is both an API question and a physical hardware question.
Confirm the robot model, module generation, caddy or adapter, firmware, deck
location, and labware before authoring commands.

## Robot Compatibility

| Hardware | Flex | OT-2 | Protocol API load name |
| --- | --- | --- | --- |
| Absorbance Plate Reader | Yes | No | `absorbanceReaderV1` |
| Flex Stacker | Yes | No | `flexStackerModuleV1` |
| Heater-Shaker GEN1 | Yes | Yes | `heaterShakerModuleV1` |
| Magnetic Block GEN1 | Yes | No | `magneticBlockV1` |
| Magnetic Module GEN1/GEN2 | No | Yes | `magnetic module` / `magnetic module gen2` |
| Temperature Module GEN2 | Yes | Yes | `temperature module gen2` |
| Thermocycler GEN2 | Yes | Yes | `thermocyclerModuleV2` |

Notes:

- Flex uses the passive Magnetic Block. The powered OT-2 Magnetic Module is not
  supported on Flex.
- Flex requires Thermocycler GEN2 for gripper-compatible operation.
- Older module generations may be supported only on OT-2. Match the load name
  to the exact hardware label.
- The HEPA/UV accessory is part of Flex operations but is not loaded and
  controlled as a Protocol API module.

See the current
[Flex module list](https://docs.opentrons.com/flex/modules/) and
[OT-2 module list](https://docs.opentrons.com/ot-2/modules/) before relying on
this snapshot.

## Deck Models

### Flex

- Working deck: A1–D3.
- Staging area: A4–D4; pipettes cannot reach it, but the Gripper can.
- Trash bins are loaded explicitly in supported column-1 or column-3 slots.
- The waste chute is loaded with `protocol.load_waste_chute()` and occupies D3.
- Powered module caddies and staging slots can conflict in the same row.
- Column-4 hardware can reserve or move through the corresponding column-3
  position.

```python
trash = protocol.load_trash_bin("A3")
chute = protocol.load_waste_chute()  # D3 only; do not load both into D3
```

Load only the fixtures physically installed for the run.

### OT-2

- User deck slots: 1–11.
- Fixed trash: slot 12.
- Do not call `load_trash_bin()` for the fixed trash.
- No Gripper or staging area.
- Labware moves are manual operator actions.

## Module Loading

```python
heater_shaker = protocol.load_module(
    module_name="heaterShakerModuleV1",
    location="D1",
)
```

Loading a powered module makes it a run requirement. The App will prevent the
run from starting unless the expected connected module is available.

Load labware through the module:

```python
plate = heater_shaker.load_labware(
    "corning_96_wellplate_360ul_flat",
    label="Mixing Plate",
)
```

For a separate adapter:

```python
temperature_module = protocol.load_module(
    "temperature module gen2",
    "D3",
)
adapter = temperature_module.load_adapter(
    "opentrons_96_well_aluminum_block"
)
plate = adapter.load_labware(
    "opentrons_96_wellplate_200ul_pcr_full_skirt"
)
```

The API generally cannot prove that every unusual module, adapter, and labware
combination is physically valid. Check the official compatibility list.

## Temperature Module

```python
temperature_module.set_temperature(celsius=4)
# Pipetting or incubation commands...
temperature_module.deactivate()
```

`set_temperature()` blocks until the target is reached. In API 2.27+,
`start_set_temperature()` can run concurrently and returns a task. Wait for the
task before relying on the target temperature.

Operational checks:

- Use the correct aluminum block or adapter.
- Include condensation and cold-surface effects in the wet-lab method.
- Deactivate when the method no longer requires control.
- Do not assume the liquid itself instantly reaches the module temperature.

## Heater-Shaker

Typical sequence:

```python
heater_shaker.close_labware_latch()
heater_shaker.set_and_wait_for_temperature(37)
heater_shaker.set_and_wait_for_shake_speed(1000)
protocol.delay(minutes=5)
heater_shaker.deactivate_shaker()
heater_shaker.deactivate_heater()
```

The exact temperature method name depends on API behavior. Current context
methods include `set_target_temperature()`,
`set_and_wait_for_temperature()`, `wait_for_temperature()`,
`set_and_wait_for_shake_speed()`, `deactivate_shaker()`, and
`deactivate_heater()`.

Always:

- Close the latch before shaking.
- Stop shaking before opening the latch or moving labware.
- Check maximum speed for the exact labware and fill volume.
- Account for clearance restrictions in neighboring slots.

API 2.27+ provides nonblocking shake and temperature operations for concurrent
work. Keep task handles and wait before a dependent step.

## Thermocycler

```python
thermocycler = protocol.load_module("thermocyclerModuleV2")
plate = thermocycler.load_labware(
    "opentrons_96_wellplate_200ul_pcr_full_skirt"
)

thermocycler.open_lid()
# Pipette into plate.
thermocycler.close_lid()
thermocycler.set_lid_temperature(temperature=105)
thermocycler.set_block_temperature(
    temperature=95,
    hold_time_seconds=180,
    block_max_volume=25,
)
thermocycler.execute_profile(
    steps=[
        {"temperature": 95, "hold_time_seconds": 15},
        {"temperature": 60, "hold_time_seconds": 30},
        {"temperature": 72, "hold_time_seconds": 30},
    ],
    repetitions=35,
    block_max_volume=25,
)
thermocycler.set_block_temperature(
    temperature=4,
    block_max_volume=25,
)
thermocycler.deactivate_lid()
```

API 2.28 adds an optional `ramp_rate` to block-temperature commands.

Checks:

- Correct plate and seal for the thermocycler.
- Lid closed before heating and cycling.
- `block_max_volume` matches the actual per-well reaction volume.
- Final hold behavior is intentional.
- Lid and block are deactivated or left active according to the method.
- No deck item conflicts with the thermocycler footprint.

## Magnetic Block, Flex

The Magnetic Block is passive. It has no engage or disengage methods.
Separation happens by moving compatible labware onto and off the block:

```python
magnetic_block = protocol.load_module("magneticBlockV1", "D1")

protocol.move_labware(
    labware=plate,
    new_location=magnetic_block,
    use_gripper=True,
)
protocol.delay(minutes=5)
protocol.move_labware(
    labware=plate,
    new_location="C1",
    use_gripper=True,
)
```

Confirm gripper compatibility and plate orientation. Avoid aspirating beads by
validating settle time, aspiration side, bottom clearance, and flow rate.

## Magnetic Module, OT-2

The powered Magnetic Module is OT-2-only:

```python
magnetic_module = protocol.load_module(
    "magnetic module gen2",
    "1",
)
plate = magnetic_module.load_labware(
    "nest_96_wellplate_2ml_deep"
)

magnetic_module.engage(height_from_base=6.5)
protocol.delay(minutes=5)
magnetic_module.disengage()
```

Engage height is labware- and assay-specific. Do not copy an arbitrary height
from another plate. The Magnetic Module is discontinued but remains supported
for existing OT-2 hardware.

## Absorbance Plate Reader, Flex API 2.21+

The reader is Flex-only and loads in A3–D3. Its caddy also uses the
corresponding column-4 location for lid travel.

Required workflow:

1. Load the module.
2. Close the lid with no plate inside.
3. Initialize the reader.
4. Open the lid.
5. Move a compatible plate onto the module with the Gripper.
6. Close the lid.
7. Read.

```python
reader = protocol.load_module(
    module_name="absorbanceReaderV1",
    location="D3",
)
plate = protocol.load_labware(
    "corning_96_wellplate_360ul_flat",
    "C2",
)

reader.close_lid()
reader.initialize(
    mode="multi",
    wavelengths=[450, 562, 600],
)
reader.open_lid()
protocol.move_labware(
    labware=plate,
    new_location=reader,
    use_gripper=True,
)
reader.close_lid()
data = reader.read(export_filename="plate_data")
```

Default hardware wavelengths are 450, 562, 600, and 650 nm.

`read()` returns:

```python
dict[int, dict[str, float]]
```

The first key is wavelength; the second is well name. In simulation every
measurement is zero, and no output file is written. Guard calculations that
would divide by a reading:

```python
if not protocol.is_simulating():
    normalized = data[450]["A1"] / data[450]["H12"]
```

Do not move the plate-reader lid manually.

## Flex Stacker, API 2.25+

Up to four Stackers attach to the right side of Flex. Each shuttle is addressed
as a column-4 location:

```python
stacker = protocol.load_module(
    module_name="flexStackerModuleV1",
    location="A4",
)
```

Configure one labware type per Stacker:

```python
stacker.set_stored_labware(
    load_name="opentrons_flex_96_tiprack_200ul",
    count=5,
    lid="opentrons_flex_tiprack_lid",
)
```

Retrieve and move:

```python
tip_rack = stacker.retrieve()
protocol.move_labware(
    labware=tip_rack,
    new_location="B2",
    use_gripper=True,
)
```

Store:

```python
protocol.move_labware(
    labware=plate,
    new_location=stacker,
    use_gripper=True,
)
stacker.store()
```

`fill()` and `empty()` pause for manual loading or unloading.

Constraints:

- Configure stored labware before `retrieve()` or `store()`.
- Only one labware type per Stacker at a time.
- Flex tip racks need compatible lids to stack.
- The Stacker does not identify what an operator physically loaded.
- Reserve the corresponding row's shuttle path and check column-3 conflicts.
- Use capacity helper methods for the exact labware height.

## Moving Labware and Lids

Flex automated move:

```python
protocol.move_labware(
    labware=plate,
    new_location="C2",
    use_gripper=True,
)
```

Manual move:

```python
protocol.move_labware(
    labware=plate,
    new_location="C2",
    use_gripper=False,
)
```

A manual move pauses for the operator. Make sure the message and run setup make
the source and destination unambiguous.

API 2.23+ supports lid stacks and `move_lid()`. Confirm lid and labware
compatibility, orientation, stack quantity, and disposal location.

## Concurrent Module Actions, API 2.27+

Concurrent methods can overlap long module actions with independent pipetting:

- Temperature: `start_set_temperature()`.
- Heater-Shaker: nonblocking temperature or shake-speed methods.
- Thermocycler: `start_set_block_temperature()`,
  `start_set_lid_temperature()`, and `start_execute_profile()`.

Pattern:

1. Start the operation and keep the returned task.
2. Perform only physically independent commands.
3. Wait for the task before any step that assumes completion.

Do not create concurrency merely to shorten runtime. Check deck access,
vibration, thermal dependencies, and collision risk.

## Module State Checklist

- Correct robot and module generation.
- Correct load name and API level.
- Valid deck slot and no footprint conflict.
- Correct caddy, adapter, and labware.
- Latch or lid state is safe before motion.
- Temperature, speed, and timing are validated for the method.
- Every started concurrent task is awaited.
- Gripper moves use compatible labware and clear paths.
- Modules are deactivated or intentionally held at protocol end.
- App analysis and a physical dry run cover the exact configuration.
