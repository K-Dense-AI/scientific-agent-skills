# Design Types and the Replication Structure

Choosing the right design structure is mostly about matching the *unit of
randomization* and the *unit of replication* to your question, and respecting any
nesting in the analysis. This file walks through the standard structures and then
treats the single most common fatal error — pseudoreplication — in depth.

## Table of contents
- [Completely randomized design](#completely-randomized-design)
- [Randomized complete block design](#randomized-complete-block-design)
- [Latin square](#latin-square)
- [Repeated-measures and crossover](#repeated-measures-and-crossover)
- [Split-plot designs](#split-plot-designs)
- [Cluster / group-randomized designs](#cluster--group-randomized-designs)
- [Nested designs and pseudoreplication](#nested-designs-and-pseudoreplication)

## Completely randomized design

Units are assigned to treatments purely at random, no blocking. Simplest design;
appropriate when units are homogeneous and there's no identifiable nuisance factor.
Analyze with one-way ANOVA / regression. If units are *not* homogeneous, the
nuisance variation inflates error — block instead.

## Randomized complete block design

Group units into **blocks** of similar units (day, batch, litter), and randomize all
treatments *within* each block. Every treatment appears once per block. The
between-block variation is removed from the error term, sharply increasing precision
when blocks differ. Analyze with `treatment + block` in the model. This is the
default upgrade over a completely randomized design whenever a nuisance factor exists.

## Latin square

Controls **two** nuisance factors simultaneously with a square layout: each treatment
appears exactly once in every row and every column. Classic uses: row = day, column =
position/order, cell = treatment. Requires #treatments = #rows = #columns, and assumes
no interactions between the blocking factors and treatment. Efficient when both
nuisance dimensions matter and runs are limited. (Graeco-Latin squares extend this to
three nuisance factors.)

## Repeated-measures and crossover

Each subject receives more than one condition, serving as its own control. This
removes between-subject variation — usually the largest noise source — so these
designs are far more powerful per subject.

- **Repeated measures:** the same units measured under several conditions or over
  time.
- **Crossover:** each subject receives each treatment in sequence, with **washout**
  periods between to clear carry-over. Subjects are randomized to treatment *orders*
  (e.g. an AB/BA crossover; or a Williams square for ≥3 treatments to balance order).

Watch for:
- **Carry-over / residual effects** — an effect of the previous treatment persisting
  into the next period. Adequate washout is essential; otherwise the design is biased.
- **Period effects** — systematic change over time (learning, fatigue, disease
  progression). Balanced orders let you separate period from treatment.
- **Correlation within subject** — the repeated observations are not independent; the
  analysis must model it (mixed model / repeated-measures ANOVA). Sample-size/power
  for these depends on the within-subject correlation — use simulation in the
  **statistical-power** skill.

## Split-plot designs

Arises when some factors are **hard to change** (applied to large units) and others
are **easy to change** (applied to sub-units). The hard-to-change factor is randomized
to whole plots; the easy factor is randomized to subplots within each whole plot.
Example: oven temperature (whole plot — you can't re-set it per sample) × coating type
(subplot — applied per sample). Crucially there are **two different error terms** — one
for whole-plot factors, one for subplot factors — and the analysis must use both.
Treating a split-plot as a completely randomized factorial gives wrong (usually
anticonservative) tests for the whole-plot factor. Industrial DOE and agricultural
trials are full of accidental split-plots; recognize when a factor can't be reset per
run.

## Cluster / group-randomized designs

When the intervention is delivered to a *group* (a clinic's protocol, a classroom
curriculum, a village water supply), you can only randomize at the group level. The
**cluster is the unit of randomization**, and because members of a cluster are
correlated, it is effectively the unit of replication too.

- Power depends on the number of **clusters** far more than the number of individuals,
  and on the **intraclass correlation (ICC)**. Adding people to existing clusters
  helps much less than adding clusters.
- The **design effect** `DEFF = 1 + (m − 1)·ICC` (m = cluster size) quantifies how
  much the effective sample size shrinks; even a small ICC with large clusters costs
  dearly. Power these by simulation (see **statistical-power**).
- Analyze with a method that accounts for clustering (mixed model with a cluster
  random effect, or GEE). Analyzing individuals as independent is pseudoreplication.

## Nested designs and pseudoreplication

**Pseudoreplication** is treating non-independent measurements as independent
replicates. It is the most common and most damaging design error in experimental
biology, and it cannot be fixed after data collection — only by designing and
analyzing at the correct level.

The principle: **the replicate is whatever the treatment is independently applied
and randomized to.** Measurements taken below that level are *technical replicates* —
they improve the precision of a single unit's value but do **not** add degrees of
freedom for testing the treatment.

Worked examples:
- **One dish per treatment, 50 cells imaged.** Treatment applied to the dish ⇒ n = 1
  per treatment. The 50 cells describe that one dish; they are not 50 independent
  tests of the treatment. You need multiple independently treated dishes.
- **3 mice per group, 100 cells each.** n = 3 (mice) for a treatment given to the
  mouse, not 300 (cells). Average within mouse, or use a mixed model with mouse as a
  random effect.
- **One tank of fish given a diet, every fish measured.** The tank is the unit (the
  diet was randomized to the tank) ⇒ n = number of tanks, not number of fish. Shared
  tank water, temperature, and social effects make fish within a tank correlated.
- **Repeated measurements over time on the same subject** are nested within subject;
  the subject is the replicate.

How to avoid it:
1. **Identify the experimental unit** = the smallest physical entity to which a
   treatment level is independently and randomly assigned.
2. **Replicate at that level** — more independently treated units, not more
   measurements per unit (though technical replicates can reduce measurement noise).
3. **Analyze with the nesting respected** — average to the unit level, or fit a mixed
   model with random effects for the nesting (cells in mice, fish in tanks, time in
   subjects). The fixed-effect treatment test then uses the correct, larger error and
   correct degrees of freedom.

Technical replicates are still worth taking — they sharpen each unit's estimate — but
report and analyze them as what they are, never as independent biological replicates.
For sample size of nested/clustered designs, use simulation in **statistical-power**.
