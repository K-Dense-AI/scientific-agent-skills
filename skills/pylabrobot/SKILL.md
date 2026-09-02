---
name: pylabrobot
description: Develop and review PyLabRobot lab-automation resources, liquid-handling plans, offline simulations, and supported-device integrations. Use for PyLabRobot protocols or API questions; keep physical execution behind an explicit operator safety gate.
license: MIT
compatibility: Verified against PyLabRobot 0.2.1 on Python 3.9+. Bundled planning CLIs require only Python 3.11+ and make no serial, USB, or network connections. Physical devices need model-specific extras, configuration, calibration, and trained operator approval.
allowed-tools: Read Write Edit Bash
metadata:
  version: "1.3"
  skill-author: "K-Dense Inc."
  pylabrobot-version: "0.2.1"
  researched: "2026-07-23"
---

# PyLabRobot

Use PyLabRobot's hardware-agnostic frontends, resource tree, trackers, and
device-specific backends to develop laboratory automation. Default to local
manifest validation, bookkeeping, and the software-only chatterbox backend.

## Verified snapshot

- PyPI stable: **`PyLabRobot==0.2.1`**, released **2026-03-23**.
- Upstream requirement: **Python >=3.9**. This skill uses Python 3.11 for its
  reproducible smoke tests.
- `/stable/` documentation identifies itself as 0.2.1. `/dev/` and repository
  `main` describe unreleased work and must not be assumed available in 0.2.1.
- Stable liquid-handler backends include `STARBackend`, `VantageBackend`,
  `EVOBackend`, `OpentronsOT2Backend`, and the offline
  `LiquidHandlerChatterboxBackend`.
- PyLabRobot's GitHub Releases page has no 0.2.x software release entry; use
  the PyPI history, `v0.2.1` tag, and changelog as release evidence.

## Non-negotiable hardware boundary

Never connect to, initialize, home, move, heat, shake, spin, pump, open/close,
or otherwise command physical equipment automatically. Do not turn a simulation
plan into a live backend merely by changing an environment variable, config
value, or import.

Before any separately authorized live run, require a trained human to:

1. Explicitly confirm the exact backend, device identity, firmware, transport,
   deck, and protocol revision.
2. Reconcile the physical deck against the resource tree, including carriers,
   adapters, lids, plates, tip racks, waste, labware orientation, barcodes, and
   every occupied coordinate.
3. Verify calibration, teaching, motion envelopes, collision risks, gripper or
   channel clearances, and all aspiration/dispense coordinates.
4. Review source identity and actual fill volume, dead volume, destination
   capacity, tip type/capacity/filter compatibility, channel mapping, units,
   heights, rates, liquid class, blowout/mixing, and contamination boundaries.
5. Confirm guards, doors, waste capacity, containment, emergency stop readiness,
   PPE, biosafety/chemical controls, and a safe abort/recovery procedure.
6. Approve a slow dry run or nonhazardous commissioning run when anything is
   new or changed.

Tracker state is **bookkeeping**, not sensing. It cannot prove that liquid or a
tip is physically present. The Visualizer renders resource/tracker events; it
does not model physics. Chatterbox prints planned operations; it does not prove
calibration, reachability, collision freedom, liquid behavior, or device state.

## Required intake

Do not guess any of these:

- Exact device model, installed options, firmware, computer/OS, and transport.
- Stable PyLabRobot version and required extras.
- Deck/deck origin, carriers, adapters, resource definitions, dimensions,
  coordinates, orientations, and motion clearances.
- Plate/tube/reservoir capacities and dead volumes; initial physical volumes.
- Tip model, filter, fitting, capacity, rack state, channel count, and channel
  mapping.
- Transfer units (`uL`, `mm`, `uL/s`, `s`), heights, rates, mixing, air gaps,
  blowout, liquid properties, and validated vendor liquid class.
- Contamination policy, controls, waste handling, operator interventions,
  acceptance criteria, and recovery procedure.

If information is missing, produce an assumptions/blockers list and an offline
draft only.

## Reproducible install

For offline API inspection and chatterbox simulation:

```bash
uv venv --python 3.11 .venv-pylabrobot
uv pip install --python .venv-pylabrobot/bin/python "PyLabRobot==0.2.1"
```

On Windows, use `.venv-pylabrobot\Scripts\python.exe`. Do not install hardware
extras until the user names the device and explicitly approves its transport
dependencies. Then inspect the matching stable device page before considering a
pin such as `"PyLabRobot[serial]==0.2.1"` or `"PyLabRobot[usb]==0.2.1"`.

## Offline-first workflow

Run from the repository root. Every bundled CLI uses strict, bounded UTF-8
JSON/CSV, local non-symlink paths, fixed allowlists, and JSON output. None can
select a live backend.

```bash
python3 skills/pylabrobot/scripts/validate_manifest.py \
  --input tests/pylabrobot/fixtures/protocol_manifest.json

python3 skills/pylabrobot/scripts/check_deck_geometry.py \
  --input tests/pylabrobot/fixtures/protocol_manifest.json

python3 skills/pylabrobot/scripts/plan_transfers.py \
  --manifest tests/pylabrobot/fixtures/protocol_manifest.json \
  --transfers tests/pylabrobot/fixtures/transfers.csv

python3 skills/pylabrobot/scripts/generate_simulation_plan.py \
  --manifest tests/pylabrobot/fixtures/protocol_manifest.json \
  --transfers tests/pylabrobot/fixtures/transfers.csv

python3 skills/pylabrobot/scripts/inspect_backends.py \
  --expected-version 0.2.1 --strict
```

