# Clean Architecture (Robert C. Martin, 2017)

**Thesis:** Good architecture minimizes the lifetime cost of building and maintaining a system by keeping options open as long as possible — separating stable high-level policy from volatile low-level details so that details (database, web, framework) can be deferred, swapped, or changed without touching business rules.

---

## What this book makes you good at

- Structuring code so business rules never depend on databases, web frameworks, or UI technology
- Applying the SOLID principles at the class, component, and architectural level
- Drawing dependency boundaries that protect high-level policy from low-level volatility
- Measuring component stability (Fan-in / Fan-out / Instability metric) and placing components on or near the Main Sequence
- Recognizing when microservices, layers, or package structures are theatrical rather than architectural
- Designing systems that are testable without running a database, web server, or framework
- Deferring irreversible technology decisions (DB choice, framework) until the last responsible moment

---

## Core principles (actionable)

### Goal of Architecture

"The goal of software architecture is to minimize the human resources required to build and maintain the required system." (PAGE 30)

Architecture's primary purpose is to support the life cycle of the system: development, deployment, operation, and maintenance. Crucially, "the strategy behind that facilitation is to leave as many options open as possible, for as long as possible." (PAGE 148)

**Behavior vs. structure:** Software has two values. Behavior is urgent but not always important. Structure is important but never urgent. Developers must fight for structure because "if architecture comes last, then the system will become ever more costly to develop, and eventually change will become practically impossible." (PAGE 44) Eisenhower's matrix applies: don't let urgent-but-not-important features crowd out important-but-not-urgent architecture.

**The only way to go fast is to go well.** "Making messes is always slower than staying clean, no matter which time scale you are using." (PAGE 37)

---

### SRP: Single Responsibility Principle

**Common misconception:** SRP does not mean "a module should do one thing." That rule applies to functions, not modules.

**Correct definition:** "A module should be responsible to one, and only one, actor." (PAGE 81) An actor is a group of users or stakeholders who require the same kind of change.

**Symptoms of violation:**
- *Accidental duplication:* Two actors share code (e.g., `calculatePay()` and `reportHours()` share `regularHours()`). The CFO's team tweaks it; the COO's reports break silently.
- *Merges:* Two developers modify the same file for different actors; their changes collide.

**Solution:** Separate the data from the functions. Use separate classes for each actor's operations (PayCalculator, HourReporter, EmployeeSaver). Use a Facade class if callers need a single entry point. "The SRP says to separate the code that different actors depend on." (PAGE 2001)

**At scale:** SRP becomes the Common Closure Principle at the component level and the Axis of Change at the architectural level.

---

### OCP: Open-Closed Principle

"A software artifact should be open for extension but closed for modification." (PAGE 87)

The goal is that new requirements produce new code, not changes to existing code. "If simple extensions to the requirements force massive changes to the software, then the architects of that software system have engaged in a spectacular failure." (PAGE 87)

**How to achieve it:**
1. Apply SRP to identify separate responsibilities.
2. Apply DIP to organize dependency arrows so they point toward high-level policy.
3. Components that should be protected from change must be depended upon, not depending.

"If component A should be protected from changes in component B, then component B should depend on component A." (PAGE 91)

The Interactor (use case) is the most protected component because it contains the highest-level policy. Controllers depend on Interactors. Presenters depend on Controllers. Views depend on Presenters. Changes at the bottom cannot cascade upward.

---

### LSP: Liskov Substitution Principle

Barbara Liskov, 1988: every object of type S can be substituted for every object of type T in a program defined in terms of T, without changing the program's behavior.

**Square/Rectangle violation:** If `Square extends Rectangle` but `Square.setWidth()` also changes height, then code that assumes width and height are independent will behave incorrectly with a Square. The only fix is adding `instanceof` checks — a smell that types are not truly substitutable.

**Architectural scope:** LSP extends beyond inheritance. Any set of services or components that claim to implement the same interface must do so consistently. If a REST API for taxi dispatch allows one provider to use `dest` instead of `destination`, the entire dispatch module must be peppered with special cases. "A simple violation of substitutability can cause a system's architecture to be polluted with a significant amount of extra mechanisms." (PAGE 99)

