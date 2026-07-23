# Simulation-study methodology (not SimPy API)

Verified 2026-07-23. This guide applies established discrete-event simulation
methods to SimPy models. SimPy schedules events; it does not perform these study
design decisions automatically.

## 1. Start with the conceptual model

Before code, specify:

- purpose, decision context, stakeholders, and intended domain;
- system boundary, entities, resources, queues, routes, state, and termination;
- input data provenance and fitted/assumed distributions;
- initial conditions and time units;
- performance measures/estimands;
- assumptions, simplifications, exclusions, and known limits;
- required accuracy and validation evidence.

Robinson defines conceptual modeling as abstraction from a real or proposed system
and emphasizes validity, credibility, utility, feasibility, and the simplest model
adequate for purpose. Sargent frames validity relative to the intended application
and domain, not as a universal property.

Use a unit table:

| Quantity | Unit | Convention |
|---|---|---|
| `env.now` | minutes | starts at opening |
| interarrival | minutes/entity | strictly positive |
| service | minutes | sampled at service start |
| throughput | entities/hour | convert from minute horizon |

SimPy time is unitless. Unit inconsistency can produce a perfectly executable but
invalid model.

## 2. Terminating versus steady-state studies

### Terminating

A terminating simulation has a natural, predeclared endpoint: closing time,
completion of an order, end of a mission, or another event relevant to the purpose.
Initial conditions are part of the estimand and should normally be identical across
replications.

Decide how to handle entities still present at a fixed clock horizon:

- stop and report/censor unfinished paths;
- stop arrivals at closing but drain the system;
- terminate on an explicit completion event.

These answer different questions. Numeric `env.run(until=horizon)` is half-open and
does not drain.

### Nonterminating / steady state

A nonterminating system has no natural endpoint and targets a long-run parameter.
Arbitrary initialization creates transient bias. A finite warm-up deletion may
reduce that bias, but neither a warm-up nor a long run proves stationarity or
convergence.

Use a declared replication/deletion design:

1. estimate/justify warm-up in a pilot study;
2. make independent production replications;
3. apply the same deletion rule to each;
4. make the post-deletion run much longer than warm-up;
5. assess sensitivity to longer warm-up and run length.

Do not label a finite-horizon operating-day model "steady state" merely because it
has many events.

## 3. Random seeds and streams

Pseudo-random generation is deterministic given algorithm, state, and consumption
order. Reproducibility requires recording:

- RNG implementation and Python/package versions;
- base seed and derived per-replication seeds;
- mapping of streams to stochastic sources;
- replication index and configuration;
- any common-random-number pairing.

Use separate local RNG objects for distinct sources:

```python
arrival_rng = random.Random(arrival_seed)
service_rng = random.Random(service_seed)
```

Avoid module-global `random.seed()` in reusable models: unrelated code can consume
or reset the shared stream.

L'Ecuyer recommends independent streams/substreams, often one stream per stochastic
source and one substream per replication. Distinct hash-derived seeds, as used by
the bundled scripts, provide deterministic separation for a compact standard-library
example; they do **not** mathematically prove stream independence. For high-stakes
or large parallel experiments, use a generator/package with explicit tested stream
and jump/substream facilities and document it.

### Common random numbers

For paired alternatives, intentionally using the same source-specific random
numbers can reduce variance of differences. Keep replication pairs aligned and use
separate source streams so a demand draw in one alternative does not become a
service draw in another. Analyze paired replication differences. Common random
numbers are a designed variance-reduction method, not independent streams across
alternatives.

## 4. Independent replications

Within-run entity outcomes are usually dependent: customers share queues and system
state. The basic independent unit is a complete replication using an independent
stream set.

For each replication:

- reset model state and statistical counters;
- use the same scenario/configuration and intended initial-condition rule;
- use new independent random streams;
- produce one estimate per performance measure.

Law's output-analysis tutorial stresses that one run does not produce "the answer."
Use at least two replications to estimate variance; practical counts should be
chosen from desired precision, distribution shape, computational cost, and a pilot,
not a universal magic number.

The bundled replication runner caps counts and records every derived seed. It does
not automatically choose a sufficient replication count.

## 5. Confidence intervals

Given independent replication estimates `X_1, ..., X_n`, a common two-sided
Student-t interval for their mean is:

`mean(X) +/- t_(n-1, 1-alpha/2) * s(X) / sqrt(n)`.

State:

- estimand and unit;
- number of independent replications;
- confidence level and method;
- point estimate, interval, and half-width;
- warm-up/run length and missing/unfinished handling.

Conditions and caveats:

- replication estimates must be independent and comparably generated;
- the t interval is exact under normal replication estimates and approximate under
  suitable large-sample behavior;
- a tiny `n` gives unstable variance and distribution diagnostics;
- a narrow interval around a biased/invalid model result is still wrong;
- optional stopping based on observed precision needs a valid sequential procedure.

### Never make a naive single-run CI

Do not feed all customer waits from one run to an IID t interval. Positive serial
dependence can severely understate variance. Law (2020) illustrates dramatic
undercoverage from this approach.

