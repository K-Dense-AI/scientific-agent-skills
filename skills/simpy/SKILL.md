---
name: simpy
description: Build, inspect, test, and analyze bounded process-based discrete-event simulations with SimPy, including events, resources, interrupts, monitoring, replications, warm-up, and reproducible output analysis.
license: MIT
compatibility: Upstream SimPy 4.1.2 supports Python 3.8+; bundled CLIs require Python 3.10+, uv, and SimPy 4.1.2. They use only SimPy and the standard library, operate on local bounded inputs, and make no network calls.
allowed-tools: Read, Write, Edit, Bash, Glob
metadata:
  version: "1.1"
  skill-author: K-Dense Inc.
---

# SimPy

## Scope

Use this skill for process-based discrete-event models where active entities yield
events and contend for resources: queues, production systems, logistics, networks,
service operations, inventory, and other event-driven systems.

SimPy supplies an event scheduler and modeling primitives. It does **not** choose a
scientifically valid conceptual model, input distribution, warm-up, run length,
replication count, estimand, or causal interpretation. Treat those as simulation-study
methodology, not SimPy API behavior.

## Current release and installation

Verified **2026-07-23**:

- Latest stable: **SimPy 4.1.2**, released on PyPI 2026-05-24; source tag
  `4.1.2` points to commit `f4381649`.
- Package metadata requires Python **>=3.8** and classifies CPython 3.8-3.14
  plus PyPy. SimPy has no runtime dependencies.
- 4.1.2 adds Python 3.13/3.14 support and modern-interpreter test fixes.
- Upstream and this skill are MIT-licensed.

Create a reproducible environment:

```bash
uv venv --python 3.13
source .venv/bin/activate
uv pip install "simpy==4.1.2"
python -c "import importlib.metadata; print(importlib.metadata.version('simpy'))"
```

Do not silently substitute the `latest` documentation build: it may describe an
unreleased development revision. Use the versioned 4.1.2 links in
`references/sources.md`.

## Model workflow

1. **Define purpose and estimands.** State the decision/question, system boundary,
   entities, resources, state, outputs, time units, and terminating event or
   steady-state target.
2. **Write a conceptual model first.** Record assumptions, distributions,
   routing, priorities, initial conditions, and omitted mechanisms.
3. **Implement generators.** A SimPy process is an event-yielding Python generator.
   Register the generator object with `env.process(...)`.
4. **Bound execution.** Give every production run explicit time, entity, event, and
   replication caps. Never call `env.run()` on a model containing an endless process.
5. **Separate random streams.** Use local RNG instances for logically distinct
   stochastic sources; retain a seed manifest.
6. **Instrument deliberately.** Observe state after the transition of interest,
   close time-weighted intervals at the horizon, and test that monitoring does not
   alter event order.
7. **Verify and validate.** Test deterministic edge cases, conservation identities,
   traces, queue discipline, and analytical benchmarks; compare against system or
   expert evidence for the stated purpose.
8. **Run independent replications.** Make intervals from replication-level
   estimates, not correlated entities within one run.
9. **Report limitations.** Include initialization, unfinished entities, run length,
   seeds/streams, precision, sensitivity, and validation evidence. Never convert
   simulation association into a causal claim.

Read `references/simulation-methodology.md` before making inferential claims.

## Minimal bounded model

```python
import random
import simpy

HORIZON = 480.0
arrival_rng = random.Random(101)
service_rng = random.Random(202)
env = simpy.Environment()
server = simpy.Resource(env, capacity=2)
completed = []

def customer(arrival):
    with server.request() as request:
        yield request
        wait = env.now - arrival
        yield env.timeout(service_rng.expovariate(1 / 6.0))
    completed.append((env.now, wait))

def arrivals():
    for _ in range(10_000):  # Entity cap.
        delay = arrival_rng.expovariate(1 / 4.0)
        if env.now + delay >= HORIZON:
            return
        yield env.timeout(delay)
        env.process(customer(env.now))

env.process(arrivals())
env.run(until=HORIZON)
```

The numeric horizon is half-open: normal events scheduled exactly at `480.0` are
not processed. Report unfinished entities rather than silently treating them as
completed observations.

## Core semantics

### Environment and deterministic ordering

`Environment` is single-threaded. The queue is ordered by simulation time, event
priority, then a strictly increasing event ID. Same-time, same-priority events are
therefore processed FIFO in scheduling order. Model processes may represent
concurrency, but callbacks execute sequentially and deterministically.

- `env.now`: unitless simulation clock; choose and document one unit.
- `env.peek()`: next event time or infinity.
- `env.step()`: process one event; raises `EmptySchedule` when empty.
- `env.active_process`: currently executing process, otherwise `None`.
- `env.run()`: drain the queue; unsafe with recurring or endless processes.

`env.run(until=number)` and `env.run(until=event)` are not interchangeable at
boundaries:

- A numeric value schedules an urgent stop event and excludes ordinary events at
  that exact time.
- An Event criterion returns that event's value when its stop callback fires.
  Other same-time ordering depends on priority and scheduling order.
- In 4.1.2, `Environment.step()` preserves callbacks remaining after
  `StopSimulation` by rescheduling the target. Consequently, after
  `env.run(until=target)`, `target.processed` can remain `False` until one more
  `step()`/`run()` even though its value was returned. Do not use `processed` as the
  sole post-run completion test.

See `references/events.md` and `references/monitoring.md`.

### Event, Timeout, Process, and Condition

- An `Event` moves once through not-triggered -> triggered/scheduled -> processed.
  `succeed(value)` or `fail(exception)` triggers it once.
- A `Timeout` triggers when created, is scheduled for `now + delay`, and cannot be
  manually succeeded again.
