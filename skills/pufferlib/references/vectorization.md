# Vectorization and Throughput

Review: **2026-10-01**. Native 5.0 guidance is in [native-5.md](native-5.md);
3.0 and the pinned 4.0 snapshot below are historical profiles. PufferLib's published 3.0.0 package and
historical 4.0 source line expose different vectorization systems. Never mix their
configuration names.

## Version split

| Profile | Vectorization surface | Use for |
|---|---|---|
| PyPI `pufferlib==3.0.0` | `pufferlib.vector.make`; `Serial`, `Multiprocessing`, optional `Ray`, and native `PufferEnv` backends | Published Python/Gymnasium/PettingZoo compatibility workflows |
| Source `4.0` at a pinned commit | Native C vector interface configured by `[vec] total_agents`, `num_buffers`, and `num_threads` | Historical Ocean/native trainer source |

The 4.0 package directory no longer contains the 3.0 `vector.py`,
`emulation.py`, or `pytorch.py` modules. Treat old examples importing those
modules as 3.0 examples, even if a stale copy remains under the 4.0 `examples/`
tree.

## Published 3.0.0 API

The source signature is:

```python
pufferlib.vector.make(
    env_creator_or_creators,
    env_args=None,
    env_kwargs=None,
    backend=pufferlib.PufferEnv,
    num_envs=1,
    seed=0,
    **kwargs,
)
```

Select a backend explicitly during development:

```python
import pufferlib.vector

serial = pufferlib.vector.make(
    reviewed_env_creator,
    backend=pufferlib.vector.Serial,
    num_envs=4,
    seed=42,
)

parallel = pufferlib.vector.make(
    reviewed_env_creator,
    backend=pufferlib.vector.Multiprocessing,
    num_envs=16,
    num_workers=4,
    batch_size=8,
    zero_copy=True,
    seed=42,
)
```

Do not replace `reviewed_env_creator` with a dotted import string. Import the
audited callable directly in trusted code. Environment construction executes
package code and may initialize native libraries.

### Stable backends

- `PufferEnv` is the default native backend. `vector.make` requires
  `num_envs=1` for this backend because that one native environment can manage
  many agents internally.
- `Serial` runs multiple environment instances in the caller process. Use it
  for contract debugging and deterministic comparisons.
- `Multiprocessing` uses worker processes and shared arrays. It supports the
  synchronous `reset`/`step` facade and asynchronous `async_reset`/`recv` plus
  `send`/`recv`.
- `Ray` is an optional 3.0 backend and requires the package's pinned Ray extra.
  It introduces a separate distributed runtime and is not a safe local default.

### Shape semantics

Do not assume `num_envs == returned batch length`.

- A single environment advertises `num_agents`,
  `single_observation_space`, and `single_action_space`.
- The full stable batch contains agent slots. For fixed-population environments,
  serial batch length is normally `num_envs * num_agents`.
- `vecenv.agents_per_batch` is the number of agent rows returned by one receive.
- Observations have leading agent-batch dimension; rewards, terminals,
  truncations, agent IDs, and masks have matching leading length.
- A synchronous call returns
  `(observations, rewards, terminals, truncations, infos)`.
- The asynchronous `recv()` additionally returns `agent_ids` and `masks`.
- Structured observations/actions are flattened by emulation. Preserve the
  recorded dtype metadata and unflatten in the policy; do not cast arbitrary
  byte views to float first.

Validate actual shapes and dtypes at reset and the first step. In multi-agent
workflows, use masks to exclude padded or inactive slots from loss and metrics.

Episode-end semantics: emulated 3.0 environments reset on the send after a done
transition, consuming no action for that slot. Native environments can differ.
See `environments.md`; do not assume PufferLib exposes Gymnasium 1.3 autoreset
metadata or that its stock learner correctly masks reset-only transitions.

### Multiprocessing constraints

The 3.0 source validates these relationships:

1. `num_envs` must be divisible by `num_workers`.
2. `batch_size` defaults to `num_envs`.
3. `batch_size` must be divisible by `num_envs / num_workers`.
4. With zero-copy enabled, `num_envs` must be divisible by `batch_size`.
5. Physical-core oversubscription is rejected unless `overwork=True`; do not
   bypass this for benchmark headline numbers.

Always call `close()` in `finally`. Keep constructors top-level and serializable.
Protect process creation with `if __name__ == "__main__":`.

