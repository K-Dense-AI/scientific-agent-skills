---
name: agentfem
description: Creates, checks, runs, and inspects AgentFEM finite-element projects, and turns parameterized simulations into learning datasets. Use for AgentFEM CLI or MCP workflows, FEniCSx-based structural simulation, and AgentFEM simulation-to-surrogate campaigns. Not a replacement for a user's existing raw DOLFINx, Abaqus, or CFD workflow.
license: MIT
metadata:
  version: "1.0"
  skill-author: Haoming Luo
  last-reviewed: "2026-09-20"
---

# AgentFEM finite-element workflows

## When to use

Use this skill for a requested AgentFEM simulation, an existing AgentFEM
project, or a parameter campaign intended to supply surrogate-model data.
AgentFEM is a Python workflow and application layer over FEniCSx/DOLFINx;
it is not an LLM or an independent replacement for that numerical kernel.

## Establish the installed contract

Requires an installed AgentFEM scientific runtime with compatible FEniCSx,
PETSc, and MPI. The optional MCP adapter requires Python 3.11+. Local solves
need no API key or network; installation and documentation lookup need network.

In the user's selected scientific environment, run:

```bash
agentfem doctor
agentfem capabilities --json
```

Use the reported version and capabilities rather than assuming a method from
the latest source tree exists locally. If the runtime is missing or unhealthy,
consult the [installation guide](https://haoming-luo.github.io/agentfem/getting_started/)
and explain the dependency gap before changing the environment. Installing the
Python package alone does not guarantee a compatible FEniCSx/PETSc/MPI stack.

The workflow below was exercised with AgentFEM 0.3.3 and DOLFINx 0.11.0 on
macOS arm64. For other releases, inspect command help and the version-matched
template before applying it. Do not replace an existing project to obtain a
fresh template.

## Start from an inspectable model

Create a new project in an empty, user-approved working directory:

```bash
agentfem init --template static-solid .
agentfem check
```

Read the generated `case.py` and project README before solving. The model is
executable Python: review projects from other sources before running even
their checks. Establish these inputs in the model, not only in conversation:

- Geometry, dimension, and the 2D assumption (plane strain or plane stress).
- Material law and units; temperature dependence only when actually specified.
- Named fixed and loaded regions; distinguish pressure/traction from total force.
- Load history, element/mesh choice, and the output being requested.

Keep modeling edits within that generated public API; do not invent solver
options or silently add damage, fatigue, or contact laws to an elastic case.
For concrete API details, use the installed template and the
[solid-mechanics guide](https://haoming-luo.github.io/agentfem/guide/solid_mechanics/).

Once the model and requested computation are clear:

```bash
agentfem run --name baseline
agentfem show latest
agentfem verify
```

Read the execution record and `result.json` at the paths the CLI returns.
Report the run identity, units, selected quantity, and field artifact paths.
The static-solid example exposes `Displacement`, `S`, `E`, and `MISES` fields;
use the actual result rather than assuming every procedure exports these.
For visualization, follow the returned XDMF/HDF5 artifacts and the
[result guide](https://haoming-luo.github.io/agentfem/guide/results/).

## Interpret the evidence correctly

- `completed` means the process finished; `computed`, `verified`, and
  `validated` are distinct result states. Report the recorded state.
- `agentfem verify` can check artifact provenance; a passing provenance check
  does not establish experimental agreement or mesh independence.
- `displacement_max_abs` is the maximum absolute displacement degree of
  freedom. Do not label it maximum vector magnitude or tip deflection unless
  that equivalence has been established for the model.
- Force balance and energy checks are useful numerical evidence, not an
  engineering safety approval. Qualify peak stresses near constraints and
  geometric singularities before comparing them to an allowable stress.

For a fixed small-displacement linear-elastic model, a controlled load-scaling
comparison is useful: doubling the load should double displacement and stress.
Preserve the baseline and compare the same quantity and units. Do not apply
that relation unchanged to plasticity, changing contact, or large deformation.

## Use MCP when a connection is already configured

The optional [official MCP adapter](https://github.com/haoming-luo/agentfem-mcp)
provides the same lifecycle through seven tools. It does not install the
scientific runtime. With adapter 0.1.0, the sequence is:

1. `describe_system(detail="summary")`: identify the runtime and approved roots.
2. `create_project(path=..., template="static-solid")`: only for a new project.
3. `validate_project(path=...)` and `inspect_project(path=...)`: inspect the
   validation payload, not only whether the MCP transport succeeded.
4. `submit_run(path=..., name="baseline", mpi_ranks=1)`: obtain a job identity.
5. `get_run_status(path=..., job_id=...)`: wait for a terminal state without
   submitting the same run again. Use bounded, spaced polling.
6. `get_result_summary(path=..., job_id=...)`: report the result and its trust state.

These tool signatures were exercised through the published adapter over stdio
against the runtime above. Keep requests inside its approved project roots.
Do not widen those roots or upload local models merely to make a task work.
The [connection guide](https://haoming-luo.github.io/agentfem/agents/mcp/)
documents setup when the user actually requests a new connection.

## Turn simulations into learning data

For the bounded elasticity teaching campaign, use a compatible source checkout
with the numerical environment active. From that checkout's root:

```bash
python examples/static_elasticity_surrogate_campaign.py
```

This command was tested using source commit
`08f3ca5a871aff5084142837f3030e0a2d88dfd5`. It is a repository example,
not a script guaranteed to ship in a wheel. It holds a plane-strain
cantilever's geometry and loading fixed, varies Young modulus from 150 to
250 GPa, generates ten FEM cases, and fits a scalar ridge baseline with an
eight-case training/two-case holdout split. The output is maximum absolute
displacement DOF, in metres.

Inspect `campaign/`, `trusted_dataset/`, and `surrogate/` under
`examples_output/static_elasticity_surrogate_campaign/`. Preserve the input
parameters, units, run provenance, output definition, and train/test split.
Do not describe these scalar predictions as neural-operator field inference.
The small holdout teaches the workflow; it does not qualify a new engineering
application. For new geometry, loading, or constitutive behavior, establish a
new sampling domain and validation set rather than extrapolating this result.

See the [campaign walkthrough](https://haoming-luo.github.io/agentfem/examples/simulation_to_surrogate/)
and [simulation-to-learning guide](https://haoming-luo.github.io/agentfem/guide/simulation_to_learning/)
for the current public interfaces. Return model files, run/result locations,
the dataset or fitted-model artifact when requested, and a concise account of
what was computed versus inferred.
