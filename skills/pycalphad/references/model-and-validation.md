# Composition basis and equilibrium validation

## Original pedagogical database

`assets/ideal-cu-ni.tdb` was written for this skill and is released under the skill's
MIT license. Cu and Ni are labels for a hypothetical ideal binary; there are no fitted
experimental data. The file defines one substitutional sublattice in FCC_A1 and LIQUID,
with no excess mixing terms or pressure dependence. Its functions span 298.15–2000 K.

With x = X(Ni), energies in J/mol, and R in J/(mol K):

- G(FCC_A1) = R T [x ln x + (1-x) ln(1-x)].
- G(LIQUID) = G(FCC_A1) + (1-x)(10000-10T) + x(12000-10T).

At T=1100 K the liquid endmember offsets are -1000 and +1000 J/mol. Equality of both
component chemical potentials gives x_liquid = 1/(1+exp(1000/(RT))) and
x_solid = 1-x_liquid. The phase fraction of solid at bulk x between those endpoints is
(x_bulk-x_liquid)/(x_solid-x_liquid). This is an independent analytic check of the
numerical common tangent, phase compositions, and lever rule. The tests use pycalphad's
R=8.3145 J/(mol K); the listed decimal values are package/model-specific regression values.

The database intentionally lacks realistic heat capacities, lattice stabilities, excess
mixing, magnetic terms, and pressure effects. Its apparent transitions are synthetic.
Do not fit a real experiment to it or replace an assessed database with this example.

## Basis conversions

For measured elemental mass fractions w_i and molar masses M_i, calculate
x_i = (w_i/M_i) / sum_j(w_j/M_j), including the dependent element. Weight percent is
first divided by 100. Store the original composition, molar masses, and converted values
with the run. The helper accepts only the resulting mole fractions and rejects a
`mass_fraction` basis instead of treating weight percent as atomic fraction.

`NP` is a molar phase fraction at total N=1. A mass phase fraction requires each phase's
composition-weighted molar mass: w_phase = NP_phase*M_phase / sum(NP_j*M_j).
Volume fractions require appropriate phase densities or molar volumes as well. Do not
compare molar fractions directly to microscopy area fractions without explaining the
conversion and sampling assumptions.

For this elemental workflow, molar energies and amounts use a mole of non-vacancy
atoms, not a mole of an arbitrary compound formula unit. `Model.GM` is normalized on
that basis; `Model.G` is formula energy and can differ with sublattice site ratios.
Site fractions `v.Y(phase, sublattice_index, species)` are internal degrees of freedom,
not bulk mole fractions. Sublattice indices are zero-based.

The tested conversion API is `v.get_mole_fractions({v.W('NI'): 0.5}, 'CU', db)`;
it uses the TDB elemental masses and returns a condition mapping keyed by `v.X('NI')`.
For the bundled masses, 50 wt% Ni is X(Ni)=0.5198487558, not 0.5. No conversion is
performed by the JSON helper itself.

## Native model, property, and plotting contracts

These examples were executed with pycalphad 0.11.2. Paths below are relative to the
collection root. `Database(path)` parses local thermodynamic data; successful parsing
does not establish that the assessment or every model feature is suitable. Review TDB
warnings rather than suppressing all warnings. `db.elements`, `db.phases`, and each
phase's `constituents`, `sublattices`, and `model_hints` expose the modeled system.

`Model(db, components, phase)` builds a symbolic energy model, not an equilibrium.
`calculate(..., output='GM', T=..., P=..., pdens=...)` samples its phase-constitution
surface. Its `points` columns are ordered internal site fractions: use the model's
`site_fractions` order; do not pass overall alloy compositions as points for a
multisublattice model. In the one-sublattice teaching FCC model only, `[0.5, 0.5]`
coincides with 50:50 bulk composition. `calculate` does not minimize across phases.
Pass sampling options to `equilibrium` or `Workspace` through `calc_opts`, not as
top-level `pdens`; unused equilibrium keyword arguments merely produce a warning.

```python
import numpy as np
from pycalphad import Database, Workspace, variables as v

db = Database('skills/pycalphad/assets/ideal-cu-ni.tdb')
components = ['CU', 'NI', 'VA']
phases = ['FCC_A1', 'LIQUID']
conditions = {v.T: [900, 1100, 1300], v.P: 101325, v.N: 1, v.X('NI'): 0.5}
wks = Workspace(db, components, phases, conditions, calc_opts={'pdens': 500})
temperature = wks.get(v.T)
phase_amounts = wks.get_dict('NP(*)')
gm = wks.get('GM')                  # system molar Gibbs energy, J/mol
x_solid = wks.get(v.X('FCC_A1', 'NI'))
assert np.allclose(temperature, [900, 1100, 1300])
assert np.isfinite(gm).all()
assert np.isnan(x_solid[-1])         # absent solid; NaN is not a failed equilibrium
```

