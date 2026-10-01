# Native PufferLib 5.0

Reviewed 2026-10-01 against official live docs and source commit
`6ffa5b10dbbbe4d1e8288367c7d9d3acd3bad4a2`. This is a source profile, not a
PyPI 5.0 package. Commands below are source-reviewed examples, not an executed
native build or training benchmark. The bundled Python planners support only
historical 3.0/4.0 schemas and must not generate 5.0 commands.

## Build one environment

Pin the source commit and record the compiler, platform, build flags, source
diff, environment config, dependencies and asset hashes. `build.sh` can download
Raylib 5.5 release archives and, for relevant environments, Box2D from a mutable
`latest` release URL. Those downloads are not checksum-locked by the script.
Review/pin them for reproducible builds. The official PufferTank installer is
an installation convenience; do not treat the moving installer as a lockfile.

- CUDA training requires NVIDIA hardware plus a CUDA development toolchain,
  including `nvcc`, cuBLAS, cuSOLVER, cuRAND, NCCL and NVML at this revision.
  The native trainer is C/CUDA, not a pip-installed Torch trainer.
- `--cpu` builds standalone evaluation/play. **There is no CPU training mode.**
- The build script has Linux and macOS paths (macOS uses Homebrew `libomp` and
  system frameworks). Its Linux Raylib archive is amd64. Native Windows and
  Linux ARM compatibility are not established by these paths; WSL/native builds
  need separate validation. This review did not build either platform.
- `--debug` adds ASan/UBSan flags on the Linux CPU path; the inspected macOS path
  leaves sanitizer flags empty. Do not assume the docs' sanitizer claim holds
  on every platform.
- GPU-only environments such as `robot_arm` reject CPU/web builds. `--cu`
  selects a CUDA environment implementation; an ordinary CPU environment can
  still be used by the CUDA trainer.

Illustrative CPU development commands from the repository root:

```bash
./build.sh breakout --cpu --debug
./breakout --headless
```

At the pinned revision, standalone headless execution without an explicit
`eval_episodes` override runs 1024 steps. With no checkpoint it is an untrained
environment smoke test. With `--base.eval_episodes=N`, it runs until the
environment's `log.n` reaches N; impose an external wall-time cap because the
meaning/rate of that counter is environment-specific.

Illustrative CUDA training and exact-checkpoint evaluation:

```bash
./build.sh breakout --cu
./puffer train --base.seed=42 --train.total_timesteps=100000
./puffer eval checkpoints/breakout/RUN/EXACT.bin --headless --base.eval_episodes=10
```

`RUN/EXACT.bin` is a placeholder, not a shipped checkpoint. The selected environment
is compiled into the binary. Do not add an environment positional argument to
`./puffer train`. The current parser supports `train`, `eval`, `match`, `sweep`,
`--headless`, and section-qualified `--section.key=value` overrides. Use
underscores exactly as in the INI keys; historical Python CLI hyphenated flags
are a different parser. There is no `--slowly`, `--wandb`, or `--neptune` path in
the reviewed native trainer.

## Environment contract: inspect the pinned header

The live docs still mention a `binding.c` checklist. At the reviewed 5.0 revision,
`ocean/minimal/minimal.h` and `src/pufferenv.h` are authoritative: Minimal defines
`obs_t`, `OBS_SIZE`, `NUM_ATNS`, `ACT_SIZES`, `struct Env`, and `struct Log`.
It implements:

```c
void puf_init(Env* env, Dict* kwargs);
void puf_reset(Env* env);
void puf_step(Env* env);
void puf_render(Env* env);
void puf_close(Env* env);
void puf_log(Log* log, Dict* out);
```

This is not the 4.0 `c_step`/`binding.c` interface. Each `Agent` holds observation,
action, reward and terminal pointers, an optional action mask and a policy index.
Environment-owned state includes agent count and RNG state. Logs contain floats,
with `n` last in the template. Inspect allocation ownership and metadata against
every buffer write. `OBS_SIZE` is per agent; actions can have multiple branches.
CPU implementations step one `Env`; GPU implementations step a device batch and
have additional stream/vector-creation hooks. Porting requires more than renaming
functions.

