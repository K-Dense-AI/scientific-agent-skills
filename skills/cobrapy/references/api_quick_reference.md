# COBRApy API reference

Checked against cobra **0.32.1** installed signatures/source and current official
docs. Examples with `model` assume a fresh `load_model("textbook")`; placeholders
such as `filename` are illustrative, not standalone runnable commands.

## Model I/O and repository contracts

```python
from cobra.io import (
    load_model, read_sbml_model, write_sbml_model,
    load_json_model, save_json_model, load_yaml_model, save_yaml_model,
    load_matlab_model, save_matlab_model,
)

model = load_model("textbook")  # Local, model.id == "e_coli_core"
# Also local: load_model("iJO1366"), load_model("salmonella")
# Remote illustrative calls; adapters may fail at redirects (see below):
# model = load_model("e_coli_core")
# model = load_model("iML1515")

# Illustrative file I/O: use your actual paths.
# model = read_sbml_model("model.xml.gz")
# write_sbml_model(model, "model.xml")
# save_json_model(model, "model.json", pretty=True)
# model = load_json_model("model.json")
# save_yaml_model(model, "model.yml")
# model = load_yaml_model("model.yml")
# save_matlab_model(model, "model.mat", varname="model")
# model = load_matlab_model("model.mat", variable_name="model")
```

MATLAB I/O needs SciPy (`cobra[array]`). Keep the default SBML `f_replace` mapping
unless intentionally preserving SBML-encoded IDs; `f_replace={}` disables prefix
and character conversion. Verify identifiers after round-trip before selecting an
objective. Formats may not retain arbitrary custom solver constraints; store those
separately and reconstruct them on reload.

`load_model(model_id, repositories=..., cache=True)` searches bundled data, BiGG,
then BioModels. In released 0.32.1 the `cache` argument is unused despite its
docstring: save downloaded files explicitly. A non-404 HTTP failure aborts lookup;
it does not necessarily fall through to the next provider. Repository-specific
IDs are not interchangeable. The BioModels adapter only supports a directly listed
XML file; OMEX-only records require an explicitly chosen SBML extraction workflow.

Verified unauthenticated provider routes (2026-09-30):

| Provider | Request and response | Current adapter caveat |
| --- | --- | --- |
| BiGG | `GET https://bigg.ucsd.edu/static/models/{id}.xml.gz` returns gzip-compressed SBML; iML1515 parsed as 2,712 reactions | 0.32.1 uses HTTP and does not follow the HTTP-to-HTTPS redirect |
| BioModels files | `GET https://www.biomodels.org/model/files/{id}` with `Accept: application/json`; `main` is a list of file records with `name` and `fileSize` | 0.32.1 uses the bare hostname and does not follow its listing redirect |
| BioModels download | `GET https://www.biomodels.org/model/download/{id}?filename={name}` returns the selected file; follow redirects | Select an actual XML name from the listing, not an invented name or arbitrary first file |

These are single-model/file operations with no pagination or credentials. The
`MODEL1510010000` listing and selected XML download were executed and parsed. That BioModels file lacked an optimization objective and many explicit flux bounds,
so its successful parse is not a validated FBA model. SDK
remote failures were observed separately; they do not mean the services retired.

A bounded BiGG fallback, executed on iML1515:

```python
from pathlib import Path
from urllib.request import urlopen
from cobra.io import read_sbml_model

path = Path("iML1515.xml.gz")  # Use the task's output directory.
with urlopen("https://bigg.ucsd.edu/static/models/iML1515.xml.gz", timeout=30) as response:
    data = response.read(16 * 1024 * 1024 + 1)
if len(data) > 16 * 1024 * 1024:
    raise ValueError("Model exceeds this example's 16 MiB download limit")
path.write_bytes(data)
model = read_sbml_model(path)
assert len(model.reactions) == 2712
```

For BioModels, fetch the JSON listing, choose `main` entries whose `name` ends in
`.xml`, URL-encode that filename using `urllib.parse.urlencode`, and use the download
route in the table with the same finite timeout/size check. Save the original file,
retrieval date and checksum. Do not assume every SBML record is a constraint-based
metabolic model with the required objective and flux bounds.