**Rule of thumb:** If you need an `if (type == X)` guard around a call through an interface, the interface's contract is probably violated.

---

### ISP: Interface Segregation Principle

"This principle advises software designers to avoid depending on things that they don't use." (PAGE 79)

**Class level:** If `User1` depends only on `op1` of an `OPS` class, any change to `op2` forces `User1` to recompile/redeploy even though it has no interest in `op2`. Break the interface into `U1Ops`, `U2Ops`, `U3Ops`.

**Architectural level:** If a system S includes framework F which is bound to database D, then a change to D may force redeployment of F and S — even though S doesn't care about that part of D. "It is harmful to depend on modules that contain more than you need." (PAGE 102-103)

**ISP and CRP:** The Common Reuse Principle at the component level is the generic form of ISP: "Don't depend on things you don't need." (PAGE 121) If you depend on a component, you implicitly depend on every class in it.

---

### DIP: Dependency Inversion Principle

"The most flexible systems are those in which source code dependencies refer only to abstractions, not to concretions." (PAGE 104)

**Specific coding rules:**
- Don't refer to volatile concrete classes. Refer to abstract interfaces instead.
- Don't derive from volatile concrete classes. Inheritance is the strongest source-code coupling.
- Don't override concrete functions. Override the abstract declaration and provide multiple implementations.
- Never mention the name of anything concrete and volatile.

**Exception:** Stable platform facilities (e.g., `String` in Java) are concrete but acceptable to depend on because they never change.

**Factories:** Creating concrete objects requires a source-code dependency on the concrete type. Use Abstract Factory — an interface for creating objects plus a concrete implementation of that factory. Keep the factory implementation in a concrete component (usually `Main`). "DIP violations cannot be entirely removed, but they can be gathered into a small number of concrete components and kept separate from the rest of the system." (PAGE 107)

**Architectural implication:** DIP is what gives OOP its power for architects. Polymorphism means any source-code dependency can be inverted. "The software architect can point the source code dependency in either direction." (PAGE 68) This is what allows UI and Database to depend on business rules instead of the reverse.

---

### Component Cohesion: REP, CCP, CRP

**REP (Reuse/Release Equivalence Principle):** "The granule of reuse is the granule of release." Classes and modules that are grouped into a component must form a cohesive group with an overarching theme. Users need to know when releases are coming and what they contain.

**CCP (Common Closure Principle):** "Gather into components those classes that change for the same reasons and at the same times. Separate into different components those classes that change at different times and for different reasons." (PAGE 119) This is SRP restated for components. If a change touches only one component, only that component needs redeployment.

**CRP (Common Reuse Principle):** "Don't force users of a component to depend on things they don't need." (PAGE 120) Classes that are reused together belong together. When you depend on a component, you depend on all its classes — so don't put classes together that are not used together.

**The tension triangle:** REP and CCP are inclusive (bigger components). CRP is exclusive (smaller components).
- Focus only on REP + CCP → too many components impacted by any change.
- Focus only on CCP + REP → too many unneeded releases propagate.
- Focus only on REP + CRP → too many components broken by simple changes.

Early in a project, prefer CCP (develop-ability). As the project matures and is reused, migrate toward REP (reusability).

---

### Component Coupling: ADP, SDP, SAP

**ADP (Acyclic Dependencies Principle):** "Allow no cycles in the component dependency graph." (PAGE 124) Cycles create the "morning after syndrome": you can't build or test a component without building everything it transitively depends on. Break cycles by (1) applying DIP — create an interface that one component implements and the other depends on, or (2) create a new component that both components depend on.

**SDP (Stable Dependencies Principle):** "Depend in the direction of stability." (PAGE 115) A component intended to be easy to change must not be depended upon by stable (hard-to-change) components. Stability metric:
- Fan-in = number of incoming dependencies (classes outside the component that depend on classes inside)
- Fan-out = number of outgoing dependencies
- Instability I = Fan-out / (Fan-in + Fan-out); range [0,1]; 0 = maximally stable, 1 = maximally unstable

