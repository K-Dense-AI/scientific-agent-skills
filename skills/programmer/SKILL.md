---
name: programmer
description: >-
  Use when any agent is designing, building, reviewing, refactoring, debugging,
  or explaining software and needs senior-engineer judgment across naming,
  functions, comments, error handling, complexity management, module depth, OO
  design, SOLID, architecture boundaries, data systems, concurrency, testing,
  code review, engineering trade-offs over time, and idiomatic Python. Includes
  an agent-neutral delegation protocol for optional read-only research, code
  scanning, mechanical verification, and bridge/consult tools.
metadata:
  version: "1.0"
  skill-author: Chenwei-1999
---

# Programmer

## Overview

Eight books on what it takes to be a good programmer, distilled into one skill. They share a single claim, seen from different angles:

> **Software is read and changed far more than it is written. The job is to manage complexity so the system stays understandable and changeable over its whole life — and to make sound trade-offs when "best practice" runs out.**

The eight, by the angle they attack:
- **Structure / complexity:** *A Philosophy of Software Design* (Ousterhout) `[APOSD]`, *Clean Code* (Martin) `[CC]`, *Code Complete* (McConnell) `[CodeC]`.
- **Architecture:** *Clean Architecture* (Martin) `[CArch]`.
- **Systems at scale:** *Designing Data-Intensive Applications* (Kleppmann) `[DDIA]`.
- **Over time & teams:** *Software Engineering at Google* (Winters et al.) `[SWE@G]`.
- **Practice / craft:** *The Pragmatic Programmer* (Hunt & Thomas) `[PP]`.
- **Language:** *Fluent Python* (Ramalho) `[FP]`.

Each rule below is tagged with the book(s) that back it. Where several books independently agree, that convergence is the strongest signal to trust; where they **disagree**, the skill takes a reconciled stance (see *Debates*).

## When to Use This Skill

Use this skill when:
- Designing or changing long-lived code, public APIs, libraries, services, shared modules, or team-owned systems.
- Reviewing, refactoring, debugging, or explaining software where maintainability and future change matter.
- Making trade-offs across naming, routine structure, module boundaries, architecture, data systems, concurrency, testing, or Python idioms.
- Choosing whether to use a helper agent for read-only research, code scanning, mechanical verification, or external review.

Use a lighter tactical approach for run-once scripts, spikes, notebooks, prototypes, and disposable migrations. In those cases, make it work simply and stop; no speculative abstractions, contracts, distributed systems, or test machinery for code that will be deleted. The real trap is the throwaway that quietly becomes load-bearing: graduate it to this skill once it outlives its one shot.

Calibrate effort to `expected lifespan × number of future readers`:
- **High**: apply this skill fully.
- **Near zero**: go tactical and keep data on a single node until scale or availability genuinely forces distribution.

## Core Capabilities

1. **Complexity and module design**: detect change amplification, cognitive load, unknown unknowns, shallow modules, and information leakage.
2. **Code construction**: improve naming, functions, comments, object/data boundaries, error handling, refactoring, and debugging.
3. **Architecture**: apply SOLID, dependency direction, boundaries, partial boundaries, and framework/database separation without dogma.
4. **Data systems**: reason about storage engines, replication lag, isolation anomalies, distributed failure modes, and schema evolution.
5. **Concurrency and Python**: choose processes, threads, async, Python protocols, dataclasses, typing strategies, and resource patterns.
6. **Engineering over time**: test behavior, review for comprehension, handle Hyrum's Law, deprecate carefully, and account for team scale.
7. **Deep reference lookup**: route high-stakes or unfamiliar questions to `references/<book>.md`, then use `scripts/read_book.py` against `assets/<book>.pdf` when a primary-source lookup is needed.

## Using This Skill

This skill is **two tiers** and is meant to be portable across Codex, Claude Code, Gemini CLI, OpenHands, and any other agent runner (see `references/agent-adapters.md` for per-runtime model/agent names and skill-install paths):

- **Tier 1 — embedded competence (this document).** Parts 1–8 below distill enough actionable judgment to handle ordinary work directly: naming, functions, error handling, module & abstraction design, OO/data structures, architecture/SOLID/boundaries, systems-at-scale decisions, concurrency, testing, engineering-over-time, craft, and Python idioms. **Read these and act — you don't need to open a book for routine work.** For each smell, *name the principle, state the why, apply the fix* — naming turns "this feels off" into a defensible change.
- **Tier 2 — self-directed deep reference.** When a problem is high-stakes, unfamiliar, or needs mechanics deliberately left out of Tier 1, **decide** you need the source, then consult the specific bundled catalog/book section yourself or delegate that read-only lookup to a cheap helper if the runner provides one. See *Deep reference (Tier 2)* at the end.

### General Workflow Guidelines

Use this section to adapt the skill to the runner you are in. The programming principles are stable; the dispatch mechanism is an implementation detail.