## Core objects and editing

```python
from cobra import Model, Reaction, Metabolite, Gene
from cobra.io import load_model

model = load_model("textbook")
reaction = model.reactions.get_by_id("PFK")
metabolite = model.metabolites.get_by_id("atp_c")
print(reaction.bounds, reaction.gene_reaction_rule, metabolite.formula)
print(model.exchanges, model.demands, model.sinks, model.boundary)

# DictList.query uses a regular expression, case-sensitive by default.
import re
matches = model.reactions.query(re.compile("atp", re.IGNORECASE))
glycolytic = model.reactions.query(lambda r: r.subsystem == "Glycolysis")
assert "PFK" in model.reactions

# Temporary changes are restored when the model context exits.
with model:
    reaction.bounds = (0, 5)
    reaction.gene_reaction_rule = "gene1 and (gene2 or gene3)"
    model.genes.get_by_id("gene1").knock_out()
    solution = model.optimize()
```

Use `add_reactions([reaction])`, not removed `add_reaction`. Set GPRs on reactions
so associated genes and reverse links are updated; do not mutate `model.genes`
directly to remove genes. For permanent deletion use
`cobra.manipulation.remove_genes(model, ["gene_id"], remove_reactions=True)` and
inspect affected GPRs/reactions. `remove_reactions([...])` accepts IDs or objects;
`remove_metabolites([...], destructive=False)` removes them from stoichiometries
and needs biological review.

`model.copy()` creates an independent model. To form a subset, copy each reaction:
`new_model.add_reactions([r.copy() for r in chosen_reactions])`; adding the same
Reaction objects to another model risks moving their model/solver associations.
A reaction is reversible when **both** `lower_bound < 0` and `upper_bound > 0`.

### Balanced toy network and gap filling

A mass/charge-balanced isomerization illustrates building without creating an
unphysical ATP source. Boundary reactions deliberately connect the model to its
environment. The toy's demand objective is product export, not a growth rate.

```python
from cobra import Model, Reaction, Metabolite
from cobra.flux_analysis import gapfill

model = Model("toy")
model.solver = "glpk"
a_e = Metabolite("a_e", formula="C6H12O6", charge=0, compartment="e")
a_c = Metabolite("a_c", formula="C6H12O6", charge=0, compartment="c")
b_c = Metabolite("b_c", formula="C6H12O6", charge=0, compartment="c")
transport = Reaction("T", lower_bound=0, upper_bound=1000)
transport.add_metabolites({a_e: -1, a_c: 1})
conversion = Reaction("A_TO_B", lower_bound=0, upper_bound=1000)
conversion.add_metabolites({a_c: -1, b_c: 1})
conversion.gene_reaction_rule = "(gene1 and gene2) or gene3"
model.add_reactions([transport, conversion])
model.add_boundary(a_e, type="exchange", lb=-10, ub=1000)
model.add_boundary(b_c, type="demand")
model.objective = "DM_b_c"
assert conversion.check_mass_balance() == {}
assert abs(model.slim_optimize(error_value=None) - 10) < 1e-6

universal = Model("candidates")
universal.add_reactions([conversion.copy()])
model.remove_reactions(["A_TO_B"])
assert abs(model.slim_optimize(error_value=None)) < 1e-6
solutions = gapfill(
    model, universal=universal, lower_bound=1.0,
    demand_reactions=False, exchange_reactions=False, iterations=1,
)
# Each entry is a LIST of Reaction objects; input model remains unchanged.
assert [[r.id for r in candidate] for candidate in solutions] == [["A_TO_B"]]
with model:
    model.add_reactions([r.copy() for r in solutions[0]])
    assert model.slim_optimize(error_value=None) >= 1 - 1e-6
```

`gapfill(..., penalties=None)` supports reaction-ID and category penalties
(`universal`, `exchange`, `demand`). Defaults permit added demand reactions but not
exchanges. `iterations=5` reuses one GapFiller and increases costs of used reactions;
five fresh calls do not preserve that penalty history or guarantee unique answers.
For real data, use a curated universal reaction model with matched metabolite IDs,
compartments, chemistry and directionality. Do not treat a MILP-selected reaction
as evidence that the organism encodes it.