- `env.process(generator)` creates a `Process`; the generator resumes with the
  yielded event value. Returning from the generator succeeds the Process with that
  return value. Uncaught exceptions fail it.
- `AnyOf` / `a | b` and `AllOf` / `a & b` yield a `ConditionValue`: an ordered,
  dict-like mapping from **event objects** to their values. Test membership using
  the original event objects; do not assume a scalar result.
- `AnyOf` does not cancel losing events. Explicitly cancel pending resource
  requests when abandoning them; ordinary timeouts remain scheduled.

### Interrupts

`process.interrupt(cause)` schedules an urgent interruption that throws
`simpy.Interrupt` into the target generator. Catch it around the yielded work that
may be interrupted, inspect `interrupt.cause`, update remaining work, then either
resume, re-yield the original event, or terminate.

Interrupting a process removes its resume callback from its current target; it does
not cancel that target event. A process cannot interrupt itself or a terminated
process. See `references/process-interaction.md`.

## Shared resources

| Type | Semantics |
|---|---|
| `Resource` | FIFO semaphore-like usage slots |
| `PriorityResource` | Queued requests sorted by lower numeric priority first |
| `PreemptiveResource` | Priority queue plus optional preemption of a current user |
| `Container` | Homogeneous numeric level; `put`/`get` wait for capacity/material |
| `Store` | FIFO Python objects |
| `FilterStore` | First available item satisfying the request's predicate |
| `PriorityStore` | Comparable items returned in priority order |

Use a request context manager:

```python
def job(env, resource):
    with resource.request() as request:
        yield request
        yield env.timeout(3)
```

On exit it releases an acquired request or cancels a still-pending one, including
during exception unwinding. For a manually retained pending `put`/`get`/request,
call `cancel()` if an interrupt or timeout makes the process abandon it.

`PreemptiveResource.request(priority=..., preempt=True)` uses lower numbers as
higher priority. The preempted process receives an `Interrupt` whose cause is a
`Preempted` object: `cause.by` is the preempting Process,
`cause.usage_since` is when use began, and `cause.resource` is the resource.
Queued priority takes precedence over the `preempt` flag; mixing preempting and
non-preempting requests needs explicit tests.

Read `references/resources.md` for blocked operations, queue rules, and examples.

## Monitoring and stepping

Prefer explicit domain observations at state transitions. For generic resource
monitoring, wrappers or subclasses can inspect `count`, `queue`, `level`, `items`,
`put_queue`, and `get_queue`. For event tracing, `schedule()` and `step()` are the
central hooks.

Queue measurements are timing-sensitive:

- A request method's pre-state, post-call state, grant callback, and release
  callback can all differ at the same simulation timestamp.
- Sample averages weight event observations, not time. Compute area under the
  left-continuous state path and divide by elapsed time.
- Add initial and final samples; close the last interval at the analysis horizon.
- `env._queue`, resource `_env`, and monkey-patching are implementation details.
  Pin SimPy, isolate the instrumentation, and regression-test after upgrades.
- Tracing every event changes runtime and memory use; cap trace records.

Use `scripts/resource_monitor.py` and `references/monitoring.md`.

## Real-time execution

`simpy.rt.RealtimeEnvironment(initial_time=0, factor=1.0, strict=True)` maps one
simulation unit to `factor` wall-clock seconds. In strict mode, `step()`/`run()`
raises `RuntimeError` when computation falls behind. `strict=False` tolerates lag;
it does not restore timing accuracy. Develop logic with `Environment`, then run
separate timing tests with generous platform-aware tolerances. See
`references/real-time.md`.

## Bundled safe CLIs

All CLIs use a fixed built-in queue model or summarize local artifacts. They reject
unknown JSON keys, URLs, symlinks, non-finite numbers, oversized inputs, and
unbounded time/events/entities/replications. They never evaluate config text,
execute user Python, import plugins, or call a network service.

```bash
# Inspect all options.
python skills/simpy/scripts/bounded_queue_scenario.py --help
python skills/simpy/scripts/replication_runner.py --help
python skills/simpy/scripts/event_trace_summary.py --help
python skills/simpy/scripts/validate_simulation_config.py --help

# Deterministic built-in scenario.
python skills/simpy/scripts/bounded_queue_scenario.py

# Independent replications with replication-level Student-t intervals.
python skills/simpy/scripts/replication_runner.py

# Validate only; no simulation runs.
python skills/simpy/scripts/validate_simulation_config.py config.json
```

The replication runner refuses one-replication intervals. Its intervals quantify
Monte Carlo uncertainty under the configured model; they neither validate the model
nor identify causal effects. See `references/cli-guide.md`.

## Testing

Use deterministic unit tests for ordering, boundary times, conditions, interrupts,
all resource disciplines, conservation, event/entity limits, seed reproducibility,
and monitor non-interference. Add stochastic tests only as broad distributional
checks with fixed seeds; avoid brittle exact sample estimates.

Run the bundled suite in the exact pinned environment without bytecode artifacts:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --isolated --no-project \
  --python 3.13 --with "simpy==4.1.2" \
  python -m unittest discover -s skills/simpy/tests -v
```

## References

- `references/events.md` — scheduler, lifecycle, run boundaries, conditions
- `references/process-interaction.md` — generators, shared events, interrupts
- `references/resources.md` — all Resource, Container, and Store variants
- `references/monitoring.md` — time weighting, queue timing, tracing, stepping
- `references/real-time.md` — factor, strict mode, drift, timing tests
- `references/simulation-methodology.md` — replications, warm-up, validation, CI
- `references/cli-guide.md` — schemas, bounds, outputs, and safe CLI examples
- `references/sources.md` — dated official and primary-method sources