- **Main agent owns judgment.** Keep task framing, risky decisions, implementation ownership, and final synthesis in the main thread. Helpers gather evidence; they do not decide architecture, edit policy, or final user-facing conclusions.
- **Delegate only independent work.** Use helpers for parallel documentation lookup, read-only code scanning, call-path tracing, log/evidence gathering, mechanical verification, or independent review. Do not delegate one-tool-call tasks, urgent blocking decisions, final synthesis, or work that depends on private conversation context the helper will not see.
- **Announce dispatches when chat-visible.** Before starting a helper, emit exactly: `→ dispatching <agent_name> (<model>): <one-line task>`. Use the runner's actual agent/model names. If the runner has no subagents, skip the announcement and do the lookup locally.
- **Route by capability and cost.** Send docs/API/book lookup to the cheapest reliable research helper; send code discovery to the cheapest reliable code-scout helper; reserve expensive or high-reasoning models for ambiguous architecture, subtle debugging, risky edits, and final integration.
- **Keep helpers read-only by default.** Give them raw artifacts, paths, symptoms, or logs; ask for concrete evidence and file/heading references. Avoid giving them your intended answer unless the task is explicitly review/adversarial.
- **Integrate and close.** Read the helper output, verify key claims when cheap, incorporate only the useful evidence, and stop using that helper thread.

**Common adapter names** (model IDs current as of 2026-05 — see `references/agent-adapters.md` for discovery paths, the shared `.agents/skills/` location, frontmatter rules, rules-based runtimes, and source links)

| Runner | main-synthesizer | code-scout (read-only) | docs-scout (research) |
|---|---|---|---|
| Codex | `gpt-5.5` | `gpt-5.3-codex-spark` † | `gpt-5.4-mini` |
| Claude Code | `claude-opus-4-8` (`opus`) | built-in `Explore` agent (Haiku) | custom agent · `claude-haiku-4-5` |
| Gemini CLI | Pro tier | Flash (auto `activate_skill`) | Flash-Lite |
| OpenHands | configured strong model | fast model via `SKILL.md` | configured cheap model |
| Generic / rules-based | strongest configured model | cheapest read-only code worker | cheapest read-only docs worker |

† `gpt-5.3-codex-spark` is OpenAI's near-instant, text-only model — fastest for read-only scanning, but it **requires ChatGPT Pro** (research preview). Without Pro, use `gpt-5.4-mini`, OpenAI's documented subagent model. For Gemini, use the current Pro/Flash/Flash-Lite IDs from `ai.google.dev`. Rules-based runtimes (Cursor, Aider, Continue, Windsurf) are model-agnostic: load this skill via their rules/modes and route the scout role to your configured fast model. For review/consult, use the runner's native review agents or an external consult/review bridge when configured.

**Bridge/consult tools.** If the runner exposes an external consult/review bridge, use it only when it has clear value: hard architecture trade-offs, unclear root-cause debugging after local evidence gathering, or independent review before a PR/merge. Batch context into one self-contained prompt. Do not use bridge tools for boilerplate, obvious API naming, or anything requiring hidden conversation context.

**OpenAI/Codex/API questions.** When the task touches OpenAI API, ChatGPT Apps SDK, Codex, Agents SDK, or MCP behavior and source accuracy matters, use the official OpenAI developer documentation source available in the runner, then cite official documentation links in the answer.

Detailed per-book catalogs live in `references/`: `references/aposd-complexity.md`, `references/clean-code.md`, `references/code-complete.md`, `references/clean-architecture.md`, `references/ddia.md`, `references/fluent-python.md`, `references/swe-at-google-principles.md`, `references/pragmatic-design.md`, `references/pragmatic-craft.md`, `references/pragmatic-tips-catalog.md`. Raw book PDFs are not shipped; when you need one, find and fetch a copy of the edition listed in *Additional Resources* with your runner's web-search/fetch tools, save it to `assets/<slug>.pdf`, then use `scripts/read_book.py` to list, read, or search those PDFs instead of hand-rolling PDF extraction.

---

## Part 1 — Manage complexity (the structural spine)

**Complexity is the enemy** `[APOSD]` — anything about a system's structure that makes it hard to understand or modify. It accumulates one small chunk at a time. Detect it by three symptoms: **change amplification** (a simple change requires edits in many places), **cognitive load** (you must hold too much in your head), **unknown unknowns** (it's not even clear what to change — the worst). Its two causes: **dependencies** and **obscurity**. Nearly everything below reduces one or both. The **Primary Technical Imperative is managing complexity** `[CodeC]`.

