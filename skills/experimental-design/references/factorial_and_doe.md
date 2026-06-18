# Factorial and Design-of-Experiments (DOE)

When several factors might affect a response, testing them **one factor at a time
(OFAT)** is both wasteful and blind to interactions. Factorial designs vary factors
*together*, so you estimate every main effect and interaction from the same runs,
with better precision per run. This file covers the family of DOE designs and the
concepts (resolution, aliasing) needed to read them. Generate them with
`scripts/doe_designs.py`.

## Table of contents
- [Why factorial beats OFAT](#why-factorial-beats-ofat)
- [Full factorial (2^k)](#full-factorial)
- [Fractional factorial (2^(k-p))](#fractional-factorial)
- [Resolution and aliasing](#resolution-and-aliasing)
- [Screening designs (Plackett-Burman)](#screening-designs)
- [Response-surface designs](#response-surface-designs)
- [Space-filling designs](#space-filling-designs)
- [Choosing a design](#choosing-a-design)

## Why factorial beats OFAT

Vary one factor while holding others fixed and you (1) spend runs inefficiently and
(2) can never see **interactions** — cases where the effect of A depends on the level
of B, which are the rule, not the exception, in real systems. A factorial varies all
factors simultaneously across runs; each effect is estimated using *all* the data, so
a 2^k factorial is more precise than k separate OFAT studies of the same size.

## Full factorial

A **2^k** design runs every combination of k factors at two levels (low/high, coded
−1/+1). It estimates all k main effects and all 2^k − k − 1 interactions.

- Runs = 2^k: 8 for 3 factors, 16 for 4, 32 for 5. Practical to ~5 factors.
- Use when you have a handful of factors and want a full picture including
  interactions.
- `two_level_factorial({"temp": (20,60), "conc": (1,10), "pH": (6,8)})` → 8 runs.
- For factors with more than two levels, use `full_factorial` with explicit level
  lists (runs = product of level counts — grows fast).

Add **center points** (all factors at their midpoint) to a two-level design to get a
cheap check for curvature: if the center response departs from the factorial average,
a linear model is inadequate and you need a response-surface design.

## Fractional factorial

When k is large, 2^k is too many runs — but most high-order interactions are
negligible (the *sparsity-of-effects* principle). A **2^(k−p)** fractional factorial
runs a carefully chosen fraction (1/2, 1/4, ...) of the full design, trading the
ability to estimate some interactions for far fewer runs.

- `fractional_factorial(factors, generator="a b c abc")` builds a half-fraction of 4
  factors in 8 runs. The generator string (Yates notation) assigns each factor to a
  column; a multi-letter token aliases that factor with an interaction.
- The price is **aliasing**: some effects become indistinguishable. You must know
  which.

## Resolution and aliasing

**Aliasing** (confounding) means two effects are estimated by the same contrast — the
data cannot separate them. Which effects are aliased is summarized by the design's
**resolution**:

| Resolution | Aliasing | Interpretation |
|------------|----------|----------------|
| **III** | main effects aliased with 2-factor interactions | Screening only; a "significant" main effect might be an interaction |
| **IV** | main effects clear of 2FI, but 2FIs aliased with each other | Good for screening; main effects trustworthy |
| **V** | main effects and 2FIs all clear of each other (aliased with 3FI+) | Can model main effects and 2-factor interactions confidently |

Always state the resolution and inspect the alias structure before interpreting a
fractional design. Concluding "factor C has no effect" is unsafe if C is aliased with
a real interaction (it could cancel out). When in doubt, choose a higher-resolution
generator (more runs) or add runs to **de-alias** (fold-over / augment the design).

## Screening designs

When the goal is to **find the vital few** factors out of many (5, 10, 20+), use a
screening design that estimates main effects only, as cheaply as possible:
- **Plackett-Burman** (`plackett_burman`): runs = the next multiple of 4 above k
  (e.g. 12 runs for up to 11 factors). Resolution III — two-factor interactions are
  heavily confounded with main effects. Perfect for triage: run it, keep the few
  factors with large effects, then study those with a full or higher-resolution
  factorial.
- Resolution III fractional factorials serve the same purpose.

Screen first, optimize later — don't try to learn interactions and find the optimum
in one cheap design.

## Response-surface designs

Two-level designs fit only a flat (linear + interaction) model; they cannot locate an
interior optimum or describe **curvature**. To fit a quadratic and optimize, use a
response-surface methodology (RSM) design over continuous factors:

- **Central composite design (CCD)** (`central_composite`): a 2^k factorial + center
  points + axial ("star") points. The axial points add the levels needed to estimate
  quadratic terms. With `face="circumscribed"` (default) the axial points sit
  *outside* the factorial box (so actual factor levels exceed your stated low/high);
  use `face="inscribed"` or `"faced"` to keep everything within the original range.
- **Box-Behnken** (`box_behnken`, needs ≥3 factors): a quadratic design that avoids
  the extreme all-low/all-high corners — useful when those corners are unsafe,
  expensive, or infeasible. More economical than a CCD for 3–5 factors.

Workflow: screen → factorial (find important factors & rough region) → response
surface (model curvature, locate optimum), often moving the experimental region
between steps (path of steepest ascent).

## Space-filling designs

For **computer experiments / simulations** (deterministic or expensive models) where
classical replication and blocking don't apply, you want even coverage of a
high-dimensional input space:
- **Latin hypercube** (`latin_hypercube`): each factor's range is divided into
  n_samples equal bins, sampled once each, arranged to spread points apart
  (`criterion="maximin"`). Gives good coverage with relatively few points and is the
  standard input design for surrogate/emulator modeling and sensitivity analysis.

## Choosing a design

| Goal | Factors | Design | Script function |
|------|---------|--------|-----------------|
| Screen many factors | 5–20+ | Plackett-Burman / Res III | `plackett_burman` |
| Main effects, some interactions, few runs | 4–8 | Res IV/V fractional | `fractional_factorial` |
| All effects + interactions | 2–5 | Full 2^k factorial | `two_level_factorial` |
| Multi-level categorical | few | Full factorial | `full_factorial` |
| Optimize a response (curvature) | 2–5 | Central composite / Box-Behnken | `central_composite`, `box_behnken` |
| Cover a simulation input space | any | Latin hypercube | `latin_hypercube` |

In all cases, **randomize run order** (the scripts do by default) so factors aren't
confounded with time-related drift, and add center points to two-level designs as a
curvature check.
