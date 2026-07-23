---
name: opentrons-integration
description: Author, review, migrate, simulate, and troubleshoot official Opentrons Python Protocol API v2 protocols for Flex and OT-2 robots. Use for robot-specific liquid handling, deck and labware setup, pipettes, modules, runtime parameters, liquid classes, and Opentrons App analysis. Use pylabrobot instead when one workflow must support multiple robot vendors.
license: MIT
compatibility: Requires Python 3.10+ and uv for local simulation. Flex examples target opentrons 9.1.1 and API 2.29; the separate OT-2 line targets API 2.28 and uses opentrons 9.0.0 as its local compatibility simulator. Physical execution requires compatible hardware, current robot software, and the appropriate Opentrons App.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
metadata:
  version: "2.0"
  skill-author: "K-Dense Inc."
---

# Opentrons Integration

## Overview

Create production-minded Python Protocol API v2 protocols for Opentrons Flex and
OT-2. This skill covers protocol structure, hardware and deck configuration,
liquid handling, runtime customization, module control, simulation, and safe
deployment.

The verified baseline as of **2026-07-23** is:

- `opentrons==9.1.1` for reproducible Flex simulation.
- `opentrons==9.0.0` for local OT-2 API 2.28 compatibility simulation.
- Flex supports API levels 2.15 through 2.29 on current software.
- OT-2 supports API levels 2.0 through 2.28 on current software.
- API 2.29 is Flex-only at this baseline. Do not put `2.29` in an OT-2 protocol.

Read `references/sources.md` for the upstream documentation used for this
snapshot. Recheck the official versioning page before targeting newer robot
software.

## Safety Boundary

Opentrons protocols control physical equipment. Never treat successful Python
syntax or local simulation as permission to run on a robot.

Before live execution:

1. Simulate locally with the same pinned `opentrons` version used for authoring.
2. Import the protocol into the correct Opentrons App and require successful
   analysis.
3. Verify robot model, software, pipettes, mounts, modules, adapters, labware
   definitions, deck fixtures, tip count, source volumes, dead volumes, and
   destination capacity.
4. Review the run preview and deck map with the operator.
5. Perform a slow dry run with nonhazardous liquid when geometry, custom
   labware, partial tip pickup, or gripper moves are new.
6. Keep the emergency stop accessible and follow site-specific biosafety,
   chemical-safety, and contamination-control procedures.

Simulation cannot verify physical calibration, liquid properties, meniscus
behavior, labware manufacturing tolerances, cap or seal removal, tubing, or all
possible collisions.

## Choose the Right Interface

Use this skill for Python files imported into the Opentrons App and run through
the Protocol API.

- Use **Protocol Designer** for supported no-code workflows.
- Use **PyLabRobot** for a hardware-agnostic workflow spanning vendors.
- Treat the robot's HTTP API as a separate integration surface. If direct HTTP
  control is explicitly required, use the OpenAPI document served by the target
  robot and do not infer endpoints from Protocol API methods.

## Required Intake

Do not write final protocol code until these facts are known:

- Robot: Flex or OT-2, plus installed robot software.
- Pipette model, volume range, channel count, and mount.
- Modules and generations; Flex Gripper or Stacker availability.
- Exact labware API load names and custom definition files, if any.
- Deck fixtures: Flex trash bin, waste chute, staging slots, or Stackers.
- Source volumes, destination volumes, dead volume, mixing needs, and liquid
  characteristics.
- Tip policy: contamination boundaries, reuse policy, filters, partial pickup,
  and total tips.
- Operator interventions, incubation timing, runtime parameters, and output
  files.
- Acceptance criteria: tolerated volume error, required controls, and dry-run
  plan.

If any physical configuration is uncertain, produce a parameterized draft and
an explicit assumptions list rather than guessing.

## Install and Simulate

Flex:

```bash
uv run --with "opentrons==9.1.1" opentrons_simulate protocol.py
```

OT-2 API 2.28:

```bash
uv run --with "opentrons==9.0.0" opentrons_simulate protocol.py
```

The 9.1.1 package intentionally rejects OT-2 protocols after the Flex/OT-2
release-line split. Always complete OT-2 analysis in the current OT-2 App.