## Optimization and solution interpretation

```python
from cobra.io import load_model
from cobra.flux_analysis import pfba, geometric_fba

model = load_model("textbook")
solution = model.optimize(raise_error=True)
print(solution.status, solution.objective_value)
print(solution.fluxes, solution.shadow_prices, solution.reduced_costs)
value = model.slim_optimize(error_value=None)
with model:
    model.objective = "ATPM"  # Also accepts Reaction or {Reaction: coefficient}.
    model.objective_direction = "max"
    atp_solution = model.optimize(raise_error=True)
    print("ATPM flux:", atp_solution.objective_value)  # Not biomass growth.

parsimonious = pfba(model, fraction_of_optimum=1.0)
centered = geometric_fba(model, epsilon=1e-6, max_tries=200, processes=1)
```

`pfba` first optimizes the specified objective, then minimizes total absolute flux.
Its returned objective is that secondary sum. Read the biomass flux explicitly.
Dual values are solver/problem dependent; integer problems need not provide them.
A default `slim_optimize()` failure returns NaN; use `error_value=None` to raise.
Do not label any feasible objective as growth unless it is the growth objective.

`model.solver.configuration` exposes `timeout`, `verbosity` and supported tolerance
settings. Inspect `cobra.util.solver.solvers` before selecting `glpk`, `hybrid`,
`cplex`, or `gurobi`. Optional commercial solvers require installation/licensing;
GLPK does not support quadratic objectives. Set and report realistic tolerances,
not a silently unsupported solver-specific setting.

## Analysis contracts

| Operation | Relevant arguments | Return and interpretation |
| --- | --- | --- |
| `flux_variability_analysis` | `reaction_list=None`, `loopless=None`, `fraction_of_optimum=1.0`, `pfba_factor=None`, `processes=1` | DataFrame indexed by reaction ID, `minimum`/`maximum`; extrema optimized independently |
| `single_gene_deletion` | `gene_list=None`, `method="fba"`, `solution=None`, `processes=1` | DataFrame columns `ids` (set), `growth`, `status` |
| `single_reaction_deletion` | `reaction_list=None`, same method/solution/process arguments | Same schema; objective must be growth to call the result growth |
| `double_gene_deletion` | `gene_list1`, `gene_list2`, method/solution/process arguments | Same schema; singleton sets are self-pairs, not double mutants |
| `double_reaction_deletion` | `reaction_list1`, `reaction_list2`, method/solution/process arguments | Same schema; no MultiIndex assumption |
| `find_blocked_reactions` | `reaction_list=None`, `zero_cutoff=None`, `open_exchanges=False`, `processes=1` | List of **ID strings** in released implementation; cutoff cannot be smaller than model tolerance |
| `find_essential_genes` / `find_essential_reactions` | `threshold=None`, `processes=1` | Sets of Gene / Reaction objects; default cutoff is 1% of objective optimum; inspect failed solves separately |
| `production_envelope` | `reactions`, `objective=None`, `carbon_sources=None`, `points=20`, `threshold=None` | Grid DataFrame with reaction coordinates, `flux_minimum`, `flux_maximum`, `carbon_yield_*`, `mass_yield_*`, `carbon_source` |

FVA loopless choices are `"fastSNP"` (optimal loopless bounds) and
`"cycleFreeFlux"` (loop removal without guaranteed optimal bounds); booleans are
deprecated. A `pfba_factor` greater than one caps the total flux relative to pFBA.
Loopless does not mean full thermodynamic consistency with measured energies.

`production_envelope` accepts IDs or reaction objects for scanned reactions.
The grid has `points ** len(reactions)` rows, so bound its dimension and resolution.
`threshold` is a numerical zero cutoff, not a minimum objective requirement;
default uses model tolerance. Set growth requirements explicitly. Yields need a
single interpretable output objective and suitable carbon/formula annotations;
missing or zero denominators can produce NaN. Two-axis plots should visualize the
objective value as a surface/color, not only scatter the input coordinates.

### Sampling

