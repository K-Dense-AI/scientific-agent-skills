# Shared resources

Verified 2026-07-23 against SimPy 4.1.2.

All resource operations return Events. An operation that cannot complete waits in
the corresponding queue; yielding the Event suspends the process. Resource events
are context managers so exception/interrupt unwinding can release an acquired
request or cancel a pending operation.

## Choose by modeled quantity

| Primitive | Modeled state | Waiting operation |
|---|---|---|
| `Resource` | limited concurrent users | `request()` |
| `PriorityResource` | users plus priority queue | `request(priority=...)` |
| `PreemptiveResource` | priority users that may be displaced | `request(..., preempt=...)` |
| `Container` | homogeneous numeric level | `put(amount)`, `get(amount)` |
| `Store` | FIFO concrete objects | `put(item)`, `get()` |
| `FilterStore` | objects selected by predicate | `get(filter)` |
| `PriorityStore` | comparable/priority-wrapped objects | `put(item)`, `get()` |

These primitives implement synchronization and congestion. They do not decide
whether a queue discipline or capacity assumption is valid for the real system.

## Resource

`Resource(env, capacity=1)` is semaphore-like. `capacity` must be positive.
Observable state:

- `count`: allocated slots;
- `users`: granted request events;
- `queue`: pending request events;
- `capacity`: maximum simultaneous users.

```python
import simpy

def user(env, resource, duration):
    with resource.request() as request:
        yield request
        yield env.timeout(duration)

env = simpy.Environment()
server = simpy.Resource(env, capacity=2)
for duration in (2, 3, 4):
    env.process(user(env, server, duration))
env.run()
```

The context manager calls `release(request)` after an acquired request and
`cancel()` for an abandoned pending request. With manual management, always release
the exact request token:

```python
request = resource.request()
try:
    yield request
    yield env.timeout(2)
finally:
    if request in resource.users:
        resource.release(request)
    elif not request.triggered:
        request.cancel()
```

`release()` succeeds immediately, even if passed a request that is not a current
user; such a call does not make the model logically correct. Prefer the context
manager.

## PriorityResource

`PriorityResource` orders pending `PriorityRequest`s by smaller numeric priority,
then request time. Equal-priority, equal-time ties use deterministic scheduler/queue
ordering.

```python
def prioritized(env, resource, name, priority):
    with resource.request(priority=priority) as request:
        yield request
        print(name, "started", env.now)
        yield env.timeout(2)

env = simpy.Environment()
resource = simpy.PriorityResource(env, capacity=1)
env.process(prioritized(env, resource, "routine", 10))
env.process(prioritized(env, resource, "urgent", 0))
env.run()
```

Priority does not preempt a current user. A later high-priority request only
overtakes queued lower-priority requests.

## PreemptiveResource

`PreemptiveResource` extends `PriorityResource`. A request accepts:

- `priority`: lower number means higher priority;
- `preempt=True`: permit displacement of a lower-priority current user.

```python
def task(env, resource, name, priority, duration):
    with resource.request(priority=priority, preempt=True) as request:
        try:
            yield request
            started = env.now
            yield env.timeout(duration)
        except simpy.Interrupt as interrupt:
            cause = interrupt.cause
            used = env.now - cause.usage_since
            print(name, "preempted by", cause.by.name, "after", used)

env = simpy.Environment()
cpu = simpy.PreemptiveResource(env, capacity=1)
env.process(task(env, cpu, "background", 5, 10))

def urgent(env):
    yield env.timeout(2)
    yield env.process(task(env, cpu, "urgent", 0, 1))

env.process(urgent(env))
env.run()
```

The preempted process receives `simpy.Interrupt`. Its `cause` is
`simpy.resources.resource.Preempted`:

- `cause.by`: Process that made the preempting request;
- `cause.usage_since`: time the displaced request began using the resource;
- `cause.resource`: resource involved.

