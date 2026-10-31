# Integration, Security, and Migration Guide

Review: **2026-10-01**. Native 5.0 guidance is in [native-5.md](native-5.md);
3.0 and the pinned 4.0 snapshot below are historical profiles.

## Compatibility matrix

| Need | Published `pufferlib==3.0.0` | Historical `4.0` source |
|---|---|---|
| Gymnasium instance adaptation | `pufferlib.emulation.GymnasiumPufferEnv` | Removed from reviewed 4.0 source |
| PettingZoo Parallel adaptation | `pufferlib.emulation.PettingZooPufferEnv` | Removed from reviewed 4.0 source |
| Python vector backends | `pufferlib.vector` | Removed from reviewed 4.0 source |
| Native Python `PufferEnv` | Supported | Replaced by historical C/Ocean interface |
| Trainer | `pufferlib.pufferl.PuffeRL` | Native backend or `pufferlib.torch_pufferl.PuffeRL` |
| External logging | W&B; Neptune historical/shut down | W&B in historical CLI |
| Primary config | merged INI sections | different INI schema |
| Checkpoints | Torch state dict plus trainer state | native `.bin`; Torch fallback state dict |

Pin a profile. Do not import from a floating branch or blend examples across
columns.

## Correct stable adaptation patterns

### Gymnasium

```python
import gymnasium
import pufferlib.emulation
import pufferlib.vector


def make_env(buf=None, seed=0):
    raw = gymnasium.make("CartPole-v1")
    return pufferlib.emulation.GymnasiumPufferEnv(raw, buf=buf, seed=seed)


vecenv = pufferlib.vector.make(
    make_env,
    backend=pufferlib.vector.Serial,
    num_envs=2,
    seed=42,
)
try:
    observations, infos = vecenv.reset(seed=42)
    vecenv.action_space.seed(43)
    actions = vecenv.action_space.sample()
    observations, rewards, terminals, truncations, infos = vecenv.step(actions)
finally:
    vecenv.close()
```

This source-reviewed pattern is illustrative, not a native PufferLib runtime
test. The vectorizer injects `buf` and `seed` into creators; a zero-argument
factory fails. Use Gymnasium 0.29.1/NumPy <2 with the published package, not
the current Gymnasium 1.3 vector API.

### PettingZoo

Use a reviewed Parallel environment instance:

```python
wrapped = pufferlib.emulation.PettingZooPufferEnv(reviewed_parallel_env)
```

The stable source does not document automatic AEC-to-Parallel conversion in
this adapter. Convert explicitly with PettingZoo's supported utilities only
when the environment's turn semantics permit it, then test action ordering,
dead-agent handling, masks, and termination/truncation dictionaries.

### Native stable environment

Subclass `pufferlib.PufferEnv`, define `single_observation_space`,
`single_action_space`, and `num_agents` before `super().__init__`, then update
the provided arrays in place. Native Puffer environments are already vector
interfaces; do not return Gym's scalar four-tuple.

## Unsupported shortcuts from the old skill

Remove or migrate these historical patterns:

| Historical pattern | Current guidance |
|---|---|
| `pufferlib.make("name", ...)` | Stable: import an audited creator and use `pufferlib.vector.make`; 4.0: build/configure a named native environment |
| `pufferlib.emulate(...)` | Stable: instantiate `GymnasiumPufferEnv` or `PettingZooPufferEnv` explicitly |
| `pufferlib.vectorization.Serial` | Stable module is `pufferlib.vector.Serial` |
| `from pufferlib import PuffeRL` | Stable trainer is `pufferlib.pufferl.PuffeRL`; 4.0 fallback is in `torch_pufferl` |
| define native `observation_space`/`action_space` | Stable native class requires `single_observation_space`/`single_action_space` before `super()` |
| return `(obs, reward, done, info)` | Return separate termination and truncation values |
| native multi-agent dictionaries and `dones["__all__"]` | Use stable vector buffers or a reviewed PettingZoo Parallel adapter |
| arbitrary dotted `entry_point` registration | Import an audited callable directly; bundled tools reject dotted paths |
| top-level `WandbLogger`/`NeptuneLogger` | Stable logger classes live in `pufferlib.pufferl`; prefer the CLI and sanitized config |
| assume Atari/Procgen/NetHack names exist everywhere | Verify the chosen version's config/source and install the separately reviewed environment |

## Migrating 3.0 to 4.0

This is a redesign, not a drop-in upgrade:

1. Preserve the 3.0 lock, source digest, config, checkpoint hashes, and baseline
   evaluation before changing anything.
2. Inventory use of `emulation`, `vector`, `PufferEnv`, third-party environments,
   policy wrappers, INI keys, logger flags, and Torch checkpoints.