The I metric of a component should be larger than the I metrics of the components it depends on.

**SAP (Stable Abstractions Principle):** "A component should be as abstract as it is stable." (PAGE 139) Stable components (I = 0) should be abstract so they can be extended without modification. Unstable components (I = 1) should be concrete. SAP + SDP combined is the DIP applied at the component level.

**Main Sequence:** Plot components on a graph with Abstractness (A) on the vertical axis and Instability (I) on the horizontal axis. The ideal positions are (0,1) — maximally abstract and stable — and (1,0) — maximally concrete and unstable. The line connecting these points is the Main Sequence. Components near (0,0) are in the Zone of Pain (rigid, concrete, highly depended on — database schemas are the archetype). Components near (1,1) are in the Zone of Uselessness (abstract, but nobody uses them). Measure distance from Main Sequence: D = |A + I - 1|; components with D far from 0 need re-examination.

---

### The Dependency Rule (Clean Architecture)

The Clean Architecture organizes software into concentric circles:
1. **Entities** (innermost): Enterprise-wide critical business rules and data. Least likely to change.
2. **Use Cases**: Application-specific business rules. Orchestrates Entities to achieve use-case goals. Does not know about UI or database.
3. **Interface Adapters**: Converts data between use-case-convenient form and external-convenient form. Contains MVC, Presenters, Views. All SQL lives here.
4. **Frameworks and Drivers** (outermost): The web framework, database, devices. "The web is a detail. The database is a detail." (PAGE 207)

**The Dependency Rule:** "Source code dependencies must point only inward, toward higher-level policies." (PAGE 205) Nothing in an inner circle can mention anything in an outer circle — no names, no classes, no function signatures, no data formats from outer circles.

**Crossing boundaries:** When a use case must call a Presenter (outward), use DIP. The use case calls an output-port interface defined in the inner circle; the Presenter (in the outer circle) implements it. Data crossing a boundary must be simple structures — plain old data transfer objects — not database rows or Entity objects.

**Entities vs. Use Cases distinction:** Entities know nothing of use cases. Use cases know about Entities. Entities are higher-level because they are more general (usable across many applications); use cases are more specific (tied to a single application). Level = "distance from inputs and outputs" — the farther a policy is from IO, the higher its level. (PAGE 189)

---

### Screaming Architecture

"Your architecture should tell readers about the system, not about the frameworks you used in your system." (PAGE 202)

When you look at the top-level directory structure, it should scream "Health Care System" or "Inventory Management System," not "Rails" or "Spring/Hibernate." Use cases are first-class entities visible at the top level. Frameworks are tools, not architectures. "Look at each framework with a jaded eye… Think about how you can preserve the use-case emphasis of your architecture." (PAGE 201)

If your architecture is use-case-centered and frameworks are at arm's length, you should be able to unit-test all use cases without any framework running — no web server, no database.

---

### The Humble Object Pattern

Split behaviors into two classes: a Humble Object (hard to test — e.g., the View that pushes strings into HTML) and a Testable Object (e.g., the Presenter that formats data into strings and booleans in a ViewModel). The Presenter is thoroughly testable; the View is trivially simple.

This pattern appears at every architectural boundary. Database gateways are Humble Objects (they call SQL); Use Case Interactors are the testable partners. ORMs (better called "data mappers") are Humble Objects that live in the database layer.

---

### Details: Database, Web, Frameworks, Main

**Database is a detail:** "From an architectural point of view, the database is a non-entity." (PAGE 265) The data model is architecturally significant; the database technology is not. The business rules should access data only through interfaces (e.g., `UserGateway.getLastNamesOfUsersWhoLoggedInAfter(date)`). SQL must not appear in use-case code. The FitNesse project ran for 18 months without a real database, using in-memory stubs, then flat files — delaying the decision until it was almost irrelevant.

