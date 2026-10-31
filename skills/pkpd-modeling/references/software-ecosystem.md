# PK/PD software interfaces reviewed 2026-10-01

Choose a tool by required model, diagnostics and verification evidence. Neither programming
language nor vendor establishes suitability for a regulatory or clinical context. Bundled scripts
are tested exploratory implementations, not a validated clinical platform.

## Executed Python interfaces

NumPy 2.5.3 and SciPy 1.18.1 were used for isolated tests. NumPy2+ provides `np.trapezoid`; it does
not sort sample times. SciPy `least_squares`, `minimize`, `solve_ivp` and distribution functions
supply numerical primitives; optimizer/solver success alone is not scientific validation.

Pharmpy 2.2.0 (26 August 2026) requires Python>=3.12, excluding 3.14.1. Installed signatures and seven
independent transformations were checked. Important changes: dataset indices begin at 1 since 2.0;
`add_placebo_model` became `set_placebo_model` in 2.1; `set_unit` became `annotate_unit` in 2.2.
Annotation declares a unit; `convert_unit` changes values. Inspect observation IDs because
`get_observations` includes all DVIDs by default.
[Changelog](https://pharmpy.github.io/latest/changelog.html).

```python
# Executed independently on Pharmpy 2.2.0's bundled model; no estimation engine required.
import pharmpy.modeling as m
base = m.load_example_model("pheno")
tmdd = m.set_tmdd(base, type="qss")
turnover = m.add_indirect_effect(base, expr="emax", prod=True)
direct = m.set_direct_effect(base, expr="sigmoid")
link = m.add_effect_compartment(base, expr="emax")
size = m.add_allometry(base, allometric_variable="WGT", reference_value=70)
transit = m.set_transit_compartments(base, n=3, keep_depot=True)
nonlinear = m.set_michaelis_menten_elimination(base)
```

Transformations return new models; unassigned calls leave the original unchanged. A successful
transformation is not a fitted/validated model. `set_tmdd` observation mapping is described in
[TMDD](tmdd-and-biologics.md), and shrinkage's `sd` convention in [population PK](population-pk.md).

The installed tools include run_allometry, run_amd, run_bootstrap, run_covsearch, run_estmethod,
run_iivsearch, run_iovsearch, run_linearize, run_modelfit, run_modelrank, run_modelsearch,
run_pdsearch, run_qa, run_retries, run_ruvsearch, run_simulation, run_structsearch, run_tool and
run_vpc. Engine-backed runs require separately configured estimation software and were not executed.
[Tool documentation](https://pharmpy.github.io/latest/tools.html).

## Specialist tools reviewed through official documentation

| Task | Tools and boundary |
| --- | --- |
| NLME | NONMEM 7.6, Monolix, nlmixr2; select estimation/diagnostics appropriate to data |
| NCA | Phoenix WinNonlin, PKNCA; predefine conventions and qualify the implementation |
| Simulation | rxode2, mrgsolve, Simulx; preserve event semantics and residual/IIV distinctions |
| BE | PowerTOST for planning; validated replicate-design analysis for ABEL/RSABE |
| PBPK | PK-Sim/MoBi 12.3, Simcyp, GastroPlus; context-specific verification |

CRAN nlmixr2 currently reports 7.0.1 with R>=4.1 and rxode2>=5.0.0. Match companion-package
versions; recent rxode2 serialization changes mean old saved objects may need conversion/refitting.
[CRAN package](https://cran.r-project.org/web/packages/nlmixr2/index.html),
[rxode2 news](https://nlmixr2.github.io/rxode2/news/index.html).
NONMEM 7.6 includes ADVAN16/17 for delay equations; consult its installed manual for control-stream
semantics. [Vendor overview](https://www.iconplc.com/solutions/technologies/nonmem).

PKPy's [author repository](https://github.com/Gumgo91/PKPy) describes its Python PK workflow;
`pkpy` returned 404 from PyPI during review, so do not assume that package name is installable there.
`chi-drm`1.0.3, PINTS0.6.1 and lmfit1.3.4 metadata were checked, but no API examples or model fits
for them were executed. They are optional alternatives, not dependencies of these scripts.
See [source ledger](source-ledger.md) for evidence boundaries.
