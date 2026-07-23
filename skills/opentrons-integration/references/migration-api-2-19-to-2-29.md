# Migrating API 2.19 Protocols to the Current Baseline

This guide updates protocols written around robot software 7.3.1 and Protocol
API 2.19 to the 2026-07-23 baseline:

- Flex: Protocol API 2.29.
- OT-2: Protocol API 2.28.
- Flex local simulator: `opentrons==9.1.1`.
- OT-2 local compatibility simulator: `opentrons==9.0.0`, followed by analysis
  in the current OT-2 App.

Do not mechanically change only the API string. Newer levels can change command
validation and behavior.

## 1. Identify the Target Robot

API 2.29 is not supported on OT-2 at this baseline.

```python
# Flex
requirements = {"robotType": "Flex", "apiLevel": "2.29"}

# OT-2
requirements = {"robotType": "OT-2", "apiLevel": "2.28"}
```

Use one `apiLevel` declaration. Older files often put it in both `metadata` and
`requirements`; current analysis rejects that.

Before:

```python
metadata = {"apiLevel": "2.19", "protocolName": "Example"}
requirements = {"robotType": "Flex", "apiLevel": "2.19"}
```

After:

```python
metadata = {"protocolName": "Example"}
requirements = {"robotType": "Flex", "apiLevel": "2.29"}
```

If the protocol must remain compatible with older robot software, keep 2.19 and
apply only changes available at that level.

## 2. Replace Incorrect Flex Pipette Names

Current Flex load names describe channels and range:

| Old or incorrect pattern | Current choice |
| --- | --- |
| `p50_single_flex` | `flex_1channel_50` |
| `p50_multi_flex` | `flex_8channel_50` |
| `p1000_single_flex` | `flex_1channel_1000` |
| `p1000_multi_flex` | `flex_8channel_1000` |
| `p300_single_flex` | No direct equivalent; choose `flex_1channel_50` or `flex_1channel_1000` from validated volume needs |
| `p300_multi_flex` | No direct equivalent; choose `flex_8channel_50` or `flex_8channel_1000` |

Also available:

- `flex_96channel_200` — API 2.25+.
- `flex_96channel_1000`.

Do not choose solely by the largest transfer. Check every operation against the
pipette's lower and upper range and compatible tip capacities.

OT-2 GEN2 names remain `p20_*_gen2`, `p300_*_gen2`, and
`p1000_single_gen2`.

## 3. Make Flex Trash Explicit

Flex API 2.16+ protocols should load the fixture actually installed:

```python
trash = protocol.load_trash_bin("A3")
```

Or:

```python
chute = protocol.load_waste_chute()
```

OT-2 keeps its fixed trash in slot 12 and does not call `load_trash_bin()`.

If both a trash bin and waste chute exist, set the intended pipette trash
container or pass the documented `trash_location` to complex commands.

## 4. Update Liquid Loading, API 2.22+

`Well.load_liquid()` is deprecated, and `Well.load_empty()` does not exist in
the current package.

Before:

```python
reservoir["A1"].load_liquid(liquid=buffer, volume=10_000)
plate["A1"].load_empty()
```

After:

```python
reservoir.load_liquid(
    wells=["A1"],
    volume=10_000,
    liquid=buffer,
)
plate.load_empty(wells=["A1"])
```

For varying volumes:

```python
plate.load_liquid_by_well(
    volumes={"A1": 20, "B1": 30},
    liquid=sample,
)
```

## 5. Update Adapter Loading

`ProtocolContext.load_labware_on_adapter()` is not a current method.

Load the adapter, then call the adapter's method:

```python
adapter = protocol.load_adapter(
    "opentrons_96_well_aluminum_block",
    "D1",
)
plate = adapter.load_labware(
    "opentrons_96_wellplate_200ul_pcr_full_skirt"
)
```

Some `load_labware()` calls also accept an `adapter=` load name for supported
stacks. Use the pattern shown for the exact hardware in current documentation.

## 6. Fix Flex Magnetic Workflows

The powered Magnetic Module is OT-2-only.

Old Flex pattern:

```python
magnetic_module = protocol.load_module(
    "magnetic module gen2",
    "C2",
)
magnetic_module.engage(height_from_base=6.5)
```

Current Flex pattern:

```python
magnetic_block = protocol.load_module("magneticBlockV1", "C2")
protocol.move_labware(
    labware=plate,
    new_location=magnetic_block,
    use_gripper=True,
)
protocol.delay(minutes=5)
protocol.move_labware(
    labware=plate,
    new_location="B2",
    use_gripper=True,
)
```