For a dedicated Flex environment:

```bash
uv venv --python 3.10
uv pip install --python .venv/bin/python -r skills/opentrons-integration/requirements-flex.txt
.venv/bin/opentrons_simulate protocol.py
```

Use `requirements-ot2.txt` instead for an OT-2 compatibility environment. On
Windows, invoke the executable from `.venv\Scripts\opentrons_simulate.exe`.
Local simulation is for Python protocols; import Protocol Designer JSON files
into the appropriate Opentrons App instead.

## Protocol Skeletons

### Flex, API 2.29

For Flex, `requirements` is mandatory. Put `apiLevel` only in `requirements`,
not in both `metadata` and `requirements`.

```python
from opentrons import protocol_api

metadata = {
    "protocolName": "Flex transfer",
    "author": "Your Name",
    "description": "Transfer buffer into a plate.",
}
requirements = {"robotType": "Flex", "apiLevel": "2.29"}


def run(protocol: protocol_api.ProtocolContext) -> None:
    tips = protocol.load_labware(
        "opentrons_flex_96_tiprack_200ul", "D1"
    )
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "D2")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "C2")
    protocol.load_trash_bin("A3")
    pipette = protocol.load_instrument(
        "flex_1channel_1000", "left", tip_racks=[tips]
    )

    pipette.transfer(
        100,
        reservoir["A1"],
        plate["A1"],
        new_tip="always",
    )
```

### OT-2, API 2.28

For OT-2 API 2.15 and later, a `requirements` block is recommended. OT-2 has a
fixed trash in slot 12; do not call `load_trash_bin()`.

```python
from opentrons import protocol_api

metadata = {
    "protocolName": "OT-2 transfer",
    "author": "Your Name",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.28"}


def run(protocol: protocol_api.ProtocolContext) -> None:
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", "1")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "2")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "3")
    pipette = protocol.load_instrument(
        "p300_single_gen2", "left", tip_racks=[tips]
    )
    pipette.transfer(100, reservoir["A1"], plate["A1"])
```

Use the lowest API level that provides every required feature when a protocol
must run across a mixed software fleet. Use the current maximum only when the
workflow needs its behavior or capabilities.

## Authoring Workflow

### 1. Select robot and API level

Check the maximum supported API in the App under the robot's advanced settings.
Map every requested feature to its minimum API level using
`references/api_reference.md`.

Important gates:

- 2.20: CSV runtime parameters, liquid presence detection, expanded partial
  nozzle layouts.
- 2.21: Absorbance Plate Reader.
- 2.22: current labware-level liquid loading methods.
- 2.23: meniscus locations and labware lids.
- 2.24: liquid classes and liquid-class complex commands.
- 2.25: Flex Stacker and Flex 96-Channel 200 µL pipette.
- 2.27: dynamic pipetting and concurrent module actions.
- 2.28: 20 µL Flex tips, improved partial-tip return, and thermocycler ramp rate.
- 2.29: step grouping; Flex only at the verified baseline.

### 2. Build the deck explicitly

- Use exact load names from the official Labware Library.
- Load Flex trash bins or the waste chute explicitly.
- Account for module footprints, staging slots, Stacker shuttles, gripper paths,
  and tall-labware adjacency.
- Load labware on adapters or module contexts in the documented order.
- Never substitute a similarly named labware definition; geometry and offsets
  are part of the protocol's safety model.

See `references/modules_and_deck.md`.

### 3. Select pipettes and tips

Current load names are:

- Flex: `flex_1channel_50`, `flex_1channel_1000`,
  `flex_8channel_50`, `flex_8channel_1000`,
  `flex_96channel_200`, `flex_96channel_1000`.
- OT-2 GEN2: `p20_single_gen2`, `p20_multi_gen2`,
  `p300_single_gen2`, `p300_multi_gen2`, `p1000_single_gen2`.

Check that every requested volume is within the configured pipette and tip
range. A 100 nL operation is not an Opentrons pipetting task.

### 4. Choose a liquid-handling layer

- Use `aspirate()`, `dispense()`, `mix()`, `air_gap()`, `blow_out()`, and
  `touch_tip()` for explicit control.
