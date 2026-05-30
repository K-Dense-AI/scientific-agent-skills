# The Pragmatic Programmer — Full Tip Catalog

Reference companion to `SKILL.md`. All 70 numbered Tips from Hunt & Thomas, *The Pragmatic Programmer: From Journeyman to Master* (Addison-Wesley, 1999), grouped by chapter, with the authors' core idea, reasoning/analogy, and technique. Extracted from the book text; design-bearing entries are expanded, process/people entries kept brief.

> The whole book is set up by **Tip 1: Care About Your Craft** and **Tip 2: Think! About Your Work** (Preface) — do the work well, and think about *what* you're doing *while* you're doing it. Every other tip is an application of those two.

---

## Ch. 1 — A Pragmatic Philosophy (framing)

- **Tip 3: Provide Options, Don't Make Lame Excuses.** Take responsibility; when something breaks, bring solutions, not blame. "The cat ate my source code" won't cut it.
- **Tip 4: Don't Live with Broken Windows.** *Broken Window Theory* — one unrepaired bad design/decision/code signals abandonment and accelerates rot. Fix it now, or visibly "board it up" (stub, comment out, `Not Implemented`) so damage doesn't spread.
- **Tip 5: Be a Catalyst for Change.** *Stone soup* — people find it easier to join an ongoing success; start something small and good, demonstrate it, let others add to it.
- **Tip 6: Remember the Big Picture.** *Boiled frog* — gradual degradation goes unnoticed. Constantly review what's happening around you, not just your own task.
- **Tip 7: Make Quality a Requirements Issue.** "Good-enough software": specify scope and quality *as a requirement*, negotiated with users; knowing when to stop is part of the craft ("striving to better, oft we mar what's well").
- **Tip 8: Invest Regularly in Your Knowledge Portfolio.** Knowledge expires; manage it like a financial portfolio — invest regularly, diversify, take some risks. (Learn a language a year, read regularly, etc.)
- **Tip 9: Critically Analyze What You Read and Hear.** Beware zealots and hype; think for yourself.
- **Tip 10: It's Both What You Say and the Way You Say It.** "A good idea is an orphan without effective communication." Know your audience (WISDOM), plan the message, pick the moment and style, listen.

## Ch. 2 — A Pragmatic Approach (CORE design)

- **Tip 11: DRY — Don't Repeat Yourself.** Every piece of knowledge needs a single, unambiguous, authoritative representation. Duplicated knowledge diverges — "it isn't a question of whether you'll remember; it's a question of when you'll forget." Four kinds: **imposed** (generate copies from one source automatically), **inadvertent** (don't store derivable data; if you cache for performance, hide it behind accessors + dirty flag), **impatient** (resist copy-paste — "short cuts make for long delays"; cf. Y2K), **inter-developer** (communication, a project librarian, a shared utilities depot, code reviews).
- **Tip 12: Make It Easy to Reuse.** "If it isn't easy, people won't do it" — and they'll re-duplicate. Foster an environment where finding and reusing is easier than rewriting.
- **Tip 13: Eliminate Effects Between Unrelated Things (Orthogonality).** Independent components → a change in one doesn't ripple. *Helicopter* analogy: when everything's coupled, "there is no such thing as a local fix." *Test:* change one requirement → only one module should be affected. Techniques: shy code + Law of Demeter; avoid global data (pass context in); avoid similar functions (Strategy); judge a toolkit by whether it forces changes into your code (transparent vs intrusive); a unit test that drags in half the system signals poor decoupling; track how many files each bug fix touches.
- **Tip 14: There Are No Final Decisions.** Reversibility. Each irreversible decision narrows your target until any change makes you miss. Decisions are "written in the sand at the beach," not carved in stone. Abstract third-party products behind interfaces; make deployment topology a config choice; put cross-cutting details in metadata so they can be removed automatically too.
- **Tip 15: Use Tracer Bullets to Find the Target.** For novel systems with unknowns, build a thin but *complete* end-to-end path (UI→logic→DB) with full error checking and structure — immediate feedback, daily integration, measurable progress. **Tracer code is not disposable — you write it for keeps**; it's the skeleton you flesh out.
- **Tip 16: Prototype to Learn.** Disposable experiments targeting one risk (architecture, new functionality, external data, third-party tools, performance, UI). Ignore correctness/completeness/robustness/style. *Balsa-and-duct-tape car.* "Its value lies not in the code produced, but in the lessons learned." Make sure everyone knows it's throwaway; if they won't, use tracer bullets instead.
- **Tip 17: Program Close to the Problem Domain.** Invent mini-languages in the domain's vocabulary so requirements read almost verbatim as executable spec, and errors are domain-specific. Data languages vs imperative; line-oriented vs formal grammar (readable grammar costs more up front but pays off over the app's long life); stand-alone (generate SQL/C/HTML) or embedded.
- **Tip 18: Estimate to Avoid Surprises.** Build a feel for magnitudes. Scale units to intended accuracy ("about six months", not "130 days"). Ask someone who's done it; build a model; decompose into components; find the multiplicative parameters; vary critical parameters to produce a range. When asked cold: "I'll get back to you."
- **Tip 19: Iterate the Schedule with the Code.** "The only way to determine the timetable for a project is by gaining experience on that same project." Refine estimates each iteration.