Use `get_dict` when phase multiplicity can change. A request such as `NP(FCC_A1)`
or `X(FCC_A1,NI)` expands to `#1`, `#2`, ... properties for a miscibility gap; `get`
can consequently return a list of arrays rather than one array. Preserve those sets
and only sum their amounts when a total phase-name fraction is intended. Suffixes
identify solver composition sets, not permanent ordered/disordered identities.
Inspect compositions and site fractions before assigning physical labels. Property
arrays squeeze singleton condition axes; use `wks.condition_axis_order` for grids.

`GM` and `HM` are J/mol; `SM` and `CPM` are J/(mol K). A phase-qualified property,
such as `GM(FCC_A1)`, is that stable composition set's property, whereas unqualified
`GM` is phase-amount-weighted. `CPM` differentiates the model at fixed constitution;
`wks.get('HM.T')` differentiates equilibrium enthalpy as temperature changes, including
phase amounts and internal relaxation. They need not agree. At 1100 K the hypothetical
two-phase example has `CPM=0` but `HM.T` approximately 1005.08 J/(mol K), matching a
small central difference of equilibrium enthalpy. Derivatives at phase boundaries or
invariant points require special care; a finite derivative is not a latent-heat integral.

For a small binary phase diagram, the current top-level `binplot` uses the mapping API:

```python
import matplotlib.pyplot as plt
from pycalphad import binplot

ax, strategy = binplot(
    db, components, phases,
    {v.T: (900, 1300, 100), v.P: 101325, v.N: 1, v.X('NI'): (0.3, 0.7, 0.1)},
    return_strategy=True,
)
ax.set_title('Hypothetical ideal binary; not assessed Cu-Ni')
ax.figure.savefig('hypothetical-binary.png', dpi=150, bbox_inches='tight')
plt.close(ax.figure)
```

The default return is an Axes; `return_strategy=True` returns `(Axes, BinaryStrategy)`.
Pass plot options in `plot_kwargs`; other keywords configure the mapper. `binplot`
requires one varying composition and one varying potential coordinate. A fixed-bulk
temperature sweep is better plotted directly from `Workspace` properties or the CSV.
For `equilibrium`/`Workspace`, a tuple is `(start, stop, step)` with an excluded stop;
a list is explicit values. Mapping uses tuple bounds and increments to follow phase
boundaries, not just a Cartesian equilibrium grid. A smooth plot alone does not
validate all stable fields; check representative points and refine difficult boundaries.

Official sources checked for these contracts:

- [Stable Model and variables source](https://github.com/pycalphad/pycalphad/tree/0.11.2/pycalphad)
- [Stable Workspace and composition conditions](https://github.com/pycalphad/pycalphad/tree/0.11.2/pycalphad/core)
- [Stable property framework](https://github.com/pycalphad/pycalphad/tree/0.11.2/pycalphad/property_framework)
- [Stable mapping compatibility API](https://github.com/pycalphad/pycalphad/blob/0.11.2/pycalphad/mapping/compat_api.py)
- [Current property and ordering workflow](https://pycalphad.org/docs/latest/examples/2_Computing_Properties/4_EquilibriumWithOrdering.html)

## Phase selection and solver checks

`VA` supports vacancy sublattices and is omitted from overall elemental mass balance.
Select actual elements present in the database. A required vacancy or other constituent
missing from every active species in one sublattice can make a phase unavailable.
The helper rejects phase lists that pycalphad filters, including redundant coupled
order/disorder selections, so the agent can review rather than silently alter them.

Excluding a phase can lower the number of stable phases and change apparent solubility.
An excluded phase list is therefore scientific provenance. Preserve each composition
set in miscibility gaps: summing fractions by phase name is useful for totals but loses
the two distinct tie-line endpoints. Never use a vertex index as a persistent phase ID.

Mass balance, phase-sum checks, and finite Gibbs energy are necessary but not sufficient.
Doubled `pdens` only tests one initialization-density change. Repeat with more density,
inspect nearby conditions, compare alternative candidate phase sets, or use a trusted
reference calculation when the result affects a scientific conclusion. Degenerate phase
fractions at invariant points may be nonunique even when Gibbs energies agree. The
helper's flags should be interpreted with that thermodynamic context.

The native regression suite also loads the small `alni_dupin_2001.tdb` shipped in
pycalphad 0.11.2, checks order/disorder filtering, and verifies an Al-Ni equilibrium
point at 1000 K and X(Al)=0.25. That is a release integration check, not independent
experimental validation of the database. No proprietary database is bundled or used.

Parameter uncertainty is separate from numerical sampling sensitivity. Without an
assessment's covariance/posterior or another justified uncertainty model, doubled
`pdens` cannot yield confidence intervals. Database coverage, omitted phases, reference
states, and extrapolation can dominate errors even when two numerical runs agree.

Preserve the actual TDB with the output under its licensing terms. A SHA-256 identifies
bytes but does not document assessment quality, reference-state conventions, or the
validity range. Include the database authors' citation and uncertainty/coverage limits
in the final scientific report.