**Web is a detail:** "The GUI is a detail. The web is a GUI. So the web is a detail." (PAGE 274) The web is an IO device. Architectures from the 1960s taught us the value of device independence; the lesson hasn't changed. Business logic should be expressible as a suite of use cases operable from a console, web, thick client, or service without architectural changes.

**Frameworks are details:** Don't marry a framework. "The framework author makes no commitment to you whatsoever." (PAGE 276) Frameworks may ask you to derive from their base classes — don't. Instead, derive proxies in plugin components. Spring annotations belong in Main, not in business objects. Use frameworks as tools kept in the outer circles of the architecture.

**Main is the ultimate detail:** Main is the dirtiest, lowest-level component. It creates all Factories, injects all dependencies, gathers all external resources, and then hands control to the high-level policy. Main is a plugin to the application — you can have one Main for Dev, one for Test, one for Production. "Think of Main as the dirtiest of all the dirty components." (PAGE 229)

---

### Services are not automatically Architecture

Services (micro-services, SOA) are just function calls across process/network boundaries. "The architecture of a system is defined by the boundaries that separate high-level policy from low-level detail and follow the Dependency Rule. Services that simply separate application behaviors are little more than expensive function calls." (PAGE 234)

**The Kitty Problem:** If your micro-services are decomposed by function (TaxiFinder, TaxiSelector, TaxiDispatcher), a new cross-cutting feature (kitten delivery) touches all of them. Services can be strongly coupled through shared data and cross-cutting concerns regardless of network separation. Well-designed services should have internal component architectures following the Dependency Rule, with polymorphic extension points for new features.

---

### Keeping Options Open / Deferring Decisions

The architect's primary tool is the boundary: "You draw lines between things that matter and things that don't." (PAGE 173)

A good architect maximizes the number of decisions not made — or defers them. Early in a project you don't know enough. Boundaries keep the high-level policy agnostic about:
- Which database (relational, NoSQL, flat files)
- Whether the system is delivered over the web
- Which web framework is used
- Whether to use REST, SOA, microservices
- How dependencies are injected

The longer you wait, the more information you have. A premature decision to adopt microservices (company P example) multiplied development effort enormously for a server farm that never existed.

---

## Chapter map

