---
name: experimental-design
description: Design experiments and studies BEFORE data is collected — choosing a design, randomizing, blocking, and laying out treatment combinations so the results will actually be interpretable. Use whenever someone is planning a study, asks how to assign subjects/samples to groups, mentions randomization, blocking, stratification, controls, factorial or fractional-factorial designs, design of experiments (DOE), screening many factors, response-surface optimization, crossover or repeated-measures or split-plot designs, cluster/group randomization, Latin squares, plate layouts, batch/run-order effects, replication vs. pseudoreplication, or sequential/adaptive/group-sequential designs. Trigger this even for informal phrasings like "how should I set up this experiment", "how do I avoid confounding", "what's the best way to test these 6 factors", or "assign these mice to conditions". For computing the sample size or power once the design is chosen, use statistical-power; for analyzing data already collected, use statistical-analysis.
allowed-tools: Read Write Edit Bash
compatibility: Requires Python >=3.10. Scripts use numpy, pandas, and pyDOE3 (DOE matrices). Install with uv as shown below.
license: MIT license
metadata: {"version": "1.0", "skill-author": "K-Dense Inc."}
---

# Experimental Design

## Overview

The design of a study — how units are assigned to conditions, what is held constant, what is varied, and in what structure — determines what questions the data can answer. No analysis can rescue a confounded or pseudoreplicated design after the fact. This skill is about the decisions made *before* data collection: picking a design that isolates the effect of interest, randomizing to license causal claims, blocking to remove known nuisance variation, and structuring multi-factor experiments so effects are estimable rather than tangled together.

