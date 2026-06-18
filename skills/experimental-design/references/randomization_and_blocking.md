# Randomization, Blocking, Stratification, and Controls

These are the tools of *local control*: removing or balancing nuisance variation so
the comparison you care about is clean. Randomization handles the unknown
confounders; blocking and stratification handle the known ones; controls and
blinding handle the systematic biases.

## Randomization — why and how

Randomization assigns treatments to units by chance, so that in expectation every
confounder (measured or not, known or unknown) is balanced across arms. This is the
foundation of causal inference: without it, an observed difference could always be
due to some variable that happened to track the grouping.

Use a **seeded, reproducible** schedule (see `scripts/randomization.py`) and follow
it exactly. Record the seed. "I randomized somehow" is neither auditable nor
reproducible.

### Methods (and when each is right)

| Method | What it does | Use when |
|--------|--------------|----------|
| **Simple** | Independent random assignment per unit | n is large (≳100); simplicity matters; imbalance is tolerable |
| **Permuted block** | Within each block, arms appear in fixed ratio; order shuffled | You need balance throughout enrollment, or n is small/moderate, or intake is sequential |
| **Stratified block** | Separate blocks within each level of a prognostic factor | A known covariate (site, sex, stage) must be balanced across arms |
| **Cluster** | Whole groups (clinics, classes) assigned to arms | The intervention is delivered at a group level |
| **Minimization** | Adaptively assign to minimize imbalance across several covariates | Many prognostic factors and small n (specialized; not in the script) |

**Simple randomization caveat:** with small n it behaves like flipping a few coins —
you can easily get 12 vs. 8 instead of 10 vs. 10, and worse for subgroups. Blocking
fixes this.

**Block size:** must be a multiple of the ratio unit (e.g. for 1:1, sizes 2, 4, 6).
Smaller blocks balance more tightly but are more predictable in unblinded trials
(a clinician who knows the block size can guess the last allocation). Vary block
size or keep it concealed when predictability is a concern.

## Blocking — removing known nuisance variation

A **block** is a group of units expected to be similar (same day, batch, litter,
plate, instrument run). You randomize treatments *within* each block. The nuisance
variation between blocks is then removed from the error term, so the treatment
comparison is more precise — often dramatically so.

Block on anything that (a) you can identify before the experiment and (b) you
expect to affect the response but isn't of interest itself:
- **Time:** day, week, session, processing batch.
- **Space:** plate, plate position/edge, shelf, cage rack, field plot.
- **Material:** reagent lot, animal litter, cell passage, donor.
- **People/instruments:** technician, machine, sequencing run.

Rule of thumb: *"Block what you can, randomize what you cannot."* If you suspect a
factor matters but can't block it, at least randomize across it and record it as a
covariate.

**Randomized complete block design (RCBD):** every treatment appears once in every
block. This is the workhorse design — analyze with treatment + block in the model.

## Stratification vs. blocking vs. covariate adjustment

These overlap; the distinction is about *when* you control the variable:
- **Stratify / block at design time** when the factor is known before assignment and
  you want guaranteed balance (the safest, since it doesn't rely on a model).
- **Adjust as a covariate at analysis time** (ANCOVA, regression) when the factor is
  continuous or measured after assignment. Often you do both: stratify on the big
  ones, adjust for the rest.

A few strata are better than many: stratifying on too many factors at once leaves
strata with too few units to block effectively. For many covariates and small n,
minimization is the alternative.

## Controls

A comparison needs a concurrent baseline. Match the control to the threat you're
ruling out:
- **Untreated / standard-of-care control** — isolates the treatment effect from time.
- **Vehicle / sham control** — isolates the active ingredient from the delivery
  (injection stress, vehicle solvent, sham surgery).
- **Positive control** — a treatment known to produce the effect, to confirm the
  assay can detect one at all.
- **Concurrent, not historical** — controls run at the same time as the treatment;
  historical controls reintroduce time confounding.

## Blinding

Blinding prevents expectation from biasing measurement and behavior:
- **Single-blind:** the subject doesn't know the assignment.
- **Double-blind:** neither subject nor experimenter/assessor knows.
- **Blinded outcome assessment:** at minimum, whoever measures the outcome shouldn't
  know the group — cheap and high-value even in animal/bench work.
Allocation concealment (the person enrolling can't foresee the next assignment) is
distinct from blinding and just as important; a sealed seeded schedule provides it.

## Batch effects and plate layout (especially omics / HTS)

Batch effects are systematic technical differences between processing groups and are
a leading cause of irreproducible high-throughput results.
- **Never let batch align with the biological condition.** If all cases are in batch
  1 and all controls in batch 2, condition and batch are perfectly confounded and
  no normalization can separate them.
- **Randomize or block sample-to-batch and position-within-plate.** Spread each
  condition across all batches and across plate positions.
- **Avoid edge effects:** evaporation and thermal gradients make outer wells differ;
  don't load all controls into edge columns. Randomize positions, or include
  replicates spanning edge and interior.
- **Include anchor/reference samples** in every batch to estimate and correct batch
  shifts.
- Use `assign_factorial_runs()` / the randomization functions to generate a
  randomized processing order and position map.

## Documentation

Record, and ideally pre-register: the randomization method, the seed, block sizes,
stratification factors, the schedule itself, and the planned analysis (which must
include block/stratum/cluster terms). This is what makes the study auditable and the
primary analysis confirmatory rather than exploratory.
