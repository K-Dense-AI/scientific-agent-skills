# Fluent Python, 2nd Ed. (Luciano Ramalho, 2022)

**Thesis:** Python's special-method protocol (the "Data Model") is a public metaobject API that lets user-defined classes behave indistinguishably from built-ins — mastering it is mastering idiomatic Python.

---

## What this book makes you good at

- Writing classes that feel native: `len(x)`, `for x in obj`, `obj[key]`, `with obj`, `obj + other` all just work.
- Choosing the right built-in collection and knowing when to subclass vs. compose.
- Encoding/decoding Unicode correctly and never hitting platform-dependent bugs.
- Using first-class functions, closures, and decorators fluently.
- Picking the right typing discipline (duck / goose / static / structural) for the situation.
- Building descriptors and properties for reusable attribute validation.
- Selecting threads, processes, or asyncio correctly based on the workload.
- Using generators and `yield from` instead of hand-rolled iterators.
- Avoiding common gotchas: mutable defaults, aliasing bugs, subclassing built-ins, the GIL.

---

## Core principles (actionable)

### 1. Implement dunder methods, never call them directly
The Python interpreter calls special methods; your code should not. Write `len(obj)` not `obj.__len__()`. Write `repr(obj)` not `obj.__repr__()`. The only exception is calling `super().__init__()` inside your own `__init__`. "If you need to invoke a special method, it is usually better to call the related built-in function (e.g., len, iter, str, etc.)." (PAGE 39)

### 2. The Data Model is a framework — implement protocols, not inheritance
Adding `__len__` and `__getitem__` to a class makes it a sequence: it gets slicing, `reversed()`, `random.choice()`, `sorted()` — for free, with no inheritance from any base. "By implementing the special methods `__len__` and `__getitem__`, our FrenchDeck behaves like a standard Python sequence, allowing it to benefit from core language features … and from the standard library … Thanks to composition, the implementations can delegate all the work to a list object." (PAGE 38)

### 3. `__repr__` over `__str__`; make repr eval-able
`__repr__` is for developers (REPL, debugger, logging). `__str__` is for end users and falls back to `__repr__` if missing. "The string returned by `__repr__` should be unambiguous and, if possible, match the source code necessary to re-create the represented object." (PAGE 43) If you implement only one, implement `__repr__`.

### 4. The four typing disciplines are complementary, not competing
From the Typing Map (Ch. 13, PAGE 462):
- **Duck typing** — structural at runtime; no explicit interface declaration needed; most flexible.
- **Goose typing** — `isinstance(obj, ABC)` using `collections.abc`; permits virtual subclasses via `.register()`; runtime-safe.
- **Static typing** — PEP 484 annotations + mypy/pyright; optional and gradual; zero runtime cost; "type hints are always optional." (PAGE 285)
- **Static duck typing** — `typing.Protocol` subclasses; structural + statically checkable; best of duck and static worlds.

Use duck typing by default. Reach for ABCs when you need reliable runtime `isinstance` checks. Use `typing.Protocol` when you want static checking without forcing callers to inherit.

### 5. Gradual typing: annotate incrementally, never seek 100% coverage
"Seeking 100% coverage of type hints is likely to stimulate type-hinting without proper thought, only to satisfy the metric. It will also prevent teams from making the most of the power and flexibility of Python." (PAGE 285) Type hints have no runtime effect — they are checked by external tools only. Leave out hints where they make APIs less user-friendly or unduly complicate implementation.

### 6. Unicode sandwich: decode early, encode late, str in the middle
"The best practice for handling text I/O is the 'Unicode sandwich' (Figure 4-2). This means that bytes should be decoded to str as early as possible on input … The 'filling' of the sandwich is the business logic of your program, where text handling is done exclusively on str objects. You should never be encoding or decoding in the middle of other processing. On output, the str are encoded to bytes as late as possible." (PAGE 131) Always pass `encoding=` explicitly to `open()`: "Code that has to run on multiple machines … should never depend on encoding defaults." (PAGE 132)

