# Protocol Authoring Guide

Use this guide to turn a wet-lab method into a reviewable Opentrons Python
protocol. It targets Protocol API v2 and assumes the protocol will be imported
into the Opentrons App.

## 1. Convert the Method into Explicit Inputs

Create a protocol specification before writing code.

### Hardware

- Robot model and installed software.
- Pipette load name, mount, channels, and calibrated volume range.
- Required modules and generations.
- Flex Gripper, Stacker, waste chute, staging slot, and trash-bin requirements.
- Whether any operator action requires opening the door or moving labware.

### Labware and consumables

- Exact API load name, namespace, and definition version.
- Adapter or module beneath each item.
- Tip capacity, filter status, and number of racks.
- Lids, seals, caps, and manual removal steps.
- Custom labware JSON and how its dimensions were verified.

### Liquids and assay constraints

- Initial source volume and dead volume.
- Per-transfer volume, number of destinations, and destination capacity.
- Viscosity, volatility, foaming risk, cells or beads that settle, and
  temperature sensitivity.
- Required pre-wet, mix, air-gap, delay, touch-tip, blowout, or push-out
  behavior.
- Contamination boundaries and whether tip reuse is permitted.

### Operations

- Runtime-configurable values and safe defaults.
- Required user pauses and setup messages.
- Module temperatures, speeds, cycle profiles, and hold behavior.
- Data input and output files.
- Dry-run and acceptance criteria.

Record every assumption that has not been confirmed by the operator.

## 2. Choose the API Level Deliberately

The API level controls both available methods and behavior. It is not merely a
documentation label.

1. Check the robot's maximum supported level in the App.
2. Identify the minimum level for each required feature.
3. Use the highest of those minimums.
4. Raise the level further only for a specific fix or behavior that the method
   needs.

At the 2026-07-23 baseline:

- Flex maximum: 2.29.
- OT-2 maximum: 2.28.
- A shared Flex/OT-2 code generator must not assume API 2.29.

Do not declare an unsupported API level just because a newer local Python
package can simulate it.

## 3. Keep Top-Level Code Declarative

A protocol file normally contains imports, `metadata`, `requirements`, optional
parameter definitions, helper functions, and `run()`.

```python
from opentrons import protocol_api

metadata = {
    "protocolName": "Assay setup",
    "author": "Automation Team",
    "description": "Prepare an eight-sample assay plate.",
}
requirements = {"robotType": "Flex", "apiLevel": "2.29"}


def add_parameters(parameters: protocol_api.ParameterContext) -> None:
    parameters.add_int(
        variable_name="sample_count",
        display_name="Sample count",
        default=8,
        minimum=1,
        maximum=24,
    )


def run(protocol: protocol_api.ProtocolContext) -> None:
    sample_count = protocol.params.sample_count
    protocol.comment(f"Preparing {sample_count} samples")
```

Avoid top-level network calls, package installation, local machine paths, or
other side effects. Protocol analysis evaluates the protocol in a controlled
environment, and the robot may not have workstation packages or network
access.

Do not use `apiLevel` in both `metadata` and `requirements`.

## 4. Build a Deck Manifest

Create a simple manifest before calling load methods:

| Slot | Item | Adapter/module | Notes |
| --- | --- | --- | --- |
| A3 | Flex trash bin | — | Required for dropped tips |
| C1 | 50 µL tip rack | Flex tip-rack adapter if required | Left pipette |
| C2 | Sample rack | — | Tubes 1–8 |
| D1 | Temperature Module GEN2 | Aluminum block | Master mix |
| Thermocycler | PCR plate | Thermocycler Module GEN2 | Destination |

Then check:

- Module and adapter footprints.
- Flex column-4 staging slots and column-3 conflicts.
- Thermocycler occupied slots.
- Heater-Shaker clearance and latch state.
- Gripper approach paths and labware compatibility.
- Tall labware adjacent to partial-nozzle pickup.
- Sufficient room for lids and plate-reader lid travel.

Use named variables and labels:

```python
sample_rack = protocol.load_labware(
    "opentrons_24_tuberack_nest_1.5ml_snapcap",
    "C2",
    label="Samples 1-8",
)
```

Labels appear in setup and run views and are more useful than generic names
such as `plate1`.

## 5. Use Exact Labware Definitions

The API load name identifies geometry, not merely a product category.

