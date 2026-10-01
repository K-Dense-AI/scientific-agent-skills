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

Preserve the actual TDB with the output under its licensing terms. A SHA-256 identifies
bytes but does not document assessment quality, reference-state conventions, or the
validity range. Include the database authors' citation and uncertainty/coverage limits
in the final scientific report.
