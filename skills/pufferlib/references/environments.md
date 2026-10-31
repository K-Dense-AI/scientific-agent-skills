# Environment Contracts and Native Environments

Review: **2026-10-01**. Native 5.0 guidance is in [native-5.md](native-5.md);
3.0 and the pinned 4.0 snapshot below are historical profiles.

## Start from the Gymnasium contract

A current single-agent Gymnasium environment defines `observation_space` and
`action_space`, then implements:

```python
def reset(self, *, seed=None, options=None):
    super().reset(seed=seed)
    return observation, info

def step(self, action):
    return observation, reward, terminated, truncated, info
```

Contract requirements:

- `observation` must be contained in `observation_space` after reset and every
  step, with the documented shape and dtype.
- `action` must be contained in `action_space`.
- `reward` is a finite scalar for ordinary single-agent tasks.
- `terminated` means the task's MDP reached a terminal state.
- `truncated` means an external limit ended the episode, commonly a time limit.
- `info` is a dictionary; never hide the only termination signal in it.
- Call `reset()` after either `terminated` or `truncated`.
- Seed the environment through `reset(seed=...)`. Seed the action space
  separately when sampled actions must be reproducible.
- Always call `close()`.

Both flags can be true in Gymnasium (for example a terminal at a time limit).
The synthetic helper deliberately makes its own flags mutually exclusive; that
is not a universal Gymnasium requirement.

Do not collapse `terminated` and `truncated` during learning. A time-limit
truncation can still permit value bootstrapping; a true terminal state does not.

Run the local contract tool before involving PufferLib:

```bash
python3 scripts/env_contract_validator.py
```

It validates only the bundled synthetic environment. It intentionally has no
module-path option, so it cannot dynamically import an untrusted package.

## Autoreset and final observations

Gymnasium 1.3's built-in vector APIs default to `NEXT_STEP`. A reset-only call
ignores that slot's action and must be excluded from learning transitions.
`SAME_STEP` returns the reset observation; the terminal observation is in
`infos["final_obs"]` with the `_final_obs` validity mask. `DISABLED` requires an
explicit boolean `reset_mask`. Record `metadata["autoreset_mode"]`, wrapper
compatibility and the resolved version. Bootstrap truncations from the final
pre-reset observation, not the next episode; terminals suppress bootstrapping.

PufferLib 3.0 pins Gymnasium `<=0.29.1`, and its own `Serial`/worker machinery
resets an already-done adapter on the next send. This is not Gymnasium 1.3's
VectorEnv contract. Do not inject a current Gymnasium vectorizer or assume its
`final_obs` key exists in PufferLib. Inspect returned arrays and exclude
reset-only transitions. Native PufferEnv implementations own their autoresets.
The bundled validator checks only the synthetic single-environment contract.

## Published PufferLib 3.0.0 native contract

For a native Python `PufferEnv`, assign these attributes **before** calling
`super().__init__(buf)`:

```python
import gymnasium
import numpy as np
import pufferlib


class ReviewedEnv(pufferlib.PufferEnv):
    def __init__(self, buf=None, seed=0):
        self.single_observation_space = gymnasium.spaces.Box(
            low=-1.0, high=1.0, shape=(4,), dtype=np.float32
        )
        self.single_action_space = gymnasium.spaces.Discrete(3)
        self.num_agents = 2
        super().__init__(buf)
```

The stable base accepts a Box observation space and Discrete, MultiDiscrete, or
Box action space. It allocates or attaches:

- `observations`
- `actions`
- `rewards`
- `terminals`
- `truncations`
- `masks`

Native methods operate on those buffers:

```python
def reset(self, seed=None):
    # update self.observations in place
    return self.observations, []

def step(self, actions):
    # update all buffers in place
    return (
        self.observations,
        self.rewards,
        self.terminals,
        self.truncations,
        [],
    )
```

The `infos` value for native Puffer environments is a list of dictionaries.
PufferLib's native interface expects vector rows for agents, even when there is
one agent. Native environments handle their own resets; clear rewards,
terminals, truncations, masks, and partially written observations explicitly.
Never leave a previous step's buffer values in place.

### Native shape checklist

For `A = num_agents` and single observation shape `S`:

- observations: `(A, *S)`
- rewards: `(A,)`
- terminals: `(A,)`
- truncations: `(A,)`
- masks: `(A,)`
- actions: joint shape derived from the single action space and `A`

Validate the exact allocated action shape rather than assuming `(A,)`, especially
for MultiDiscrete and Box actions.

## Stable Gymnasium and PettingZoo adaptation

PufferLib 3.0 uses explicit adapters:

```python
import pufferlib.emulation

wrapped = pufferlib.emulation.GymnasiumPufferEnv(reviewed_gymnasium_instance)
```

or:

```python
wrapped = pufferlib.emulation.PettingZooPufferEnv(reviewed_parallel_instance)
```

There is no supported 3.0 `pufferlib.emulate(...)` convenience function matching
the old skill examples. Pass either an `env` instance or an `env_creator`
callable according to the class signature; do not pass both.

The Gymnasium adapter:

- maps structured observation/action spaces to flat arrays;
- checks the first observation and action against the original spaces;
- returns separate terminal and truncation values;
- requires reset before step and reset after episode end.

The PettingZoo adapter:

- targets the Parallel API;
- uses `possible_agents` as the fixed slot set;
- pads missing agents and exposes masks;
- canonicalizes per-agent spaces and flattened buffers.

Validate heterogeneous-agent spaces before use. The adapter derives its single
spaces from the first possible agent, so environments with incompatible spaces
need an explicit reviewed transformation.

### Structured spaces

Stable emulation supports Box, Discrete, MultiDiscrete, Tuple, and Dict patterns
through a packed NumPy dtype. This is byte-layout conversion, not semantic
feature engineering. Check:

- deterministic Dict key order;
- leaf shape and dtype;
- finite numeric values;
- lossless action reconstruction;
- policy-side unflattening;
- padding/mask handling for variable populations.

## Historical 4.0 Ocean contract

The reviewed 4.0 source focuses on first-party C environments. It no longer
provides the 3.0 Python emulation/vector modules. The official starting points
are:

- `ocean/squared`: commented single-agent template
- `ocean/target`: commented multi-agent template

A binding defines compile-time metadata such as:

```c
#define OBS_SIZE 121
#define NUM_ATNS 1
#define ACT_SIZES {5}
#define OBS_TENSOR_T ByteTensor

#define Env Squared
#include "vecenv.h"
```

The environment struct must include pointers for observations, actions,
rewards, and terminals, plus `num_agents` and a log struct. It implements
`c_reset`, `c_step`, `c_render`, and `c_close`; `binding.c` supplies `my_init`
and `my_log`.

Security and correctness rules:

1. Treat the C environment and every linked library as native code.
2. Verify repository/commit, license, asset rights, and checksums before build.
3. Build only the selected environment in a disposable container or VM.
4. Start with the local/address-sanitizer build described by upstream.
5. Match `OBS_SIZE`, tensor dtype, action branch count/sizes, and actual writes.
6. Bounds-check every index and allocation; use checked arithmetic for sizes.
7. Initialize every output element each step. Reset reward/terminal buffers
   before early returns.
8. Use an environment-owned RNG seeded per instance; do not use global RNG
   state for reproducibility.
9. Free only memory owned by the environment. Do not free framework buffers.
10. Fuzz reset/step/action boundaries before optimization.

`c_step` may reset immediately after marking a terminal. Record this autoreset
behavior when interpreting terminal observations.

## Environment provenance

An environment package may execute arbitrary Python/native code and may fetch
assets at import, build, reset, or render time. Before execution:

- use the official repository and immutable revision;
- inspect package/build scripts and transitive dependencies;
- verify artifact hashes or attestations;
- review license compatibility for code, datasets, media, ROMs, maps, and model
  opponents separately;
- reject unlicensed ROMs or “accept ROM license” automation without proof of
  rights;
- disable network and credentials in the first-run sandbox;
- cap disk, memory, processes, threads, episode length, agents, and render size;
- do not load bundled checkpoints or pickle files during environment import.

An entry in Ocean/config is not a blanket security, quality, or licensing
approval.

## Testing ladder

1. Built-in synthetic contract validator.
2. One environment, one seed, serial, tens of steps.
3. Boundary actions and intentionally invalid actions.
4. Termination and time-limit truncation tests.
5. Same-seed trace comparison.
6. Independent-seed diversity check.
7. Structured-space round trip.
8. Multi-agent join/leave and mask tests.
9. Serial versus vectorized trace equivalence where ordering permits.
10. Bounded throughput benchmark only after correctness passes.

## Sources

- [Gymnasium vector API](https://gymnasium.farama.org/api/vector/) and
  [autoreset modes](https://farama.org/Vector-Autoreset-Mode) — checked 2026-10-01.


- [Gymnasium Env API](https://gymnasium.farama.org/api/env/) — current reset,
  step, spaces, and seeding contract; accessed 2026-07-23.
- [Gymnasium terminated/truncated explanation](https://farama.org/Gymnasium-Terminated-Truncated-Step-API)
  — published 2023-10-27; accessed 2026-07-23.
- [PufferLib 3.0 core environment source](https://github.com/PufferAI/PufferLib/blob/3.0/pufferlib/pufferlib.py)
  — stable native contract; accessed 2026-07-23.
- [PufferLib 3.0 emulation source](https://github.com/PufferAI/PufferLib/blob/3.0/pufferlib/emulation.py)
  — stable adapters; accessed 2026-07-23.
- [PufferLib 3.0 Gymnasium example](https://github.com/PufferAI/PufferLib/blob/3.0/examples/gymnasium_env.py)
  — stable example; accessed 2026-07-23.
- [PufferLib 3.0 PettingZoo example](https://github.com/PufferAI/PufferLib/blob/3.0/examples/pettingzoo_env.py)
  — stable example; accessed 2026-07-23.
- [PufferLib 4.0 Squared template](https://github.com/PufferAI/PufferLib/tree/25647630e1b15330bb3153a5a0d3ff8d234c3acf/ocean/squared)
  — historical single-agent native template; accessed 2026-07-23.
- [PufferLib 4.0 Target template](https://github.com/PufferAI/PufferLib/tree/25647630e1b15330bb3153a5a0d3ff8d234c3acf/ocean/target)
  — historical multi-agent native template; accessed 2026-07-23.
- [PufferLib Ocean](https://puffer.ai/ocean.html) — current first-party
  collection; accessed 2026-07-23.
