# COBRApy workflows

The five Python workflows below were executed with cobra 0.32.1, GLPK, and Python
3.12 on the bundled textbook model. They are small demonstrations, not validated
predictions for an organism or condition. Run this setup first, then each workflow
independently; each loads a fresh model. Plotting needs matplotlib/seaborn. Choose
`OUTDIR` from the task context; authorization to produce outputs covers those files.

```python
from pathlib import Path
import cobra

OUTDIR = Path("cobrapy_output")
OUTDIR.mkdir(parents=True, exist_ok=True)
cobra.Configuration().solver = "glpk"
cobra.Configuration().processes = 1
```

## Workflow 1: Knockouts and synthetic-lethal candidates

The 1% wild-type growth threshold is an analysis choice. Separate successful
low-growth predictions from infeasible, numerical, or other unresolved solves.
The `ids` column contains sets, including singletons for self-pairs. Never derive
identifiers from the integer row index. GPR redundancy means one gene need not
correspond to one reaction. A bounded subset is a screen, not an exhaustive study.

```python
import pandas as pd
import matplotlib.pyplot as plt
from cobra.io import load_model
from cobra.flux_analysis import single_gene_deletion, double_gene_deletion

model = load_model("textbook")
baseline = model.slim_optimize(error_value=None)
assert baseline > 0
threshold = 0.01 * baseline
single_results = single_gene_deletion(model, processes=1)
valid_single = single_results[
    single_results.status.eq("optimal") & single_results.growth.notna()
].copy()
valid_single["gene"] = valid_single.ids.map(lambda ids: next(iter(ids)))
single_by_gene = valid_single.set_index("gene")["growth"]
low_growth = valid_single[valid_single.growth < threshold]
unresolved_single = single_results.drop(valid_single.index)
target_genes = sorted(single_by_gene[single_by_gene >= 0.5 * baseline].index)[:30]
double_results = double_gene_deletion(
    model, gene_list1=target_genes, gene_list2=target_genes, processes=1,
)
synthetic_lethals = double_results[
    double_results.status.eq("optimal")
    & double_results.growth.lt(threshold)
    & double_results.ids.map(
        lambda ids: len(ids) == 2
        and all(single_by_gene.get(g, float("nan")) >= 0.5 * baseline for g in ids)
    )
].copy()

fig, ax = plt.subplots()
valid_single.growth.hist(bins=25, ax=ax)
ax.axvline(baseline, color="red", linestyle="--", label="Wild type")
ax.set(xlabel="Predicted growth (1/h)", ylabel="Number of genes")
ax.legend()
fig.savefig(OUTDIR / "single_deletion_distribution.png", dpi=150)
plt.close(fig)
# Sort identifiers for reproducible, human-readable CSVs.
for name, table in [("single", single_results), ("double", double_results),
                    ("synthetic_lethals", synthetic_lethals)]:
    exported = table.assign(ids=table.ids.map(lambda ids: ";".join(sorted(ids))))
    exported.sort_values("ids").to_csv(OUTDIR / f"{name}_deletions.csv", index=False)
print("Low-growth single mutants:", len(low_growth))
print("Unresolved single mutants:", len(unresolved_single))
print("Candidate synthetic-lethal pairs:", len(synthetic_lethals))
```

## Workflow 2: Minimal and custom media

With `open_exchanges=False`, the **allowed nutrient universe stays fixed**. The
optimizer still **selects the nutrient subset and its import bounds** within that
universe; the selected nutrients and amounts are not fixed. This workflow therefore
minimizes component count within allowed nutrients, then rechecks the selected
medium. Opening all exchanges expands the allowed universe, permits alternative
carbon sources, and defines a different experiment. Minimal media may be nonunique; integer tolerances can affect tiny
imports. Report the objective, growth target and tested uptake units.

