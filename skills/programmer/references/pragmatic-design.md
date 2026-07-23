# The Pragmatic Programmer — Design Mechanics

Andrew Hunt & David Thomas, *The Pragmatic Programmer* (Addison-Wesley, 1999). The tactical **design principles** — each a way to keep one change from rippling into many. The professional/process side lives in `pragmatic-craft.md`; the full 70-tip extraction is in `pragmatic-tips-catalog.md`.

The core bet: **software changes constantly, so design so that change is cheap and stays local.** "There Are No Final Decisions" — decisions are "written in the sand, not carved in stone." Held together by two framing disciplines: **Don't Live With Broken Windows** (Tip 4 — fix bad design the moment you see it, or board it up) and **Don't Program by Coincidence** (Tip 44 — rely only on documented, understood behavior; if you can't tell whether behavior is guaranteed, assume the worst).

## The design principles

### 1. DRY — Don't Repeat Yourself (Tips 11, 12)
**Every piece of knowledge has a single, unambiguous, authoritative representation.** Duplicated knowledge *will* diverge — "it isn't a question of whether you'll remember; it's a question of when you'll forget." Four kinds: **imposed** (generate copies from one source), **inadvertent** (don't store what you can derive), **impatient** (copy-paste), **inter-developer** (communicate). Make reuse *easier than rewriting* (Tip 12). Comments explain **why**, not how — restating code is duplication.

### 2. Orthogonality (Tip 13)
**A change to one thing should affect exactly one module.** Test: "If I dramatically change the requirements behind one function, how many modules are affected?" Answer should be **one**. Avoid global/shared mutable state, don't write similar functions (extract / Strategy), and treat a unit test that drags in half the system as a coupling alarm.

### 3. Minimize coupling — write shy code (Tip 36, Law of Demeter)
**Don't talk to strangers.** A method should call only methods of: itself, its parameters, objects it created, and its direct components. `customer.getAccount().getRegion().getTaxRate()` is a *train wreck* — every hop is a hidden dependency. Fix by asking for what you need: add `customer.taxRate()`.

### 4. Configure, don't integrate — details in metadata (Tips 37, 38)
**Program for the general case; push specifics outside the compiled code.** Frequently-changing details — region→format maps, business rules, thresholds, the DB vendor, deployment topology — belong in metadata/config, not `if/elif` ladders. Defer details to the last moment and keep them soft.

```python
# before: details welded into code, silent failure on a new region
if region.name == "EU":   fmt = "eu_invoice_v3"
elif region.name == "US": fmt = "us_invoice_v2"
# after: detail lives in data; unknowns fail loudly
REGION_FORMAT = {"EU": "eu_invoice_v3", "US": "us_invoice_v2"}
fmt = REGION_FORMAT[region.name]   # KeyError crashes early instead of corrupting output
```

### 5. Separate views from models (Tip 42)
**A model must not know about its views.** Use events / publish-subscribe / MVC so many views observe one model and "the sender of the event doesn't need any explicit knowledge of the receiver." The antipattern is one giant `case` that knows every object's interactions.

### 6. Don't couple in time (Tips 39–41)
**Hidden assumptions about *order* and *simultaneity* are coupling too.** A class that requires `connect()`/`init()` before any other call has a fragile, undocumented ordering contract. Prefer objects valid the moment they exist (inject dependencies in the constructor). Design for concurrency up front.

### 7. Design by Contract (Tip 31)
**State each routine's preconditions, postconditions, and invariants.** Be *strict in what you accept, promise as little as possible in return.* A violated contract is a **bug**, not a runtime condition to handle — and not the place to validate user input. Where the language lacks support, write them as assertions and comments.

### 8. Crash early; assert the impossible (Tips 32, 33)
**A dead program does far less damage than a crippled one.** When something "can't happen" happens, fail fast at the source with a stack trace instead of limping on with corrupt state. Guard the impossible with assertions, add a `default` to every switch, and **leave assertions on in production**. (Never put side effects inside an assertion.)

### 9. Use exceptions for exceptional problems only (Tip 34)
**An exception is a cascading `goto`; normal flow shouldn't depend on it.** Test: "Would this code still run correctly if I removed all the exception handlers?" Opening a file that *should* exist → exception on failure; opening a user-supplied name that *might* not exist → return an error value.

### 10. Finish what you start — balance resources (Tip 35)
**Whoever allocates a resource deallocates it.** Keep `open`/`close`, `acquire`/`release` visibly paired in the *same* scope (`with`/`finally`/RAII). Deallocate in reverse order of allocation; allocate in a consistent order to avoid deadlock.

### 11. Refactor early, refactor often (Tip 47)
**Code is a garden, not a building.** Treat code needing refactoring as a *tumor* — cut it out while small and cheap. Triggers: duplication, non-orthogonal design, drifted requirements, performance. Rules: don't add features while refactoring; have tests first; take small steps.

### 12. Design to test (Tips 48, 49)
**Testability is a design property — build it in.** Write the contract and its test *as you design* the module (untestable code is usually over-coupled code). Keep tests close to the code. *Test Your Software, or Your Users Will.*

### 13. Build deliberately and incrementally (Tips 15, 16, 17)
- **Tracer Bullets (15):** when the target is uncertain, build a *thin but complete* path through every layer first, with real error-handling. Kept, not thrown away — the skeleton you flesh out.
- **Prototype to Learn (16):** disposable experiments targeting *one* risk; "its value lies not in the code produced, but in the lessons learned." Thrown away. Don't confuse the two.
- **Program Close to the Problem Domain (17):** raise the abstraction level with notation in the vocabulary of the domain.

## Quick reference: smell → principle

| Smell | Principle (Tip) |
|---|---|
| Same knowledge/logic in two places | DRY (11) |
| One requirement change touches many modules | Orthogonality (13) |
| `a.getB().getC().getD()` chains | Law of Demeter / shy code (36) |
| `if region == "EU"…`, magic constants, vendor names in code | Configure / metadata (37/38) |
| Model reaches into UI; giant dispatch `case` | Separate views from models (42) |
| Must call `init()`/`connect()` before use | Temporal coupling (39–41) |
| Function trusts inputs it never states | Design by Contract (31) |
| `// this can't happen`; errors swallowed; limps on bad state | Crash early + assertions (32/33) |
| Exceptions used for normal/expected outcomes | Exceptions only for exceptional (34) |
| Resource opened here, closed "elsewhere" / leaked | Finish what you start (35) |
| Duplicated, tangled, "afraid to touch" code | Refactor early (47) |
| Can't unit-test without the whole system | Design to test (48/49) |
| "It works but I'm not sure why" | Don't program by coincidence (44) |

## Common mistakes
- **Spotting the smell but not naming the principle.** Say *which* coupling (Demeter? temporal? global state?) and apply that specific fix.
- **Treating DRY as "don't type the same characters twice."** It's *one representation of each piece of knowledge*. Two functions that look alike but encode different decisions are fine.
- **Using Design by Contract to validate user input.** Preconditions catch *programmer* errors (bugs), not bad data.
- **Disabling assertions in production.** Keep them on.
- **Keeping prototype code.** Throw it away; the lesson was the deliverable.
- **Over-applying.** Externalize the details that *change*; relax coupling where change actually ripples. "Circles and arrows make poor masters."
