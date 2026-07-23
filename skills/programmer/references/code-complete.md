# Code Complete, 2nd Edition (Steve McConnell, 2004)

**Thesis:** Software construction is an engineering discipline, and managing complexity is its single Primary Technical Imperative; every practice in this book — from naming to refactoring — is a tool for keeping complexity within a human brain's span of control.

---

## What this book makes you good at

- Structuring classes and routines so that complexity is hidden and localised, not spread
- Applying a principled Pseudocode Programming Process to routine and class construction
- Distinguishing assertions from error-handling, and deploying barricades correctly
- Naming variables, routines, and classes with precision and consistency
- Organising conditionals, loops, and control flow to reduce cognitive load
- Debugging systematically (scientific method) instead of by trial-and-error
- Recognising refactoring "smells" and applying the correct refactoring
- Calibrating when to optimise vs when to keep code readable
- Quantifying quality-technique effectiveness and understanding the cost-of-defect curve

---

## Core principles (actionable)

### Managing Complexity Is the Primary Technical Imperative

"Managing complexity is the most important technical topic in software development." (PAGE 116)

Every design and construction decision should be evaluated against one question: does this make the program easier or harder to hold in a human brain at one time? Dijkstra observed that no programmer's skull is large enough to contain a modern program, so the only safe strategy is to organise work so that you must focus on only one part at a time.

Concrete attack:
- At architecture level: divide into independent subsystems.
- At class level: use ADTs, encapsulation, and information hiding to present simple interfaces.
- At routine level: write short routines with strong cohesion, minimal parameters.
- At statement level: choose names that close the gap between the code and the domain.

### Information Hiding

"Ask yourself, 'What should I hide?'" (PAGE 134). Secrets fall into two camps: (1) hiding complexity so the brain doesn't have to deal with it; (2) hiding sources of change so effects are localised.

Rules:
- Replace `++g_maxId` scattered everywhere with a single `NewId()` routine — hide the ID-creation decision.
- Replace a bare `int` type alias with an `IdType` — hide the representation.
- Concentrate hardware dependencies, I/O formats, and business rules in single classes; other code sees only the interface.
- Barriers to information hiding: excessive distribution of literals (prefer `MAX_EMPLOYEES`), circular dependencies, confusing class data for global data.
- Information hiding is part of the foundation of both structured design and object-oriented design; programs that use it have been found easier to modify by a factor of 4 (Korson and Vaishnavi 1986). (PAGE 133)

### Good Class Interfaces — Abstract Data Types First

"The single most important reason to create a class is to reduce a program's complexity." (PAGE 190)

Build classes as ADTs, then layer inheritance and polymorphism on top.
- Each class must implement **one and only one** ADT. If you can't name the ADT, the class needs to be split.
- Present a **consistent level of abstraction** in the public interface — no mixing `AddEmployee()` with `NextItemInList()`.
- A class interface is like an iceberg: seven-eighths must stay hidden. Ask "what does this need to hide?" before every public member decision.
- Avoid god classes (omniscient Get/Set callers), irrelevant classes (data-only, no behaviour), and verb-only classes (no data).
- Keep fewer than ~7 data members per class; above that, cognitive overload sets in.
- Prefer deep copies to shallow copies until a measured performance reason forces otherwise.
- Use containment over inheritance unless the relationship is truly "is a"; derive only when a derived class adheres to the Liskov Substitution Principle.
- Make all base-class data members private, not protected.

Valid reasons to create a class: model real-world or abstract objects; reduce complexity; isolate complexity; hide implementation details; limit effects of changes; hide global data; streamline parameter passing; make central points of control; facilitate reusable code; plan for a family of programs; package related operations; accomplish a specific refactoring. (PAGE 192-193)

### High-Quality Routines

"The routine is the single greatest invention in computer science." (PAGE 200)

**Cohesion** — the gold standard is functional cohesion: a routine does **one and only one** operation. Study found 50% of highly cohesive routines were fault-free vs 18% of low-cohesion ones (Card et al. 1986). (PAGE 205)