The Magnetic Block is passive and has no `engage()` or `disengage()` method.

## 7. Fix Absorbance Plate Reader Calls

The reader was added in API 2.21 and is Flex-only. It does not accept
`read(wavelengths=[...])`.

Incorrect:

```python
result = plate_reader.read(wavelengths=[450, 650])
```

Correct sequence:

```python
reader = protocol.load_module("absorbanceReaderV1", "D3")

reader.close_lid()
reader.initialize(mode="multi", wavelengths=[450, 650])
reader.open_lid()
protocol.move_labware(
    labware=plate,
    new_location=reader,
    use_gripper=True,
)
reader.close_lid()
result = reader.read(export_filename="absorbance")
```

The plate reader returns zeros during simulation. Avoid divide-by-zero logic in
the simulation branch.

## 8. Remove Unsupported Complex-Command Options

Do not preserve options merely because an old reference listed them.

For example, `gradient=(start, end)` is not a supported generic `transfer()`
option in the current API. Build a validated volume list explicitly:

```python
volumes = [10, 20, 30, 40]
pipette.transfer(
    volume=volumes,
    source=reservoir["A1"],
    dest=plate.wells()[:4],
    new_tip="always",
)
```

Check uncommon options against the exact current method and API level. The
supported options for standard and liquid-class commands are not identical.

## 9. Revisit Behavior Changes

### API 2.20

- Liquid presence detection.
- CSV runtime parameters.
- Expanded partial-nozzle layouts.

### API 2.21

- Absorbance Plate Reader.
- Liquid presence checks only the first aspiration of a `mix()` cycle.

### API 2.22

- Labware-level liquid loading.
- `Well.load_liquid()` deprecated.
- Low-level robot motor control.

### API 2.23

- Meniscus locations.
- Labware lids and lid moves.
- Labware offset behavior aligned with newer App checks.

### API 2.24

- Verified and custom liquid classes.
- `transfer_with_liquid_class()`, `distribute_with_liquid_class()`, and
  `consolidate_with_liquid_class()`.
- Additional flow, delay, position, and push-out options.

### API 2.25

- Flex Stacker.
- Flex 96-Channel 200 µL pipette.

### API 2.26

- Liquid-class support for the 96-channel 200 µL pipette.

### API 2.27

- Concurrent module tasks.
- Dynamic aspirate, dispense, and mix paths.
- Built-in camera capture.
- Explicit tips for liquid-class transfers.

### API 2.28

- Flex 20 µL tips.
- Improved return of partially picked-up tips.
- Absolute blowout customization.
- Thermocycler ramp-rate control.
- `set_empty()` tip-rack state.
- Errors for unsafe `touch_tip()` use in large spaces.

### API 2.29

- Step grouping in source and protocol visualization.
- Flex-only at this migration baseline.

## 10. Revisit Module and Deck Assumptions

Check for:

- Flex trash or waste chute not represented in old code.
- Staging area and column-3 conflicts.
- New Gripper or lid moves.
- Heater-Shaker latch state.
- Thermocycler generation and footprint.
- Plate-reader caddy and lid travel.
- Stacker shuttle paths.
- Tip-rack adapter requirements for full versus partial 96-channel pickup.

API analysis has improved, so a newly raised deck-conflict error may reveal an
old protocol assumption that was never physically safe.

## 11. Revalidate Tip and Volume Policies

Do not assume newer pipetting behavior produces assay-equivalent results.

- Recalculate tip count.
- Recalculate source and dead volume.
- Confirm complex-command expansion in the run log.
- Requalify flow rates, mix behavior, bottom clearances, air gaps, and blowout.
- Recheck contamination policy.
- Recheck multi-channel and partial-nozzle well targeting.

## 12. Migration Test Plan

1. Preserve the original protocol and expected run log.
2. Update declarations and load names.
3. Replace deprecated or invalid calls.
4. Simulate with the robot-specific pin: `opentrons==9.1.1` for Flex or
   `opentrons==9.0.0` for OT-2.
5. Compare command order, tip use, source/destination mapping, and module states.
6. Test every runtime parameter branch.
7. Import into the correct App and target robot.
8. Resolve every analysis warning and error.
9. Perform a nonhazardous dry run.
10. Requalify assay performance before production use.

Do not claim a migration is equivalent solely from a successful simulation.