There is a terminal buffer but **no separate truncation buffer** in this interface.
Do not claim Gymnasium time-limit bootstrapping semantics automatically survive a
port. Define how time limits, terminal transitions, immediate reset, final
observations and recurrent-state reset are represented, and verify the learner's
target calculation. The Minimal example is continuing coordination; `log.n`
counts logged task events and is not automatically an episode count. Use an
episodic environment/test when evaluating end-of-episode behavior.

## Vectorization, policy and PPO

Current configuration uses `[vec] total_agents`, `num_buffers`, `num_threads`;
`[policy] hidden_size`, `num_layers`; and `[train] horizon`, `minibatch_size`,
`total_timesteps`. CPU environment buffers coordinate OpenMP workers and CUDA
streams; the reviewed GPU environment path asserts `num_buffers == 1`. Record
resolved environment overrides rather than copying default.ini blindly.

The trainer implements a PPO variant. Record `[base] async` (one-epoch actor/learner
pipelining), `reset_every_horizon`, `cudagraphs`, seed, the policy architecture,
GAE/V-trace settings, replay ratio, reward transformation and precision.
The reviewed defaults use asynchronous execution and carry recurrent state across
horizons, resetting it on terminal signals. Compare synchronous/asynchronous and
float/default precision only with the same environment workload and evaluation
protocol. The default precision is bf16; `--float` is a build-time comparison.
The historical Python `Policy(encoder, decoder, network)` API does not apply.

## Evaluation and checkpoints

For CPU evaluation, build the matching environment and pass an explicit model:

```bash
./build.sh breakout --cpu
./breakout checkpoints/breakout/RUN/EXACT.bin --headless --base.eval_episodes=10
```

Keep the matching environment INI and policy dimensions. Native `.bin` files
are raw weight data, not self-describing training checkpoints. The trainer
reads a number of float bytes derived from the current architecture; a successful
size check cannot prove that architecture/action ordering matches. Record exact
path, SHA-256, byte size, source/build revision and complete config. The bundled
`inspect_checkpoint.py` only hashes/classifies bytes; it cannot validate weights.
`latest` recursively selects a file by filesystem times and is unsuitable for
reproducible evaluation. Model weights do not restore optimizer/RNG/environment
state for an exact resume.

A seed config entry alone is insufficient: inspect the selected environment's
RNG and the standalone runner's initialization. In particular, the reviewed
standalone runner does not consume `base.seed` to initialize the environment RNG;
do not claim independent evaluation seeds simply by changing that flag. Implement
and test explicit seed wiring before reporting a multi-seed CPU evaluation.
Report held-out environment instances, completed episodes/events, action-sampling
protocol, recurrent resets and per-seed uncertainty separately from training
metrics. Constellation consumes local logs; no authenticated service or REST
request is needed for this native workflow.

## Official evidence

- [Live documentation](https://puffer.ai/docs.html): build/CLI and CPU-eval-only policy.
- [Pinned build script](https://github.com/PufferAI/PufferLib/blob/6ffa5b10dbbbe4d1e8288367c7d9d3acd3bad4a2/build.sh): platform and dependency paths.
- [Pinned environment header](https://github.com/PufferAI/PufferLib/blob/6ffa5b10dbbbe4d1e8288367c7d9d3acd3bad4a2/src/pufferenv.h) and [Minimal](https://github.com/PufferAI/PufferLib/blob/6ffa5b10dbbbe4d1e8288367c7d9d3acd3bad4a2/ocean/minimal/minimal.h): native contracts.
- [Pinned trainer](https://github.com/PufferAI/PufferLib/blob/6ffa5b10dbbbe4d1e8288367c7d9d3acd3bad4a2/src/pufferl.cu), [CPU runner](https://github.com/PufferAI/PufferLib/blob/6ffa5b10dbbbe4d1e8288367c7d9d3acd3bad4a2/src/puffercpu.c), and [config](https://github.com/PufferAI/PufferLib/blob/6ffa5b10dbbbe4d1e8288367c7d9d3acd3bad4a2/config/default.ini): parser, weight loading, evaluation and algorithm settings.