| Part/Chapter | Title | Problem it solves |
|---|---|---|
| Ch 1 | What Is Design and Architecture? | Defines the goal: minimize lifetime human cost of system |
| Ch 2 | A Tale of Two Values | Why architecture (structure) outranks behavior when they conflict |
| Ch 3 | Paradigm Overview | How structured, OO, functional paradigms relate to architecture |
| Ch 4 | Structured Programming | Why functional decomposition and testability stem from structured programming |
| Ch 5 | Object-Oriented Programming | How polymorphism enables dependency inversion; OO = control over source-code dependencies |
| Ch 6 | Functional Programming | Immutability eliminates concurrency bugs; segregate mutable/immutable components |
| Ch 7 | SRP | How to separate code by actor to prevent accidental coupling between departments |
| Ch 8 | OCP | How to protect high-level policy from change by arranging dependency hierarchy |
| Ch 9 | LSP | How to design substitutable types at class and architectural (REST service) level |
| Ch 10 | ISP | How depending on fat interfaces causes unnecessary coupling and redeployment |
| Ch 11 | DIP | How to structure source-code dependencies against flow of control using abstraction |
| Ch 12 | Components | What components are (units of deployment); history of relocatable binaries |
| Ch 13 | Component Cohesion | REP/CCP/CRP: which classes belong together; the tension triangle |
| Ch 14 | Component Coupling | ADP (no cycles), SDP (depend toward stability), SAP (stable = abstract), Main Sequence |
| Ch 15 | What Is Architecture? | Architecture serves development, deployment, operation, maintenance; keep options open |
| Ch 16 | Independence | How to decouple layers and use cases for independent develop-ability and deployability |
| Ch 17 | Boundaries: Drawing Lines | How to draw boundary lines (between business rules and DB, GUI, etc.) |
| Ch 18 | Boundary Anatomy | Monoliths, deployment components, local processes, services — costs and speeds |
| Ch 19 | Policy and Level | Level = distance from IO; source-code deps must follow level, not data flow |
| Ch 20 | Business Rules | Entities (critical business rules) vs. Use Cases (application-specific rules) |
| Ch 21 | Screaming Architecture | Architecture should express use cases, not frameworks |
| Ch 22 | The Clean Architecture | The four concentric circles; the Dependency Rule |
| Ch 23 | Presenters and Humble Objects | How to make hard-to-test boundaries testable by splitting humble/testable behavior |
| Ch 24 | Partial Boundaries | When to implement a partial boundary instead of a full one (YAGNI vs. future cost) |
| Ch 25 | Layers and Boundaries | Multiple streams of data flow; when to add architectural boundaries |
| Ch 26 | The Main Component | Main as plugin and ultimate detail; how to inject dependencies |
| Ch 27 | Services: Great and Small | Why services are not architecture by themselves; the Kitty Problem |
| Ch 28 | The Test Boundary | Tests as outermost circle; avoiding fragile tests through a testing API |
| Ch 29 | Clean Embedded Architecture | HAL, OSAL, PAL patterns for embedded systems; firmware vs. software |
| Ch 30 | The Database Is a Detail | Database is a mechanism, not an architectural element |
| Ch 31 | The Web Is a Detail | Web is an IO device; business rules must be web-agnostic |
| Ch 32 | Frameworks Are Details | Don't marry frameworks; keep them in outer circles |
| Ch 33 | Case Study: Video Sales | End-to-end example applying SRP, Dependency Rule, component architecture |
| Ch 34 | The Missing Chapter | Package-by-layer vs. package-by-feature vs. ports-and-adapters vs. package-by-component; encapsulation matters |
| App A | Architecture Archaeology | 45-year project history showing how architectural principles were discovered empirically |

---

## Problem -> where to look

| Engineering problem | Book section (page) |
|---|---|
| Business rules breaking when DB schema changes | Ch 17 Boundaries: Drawing Lines (PAGE 174-176); Ch 30 Database Is a Detail (PAGE 265) |
| Tests that break whenever the GUI or DB changes | Ch 28 Test Boundary (PAGE 244); Ch 23 Humble Object (PAGE 210) |
| Feature changes touching many unrelated components | Ch 7 SRP / Ch 13 CCP (PAGE 119); Ch 27 Services / Kitty Problem (PAGE 236) |
| Can't deploy one component without redeploying everything | Ch 14 ADP — break cycles (PAGE 124); Ch 16 Independence (PAGE 158) |
| Stable component being dragged into changes by a volatile one | Ch 14 SDP (PAGE 132-133) |
| A stable component can't be extended without modification | Ch 14 SAP (PAGE 139); Ch 8 OCP (PAGE 87) |
| How to decide what goes in which component | Ch 13 REP/CCP/CRP tension triangle (PAGE 121-122) |
| Framework wants me to derive my entities from its base classes | Ch 32 Frameworks Are Details (PAGE 275); Ch 22 Clean Architecture (PAGE 204) |
| Where should SQL / database queries live? | Ch 22 Interface Adapters layer (PAGE 206); Ch 23 Database Gateways (PAGE 212) |
| How to structure code to be testable without a running server | Ch 21 Screaming Architecture (PAGE 202); Ch 22 Dependency Rule (PAGE 205) |
| Microservice decomposition causing cross-cutting coupling | Ch 27 Services: Kitty Problem (PAGE 235-238) |
| Where to put dependency injection / factory logic | Ch 11 DIP Factories (PAGE 106-107); Ch 26 Main Component (PAGE 228) |
| How to decide what is an Entity vs. a Use Case | Ch 20 Business Rules (PAGE 193-198) |
| Deciding whether to draw an architectural boundary or not | Ch 25 Layers and Boundaries — inflection point (PAGE 227) |
| Package organization doesn't enforce architecture | Ch 34 Missing Chapter — Organization vs. Encapsulation (PAGE 297) |
| Embedded code tightly coupled to hardware | Ch 29 Clean Embedded — HAL/OSAL (PAGE 253-261) |

