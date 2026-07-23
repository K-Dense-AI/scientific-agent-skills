# Events, environments, and scheduling

Verified 2026-07-23 against SimPy 4.1.2 documentation and tagged source.

## Scheduler model

`Environment` owns a single event queue and processes one event at a time. Tagged
4.1.2 stores queue entries as `(time, priority, event_id, event)`:

1. smallest simulation time first;
2. smallest numeric priority first (`URGENT=0`, `NORMAL=1` in public event APIs);
3. smallest strictly increasing event ID first.

Thus same-time, same-priority events are FIFO by scheduling order. This is
deterministic sequential execution, even when model processes represent concurrent
activities. Floating-point discretization can collapse physically distinct times
onto the same value, so test tie behavior explicitly.

## Event lifecycle

An `Event` moves once through:

1. **not triggered** — not scheduled and no value;
2. **triggered** — outcome/value fixed and scheduled; `event.triggered` is true;
3. **processed** — removed for callback execution; `event.processed` is true when
   `event.callbacks is None`.

```python
import simpy

env = simpy.Environment()
event = env.event()
assert not event.triggered and not event.processed

event.succeed("ready")
assert event.triggered and not event.processed

env.step()
assert event.processed and event.value == "ready"
```

`event.succeed(value)` and `event.fail(exception)` return that event and may be
called only once. In 4.1.2 `fail()` requires an `Exception`. `event.trigger(other)`
copies the other event's success/failure and value, and returns `None`.

A failed event throws its exception into a waiting process. If no process or
callback defuses it, `Environment.step()` raises it. Treat private `_ok`, `_value`,
and `_defused` as implementation details.

## Callbacks

Before processing, `event.callbacks` is a mutable list of one-argument callables.
Yielding an event adds the waiting process's resume method. Processing executes
callbacks in list order. Once fully processed, callbacks becomes `None`; appending
then is invalid.

```python
log = []
timeout = env.timeout(2, value=7)
timeout.callbacks.append(lambda completed: log.append(completed.value))
env.run()
assert log == [7]
```

Keep callbacks short and non-blocking. A callback runs synchronously inside
`Environment.step()` and can affect scheduler latency.

## Timeout

`env.timeout(delay, value=None)` creates a `Timeout`, immediately triggers it, and
schedules it at `env.now + delay`. Because it is already triggered at construction,
do not call `succeed()` or `fail()` on it.

```python
def timer(env):
    result = yield env.timeout(3, value="elapsed")
    assert result == "elapsed"
```

Reject negative delay. Use a consistent numeric time unit; SimPy does not attach
units or protect against incompatible scales.

## Process

`env.process(generator)` requires a **generator object**, not an ordinary function
result. It schedules an urgent `Initialize` event. Each yielded event suspends the
generator; after the event's outcome, SimPy sends its value back or throws its
failure into the generator.

```python
def child(env):
    yield env.timeout(1)
    return 42

def parent(env):
    child_process = env.process(child(env))
    result = yield child_process
    assert result == 42

env = simpy.Environment()
env.process(parent(env))
env.run()
```

A `Process` is itself an event. It succeeds with the generator's return value or
fails with an uncaught exception. `process.is_alive`, `process.target`, and
`process.name` expose its current status.

Common mistakes:

- `env.process(worker)` instead of `env.process(worker(env))`;
- a function without any reachable `yield`, which is not a generator;
- performing blocking I/O or `time.sleep()` inside a normal Environment process;
- yielding a number rather than an Event.

## Condition events

`AnyOf(env, events)` / `a | b` and `AllOf(env, events)` / `a & b` return a
`Condition`. Yielding one produces a `ConditionValue`, an ordered dict-like mapping
whose keys are the original Event objects and whose values are their values.

```python
def coordinate(env):
    fast = env.timeout(1, value="fast")
    slow = env.timeout(2, value="slow")

    first = yield fast | slow
    assert fast in first
    assert first[fast] == "fast"

    both = yield fast & slow
    assert list(both.items()) == [(fast, "fast"), (slow, "slow")]
```

For `AllOf`, all input events appear. For `AnyOf`, all target events that occurred
before the condition itself is processed can appear; do not assume exactly one
winner when events tie. Input order determines result order.

If any input event fails before the condition succeeds, `AnyOf` and `AllOf` fail.
Conditions can be nested. `AnyOf` does **not** cancel losing events:

```python
with resource.request() as request:
    patience = env.timeout(5)
    result = yield request | patience
    if request not in result:
        # Context-manager exit cancels the still-pending request.
        return
    yield env.timeout(2)
```

An ordinary losing timeout remains scheduled. This is usually harmless but matters
for event counts and traces.

## `Environment.run()` boundaries

### No criterion

`env.run()` stops only when the event queue is empty. An endless generator such as
`while True: yield env.timeout(1)` makes it nonterminating.

### Numeric criterion

`env.run(until=10)` creates an internal urgent stop event at time 10. It advances
`env.now` to 10 but does **not** process ordinary events scheduled exactly at 10:

```python
env = simpy.Environment()
boundary = env.timeout(10)
env.run(until=10)
assert env.now == 10
assert not boundary.processed
```

The numeric target must be strictly greater than `env.now`.

### Event criterion

`env.run(until=event)` attaches a stop callback and returns the event value when
that callback fires. It raises `RuntimeError` if the schedule empties before the
criterion is triggered.

Important 4.1.2 implementation detail: `Environment.step()` catches
`StopSimulation`, preserves callbacks after the stopping callback, and reschedules
the event at priority `-1`. Since `processed` means callbacks is `None`, the target
can still report `processed == False` immediately after `run()` returns:

```python
env = simpy.Environment()
target = env.timeout(5, value="done")
assert env.run(until=target) == "done"
assert target.triggered
assert not target.processed
env.step()
assert target.processed
```

This behavior follows tagged 4.1.2 `simpy/core.py`; the topical guide's informal
"processed" wording is not a safe postcondition. Depend on the returned value and
your model state, not solely on `processed`.

A timeout event and a numeric time can reach the same clock value but differ in
same-time ordering. Numeric stopping is the clearer half-open horizon.

## Manual stepping

```python
until = 10
steps = 0
max_steps = 100_000
while env.peek() < until and steps < max_steps:
    env.step()
    steps += 1
if steps == max_steps:
    raise RuntimeError("event budget reached")
```

`peek()` returns infinity when empty; `step()` raises `simpy.core.EmptySchedule`
when no event remains. Explicit step/event caps prevent a zero-delay loop from
hanging diagnostics.

## Sources

See `sources.md` for versioned environment/event guides, API references, tagged
`core.py`, and the scheduling guide.
