# Hardware backends and supported robots

Verified against **PyLabRobot 0.2.2** on **2026-10-01**. Released exports were inspected without constructing hardware backends. Hosted
`/stable/` support tables now describe development APIs; see [review](review.md).

## Architecture

PyLabRobot separates:

- a frontend such as `LiquidHandler`, which validates and records standard
  operations;
- a backend, which translates those operations for one device family;
- a resource/deck tree, which supplies geometry and state.

A common frontend does not guarantee identical channels, tools, operations,
parameters, calibration, error semantics, timing, or firmware support.
Backend-specific kwargs must be reviewed against the exact release implementation and model page.

## Verified stable liquid-handler names

```python
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import (
    EVOBackend,
    LiquidHandlerChatterboxBackend,
    OpentronsOT2Backend,
    STARBackend,
    VantageBackend,
)
```

Do not use stale names from older skill text:

- `STAR` is not the stable high-level backend name; use `STARBackend`.
- `TecanBackend` is not the 0.2.2 EVO backend; use `EVOBackend`.
- `OpentronsBackend` is stale; use `OpentronsOT2Backend`.
- `ChatterboxBackend` has incorrect naming/capitalization for the recommended
  generic liquid-handler testing backend; use
  `LiquidHandlerChatterboxBackend`.
- `ChatterBoxBackend` (capital `B`) is a separate exported legacy-named class.
  Avoid it when the stable docs specifically call for
  `LiquidHandlerChatterboxBackend`.

## Released exports and current support listings

The 0.2.2 wheel exposes STAR, Vantage, EVO and OT-2 backends listed above.
The current hosted machine table labels STAR **Full**, Vantage **Mostly**,
EVO **Basic**, OT-2 **Mostly**, Nimbus **Mostly**, and Prep **WIP**. These are
upstream development-support assessments, not validation of the 0.2.2 wheel,
firmware, attachments, or a protocol. Nimbus/Prep entries do not establish a
portable released backend import. Read the exact device source before using it.

The hosted table also distinguishes v0 and v1 drivers; these labels are not
PyLabRobot release numbers. Never infer a released capability from that table
alone or from inherited method presence.

## Offline backend

```python
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import LiquidHandlerChatterboxBackend
from pylabrobot.resources.hamilton import STARLetDeck

lh = LiquidHandler(
    backend=LiquidHandlerChatterboxBackend(num_channels=8),
    deck=STARLetDeck(),
)
await lh.setup()
try:
    # Build resources and exercise planned operations only.
    ...
finally:
    await lh.stop()
```

This backend prints operations and updates software state. It does not connect
to a robot and does not model robot physics. Keep the backend construction
literal; never choose a live class from a string, plugin, environment variable,
or untrusted config.

## Capability/version inspection without connection

```bash
python3 skills/pylabrobot/scripts/inspect_backends.py \
  --expected-version 0.2.2 --strict
```

The inspector:

- imports a fixed allowlist of stable classes only after argument parsing;
- reads installed distribution metadata;
- inspects class signatures/method presence;
- creates zero backend instances;
- never calls `setup()`;
- performs no serial, USB, HID, FTDI, Modbus, or network operation.

Method presence is not proof that a model implements the operation; some
backends deliberately raise `NotImplementedError`.

## Extras and transports

Base `PyLabRobot==0.2.2` keeps hardware dependencies optional. The release metadata lists extras including:

- `serial`
- `usb`
- `ftdi`
- `hid`
- `modbus`
- `opentrons`
- `sila`
- `microscopy`
- `pico`
- `all`

Install only the exact reviewed extra for a named device and keep the top-level
pin:

```bash
# Example form only; do not run until the device and transport are approved.
uv pip install "PyLabRobot[serial]==0.2.2"
```

`all` intentionally does not include microscopy in stable 0.2.2 because of its
separate NumPy/SDK constraints. Optional transport packages can enumerate or
communicate with devices; installation does not authorize their use.

## Live-run gate

Do not instantiate a live backend or call `setup()` until a trained operator has
explicitly confirmed:

1. Backend class, exact robot model/serial number, firmware, options, and
   transport.
2. Vendor/organization permission, warranty implications, maintenance state,
   access controls, and exclusive control of the device.
3. Deck definition, carriers/adapters, resources, coordinates, orientation,
   clearances, and collision/motion review.
4. Calibration, teaching, tip/head compatibility, channel mapping, units,
   heights, rates, liquid classes, and all backend kwargs.
5. Source/dead/destination volumes, physical liquid identity, tip state,
   contamination policy, waste, lids/seals, tubing/cables, and operator steps.
6. Guards/doors, emergency stop readiness, PPE, containment, dry-run plan,
   abort path, and recovery/resume rules.

Never make a live run conditional only on `USE_HARDWARE=true`, a CLI flag, or an
IP/serial value. Confirmation must be tied to the reviewed protocol and current
physical setup.

## Backend-specific cautions

### Hamilton STAR/Vantage

These are direct firmware drivers. Upstream states that PyLabRobot is not
endorsed or supported by robot manufacturers and that firmware-driver use may
affect warranty. Review USB permissions, device selection, cover/arm/head
configuration, firmware ranges, liquid-level detection, channels, CO-RE tips,
and all device-specific errors.

### Tecan EVO

The current hosted EVO support label remains **Basic**. Use `EVOBackend`; verify which LiHa/RoMa
commands, arms, tips, carriers, and firmware paths are implemented. Never infer
Hamilton behavior or liquid classes.

### Opentrons OT-2

`OpentronsOT2Backend(host, port=31950)` uses the optional pinned
`opentrons-http-api-client==0.2.1`. Its `setup(skip_home=False)` creates an HTTP
run and homes by default; `skip_home=True` still creates a run and queries the
robot. Neither is an offline connectivity check. Current 0.2.2 `stop()` tries
cancellation paths not in the current official HTTP specification and swallows
failures. **Do not treat successful cleanup as confirmation that a robot stopped.**
The [transport review](review.md) records exact paths and the supported API
contract. No robot HTTP request was made during this review.

## Stable versus development

The tested pin is 0.2.2. No `v0.2.2` GitHub tag was listed at review time,
and the changelog did not have a 0.2.2 section. MicroSpin and plate stacking
metadata are in the released wheel despite remaining under `Unreleased` in
the changelog. Prefer the PyPI source artifact plus executable checks.

When considering a later release:

1. Confirm it exists on PyPI and is not a prerelease.
2. Compare `Requires-Python`, extras, tag, changelog, and source.
3. Run import/signature and software-only tests in an isolated environment.
4. Revalidate each target model/firmware and repeat commissioning.

## Sources

Reviewed **2026-10-01**: [PyPI release files and extras](https://pypi.org/project/PyLabRobot/0.2.2/#files),
[current supported machines](https://docs.pylabrobot.org/stable/user_guide/machines.html),
[official Opentrons HTTP specification](https://docs.opentrons.com/http/api_reference.html),
and the [release/transport evidence ledger](review.md). Support listings and
physical firmware compatibility were not tested on instruments.
