# Policies and Model Contracts

Review: **2026-10-01**. Native 5.0 guidance is in [native-5.md](native-5.md);
3.0 and the pinned 4.0 snapshot below are historical profiles. Policy APIs changed substantially between
published PufferLib 3.0.0 and historical 4.0 source. The PyPI sdist was
hash-verified for this review; moving-branch source can differ. Policy examples
are illustrative/source-reviewed, not executed neural-network tests.

## Published 3.0.0

PufferLib 3.0 policies are ordinary `torch.nn.Module` objects. The environment
exposes `single_observation_space` and `single_action_space`; size heads from
those single-agent spaces, not from the batched spaces.

### Minimal feed-forward policy

Build an `nn.Module` with an encoder sized from
`env.single_observation_space.shape`, an action head sized from
`env.single_action_space`, and a one-value critic head. The official stable
example defines a rollout method named `forward_eval(observations, state=None)`
and makes the normal `forward` method use the same contract. Here, `forward_eval`
is a PufferLib/PyTorch method name; it does **not** invoke Python's dangerous
`eval()` builtin.

For a discrete action space, the first output contains action logits and the
second is the value estimate. Preserve the leading agent-batch dimension.

### Recurrent composition

The stable `pufferlib.models.LSTMWrapper` expects a base policy with:

```python
def encode_observations(self, observations, state=None):
    ...

def decode_actions(self, hidden):
    ...
```

The wrapper uses an `LSTMCell` during rollout inference and an `LSTM` over
time-batched data during training. Do not manually reshape recurrent state
without checking the source's batch/time convention. Verify hidden-state reset on
actual terminations/truncations; the sdist learner has incomplete truncation and
inactive-slot mask handling, so adapter correctness alone is insufficient.

### Structured observations

Stable emulation flattens `Dict` and `Tuple` spaces into a homogeneous array.
The byte layout is described by `env.emulated`. In policy setup:

```python
native_dtype = pufferlib.pytorch.nativize_dtype(env.emulated)
```

In the forward pass:

```python
structured = pufferlib.pytorch.nativize_tensor(observations, native_dtype)
```

Keep the original flattened dtype. Constructing a new float tensor before
unflattening can destroy the packed representation. Validate every recovered
leaf shape and dtype before training.

### Action spaces

The 3.0 source handles:

- `Discrete`: one categorical logits tensor.
- `MultiDiscrete`: one logits tensor per action branch.
- `Box`: a Normal distribution path for continuous actions.

Do not infer support from the 2024 paper's limitations section; that paper
describes an earlier release. Test clipping/scaling against the environment's
actual `Box.low`, `Box.high`, shape, and dtype. A `tanh` output is not a general
substitute for affine mapping to arbitrary bounds.

### Stable model utilities

Useful 3.0 symbols include:

- `pufferlib.pytorch.layer_init`
- `pufferlib.pytorch.nativize_dtype`
- `pufferlib.pytorch.nativize_tensor`
- `pufferlib.models.Default`
- `pufferlib.models.LSTMWrapper`
- `pufferlib.models.Convolutional`
- `pufferlib.models.ProcgenResnet`

Inspect the exact 3.0 source before copying signatures. Do not use top-level
`from pufferlib import PuffeRL`; the trainer is
`pufferlib.pufferl.PuffeRL`.

## Historical 4.0 source

The historical PyTorch fallback composes a policy from three modules:

```python
policy = pufferlib.models.Policy(
    encoder=encoder,
    decoder=decoder,
    network=network,
)
```

The source contract is:

- `Policy.initial_state(batch_size, device)`
- `Policy.forward_eval(x, state)` for rollout inference
- `Policy.forward(x)` for time-batched training
- encoder maps observations to hidden vectors
- recurrent/network module maps hidden vectors and state
- decoder maps hidden vectors to action logits and values

Historical built-ins include `DefaultEncoder`, `DefaultDecoder`, `MLP`, `MinGRU`,
`LSTM`, `GRU`, `NatureEncoder`, and `ImpalaEncoder`. INI config selects the
Torch fallback components:

```ini
[torch]
network = MinGRU
encoder = DefaultEncoder
decoder = DefaultDecoder

[policy]
hidden_size = 128
num_layers = 4
```

The default 4.0 backend is the native implementation, not this Torch fallback.
The CLI flag `--slowly` selects the fallback.

## Shape and numerical checks

Run these checks before a long job:

1. Reset the reviewed environment and record observation shape/dtype/range.
2. Run one policy inference under `torch.no_grad()`.
3. For discrete actions, require logits shape
   `(agent_batch, action_space.n)`.
4. Require values to represent one scalar per active agent.
5. For `MultiDiscrete`, verify branch count and each branch width.
6. For recurrent policies, verify state batch matches active agent rows and
   that masks reset state at episode boundaries.
7. Reject NaN/Infinity in observations, logits, values, losses, and gradients.
8. Confirm inactive/padded multi-agent rows do not contribute to loss.
9. Run backward once and verify finite, non-missing gradients.
10. Compare eager and compiled outputs before enabling compilation.

`torch.compile` and reduced precision can alter performance and numerical
behavior. Record PyTorch, CUDA, compiler mode, precision, and deterministic
settings. Do not claim determinism solely because seeds are fixed.

## Checkpoint-safe policy workflow

- Save weights/state dictionaries, architecture config, environment revision,
  package lock, seed, and checksum separately.
- Do not serialize arbitrary policy objects.
- Never call `torch.load` on an untrusted file. PufferLib 3.0 and the 4.0 Torch
  fallback use `torch.load` for model paths; provenance review is therefore a
  precondition, not an optional cleanup.
- Inspect metadata first with `scripts/inspect_checkpoint.py`; it never imports
  Torch or deserializes.
- Verify an expected SHA-256 and license before loading.
- If business requirements force inspection of an untrusted model, isolate the
  operation in a disposable sandbox with no credentials, network, host mounts,
  or sensitive data. PyTorch warns that models are programs and that even
  inspection tools may execute model code.

## Sources

- [PufferLib 3.0 policy example](https://github.com/PufferAI/PufferLib/blob/3.0/examples/pufferl.py)
  — stable example; accessed 2026-07-23.
- [PufferLib 3.0 PyTorch utilities](https://github.com/PufferAI/PufferLib/blob/3.0/pufferlib/pytorch.py)
  — stable implementation; accessed 2026-07-23.
- [PufferLib 3.0 models](https://github.com/PufferAI/PufferLib/blob/3.0/pufferlib/models.py)
  — stable model classes; accessed 2026-07-23.
- [PufferLib 4.0 models](https://github.com/PufferAI/PufferLib/blob/25647630e1b15330bb3153a5a0d3ff8d234c3acf/pufferlib/models.py)
  — reviewed 4.0 source model contract; accessed 2026-07-23.
- [PufferLib 4.0 Torch trainer](https://github.com/PufferAI/PufferLib/blob/25647630e1b15330bb3153a5a0d3ff8d234c3acf/pufferlib/torch_pufferl.py)
  — historical fallback and checkpoint loading; accessed 2026-07-23.
- [PyTorch security policy](https://github.com/pytorch/pytorch/security) —
  untrusted-model guidance; accessed 2026-07-23.
- [PyTorch `torch.load` documentation](https://docs.pytorch.org/docs/stable/generated/torch.load.html)
  — deserialization warning; accessed 2026-07-23.