---

## Convergences & debates

### Agrees with

**The Pragmatic Programmer:** Both emphasize avoiding tight coupling to specific technologies (databases, frameworks). Hunt/Thomas's "orthogonality" is structurally identical to Martin's dependency inversion — keep concerns separated so a change in one place doesn't cascade. Both stress DRY; Ch 29 explicitly cites Pragmatic Programmer on DRY.

**Software Engineering at Google:** Both books acknowledge that architecture must serve team structure (Conway's Law, Ch 16). Both emphasize that testability is not optional and must be designed in. SEaT Google's "large-scale changes" problem is exactly what the Dependency Rule is designed to prevent: if all source-code deps point inward, refactoring inner rings is possible without touching outer rings.

**Code Complete:** Both stress separation of concerns and modular design. Code Complete's "cohesion" concept maps to REP/CCP/CRP. Both books believe that design quality is measurable (Martin has stability/abstractness metrics; McConnell has coupling/cohesion classifications).

**DDIA (Designing Data-Intensive Applications):** Both recognize that the data model is architecturally significant but the storage mechanism is not. Martin's "database is a detail" aligns with Kleppmann's advice to choose storage for access patterns, not for prestige.

### Key disagreements

**vs. A Philosophy of Software Design (Ousterhout / APOSD):**

This is the most significant tension in the book set.

- **APOSD** argues for *deep modules*: prefer fewer, wider interfaces that hide complexity. A module with a simple interface but rich implementation is good. It explicitly warns against "classitis" — the proliferation of tiny, shallow classes that fragment logic and increase cognitive load.
- **Clean Architecture / SOLID** consistently pushes in the opposite direction: many small classes, each with a single responsibility, each depending only on abstractions. The SRP, ISP, and DIP all favor splitting rather than consolidating.

Martin's canonical Employee class splits into three separate classes (PayCalculator, HourReporter, EmployeeSaver) to honor SRP — but each of those classes becomes shallow (a few methods) and requires a Facade to use together. Ousterhout would call these shallow modules and argue the Facade merely adds indirection while hiding nothing.

The disagreement is real and architectural: Martin's approach favors flexibility for future change (easy to plug in a new persistence implementation); Ousterhout's favors present cognitive simplicity (the user of a module need not know about many collaborators). Neither is purely right — the tradeoff depends on how often the boundary will actually be crossed.

- **Comments:** APOSD says comments are essential documentation that captures design rationale invisible in code. Clean Code (Martin's companion book) says comments are failures. Clean Architecture is less strident but shares the view that self-documenting code is preferred.

**vs. Clean Code (Martin's own earlier book):**

Clean Architecture explicitly corrects the overemphasis on function-level cleanliness: "A function should do one, and only one, thing... But it is not one of the SOLID principles — it is not the SRP." (PAGE 80) Clean Architecture argues that function-level decomposition is insufficient; component-level and architectural-level structure are where the real design decisions live. Clean Architecture is the more mature, higher-altitude view.

**vs. The Pragmatic Programmer on abstractions:**

Hunt/Thomas warn against premature abstraction (YAGNI, tracer bullets, avoid speculative generality). Martin's Clean Architecture recommends drawing boundaries early (interfaces between business rules and DB/web) even before you know which DB you'll use. Ch 24 (Partial Boundaries) directly acknowledges this tension and argues that a partial boundary (reciprocal interfaces in place but deployed together) is a reasonable hedge against YAGNI while preserving the option to separate later.

**On microservices:**

Martin is iconoclastic here. He argues that microservices are not architecturally significant by themselves — they are just function calls across network boundaries. The architecture lives in the boundaries within services (Dependency Rule, component structure), not in the service-level decomposition. This directly challenges the mainstream microservices narrative that decomposing by service automatically provides decoupling and independent deployability. Ch 27 (Kitty Problem) is the most direct refutation available in print of naive service-level decomposition.