- **Tactical vs. strategic** `[APOSD]`. Tactical = make *this* work fast, accreting complexity. Strategic = working code is necessary but not sufficient; invest ~10–20% up front in design. The biggest difference between engineers is this mindset, not raw skill.
- **Deep modules** `[APOSD] [CodeC]`. "The best modules are deep: a lot of functionality through a simple interface." A shallow module (interface ≈ implementation in complexity) buys nothing. Hide secrets: ask of every module, *what should I hide?* `[CodeC]`
- **Information hiding, not leakage** `[APOSD]`. The same design decision living in two modules is *leakage* — a dependency. "Determining who needs to know what, and when" is the core of design.
- **Somewhat general-purpose** `[APOSD]`. Functionality for today's needs; interface general enough for several uses. The word *somewhat* matters — don't build speculative generality.
- **Design it twice** `[APOSD]`. Sketch two or three genuinely different designs and compare; even excellent engineers don't get the best one first.
- **Comments capture what code can't** `[APOSD]`. Write the *why* and the abstraction; a comment that restates the *how* is noise. (Contested — see Debate 1.)
- **Obviousness is the goal.** Good design is what the next reader finds *obvious* — they guess what it does and how to change it on the first try.

## Part 2 — Writing the code well (construction)

- **Naming** `[CC] [CodeC]`. Intention-revealing; name length ∝ scope (short-lived loop index `i` is fine; a field needs a full name). Booleans read as predicates (`is_/has_/can_/should_`). No noise words (`data`, `info`, `theManager`), one word per concept (don't mix `fetch/get/retrieve`). A name you can't choose signals a muddled abstraction.
- **Functions / routines** `[CC] [CodeC]`. One level of abstraction per function; it should do **one thing**. Decompose for **depth and one-abstraction, not a line count** (Debate 1). Few arguments (≤~3); **no flag/boolean arguments** — split into two functions. **Command–Query Separation**: a function either does something or answers something, never both. No hidden side effects.
- **Objects vs. data structures** `[CC]`. Objects hide data and expose behavior; data structures expose data and have no behavior. Don't build hybrids (a half-object that exposes its guts *and* has methods). **Law of Demeter** — "don't talk to strangers"; `a.getB().getC().doThing()` train wrecks are hidden dependencies. Tell, don't ask.
- **Error handling & defensive programming** `[CodeC] [CC] [PP]` (Debate 3 reconciled):
  - **Assertions** guard conditions that *should never happen* (internal invariants, bugs) — they may abort. **Error handling** copes with conditions that *can happen* (bad input, missing file) — it stays in production.
  - **Barricade**: validate untrusted/external input at the boundary; inside the barricade, trust the data and assert invariants.
  - Prefer **exceptions over return codes**; **don't return or pass `null`** (return empty/Special-Case objects). Use exceptions only for the *exceptional* — normal flow shouldn't depend on them.
  - **Crash early** on "impossible" states — a dead program does far less damage than a crippled one. Never put side effects inside an assertion.
- **Refactoring** `[CodeC] [PP]`. Refactor in small, individually-tested steps; one change at a time; never add features while refactoring. Triggers: duplication, a smell, drifted requirements. Treat code needing refactoring as a tumor — excise it while small.
- **Debugging** `[CodeC] [PP]`. Use the **scientific method**: stabilize/reproduce → form a hypothesis → binary-search to localize → fix the **root cause** (not the symptom) → add a regression test. Never change code at random ("voodoo"). "Fix the problem, not the blame"; "`select` isn't broken" — suspect your own code first.

## Part 3 — Design at the system level (architecture)

- **SOLID** `[CArch]`, each made actionable:
  - **SRP** — a module should be responsible to **one actor** (one reason to change). Not "does one thing" — *answers to one stakeholder*. Two actors sharing a class is the accidental-duplication smell.
  - **OCP** — open for extension, closed for modification; add behavior via new code, not by editing tested code.
  - **LSP** — subtypes must be substitutable for their base; a subtype that breaks the base's contract isn't one.
  - **ISP** — don't force clients to depend on methods they don't use; split fat interfaces.
  - **DIP** — depend on abstractions; source-code dependencies point *against* the flow of control; gather concretions in `main()`.
- **The Dependency Rule** `[CArch]`. Source-code dependencies point **inward** toward policy: entities → use cases → interface adapters → frameworks/drivers. **"The database is a detail. The web is a detail. The framework is a detail."** Business rules must be unit-testable with no server, DB, or UI present (Humble Object: push untestable bits to a thin edge). *But calibrate (Debate 6 / "When this applies"):* don't reflexively wrap a framework in a full repository/ports layer — often the lighter fix is to extract the pure **decision logic over plain data** (dataclasses, not ORM rows) and keep a thin adapter at the edge.
- **Boundaries & components** `[CArch]`. Split by the **real axis of change that will occur**, not by ideology (Debate 2). Break dependency cycles with DIP or a new component (Acyclic Dependencies). Default hedge against premature separation: a **partial boundary** (an interface at the seam, single deployable) — cheap now, separable later (Debate 6). **Services are not architecture** — decomposing into microservices doesn't draw architectural boundaries (the "Kitty Problem": a cross-cutting change still touches every service).

## Part 4 — Systems at scale (data-intensive) `[DDIA]`

Tier-1 embeds the **decisions**; the mechanics (full isolation tables, 2PL vs SSI, 2PC recovery, consensus) are Tier-2 (`references/ddia.md`).

- **Three independent axes**: **Reliability** (works correctly under faults), **Scalability** (load parameters + measure **percentiles, not averages** — tail latency is what users feel), **Maintainability**.
- **Storage engine**: **LSM-tree → write-heavy** (high write throughput, compaction); **B-tree → read-heavy, range scans, strong single-key transactions**. Don't run analytics (OLAP) on your transactional store — use a **column store** for scans over many rows/few columns.
- **Replication lag** gives three anomalies, each app-fixable: **read-your-writes** (see your own writes), **monotonic reads** (don't see time go backward), **consistent-prefix** (causally-ordered writes seen in order).
- **Transactions / isolation**: pick the level by *which anomaly it must prevent*. **Snapshot isolation does NOT stop write skew or phantoms.** To fix a write-skew/phantom — e.g. two concurrent "is this room free?" checks that both then `INSERT` a booking — use **serializable (SSI)**, or **materialize the conflict with a UNIQUE / exclusion constraint**, or **lock an existing proxy row** (e.g. the room row) with `SELECT … FOR UPDATE`. Note: plain `SELECT … FOR UPDATE` over the *result set* does **not** stop an *insert*-phantom — there is no row yet to lock. "Read committed" doesn't stop lost updates.
- **Distributed reality**: partial failure is the baseline; the network is unreliable; **clocks are unreliable — never order events by wall-clock time**; use **fencing tokens** to stop a paused node corrupting state. **2PC is a blocking protocol.** **Linearizability is expensive** — often **causal consistency** suffices.
- **Schema evolution**: design for **backward *and* forward compatibility** (old and new code coexist during rolling deploys). **Never use language-native serialization (pickle, Java Serializable) for durable or cross-service data** — use Avro/Protobuf/Thrift with explicit schema evolution.

## Part 5 — Concurrency (three contexts)

- **Python (process/async)** `[FP]`: **CPU-bound → processes** (`ProcessPoolExecutor`/`multiprocessing`) — the **GIL** prevents threads from parallelizing *pure-Python* CPU work. (Caveat: C extensions such as NumPy/Pillow/OpenCV release the GIL during native compute, so threads *can* parallelize that — reach for processes when the hot loop is pure Python.) **I/O-bound, many connections → `asyncio`**; offload a blocking call from the event loop with `asyncio.to_thread`. **I/O-bound, modest → threads** are fine.
- **Thread-level safety** `[CC]`: limit shared mutable state to the absolute minimum; keep critical sections small; apply SRP to threads (a class does one concurrency-related thing).
- **Distributed coordination** → Part 4 / `[DDIA]`.
- **Temporal coupling** `[PP]`: don't require `init()`/`connect()` before use; inject dependencies in the constructor so an object is valid the moment it exists.

## Part 6 — Idiomatic Python `[FP]`

Tier-1 decisions; descriptor/metaclass/`yield from` internals are Tier-2 (`references/fluent-python.md`).

- **Use the data model**: implement dunder methods (`__len__`, `__getitem__`, `__repr__`, …) and let built-ins (`len`, `[]`, slicing, `for`, `in`, `sorted`, `random.choice`) work on your objects. Implement dunders; don't call them. `__repr__` over `__str__` for debugging.
- **Variables are labels, not boxes** (aliasing is real); **never use a mutable default argument** (`def f(x, items=[])` is a bug — use `None` sentinel).
- **Pick the container**: `@dataclass` (mutable, validation, defaults) vs `NamedTuple`/`namedtuple` (immutable record). A fields-only data class is fine as scaffolding but watch for behavior that belongs with the data `[CC]`.
- **Typing Map**: duck-type by default; an **ABC** when you need runtime `isinstance`; **`typing.Protocol`** for static structural typing without forcing inheritance. Gradual typing — don't chase 100% coverage.
- **Favor composition over inheritance**; don't subclass built-in `dict`/`list` (use `UserDict`/`UserList`); generators over hand-rolled iterators; `@contextmanager` for simple resources.
- **Unicode sandwich**: decode bytes→str at input, work in `str`, encode str→bytes at output; **always pass `encoding=` to `open()`** (platform defaults bite).

## Part 7 — Engineer for time, scale, and teams `[SWE@G]`

> **"Software engineering is programming integrated over time."** The dimensions are **time, scale, and trade-offs**. "It's programming if 'clever' is a compliment; it's software engineering if 'clever' is an accusation."

- **Sustainability** — "capable of reacting to whatever valuable change comes along" over the software's life. It's about *capability*, not churning change. Ask "is this maintainable?" not just "does it work?"
- **Hyrum's Law** — "With a sufficient number of users of an API, … all observable behaviors of your system will be depended on by somebody." Your real contract is everything observable — hide what you don't want depended on.
- **It depends / trade-offs** — no context-free best practices, only better/worse trade-offs. Every decision is "we must" or "best option on current evidence," never "because I said so." Cost is multidimensional (**personnel time usually dominates**).
- **Shift left** — "the earlier we find a problem, the cheaper it is to fix it."
- **Testing** — test **behaviors, not methods** (given/when/then); smallest test that works; test through **public APIs**, state over interaction; **DAMP over DRY in tests**; the **Beyoncé Rule**: "If you liked it, then you shoulda put a test on it" (in CI).
- **Code review is about comprehension, not bugs** — "code itself is a liability"; the value is understandability + knowledge transfer; one LGTM; defer to the author's approach.
- **Teams** — "Genius is a myth"; build on **Humility, Respect, Trust**; protect psychological safety; track bus factor; nothing lasts forever (deprecate; trunk-based change).

## Part 8 — Professional craft `[PP]`

- **Take responsibility** — "provide options, don't make lame excuses." **Don't live with broken windows** — fix bad design the moment you see it, or board it up; rot is cultural.
- **Good-enough software** — quality is a *requirements* issue; involve the user; "know when to stop." (Never sloppy.)
- **Invest in your knowledge portfolio** — learn continuously, diversify; "critically analyze what you read" — don't fall for hype or dogma.
- **Communicate** — know your audience (WISDOM); "it's both what you say and the way you say it."
- **Automate everything repeatable** — "people just aren't as repeatable as computers."

---

## Examples (each carries several books at once)

**1 — Demeter train wreck *and* shallow interface** `[PP] [CC] [APOSD]`:
```python
# BEFORE — caller knows the whole object graph; every hop is a hidden dependency
fmt = order.get_customer().get_region().get_settings().invoice_format

# AFTER — tell, don't ask; the traversal hides behind a one-call deep interface
fmt = order.invoice_format()     # Order delegates internally
```
Name it (Demeter/coupling `[PP]`), say the why (a change to the graph ripples to every caller), and note the deepening: the new method hides the traversal behind a simple interface `[APOSD]`.

**2 — Shallow getter ceremony → a deep Pythonic protocol** `[FP] [APOSD] [CC]`:
```python
# BEFORE — manual getters, not iterable, not Pythonic (shallow ceremony)
class Deck:
    def __init__(self): self._cards = build()
    def get_card(self, i): return self._cards[i]
    def count(self):       return len(self._cards)

# AFTER — implement two dunders; get a huge amount of behavior for free
class Deck:
    def __init__(self): self._cards = build()
    def __len__(self):        return len(self._cards)
    def __getitem__(self, i): return self._cards[i]
# now free: len(deck), deck[0], deck[:3], for c in deck, reversed(deck),
#           random.choice(deck), sorted(deck)  — the canonical deep module
```
Two dunders yield slicing/iteration/`reversed`/`random.choice` `[FP]` — a tiny interface with rich functionality (deep module `[APOSD]`), and the right answer to "objects expose behavior" `[CC]` without Java getter ceremony.

## Best Practices: where the books converge

| One idea, many authors | Backed by |
|---|---|
| **Software lives a long time; optimize for change & reading** | APOSD (strategic) · SWE@G (over time) · PP (no final decisions) · CArch (keep options open) |
| **Manage complexity / hide information behind deep abstractions** | APOSD (deep modules) · CodeC (hide secrets) · CC (small classes, SRP) · DDIA ("SQL hides the B-tree") · FP (protocols) |
| **Keep one change from rippling** | APOSD (info hiding) · PP (DRY, Demeter, orthogonality) · CArch (boundaries, DIP) · CC (Demeter) |
| **No dogma — it's a trade-off** | SWE@G ("it depends") · APOSD ("decide what matters") · PP ("critically analyze") · DDIA (every choice is a trade-off) |
| **Test the behavior, ruthlessly & automatically** | SWE@G (behaviors, Beyoncé) · CC (F.I.R.S.T.) · CodeC (developer testing) · PP (find bugs once) |
| **Fail loudly & early on programmer errors** | PP (crash early, DbC) · CodeC (assertions/barricades) · CC (exceptions, no null) |
| **Software is a human/team activity** | SWE@G (genius is a myth, HRT) · PP (communicate, sign your work) · APOSD (obvious to the next reader) |

When several independent authors reach the same conclusion, treat it as load-bearing, not stylistic.

## Debates — where the books disagree, and the skill's stance

These are genuinely contested. Know the stance *and* that it's contested — reason, don't parrot.

1. **Function size & "comments are failures."** Martin `[CC]`: "should be small… smaller than that," "comments are always failures." Ousterhout `[APOSD]`: "depth is more important than length," comments "serve a fundamental role." McConnell `[CodeC]`: length should follow cohesion, not a line count. **Stance:** decompose for **depth and one level of abstraction**, never to hit a line count; if a split forces the reader to hold two functions in their head at once, you went too far. Comments are not failures — write the *why* and the abstraction; delete comments that restate the *how*.
2. **Many small classes / SOLID vs. deep modules.** `[CArch]` SRP/ISP/DIP push to split; `[APOSD]` warns the splits go shallow ("classitis"). **Stance:** split by the **axis of change that will actually occur** (distinct actors, swappable persistence); keep a cohesive deep module whole when the boundary will never be crossed. Tie-break (APOSD): "best information hiding, fewest dependencies, deepest interfaces."
3. **How much defensive programming.** `[CodeC]` separates assertions (internal, may compile out) from error handling (external, stays); `[PP]` says crash early and leave assertions on in production. **Stance:** validate untrusted **external** input with error-handling at the barricade; **assert internal invariants**. Keep assertions on for internal services/tools (fast crash > silent corruption); allow graceful degradation where availability is the requirement.
4. **DRY everywhere vs. DAMP / replication.** **Stance:** DRY = one representation of each piece of *knowledge*, not "no two similar lines"; two snippets encoding *different decisions* aren't duplication. **In tests, prefer DAMP** (clear inline setup). **In distributed data, replication is not a DRY violation** — it's a chosen reliability trade-off `[DDIA]`. Apply rule-of-three before extracting.
5. **Inheritance/patterns vs. composition/protocols.** `[CC][CArch]` classic OO & GoF; `[FP]` "favor composition," "don't subclass built-ins," many patterns collapse to a first-class function. **Stance:** prefer **composition and duck/`Protocol` typing**; reach for an interface only for a real runtime/contract need; don't import Java ceremony into Python; `@dataclass`/`property` express encapsulation without getter rituals.
6. **Premature abstraction vs. draw-boundaries-early.** **Stance:** defer *concrete technology* choices (which DB/framework) and keep business rules from importing them — these are compatible. Use a **partial boundary** as the default hedge; generalize the *interface* "somewhat," not the *implementation*.
7. **Strict clean layering vs. physical reality in data systems.** **Stance:** apply the Dependency Rule to **business logic**; don't impose it dogmatically on the **storage layer**, where I/O, network, and clock constraints legitimately dictate structure `[DDIA]`.

## Quick reference: situation → principle → source

| Situation | Principle | Source |
|---|---|---|
| Interface nearly as complex as the implementation | Shallow module — make it deeper | APOSD |
| Function long / does several things | Decompose for depth & one abstraction (not line count) | CC · CodeC · APOSD |
| Boolean/flag argument in a call | Split into two functions | CC |
| Method returns / accepts `null` | Don't return/pass null; Special-Case object | CC |
| `a.getB().getC().doX()` chains | Law of Demeter / tell-don't-ask | CC · PP |
| Validate input vs. guard a bug | Error-handling at barricade; assert invariants | CodeC · PP |
| Class pulled by two stakeholders | SRP = one actor | CArch |
| Business logic imports the DB/framework | Dependency Rule — "DB is a detail" | CArch |
| Microservices still ripple on one change | Services aren't architecture (Kitty Problem) | CArch |
| Write-heavy vs. read/range workload | LSM-tree vs. B-tree | DDIA |
| Anomaly under concurrent writes | Choose isolation by anomaly; SI ≠ write-skew-safe | DDIA |
| Stale/jumping reads behind a replica | Replication-lag anomalies (read-your-writes…) | DDIA |
| Ordering events across machines | Never trust wall-clocks; fencing tokens | DDIA |
| CPU-bound parallelism in Python | Processes, not threads (GIL) | FP |
| Many concurrent I/O connections | asyncio; `to_thread` for blocking calls | FP |
| Mutable default argument | Use a `None` sentinel | FP |
| Subclassing `dict`/`list` | Use `UserDict`/`UserList` | FP |
| "It works but I can't explain why" | Don't program by coincidence | PP |
| Changing undocumented behavior broke a caller | Hyrum's Law | SWE@G |
| Test breaks on every refactor | Behaviors via public APIs; state over interaction | SWE@G |
| Bug hunt turning into blame/guessing | Fix problem not blame; scientific-method debugging | PP · CodeC |

---

## Deep reference (Tier 2): decide, then use a cheap read-only lookup

The rules above embed enough judgment for ordinary work. For a **high-stakes, unfamiliar, or beyond-the-distillation** problem, don't guess and don't burn main-agent tokens reading a whole book. **Decide whether you need the source, read the relevant `references/<book>.md` catalog first, then use `scripts/read_book.py` to search the corresponding PDF in `assets/` or dispatch a cheap read-only helper to do the same.**

### Self-assessment: is embedded knowledge enough?
Act from Tier-1 (no lookup) when **all** hold: the decision is reversible / low-blast-radius; an embedded rule or quick-reference row directly names the principle and fix; and you can state the *why* in one sentence without hedging.

**Dispatch to Tier 2** when **any** hold: high stakes or hard to reverse (storage-engine choice, isolation level for money, a public API contract, a cross-team boundary, a service's concurrency model); you have the *decision* but need the *mechanics* left out of Tier 1 (exact anomalies per isolation level, 2PC recovery, descriptor/`yield from` internals, the full smell catalog, component-stability metrics); the problem is outside these topics; two embedded rules conflict and you can't break the tie; or you're about to cite a quote/page in a deliverable and must verify it.

### The router — which book, which chapter
| Problem area | PRIMARY → catalog · chapter (page) | SECONDARY |
|---|---|---|
| Naming | `clean-code` · Ch 2 Meaningful Names (17–30); N-heuristics (309–313) | `code-complete` · Ch 11 Variable Names (259) |
| Functions / routines | `clean-code` · Ch 3 Functions (34–46) | `code-complete` · Ch 7 (cohesion 168, params 174) |
| Comments & docs | `aposd-complexity` · Ch 12 (why-not-how, write-first) | `code-complete` · Ch 32; `swe-at-google-principles` (docs-as-code) |
| Error handling / defensive | `code-complete` · Ch 8 (assertions 189, barricades 203, correctness-vs-robustness 197) | `clean-code` · Ch 7; `pragmatic-design` Tips 31–34 |
| Module / abstraction / info hiding | `aposd-complexity` · Ch 6 (deep modules, leakage) | `code-complete` · §5.3 Hide Secrets (90) |
| OO design & data structures | `clean-code` · Ch 6 (objects vs data, Demeter 95–98) | `code-complete` Ch 6; `fluent-python` Ch 11–12 |
| SOLID & dependencies | `clean-architecture` · Ch 7–11 SRP/OCP/LSP/ISP/DIP (79–107) | `clean-code` · Ch 10 |
| Architecture & boundaries | `clean-architecture` · Ch 17 Boundaries (174); Ch 22 Dependency Rule (205); Ch 30–32 "X is a detail" | `clean-architecture` · Ch 13–14 (REP/CCP/CRP, ADP/SDP/SAP) |
| Data modeling & storage engines | `ddia` · Ch 3 (LSM vs B-tree 74–82; column stores 93–100) | `ddia` · Ch 2 (relational/document/graph) |
| Replication, partitioning, consistency | `ddia` · Ch 5 (lag 155–161), Ch 6 (hot spots 195–197) | `ddia` · Ch 9 (linearizability vs causal 314–355) |
| Distributed failure modes | `ddia` · Ch 8 (networks/clocks/pauses, fencing 265–302) | `ddia` · Ch 9 (CAP, 2PC, consensus) |
| Transactions & isolation | `ddia` · Ch 7 (isolation table, write skew, 2PL/SSI 224–257) | — |
| Concurrency & async | *Python:* `fluent-python` Ch 19–21 (GIL, CPU→proc/IO→async 713–775) · *threads:* `clean-code` Ch 13 · *distributed:* `ddia` Ch 8–9 | `pragmatic-design` (temporal coupling, Tips 39–41) |
| Performance & tuning | `code-complete` · Ch 25 (measure first, 588) | `ddia` · Ch 1 (percentiles/tail latency 35) |
| Testing strategy | `swe-at-google-principles` (behaviors, sizes, DAMP, Beyoncé) | `clean-code` Ch 9 (F.I.R.S.T.); `pragmatic-craft` Tips 49,62–66 |
| Refactoring | `code-complete` · Ch 24 (smells + refactorings 565–571) | `clean-code` Ch 14–17; `pragmatic-design` Tip 47 |
| Debugging | `code-complete` · Ch 23 (scientific method 540) | `pragmatic-craft` (Tips 24–27) |
| Over time / scale / deprecation | `swe-at-google-principles` (time/scale/trade-offs, Hyrum, deprecation) | `clean-architecture` Ch 15; `pragmatic-design` |
| Team, review & craft | `swe-at-google-principles` (review, HRT, psych safety) | `pragmatic-craft` (responsibility, WISDOM, estimating) |
| Python idioms | `fluent-python` · Ch 1 Data Model; Ch 5 data classes; Ch 13 Typing Map; Ch 14 inheritance; Ch 17–18 generators/context mgrs | `fluent-python` Ch 22–23 (properties/descriptors); Ch 4 (Unicode) |

### Lookup recipe
1. **Index first (cheap, local).** Open the relevant per-book catalog in `references/`; use its **Chapter map** and **Problem -> where to look** table to find the exact section *heading text*.
2. **Get the source text, then use the reader script.** PDFs are not shipped. If `assets/<slug>.pdf` is missing, **find and fetch it yourself**: use your runner's web-search/fetch tools to locate an available copy of the edition pinned in *Additional Resources* (prefer a legitimate source; for APOSD use the author's free Stanford extract), and save it to `assets/<slug>.pdf`. Then run `python scripts/read_book.py --list` to see available PDF slugs, and search a source PDF with `python scripts/read_book.py <slug> --query "<heading or term>" --context 8`. The script extracts text from `assets/<slug>.pdf` using `pdftotext`, `pypdf`, `PyPDF2`, or its built-in PDF-stream fallback when those tools are unavailable.
3. **Choose the lookup path.** If no helper is available, read the targeted catalog/book section locally. If helpers are available, dispatch a read-only docs/research helper for book/API/documentation questions or a code-scan helper when the answer is in source code. Announce it with the runner's actual agent/model names: `→ dispatching <agent_name> (<model>): <task>`.
4. **Point at bundled assets, by heading not page.** PDF assets are in `assets/` (`designing-data-intensive-applications`, `clean-architecture`, `clean-code`, `code-complete-2e`, `fluent-python-2e`, `the-pragmatic-programmer`, `software-engineering-at-google`, and `aposd-2nd-ed-extract`). Ask the helper to search the chapter **heading**, read that section, and report (a) the specific answer, (b) caveats/exceptions the author states, and (c) a short quote only if useful and within the runner's copyright limits. **Cite by chapter/heading, not page** — catalog page numbers are book pages and won't map to extracted text.
5. **Integrate yourself.** The helper returns evidence; you make the call. Don't delegate the decision.

### Caveat — APOSD is only a 20-page extract
`assets/aposd-2nd-ed-extract.pdf` is a 20-page public extract (the public extract has Ch 6, Ch 21, and the tails of Ch 9 & 12; its text layer may be difficult to extract). **Do not dispatch a subagent to "read the APOSD chapter" in that file — most isn't there.** For APOSD, the catalog `references/aposd-complexity.md` is the deepest bundled source (it marks which concepts are verbatim from the extract vs. `[beyond the extract]`). Treat the catalog as authoritative for APOSD. The other seven books have full text and are safe to dispatch against.

## Additional Resources

The per-book catalogs under `references/` are the distilled, always-available Tier-1 source and are sufficient for most work. **Raw book PDFs are not shipped with this skill** (no copies, no download links). For a Tier-2 source-text lookup, **find and fetch** a copy of the specific **edition** below using your runner's web-search/fetch tools — prefer a legitimate source (publisher, library, your own copy; for APOSD, the author's free Stanford extract) — and save it to the matching `assets/<slug>.pdf`. Then `scripts/read_book.py` reads/searches it. **Edition matters:** the catalogs were built against the editions named here; a different edition may renumber chapters (Fluent Python, The Pragmatic Programmer, and DDIA changed substantially between editions). Always cite by **heading text, not page or number**, which stays stable across copies of the same edition.

| Book | Edition (match this) | Save to | Catalog |
|---|---|---|---|
| *A Philosophy of Software Design* — Ousterhout | 2nd ed. (author's free 20-pg extract) | `assets/aposd-2nd-ed-extract.pdf` | `references/aposd-complexity.md` |
| *The Pragmatic Programmer* — Hunt & Thomas | 20th-Anniversary 2nd ed. (2019) | `assets/the-pragmatic-programmer.pdf` | `references/pragmatic-design.md`, `references/pragmatic-craft.md`, `references/pragmatic-tips-catalog.md` |
| *Software Engineering at Google* — Winters et al. | 1st ed. (2020) | `assets/software-engineering-at-google.pdf` | `references/swe-at-google-principles.md` |
| *Clean Code* — Robert C. Martin | 2008 (only ed.) | `assets/clean-code.pdf` | `references/clean-code.md` |
| *Code Complete* — Steve McConnell | 2nd ed. (2004) | `assets/code-complete-2e.pdf` | `references/code-complete.md` |
| *Designing Data-Intensive Applications* — Kleppmann | 1st ed. (2017) | `assets/designing-data-intensive-applications.pdf` | `references/ddia.md` |
| *Clean Architecture* — Robert C. Martin | 1st ed. (2017) | `assets/clean-architecture.pdf` | `references/clean-architecture.md` |
| *Fluent Python* — Luciano Ramalho | 2nd ed. (2022) | `assets/fluent-python-2e.pdf` | `references/fluent-python.md` |

> APOSD note: the public PDF is a 20-page extract; concepts named but not fully in it (design-it-twice, tactical/strategic, the full red-flags list) are genuine APOSD material marked as such in `references/aposd-complexity.md`, not presented as quotations from the extract.