The timeout representing interrupted work is not canceled; the process's callback
is removed from it. Track completed work and schedule a new timeout to resume.

Priority outranks the preempt flag. A queued request with higher priority and
`preempt=False` can prevent a lower-priority preempting request from displacing a
user. Do not mix policies without a tested discipline specification.

## Container

`Container(env, capacity=float("inf"), init=0)` models homogeneous matter. Current
state is `level`.

- `put(amount)` waits until `level + amount <= capacity`;
- `get(amount)` waits until `level >= amount`;
- amounts must be strictly positive;
- `0 <= init <= capacity`.

```python
env = simpy.Environment()
tank = simpy.Container(env, capacity=100, init=40)

def transfer(env):
    yield tank.put(30)
    assert tank.level == 70
    yield tank.get(20)
    assert tank.level == 50

env.process(transfer(env))
env.run()
```

Pending operations are visible through `put_queue` and `get_queue`. A blocked put
or get can deadlock the model if no future process can change the level. Bound
execution and assert conservation:

`initial + completed_puts - completed_gets == final_level`.

## Store

`Store(env, capacity=float("inf"))` holds concrete Python objects. `put(item)` waits
when full; `get()` waits when empty. Available objects are in `items`; pending
operations are in `put_queue` and `get_queue`.

```python
env = simpy.Environment()
buffer = simpy.Store(env, capacity=2)

def producer(env):
    for item in ("a", "b", "c"):
        yield buffer.put(item)

def consumer(env):
    for _ in range(3):
        item = yield buffer.get()
        print(item)

env.process(producer(env))
env.process(consumer(env))
env.run()
```

Store is FIFO for available items and ordinary pending requests.

## FilterStore

`FilterStore.get(predicate)` takes the first available item for which the predicate
returns truthy:

```python
env = simpy.Environment()
machines = simpy.FilterStore(env, capacity=2)
machines.items = [
    {"id": "small", "size": 1},
    {"id": "large", "size": 2},
]

def borrow_large(env):
    machine = yield machines.get(lambda item: item["size"] >= 2)
    yield env.timeout(1)
    yield machines.put(machine)

env.process(borrow_large(env))
env.run()
```

Unlike a plain FIFO get queue, a later FilterStore request can complete before an
earlier request when only the later predicate matches. Predicates execute inside
resource processing: keep them deterministic, fast, side-effect-free, and defined
in trusted model code. The bundled JSON CLIs do not accept predicate code.

## PriorityStore

`PriorityStore` returns the smallest item according to comparison. Prefer
`simpy.PriorityItem(priority, item)` so payloads need not be comparable:

```python
env = simpy.Environment()
work = simpy.PriorityStore(env)

def schedule(env):
    yield work.put(simpy.PriorityItem(10, "routine"))
    yield work.put(simpy.PriorityItem(1, "urgent"))
    first = yield work.get()
    assert first.item == "urgent"

env.process(schedule(env))
env.run()
```

Equal-priority payloads preserve the wrapper's comparison behavior; if business
policy requires a specific tie-breaker, include one explicitly in a comparable
dataclass/tuple and test it.

## Waiting, cancellation, and reneging

Use a condition to race a request against patience:

```python
def customer(env, resource, patience):
    with resource.request() as request:
        result = yield request | env.timeout(patience)
        if request not in result:
            return "reneged"  # Pending request canceled on context exit.
        yield env.timeout(2)
        return "served"
```

If retaining resource events outside a context manager:

- re-yield after a temporary interrupt if still waiting;
- call `cancel()` when permanently abandoning a pending put/get/request;
- release only an acquired Resource request;
- account for losing timeouts that remain in the event queue.

## Monitoring caveat

Resource state may change synchronously when an operation is created and again when
its callbacks are processed. Label whether a sample is pre-call, post-call, grant,
release, or final. Time-weight state paths; do not average event samples. See
`monitoring.md`.

## Sources

See `sources.md` for the 4.1.2 shared-resource guide and API reference.