Levels from acceptable to unacceptable:
1. Functional — `Cosine()`, `GetLeafName()` — best
2. Sequential — operations share data step-to-step; acceptable
3. Communicational — operations use same data, unrelated otherwise
4. Temporal — `Startup()` orchestrating; acceptable if it delegates
5. Procedural, Logical, Coincidental — avoid; refactor immediately

**Routine length** — evidence does not support arbitrary short-routine dogma. Studies found routines up to 200 non-comment, non-blank lines are no more error-prone than shorter ones. Let complexity measures (nesting depth, decision points, number of variables) drive length, not a line-count rule. Routines longer than 200 lines require careful justification. (PAGE 211)

**Parameter rules** (39% of all errors are interface errors — Basili and Perricone 1984): (PAGE 211)
- Order parameters: input-only, then input-and-output, then output-only.
- Limit to ~7 parameters; if consistently more, the coupling is too tight — consider a class.
- Never use a parameter as a working variable; copy to a local.
- Use all parameters or remove them; unused parameters correlate with elevated error rates.
- Document assumptions: units, expected ranges, forbidden values, pointer-null expectations.
- Match the abstraction of what you pass — don't pass individual fields when the routine's true contract is the whole object, and vice versa.

**Valid reasons to create a routine:** reduce complexity; introduce a named abstraction; avoid duplicate code; hide sequences; hide pointer operations; improve portability; simplify complex booleans; improve performance; support subclassing. (PAGE 204)

### Defensive Programming

**Assertions vs. error handling** — this is the most important distinction in defensive programming.

- **Assertions** check conditions that **should never occur** — programmer bugs, violated preconditions/postconditions. Compile out for production. "A good way to think of assertions is as executable documentation." (PAGE 228)
- **Error-handling code** checks conditions that **might occur** — bad user input, file not found, network dropout. Stays in production.
- Never put executable code inside an assertion expression — it may be compiled away.

**Barricades** — designate sanitisation boundaries inside the system. (PAGE 241)
- Outside the barricade: use error-handling code (data is dirty).
- Inside the barricade: use assertions (data is guaranteed clean).
- Convert external inputs to proper types at input time.
- The barricade is an architecture-level decision.

**Error-handling options** (choose a strategy and apply it consistently): return neutral value; next valid data; same as last time; closest legal value; log a warning; return error code; call error-processing routine; display message; shut down. Decide between correctness (never return a wrong result) and robustness (always return something) based on the application domain.

**Exception guidelines:**
- Throw exceptions only for truly exceptional conditions, not for normal flow.
- Throw exceptions at the right level of abstraction — `EmployeeDataNotAvailable`, not `EOFException`, from `Employee.GetTaxId()`. (PAGE 237)
- Never swallow exceptions silently; at minimum log them.
- Standardise exception handling across the project.

### The Pseudocode Programming Process (PPP)

The PPP is a concrete method for building routines and classes:
1. Write pseudocode in plain English that captures intent without implementation detail.
2. Iterate until the pseudocode is clear enough to translate mechanically.
3. Translate each pseudocode line into one or more lines of real code; the pseudocode becomes comments.
4. If a pseudocode step is still complex, expand it into more detailed pseudocode before coding.

Key discipline: write the pseudocode before thinking about language syntax. This prevents premature commitment to implementation details. Pseudocode that reads like a narrative proves the design is sound before code is written.

### Variables — Initialisation, Scope, and Single Purpose

**Initialisation rules:**
- Declare and initialise each variable as close as possible to its first use.
- Initialise all member data in every constructor.
- Be especially alert to uninitialized variables in loops and conditional paths.
- Watch for variables re-initialised improperly at the top of a loop.

**Scope minimisation** — "Keep variables live for as short a time as possible" (Chapter 10). Minimise the span (lines between variable uses) and live-time (lines between variable declaration and last use). Long spans and live-times mean more code that could corrupt the variable, more code to re-read when debugging.

