# Software Engineering at Google — Engineering Over Time & At Scale

Titus Winters, Tom Manshreck, Hyrum Wright (eds.), *Software Engineering at Google* (O'Reilly, 2020). This catalog captures the **durable philosophy**, deliberately skipping Google-specific tooling (Bazel, Critique, Tricorder, Code Search). Quotes are verbatim; page numbers refer to the logical PDF page of the local copy.

## The central thesis

> **"Software engineering is programming integrated over time."**

Three dimensions separate engineering from programming: **time, scale, and trade-offs.**

- **Time.** "programming is about producing code. Software engineering extends that to include the maintenance of that code for its useful life span." Short-lived code is "effectively 'just' a programming problem." There is "a factor of at least 100,000 times between the life spans of short-lived code and long-lived code. It is silly to assume that the same best practices apply universally on both ends of that spectrum." The transition: "a project must begin to react to changing externalities."
- **Scale.** Software engineering is "the multiperson development of multiversion programs." "A programming task is often an act of individual creation, but a software engineering task is a team effort." Every repeated task should scale **sublinearly** in human effort: "Every task your organization has to do repeatedly should be scalable (linear or better) in terms of human input." Superlinear human cost = unsustainable.
- **Trade-offs.** "In software engineering, we are regularly forced to evaluate the trade-offs between several paths forward."

The litmus distinction: **"It's programming if 'clever' is a compliment, but it's software engineering if 'clever' is an accusation."**

## Sustainability — the central question

> **"Your project is sustainable if, for the expected life span of your software, you are capable of reacting to whatever valuable change comes along, for either technical or business reasons. Importantly, we are looking only for capability — you might choose not to perform a given upgrade."**

It's about *capability*, not constant change: "We shouldn't change just for the sake of change. But we do need to be capable of change." The discipline is distinguishing **"'it works' versus 'it is maintainable.'"**

## Hyrum's Law

> **"With a sufficient number of users of an API, it does not matter what you promise in the contract: all observable behaviors of your system will be depended on by somebody."**

"Akin to entropy" — it "can never be eradicated," only mitigated. "Given enough time and enough users, even the most innocuous change will break something." (Canonical example: randomizing hash-map order to *prevent* dependence becomes a behavior someone depends on as a random source.) **Practical consequence:** your real contract is everything observable, not just what you documented — so hide behavior you don't want depended on, and expect to break someone whenever you change anything observable.

## The Beyoncé Rule

> **"If a product experiences outages or other problems as a result of infrastructure changes, but the issue wasn't surfaced by tests in our CI system, it is not the fault of the infrastructure change."** Colloquially (the book's canonical phrasing): **"If you liked it, then you shoulda put a test on it"** — and it must be a *CI* test specifically (an informal passage also phrases it "you should have put a CI test on it").

This is what makes sweeping change safe at scale: the team that owns a behavior must encode it as a CI test; infrastructure teams "do not need to worry about every unknown usage, only the ones that are visible in our CI systems." One-off bespoke tests outside CI "do not count."

## Trade-offs — "It depends" / nothing is free

- "As with effectively everything else in this book, it depends." "Rarely is there a one-size-fits-all solution in software engineering." There are no context-free **best practices**, only better and worse trade-offs *in context*.
- Every decision must reduce to **"We are doing this because we must"** or **"because it is the best option … based on current evidence"** — never **"because I said so."** "The goal is consensus, not unanimity."
- **Cost is multidimensional:** financial, resource (CPU/RAM), personnel (engineering effort), transaction (cost to act), opportunity (cost of *not* acting), and societal. "In highly creative and lucrative fields like software engineering, financial cost is usually not the limiting factor — personnel cost usually is."
- Decisions are revisited as evidence changes: "leaders who admit mistakes are more respected, not less." Even without data, "there might still be evidence, precedent, and argument … things that can't be measured may still have value."
- **The markers parable:** Google leaves closets of whiteboard markers unlocked because "it is far more important to optimize for obstacle-free brainstorming than to protect against someone wandering off with a bunch of markers." Optimize the expensive thing (people thinking), not the cheap thing.

## Shifting left — find problems earlier

> "finding problems earlier in the developer workflow usually reduces costs."

Along the conception → design → implementation → review → testing → commit → canary → production timeline, "the earlier we find a problem, the cheaper it is to fix it." This is the unifying economic argument behind code review, testing, static analysis, and design docs.

## The first change is the hardest

"Expect the first upgrade for a codebase to be significantly more expensive than later upgrades." The more frequently you exercise change (compiler upgrades, dependency bumps), the cheaper change becomes — practice builds the muscle. Five factors that make a codebase flexible: **Expertise, Stability, Conformity, Familiarity, Policy.** Beware the **boiled frog** of slowly-worsening build/test/upgrade times.

## Culture — people, not heroes

- **Genius is a myth.** "Software engineering is a team endeavor." "lone craftspeople are extremely rare — and even when they do exist, they don't perform superhuman achievements in a vacuum." "The vast majority of the work … doesn't require genius-level intellect, but 100% of the work requires a minimal level of social skills." The Genius Myth is "just another manifestation of our insecurity."
- **Don't hide.** Working alone maximizes risk of failure and forfeits growth: "Fail early, fail fast, fail often." "In Short, Don't Hide."
- **The three pillars — Humility, Respect, Trust (HRT):**
  - *Humility* — "You are not the center of the universe (nor is your code!). You're neither omniscient nor infallible."
  - *Respect* — "You genuinely care about others you work with."
  - *Trust* — "You believe others are competent and will do the right thing, and you're OK with letting them drive."
  - "If you perform a root-cause analysis on almost any social conflict, you can ultimately trace it back to a lack of humility, respect, and/or trust." First move: "Lose the ego" → a "collective ego."
- **Bus factor:** "the number of people that need to get hit by a bus before your project is completely doomed." Mitigate with documentation and a primary + secondary owner per area; fight knowledge silos.
- **Psychological safety** is "the most important part of an effective team" (Google's own research) and "the foundation for fostering a knowledge-sharing" culture. It's eroded by "feigned surprise" ("You don't know what X is?!").

## Code review — comprehension over correctness

- Reviews are **precommit**; the end goal is "to get another engineer to consent to the change" (**LGTM**). One LGTM is required by default.
- **"code itself is a liability."** "It might be a necessary liability, but by itself, code is simply a maintenance task to someone somewhere down the line." Writing new code from scratch is to be justified, not celebrated.
- **Code review is not primarily bug-finding:** "checking for code correctness is not the primary benefit … more importance is attached to ensuring that a code change is understandable and makes sense over time and as the codebase itself scales."
- Reviewers defer to the author's approach and "approve changes that improve the codebase rather than wait for consensus on a more 'perfect' solution." A reviewer "shouldn't propose alternatives because of personal opinion."
- Underrated benefit: **knowledge sharing.** "Code review is a perfect time for knowledge transfer: it is timely and actionable." Plus **consistency** and the durable fact that "code will be read many more times than it is written."
- **Readability certification:** a company-wide mentorship process certifying idiomatic code in a language, "first and foremost a mentoring and cooperative process, not a gatekeeping or adversarial one."

## Testing — why and how

- **Why:** "you can't rely on programmer ability alone to avoid product defects." (A 100-engineer team each shipping one bug/month ships ~5 bugs/workday.) But trust is fragile: **"A bad test suite can be worse than no test suite at all."**
- **Test sizes** are defined by *resources*, not lines: "small tests run in a single process, medium tests run on a single machine, and large tests run wherever they want." Always "write the smallest possible test." Small tests forbid sleeps, I/O, and blocking calls → fast + deterministic.
- **Test behaviors, not methods:** "rather than writing a test for each method, write a test for each behavior. A behavior is any guarantee that a system makes about how it will respond to a series of inputs while in a particular state." Express as **given / when / then.**
- **Strive for unchanging tests.** Four kinds of change: pure refactorings, new features, and bug fixes should *not* force test edits; only a real **behavior change** should — and that's "significantly more expensive than the other three."
- **Avoid brittleness:** test through **public APIs**, not implementation details ("accessing the system … in the same manner that its users would"). Prefer **state testing over interaction testing**; over-mocking causes brittleness.
- **DAMP, not (only) DRY in tests:** prefer **"Descriptive And Meaningful Phrases"** — "A little bit of duplication is OK in tests so long as that duplication makes the test simpler and clearer." Tests *should* break when behavior changes, so DRY's leverage is weaker there. DAMP complements DRY; it doesn't replace it.
- **Flakiness is a tax on trust:** even a ~0.15% flaky rate means thousands of false failures and erodes confidence in the whole suite.

## Knowledge sharing & documentation

- "Knowledge is viral, experts are carriers" — one expert answering in a shared forum upgrades a hundred engineers. Psychological safety is the precondition.
- **Documentation is like code:** "a tool, written in a different language (usually English) to accomplish a particular task." So docs should be under **source control**, have **clear owners**, be **reviewed** (and change *with* the code), have issues tracked, and be periodically evaluated. Ownerless docs go stale (the GooWiki cautionary tale — ~90% unviewed). Designate **canonical** docs. "Misleading information is worse than no information at all."

## Deprecation & dependencies — nothing lasts forever

- "All systems age." Deprecation rests on the premise that **code is a liability, not an asset** — "if code were an asset, why should we even bother … to turn down and remove obsolete systems?"
- But age ≠ obsolescence: "Just because something is old, it does not follow that it is obsolete." Deprecate systems that are *demonstrably obsolete* with a viable replacement; running two systems that do the same thing imposes compounding cost and "impedes the evolution of the newer system."
- **Dependencies aren't free.** Forking buys isolation but destroys scalability — "if every developer forks everything," a single security fix becomes hunting down every fork. Avoid forking cross-boundary interfaces (data structures, serialization, protocols).
- **Trunk-based development:** "new development must not have a choice when adding a dependency" — new code lands on trunk (flag-disabled if unfinished), not long-lived branches, which are "an awfully large tax" on large-scale changes (LSCs).
