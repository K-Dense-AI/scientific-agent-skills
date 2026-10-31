# Release and transport review

Reviewed **2026-10-01**, targeting **PyLabRobot 0.2.2** on Python 3.13.
This review used imports, class inspection, resource serialization, chatterbox
frontends and mocked failure paths. It made no device connections or commands.

## Release evidence and documentation drift

- [PyPI 0.2.2 metadata](https://pypi.org/pypi/pylabrobot/0.2.2/json) reports
  release 2026-07-30, Python >=3.9 and optional hardware extras.
- The official [release artifacts](https://pypi.org/project/PyLabRobot/0.2.2/#files)
  were inspected. Source archive SHA-256:
  `ec5c6308dae5280a36dd08dc50b709230efea11f23135ea625d238386083efde`.
  Wheel SHA-256:
  `18f61a943301bc448500c9f4babf28ecbd8a520fcdc2d01dfa8c8c5c71be66e2`.
- [Official tags](https://api.github.com/repos/PyLabRobot/pylabrobot/tags?per_page=100)
  listed `v0.2.1`, `v0.2.0`, and `paper-tag`; there was no `v0.2.2` tag.
- [Changelog](https://github.com/PyLabRobot/pylabrobot/blob/main/CHANGELOG.md)
  has no 0.2.2 release heading. MicroSpin and `Plate.stacking_z_height` appear
  under `Unreleased` but are present in the wheel. Do not infer absence from
  that heading or invent a release-tag URL.
- The hosted [installation](https://docs.pylabrobot.org/stable/user_guide/_getting-started/installation.html)
  and [liquid-handler API](https://docs.pylabrobot.org/stable/api/pylabrobot.liquid_handling.html)
  identify 0.2.1, while [machines](https://docs.pylabrobot.org/stable/user_guide/machines.html)
  and [trackers](https://docs.pylabrobot.org/stable/user_guide/machine-agnostic-features/using-trackers.html)
  serve development content. The released source resolves this conflict.

## Native contracts verified

- `LiquidHandler` with literal `LiquidHandlerChatterboxBackend`: async lifecycle,
  resource/carrier assignment, fresh tip pickup, aspiration, dispense, return,
  and exact 100 -> 90 uL source / 0 -> 10 uL destination ledger.
- A synthetic backend exception rolls back pending volumes. Underfilled source
  is rejected before the mocked aspiration backend runs. These tests do not
  reproduce partial physical success or vendor/channelized errors.
- `cor_96_wellplate_360uL_Fb` replaces deprecated `Cor_96_wellplate_360ul_Fb`.
  Released Hamilton decks use `rails=`, not development `track=`.
- A trusted resource-only tree and separate volume state round-trip through
  JSON at `allow_marshal=False`; plate nesting metadata round-trips and three
  20 mm plates with 15 mm nesting pitch produce 50 mm stack height.
- Reader chatterbox: selected-well masks, full-plate behavior for `wells=[]`,
  legacy matrix versus explicit `use_new_return_type=True` records.
- Pump volume conversion delegates to duration using an explicit calibration;
  no pump backend was constructed. `pump_volume()` exists in 0.2.2.
- Scale `read_weight()` is current; `get_weight()` is deprecated. Use
  `pylabrobot.scales.MettlerToledoWXS205SDUBackend`; the old module is absent
  and the old unsuffixed class raises on construction. Synthetic scale
  readings use `ScaleChatterboxBackend`, never a hardware backend.

## Transport contracts inspected, without transport execution

The skill's CLIs have no endpoint or transport operations. API inspection
imports a fixed set of symbols without backend construction. The following
upstream behavior matters when reviewing a future, separately authorized run.

### OT-2 HTTP

Released `liquid_handling/backends/opentrons_backend.py` uses optional
`opentrons-http-api-client==0.2.1`. Its source sends plain HTTP to the configured
host on port 31950 with `Opentrons-Version: 3`; it has no built-in bearer-token
configuration or explicit request timeout. `setup()` creates a run via
`POST /runs` (extracting `data.id`), loads mounted pipettes, reads `GET /health`
(`api_version`), and homes unless `skip_home=True`. Commands are submitted as
`data.commandType`, `data.params`, and `data.intent` under
`POST /runs/{id}/commands`; responses provide command IDs and status. A submitted
command is not proof of completed physical execution.

The released `stop()` tries `POST /runs/{id}/cancel`, then
`POST /runs/{id}/actions/cancel`, then `DELETE /runs/{id}`, swallowing failures.
The [official HTTP specification](https://docs.opentrons.com/http/api_reference.html)
has `POST /runs/{runId}/actions` and `DELETE /runs/{runId}`, not those two cancel
paths. The [official action model](https://github.com/Opentrons/opentrons/blob/edge/robot-server/robot_server/runs/action_models.py)
defines `data.actionType="stop"`; the [router](https://github.com/Opentrons/opentrons/blob/edge/robot-server/robot_server/runs/router/actions_router.py)
returns an action record (201) and checks robot-control authorization in current
source. No compatibility with a particular robot software/auth configuration
is established. Do not use the released cleanup return as evidence of physical
halt or silently patch/retry live commands. Resolve the integration under the
site's commissioning process. Listing/pagination APIs are not used by the skill.

### MicroSpin TCP

Released `centrifuge/highres/microspin_backend.py` specifies persistent TCP
port 1000 and ASCII commands terminated by CRLF. Responses correlate an ACK
and command ID with `OK!`, `ERROR!`, or `ABORTED!` terminal records.
`status` may block until the spindle stops. `setup()` connects; `stop()` only
closes the socket. Neither a closed socket nor a software timeout proves halt.
The driver references HighRes manual 1058675; that manufacturer's manual and
physical firmware were not independently obtained/validated. The in-package
mock server was not started. No network scanning or device probe occurred.

### Other devices and Visualizer

STAR/Vantage and EVO use model-specific firmware over USB; Masterflex takes a
serial `com_port`; VSpin/Access2 use device-specific FTDI interfaces. Imports
and signatures were checked without optional USB/serial/FTDI/HID discovery.
The generic frontends do not establish baud rates, USB identity, firmware,
liquid classes, interlocks, or supported physical options.

Visualizer source keeps loopback host, WS 2121, HTTP 1337 defaults and async
`setup()`/`stop()`. It serves resource/state events, not physical simulation.
Its browser and socket lifecycle were source-inspected, not executed. No
analytical measurement, calibration, mechanical motion or temperature control
was validated in this review.