## Ch. 3 — The Basic Tools (timeless ideas; tool specifics dated)

- **Tip 20: Keep Knowledge in Plain Text.** Human-readable, self-describing data outlives the apps that made it and can be processed with every tool you have. Insurance against obsolescence.
- **Tip 21: Use the Power of Command Shells.** Compose tools in ways GUIs can't ("WYSIAYG — what you see is all you get"). Ad hoc automation lives at the command line.
- **Tip 22: Use a Single Editor Well.** Master one editor across all tasks so manipulation becomes reflex and the editor is "an extension of your hand."
- **Tip 23: Always Use Source Code Control.** A project-wide UNDO / time machine; tracks who/what/when; enables branching and automated builds. Always — even solo, even throwaway. Put *everything* under it (code, docs, config, build scripts, test data).
- **Tips 24–27 (Debugging mindset): Fix the Problem, Not the Blame · Don't Panic · "select" Isn't Broken · Don't Assume It—Prove It.** Debugging is just problem solving. It's your problem regardless of whose fault. Don't waste a neuron on "but that can't happen" — it can and did. Assume the bug is in *your* code first (the OS/compiler/library is almost certainly fine); reproduce it, binary-search, rubber-duck it, and *prove* assumptions by testing boundaries. When surprised, you found a false assumption — add a test so it never returns.
- **Tip 28: Learn a Text Manipulation Language.** Force multiplier for prototyping, code generation, and one-off transforms — jobs 5–10× faster than in a conventional language.
- **Tip 29: Write Code That Writes Code.** *Passive* generators save typing (templates); *active* generators enforce DRY by producing all derived forms from one canonical source as part of the build, so divergence is caught at compile time.

## Ch. 4 — Pragmatic Paranoia (CORE defensive design)

