# Monitoring, tracing, and stepping

Verified 2026-07-23 against SimPy 4.1.2.

Monitoring is model instrumentation, not an automatic statistical analysis. Define:

1. the estimand/state (queue waiting only, users in service, total in system);
2. the observation instant (before request, after request, grant, release, final);
3. the aggregation rule (time average, entity average, count, quantile);
4. the analysis window and warm-up;
5. memory/trace caps.

## Prefer explicit domain observations

Record domain events where their meaning is unambiguous:

```python
def customer(env, resource, log):
    arrival = env.now
    log.append({"event": "arrival", "time": env.now})
    with resource.request() as request:
        yield request
        log.append(
            {
                "event": "service_start",
                "queue_wait": env.now - arrival,
                "time": env.now,
            }
        )
        yield env.timeout(2)
    log.append({"event": "departure", "time": env.now})
```

Entity-average wait and time-average queue length are different estimands.

## Why queue samples are timing-sensitive

For `Resource.request()`:

- before the method: the new request is absent;
- immediately after: an available slot may already be allocated, or the request is
  in `queue`;
- when the request Event is processed: waiting Process callbacks run;
- during release: a queued request may be granted synchronously before the release
  Event's callbacks finish.

Several states may therefore exist at the same simulation timestamp. Label sample
phase. Equal-time samples contribute zero duration to a time integral but affect an
unweighted sample average.

`len(resource.queue)` counts pending requests, not users in service. Total number in
the congestion point is normally `resource.count + len(resource.queue)`.

For Container/Store, distinguish `level`/`len(items)` from pending
`put_queue`/`get_queue`.

## Time-weighted state

For a left-continuous piecewise-constant state `q(t)`, compute:

`average = sum(q_i * (t_{i+1} - t_i)) / (end - start)`.

Requirements:

- initial sample at monitoring start;
- every relevant state transition;
- final sample exactly at the reporting horizon;
- warm-up window clipping;
- nondecreasing timestamps.

Do not use `sum(queue_samples) / len(queue_samples)` as time-average queue length;
busy periods typically generate more events and become overrepresented.

## Bundled ResourceMonitor

`scripts/resource_monitor.py` wraps one Resource-like instance, records request,
grant, cancellation, release, and final states, and calculates time-weighted
utilization/queue length.

```python
import simpy
from resource_monitor import ResourceMonitor

env = simpy.Environment()
resource = simpy.Resource(env, capacity=2)
monitor = ResourceMonitor(env, resource, "server")

# Register bounded processes, then run.
env.run(until=100)
monitor.finalize(at=100)
summary = monitor.summary(start=20, end=100)
```

The warm-up sample state is reconstructed from the last transition at or before
`start`; the final sample closes the interval. `export_csv()` writes local private
CSV atomically and refuses overwrite unless requested.

Monkey-patching changes method identity and can interact with other wrappers. Attach
one monitor per instance, patch before processes obtain method references, and call
`detach()` before another instrumentation layer.

## Generic resource wrappers

The official guide demonstrates pre/post method wrappers:

```python
from functools import wraps

def patch_resource(resource, pre=None, post=None):
    def wrap(operation):
        @wraps(operation)
        def wrapper(*args, **kwargs):
            if pre is not None:
                pre(resource)
            event = operation(*args, **kwargs)
            if post is not None:
                post(resource)
            return event
        return wrapper

    for name in ("put", "get", "request", "release"):
        if hasattr(resource, name):
            setattr(resource, name, wrap(getattr(resource, name)))
```

Here "post" means after the method call, not necessarily after the returned Event
is processed. To observe completion, append a callback while `event.callbacks` is
still a list. Handle immediately triggered events before the environment steps.

Subclassing can be clearer for one stable use case, but it still depends on
protected `_env` in common examples. Prefer an explicit `env` reference.

## Event tracing

The official guide identifies:

- `Environment.schedule()` — event enters the queue;
- `Environment.step()` — next queued event is processed.

The bundled `EventTraceRecorder` wraps `step()`, reads the next queue tuple, and
records only:

- simulation time;
- priority;
- event ID;
- event class name;
- queue size before the step.

It avoids `repr(event)`, which can contain nondeterministic memory addresses. It
caps records and writes JSON Lines.

```python
from resource_monitor import EventTraceRecorder

trace = EventTraceRecorder(env, max_records=10_000)
env.run(until=100)
trace.detach()
trace.export_jsonl("trace.jsonl")
```

This intentionally accesses `env._queue`, a private implementation detail. Pin
SimPy and regression-test the tuple shape after upgrades. Full tracing increases
runtime and memory; use a small deterministic diagnostic scenario.

Summarize without executing model code:

```bash
python skills/simpy/scripts/event_trace_summary.py trace.jsonl
python skills/simpy/scripts/event_trace_summary.py resource_samples.csv
```

The summarizer validates fixed schemas, file size, record count, numeric finiteness,
and ordering.

## Manual stepping

Stepping is useful for debuggers, GUI integration, invariants, and hard event caps:

```python
from simpy.core import EmptySchedule

max_events = 100_000
processed = 0
while env.peek() < 100 and processed < max_events:
    env.step()
    processed += 1

if processed == max_events:
    raise RuntimeError("event budget exhausted")
if env.peek() == float("inf"):
    # Empty schedule; verify intended completion instead of assuming success.
    pass
```

`env.peek() < horizon` gives the same half-open boundary policy as numeric
`run(until=horizon)`. `<=` processes events at the boundary and is a different
estimand/termination convention.

If a stop callback fires during `step()` in 4.1.2, SimPy may reschedule the Event to
preserve remaining callbacks. See `events.md`.

## Periodic polling

Polling is simple but approximates the state path and adds events:

```python
def poll(env, resource, interval, end, samples):
    while env.now < end:
        samples.append((env.now, resource.count, len(resource.queue)))
        delay = min(interval, end - env.now)
        if delay <= 0:
            return
        yield env.timeout(delay)
```

Never use a zero/negative interval. Polling can miss short peaks. It is suitable
for visualization at a declared resolution, not exact time integrals.

## Measurement windows and censoring

At a finite horizon:

- an entity may arrive but remain queued;
- service may start but not finish;
- a future timeout may remain scheduled;
- numeric `run(until=horizon)` excludes ordinary events exactly at the horizon.

Report arrived, admitted, rejected, completed, and unfinished counts. A
completed-only customer mean can be biased when long waits/services are more likely
to be unfinished. Consider a terminating design that drains the system, a
right-censoring-aware estimand, or sensitivity to a longer horizon.

For steady-state replication/deletion, define whether an observation enters the
analysis by arrival time, service-start time, departure time, or time-integral
window. Do not choose after seeing favorable results.

## Monitor non-interference tests

For a deterministic miniature model, compare monitored and unmonitored runs:

- same completion order and timestamps;
- same resource counts and outputs;
- same random draws/seed manifest;
- no pending monitor bookkeeping after completion;
- identical exception/interrupt behavior.

Also test:

- simultaneous request/release;
- cancellation while queued;
- preemption;
- zero queue capacity;
- final interval closure;
- warm-up starting between transitions;
- trace-cap behavior.

## Sources

See `sources.md` for the official monitoring, environment, time/scheduling, and
tagged core source links.
