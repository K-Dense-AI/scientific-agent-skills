# Visualization and software-only simulation

Verified against **PyLabRobot 0.2.2** on **2026-10-01**.

## Three different layers

Do not conflate:

1. **Manifest/ledger planning** — the bundled dependency-free CLIs validate
   bounded JSON/CSV and produce non-executable JSON.
2. **Chatterbox backend** — PyLabRobot validates frontend/tracker operations and
   prints them instead of sending hardware commands.
3. **Visualizer** — a browser renderer that receives resource and tracker events
   over localhost HTTP/WebSocket services.

None is a robot physics simulator, collision-motion planner, liquid-dynamics
model, or physical sensor.

## Chatterbox backend

The verified stable import is:

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
    # Assign resources, seed tracker state, and execute planned calls.
    ...
finally:
    await lh.stop()
```

`setup()` above is offline only because the backend is constructed literally as
`LiquidHandlerChatterboxBackend`. Never replace it from a config string,
environment variable, plugin, or auto-detected device.

The stable docs sometimes use the generic phrase `ChatterboxBackend`, but the
verified liquid-handler class/import is `LiquidHandlerChatterboxBackend`.
`ChatterBoxBackend` (capital `B`) is a distinct exported legacy-named class.

## Visualizer API

Source-verified illustrative usage; server startup/browser rendering was not
run during this refresh:

```python
from pylabrobot.visualizer import Visualizer

vis = Visualizer(
    resource=lh,
    host="127.0.0.1",
    ws_port=2121,
    fs_port=1337,
    open_browser=False,
)
await vis.setup()
try:
    # Exercise the software-only liquid handler.
    ...
finally:
    await vis.stop()
```

Corrections to stale examples:

- `Visualizer` requires a root `resource`; `Visualizer()` alone is incomplete.
- Use `setup()` / `stop()`, not `start()`.
- Do not assign `lh.visualizer = vis`; pass `lh` as the Visualizer resource.
- Stable defaults are WebSocket port 2121 and file-server port 1337, not 1234.

The Visualizer starts two local servers and can open a browser. It therefore
uses localhost networking even when the liquid handler is software-only.
Do not use it where the requirement is "no network." Bind only to loopback,
keep `open_browser=False` for controlled tests, avoid shared/untrusted hosts,
and stop both services reliably.

The bundled CLIs and tests do **not** start the Visualizer or any socket.

## What the Visualizer does

It:

- renders a `Resource` tree;
- receives assignment/unassignment callbacks;
- renders tracker state such as planned tips and volumes;
- updates as frontend operations change state.

It does not:

- calculate physical trajectories or clearances;
- detect an incorrect/missing physical resource, tip, or liquid;
- model meniscus, viscosity, foam, pressure, carryover, or pipetting error;
- emulate firmware timing, sensors, interlocks, doors, arms, or failures;
- validate liquid classes or calibrations;
- authorize a live run.

Upstream's contributor guide explicitly describes the browser as passive: it
renders messages and does not perform simulation logic.

## Tracker setup

```python
from pylabrobot.resources import set_tip_tracking, set_volume_tracking

set_tip_tracking(True)
set_volume_tracking(True)
source.get_well("A1").tracker.set_volume(100.0)
```

Set initial state from a synthetic fixture for tests. For later live work,
reconcile planned state with the physical deck; do not infer physical presence
from what the browser draws.

## Deterministic no-network plan

Generate a JSON plan without importing PyLabRobot:

```bash
python3 skills/pylabrobot/scripts/generate_simulation_plan.py \
  --manifest tests/pylabrobot/fixtures/protocol_manifest.json \
  --transfers tests/pylabrobot/fixtures/transfers.csv
```

The output:

- fixes the target at `PyLabRobot==0.2.2`;
- names only `LiquidHandlerChatterboxBackend`;
- marks live backends as forbidden;
- records zero connection attempts and no serial/USB/network access;
- expands each transfer into tip pickup, aspirate, dispense, and tip disposal;
- includes final planned volumes, tip counts, limitations, and a mandatory human
  review checklist.

It intentionally produces data, not executable Python.

## Test strategy

Use layers of evidence:

1. Strict manifest schema validation.
2. Static deck bounds and axis-aligned overlap screen.
3. Transfer/dead-volume/destination/tip/channel/rate/height ledger.
4. Non-executable simulation plan review.
5. Pinned 0.2.2 import/signature inspection with zero backend instances.
6. Chatterbox-only protocol smoke with synthetic resources.
7. Optional Visualizer review on an approved loopback host.
8. Independent physical commissioning only after explicit operator approval.

Test failures should be deterministic. Do not catch broad errors and continue;
do not disable trackers; do not mutate expected state to make a failed
assertion pass.

Run the skill's tests without bytecode:

```bash
PYTHONDONTWRITEBYTECODE=1 python tests/run_all.py --isolated pylabrobot
```

## Stable versus development

Use the released wheel/source for pinned 0.2.2 behavior. Hosted `/stable/` now
mixes older API pages with development pages; `/dev/` and repository `main` may
change event payloads, serialization or the UI. See [review](review.md).
Do not copy development examples without checking the installed release.

## Sources

Checked **2026-10-01**:

- [Hosted Visualizer guide](https://docs.pylabrobot.org/stable/user_guide/machine-agnostic-features/using-the-visualizer.html)
  — development guide; released constructor and ports checked in source.
- [Visualizer contributor architecture](https://docs.pylabrobot.org/stable/contributor_guide/visualizer.html)
  — passive rendering, file server, WebSocket server, and callbacks.
- [Hosted tracker guide](https://docs.pylabrobot.org/stable/user_guide/machine-agnostic-features/using-trackers.html)
  — planned tip/volume state.
- [Hosted liquid-handling API](https://docs.pylabrobot.org/stable/api/pylabrobot.liquid_handling.html)
  — `LiquidHandlerChatterboxBackend`.
- [released 0.2.2 Visualizer source](https://pypi.org/project/PyLabRobot/0.2.2/#files)
  and [chatterbox source](https://pypi.org/project/PyLabRobot/0.2.2/#files)
  — exact constructor/method verification; released 2026-07-30.