```python
import pandas as pd
from cobra.io import load_model
from cobra.medium import minimal_medium

model = load_model("textbook")
baseline = model.slim_optimize(error_value=None)
assert baseline > 0
minimal_media = {}
rechecked_growth = {}
for fraction in [0.25, 0.5, 0.75, 0.95]:
    target = fraction * baseline
    medium = minimal_medium(
        model, min_objective_value=target,
        minimize_components=True, open_exchanges=False,
    )
    if medium is None:
        raise RuntimeError(f"No medium found for growth {target}")
    with model:
        model.medium = medium.to_dict()
        growth = model.slim_optimize(error_value=None)
        assert growth >= target - 1e-6
    minimal_media[fraction] = medium
    rechecked_growth[fraction] = growth
pd.DataFrame(minimal_media).fillna(0).to_csv(OUTDIR / "minimal_media.csv")

# Retain valid IDs and other nutrients in this model; textbook has no EX_so4_e.
custom_medium = model.medium
custom_medium["EX_glc__D_e"] = 5.0
custom_medium["EX_o2_e"] = 0.0
with model:
    model.medium = custom_medium
    custom_growth = model.slim_optimize(error_value=None)
    limiting = []
    if custom_growth > model.tolerance:
        for exchange, bound in custom_medium.items():
            if bound <= 0:  # Doubling zero is not nutrient supplementation.
                continue
            with model:
                altered = model.medium
                altered[exchange] = 2 * bound
                model.medium = altered
                growth = model.slim_optimize(error_value=None)
                if growth > 1.01 * custom_growth:
                    limiting.append((exchange, growth / custom_growth - 1))
print("Custom growth:", custom_growth, "Candidate limiting imports:", limiting)
```

## Workflow 3: Matched FVA and sampling

FVA constraints are temporary. Explicitly install the growth floor **before**
creating the sampler. Compare samples with FVA from that same constrained model.
OptGP feasibility checks do not measure convergence; use independent seeds/chains,
trace plots and effective sample size for scientific inference. Correlation from
stoichiometric constraints is not evidence of regulation or causation.

```python
import matplotlib.pyplot as plt
import seaborn as sns
from cobra.io import load_model
from cobra.flux_analysis import flux_variability_analysis
from cobra.sampling import OptGPSampler

model = load_model("textbook")
biomass_id = "Biomass_Ecoli_core"
baseline = model.slim_optimize(error_value=None)
key_reactions = ["PFK", "FBA", "TPI", "GAPD", "PGK", "PGM", "ENO", "PYK"]
fva_optimal = flux_variability_analysis(
    model, reaction_list=key_reactions, fraction_of_optimum=1.0, processes=1,
)
with model:
    model.reactions.get_by_id(biomass_id).lower_bound = 0.9 * baseline
    fva_sampled = flux_variability_analysis(
        model, reaction_list=key_reactions, fraction_of_optimum=0.0, processes=1,
    )
    sampler = OptGPSampler(model, processes=1, thinning=100, seed=7)
    samples = sampler.sample(500)
    assert (sampler.validate(samples) == "v").all()
    assert (samples[biomass_id] >= 0.9 * baseline - 1e-6).all()

for reaction_id in key_reactions:
    assert samples[reaction_id].min() >= fva_sampled.loc[reaction_id, "minimum"] - 1e-6
    assert samples[reaction_id].max() <= fva_sampled.loc[reaction_id, "maximum"] + 1e-6
fig, ax = plt.subplots()
samples.PFK.hist(bins=25, ax=ax)
for bound in fva_sampled.loc["PFK", ["minimum", "maximum"]]:
    ax.axvline(bound, color="red", linestyle="--")
ax.set(xlabel="PFK flux (mmol/gDW/h)", ylabel="Frequency")
fig.savefig(OUTDIR / "matched_flux_distribution.png", dpi=150)
plt.close(fig)
correlation = samples[key_reactions].corr()
fig, ax = plt.subplots()
sns.heatmap(correlation, vmin=-1, vmax=1, center=0, cmap="coolwarm", ax=ax)
fig.tight_layout()
fig.savefig(OUTDIR / "flux_correlations.png", dpi=150)
plt.close(fig)
samples.to_csv(OUTDIR / "flux_samples.csv", index=False)
fva_optimal.to_csv(OUTDIR / "fva_optimal.csv")
fva_sampled.to_csv(OUTDIR / "fva_sampled.csv")
```

## Workflow 4: Product coupling at a common growth floor

