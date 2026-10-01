# Input contract, schema version 1

Use the bundled JSON assets as runnable templates. The CLI rejects unknown fields,
duplicate JSON keys, nonfinite numbers, negative fractions, and incomplete mixtures.
All files are local. No Python expressions, model scripts, pickles, or remote URLs
are evaluated from input data.

## Model

Required top-level fields: `schema_version` (integer 1), `name`, `flux_unit`,
`provenance`, `metabolites`, `reactions`, `fragments`.
The three text fields must be nonempty. IDs start with an ASCII letter and contain
only ASCII letters/digits, at most 40 characters. This avoids upstream renaming and
protects the mfapy code generator. Use distinct IDs for compartments, such as `CitM`
and `CitC`; explain their meaning in provenance.

### Metabolites

Each has `id`, integer `carbons` (1–12), `boundary` (`source`, `internal`, `sink`),
and optional boolean `symmetric` (default false).

- Sources are external carbon inputs with explicitly prescribed labeling. They may
  only appear on the substrate side. They are not steady-state-balanced pools.
- Sinks are external products, may only appear on the product side, and are not balanced.
- Internal pools must have a net-producing and a net-consuming reaction. Their
  steady-state stoichiometric balances are imposed for every fit and simulation.
- Symmetry is only the average of the given ordering and its complete reversal.
  It is allowed only for internal pools. Carbon numbering must make that reversal
  the correct physical permutation.

Limits are 100 metabolites, 200 reactions, 100 fragments. They bound the supported
input surface, not runtime: EMU construction can still be expensive for a complex
network. Begin with the smallest scientifically adequate model.

### Reactions

Each has `id`, `substrates`, `products`, `lower`, `upper`, and optional `fixed`.
Bounds are finite with `0 <= lower < upper`; `fixed` must lie inside them. All
reaction fluxes are nonnegative one-way event rates in `flux_unit`. A reversible
reaction is two reactions with inverse atom maps; their difference is the net flux.

Each reaction side is a list of `[metabolite_id, atom_labels]` pairs. For example:

```json
{
  "id": "condense",
  "substrates": [["AcCoA", "AB"], ["OAC", "CDEF"]],
  "products": [["Cit", "FEDBAC"]],
  "lower": 0.001,
  "upper": 300,
  "fixed": 100
}
```

Letters identify individual carbon atoms **within one reaction**, not globally.
Their order is the declared carbon numbering of each metabolite. Every letter on
the substrate side must occur exactly once on the product side. Include carbon
lost to CO2 as an explicit product; include fixed carbon as an explicit substrate.

Repeated molecules are separate occurrences: `[["Pyr","ABC"],["Pyr","DEF"]]`
means two pyruvates per reaction event, and the adapter builds coefficient 2 in
the mass balance. Fractional stoichiometry and untracked carbon-bearing cofactors
are not supported. Noncarbon balancing chemistry is outside this representation;
carbon conservation does not prove full elemental/charge conservation.

Positive lower bounds in demonstrations keep internal pools turning over. Do not
copy these bounds to real biology merely to obtain convergence. A truly inactive
pool may have no unique steady-state isotope distribution; remove it only when
scientifically justified, or model its transient behavior.

### Fragments

Each has `id`, `metabolite`, `carbons`, and nonempty `provenance`.
`carbons` is a unique list of **1-based positions** in an internal metabolite.
The prediction is the distribution of the number of labeled carbons in this subset,
ordered M+0 through M+N. Position order within the subset does not affect mass counts.

This is not a GC-MS chemical-formula parser. Derivatization atoms, natural heavy
isotopes of other elements, adducts, and MS/MS precursor/product selection must be
handled in a validated upstream measurement model. An arbitrary fragment name does
not establish its carbon assignment.

## Experiment and measurement file

Required fields:

```json
{
  "schema_version": 1,
  "steady_state": {"metabolic": true, "isotopic": true},
  "shared_fluxes": true,
  "mdv_basis": "tracer_only",
  "correction_notes": "Describe actual correction and tracer-purity handling here.",
  "experiments": []
}
```

The empty list above documents the envelope; at least one experiment is required.
Each experiment has a unique `id`, `substrates`, `measurements`, and optional
`flux_measurements`. An empty measurement list is useful for simulation only.

`substrates` maps **every** source ID to a dictionary of positional isotopomer
fractions. `{"100000": 0.98, "000000": 0.02}` describes a six-carbon feed with
98% carbon-1 labeling and 2% unlabeled molecules. All fractions must be nonnegative
and sum to one within 1e-10. Strings run carbon 1 to carbon N left to right.
Do not derive a positional distribution from whole-molecule mass counts alone.

`mdv_basis: "tracer_only"` asserts that nontracer natural abundance has already been
handled consistently. The simulator neither adds nor removes natural abundance.
If preprocessing also corrected tracer purity to an ideal tracer, do not encode
that impurity a second time. Record the basis and method explicitly; obtain the
upstream correction matrix or corrected covariance when needed.

### Mass-distribution measurements

Every measurement has `fragment`, full `mdv`, integer `omit`, and exactly one of
`covariance` or `sem`:

```json
{
  "fragment": "Bfirst",
  "mdv": [0.44, 0.56],
  "omit": 1,
  "covariance": [[0.0001, -0.0001], [-0.0001, 0.0001]]
}
```

For an N-carbon fragment, supply all N+1 fractions, nonnegative, summing to one
within the smaller of 1e-10 and 1e-5 times the smallest retained-bin standard error.
Supply sufficient precision from upstream normalization; the CLI does not silently
renormalize rounded measurements. `omit` is the **0-based mass-bin index**, not a carbon position.
Omit one bin because normalized fractions are linearly dependent. Missing measured
bins are not zeros: this schema requires a complete, justified distribution.

`covariance` is the (N+1)-square covariance of the **reported mean MDV**, in squared
fraction units. It must be symmetric with zero row/column sums and positive definite
after the omitted bin is removed. This preserves the sum constraint and supports
correlated errors. For independent replicate vectors, an estimate for the covariance
of their mean is sample covariance divided by replicate count. A rank-deficient
estimate needs a scientifically justified error model or more replicates; the CLI
does not silently add regularization.

Alternatively `sem` is an N+1-vector of strictly positive standard errors of the
reported fractions. The retained bins are treated as independent. This is an explicit
approximation; fit/profile results can depend on which bin is omitted. Distinguish SD
from SEM, analytical replicates from biological variability, and count noise from
uncertainty introduced by correction. Zero uncertainty is not an exact observation.

Different measurement blocks are treated as independent. Do not duplicate fragments
within an experiment or include overlapping fragments as independent measurements
without assessing their cross-fragment error correlation. A full cross-block covariance
is not supported. Analyze correlated blocks with an appropriate external likelihood.

### Extracellular flux measurements

```json
{"reaction": "uptake", "value": 100.0, "sem": 0.2}
```

Add these to `flux_measurements` using the same flux units as the network. They are
Gaussian observations, not exact constraints, and can anchor absolute scale. An
exact reference belongs in a reaction's `fixed` field. Do not copy the same measured
rate into every parallel tracer block: it would be counted repeatedly. Measurements
from independent cultures can be combined only if the common-flux assumption is valid.

## Forward-simulation flux file

A JSON object mapping every reaction ID to a finite numerical flux. No omitted
reactions or additional fields. The vector must satisfy internal balances, fixed
constraints, and bounds. Use the bundled flux files as examples.