### Start methods

The stable API does not expose a `start_method` argument. The process context is
therefore affected by Python and platform defaults. Set an application-wide
method before constructing workers if your program requires one:

```python
import multiprocessing as mp

if __name__ == "__main__":
    mp.set_start_method("spawn")
    main()
```

Prefer `spawn` when CUDA, threads, or non-fork-safe native libraries may already
be initialized. Do not call `set_start_method(..., force=True)` inside a library.
Record the effective method in benchmark output. `forkserver` can also be
appropriate when available and tested. Never compare results that silently use
different methods.

### Seeding

- Pass one integer seed to `vector.make`; the stable implementation derives
  per-environment seeds.
- `reset(seed=base_seed)` similarly offsets seeds across serial environments.
- Seed action-space sampling separately when random actions are part of a test.
- A deterministic seed does not guarantee bitwise deterministic GPU training or
  deterministic third-party simulators.
- Recreate workers and environments for independent replicates; do not treat
  adjacent episodes from one long run as independent seeds.

## Historical 4.0 source

The reviewed 4.0 source uses native C environments and a different vector
layout:

```ini
[vec]
total_agents = 4096
num_buffers = 2
num_threads = 16
```

Environment instances are grouped into buffers. Native execution uses OpenMP
threads inside those buffers; rollout workers coordinate buffer transfers and,
for GPU training, pinned memory and CUDA streams. The default trainer backend is
native; `--slowly` selects the PyTorch fallback. Multi-GPU launch code explicitly
uses a `spawn` multiprocessing context.

Build and test one audited Ocean environment at a time. The C binding defines
observation size/type and action branches. A mismatch can cause memory
corruption rather than a friendly Python shape error.

## Benchmark methodology

Throughput is not a library constant. Report enough detail to reproduce it:

1. Pin source/package, Python, dependencies, compiler, and environment revision.
2. Record CPU model/core topology, GPU/driver/CUDA, OS, precision, backend,
   start method, env count, agent count, workers/threads, buffers, and batch.
3. State whether timing includes construction, reset, policy inference,
   host-device transfer, learning, rendering, logging, and checkpoint I/O.
4. Warm up separately; use a fixed number of **agent steps**, not only wall time.
5. Run at least three independent repeats; report all samples plus median and
   spread. Report failures and memory use.
6. Validate equivalent observations, actions, reset/autoreset behavior, frame
   skip, and policy workload before comparing backends.
7. Distinguish simulation SPS from end-to-end training SPS.

The 2024 compatibility paper benchmarked PufferLib 1.x-style vectorization on an
i9-14900K/RTX 4090 desktop and an i7-10750H/RTX 3070 laptop. The 2025 PufferLib
2.0 paper reports a different Ocean/training system. Those results are scoped to
their listed hardware and workloads; they are not expected values for 3.0 or
4.0.

Run the bundled bounded harness first:

```bash
python3 scripts/benchmark_vectorization.py --backend serial
python3 scripts/benchmark_vectorization.py \
  --backend multiprocessing --start-method spawn \
  --envs 8 --workers 2 --steps-per-env 2000
```

It benchmarks only the bundled synthetic environment, never imports PufferLib,
and cannot substantiate an upstream PufferLib performance claim.

## Sources

- [PufferLib 3.0 vector source](https://github.com/PufferAI/PufferLib/blob/3.0/pufferlib/vector.py)
  — stable API source; accessed 2026-07-23.
- [PufferLib 3.0 vectorization example](https://github.com/PufferAI/PufferLib/blob/3.0/examples/vectorization.py)
  — stable usage example; accessed 2026-07-23.
- [PufferLib live 5.0 documentation](https://puffer.ai/docs.html) — current native
  architecture and CLI; rechecked 2026-10-01, not a 4.0 API reference.
- [PufferLib 4.0 trainer source](https://github.com/PufferAI/PufferLib/blob/25647630e1b15330bb3153a5a0d3ff8d234c3acf/pufferlib/pufferl.py)
  — historical config and spawn behavior; accessed 2026-07-23.
- [PufferLib compatibility paper](https://arxiv.org/abs/2406.12905) — submitted
  2024-06-11.
- [PufferLib 2.0 paper](https://openreview.net/forum?id=qRyteMTgn0) —
  Reinforcement Learning Journal, 2025.