### 7. Variables are labels, not boxes — understand aliasing and shallow copy
Python assignment binds a name to an object; it does not copy. `b = a` makes b another label for the same object. Copies are shallow by default (`list[:]`, `copy.copy()`). Use `copy.deepcopy()` for truly independent nested structures. Never use mutable objects as parameter defaults: `def f(data=[])` shares that list across all calls. Use `None` as the sentinel and create fresh inside the function.

### 8. Iterables vs. iterators — never conflate them
An **iterable** has `__iter__` returning a new iterator on every call. An **iterator** has `__next__` and `__iter__` returning `self`. "Iterators are also iterable, but iterables are not iterators." (PAGE 635) Do not implement `__next__` on your collection class — that makes it a one-shot, non-restartable iterator. Use a generator function in `__iter__` instead. "Don't Make the Iterable an Iterator for Itself." (PAGE 605)

### 9. Prefer generator functions over manual iterator classes
A generator function with `yield` replaces a full iterator class. Use `yield from sub_gen()` to delegate to a sub-generator transparently — pauses the outer generator and lets the sub-generator drive directly. Generators are lazy: use a generator expression (parentheses) when building a non-list sequence to avoid materializing the whole list in memory.

### 10. Closures are functions with extended scope — use `nonlocal` for rebinding
A closure retains references to free variables from the enclosing scope even after that scope returns. "A closure is a function that retains the bindings of the free variables that exist when the function is defined, so that they can be used later when the function is invoked and the defining scope is no longer available." (PAGE 345) Use `nonlocal` when the inner function needs to *rebind* (not just mutate) a variable from the enclosing scope.

### 11. Decorators run at import time; use `functools.wraps`
A decorator replaces the decorated function with another callable. When Python *loads the module*, decorators are applied. Use `@functools.wraps(func)` inside every decorator so the wrapper preserves `__name__`, `__doc__`, and other attributes. For class-wide memoization, prefer `@functools.cache` (unbounded) or `@functools.lru_cache` (bounded).

### 12. Operator overloading: return new objects, never mutate; return `NotImplemented` for unsupported types
"Unary and infix operators are supposed to produce results by creating new objects, and should never change their operands." (PAGE 585) For augmented assignment (`+=`), mutable types may update in-place and return `self`. When the types are incompatible, return the sentinel `NotImplemented` (not raise `TypeError`) so Python can try the reflected operator (`__radd__`, etc.). Restrictions: cannot redefine operators on built-ins; cannot create new operators; `is`, `and`, `or`, `not` cannot be overloaded.

### 13. Inheritance rules: favor composition; subclass only designed-for-subclassing classes
Seven rules for coping with inheritance (Ch. 14):
1. **Favor object composition over class inheritance** — delegation avoids fragile base class problems.
2. **Subclass only classes designed for subclassing** — check docs/`@final`.
3. **Avoid subclassing concrete classes** — internal state may be corrupted. "All non-leaf classes should be abstract." (Meyers, quoted PAGE 543)
4. **Make interfaces explicit with ABCs** — if it defines an interface, make it `abc.ABC` or `typing.Protocol`.
5. **Use explicit mixins for code reuse** — name them `*Mixin`; no instance state; no instantiation; single behavior.
6. **Provide aggregate classes** — assemble ABCs + mixins for users in one concrete class.
7. **Do not subclass built-in types** (`list`, `dict`, `str`) — their C-implemented methods bypass Python overrides. Subclass `UserList`, `UserDict`, `UserString` from `collections` instead.