```python
from cobra.io import load_model
from cobra.sampling import sample, OptGPSampler, ACHRSampler

model = load_model("textbook")
samples = sample(model, n=20, method="achr", thinning=100, seed=7)
sampler = OptGPSampler(model, processes=1, thinning=100, seed=7)
samples = sampler.sample(20)
validation = sampler.validate(samples)
assert (validation == "v").all()
for batch in sampler.batch(10, 2):
    assert len(batch) == 10
```

`sample(..., method="auto")` now chooses CHRR if hopsy is installed, otherwise
OptGP. Use `"optgp"`, `"achr"`, or optional `"chrr"` explicitly. ACHR uses one
process; OptGP can return more than `n` samples when `n` is not divisible by
`processes`. CHRR requires `cobra[chrr]` and incurs an initial rounding cost;
that backend was not executed here. Validation codes `v`, `l`, `u`, `e` indicate
valid, lower-bound, upper-bound and equality checks; codes may combine violations.
Thinning and a passing feasibility check do not establish chain convergence.

### Media

```python
from cobra.medium import minimal_medium

medium = model.medium
medium["EX_glc__D_e"] = 10.0
medium["EX_o2_e"] = 20.0
model.medium = medium
min_medium = minimal_medium(
    model, min_objective_value=0.1, exports=False,
    minimize_components=False, open_exchanges=False,
)
```

There is **no `penalties` argument** to `minimal_medium` in 0.32.1. Its default
minimizes total import flux; `minimize_components=True` uses MILP to minimize
component count. With `open_exchanges=False`, the allowed nutrient universe stays
fixed but the optimizer selects the subset and import bounds within it. An integer
greater than one asks for alternative media. The
return is a Series, a DataFrame of alternatives, or None on failure. `exports`
controls whether exporting fluxes appear in the returned medium; it does not
control whether secretion is allowed in the model. The medium mapping lists
positive import bounds; assigning it closes omitted import directions while
retaining export bounds.

## Validation and summaries

`reaction.check_mass_balance()` returns elemental/charge imbalances or an empty
dict, but missing formulas or charges can prevent a meaningful check. The
`cobra.manipulation.check_mass_balance(model)` helper excludes annotated
boundary/biomass/pseudo reactions. `check_metabolite_compartment_formula(model)`
only checks whether nonempty formulas are alphanumeric: despite its name it does
not comprehensively validate chemical formulas, compartment assignment, or charges.
Use the explicit missing-data and exception reporting in [workflows](workflows.md).

`model.summary()`, `model.metabolites.atp_c.summary()` and
`model.reactions.PFK.summary()` return summary objects. `model.summary(fva=0.95)`
adds FVA at that fraction. Summaries often compute pFBA internally; state the
constraints and objective rather than treating them as measured fluxes.

## Official sources and release/source distinctions

- [0.32.1 release](https://github.com/opencobra/cobrapy/releases/tag/0.32.1)
- [Model I/O](https://cobrapy.readthedocs.io/en/latest/io.html)
- [Released model loader](https://github.com/opencobra/cobrapy/blob/0.32.1/src/cobra/io/web/load.py)
- [Released BiGG adapter](https://github.com/opencobra/cobrapy/blob/0.32.1/src/cobra/io/web/bigg_models_repository.py)
- [Released BioModels adapter](https://github.com/opencobra/cobrapy/blob/0.32.1/src/cobra/io/web/biomodels_repository.py)
- [BiGG iML1515 record](https://bigg.ucsd.edu/models/iML1515)
- [Model methods](https://cobrapy.readthedocs.io/en/latest/autoapi/cobra/core/model/index.html)
- [Flux analysis](https://cobrapy.readthedocs.io/en/latest/autoapi/cobra/flux_analysis/index.html)
- [Minimal medium signature](https://cobrapy.readthedocs.io/en/latest/autoapi/cobra/medium/minimal_medium/index.html)
- [Released sampler selection](https://github.com/opencobra/cobrapy/blob/0.32.1/src/cobra/sampling/sampling.py)

Some generated API prose still describes the old deletion index or blocked-reaction
object type. The released implementation, tutorial tables and executed return
values are the authority for the schemas recorded here.