**Single purpose** — use each variable for exactly one purpose. Never reuse loop counters or temporary variables for unrelated tasks. Multiple semantic uses of one name obscure the program's meaning.

### Naming Conventions

Good names: the optimal variable name is as long as necessary to be self-documenting, typically 9-15 characters for local variables but longer for wider-scope variables.

Rules:
- Avoid names that differ only by case, only by one letter, or by a number suffix (`claims1`, `claims2`).
- Avoid abbreviations that mislead or require a lookup guide.
- Use opposites consistently (`begin/end`, `open/close`, `source/destination`).
- Prefix booleans with `is`, `has`, `can`, `should` — never name a boolean `status` or `flag`.
- Routines: procedures use verb-noun phrases (`PrintReport()`); functions return values and name the value (`CustomerCount()`).
- Avoid generic names (`temp`, `x`, `data`) except in genuine throwaway contexts.
- Establish and follow a consistent naming convention for the entire project; inconsistency between `employee.id.Get()`, `dependent.GetId()`, and `supervisor()` is a real maintenance burden. (PAGE 210)

### Organising Straight-Line Code and Conditionals

**Straight-line code** — when order matters, make dependency explicit:
- Put initialisation code immediately before the code that uses it.
- Name routines to reveal the dependency (`ComputeNetSalary` implies prior `ComputeGrossSalary`).

**Conditionals:**
- Put the normal case after `if`, the exception after `else`.
- Test the most common case first in chains of `else if`.
- Always write the else clause, even if it only contains a comment explaining why it's empty.
- Use `case`/`switch` for enumerations; add a `default` that asserts/errors to catch unanticipated values.

**Loops:**
- Put the loop-control variable at the top of the loop and nowhere else.
- Enter the loop from the top only.
- Make the exit condition explicit; avoid hidden exits deep in the loop body.
- Limit nested loop depth to ~3 levels; extract inner loops to routines.
- Keep loop bodies short enough to fit on one screen.

### Table-Driven Methods

Use tables to replace complex logic that maps inputs to outputs. Instead of a chain of `if-else` or `case` statements that encode a business rule, store the rule in a table (array, hash, configuration file). The code becomes `result = table[key]` with a table lookup instead of complex conditional logic. Changes to the rule require only a table update, not code modification. (Chapter 18)

Three kinds of table access: direct (use the key as the index), indexed (map the key to a smaller index), and stair-step (find the range the key falls in).

### The General Principle of Software Quality

"Improving quality reduces development costs." (PAGE 474)

Debugging and associated rework consumes about 50% of time on a naive software-development cycle. Upstream activities (requirements, design, code review) have more leverage than downstream ones (testing, debugging). NASA SEL: increased quality assurance was associated with decreased error rates **without increasing cost**. IBM data: "Software projects with the lowest levels of defects had the shortest development schedules and the highest development productivity." (PAGE 474)

Collaborative construction (inspections, pair programming) detects **different kinds** of errors than testing. Formal inspections find 60-90% of defects. No single technique catches everything; use several in combination.

### Debugging — The Scientific Method

Effective debugging follows the scientific method, not trial-and-error:
1. **Stabilise the error** — find a minimal, reproducible test case.
2. **Locate the source** — form a hypothesis, design tests to prove or disprove it, narrow by binary search.
3. **Fix the problem, not the symptom** — understand the root cause before touching code.
4. **Test the fix** — rerun the original test case, add a regression test, check for similar defects.

"Debugging is twice as hard as writing the code in the first place. Therefore, if you write the code as cleverly as possible, you are, by definition, not smart enough to debug it." — Kernighan (PAGE 572)