- **Tip 31: Design with Contracts.** Each routine has preconditions (caller's obligation), postconditions (its guarantee), and class invariants. *Be strict in what you accept, promise as little as possible in return* ("lazy"/closed code). A broken contract is a **bug**, not a runtime case — and not for validating user input. Honor LSP for subclasses. Write contracts as comments/assertions when the language lacks support; they're design docs and the first place to look when things break.
- **Tip 32: Crash Early.** *Dead programs tell no lies.* Every "impossible" error signal is real information; a program that detects a corrupt state should die at the source with a stack trace rather than limp on. "A dead program normally does a lot less damage than a crippled one." Check every return code; add `default` to every switch.
- **Tip 33: If It Can't Happen, Use Assertions to Ensure That It Won't.** Assert the impossible (`assert ptr != null`, post-sort ordering). **Don't disable assertions in production** — "like crossing a high wire without a net because you once made it across in practice." Never put side effects inside an assertion (Heisenbugs). Assertions are not a substitute for real error handling.
- **Tip 34: Use Exceptions for Exceptional Problems.** An exception is "a kind of cascading goto"; using it for normal flow creates spaghetti and tightens coupling. *Test:* "Will this code still run if I remove all the exception handlers?" — if no, you're overusing them. File that *should* exist → exception; user-supplied file that *might* not → error return.
- **Tip 35: Finish What You Start.** Whoever allocates a resource deallocates it — keep open/close, acquire/release, malloc/free paired in the same scope (RAII / `finally`). Deallocate in reverse order; allocate in consistent order to avoid deadlock. For nested structures, pick and enforce one ownership invariant.

## Ch. 5 — Bend, or Break (CORE decoupling & flexibility)

- **Tip 36: Minimize Coupling Between Modules.** Write *shy code* — don't reveal yourself unnecessarily, don't talk to strangers (Law of Demeter: call only methods of self, parameters, created objects, direct components). Train-wreck chains (`a.getB().getC().getD()`) create "a combinatorial explosion of dependency relationships." *Spy-cell* analogy. Fix with delegating/facade methods; document any intentional coupling chosen for performance.
- **Tip 37: Configure, Don't Integrate.** Externalize deep choices — algorithm, database product, middleware, UI style, deployment — not just colors and prompts. "Dodo-code" that can't adapt goes extinct.
- **Tip 38: Put Abstractions in Code, Details in Metadata.** Program the general case; push specifics into metadata/config/rules/scripts, soft and changeable, ideally reloadable at runtime. Think declaratively (what, not how). Aim for a reusable engine driven by metadata.
- **Tips 39–41: Analyze Workflow to Improve Concurrency · Design Using Services · Always Design for Concurrency.** Linear "do this then that" thinking creates *temporal coupling*. Map the real workflow (activity diagrams) to find what can run independently (the piña-colada example); use async work queues and the *hungry consumer* model. Design components as independent services behind consistent interfaces; protect shared state; keep objects always-valid (no separate init step) — retrofitting concurrency later is much harder.
- **Tip 42: Separate Views from Models.** MVC + publish/subscribe: the model holds data with no knowledge of its views; "the sender of the event doesn't need any explicit knowledge of the receiver." One model, many views (and viewer-of-viewer networks). Avoid the giant central event/`case` routine that knows everyone's interactions.
- **Tip 43: Use Blackboards to Coordinate Workflow.** A shared space where independent agents post and consume facts anonymously and asynchronously, with no knowledge of each other (*murder-investigation blackboard*). Combine with a rules engine so order of arrival is irrelevant; partition large boards into zones.

## Ch. 6 — While You Are Coding (CORE)

- **Tip 44: Don't Program by Coincidence.** *Minefield* — succeeding by luck teaches nothing safe. Don't rely on accidents of implementation/context or implicit assumptions. Program deliberately: proceed from a plan, rely only on documented behavior (else document your assumption), test assumptions, and don't be a slave to history.
- **Tips 45–46: Estimate the Order of Your Algorithms · Test Your Estimates.** Know the Big-O of loops/recursion (O(n), O(m·n), O(log n), O(n log n), factorial). "An algorithm that takes a minute on ten items may take a lifetime on 100." But the notation hides constants — profile and measure with real data; beware premature optimization; the fastest algorithm isn't always best for small n.
- **Tip 47: Refactor Early, Refactor Often.** Code is a *garden*, not a building. Treat code needing refactoring as a *tumor* — remove it while small and cheap. Triggers: duplication, non-orthogonality, drifted requirements, performance. Don't refactor and add features at once; have tests first; small deliberate steps. "No time" now = far more time later.
- **Tips 48–49: Design to Test · Test Your Software, or Your Users Will.** Testability is a design property (*Software IC* with built-in self test). Design the contract and its test together — try the interface before committing; test against contract (pre/postconditions, boundaries, expected rejections); test subcomponents first to localize failures; keep tests close to the code so they're used. "Testing is more cultural than technical."
- **Tip 50: Don't Use Wizard Code You Don't Understand.** Library calls hide behind a clean interface; *wizard* code is interwoven into yours line by line and becomes yours. "No one should be producing code they don't fully understand."

## Ch. 7 — Before the Project

- **Tip 51: Don't Gather Requirements — Dig for Them.** They're buried "beneath layers of assumptions, misconceptions, and politics."
- **Tip 52: Work with a User to Think Like a User.** Spend time in their world to learn how the system will really be used.
- **Tip 53: Abstractions Live Longer than Details.** Separate stable *requirement* from changeable *policy* ("only authorized users…" → an access-control system whose rules live in metadata).
- **Tip 54: Use a Project Glossary.** One name per concept across the whole team.
- **Tip 55: Don't Think Outside the Box — Find the Box.** Solve "impossible" puzzles by identifying the *real* constraints and the degrees of freedom within them; can you *prove* a path is closed?
- **Tip 56: Listen to Nagging Doubts — Start When You're Ready.** Instinct from experience; prototype to tell genuine unease from procrastination.
- **Tip 57: Some Things Are Better Done than Described.** Don't fall into the specification spiral; over-specification robs coding of skill and can specify the unbuildable. Spec, design, and implementation are facets of one process with feedback between them.
- **Tips 58–59: Don't Be a Slave to Formal Methods · Expensive Tools Do Not Produce Better Designs.** Methods/notations are fallible interpretations; use them in context, prefer prototypes and real user interaction. "Circles and arrows make poor masters."

## Ch. 8 — Pragmatic Projects

- **Tip 60: Organize Around Functionality, Not Job Functions.** Apply orthogonality and Design by Contract to *teams*: cohesive, self-contained teams own functional areas → fewer interactions, more ownership.
- **Tip 61: Don't Use Manual Procedures.** "People just aren't as repeatable as computers." Automate checkout/build/test/ship — ideally a single command — plus the nightly build.
- **Tips 62–66 (Ruthless Testing): Test Early. Test Often. Test Automatically · Coding Ain't Done 'Til All the Tests Run · Use Saboteurs to Test Your Testing · Test State Coverage, Not Code Coverage · Find Bugs Once.** The earlier a bug is found, the cheaper it is. A good project may have more test code than production code. Types form a net: unit, integration, validation, resource-exhaustion, performance, usability. Once a human finds a bug, add a test so a human never finds it again.
- **Tips 67–68: Treat English as Just Another Programming Language · Build Documentation In, Don't Bolt It On.** Docs and code are two views of one model — apply DRY (generate API docs and schemas from one source; comments say *why*, not how). "All documentation is a mirror of the code. If there's a discrepancy, the code is what matters."
- **Tip 69: Gently Exceed Your Users' Expectations.** Success = meeting (and slightly beating) expectations; communicate continuously so expectations stay accurate.
- **Tip 70: Sign Your Work.** Ownership and pride; anonymity breeds sloppiness. "Your signature should come to be recognized as an indicator of quality."

---

*Tip 30 is not a numbered tip in the original sequence as printed; the design-bearing tips above are numbered 1–70 as they appear in the book's tip boxes. When in doubt, the book text in `/tmp/pp_full.txt` (if still present) or the published edition is authoritative.*
