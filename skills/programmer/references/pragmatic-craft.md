# The Pragmatic Programmer — Craft, Attitude & Process

Andrew Hunt & David Thomas, *The Pragmatic Programmer* (Addison-Wesley, 1999). This catalog covers the **professional / human / workflow** side. The *design mechanics* (DRY, orthogonality, Demeter, design-by-contract, crash-early, exceptions, resource balancing, refactoring, tracer bullets, metadata) live in `pragmatic-design.md`. Numbered **Tips** are quoted verbatim.

## The pragmatic philosophy

- **Tip 1 — Care About Your Craft.** "there is no point in developing software unless you care about doing it well."
- **Tip 2 — Think! About Your Work.** "an ongoing critical appraisal of every decision you make, every day… Never run on auto-pilot."
- Traits of a pragmatic programmer: early adopter / fast adapter, inquisitive, critical thinker (smells a challenge in "that's the way it's done"), realistic, jack-of-all-trades.
- Continuous refinement (kaizen / Eton lawns): "Great lawns need small amounts of daily care, and so do great programmers."

## Take responsibility — "The Cat Ate My Source Code"

- "taking responsibility for yourself and your actions" is a cornerstone. A pragmatic programmer "isn't afraid to admit ignorance or error."
- "Responsibility is something you actively agree to." You may decline an impossible assignment, but once you accept, "you should expect to be held accountable."
- **Tip 3 — Provide Options, Don't Make Lame Excuses.** Before saying it can't be done, run the conversation in your head (or tell the rubber duck): does the excuse sound reasonable or stupid? "Instead of excuses, provide options. Don't say it can't be done; explain what *can* be done."

## Don't live with broken windows (the attitude)

- Software rot is driven by "the psychology, or culture, at work on a project." One unrepaired broken window "instills a sense of abandonment" and decay accelerates.
- **Tip 4 — Don't Live with Broken Windows.** "Fix each one as soon as it is discovered. If there is insufficient time to fix it properly, then board it up" — comment it out, mark "Not Implemented," or stub it. "Neglect accelerates the rot faster than any other factor." (Mechanics overlap `pragmatic-design.md`; the point *here* is the culture.)

## Be a catalyst; watch the big picture — "Stone Soup and Boiled Frogs"

- **Tip 5 — Be a Catalyst for Change.** "You can't force change on people. Instead, show them how the future might be and help them participate in creating it." Build a small good thing, demo it, and "people find it easier to join an ongoing success." ("It's easier to ask forgiveness than to get permission.")
- **Tip 6 — Remember the Big Picture.** "Don't be like the frog" in slowly-heated water. "Most software disasters start out too small to notice… It's often the accumulation of small things that breaks morale and teams." Distinction from broken windows: there people *lose the will* to fight rot; the frog simply *doesn't notice*.

## Good-enough software — quality is a requirement

- "the real world just won't let us produce much that's truly perfect." But "good enough" is **never** sloppy — "All systems must meet their users' requirements."
- **Involve the user in the trade-off:** how good they want it is *their* call. It's unprofessional both to "polish up the code just one more time" against their needs and to "cut basic engineering corners to meet a deadline."
- **Tip 7 — Make Quality a Requirements Issue.** "The scope and quality of the system you produce should be specified as part of that system's requirements." Often "great software today is preferable to perfect software tomorrow."
- **Know when to stop.** Programming is like painting: "Don't spoil a perfectly good program by overembellishment and overrefinement… It may not be perfect. Don't worry: it could never be perfect." ("Striving to better, oft we mar what's well." — *King Lear*.)

## Your knowledge portfolio — invest in yourself

Your knowledge and experience are "expiring assets." Manage them like a financial portfolio: invest **regularly** (the habit matters more than the amount), **diversify**, **manage risk** (mix safe standards with high-reward bets), **buy low / sell high** (learn emerging tech early), and **review & rebalance**.

- **Tip 8 — Invest Regularly in Your Knowledge Portfolio.** "Make learning a habit."
- Concrete goals: **learn at least one new language every year**; **read a technical book each quarter** (then a book a month, then branch out); read **nontechnical** books too ("computers are used by people"); take classes; **join local user groups** ("Isolation can be deadly to your career"); experiment with different environments; stay current.
- **Tip 9 — Critically Analyze What You Read and Hear.** "Don't be swayed by vendors, media hype, or dogma." "Never underestimate the power of commercialism."

## Communicate!

"A good idea is an orphan without effective communication." "It's not just what you've got, but also how you package it."

