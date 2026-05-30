# A Philosophy of Software Design — Complexity & Design Depth

John Ousterhout, *A Philosophy of Software Design*, 2nd ed. (Yaknyam Press, 2021). The local copy is a **20-page public extract** (complete Ch. 6 and Ch. 21, plus the tails of Ch. 9 and Ch. 12). Concepts the extract *names but does not fully develop* are marked **[APOSD concept, beyond the extract]** — they are genuinely Ousterhout's and safe to apply, but are not quotations from the local PDF. Verbatim quotes below are transcribed from the extract images.

## The thesis: complexity is the enemy

The whole book reduces to one objective: **minimize complexity.** A good design is one that a developer can work in without holding the whole system in their head.

**Complexity = anything about a system's structure that makes it hard to understand or modify.** [APOSD Ch. 2, beyond the extract] It is *incremental*: it accumulates from many small chunks, no one of which seems bad, which is why it must be fought continuously rather than in a single cleanup.

**Three symptoms — how you know complexity is present** (restated in the Ch. 12 fragment of the extract):
- **Change amplification** — "a seemingly simple change requires code modifications in many places."
- **Cognitive load** — "in order to make a change, the developer must accumulate a large amount of information."
- **Unknown unknowns** — "it is unclear what code needs to be modified, or what information must be considered in order to make those modifications." *This is the worst of the three:* with the other two you at least know what you're up against.

