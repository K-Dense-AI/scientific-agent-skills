# Validation and Operations

Use layered validation. A protocol is not ready for live samples merely because
it compiles or simulates.

## Reproducible Local Environment

The skill pins separate compatibility environments:

- `requirements-flex.txt`: `opentrons==9.1.1`, Flex API 2.29.
- `requirements-ot2.txt`: `opentrons==9.0.0`, OT-2 API 2.28.

One-shot simulation:

```bash
# Flex
uv run --with "opentrons==9.1.1" opentrons_simulate protocol.py

# OT-2
uv run --with "opentrons==9.0.0" opentrons_simulate protocol.py
```

Dedicated Flex environment:

```bash
uv venv --python 3.10
uv pip install --python .venv/bin/python -r skills/opentrons-integration/requirements-flex.txt
.venv/bin/opentrons_simulate protocol.py
```

Use `requirements-ot2.txt` instead for the OT-2 compatibility environment.
`opentrons==9.1.1` intentionally rejects OT-2 protocols after the release-line
split; the current OT-2 App remains the authoritative OT-2 analyzer.

Check the package and maximum API implemented by the local library:

```bash
uv run --with "opentrons==9.1.1" python -c \
  "import opentrons; from opentrons import protocol_api; print(opentrons.__version__, protocol_api.MAX_SUPPORTED_VERSION)"
```

The local package does not update robot software. A protocol can simulate
locally and still request an API level unavailable on the target robot.

## Validation Ladder

### 1. Syntax and import

```bash
python -m py_compile protocol.py
```

This catches Python syntax errors only. It does not instantiate Protocol API
objects or validate deck geometry.

### 2. Local simulation

```bash
# Flex
uv run --with "opentrons==9.1.1" opentrons_simulate protocol.py

# OT-2
uv run --with "opentrons==9.0.0" opentrons_simulate protocol.py
```

Review:

- Robot type and API level.
- Every loaded labware, adapter, fixture, pipette, and module.
- Expanded command order.
- Tip pickup and disposal.
- Source and destination wells.
- Mix, air-gap, blowout, delay, and pause placement.
- Module state transitions.
- Gripper and labware moves.
- Unexpected warnings.

Useful simulator options:

```bash
# More diagnostic logs
opentrons_simulate -l info protocol.py

# Custom labware directory; repeat -L as needed
opentrons_simulate -L custom_labware protocol.py

# Add only named data files; repeat -d as needed
opentrons_simulate -d plate_map.csv protocol.py

# Experimental estimate
opentrons_simulate -e protocol.py
```

Prefer `-d` over `-D` for data because `-D` loads every file in a directory
into memory. Never point `-D` at a directory containing credentials, unrelated
data, or large files.

The current directory is searched for custom labware implicitly, but explicit
`-L` paths make validation more reproducible.

### 3. Resource audit

Independently calculate:

- Individual tips or multi-channel tip sets.
- Source volume, disposal volume, dead volume, mixing loss, and reserve.
- Maximum intermediate volume of every destination.
- Pipette capacity including air gaps.
- Module, adapter, staging, trash, and waste positions.
- Lids and Gripper paths.
- Runtime under worst-case parameters.

Simulation does not prove that the liquid budget is sufficient.

### 4. Opentrons App analysis

Use the App appropriate for the target robot. At API 2.29 and newer, Flex and
OT-2 use separate software and App release lines.

1. Connect to the intended robot.
2. Import the Python protocol and required custom labware or data.
3. Require successful protocol analysis.
4. Review analysis warnings and errors; do not bypass them.
5. Check the starting deck and module setup.
6. Set runtime parameters and inspect the resulting protocol.
7. Review protocol visualization and run preview.
8. Verify labware offsets or Labware Position Check results.
9. Confirm installed pipettes, mounts, modules, and firmware.

App analysis is closer to the target robot than local simulation, but it still
does not verify actual liquids, tips, caps, seals, or calibration.

### 5. Operator review

Use a second-person check for:

- Correct protocol revision.
- Correct robot.
- Deck map against physical deck.
- Labware identity and orientation.
- Tip type and sufficient count.
- Source identity and volume.
- Destination capacity.
- Runtime parameter values.
- Required manual steps.
- Waste capacity.
- Safety controls and emergency stop access.

### 6. Dry run

For a new or materially changed method:

- Use water or another validated nonhazardous surrogate.
- Remove valuable samples and hazardous reagents.
- Start with low-risk geometry and reduced speed where feasible.
- Check pickup, aspiration depth, dispense depth, mixing, and disposal.
- Observe every Gripper, lid, Stacker, and partial-nozzle move.
- Verify module transitions and operator prompts.
- Measure delivered volumes when accuracy matters.