- Copy load names from the
  [Labware Library](https://labware.opentrons.com/).
- Check definition version when a labware has multiple revisions.
- Do not replace a missing definition with a "close enough" plate or rack.
- Bundle the exact custom labware JSON with the protocol when needed.
- Verify custom labware dimensions, well coordinates, and stacking offsets.
- Run Labware Position Check or the current App equivalent before first use.

Loading on an adapter should reflect the physical stack:

```python
adapter = protocol.load_adapter(
    "opentrons_96_well_aluminum_block",
    "D1",
)
plate = adapter.load_labware(
    "opentrons_96_wellplate_200ul_pcr_full_skirt"
)
```

For modules, call the module or module adapter's `load_labware()` method. Do not
repeat a deck slot already supplied to `load_module()`.

## 6. Represent Initial Liquids

Liquid definitions improve setup visualization but do not move or measure
liquid.

```python
master_mix = protocol.define_liquid(
    name="Master mix",
    description="2x PCR master mix",
    display_color="#E377C2",
)

reagent_rack.load_liquid(
    wells=["A1"],
    volume=500,
    liquid=master_mix,
)
```

For varying volumes:

```python
sample_rack.load_liquid_by_well(
    volumes={"A1": 30, "A2": 40, "A3": 50},
    liquid=sample,
)
```

In API 2.22+ protocols, prefer labware-level methods over deprecated
`Well.load_liquid()`.

Declared volumes support visualization and meniscus calculations. They do not
replace physical setup checks or a source-volume budget.

## 7. Define Runtime Parameters

Use runtime parameters for values an operator should set without editing code:

- Sample count.
- Transfer volume within a validated range.
- Number of cycles.
- Incubation time.
- Dry-run mode.
- A fixed choice of pipette or workflow branch.
- A CSV plate map.

Keep hardware geometry and safety-critical invariants in code unless every
allowed choice is separately validated.

```python
def add_parameters(parameters: protocol_api.ParameterContext) -> None:
    parameters.add_float(
        variable_name="transfer_volume",
        display_name="Transfer volume",
        description="Volume delivered to each destination.",
        default=25.0,
        minimum=10.0,
        maximum=40.0,
        unit="µL",
    )
    parameters.add_bool(
        variable_name="dry_run",
        display_name="Dry run",
        description="Shorten delays and use test-safe behavior.",
        default=False,
    )
```

Constraints:

- Display name: at most 30 characters.
- Description: at most 100 characters.
- Numeric parameters need a min/max range or enumerated choices.
- A CSV parameter has no default.
- The App and touchscreen currently support one CSV parameter per run.
- CSV cells are initially strings; parse and validate every row, column, well
  name, and numeric value before issuing commands.

Use defaults that simulate successfully. Do not make a hazardous setting the
default.

## 8. Structure the Protocol

Separate configuration from repetitive actions:

```python
def transfer_samples(
    pipette: protocol_api.InstrumentContext,
    sources: list[protocol_api.Well],
    destinations: list[protocol_api.Well],
    volume: float,
) -> None:
    for source, destination in zip(sources, destinations, strict=True):
        pipette.transfer(
            volume,
            source,
            destination,
            new_tip="always",
            mix_after=(3, min(volume, 20)),
        )
```

Guidelines:

- Use explicit lists for safety-critical well order.
- Use `zip(..., strict=True)` only if the robot's Python version supports it;
  the current baseline uses Python 3.10 and does.
- Validate list lengths before command generation.
- Name physical quantities with units, for example `volume_ul` and
  `temperature_c`.
- Put all robot commands under `run()` or helpers called from `run()`.
- Let Protocol API errors stop analysis or execution. Do not broadly catch
  exceptions and continue physical motion.
- Use `protocol.pause()` for required operator intervention.

`protocol.comment()` text is computed during analysis. Do not rely on it to
report a live sensor value that only exists during physical execution.

## 9. Plan Tips and Contamination

Define a policy before choosing `new_tip`:

- `"always"`: isolate samples or source-destination pairs.
- `"once"`: one tip for an entire complex command; safe only when all contacts
  share a contamination domain.
- `"never"`: caller must already hold a tip and must handle disposal.

Examples of unsafe optimization:

- Dispensing into samples and returning to a shared reagent with the same tip.
- Reusing a tip across positive and negative controls.
- Returning a wet tip to a rack for later unrelated use.
- Reusing tips after liquid presence detection when the next detection expects
  a fresh, dry tip.

Count multi-channel tips as tip sets. A full 8-channel pickup consumes eight
tips, and a full 96-channel pickup consumes an entire rack.

## 10. Budget Volumes

For each source:

```text
required source volume =
    delivered volume
  + disposal volume
  + mixing and pre-wet loss
  + geometry-dependent dead volume
  + validated reserve
```

For each destination, calculate the maximum intermediate volume, not just the
final expected volume. Include mix strokes, carryover splits, and any material
left before a subsequent transfer.

Do not use a pipette below its supported range. For example, 100 nL is below
the range of every current Opentrons pipette and requires a different
dispensing technology or a redesigned dilution scheme.

## 11. Data and Dependencies

- Prefer runtime CSV parameters for operator-supplied tabular data.
- Bundle static data when the workflow requires a fixed resource.
- Validate file schema, required columns, allowed well names, volume ranges,
  duplicates, and total volume before generating robot commands.
- Do not download data or packages during a run.
- Do not embed credentials or make a protocol depend on broad environment
  variable access.
- Pin the local `opentrons` package used for simulation, but remember that the
  robot executes its installed software stack.

## 12. Review Checklist

- Correct robot and API level.
- Current pipette load names and compatible tips.
- Exact labware definitions and adapters.
- Explicit Flex trash or waste chute.
- No deck conflicts or unreachable partial-nozzle targets.
- Source and destination volume budgets pass.
- Tip count covers every branch and retry policy.
- Contamination policy is documented.
- Runtime parameter defaults are safe and simulation-ready.
- Module state transitions are complete.
- Every operator pause has an actionable message.
- Local simulation and App analysis both succeed.
- New geometry is covered by a nonhazardous dry run.