### 14. Descriptors vs. properties: use property for one attribute, descriptor for reuse
A `@property` is the simplest overriding descriptor. Use a descriptor class when you need the same validation/access logic on multiple attributes or classes. Key descriptor tips (PAGE 900):
- `@property` alone creates a read-only attribute without a setter.
- Read-only descriptors require *both* `__get__` and `__set__` (which raises `AttributeError`); otherwise an instance attribute of the same name silently shadows it.
- For caching, a non-overriding descriptor (only `__get__`) that stores the result in the instance `__dict__` under the same name is self-extinguishing after the first call — `@functools.cached_property` does exactly this.
- Validation-only descriptors: implement `__set__` only; store directly in `instance.__dict__`; reading will bypass the descriptor and be fast.

### 15. ABCs: use the library's; create your own rarely
"I would discourage all but the most advanced Pythonistas from going that route [creating custom ABCs]." (Alex Martelli, PAGE 475) Use `collections.abc` ABCs. "Premature abstraction is as bad as premature optimization." (PAGE 735) Existing ABCs support virtual subclasses via `.register()`, so third-party classes can be declared conformant without inheritance.

### 16. Concurrency model selection
- **CPU-bound work**: use `multiprocessing` or `concurrent.futures.ProcessPoolExecutor`. Threads *do not help* for CPU-bound Python code — the GIL prevents true parallel execution.
- **I/O-bound, many connections**: use `asyncio`. "threading is still an appropriate model if you want to run multiple I/O-bound tasks simultaneously" when asyncio overhead is undesired.
- **Blocking calls inside asyncio**: offload via `loop.run_in_executor()` or `asyncio.to_thread()` (Python 3.9+) to avoid starving the event loop.
- The GIL is a CPython implementation detail, not part of the language spec.

### 17. Context managers: use `@contextlib.contextmanager` for simple cases
Write a generator function that `yield`s the value to be bound to `as`, wrapping setup/teardown around the `yield`. Preserves exception propagation correctly. For complex state, implement `__enter__`/`__exit__`. The `with` statement also works with async (`async with` and `__aenter__`/`__aexit__`).

### 18. `else` on loops and `try` blocks
`for … else`: the `else` runs only when the loop completes without a `break`. `try … else`: the `else` runs only when no exception was raised in the `try`. Use these to replace flag variables: `for item in seq: if found: break; else: raise ValueError`.

### 19. Metaclasses: avoid unless building a broad framework
Prefer in order: class decorators > `__init_subclass__` > `__set_name__` > metaclass. "Modern Features Simplify or Replace Metaclasses." (PAGE 947) Metaclasses add complexity and conflict risk; they are justified only for framework authors needing hooks no simpler mechanism provides.

### 20. `@dataclass`, `typing.NamedTuple`, `collections.namedtuple` — choose by need

| Need | Use |
|---|---|
| Immutable record, positional protocol | `typing.NamedTuple` (class syntax, type hints) |
| Simple immutable record, no type hints needed | `collections.namedtuple` |
| Mutable, rich validation, `__post_init__` | `@dataclass` |
| Truly frozen mutable-style class | `@dataclass(frozen=True)` |

A data class that has only fields and no behavior is a code smell ("Data Class as Scaffolding" PAGE 191) — it signals missing logic that belongs in the class. Data classes are fine as intermediate representations (e.g., for serialization).

---

## Chapter map