**Two root causes:** **dependencies** (when code can't be understood or changed in isolation) and **obscurity** (when important information is not obvious). Almost every design technique in the book attacks one or both.

## Tactical vs. strategic programming [APOSD Ch. 3, referenced in the extract via the "investment mindset"]

- **Tactical programming**: the goal is to get *this* feature working / *this* bug fixed as fast as possible. Each tactical shortcut adds a little complexity; tactical programmers accept that to move fast today. The complexity compounds into an unworkable system.
- **Strategic programming**: the primary goal is a *great design* that also happens to work; working code is necessary but not sufficient. You deliberately **"spend a bit more time up front to save time later on"** (the *investment mindset*, quoted in the extract). The recommended investment is roughly 10–20% of development time, paid back as the codebase staying changeable.
- "Working code isn't enough." The most important division of programmers is not skill but mindset: tactical tornadoes produce features fast and leave wreckage; strategic programmers compound a clean codebase.

## Deep modules — the central design move

A module = any unit with an interface and an implementation (a class, a method, a service). Think of each as having two parts: an **interface** (what a caller must know to use it) and an **implementation** (everything else).

- **Deep module:** powerful functionality behind a *simple* interface. Best ratio of benefit (functionality) to cost (interface complexity). Example: a garbage collector — enormous machinery, *no* interface at all.
- **Shallow module:** interface is complex relative to the functionality it provides. A method whose signature is nearly as complicated as its body buys you nothing.
- **"the best modules are deep: they allow a lot of functionality to be accessed through a simple interface."**
- **Classitis** [APOSD term, beyond the extract]: the mistaken doctrine that classes/methods should be tiny, which multiplies shallow modules and *interfaces*, raising total complexity. From the Ch. 9 extract, directly rebutting *Clean Code*'s "functions should be tiny": **"Depth is more important than length: first make functions deep, then try to make them short enough to be easily read. Don't sacrifice depth for length."** Functions split too far become **"conjoined functions that must be read and understood together"** — worse than one larger function.

The split-or-join decision (Ch. 9 conclusion, verbatim): **"The decision to split or join modules should be based on complexity. Pick the structure that results in the best information hiding, the fewest dependencies, and the deepest interfaces."**

## Information hiding & leakage (Ch. 6)

- **Information hiding:** each module encapsulates design decisions (knowledge) that don't appear in its interface. This is what *makes* modules deep and reduces both dependencies and obscurity.
- **Information leakage:** the opposite — a design decision is reflected in *multiple* modules, creating a dependency between them. In the extract's editor example, UI concepts (backspace, selection, cursor) leaked into the text-storage class, coupling the two so "each new UI operation required a new text-class method."
- **General-purpose modules are deeper.** The extract's core finding: **"general-purpose interfaces are simpler and deeper than special-purpose ones, and they result in less code in the implementation."** The sweet spot is **"somewhat general-purpose"** — *functionality* reflects today's needs, but the *interface* is general enough to support several uses: **"easy to use for today's needs without being tied specifically to them."** (Don't over-generalize either — "the word 'somewhat' is important.")
- A **false abstraction** purports to hide information the caller actually needs (the `backspace` method "purported to hide information about which characters are deleted, but the user interface module really needs to know this"). **"One of the most important parts of software design is determining who needs to know what, and when. When the details are important, it is better to make them explicit and as obvious as possible."**
- **Push specialization up or down** to keep general-purpose code clean: app-specific features belong in *top* layers (push up); device-specific behavior belongs in *drivers* behind a general interface (push down). Specialization "should not percolate down" into general-purpose modules.

### Three questions to find the general/special balance (Ch. 6.5, verbatim)
1. **"What is the simplest interface that will cover all my current needs?"** — reducing the number of methods without reducing capability makes an API more general. (Watch out: cramming in arguments isn't real simplification.)
2. **"In how many situations will this method be used?"** — a method designed for *one* use (like `backspace`) is a **red flag** of over-specialization.
3. **"Is this API easy to use for my current needs?"** — needing a lot of extra glue code to use a class is a **red flag** the interface is wrong.

## Eliminate special cases (Ch. 6.8)

Code "riddled with `if` statements" is hard to follow and bug-prone. **"The best way to [eliminate special cases] is by designing the normal case in a way that automatically handles the edge conditions without any extra code."** Extract example: instead of a "no selection" flag checked everywhere, represent an empty selection (start == end) so copy inserts 0 bytes and delete regenerates the line — *the special case disappears.*

## Design it twice [APOSD Ch. 11, referenced in the extract]

Referenced in Ch. 21: it's much easier to spot what matters when you have **multiple options to compare.** Before committing to the first design that comes to mind, sketch **two or three radically different approaches** and compare them on interface simplicity and complexity. "Designing it twice" costs little and consistently produces a better result — even very smart people don't get the best design on the first try.

## Comments capture what the code can't (Ch. 12)

- The purpose of a comment is to **capture information that was in the designer's mind but couldn't be expressed in the code** — and to make it unnecessary to read the implementation to use an abstraction.
- Comments explain **why** and state the **abstraction** (interface comments), not restate the **how**. A comment that just paraphrases the code is a red flag.
- Direct rebuttal of *Clean Code*'s "comments are failures": **"Well-written comments are not failures. They increase the value of code and serve a fundamental role in defining abstractions and managing system complexity."** Replacing a comment with a long method name (`isLeastRelevantMultipleOfNextLargerPrimeFactor`) carries *less* information than a sentence and forces re-reading.
- **Write comments first** [APOSD Ch. 15, beyond the extract]: writing the interface comment *before* the code is a design tool — if the comment is hard to write or long, the abstraction is probably wrong.

## Decide what matters (Ch. 21)

- **"One of the most important elements of good software design is separating what matters from what doesn't matter."** Emphasize the things that matter (make them prominent, repeated, central); hide the things that don't.
- Look for **leverage points**: "where the solution to one problem also allows many other problems to be solved." A general insert/delete interface has more leverage than `backspace`. An **invariant** is a leverage point — knowing it lets you predict behavior in many situations.
- **Minimize what matters**: fewer constructor parameters, sensible defaults, hide info inside modules, handle exceptions low so they "don't matter to the rest of the system."
- **"The phrase 'good taste' describes the ability to distinguish what is important from what isn't important. Having good taste is an important part of being a good software designer."**

## Red flags — design smells (Ch. 6 + the broader APOSD catalog)

The extract explicitly flags two (a method built for one specific use; needing lots of glue code to use a class). The full APOSD red-flag list **[beyond the extract, but core to the book]**:

| Red flag | Meaning |
|---|---|
| **Shallow Module** | Interface complexity ≈ implementation complexity; the module isn't pulling its weight. |
| **Information Leakage** | The same design decision appears in two+ modules. |
| **Temporal Decomposition** | Structure mirrors *execution order* (read→process→write) instead of knowledge; spreads one decision across stages. |
| **Overexposure** | The API forces callers to learn rarely-used features to use common ones (e.g., buffered vs. unbuffered I/O). |
| **Pass-Through Method** | A method that does nothing but call another with the same signature — adds interface, no value. |
| **Repetition** | The same snippet appears again and again (a DRY failure). |
| **Special-General Mixture** | General-purpose mechanism tangled with special-purpose code for one use of it. |
| **Conjoined Methods** | Two methods so interdependent you must read both to understand either. |
| **Comment Repeats Code** | The comment adds no information beyond the code. |
| **Implementation Documentation Contaminates Interface** | Interface comments describe implementation details callers shouldn't need. |
| **Vague Name** | A name so generic it carries no information (`data`, `obj`, `count`). |
| **Hard to Pick Name** | Difficulty naming signals the underlying abstraction is muddled. |
| **Hard to Describe** | If the interface comment must be long/complex, the abstraction is probably wrong. |
| **Nonobvious Code** | Behavior that isn't apparent from a quick read — the cardinal sin, since obviousness is the goal. |

**Obviousness is the north star.** "If code is nonobvious, that's a red flag." Good design is design that the next reader finds *obvious* — they guess correctly what it does and how to change it on the first try.
