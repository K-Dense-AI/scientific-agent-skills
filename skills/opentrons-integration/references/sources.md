# Upstream Sources

This skill snapshot was verified on **2026-07-23**. Opentrons publishes robot
software, the desktop/touchscreen Apps, the Python package, and Protocol API
levels on related but distinct release cycles. Recheck time-sensitive facts
before generating a production protocol.

## Verified Baseline

- Stable PyPI package:
  [`opentrons==9.1.1`](https://pypi.org/project/opentrons/), released
  2026-07-13, requiring Python 3.10 or newer. This package targets the current
  Flex release line and implements Protocol API 2.29.
- Local OT-2 API 2.28 compatibility simulation uses `opentrons==9.0.0`, the
  last shared PyPI release that accepts OT-2 protocols at that API level.
- Current robot-software support documented by Opentrons:
  - Flex: API 2.15–2.29.
  - OT-2: API 2.0–2.28.
- API 2.29 and newer use separate Flex and OT-2 software/App release lines.

`opentrons==9.1.1` rejects OT-2 simulation and directs users to the separate
OT-2 App. The target robot's maximum API value and analysis result in the
appropriate App are authoritative for whether a specific protocol can run.

## Core Protocol API Documentation

- [Python Protocol API home](https://docs.opentrons.com/python-api/)
  — current Flex and OT-2 protocol overview and minimal examples.
- [Tutorial](https://docs.opentrons.com/python-api/tutorial/)
  — protocol structure, requirements, labware, trash, pipettes, simulation, and
  App import.
- [Versioning](https://docs.opentrons.com/python-api/versioning/)
  — supported API ranges, robot-software mapping, and changes by API level.
- [ProtocolContext API reference](https://docs.opentrons.com/python-api/reference/protocols/)
  and [InstrumentContext API reference](https://docs.opentrons.com/python-api/reference/instruments/)
  — exact current class and method signatures and navigation to other classes.
- [Protocol examples](https://docs.opentrons.com/python-api/examples/)
  — official ready-made Flex and OT-2 examples.
- [Adapting from OT-2 to Flex](https://docs.opentrons.com/python-api/adapting-ot2-flex/)
  — robot declaration, deck, trash, pipettes, and module migration.

## Pipettes and Liquid Handling

- [Loading Pipettes](https://docs.opentrons.com/python-api/pipettes/loading/)
  — current load names, tip compatibility, trash containers, and liquid
  presence detection.
- [Pipette Characteristics](https://docs.opentrons.com/python-api/pipettes/characteristics/)
  — channels, movement, and flow behavior.
- [Partial Tip Pickup](https://docs.opentrons.com/python-api/pipettes/partial-tip-pickup/)
  — nozzle layouts, target-well rules, adapters, deck reach, and collision
  warnings.
- [Liquid Control](https://docs.opentrons.com/python-api/building-block-commands/liquids/)
  — aspirate, dispense, push out, blowout, touch tip, mix, dynamic mix, and air
  gaps.
- [Complex Commands](https://docs.opentrons.com/python-api/complex-commands/)
  — transfer, distribute, consolidate, order, and parameters.
- [Using Liquid Classes](https://docs.opentrons.com/python-api/liquid-classes/using/)
  — verified class selection and liquid-class transfer methods.
- [Liquid Class Definitions](https://docs.opentrons.com/python-api/liquid-class-definitions/)
  — verified behavior definitions.

## Parameters, Labware, and Deck

- [Runtime Parameters](https://docs.opentrons.com/python-api/runtime-parameters/)
  — overview and use cases.
- [Defining Runtime Parameters](https://docs.opentrons.com/python-api/runtime-parameters/defining/)
  — exact Boolean, numeric, string, and CSV definitions.
- [Labware](https://docs.opentrons.com/python-api/labware/)
  — loading, well access, adapters, liquids, and lids.
- [Moving Labware](https://docs.opentrons.com/python-api/moving-labware/)
  — manual and Gripper moves.
- [Deck Slots](https://docs.opentrons.com/python-api/deck-slots/)
  — Flex and OT-2 labels, staging area, trash, waste chute, and conflicts.
- [Step Grouping](https://docs.opentrons.com/python-api/groups/)
  — API 2.29 grouping methods and protocol visualization.
- [Opentrons Labware Library](https://labware.opentrons.com/)
  — authoritative standard labware load names and definitions.

## Hardware Modules

- [Module Setup](https://docs.opentrons.com/python-api/modules/setup/)
  — load names, API introduction levels, adapters, and labware.
- [Absorbance Plate Reader API](https://docs.opentrons.com/python-api/modules/absorbance-plate-reader/)
  — initialization, lid operations, reading, and output data.
- [Flex Stacker API](https://docs.opentrons.com/python-api/modules/flex-stacker/)
  — storage configuration, retrieve/store, capacity, fill, and empty.
- [Heater-Shaker API](https://docs.opentrons.com/python-api/modules/heater-shaker/)
  — latch, temperature, and shake control.
- [Magnetic Block API](https://docs.opentrons.com/python-api/modules/magnetic-block/)
  — passive Flex separation workflow.
- [Magnetic Module API](https://docs.opentrons.com/python-api/modules/magnetic-module/)
  — powered OT-2 module control.
- [Temperature Module API](https://docs.opentrons.com/python-api/modules/temperature-module/)
  — blocking and concurrent temperature control.
- [Thermocycler API](https://docs.opentrons.com/python-api/modules/thermocycler/)
  — lid, block, profiles, ramp rate, and concurrent operations.
- [Concurrent Module Actions](https://docs.opentrons.com/python-api/modules/concurrent/)
  — API 2.27+ background tasks and waiting.

## Robot and App User Guides

- [Flex Instruction Manual](https://docs.opentrons.com/flex/)
  — installation, hardware, touchscreen, App, modules, calibration, and
  operations.
- [Flex Python API overview](https://docs.opentrons.com/flex/protocols/python-api/)
  — capabilities available to Flex protocol authors.
- [Flex supported modules](https://docs.opentrons.com/flex/modules/)
  — current physical module compatibility.
- [OT-2 Instruction Manual](https://docs.opentrons.com/ot-2/)
  — installation, hardware, App, calibration, and operations.
- [OT-2 supported modules](https://docs.opentrons.com/ot-2/modules/)
  — current physical module compatibility.
- [Opentrons App download](https://opentrons.com/app/)
  — current Flex and OT-2 App installers.

## Releases and Source

- [PyPI package](https://pypi.org/project/opentrons/)
  — stable package version, release date, Python requirement, and package
  license.
- [Robot software release notes](https://github.com/Opentrons/opentrons/blob/edge/api/release-notes.md)
  — user-facing robot software and API changes.
- [GitHub releases](https://github.com/Opentrons/opentrons/releases)
  — tagged robot software artifacts.
- [Opentrons monorepo](https://github.com/Opentrons/opentrons)
  — source for the Protocol API, robot stack, App, shared data, and docs.

## Separate HTTP API Surface

The Python Protocol API is the preferred surface for protocol files. Direct
robot-server integrations are separate:

- [HTTP API specification](https://docs.opentrons.com/http/api_reference.html)
  — published OpenAPI description.
- A target robot also serves its OpenAPI document on port 31950.

Use the specification served by the target robot when integrating directly.
Do not translate Protocol API methods into guessed HTTP endpoints.

## Source Precedence

When sources differ:

1. Target robot's maximum API and analysis result in the appropriate App.
2. Current official versioning and API reference.
3. Current robot/module instruction manual.
4. Stable PyPI metadata and tagged GitHub release.
5. Example protocols.

Examples can lag the versioning page or show a higher generic API level than a
particular robot currently supports. Apply the target robot's maximum.