| Part / Ch | Title | Problem it solves |
|---|---|---|
| I / 1 | The Python Data Model | How dunder methods make objects Pythonic; the full special-method table |
| I / 2 | An Array of Sequences | list, tuple, deque, array — when to use each; slicing, unpacking, listcomps |
| I / 3 | Dictionaries and Sets | dict variants, defaultdict, __missing__, set algebra, hash table consequences |
| I / 4 | Unicode Text vs. Bytes | Unicode sandwich; encodings; NFC normalization; always pass encoding= |
| I / 5 | Data Class Builders | namedtuple, typing.NamedTuple, @dataclass feature comparison |
| I / 6 | Object References, Mutability, Recycling | Variables-as-labels; aliasing; shallow vs. deep copy; mutable defaults |
| II / 7 | Functions as First-Class Objects | Higher-order functions; 9 callable types; functools.partial; operator module |
| II / 8 | Type Hints in Functions | Gradual typing; Any; Optional/Union; TypeVar; Callable; Protocol annotations |
| II / 9 | Decorators and Closures | How decorators work; closures and free variables; nonlocal; functools.cache |
| II / 10 | Design Patterns with First-Class Functions | Strategy, Command patterns simplified with callables |
| III / 11 | A Pythonic Object | __repr__, __hash__, __slots__; classmethod vs staticmethod |
| III / 12 | Special Methods for Sequences | Building a custom sequence; slicing __getitem__; hashing multi-component |
| III / 13 | Interfaces, Protocols, and ABCs | Typing Map; duck/goose/static/structural typing; designing protocols |
| III / 14 | Inheritance: For Better or for Worse | 7 rules; mixins; MRO; subclassing built-ins pitfall |
| III / 15 | More About Type Hints | @overload; TypedDict; variance (covariant/contravariant/invariant); Generic |
| III / 16 | Operator Overloading | Implementing +, *, @, ==; __radd__ fallback; augmented assignment |
| IV / 17 | Iterators, Generators, Classic Coroutines | iter/next protocol; generator functions; yield from; classic send-based coroutines |
| IV / 18 | with, match, and else Blocks | Context managers; @contextmanager; match/case; for/else, try/else |
| IV / 19 | Concurrency Models | GIL; threads vs. processes vs. coroutines; when each applies |
| IV / 20 | Concurrent Executors | ThreadPoolExecutor, ProcessPoolExecutor, futures.as_completed |
| IV / 21 | Asynchronous Programming | asyncio; async/await; async context managers; run_in_executor |
| V / 22 | Dynamic Attributes and Properties | __getattr__; computed properties; @property; property factory; cached_property |
| V / 23 | Attribute Descriptors | __get__/__set__/__delete__; overriding vs non-overriding; descriptor tips |
| V / 24 | Class Metaprogramming | type(); __init_subclass__; class decorators; metaclasses; __prepare__ |

---

## Problem -> where to look

| Problem | Chapter / Section | Approx. Page |
|---|---|---|
| My class should support `len()`, `in`, iteration, slicing | Ch. 1 "Collection API"; Ch. 12 "Special Methods for Sequences" | 14, 397 |
| Which collection type to use (list vs deque vs array vs dict vs set) | Ch. 2 "When a List Is Not the Answer"; Ch. 3 | 59, 77 |
| UnicodeDecodeError / platform-specific text encoding bugs | Ch. 4 "Handling Text Files", "Beware of Encoding Defaults" | 131, 134 |
| Choosing between namedtuple, TypedDict, @dataclass | Ch. 5 "Overview of Data Class Builders" | 164 |
| Mysterious aliasing bug / shared mutable state | Ch. 6 "Variables Are Not Boxes", "Copies Are Shallow by Default" | 202, 208 |
| Writing a reusable decorator with correct metadata propagation | Ch. 9 "Decorators 101", "Implementing a Simple Decorator" | 304, 317 |
| Whether to use an ABC, Protocol, or just duck-type | Ch. 13 "The Typing Map", "Goose Typing", "Static Protocols" | 432, 442, 466 |
| Inheritance hierarchy is becoming fragile / complex | Ch. 14 "Coping with Inheritance" (7 rules) | 510 |
| Need validated/cached attributes without repeating getter/setter | Ch. 22 "Using a Property for Attribute Validation"; Ch. 23 "Descriptor Usage Tips" | 857, 900 |
| CPU-bound vs I/O-bound concurrency — which model to use | Ch. 19 "The Real Impact of the GIL"; Ch. 20; Ch. 21 | 713, 743, 775 |
| Writing a context manager without a full class | Ch. 18 "@contextmanager" | 664 |
| Custom sequence with slicing support | Ch. 12 "A Slice-Aware __getitem__" | 406 |
| Operator overloading with type-safe fallback | Ch. 16 "Overloading + for Vector Addition", "Wrapping-Up Arithmetic Operators" | 566, 576 |
| Making classes support pattern matching (`match`/`case`) | Ch. 5 "Pattern Matching Class Instances"; Ch. 11 "Supporting Positional Pattern Matching" | 192, 377 |
| Metaclass vs class decorator vs `__init_subclass__` | Ch. 24 "Modern Features Simplify or Replace Metaclasses" | 947 |
| Generator vs list comprehension for memory efficiency | Ch. 2 "Generator Expressions" | 29 |
| Classic coroutine (send-based) vs async/await | Ch. 17 "Classic Coroutines"; Ch. 21 | 641, 775 |
| Type variance (covariant vs contravariant containers) | Ch. 15 "Variance" | 544 |