The geometry checker uses conservative static axis-aligned boxes; it is not a
motion planner. The transfer planner requires one new tip per row and checks
source/dead/destination volumes, tip capacity, wells, channels, heights, rates,
units, and allowlists. Review
`assets/protocol-manifest.schema.json` and the synthetic fixtures before making
a project-specific manifest.

## Verified software-only example

The exact backend below is software-only. Do not substitute a hardware backend.

```python
from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import LiquidHandlerChatterboxBackend
from pylabrobot.resources import (
    Cor_96_wellplate_360ul_Fb,
    PLT_CAR_L5AC_A00,
    TIP_CAR_480_A00,
    hamilton_96_tiprack_1000uL_filter,
    set_tip_tracking,
    set_volume_tracking,
)
from pylabrobot.resources.hamilton import STARLetDeck

set_tip_tracking(True)
set_volume_tracking(True)

deck = STARLetDeck()
tip_carrier = TIP_CAR_480_A00(name="tip_carrier")
tips = hamilton_96_tiprack_1000uL_filter(name="tips")
tip_carrier[0] = tips
plate_carrier = PLT_CAR_L5AC_A00(name="plate_carrier")
source = Cor_96_wellplate_360ul_Fb(name="source")
destination = Cor_96_wellplate_360ul_Fb(name="destination")
plate_carrier[0] = source
plate_carrier[1] = destination
deck.assign_child_resource(tip_carrier, rails=3)
deck.assign_child_resource(plate_carrier, rails=15)
source.get_well("A1").tracker.set_volume(100.0)  # planned state, not sensing

lh = LiquidHandler(backend=LiquidHandlerChatterboxBackend(), deck=deck)
await lh.setup()  # safe here only because the backend above is software-only
try:
    await lh.pick_up_tips(tips["A1"])
    await lh.aspirate(source["A1"], vols=[10.0])
    await lh.dispense(destination["A1"], vols=[10.0])
    await lh.return_tips()
finally:
    await lh.stop()
```

## API rules that prevent stale code

- Current names are `STARBackend`, `VantageBackend`, `EVOBackend`, and
  `OpentronsOT2Backend`; do not use stale `STAR`, `TecanBackend`,
  `OpentronsBackend`, or `ChatterboxBackend` imports.
- Use `LiquidHandlerChatterboxBackend` for generic offline liquid-handler
  testing. `ChatterBoxBackend` is a separate legacy-named export; do not
  conflate the two.
- `Visualizer(resource=...)` is valid, followed by `await vis.setup()` and
  `await vis.stop()`; it starts localhost HTTP/WebSocket servers and may open a
  browser.
- There is no generic `from pylabrobot.liquid_handling import LiquidClass` in
  0.2.1. Stable liquid classes are vendor-specific, for example
  `pylabrobot.liquid_handling.liquid_classes.hamilton.HamiltonLiquidClass`.
- Most frontend methods are async. Backend kwargs and capabilities are
  vendor/model specific; a shared frontend does not imply identical behavior.

## References

- [Liquid handling](references/liquid-handling.md) — operations, tips, tracking,
  liquid classes, units, and validation.
- [Resources](references/resources.md) — decks, coordinates, plates, tip racks,
  collisions, state, and serialization.
- [Hardware backends](references/hardware-backends.md) — verified names,
  support levels, capabilities, and live-run gate.
- [Analytical equipment](references/analytical-equipment.md) — plate readers
  and scales.
- [Material handling](references/material-handling.md) — pumps, heaters,
  shakers, temperature control, storage, and centrifuges.
- [Visualization](references/visualization.md) — chatterbox, Visualizer,
  localhost services, and simulation limits.

## Dated upstream sources

Checked **2026-07-23**:

- [PyPI 0.2.1](https://pypi.org/project/PyLabRobot/) — released 2026-03-23;
  Python >=3.9; extras and artifacts.
- [Stable installation guide](https://docs.pylabrobot.org/stable/user_guide/_getting-started/installation.html)
  — stable versus source/dev install and optional transport groups.
- [Stable API](https://docs.pylabrobot.org/stable/api/pylabrobot.html) and
  [supported machines](https://docs.pylabrobot.org/stable/user_guide/machines.html)
  — 0.2.1 API and model-specific support labels.
- [`v0.2.1` source tag](https://github.com/PyLabRobot/pylabrobot/tree/v0.2.1)
  and [changelog](https://github.com/PyLabRobot/pylabrobot/blob/main/CHANGELOG.md)
  — tag dated 2026-03-23; `Unreleased` is development-only.

## Citing Scientific Agent Skills

This skill is part of Scientific Agent Skills by K-Dense. If it materially contributed to a
manuscript, report, presentation, or code release, add the paper to the references or
software section and tell the user you did so:

> Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). Scientific Agent
> Skills: A Library of Procedural Knowledge for Research Agents. arXiv:2609.00065.
> https://doi.org/10.48550/arXiv.2609.00065

Always cite the current version. The DOI and https://arxiv.org/abs/2609.00065 resolve to the
latest arXiv version, so never append a version suffix such as `v1`. When network access is
available, fetch https://arxiv.org/abs/2609.00065 (or
http://export.arxiv.org/api/query?id_list=2609.00065) before writing the reference and take
the author list, year, and version from that record. If the record lists a journal reference
or publisher DOI, cite the published version instead.