Key rules:
- Don't change code randomly ("voodoo programming"). Every change should be based on a confident hypothesis.
- Make one change at a time.
- If stuck after a time-boxed attempt, resort to a brute-force technique (code review, rewrite, unit-test harness isolation).
- Confessional debugging ("talk to someone") works because explaining forces you to form the hypothesis you were avoiding.
- Set compiler warnings to maximum; treat them as errors.

### Refactoring — When and How

**The Cardinal Rule of Software Evolution:** evolution should improve the internal quality of the program. (PAGE 602)

"A change made to the internal structure of the software to make it easier to understand and cheaper to modify without changing its observable behavior." (Fowler, cited at PAGE 601)

**Smells that demand refactoring** (selected):
- Duplicate code ("Copy and paste is a design error" — Parnas, cited at PAGE 601)
- A routine is too long / a loop is too deeply nested
- A class has poor cohesion or a mixed-level interface
- Parameter lists with too many parameters
- Parallel modifications required in multiple classes or case statements
- Primitive data types overloaded to represent real-world concepts
- Public data members
- Setup/takedown code surrounding every routine call (wrong abstraction)
- Comments explaining difficult code — "Don't document bad code — rewrite it" (Kernighan and Plauger 1978, cited at PAGE 605)

**Specific refactorings:**
- Data: replace magic number with named constant; rename for clarity; introduce intermediate variable; convert multi-use variable to single-use; convert primitive to class; encapsulate collection.
- Statement: decompose boolean expression; move complex boolean to named function; consolidate conditional fragments.
- Routine: extract routine; move routine to class that uses it most; replace conditionals with polymorphism.
- Class: extract class; hide delegate; convert inheritance to containment (has-a instead of is-a).

**Refactoring safety:** keep changes small; run regression tests after each step; one refactoring at a time; save original code before starting.

### Code-Tuning Strategies

"The General Principle of Software Performance: first, make it work correctly; then, make it work efficiently — but only if efficiency is actually needed." (Chapter 25 summary)

- Don't optimise until you have measured evidence of where the bottleneck is.
- Common misconceptions: loops are always the bottleneck (often not), clever code is faster (often the opposite).
- Profiles, not intuition, reveal actual bottlenecks.
- After measuring and finding a hot spot: loop unrolling, strength reduction, caching, short-circuit evaluation, lookup tables.
- Always re-measure after an optimisation — many optimisations make code faster in theory and slower in practice on real hardware.

---

## Chapter map

