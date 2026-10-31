# Analytical equipment

Verified against **PyLabRobot 0.2.2** on **2026-10-01**. This reference describes
APIs without connecting to or commanding instruments.

## Plate-reader frontend

Stable imports include:

```python
from pylabrobot.plate_reading import (
    CLARIOstarBackend,
    Cytation5Backend,
    PlateReader,
    PlateReaderChatterboxBackend,
)
```

`PlateReader` is a resource and requires dimensions plus a backend:

```text
PlateReader(name, size_x, size_y, size_z, backend, rotation=None,
            category="plate_reader", model=None,
            child_location=Coordinate(...), preferred_pickup_location=None)
```

Do not copy the stale constructor
`PlateReader(name="CLARIOstar", backend=CLARIOstarBackend())`; the stable
frontend requires `size_x`, `size_y`, and `size_z`.

Verified frontend methods include:

```text
open(**backend_kwargs)
close(**backend_kwargs)
read_absorbance(wavelength, wells=None, use_new_return_type=False,
                **backend_kwargs)
read_fluorescence(excitation_wavelength, emission_wavelength, focal_height,
                  wells=None, use_new_return_type=False, **backend_kwargs)
read_luminescence(focal_height, wells=None, use_new_return_type=False,
                  **backend_kwargs)
```

In 0.2.2 `use_new_return_type=False` returns the first measurement's nested
`data` matrix, despite the annotated `List[Dict]` return type. Set
`use_new_return_type=True` to retain measurement dictionaries, timestamps,
wavelengths and temperature. Chatterbox returns synthetic zero measurements,
`None` for unselected wells and a `NaN` temperature; strict JSON exporters must
represent missing temperature explicitly. An empty `wells=[]` means all wells
because the frontend uses `wells or plate.get_all_items()`.

Record exact arguments, plate/well mapping, settings, raw response, and package
version. Wavelengths are nm and focal height is mm. The legacy default discards
additional measurement records; do not use it for kinetics or multi-read data.

`PlateReader` does not expose a universal `set_temperature` method in the
verified 0.2.2 frontend. Temperature, shaking, injectors, kinetics, pathlength,
read mode, and optics are backend/model-specific; do not infer them from another
reader.

## Offline interface checks

`PlateReaderChatterboxBackend` is available for software-only frontend testing.
It can exercise method calls and resource state without an instrument, but it
does not simulate optics, plate seating, thermal behavior, gain, focus,
measurement noise, or assay chemistry.

For import and method-presence checks without backend construction:

```bash
python3 skills/pylabrobot/scripts/inspect_backends.py \
  --expected-version 0.2.2 --strict
```

The inspector does not call `setup()` and makes no transport connection.

## Released plate-reader inventory

The 0.2.2 module exports `CLARIOstarBackend`, `Cytation5Backend`,
`SynergyH1Backend`, Byonoy and SpectraMax drivers, plus
`ExperimentalTecanInfinite200ProBackend` and `ExperimentalSparkBackend`.
The `Experimental` names remain significant. Verify the exact import and
required serial/FTDI/USB/SiLA/microscopy extra without constructing a device.

The current hosted machine table describes development drivers, including
Cytation 1 microscopy and Cytation 5 multi-mode reading. Its model labels do
not establish matching modalities or firmware compatibility for every 0.2.2
backend. Avoid copying the old blanket Cytation 1 absorbance/fluorescence/
luminescence claim; check the exact model, optics, plate and implementation.

## Plate-reader live-run checklist

Before a separately authorized connection or read:

1. Confirm instrument model, serial/device ID, firmware, approved transport,
   exclusive control, and current calibration/QC.
2. Confirm plate manufacturer/catalog, format, material, bottom, lid/seal,
   orientation, barcode, and correct seating.
3. Confirm read mode and units: wavelength(s), focal height, gain, flashes,
   integration, shaking, temperature, kinetics, injectors, well selection, and
   read direction as applicable.
4. Check tray/door state and robot/manual transfer path; prevent closing on an
   obstruction or moving a plate while a device is active.
5. Include blanks, standards, controls, expected ranges, saturation rules, and
   acceptance criteria.
6. Save raw data and complete settings before derived analysis.

Opening/closing a tray is physical motion. Never call it merely to test
connectivity.

## Scales

Stable frontend:

```python
from pylabrobot.scales import Scale
```

Verified methods are:

```text
read_weight(**backend_kwargs) -> float
tare(**backend_kwargs)
zero(**backend_kwargs)
```

`get_weight()` is a deprecated alias. `read_weight()` reports grams; stability
and timeout semantics depend on the selected backend. The scale constructor
requires a name, dimensions, and backend.

The released package provides the model-specific backend:

```python
from pylabrobot.scales import MettlerToledoWXS205SDUBackend
```

The old `pylabrobot.scales.mettler_toledo` module is absent in 0.2.2.
`MettlerToledoWXS205SDU` is a deprecated class that raises on construction; use
the `Backend`-suffixed class. Do not instantiate it or call `setup()` during planning. The current inventory distinguishes models and suffixes; its Full entry is
WXS205SDU/15, not a claim about every WXS205 variant.

Before live weighing, verify:

- model, port, units, resolution, range, calibration, leveling, warm-up, and
  environmental limits;
- tare container, stability/status flags, vibration, drafts, static, and
  evaporation;
- whether returned values are stable/net/gross and how errors are represented;
- physical placement/removal route and collision clearance.

Mass is not automatically volume. Converting grams to microlitres requires a
validated density at the relevant temperature and uncertainty propagation. Do
not assume water density equals exactly `1 g/mL`.

## Coordinating liquid handlers and analytical devices

Treat each device as a separate state machine:

- never overlap motion unless the workcell has an approved interlock and
  scheduler;
- transfer ownership of a plate explicitly between deck, arm, reader, scale,
  and operator;
- verify doors/trays/buckets are in the required state;
- use unique plate IDs and record handoff timestamps;
- stop safely on partial failure; do not blindly retry a measurement or move;
- distinguish software resource assignment from physical plate location.

An async Python call does not create a physical safety interlock.

## Data integrity

For every measurement, retain:

- protocol and manifest revisions;
- PyLabRobot/backend version and instrument identity/firmware;
- plate/barcode and well map;
- complete acquisition settings and units;
- calibration/QC status, blanks/controls, timestamps, and error/status fields;
- unmodified raw output plus checksums;
- transformation code/version and rejected/out-of-range values.

Validate dimensions and well labels before joining measurement data to sample
metadata.

## Sources

Reviewed **2026-10-01**: [0.2.2 released source files](https://pypi.org/project/PyLabRobot/0.2.2/#files)
(`plate_reading/plate_reader.py`, `plate_reading/chatterbox.py`, `scales/scale.py`),
[current machine inventory](https://docs.pylabrobot.org/stable/user_guide/machines.html),
and [release review](review.md). Native chatterbox tests cover selected-well
masking and both return contracts; no reader, microscope or scale was connected.