The three ideas behind almost every good design (Fisher's principles):
- **Randomization** — assign treatments at random so that confounders, known and unknown, are balanced in expectation. This is what turns a comparison into a causal claim.
- **Replication** — independent repetition at the right level, so you can estimate variability and your effects aren't artifacts of a single unit. The most common fatal error is **pseudoreplication**: counting repeated measurements on the same unit as independent replicates.
- **Blocking / local control** — group similar units (by batch, day, site, litter) and randomize within blocks, removing that nuisance variation from the error term instead of letting it inflate noise.

This skill helps you choose among design types, generate the actual randomization or DOE layout (with reproducible scripts), and avoid the structural mistakes that make data uninterpretable.

## When to Use This Skill

- Planning any comparative experiment or trial and deciding how to assign units
- Randomizing subjects/samples to arms (simple, blocked, stratified, or cluster)
- Removing nuisance variation by blocking or stratification
- Designing multi-factor experiments: full or fractional factorial, screening designs
- Optimizing a response over continuous factors (response-surface designs)
- Within-subject / repeated-measures, crossover, split-plot, or Latin-square designs
- Cluster- or group-randomized designs (sites, clinics, classrooms, litters)
- Deciding the number and level of replicates and avoiding pseudoreplication
- Sequential, group-sequential, or adaptive designs with interim analyses
- Laying out plates/batches and randomizing run order to defeat drift

## Installation

```bash
uv pip install "numpy>=1.26" "pandas>=2.0" pyDOE3
```

`pyDOE3` is the maintained successor to pyDOE/pyDOE2 and supplies factorial,
fractional-factorial, Plackett-Burman, central-composite, Box-Behnken, and
Latin-hypercube generators. The bundled scripts wrap it to return designs in real
factor units with named columns and randomized run order.

---

## Choosing a design

Start from the question and the structure of your units, not from a favorite design.

```
What are you trying to learn?
│
├─ Compare a few predefined conditions (A vs B vs C)?
│   ├─ Units independent, possibly with a known nuisance factor (day, batch, site)?
│   │     → Completely randomized (no nuisance) or RANDOMIZED BLOCK design.
│   ├─ Each unit can receive every condition in sequence (washout possible)?
│   │     → CROSSOVER / repeated-measures design (more power, watch carry-over).
│   └─ You can only randomize groups, not individuals (schools, clinics)?
│         → CLUSTER-randomized design (analyze at the cluster level; see pseudoreplication).
│
├─ Screen MANY factors (5+) to find the few that matter?
│     → FRACTIONAL FACTORIAL or PLACKETT-BURMAN screening design.
│
├─ Quantify main effects AND interactions among a handful of factors?
│     → FULL 2^k FACTORIAL design.
│
├─ Find the settings that OPTIMIZE a response (curvature matters)?
│     → RESPONSE-SURFACE design: central composite or Box-Behnken.
│
└─ Explore a simulation/computer model over a continuous space?
      → SPACE-FILLING design: Latin hypercube.
```

Detailed guidance per branch:
- **Randomization, blocking, stratification, controls** → `references/randomization_and_blocking.md`
- **Factorial, fractional-factorial, screening, response-surface, DOE concepts (aliasing, resolution)** → `references/factorial_and_doe.md`
- **Crossover, repeated-measures, split-plot, Latin-square, cluster, nested designs** → `references/design_types.md`
- **Sequential, group-sequential, and adaptive designs (interim analyses)** → `references/sequential_and_adaptive.md`

---

## Generating the design

Two scripts produce ready-to-use, reproducible layouts. Run them from the skill's
`scripts/` directory or add it to `sys.path`. Everything is seeded so the exact
schedule can be archived and regenerated — a requirement for trial registration
and good lab practice.

### Randomization / allocation schedules — `scripts/randomization.py`

```python
from randomization import (
    simple_randomization, block_randomization,
    stratified_block_randomization, cluster_randomization,
    assign_factorial_runs, arm_balance,
)

# Permuted blocks keep the arms balanced throughout enrollment (use for n < ~100
# or sequential intake — simple randomization can drift out of balance with small n)
sched = block_randomization(n=60, arms=["treatment", "control"], seed=42)

# Balance a prognostic variable across arms by randomizing within each stratum
sched = stratified_block_randomization({"siteA": 30, "siteB": 30},
                                       arms=["drug", "placebo"], ratio=(2, 1), seed=42)

# Randomize whole clusters, not individuals (the cluster is the unit)
sched = cluster_randomization(["clinic1", "clinic2", "clinic3", "clinic4"], seed=42)

arm_balance(sched)            # sanity-check the counts per arm
sched.to_csv("allocation_schedule.csv", index=False)
```

Choosing among them: **simple** is fine for large n but can produce imbalance with
small n; **block** guarantees balance throughout; **stratified block** additionally
balances a known prognostic factor; **cluster** is mandatory when the intervention
is delivered at a group level. See `references/randomization_and_blocking.md`.

### DOE matrices — `scripts/doe_designs.py`

```python
from doe_designs import (
    full_factorial, two_level_factorial, fractional_factorial,
    plackett_burman, central_composite, box_behnken, latin_hypercube,
)

# Factors as real-world (low, high) ranges -> design comes back in real units
factors = {"temp_C": (20, 60), "conc_mM": (1, 10), "pH": (6, 8)}

# Full 2^3: all main effects + all interactions (8 runs), run order randomized
design = two_level_factorial(factors, seed=42)

# Screen 7 factors cheaply (main effects only)
many = {f"factor_{i}": (0, 1) for i in range(7)}
design = plackett_burman(many, seed=42)

# Optimize over 2 factors with curvature (response-surface)
design = central_composite({"temp_C": (20, 60), "conc_mM": (1, 10)}, seed=42)

design.to_csv("experimental_runs.csv", index=False)
```

Run order is randomized by default so factors aren't confounded with time/drift
(machine warm-up, reagent aging). See `references/factorial_and_doe.md` for picking
generators, reading the alias structure, and choosing resolution.

---

## The mistakes that ruin studies

These are structural — they can't be fixed in analysis, only in design.

1. **Pseudoreplication.** Treating repeated measurements of one unit as independent
   replicates: 3 mice with 100 cells each is n = 3 (mice), not n = 300 (cells), for
   any treatment applied to the mouse. The replicate must be at the level the
   treatment is randomized. This single error invalidates a large share of published
   experiments. Randomize and replicate at the right level; analyze with the nesting
   respected (mixed model). See `references/design_types.md`.
2. **Confounding by a nuisance variable.** Running all treatment samples on Monday
   and all controls on Tuesday confounds treatment with day. Randomize across, or
   block on, every nuisance factor you can name (batch, day, plate, technician,
   instrument, position).
3. **No or broken randomization.** Convenience assignment (first-come → treatment)
   lets confounders sneak in. Use a seeded schedule and follow it.
4. **No proper control.** Without a concurrent control (and, where relevant, a
   vehicle/sham and blinding), you can't separate the treatment effect from time,
   placebo, or handling effects.
5. **Batch effects mistaken for biology.** In omics especially, process samples in a
   randomized/blocked order across batches; never let batch align with the condition.
6. **Edge/position effects on plates.** Evaporation and thermal gradients make plate
   edges differ. Randomize or block sample positions; don't put all controls in
   column 1.
7. **Aliasing ignored in fractional designs.** A low-resolution fractional factorial
   confounds main effects with interactions; know your alias structure before
   concluding a factor "has no effect."
8. **Optimizing without curvature.** A two-level factorial can't detect a curved
   response; you'll miss an interior optimum. Use a response-surface design.

---

## Workflow

1. **State the question, the unit, and the response.** What is randomized? What is
   measured? At what level is a true independent replicate? This determines everything.
2. **List nuisance factors** (batch, day, site, operator, position) — plan to block,
   stratify, or randomize across each.
3. **Pick the design** using the decision tree and reference files.
4. **Decide replication** at the correct level (and get n from the
   **statistical-power** skill for the chosen design).
5. **Generate the layout** with `randomization.py` / `doe_designs.py`, seeded.
6. **Randomize run/processing order** and plate/batch positions.
7. **Document** the design, seed, and schedule (pre-register if possible) so the
   analysis is confirmatory and the layout is auditable.
8. **Match the analysis to the design** — blocks, strata, clusters, and nesting must
   appear in the model (hand off to **statistical-analysis** / **statsmodels**).

---

## Resources

### Scripts
- `scripts/randomization.py` — seeded allocation schedules: `simple_randomization`,
  `block_randomization`, `stratified_block_randomization`, `cluster_randomization`,
  `assign_factorial_runs`, `arm_balance`.
- `scripts/doe_designs.py` — DOE matrices in real units: `full_factorial`,
  `two_level_factorial`, `fractional_factorial`, `plackett_burman`,
  `central_composite`, `box_behnken`, `latin_hypercube`.

### References
- `references/randomization_and_blocking.md` — randomization methods, blocking,
  stratification, controls, blinding, batch/plate layout.
- `references/factorial_and_doe.md` — factorial and fractional designs, resolution
  and aliasing, screening, and response-surface methodology.
- `references/design_types.md` — completely randomized, randomized block, crossover,
  repeated-measures, split-plot, Latin-square, cluster, and nested designs; the
  pseudoreplication problem in depth.
- `references/sequential_and_adaptive.md` — group-sequential designs, alpha spending,
  interim stopping, and adaptive sample-size re-estimation.

### Related skills
- **statistical-power** — required sample size / power for the design you've chosen.
- **statistical-analysis** — running and reporting the analysis after collection.
- **statsmodels** / **pymc** — fitting the models the design implies.

### Key references
- Fisher, R. A. (1935). *The Design of Experiments*.
- Montgomery, D. C. (2019). *Design and Analysis of Experiments* (10th ed.).
- Hurlbert, S. H. (1984). Pseudoreplication and the design of ecological field
  experiments. *Ecological Monographs*, 54(2), 187–211.
- Lazic, S. E. (2016). *Experimental Design for Laboratory Biologists*.