For affected reactions whose bounds already allow zero, deletion removes feasible
flux states; it cannot increase the global product maximum if other constraints
are identical. Verify this premise: resetting a forced nonzero reaction to zero
can instead relax an original requirement. Instead, this screen asks whether
minimum acetate secretion increases at the **same absolute growth floor**, while
recording growth capacity and maximum secretion. A higher minimum is a conditional
coupling prediction, not proof of better experimental production. Ranking only one
arbitrary FBA solution can mistake alternate optima for improved production.

```python
import pandas as pd
import matplotlib.pyplot as plt
from cobra.io import load_model
from cobra.flux_analysis import production_envelope, flux_variability_analysis

model = load_model("textbook")
biomass_id = "Biomass_Ecoli_core"  # Explicit model-specific objective, not solver variable order.
product_id = "EX_ac_e"
baseline = model.slim_optimize(error_value=None)
growth_floor = 0.1 * baseline
with model:
    model.reactions.get_by_id(biomass_id).lower_bound = growth_floor
    envelope = production_envelope(
        model, reactions=["EX_glc__D_e"], objective=product_id,
        carbon_sources=["EX_glc__D_e"], points=12,
    )
    wt_range = flux_variability_analysis(
        model, reaction_list=[product_id], fraction_of_optimum=0.0, processes=1,
    ).loc[product_id]
    records = []
    for gene in sorted(model.genes, key=lambda g: g.id):
        with model:
            gene.knock_out()
            growth_solution = model.optimize()
            record = {"gene": gene.id, "status": growth_solution.status}
            if growth_solution.status == "optimal":
                product_range = flux_variability_analysis(
                    model, reaction_list=[product_id], fraction_of_optimum=0.0,
                    processes=1,
                ).loc[product_id]
                record.update(max_growth=growth_solution.objective_value,
                              product_min=product_range.minimum,
                              product_max=product_range.maximum)
            records.append(record)
knockout_results = pd.DataFrame(records)
feasible = knockout_results[knockout_results.status.eq("optimal")].copy()
# Bounds can differ by solver tolerance, but a strict subset cannot raise the maximum.
assert (feasible.product_max <= wt_range.maximum + 1e-6).all()
candidates = feasible[feasible.product_min > wt_range.minimum + 1e-6]
candidates = candidates.sort_values("product_min", ascending=False)
knockout_results.to_csv(OUTDIR / "product_coupling_screen.csv", index=False)

plot_data = envelope.assign(uptake=-envelope.EX_glc__D_e).sort_values("uptake")
fig, ax = plt.subplots()
ax.plot(plot_data.uptake, plot_data.flux_maximum, label="Maximum acetate flux")
ax.plot(plot_data.uptake, plot_data.flux_minimum, label="Minimum acetate flux")
ax.set(xlabel="Glucose uptake (mmol/gDW/h)", ylabel="Acetate secretion (mmol/gDW/h)")
ax.legend()
fig.savefig(OUTDIR / "production_envelope.png", dpi=150)
plt.close(fig)
print("Conditional coupling candidates:", len(candidates))
```

Do not automatically combine the best single knockouts: rerun combined genotypes
under the identical medium and growth requirement. Report failed statuses and any
trade-off in growth or secretion bounds. Yield requires a nonzero, correctly
oriented substrate flux; flux units are not yield units.

## Workflow 5: Validation and bounded diagnostics

Feasibility, chemistry, connectivity, and loop constraints answer different
questions. Missing formulas/charges make chemical validation incomplete. Boundary,
biomass and pseudoreactions have deliberate bookkeeping exceptions; inspect them
rather than declaring every nonzero imbalance an error. A direction-aware local
dead-end screen is only a topology heuristic, not flux consistency.

