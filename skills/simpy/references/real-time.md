# Real-time simulation

Verified 2026-07-23 against SimPy 4.1.2.

`simpy.rt.RealtimeEnvironment` retains the Event/Process API but delays event
processing so simulation time tracks wall-clock time.

```python
from simpy.rt import RealtimeEnvironment

env = RealtimeEnvironment(
    initial_time=0,
    factor=0.1,
    strict=True,
)
```

## Parameters

- `initial_time`: starting simulation clock.
- `factor`: wall-clock seconds per simulation time unit; must be positive.
  - `1.0`: one simulation unit takes one second;
  - `0.1`: one simulation unit takes 0.1 seconds;
  - `60.0`: one simulation unit takes one minute.
- `strict=True`: raise `RuntimeError` when processing falls more than the allotted
  factor behind.

`strict=False` suppresses deadline failure. It permits drift; it does not make an
overloaded simulation accurately synchronized.

## Minimal bounded example

```python
import time
from simpy.rt import RealtimeEnvironment

def ticker(env, count):
    for index in range(count):
        before = time.monotonic()
        yield env.timeout(1)
        elapsed = time.monotonic() - before
        print(index, env.now, elapsed)

env = RealtimeEnvironment(factor=0.05, strict=True)
process = env.process(ticker(env, count=3))
env.run(until=process)
```

Use `time.monotonic()` for elapsed wall time. Calendar time can jump.

## Strict-mode behavior

Callbacks and generator code execute synchronously on the simulation thread. Slow
computation, blocking I/O, logging, garbage collection, OS scheduling, and loaded
CI hosts all consume the real-time budget.

```python
import time
import simpy.rt

def slow(env):
    time.sleep(0.02)
    yield env.timeout(1)

env = simpy.rt.RealtimeEnvironment(factor=0.01, strict=True)
env.process(slow(env))
try:
    env.run()
except RuntimeError:
    print("simulation missed its real-time budget")
```

This `sleep()` intentionally demonstrates a missed deadline. Do not put blocking
sleep in ordinary SimPy process logic to represent simulated delay; use
`env.timeout()`.

## Appropriate use

Real-time execution is useful when wall-clock synchronization is intrinsic:

- hardware- or software-in-the-loop tests;
- human-paced demonstrations;
- interactive controllers;
- adapters to an external system with explicit timing contracts.

It is usually inappropriate for Monte Carlo replications: normal `Environment`
runs faster, is less affected by host load, and preserves the same model-time
logic.

## External I/O boundary

SimPy itself is single-threaded and does not make external I/O asynchronous.
Integrating devices or services requires an explicit adapter and failure model.
Document:

- blocking/nonblocking behavior;
- timeout and retry policy;
- conversion between wall and simulation timestamps;
- thread-safety and event handoff;
- late/out-of-order data behavior;
- shutdown and exception propagation.

The bundled skill CLIs intentionally provide no device, network, plugin, or
external-service integration.

## Drift measurement

Choose a real origin and compare expected elapsed wall time with actual monotonic
elapsed time:

```python
import time

origin_real = time.monotonic()
origin_sim = env.now

def drift_seconds(env, factor):
    expected = (env.now - origin_sim) * factor
    actual = time.monotonic() - origin_real
    return actual - expected
```

Define sign, sampling instant, percentile, maximum allowed lag, and platform before
testing. A mean near zero can hide large deadline misses.

## Testing strategy

1. Test model logic with normal `Environment`.
2. Test deterministic ordering and interrupts independently of wall time.
3. Keep real-time tests short and separately marked.
4. Use `time.monotonic()` and broad platform-aware bounds.
5. Test both `strict=True` deadline detection and intentional `strict=False` lag.
6. Avoid exact-duration assertions.
7. Record Python/SimPy version, OS, architecture, host load assumptions, and factor.

Example tolerant assertion:

```python
start = time.monotonic()
env = RealtimeEnvironment(factor=0.02, strict=False)
env.run(until=env.timeout(2))
elapsed = time.monotonic() - start
assert elapsed >= 0.02
assert elapsed < 1.0
```

The upper bound is deliberately generous; tune it for controlled hardware, not a
busy shared runner.

## Boundaries and stopping

Real-time environments inherit `Environment.run()` semantics:

- no `until` can run forever;
- numeric `until` excludes normal events at the boundary;
- Event `until` returns the Event value;
- `peek()`/`step()` remain available.

Always bound real-time runs. A tiny factor combined with a huge event count can
still consume substantial CPU, and a huge factor can make a short model wait for a
long wall duration.

## Limitations

- Wall-clock results are not bit-for-bit timing reproducible across hosts.
- Python/OS timer granularity and scheduling affect jitter.
- One slow callback delays all later events.
- Real-time synchronization does not make simulated processes parallel.
- `strict=False` can accumulate unbounded lag.
- Real-time agreement is not model validation.

## Sources

See `sources.md` for the 4.1.2 real-time topical guide and `simpy.rt` API.