---

## Convergences & debates

### Agrees with A Philosophy of Software Design (Ousterhout / APOSD)
- **Deep interfaces, not shallow ones**: Fluent Python's protocols encode the same insight — a class implementing `__len__` and `__getitem__` exposes enormous capability through a tiny interface. Both books push against unnecessary API surface area.
- **Comments and clarity**: Fluent Python uses docstrings and does not treat them as failures (unlike Clean Code's "comments are apologies" stance).
- **Composition over inheritance**: Both APOSD and Ch. 14 recommend favoring composition; APOSD's "deep modules" prefer stable, simple interfaces — mixins and protocol conformance fit this model.

### Diverges from / adds to Clean Code (Martin)
- **Many small classes vs. data model**: Clean Code advocates small, single-responsibility classes. Fluent Python shows that Python's Data Model often lets one well-designed class do what Clean Code would split into many: a class with `__iter__` + `__len__` + `__getitem__` is still SRP — it just expresses a richer protocol.
- **Comments**: Clean Code treats most comments as failures; Fluent Python treats docstrings as essential API documentation and the `__doc__` protocol as a first-class feature.

### Diverges from Code Complete (McConnell)
- Code Complete was written in a pre-protocol, pre-functional era. Its guidance on inheritance hierarchies and defensive copying maps poorly to Python's duck typing and aliasing semantics. Fluent Python's "variables are labels" model fundamentally changes mutation analysis.

### Diverges from Clean Architecture (Martin)
- SOLID's interface segregation principle aligns with protocols; however, Clean Architecture's many-small-classes philosophy conflicts with Fluent Python's view that composition and delegation (not fragmented classes) produces the cleanest Python. Python's data model often achieves what SOLID tries to achieve through structural subtyping without explicit interfaces.

### Agrees with The Pragmatic Programmer (Hunt & Thomas)
- **Don't repeat yourself**: Descriptors and property factories (Ch. 22-23) eliminate DRY violations in attribute validation — the Pragmatic book advocates the same via code generation or metaprogramming.
- **Orthogonality**: Mixing classes via mixins follows the orthogonality principle — each mixin adds one independent behavior.

### Agrees with Software Engineering at Google (Winters et al.)
- **Gradual typing**: Both books advocate incremental adoption of type annotations, not all-or-nothing. SWE at Google discusses the same tradeoff of annotation coverage vs. annotation quality.
- **Testing over type checking**: Fluent Python's Ch. 8 states "Imperfect Typing and Strong Testing" — type hints are a complement, not a substitute for tests; SWE at Google makes the same argument.

### Unique to this book (not well-covered elsewhere in the set)
- The complete dunder/special-method table and which built-in each maps to.
- The Typing Map quadrant (duck / goose / static / static-duck) as a decision framework.
- Descriptor protocol internals (overriding vs. non-overriding; shadowing rules).
- Generator protocol and `yield from` delegation.
- The Unicode sandwich as an explicit architectural pattern for I/O.
- GIL consequences and the CPU-bound vs. I/O-bound concurrency decision tree.
- Metaclass progression: class decorator > `__init_subclass__` > metaclass.