```python
import pandas as pd
from cobra.io import load_model
from cobra.flux_analysis import find_blocked_reactions, flux_variability_analysis

model = load_model("textbook")
solution = model.optimize()
status = solution.status
objective_value = solution.objective_value if status == "optimal" else None
missing_chemistry = [m.id for m in model.metabolites if not m.formula or m.charge is None]
excluded_sbo = {"SBO:0000627", "SBO:0000628", "SBO:0000629", "SBO:0000631", "SBO:0000632"}
excluded_ids = {"Biomass_Ecoli_core"} | {r.id for r in model.boundary}
unbalanced = {}
unchecked = []
for reaction in model.reactions:
    if reaction.id in excluded_ids or reaction.annotation.get("sbo") in excluded_sbo:
        continue
    if any(m.id in missing_chemistry for m in reaction.metabolites):
        unchecked.append(reaction.id)
        continue
    try:
        imbalance = reaction.check_mass_balance()
    except ValueError:
        unchecked.append(reaction.id)
        continue
    if imbalance:
        unbalanced[reaction.id] = imbalance

tol = model.tolerance
dead_end_candidates = []
for met in model.metabolites:
    producers, consumers = set(), set()
    for reaction in met.reactions:
        coefficient = reaction.metabolites[met]
        if (coefficient > 0 and reaction.upper_bound > tol) or (coefficient < 0 and reaction.lower_bound < -tol):
            producers.add(reaction.id)
        if (coefficient < 0 and reaction.upper_bound > tol) or (coefficient > 0 and reaction.lower_bound < -tol):
            consumers.add(reaction.id)
    if not producers or not consumers:
        dead_end_candidates.append(met.id)

# Exact stoichiometric duplicates only; compare bounds/GPRs before merging anything.
seen, duplicates = {}, []
for reaction in model.reactions:
    key = tuple(sorted((m.id, c) for m, c in reaction.metabolites.items()))
    if key in seen:
        duplicates.append((seen[key], reaction.id))
    else:
        seen[key] = reaction.id
orphan_genes = [g.id for g in model.genes if not g.reactions]
blocked, loop_sensitive = None, None
if status == "optimal":
    blocked = find_blocked_reactions(model, open_exchanges=False, processes=1)
    subset = ["PFK", "FRD7", "SUCDi"]
    ordinary = flux_variability_analysis(model, subset, processes=1)
    loopless = flux_variability_analysis(model, subset, loopless="fastSNP", processes=1)
    loop_sensitive = [rid for rid in subset if
                      ordinary.loc[rid, "maximum"] > loopless.loc[rid, "maximum"] + 1e-6
                      or ordinary.loc[rid, "minimum"] < loopless.loc[rid, "minimum"] - 1e-6]
else:
    print("[FAIL] Original model status:", status)
    with model:
        medium = {r.id: 1000.0 for r in model.exchanges}
        model.medium = medium
        diagnostic = model.optimize()
        print("Open-import diagnostic status:", diagnostic.status)
    # Do not overwrite the original status or claim a structural cause from this alone.
report = {
    "model_id": model.id, "status": status, "objective_value": objective_value,
    "missing_chemistry": len(missing_chemistry), "unchecked_internal": len(unchecked),
    "unbalanced_internal": len(unbalanced), "dead_end_candidates": len(dead_end_candidates),
    "exact_duplicate_pairs": len(duplicates), "orphan_genes": len(orphan_genes),
    "blocked_in_current_medium": None if blocked is None else len(blocked),
    "loop_sensitive_in_tested_subset": None if loop_sensitive is None else len(loop_sensitive),
}
pd.DataFrame([report]).to_csv(OUTDIR / "validation_report.csv", index=False)
print(report)
```

A negative loop screen on three reactions is not a whole-model thermodynamic
certificate. Growth, knockouts, media, and sampling all depend on the model's
objective, uptake bounds, maintenance costs, and solver tolerances.

## Official sources

- [Deletion tutorial](https://cobrapy.readthedocs.io/en/latest/deletions.html)
- [Media tutorial](https://cobrapy.readthedocs.io/en/latest/media.html)
- [Sampling tutorial](https://cobrapy.readthedocs.io/en/latest/sampling.html)
- [FVA API and loopless methods](https://cobrapy.readthedocs.io/en/latest/autoapi/cobra/flux_analysis/variability/index.html)
- [Production-envelope API](https://cobrapy.readthedocs.io/en/latest/autoapi/cobra/flux_analysis/phenotype_phase_plane/index.html)