| Part | Ch | Title | Problem Solved |
|------|----|-------|----------------|
| I | 1 | Welcome to Software Construction | Defines construction scope: coding, testing, debugging, not requirements/architecture |
| I | 2 | Metaphors for Understanding Software | Gives mental models (accretion, building) to reason about software development |
| I | 3 | Measure Twice, Cut Once: Upstream Prerequisites | Establishes when to do requirements and architecture before coding; cost-of-change data |
| I | 4 | Key Construction Decisions | Language choice, conventions, and technology-wave effects on construction |
| II | 5 | Design in Construction | Managing complexity via design heuristics: abstraction, encapsulation, information hiding, cohesion, coupling, design levels |
| II | 6 | Working Classes | ADTs, class interface quality, reasons to create a class, inheritance rules |
| II | 7 | High-Quality Routines | Cohesion, length, parameter ordering, naming, reasons to create a routine |
| II | 8 | Defensive Programming | Assertions vs error handling, barricades, exception guidelines, debugging aids |
| II | 9 | Pseudocode Programming Process | Step-by-step process for designing and coding a routine top-down |
| III | 10 | General Issues in Using Variables | Initialisation, scope, live-time, binding time, single-purpose rule |
| III | 11 | The Power of Variable Names | Naming length, kind-specific rules, conventions, names to avoid |
| III | 12 | Fundamental Data Types | Type-specific guidelines: numbers, booleans, enums, named constants, arrays |
| III | 13 | Unusual Data Types | Structures, pointers, global data, access routines |
| IV | 14 | Organizing Straight-Line Code | Dependencies, ordering, and documentation of required ordering |
| IV | 15 | Using Conditionals | if-then-else, case, decision tables, guarding clauses |
| IV | 16 | Controlling Loops | Loop entry/exit, variable placement, nesting limits |
| IV | 17 | Unusual Control Structures | Multiple returns, recursion, goto (almost always wrong) |
| IV | 18 | Table-Driven Methods | Direct, indexed, and stair-step access to replace complex logic |
| IV | 19 | General Control Issues | Boolean expressions, null statements, deep nesting, structured programming |
| V | 20 | The Software-Quality Landscape | Quality characteristics, technique effectiveness, General Principle of Software Quality |
| V | 21 | Collaborative Construction | Pair programming, formal inspections, walkthroughs, code reviews |
| V | 22 | Developer Testing | Unit/integration/regression testing, test-case strategies, test-support tools |
| V | 23 | Debugging | Scientific method for debugging, finding/fixing defects, psychological factors |
| V | 24 | Refactoring | When/how to refactor, full catalog of refactorings, safe refactoring practices |
| V | 25 | Code-Tuning Strategies | When to tune, performance myths, measurement discipline |
| V | 26 | Code-Tuning Techniques | Loop, logic, data, expression, and routine-level optimisations |
| VI | 27 | How Program Size Affects Construction | Error rates, productivity, and required formality as project size grows |
| VI | 28 | Managing Construction | Configuration management, estimation, measurement, treating programmers well |
| VI | 29 | Integration | Phased vs incremental integration, integration strategies |
| VI | 30 | Programming Tools | IDE, version control, build tools, testing frameworks, refactoring tools |
| VII | 31 | Layout and Style | Visual formatting rules for readability |
| VII | 32 | Self-Documenting Code | Commenting philosophy, when/how to comment, documentation standards |
| VII | 33 | Personal Character | Curiosity, honesty, communication, and the intellectual humility to improve |
| VII | 34 | Themes in Software Craftsmanship | Program **into** your language (not **in** it); the importance of conventions |
| VII | 35 | Where to Find More Information | Reading list by topic |

---

## Problem -> where to look

| Problem | Chapter / Section (page) |
|---------|--------------------------|
| My design is hard to understand and change | Ch 5 Design in Construction, esp. §5.2 Key Design Concepts (p. 77) and §5.3 "Hide Secrets" (p. 90) |
| Deciding whether to create a class or routine | §6.4 Reasons to Create a Class (p. 152); §7.1 Valid Reasons to Create a Routine (p. 164) |
| Routine has too many responsibilities or parameters | §7.2 Design at the Routine Level (cohesion, p. 168); §7.5 How to Use Routine Parameters (p. 174) |
| When to use assertions vs. try/catch/error codes | §8.2 Assertions (p. 189); §8.3 Error-Handling Techniques (p. 194); §8.5 Barricades (p. 203) |
| How to write a new routine from scratch | Ch 9 Pseudocode Programming Process (p. 215) |
| Variable name or scope is confusing code | Ch 10 General Issues in Using Variables (p. 237); Ch 11 Power of Variable Names (p. 259) |
| Complex conditional or loop logic | Ch 15 Using Conditionals (p. 355); Ch 16 Controlling Loops (p. 367); Ch 18 Table-Driven Methods (p. 411) |
| How to detect when to refactor and what to do | §24.2 Introduction to Refactoring, smells (p. 565); §24.3 Specific Refactorings (p. 571) |
| A bug is hard to find and I am guessing randomly | §23.2 Finding a Defect (scientific method, p. 540); debugging checklist (p. 596) |
| Justifying code reviews to management | §20.3 Relative Effectiveness of Quality Techniques (p. 469); §21.3 Formal Inspections (p. 485) |
| Project is slow; need to decide whether to optimise code | §25.1 Performance Overview (p. 588); §25.4 Measurement (p. 603) |
| How much up-front requirements/design before coding | §3.6 Amount of Time to Spend on Upstream Prerequisites (p. 55); §3.4 Requirements Prerequisite (p. 38) |
| Choosing a consistent error-handling strategy for a project | §8.3 High-Level Design Implications of Error Processing (p. 197) |
| Code review / inspection — how to run one | §21.3 Formal Inspections (p. 485) |
| Testing strategy for a module | §22.2 Recommended Approach to Developer Testing (p. 503); §22.3 Bag of Testing Tricks (p. 505) |