For one long steady-state run, use a justified output-analysis method such as batch
means, spectral methods, or regenerative analysis with diagnostics. The bundled
CLI deliberately implements independent replications, not a naive single-run CI.

## 6. Warm-up and transient bias

Warm-up is an estimand/study-design issue, not an `Environment` option. SimPy has no
automatic steady-state detector.

Good practice:

- reason from initial conditions and system dynamics;
- inspect multiple pilot replications, not one noisy path;
- use an established rule (for example Welch-type graphical analysis or a
  documented method);
- separate pilot selection from production inference;
- use the same declared deletion in production runs;
- examine sensitivity to longer warm-up and run length;
- report discarded observations/time and window membership rule.

Schruben developed tests for initialization bias; Robinson and Hoad et al. developed
warm-up selection procedures. No method makes every model stationary, and visual
flattening is not proof.

Choose the measurement-window rule before analysis:

- arrivals after warm-up;
- departures after warm-up;
- entities entirely contained after warm-up;
- time integral clipped to `[warm_up, horizon)`.

These estimate different quantities. The bundled queue scripts use completed
entities whose arrival is at or after warm-up plus clipped time-weighted resource
metrics, and disclose unfinished entities.

## 7. Verification and validation

Sargent distinguishes:

- **conceptual model validity** — assumptions/theories and representation are
  reasonable for intended purpose;
- **computerized model verification** — implementation matches the conceptual
  model;
- **operational validation** — outputs have sufficient accuracy over the intended
  domain;
- **data validity** — data are adequate and correct for building/testing/running.

### Verification

Use:

- deterministic traces and event-order assertions;
- conservation/balance identities;
- extreme and degenerate cases;
- analytical queue benchmarks where assumptions match;
- independent implementation or hand calculations;
- tests for resource release, cancellation, preemption, and deadlock;
- monitor-on versus monitor-off equivalence.

Passing tests establishes implementation evidence, not real-world validity.

### Validation

Use evidence appropriate to purpose:

- subject-matter expert face validation;
- historical/holdout system data;
- graphical and statistical comparison of system/model behavior;
- predictive validation when future observations become available;
- comparison with accepted models;
- traces/animations for logic review;
- parameter variability and sensitivity analysis.

Predeclare acceptable accuracy where possible. Validation is iterative and
domain-specific; failure in a required operating condition invalidates use there.

## 8. Sensitivity and uncertainty

Vary uncertain inputs, structural assumptions, warm-up, run length, capacities,
queue discipline, and initial conditions over defensible ranges. Preserve paired
random streams for alternative comparisons when intentionally using common random
numbers.

Separate:

- **Monte Carlo uncertainty** — finite replications;
- **parameter uncertainty** — uncertain input values/distributions;
- **structural uncertainty** — alternate model logic/boundaries;
- **validation discrepancy** — model versus system;
- **scenario uncertainty** — different future conditions.

A replication CI addresses only the first under the configured model.

## 9. Reproducibility and reporting

The STRESS-DES guidelines organize complete reporting around objectives, model
logic, data, experimentation, implementation, and code access. At minimum retain:

- conceptual model and assumptions;
- exact config and input-data provenance;
- SimPy/Python versions and environment lock/pin;
- source revision;
- seed/stream manifest;
- warm-up, horizon, entity/event caps, and replications;
- metric definitions and unit conversions;
- validation/sensitivity evidence;
- raw replication-level outputs and analysis code.

Reproducibility of the program is not validity of the model.

## 10. No causal claims from a queue simulation alone

A simulation computes implications of encoded assumptions. Changing a parameter
and observing an output difference is a **model-based scenario contrast**, not an
identified causal effect in the real system. Causal language requires defensible
causal assumptions/design, calibrated interventions, and validation beyond SimPy.

Use phrasing such as:

> Under the specified arrival, service, routing, and capacity assumptions, the
> simulated scenario produced ...

## Primary method sources

- [Law, "Statistical Analysis of Simulation Output Data," WSC 2020](https://informs-sim.org/wsc20papers/134.pdf)
- [L'Ecuyer, "Random Number Generation with Multiple Streams," WSC 2015](https://informs-sim.org/wsc15papers/003.pdf)
- [Sargent, "Verification and Validation of Simulation Models," WSC 2010](https://www.informs-sim.org/wsc10papers/016.pdf)
- [Robinson, "Conceptual Modelling for Simulation Part I," 2008](https://doi.org/10.1057/palgrave.jors.2602368)
- [Schruben, "Detecting Initialization Bias," 1982](https://doi.org/10.1287/opre.30.3.569)
- [Robinson, warm-up selection, 2007](https://ideas.repec.org/a/eee/ejores/v176y2007i1p332-346.html)
- [Hoad, Robinson, Davies, replication selection, 2010](https://doi.org/10.1057/jors.2009.121)
- [Monks et al., STRESS guidelines, 2018](https://doi.org/10.1080/17477778.2018.1442155)

See `sources.md` for full dated notes.
