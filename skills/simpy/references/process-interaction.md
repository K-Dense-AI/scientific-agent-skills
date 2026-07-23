# Process interaction and interrupts

Verified 2026-07-23 against SimPy 4.1.2.

## Processes are event-yielding generators

A process function must return a generator object. `env.process(generator)` starts
it through an urgent `Initialize` event. The generator executes until it yields an
Event, then resumes with that Event's value or exception.

```python
import simpy

def operation(env, duration):
    yield env.timeout(duration)
    return {"finished_at": env.now}

env = simpy.Environment()
process = env.process(operation(env, 3))
result = env.run(until=process)
assert result == {"finished_at": 3}
```

Store a `Process` reference when another process must wait for or interrupt it.
`Process` is itself an Event.

## Waiting for another process

```python
def stage(env, label, duration):
    yield env.timeout(duration)
    return label

def workflow(env):
    first = env.process(stage(env, "first", 2))
    first_result = yield first

    second = env.process(stage(env, "second", 3))
    second_result = yield second
    return first_result, second_result
```

For parallel activities, create all Processes before yielding:

```python
def parallel(env):
    a = env.process(stage(env, "a", 2))
    b = env.process(stage(env, "b", 3))
    results = yield a & b
    assert results[a] == "a"
    assert results[b] == "b"
```

Condition results map Event objects to values. Keep the original Process/Event
references.

## Shared one-shot events

A plain Event can passivate multiple waiters and broadcast one value:

```python
def listener(env, signal, log, name):
    value = yield signal
    log.append((name, env.now, value))

env = simpy.Environment()
signal = env.event()
log = []
env.process(listener(env, signal, log, "a"))
env.process(listener(env, signal, log, "b"))
signal.succeed("go")
env.run()
```

Events are one-shot. For repeated signals, replace the shared Event **after**
triggering it and ensure all participants read the same shared attribute:

```python
class Clock:
    def __init__(self, env):
        self.env = env
        self.tick = env.event()

    def pulse(self):
        current = self.tick
        self.tick = self.env.event()
        current.succeed(self.env.now)
```

Passing separate local event variables to two loops and then "resetting" each local
variable creates disconnected signals. Encapsulate ownership.

## Interrupt delivery

`target_process.interrupt(cause=None)` schedules an urgent `Interruption`. When
processed, it:

1. removes the target process's resume callback from its current target Event;
2. throws `simpy.Interrupt(cause)` into the generator immediately.

```python
def worker(env, log):
    try:
        yield env.timeout(10)
        log.append(("finished", env.now))
    except simpy.Interrupt as interrupt:
        log.append(("interrupted", env.now, interrupt.cause))

def controller(env, target):
    yield env.timeout(3)
    target.interrupt("maintenance")

env = simpy.Environment()
log = []
worker_process = env.process(worker(env, log))
env.process(controller(env, worker_process))
env.run()
assert log == [("interrupted", 3, "maintenance")]
```

Interrupting a terminated process or the currently active process itself raises
`RuntimeError`.

### The target Event is not canceled

An interrupt removes the Process callback from the Event it was yielding; it does
not cancel the Event. The generator can re-yield that same Event:

```python
def temporarily_distracted(env, opening_event):
    while True:
        try:
            return (yield opening_event)
        except simpy.Interrupt:
            yield env.timeout(1)  # Handle interruption.
            # Loop and wait for the original opening_event again.
```

If the original Event occurred during handling, yielding it resumes immediately
with its value.

Resource request events need an additional decision:

- still waiting: re-yield the same request;
- abandoning the wait: call `request.cancel()`;
- already acquired: release it when leaving.

Using the resource request as a context manager handles release/cancel on exception
exit.

## Resumable work

A Timeout cannot be "paused." On interruption, calculate completed work and create
a new Timeout for the remainder:

```python
def resumable_job(env, total_work, log):
    remaining = total_work
    while remaining > 0:
        started = env.now
        try:
            yield env.timeout(remaining)
            remaining = 0
        except simpy.Interrupt as interrupt:
            remaining -= env.now - started
            log.append(
                {
                    "cause": interrupt.cause,
                    "remaining": remaining,
                    "time": env.now,
                }
            )
```

Define whether interrupted setup is lost, retained, or repeated. The code above
assumes linear preempt-resume work.

## PreemptiveResource interrupts

A `PreemptiveResource` generates the interrupt, not application code. The cause is
a `Preempted` record:

```python
def preemptible(env, resource, priority, work):
    with resource.request(priority=priority, preempt=True) as request:
        try:
            yield request
            yield env.timeout(work)
        except simpy.Interrupt as interrupt:
            cause = interrupt.cause
            print(
                "preempted by",
                cause.by,
                "used since",
                cause.usage_since,
                "resource",
                cause.resource,
            )
```

Do not assume every Interrupt has those attributes; manually generated interrupt
causes can be any object. Use `isinstance(cause, simpy.resources.resource.Preempted)`
when the distinction matters.

## Timeout/renege races

```python
def impatient(env, resource, patience):
    with resource.request() as request:
        patience_event = env.timeout(patience)
        result = yield request | patience_event
        if request not in result:
            return {"outcome": "reneged", "time": env.now}
        yield env.timeout(2)
        return {"outcome": "served", "time": env.now}
```

At an exact tie, `AnyOf` may contain multiple events that occurred before the
Condition was processed. Decide tie policy explicitly:

```python
if request in result:
    # This policy treats simultaneous grant/patience as served.
    ...
```

The losing Timeout remains in the queue. The context manager cancels only a pending
request, not arbitrary condition members.

## Failure propagation

An uncaught process exception fails the Process. A parent yielding that Process
receives the exception:

```python
def broken(env):
    yield env.timeout(1)
    raise ValueError("model invariant failed")

def supervisor(env):
    try:
        yield env.process(broken(env))
    except ValueError:
        return "handled"
```

Do not broadly suppress failures merely to keep a simulation running. Convert only
expected domain failures into explicit state; let invariant/programming errors fail
tests.

## Deadlock and liveness checks

`env.run()` returning because the queue is empty does not prove that every intended
process completed. Processes can remain waiting on untriggered events with no future
trigger. Keep references to required completion Processes and run until an explicit
completion Event; if the schedule empties first, SimPy raises `RuntimeError`.

For production models:

- set a numeric horizon and event/entity caps;
- count completed and unfinished entities;
- assert conservation of resources/items;
- detect zero-delay recurrence;
- trace a small deterministic scenario before stochastic experiments.

## Sources

See `sources.md` for the versioned Process Interaction, Events, and resource guides
and API references.