---

## Convergences and debates

### Agrees with

**A Philosophy of Software Design (Ousterhout):**
- Both books centre on reducing complexity as the supreme goal.
- Both endorse deep modules with narrow, well-defined interfaces; Code Complete frames this as information hiding, APOSD calls it "deep modules."
- Both reject meaningless or cosmetic comments in favour of comments that explain "why."

**The Pragmatic Programmer (Hunt & Thomas):**
- DRY principle (Don't Repeat Yourself): Code Complete calls it "avoid duplicate code" and quotes Parnas that "copy and paste is a design error." (PAGE 601)
- Both endorse defensive programming; both say assertions should abort loudly in development.
- Refactoring as a continuous activity, not a one-time cleanup.

**Clean Code (Martin):**
- Strong cohesion and small, focused routines.
- Meaningful names; avoid noise words.
- Limit function parameters.

**Software Engineering at Google (Winters et al.):**
- Automated testing and regression testing are non-negotiable.
- Code reviews as a quality gate.

### Disagrees with or offers a contrasting view

**Clean Code vs. Code Complete on routine length:**
- Clean Code advocates aggressively tiny functions (5-10 lines max, named for what they do). Code Complete explicitly cites empirical research showing no evidence that routines below ~200 lines are safer than routines up to 200 lines, and warns that breaking everything into micro-functions can hurt readability. (PAGE 211)
- Code Complete says "Let cohesion, nesting depth, and complexity drive length" — not an arbitrary line count.

**APOSD vs. Code Complete on comments:**
- APOSD argues more comments are needed (Ousterhout explicitly criticises the "comments are failures" school). Code Complete agrees: it calls for "self-documenting code supplemented by meaningful comments," and says comments should explain purpose and intent, not restate the code.
- Neither agrees with Clean Code's position that comments are a code smell.

**Clean Architecture / SOLID vs. Code Complete:**
- SOLID's many-small-classes principle (Single Responsibility Principle taken to an extreme, Interface Segregation) pushes toward tiny, verb-like classes. Code Complete explicitly warns against "classes named after verbs" (no data, only behaviour) as usually the wrong abstraction, and says "avoid creating god classes" but also avoid irrelevant classes with no behaviour. (PAGE 192)
- Code Complete is more pragmatic: class size should be driven by ADT coherence, not an ideological small-class principle.

**DDIA (Kleppmann):**
- Code Complete is focused on individual-programmer construction quality; DDIA addresses distributed-systems reliability patterns. They operate at different levels and rarely conflict directly.
- Where they touch: Code Complete's advice on error handling (correctness vs. robustness trade-off at PAGE 197) parallels DDIA's discussion of failure modes, but CC is code-centric while DDIA is system-centric.

**Fluent Python (Ramalho):**
- Fluent Python explores language-specific idioms for expressiveness. Code Complete is language-agnostic and occasionally cautious about "clever" solutions that sacrifice readability for cleverness.
- Code Complete's "program **into** your language" (Section 34.4) actually aligns with Fluent Python's spirit: use the language's strengths, but thoughtfully.

**Pragmatic Programmer on try-error approaches:**
- The Pragmatic Programmer quote "A dead program does a lot less damage than a crippled one" (cited in CC at PAGE 243 as Hunt and Thomas) agrees with offensive programming: fail hard in development. Code Complete endorses this for development but specifies that production should be graceful, not aborted, in most consumer contexts. The nuance is that both agree on the direction but Code Complete is more explicit about the correctness vs. robustness trade-off by application domain.