3. Decide whether the application should stay on published 3.0.0 or port to a
   historical 4.0 C environment. The pinned 4.0 package tree has no Python
   emulation/vector modules. For a new native port, use the separate 5.0 guide.
4. Port environment logic to the reviewed Squared/Target C binding contract.
5. Recreate configuration using 4.0 `[vec]`, `[policy]`, `[torch]`, and `[train]`
   keys. Do not mechanically rename old keys.
6. Rebuild policy composition around 4.0 encoder/decoder/network modules or the
   native backend.
7. Treat old `.pt` and new `.bin` files as incompatible unless an official,
   tested converter says otherwise. Do not improvise binary conversion.
8. Re-run contract, same-seed trace, throughput, and held-out learning
   baselines. Attribute behavior changes; do not compare headline SPS alone.

The historical 4.0 snapshot contains some stale 3.0-style examples even though the
corresponding modules are absent. Prefer current implementation and docs over
those copied examples.

## Third-party environments and native code

Environment extras can pull old Gym versions, native libraries, renderers,
emulators, datasets, model opponents, and ROM tooling. A package name in a
PufferLib optional extra is not a security or license endorsement.

Before install/import/build:

1. Identify the official repository and immutable revision.
2. Read build/install hooks and all network downloads.
3. Verify licenses for code and assets separately.
4. Verify hashes/attestations; record missing provenance.
5. Use a disposable sandbox without credentials, home-directory mounts, or
   network after required artifacts are staged.
6. Cap processes, threads, memory, disk, render resolution, agents, and steps.
7. Do not execute bundled native extensions, ROMs, checkpoints, or pickle files
   until separately trusted.

For Atari and similar systems, the user must supply legally obtained assets.
Never download ROM sets or auto-accept a license on the user's behalf.

## Logging integration

External tracking is disabled by default. The stable logger implementations can
log the full argument mapping and upload model artifacts at close. The PyPI
3.0.0 sdist has no CLI opt-out for that upload; use local logging or a reviewed
custom logger for metrics-only tracking. Neptune hosted service is retired
(2026-03-05); its token/integration names below are historical. Therefore:

- sanitize arguments before logger construction;
- keep `WANDB_API_KEY` and `NEPTUNE_API_TOKEN` only in an approved environment
  injection or secret manager;
- never add credential keys to nested INI/JSON/config objects;
- do not pass a token on the command line;
- disable model/source upload unless explicitly approved;
- review project visibility, retention, residency, access controls, and cost;
- use vendor offline/disabled modes only after confirming what is written
  locally and how later sync behaves.

Do not print all environment variables or recursively discover `.env` files.
Checking whether one explicitly named credential variable exists can be
acceptable; reading or logging its value is not.

## Integration acceptance test

For each reviewed environment/profile:

1. Create one instance without network or GPU.
2. Validate spaces and reset return.
3. Step a fixed action trace until both ordinary and episode-end paths run.
4. Verify terminated/truncated semantics and final observation behavior.
5. Close and confirm no child processes/resources remain.
6. Run stable Serial or one 4.0 local native instance.
7. Compare a same-seed trace.
8. Scale to two workers/threads with small caps.
9. Run policy shape and finite-value checks.
10. Run held-out evaluation with logging still disabled.

Only then consider GPU training, external logging, or larger parallelism.

## Sources

- [PufferLib PyPI 3.0.0](https://pypi.org/project/pufferlib/3.0.0/) —
  published 2025-06-23; accessed 2026-07-23.
- [PufferLib 3.0 emulation source](https://github.com/PufferAI/PufferLib/blob/3.0/pufferlib/emulation.py)
  — stable adapters; accessed 2026-07-23.
- [PufferLib 3.0 vector source](https://github.com/PufferAI/PufferLib/blob/3.0/pufferlib/vector.py)
  — stable vector API; accessed 2026-07-23.
- [PufferLib 3.0 trainer source](https://github.com/PufferAI/PufferLib/blob/3.0/pufferlib/pufferl.py)
  — stable logger/checkpoint behavior; accessed 2026-07-23.
- [PufferLib 4.0 package tree](https://github.com/PufferAI/PufferLib/tree/25647630e1b15330bb3153a5a0d3ff8d234c3acf/pufferlib)
  — historical modules; accessed 2026-07-23.
- [PufferLib live 5.0 docs](https://puffer.ai/docs.html) — current native architecture;
  checked 2026-10-01. Historical 4.0 module removal is verified from pinned source.
- [PufferLib releases](https://github.com/PufferAI/PufferLib/releases) —
  checked for source releases on 2026-07-23.
- [Gymnasium Env API](https://gymnasium.farama.org/api/env/) — current
  single-agent contract; accessed 2026-07-23.
- [PyTorch security policy](https://github.com/pytorch/pytorch/security) —
  model/native-package safety; accessed 2026-07-23.