- Use `transfer()`, `distribute()`, and `consolidate()` for standard movements.
- On Flex, consider `transfer_with_liquid_class()`,
  `distribute_with_liquid_class()`, or `consolidate_with_liquid_class()` for
  Opentrons-verified aqueous, volatile, or viscous behavior.
- Use dynamic start/end locations or `dynamic_mix()` only when API 2.27+ and the
  geometry has been reviewed.

Model contamination boundaries before optimizing tips. Never reuse a tip across
unrelated samples merely to reduce consumables. See
`references/liquid_handling.md`.

### 5. Add setup information and runtime controls

Use `define_liquid()` and labware-level `load_liquid()` or
`load_liquid_by_well()` to improve setup visualization. Do not use deprecated
`Well.load_liquid()` in new API 2.22+ protocols.

Define operator-controlled values in `add_parameters()` and read them from
`protocol.params`. Validate ranges and use defaults that produce a safe,
meaningful simulation. CSV parameters have no default and only one CSV
parameter can be selected per run.

### 6. Budget resources

Before simulation, calculate:

- Tips or tip sets required under every branch.
- Source volume = delivered volume + mixing loss + disposal volume + dead
  volume + a justified reserve.
- Maximum destination volume after every addition and mix.
- Number of module, adapter, trash, and staging positions.
- Incubation and module timing, including concurrent tasks.

### 7. Validate in layers

1. Compile: `python -m py_compile protocol.py`.
2. Simulate with the pinned package.
3. Inspect the run log for command count, tip changes, pauses, and unexpected
   locations.
4. Import into the appropriate App and require successful analysis.
5. Check protocol visualization, runtime parameter defaults, deck map, module
   setup, and labware offsets.
6. Perform an operator-reviewed dry run before first use.

See `references/validation_and_operations.md`.

## Common Failure Modes

- Using old names such as `p300_single_flex`; use current `flex_*` load names.
- Declaring `apiLevel` in both `metadata` and `requirements`.
- Using API 2.29 for OT-2.
- Forgetting a Flex trash bin or waste chute.
- Loading a Magnetic Module on Flex; use supported Flex magnetic hardware.
- Calling `read(wavelengths=...)` on the plate reader; call `initialize()` first,
  then `read()`.
- Using deprecated `Well.load_liquid()` instead of labware-level methods.
- Assuming simulation verifies calibration, liquid height, or physical
  clearances.
- Passing an unsafe well to a partial-nozzle pipette, which can place tips
  outside labware and cause a crash.
- Using `new_tip="once"` across samples with incompatible contamination
  requirements.

## Bundled Templates

| File | Purpose |
| --- | --- |
| `scripts/basic_protocol_template.py` | Minimal Flex 2.29 transfer with current names |
| `scripts/ot2_basic_protocol_template.py` | Minimal OT-2 2.28 transfer |
| `scripts/serial_dilution_template.py` | Full-plate 1:2 dilution with an 8-channel Flex pipette |
| `scripts/pcr_setup_template.py` | Flex PCR setup and Thermocycler cycling |
| `scripts/runtime_parameters_template.py` | Safe numeric and Boolean runtime parameters |
| `scripts/absorbance_reader_template.py` | Correct Flex plate-reader initialization and read workflow |

Templates are starting points, not validated assays. Replace volumes, labware,
liquids, timing, and tip policies only after checking hardware compatibility and
the wet-lab method.

## Reference Guide

| Reference | Use it for |
| --- | --- |
| `references/api_reference.md` | Current load names, version gates, and high-value methods |
| `references/protocol_authoring.md` | Requirements, labware, runtime parameters, and design workflow |
| `references/liquid_handling.md` | Command selection, liquid classes, sensing, and partial tips |
| `references/modules_and_deck.md` | Module compatibility, deck fixtures, gripper, and Stacker |
| `references/validation_and_operations.md` | Simulation, App analysis, dry runs, and troubleshooting |
| `references/migration-api-2-19-to-2-29.md` | Updating older protocols and this skill's former patterns |
| `references/sources.md` | Official documentation and release sources |