- **Know what you want to say** (plan, outline, refine). **Know your audience** — "You're communicating only if you're conveying information."
- **The WISDOM acrostic:** **W**hat do you want them to learn? Their **I**nterest? How **S**ophisticated? How much **D**etail? Whom do you want to **O**wn it? How do you **M**otivate them to listen?
- **Choose your moment**, **choose a style**, **make it look good**, **involve your audience** (share drafts), **be a listener** ("if you want people to listen to you: listen to them"), **get back to people** ("E-mail is forever").
- **Tip 10 — It's Both What You Say and the Way You Say It.**

## Estimating

- **Tip 18 — Estimate to Avoid Surprises.** "Estimate before you start. You'll spot potential problems up front." All answers are estimates; first ask the *context* (ballpark vs. high-accuracy).
- **Units convey accuracy.** Quote 1–15 days in days, 3–8 weeks in weeks, 8–30 weeks in months, 30+ weeks "think hard." 125 working days → "about six months," not "125 days."
- Estimates come from **models** — best trick: "ask someone who's already done it." Break the system into components, identify the high-impact parameters, run multiple calculations, and "keep track of your estimating prowess." When asked on the spot: **"I'll get back to you."**
- **Tip 19 — Iterate the Schedule with the Code.** "the only way to determine the timetable for a project is by gaining experience on that same project."

## Debugging — the mindset

Debugging "is just problem solving"; attack it as such, without denial, finger-pointing, or apathy.

- **Tip 24 — Fix the Problem, Not the Blame.** "It doesn't really matter whether the bug is your fault or someone else's. It is still your problem."
- **Tip 25 — Don't Panic.** "the first rule of debugging." "Don't waste a single neuron on the train of thought that begins 'but that can't happen' because quite clearly it can, and has." Always find the **root cause**, not just this appearance.
- Gather data accurately: compile with **warnings at maximum** first ("don't waste time finding a problem the compiler could find for you"); interview/watch the user (the brush-stroke story); make the bug **reproducible**, ideally with a single command. **Rubber-duck** it — verbalizing assumptions surfaces the bug.
- **Tip 26 — "select" Isn't Broken.** "It is rare to find a bug in the OS or the compiler… The bug is most likely in the application." "If you see hoof prints, think horses — not zebras." If you changed one thing and it broke, that one thing is the suspect.
- **Tip 27 — Don't Assume It — Prove It.** "Prove it in *this* context, with *this* data, with *these* boundary conditions." Then ask *why it wasn't caught earlier*, add a test, and check whether the same bug lives elsewhere. "The amount of surprise you feel when something goes wrong is directly proportional to the … trust and faith you have in the code."

## Ubiquitous automation

- **Tip 61 — Don't Use Manual Procedures.** "People just aren't as repeatable as computers are." Scripts give **consistency and repeatability** and go under source control. Automate the build, tests, nightly builds (run *all* tests), site generation, and approval workflows. "Let the computer do the repetitious… we've got more important things to do." ("The cobbler's children have no shoes.")

## Pragmatic paranoia & ruthless testing

- **Tip 30 — You Can't Write Perfect Software.** "Accept it as an axiom of life." Code **defensively** — and "they don't trust themselves, either."
- "Most developers hate testing… Pragmatic Programmers are different. We are driven to find our bugs *now*, so we don't have to endure the shame of others finding our bugs later." Testing is **more cultural than technical**.
- **Tip 49 — Test Your Software, or Your Users Will.**
- **Tip 62 — Test Early. Test Often. Test Automatically.** "Tests that run with every build are much more effective than test plans that sit on a shelf."
- **Tip 63 — Coding Ain't Done 'Til All the Tests Run.**
- **Tip 64 — Use Saboteurs to Test Your Testing.** Deliberately introduce the bug and confirm the test complains.
- **Tip 65 — Test State Coverage, Not Code Coverage.** "What is important is the number of states that your program may have."
- **Tip 66 — Find Bugs Once.** "Once a human tester finds a bug, it should be the *last* time a human tester finds that bug" — add the automated test so it can never recur.

## Other professional tips worth keeping

- **Tip 20 — Keep Knowledge in Plain Text.** It won't go obsolete; it leverages your work.
- **Tip 22 — Use a Single Editor Well.** "an extension of your hand."
- **Tip 23 — Always Use Source Code Control.** "a time machine for your work."
- **Tip 50 — Don't Use Wizard Code You Don't Understand.** "no one should be producing code they don't fully understand."
- **Tip 57 — Some Things Are Better Done than Described.** Don't fall into the specification spiral.
- **Tip 60 — Organize Teams Around Functionality.** "Build teams the way you build code."
- **Tip 69 — Gently Exceed Your Users' Expectations.** Understand their expectations, "then deliver just that little bit more."
- **Tip 70 — Sign Your Work.** "Craftsmen of an earlier age were proud to sign their work. You should be, too."
