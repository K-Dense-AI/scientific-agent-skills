---
name: tellurium
description: Simulates biochemical kinetic models from SBML or Antimony with Tellurium and libRoadRunner, checks model units, compares deterministic parameter perturbations, and exports and replays SBML plus SED-ML COMBINE archives. Use for reaction-network time courses, kinetic parameters, concentration dynamics and reproducible simulation experiments; steady-state constraint-based metabolic flux analysis belongs to cobrapy.
license: MIT
compatibility: Requires Python 3.11 with Tellurium 2.2.13.1, libRoadRunner 2.10.0, Antimony 3.2.0, python-libsbml 5.21.2, python-libsedml 2.0.34 and python-libcombine 0.2.20. Network is needed for installation only. Native wheels were tested on macOS ARM64. No credentials or external services.
metadata:
  version: "1.1"
  skill-author: K-Dense Inc.
  upstream-version: "2.2.13.1"
  last-reviewed: "2026-10-01"
---

# Tellurium kinetic experiments

## When to use

Use this skill for deterministic reaction-network trajectories and independent parameter conditions
from a local model. The helper performs SBML consistency checks, CVODE integration and an actual
COMBINE archive replay. It exports each condition's exact SBML and the SED-ML experiment rather
than handing off an unrecorded notebook state.

## Runtime

```bash
uv venv --python 3.11 kinetic-env
uv pip install --python kinetic-env/bin/python tellurium==2.2.13.1 libroadrunner==2.10.0 \
  antimony==3.2.0 python-libsbml==5.21.2 python-libsedml==2.0.34 python-libcombine==0.2.20
```

The full workflow ran with these packages on macOS ARM64. It constructs SED-ML with libSEDML and
archives with Tellurium/libCombine; PhraSEDML is not required by this helper. Headless runs can set
`MPLBACKEND=Agg`. No plotting window is opened by the helper.

The six pinned releases were rechecked against official PyPI metadata on 2026-10-01. RoadRunner's
documentation site still displays an old version banner; the solver settings below were also
checked against released 2.10.0 source and the installed native runtime.

## Workflow

1. Inspect the supplied model's compartments, species, initial conditions, boundary species,
   reactions, parameter definitions and rules/events. Identify the scientific question and
   distinguish a mechanistic kinetic model from a flux-balance reconstruction. Record the
   source model, version and any literature parameters; do not treat an example model as
   experimentally calibrated.
2. Check units before interpreting a trajectory. SBML reaction rates have amount/time units;
   species may have concentration or amount semantics. In a fixed-volume first-order model,
   `k*A*cell` converts concentration dependence into amount/time. The helper checks SBML
   consistency and retains every warning, including undefined units. Undefined units are
   reported as empty/indeterminable, not silently assumed to mean SI.
3. Select concentration outputs and an experiment in the JSON format described in
   [references/experiments.md](references/experiments.md). Time values use the model's own time
   units. The tested helper outputs concentration for species with `hasOnlySubstanceUnits=false`;
   it rejects amount-only selections to avoid changing their meaning during SED-ML replay.
   Zero-dimensional compartments and rate-rule models are also rejected; the latter need a separate
   tolerance workflow because RoadRunner 2.10.0 can order scalar tolerances differently from states.
4. Run baseline and desired constant-global-parameter changes. Every scenario starts from a
   fresh SBML model, so previous final concentrations cannot leak into the next condition.
   Changes to species initial values, compartment volume, assignment rules or time-varying
   inputs require explicit model changes and corresponding tests; they are not parameter
   mutations hidden in this helper.
5. Examine finite outputs, signs, relevant conservation relations and timescales. Check solver
   sensitivity by repeating at stricter tolerances when the scientific interpretation depends
   on small differences. A smooth curve or zero archive-replay error does not establish model
   validity or parameter identifiability. Never clip negative concentrations to hide solver
   or model problems.
6. Review the COMBINE replay comparison, model warnings and units in `report.json`. The helper
   replays the archive it generated and compares every selected value against the direct
   trajectories. Deliver the archive, report, source model, experiment config and CSV curves.

## Run the executable reference

[assets/first-order.ant](assets/first-order.ant) defines the closed reaction A → B in a constant
1-L compartment, initially A=1 and B=0 mol/L, with k=0.2 per second.
[assets/experiment.json](assets/experiment.json) runs baseline and k=0.4 per second from 0 to 10 s.
From the skill directory, point the interpreter to the environment created above:

```bash
MPLBACKEND=Agg kinetic-env/bin/python scripts/kinetic_experiment.py \
  --model assets/first-order.ant --format antimony --experiment assets/experiment.json \
  --output kinetic-reference

# The SBML branch was also exercised; replace these filenames with actual user inputs.
MPLBACKEND=Agg kinetic-env/bin/python scripts/kinetic_experiment.py \
  --model model.xml --format sbml --experiment experiment.json --output kinetic-analysis
```

Output directories must be new. The reference was executed, including Antimony-to-SBML conversion,
libSBML checks, both direct integrations, SED-ML creation and COMBINE replay. Both conditions matched
the analytical `A(t)=exp(-k*t)`, `B(t)=1-A(t)` within 2e-8 absolute/relative tolerance; A+B was
conserved within 1e-10, and archive replay matched direct output exactly on the tested stack.
Additional checks use a 5-L compartment and an initial amount of 10 mol (2 mol/L), resolve every
SED-ML species XPath against its actual SBML file, and verify the solver tolerance scaling.
That verifies this controlled example; arbitrary SBML packages, events, delays or stochastic models
are not covered by those tests.

## Artifacts

| File | Contents |
| --- | --- |
| `baseline.csv`, other scenario CSVs | Time and selected concentrations, with bracketed species headers |
| `model_<scenario>.xml` | Exact independent SBML condition used by both execution routes |
| `experiment.sedml` | Uniform time course, CVODE/tolerances, models, tasks and output selections |
| `experiment.omex` | Those SBML files plus the master SED-ML and archive manifest |
| `report.json` | Versions, input/archive checksums, parameters, units, validation findings, initial state tolerance vectors, minimum concentrations and replay differences |

The libSEDML findings in the report are **parse diagnostics**. Successful execution and equality
provide additional evidence that this generated uniform-course experiment works in Tellurium;
they do not certify every SED-ML feature or every simulator's compatibility.

In RoadRunner 2.10.0, the JSON `absolute_tolerance` value is a **scalar adjustment factor** for
state/amount tolerances, not a uniform concentration error bound. The archive records that meaning
as `KISAO:0000571`; inspect `initial_state_absolute_tolerances` and the detailed explanation in
[references/experiments.md](references/experiments.md). Declared SBML XPath namespaces and explicit
stiff/uniform-output settings prevent successful Tellurium replay from hiding missing archive context.

## Primary references

- [Tellurium model loading and export methods](https://tellurium.readthedocs.io/en/latest/tellurium_methods.html)
- [Antimony unit and reaction semantics](https://tellurium.readthedocs.io/en/latest/antimony.html)
- [Tellurium SED-ML implementation](https://tellurium.readthedocs.io/en/latest/_modules/tellurium/sedml/tesedml.html)
- [SED-ML Level 1 Version 3 specification](https://sed-ml.org/documents/sed-ml-L1V3.pdf)
- [RoadRunner 2.10.0 CVODE implementation](https://github.com/sys-bio/roadrunner/blob/v2.10.0/source/CVODEIntegrator.cpp)
- [KiSAO algorithm and parameter definitions](https://github.com/SED-ML/KiSAO/blob/master/kisao.owl)
