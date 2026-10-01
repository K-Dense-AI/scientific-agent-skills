---
name: pycalphad
description: Computes finite-temperature CALPHAD equilibria, phase fractions, and phase compositions from thermodynamic TDB databases using pycalphad. Use for alloy phase stability, equilibrium temperature sweeps, tie lines, lever-rule checks, or reproducible phase-fraction calculations with explicit components and mole-fraction conditions.
license: MIT
compatibility: Requires Python 3.12+, pycalphad 0.11.2, and NumPy. Installation needs network access; calculations run locally without credentials. Real-material predictions require a suitable licensed thermodynamic database.
metadata:
  version: "1.0"
  skill-author: K-Dense Inc.
  tested-package-version: "0.11.2"
---

# pycalphad: TDB equilibrium calculations

## When to use

Use for equilibrium phase fractions and compositions at a fixed bulk elemental mole
composition, specified pressure, and a list of finite temperatures. The bundled helper
executes real pycalphad equilibria, checks mass balance, repeats at greater sampling
density, and exports each stable composition set separately.

Equilibrium is constrained by the selected database, components, phases, and conditions.
It does not predict precipitation rates, retained metastable microstructures, or properties
of phases missing from the database. Successful numerical checks do not establish the
database's experimental accuracy.

## Workflow

1. Identify the TDB's source, license, assessment/publication, valid temperature/pressure
   and composition range, and required elements. Use the user's database for real alloys.
   The bundled [assets/ideal-cu-ni.tdb](assets/ideal-cu-ni.tdb) is an original hypothetical
   teaching model, **not an assessed Cu-Ni database**.
2. Inspect database elements and phases. Select the relevant phases deliberately; record
   exclusions because they can turn the calculation into a metastable constrained result.
   Include `VA` where required by sublattice models. Vacancies are not an independent bulk
   mole fraction. Order-disorder models may require their coupled phase definitions.
3. Copy [assets/equilibrium.json](assets/equilibrium.json). Specify exactly N-1 elemental
   mole fractions and one dependent non-vacancy element. The dependent fraction is
   `1 - sum(independent fractions)`; fractions are not silently normalized. Set K and Pa.
   Convert weight percentages or mass fractions before using this helper.
4. Declare the database temperature interval from its assessment if known, or set
   `database_temperature_range_k` to null if unknown. This is user-supplied evidence,
   not a range automatically inferred from every TDB function. Requests outside a declared
   interval fail. Check pressure and composition validity separately.
5. Run the calculation. Check finite Gibbs energies, phase fractions summing to one,
   reconstructed bulk composition, and stability to doubled `pdens` (phase-constitution
   sampling density). Near transitions, refine temperatures and sampling density further.
6. Deliver phase fractions with their **molar** basis, phase compositions, database hash,
   conditions, excluded phases, and any numerical or assessment limitations.

Read [references/model-and-validation.md](references/model-and-validation.md) for the
analytic example, basis conversion, miscibility-gap handling, and convergence limits.

## Execute the tested example

From the collection root:

```bash
uv run --no-project --python 3.12 --with pycalphad==0.11.2 --with numpy==2.5.3 \
  python skills/pycalphad/scripts/equilibrate.py \
  skills/pycalphad/assets/ideal-cu-ni.tdb \
  skills/pycalphad/assets/equilibrium.json equilibrium-result
```

Tested on Python 3.12, pycalphad 0.11.2, and NumPy 2.5.3. Use a new output directory.
All thermodynamic calculations are local; the script does not upload a TDB.

For the supplied hypothetical model at X(Ni)=0.5 and 101325 Pa:

| Temperature | Equilibrium result |
| --- | --- |
| 900 K | FCC_A1 only |
| 1100 K | 0.5 FCC_A1 + 0.5 LIQUID; X(Ni) approximately 0.527307 and 0.472693 respectively |
| 1300 K | LIQUID only |

The suite verifies analytic common-tangent compositions, a noncentral lever-rule case,
Gibbs energy, mass balance, both single-phase limits, and actual same-phase miscibility
gap vertices. These validate the computational workflow, not real Cu-Ni metallurgy.

## Outputs and acceptance

- `report.json`: settings and versions, TDB/settings SHA-256, excluded database phases,
  reconstructed bulk composition, per-temperature baseline/refined results, and checks.
- `phase-equilibria.csv`: one row per stable vertex per temperature and sampling run,
  including phase name, molar phase fraction, and elemental mole fractions. Its Gibbs
  energy column is the **whole-system molar Gibbs energy**, repeated for each vertex;
  it is not the individual phase energy.

Unused pycalphad vertices have blank names and NaN values; those are omitted. Named
vertices with invalid values cause failure. Multiple vertices with the same phase name
are retained because a miscibility gap can contain two composition sets of one phase.
Vertex indices do not track the same physical phase continuously across temperatures.

`all_checks_passed` requires each run's phase-sum and bulk-composition residuals within
`mass_balance_tolerance`, phase totals stable within `phase_fraction_tolerance`, and
system Gibbs energy stable within `gibbs_energy_tolerance_j_per_mol` when `pdens` doubles.
This comparison does not certify the global minimum or track individual composition-set
movement within a same-phase miscibility gap; inspect their exported compositions too.
Failed checks remain visible in the report rather than being relabeled as convergence.

## Boundaries and upstream contracts

The helper handles elemental mole fractions, one composition, one pressure, and up to
1000 explicit positive temperatures. It validates selected phases through pycalphad's
phase-compatibility rules; incompatible or automatically filtered order/disorder phase
sets produce an explicit error. It does not silently remove requested phases.

Charged-species constraints, externally imposed chemical potentials, custom models,
activity reference-state changes, and database optimization require additional modeling
and are outside this helper's tested scope. Do not extrapolate the pedagogical asset to
real material selection or heat-treatment decisions.

- [Equilibrium dataset semantics](https://pycalphad.org/docs/latest/examples/3_High_Throughput_Analysis/2_UsingCalculationResults.html)
- [Phase fractions and composition basis](https://pycalphad.org/docs/latest/examples/2_Computing_Properties/1_PhaseCompositions.html)
- [Equilibrium and sampling API](https://pycalphad.org/docs/latest/api/pycalphad.core.html)
- [Ordering examples](https://pycalphad.org/docs/latest/examples/EquilibriumWithOrdering.html)

Upstream `latest` documentation includes development APIs; the bundled helper and phase
filtering behavior were exercised against the pinned stable 0.11.2 release.