A tip-only dry run is appropriate for new partial-nozzle layouts.

### 7. Controlled release

Keep:

- Protocol file hash or version.
- `opentrons` package version used in local simulation.
- Robot software and App versions.
- Custom labware definitions and versions.
- Runtime parameter record.
- Dry-run and qualification results.
- Operator and reviewer sign-off as required by the lab's quality system.

## What Simulation Does Not Validate

- Pipette calibration or mechanical wear.
- Labware manufacturing variation or placement error.
- Physical caps, seals, lids, warped plates, or obstructions.
- Actual liquid volume or identity.
- Viscosity, volatility, surface tension, foaming, or aerosols.
- Bead settling, pellet location, or cell sedimentation.
- Reliable liquid-level sensing with the chosen liquid.
- Gripper friction and every collision scenario.
- Module thermal equilibration inside the sample.
- Plate-reader optical performance; simulated readings are zeros.
- Operator compliance with a pause message.

## Runtime Parameter Testing

The default value should always produce a meaningful local simulation.

For each parameter:

- Test minimum, maximum, default, and every fixed choice.
- Test branch combinations that change tip count, deck use, timing, or modules.
- Reject invalid CSV rows before generating any commands.
- Confirm parameter labels and descriptions are understandable in the App.
- Recompute source volume and tips for the largest allowed run.

The command-line simulator primarily analyzes defaults. Use App analysis or
dedicated test variants to exercise alternate runtime values.

## Custom Labware

Before live use:

1. Validate the JSON schema with current Opentrons tooling.
2. Confirm dimensions against manufacturer drawings and physical measurement.
3. Check well depth, diameter or dimensions, and total capacity.
4. Check corner offset and well ordering.
5. Add stacking offsets for custom labware used on adapters.
6. Import the exact definition into the App.
7. Perform Labware Position Check.
8. Dry-run the highest-risk wells and edge positions.

Do not silently replace a missing custom definition with standard labware.

## Failure Triage

### Unsupported API version

Symptoms:

- Protocol imports locally but fails App analysis.
- Error states that requested API is above the robot maximum.

Actions:

1. Check the maximum in robot settings.
2. Update robot software and the appropriate App if approved.
3. Otherwise lower the API level and remove or replace unsupported features.

Do not edit the version string alone; audit every method and behavior gate.

### Invalid pipette or labware load name

Actions:

- Copy the current pipette name from the official loading guide.
- Copy labware names from the Labware Library.
- Confirm custom namespace and definition version.
- Replace obsolete Flex names such as `p300_single_flex` with current
  `flex_*` names only after matching volume and channel count.

### Deck conflict

Check:

- Thermocycler footprint.
- Module caddies.
- Heater-Shaker adjacent-slot restrictions.
- Flex staging area and corresponding column-3 slot.
- Plate-reader lid travel.
- Stacker shuttle row.
- Waste chute D3.
- Partial-nozzle reach and tall adjacent labware.

### Out of tips

Count:

- Every `new_tip="always"` pair.
- Tip sets for multi-channel pipettes.
- Branch-specific and retry operations.
- Tips used for liquid detection.
- Tips reserved for controls.

Add racks or redesign the validated tip policy. Do not reset tracking unless the
operator has physically replaced or correctly refilled racks.

### Insufficient source volume

Include distribution disposal volume, dead volume, pre-wet, mixing, carryover,
and reserve. Liquid setup visualization does not prevent a physical source from
running dry.

### Module not ready

Check:

- Correct generation and load name.
- USB connection and power.
- Module firmware.
- Lid or latch state.
- Returned concurrent task was awaited.
- Temperature or speed is physically reachable.

### Plate-reader calculation fails only in simulation

The reader returns zeros during simulation. Skip or substitute analysis-only
calculations under `protocol.is_simulating()` when a zero denominator is
possible. Keep the physical-run path unchanged.

### Physical pickup or positioning issue

Stop the run if collision or pickup failure is possible. Check calibration,
labware definition, offsets, tip compatibility, adapter use, nozzle layout, and
deck placement. Do not compensate with arbitrary offsets until the underlying
geometry is understood.

## Release Checklist

- [ ] Python compilation passes.
- [ ] Pinned local simulation passes.
- [ ] Run log reviewed.
- [ ] Resource audit completed.
- [ ] App analysis passes on the target robot.
- [ ] Deck map and parameters reviewed.
- [ ] Custom labware and offsets verified.
- [ ] Nonhazardous dry run completed for new geometry.
- [ ] Module and Gripper actions observed.
- [ ] Contamination and waste plan approved.
- [ ] Protocol revision and environment recorded.
