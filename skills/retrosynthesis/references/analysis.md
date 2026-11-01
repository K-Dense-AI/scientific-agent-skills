# Reading AiZynthFinder results

Everything below was run with aizynthfinder 4.4.1, the public USPTO expansion
and filter policies, and the ZINC stock, on CPU.

## Statistics

`finder.extract_statistics()` after `build_routes()`, and every column of a
batch `output.json.gz`, carry these fields. The ones that decide whether a
result is usable:

| Field | What it actually says |
| --- | --- |
| `is_solved` | Whether the **top-ranked** route's leaves are all in the selected stock, and nothing about the other routes. Under multi-objective ranking it is not a Boolean at all but a pipe-joined string over the Pareto front, see below. |
| `number_of_steps` | The top-ranked MCTS state's `max_transforms`, which is the route's **depth**. For a convergent route that is fewer than the number of reactions, so do not read it as a step count: count `tree.reactions()`, or the `steps` column from `summarize_routes.py`. |
| `number_of_solved_routes` / `number_of_routes` | Under MCTS, childless nodes of the **search tree**, not the extracted set: 23 solved of 46 for paracetamol, 0 of 150 for ibuprofen at 100 iterations, while `len(finder.routes)` for that ibuprofen run was 8. Under the AND/OR algorithms (Retro\*, DFPN, breadth-first) the same fields count what `search_tree.routes()` returns, so the two are not comparable. `post_processing.min_routes` and `max_routes` govern extraction either way. |
| `top_score` | The top-ranked route's score under the active scorer, `state score` by default. Not a probability of success, and `None` under multi-objective ranking, where the per-route scores in `trees` are the ones to read. |
| `first_solution_iteration`, `first_solution_time` | 0 when nothing was solved. A value close to the iteration limit means the budget was the binding constraint. |
| `precursors_in_stock`, `precursors_not_in_stock` | Comma-separated SMILES. The second is the shopping list, or the reason the target is unsolved. |
| `precursors_availability` | Semicolon-separated per precursor, naming each stock that holds it, which is how you tell an in-house hit from a catalogue hit. |
| `number_of_nodes`, `max_transforms`, `max_children` | Shape of the search tree, useful to see whether the search explored or thrashed. |
| `profiling` | `expansion_calls`, `reactants_generations`, `iterations`. Measured: 284 expansion calls and 2433 reactant generations for a 100-iteration paracetamol search against a small stock, 33 and 479 against ZINC, because a solved node stops being expanded. |
| `policy_used_counts` | Reaction actions in the search tree per policy, read off every node-child edge, not the number of model calls. Still the check that a second policy is contributing. |
| `stock_info`, `trees` | Per-leaf availability and the route dictionaries. Batch output only. |

**Multi-objective searches change the shape of these fields.** With
`search_rewards: ["state score", "number of reactions"]` on osimertinib,
`top_score` was `None` and the per-route fields came back as pipe-joined
strings across the Pareto front: `is_solved` as
`True|True|...|False|False` (31 entries) and `number_of_steps` as
`4|4|5|5|6|...`. Anything parsing these fields has to handle both shapes, and
the per-route scores in `trees` are the reliable source under multi-objective
ranking.

A batch file is a pandas "table" JSON:

```python
import pandas as pd
data = pd.read_json("output.json.gz", orient="table")
data[["target", "is_solved", "number_of_steps", "top_score", "number_of_solved_routes"]]
```

`--cluster` adds `cluster_labels`, `cluster_time` and `distance_matrix`. The
upstream documentation also lists a `top_scores` column; 4.4.1 writes
`top_score` only, so select columns from `data.columns` rather than from the
documentation.

## Scorers

`AiZynthFinder` loads four by default: `state score`, `number of reactions`,
`number of pre-cursors`, `number of pre-cursors in stock`. After
`routes.compute_scores(*finder.scorers.objects())` each route carries all four:

```python
finder.routes.all_scores[0]
# {'state score': 0.975, 'number of reactions': 4,
#  'number of pre-cursors': 4, 'number of pre-cursors in stock': 4}
```

`routes.scores` holds one dict per route keyed by the active scorer, so a
multi-objective search and a single-objective one read the same way. `state
score` is `0.95 * fraction_of_precursors_in_stock + 0.05 * squashed_depth`
(`StateScorer` in `context/scoring/scorers.py`, the depth term squashed around
`max_transforms` 4), so it is dominated by purchasability and only mildly
prefers short routes. It guides MCTS by default, but it is not privileged:
`search.algorithm_config.search_rewards` decides which scorers guide the
search, and any configured scorer can be named there. Otherwise scorers only
rank; the other scorers only rank afterwards. Additional
scorers in the package include average template occurrence, sum of prices,
route cost (Badowski et al., *Chem. Sci.* 2019, 10, 4640), stock availability,
broken bonds, reaction-class membership, delta synthetic complexity, and route
similarity to reference routes. Rank with the one that matches the decision:
price if the question is cost, template occurrence if the question is how well
precedented the steps are.

```yaml
post_processing:
  route_scorers:
    - number of reactions
```

## Route dictionaries

A route is a nested dict alternating molecule and reaction nodes, which is what
`trees.json`, the `trees` column, and `ReactionTree.to_dict()` all contain:

```python
from aizynthfinder.reactiontree import ReactionTree
tree = ReactionTree.from_dict(route_dict)
tree.is_branched()                      # convergent route or linear
[r.smiles for r in tree.reactions()]    # see the note below: template-level, not whole molecules
[(m.smiles, tree.in_stock(m)) for m in tree.leafs()]
tree.depth(tree.root)                   # 0 at the target
tree.hash_key()                         # stable identity for de-duplication
tree.metadata                           # {'created_at_iteration': 1, 'is_solved': True}
```

A reaction node's own `smiles` is the applied template in
`product>>reactants` form with atom maps, so it shows the reacting fragments
rather than the whole molecules. For paracetamol's acetylation it reads
`[C:1]([CH3:2])(=[O:3])[N:4][cH3:5]>>CC(=O)O[C:1]([CH3:2])=[O:3].[N:4][cH3:5]`.
The fully mapped reaction between complete structures is
`metadata["mapped_reaction_smiles"]`, and the child molecule nodes hold the
reactant SMILES. Use those two, not the reaction node's `smiles`, when
exporting reactions elsewhere.

Molecule nodes carry `in_stock`; reaction nodes carry metadata the policy
produced. Measured keys on a USPTO expansion: `template_hash`,
`classification`, `library_occurence`, `policy_probability`,
`policy_probability_rank`, `policy_name`, `template_code`, `template`,
`mapped_reaction_smiles`, and `feasibility` when a filter policy ran.

Three of those are the ones to read:

- `policy_probability` is the model's confidence in the **template**, not in
  the reaction working. 0.74 for the top osimertinib amide coupling.
- `library_occurence` is the template library's own occurrence count, a column
  of `uspto_templates.csv.gz` alongside `template_code`, `retro_template`,
  `template_hash` and `classification`.
  1706 for the paracetamol acetylation with acetic anhydride, 13100 for a
  methyl-ether route. A single-digit occurrence is a rare template.
- `classification` comes from the template library's reaction-class
  annotation and is frequently `0.0 Unrecognized` with the public models, so do
  not build a filter on it without checking coverage.

Export:

```python
import json
json.dump(finder.routes.dict_with_extra(include_metadata=True, include_scores=True),
          open("routes.json", "w"), indent=2)
finder.routes.reaction_trees[0].to_image().save("route000.png")
```

Measured: 6 osimertinib routes serialized to 66 kB of JSON; one route image was
1830x602 px and 80 kB, rendered in 0.9 s. `CombinedReactionTrees` has
`to_dict()` and `to_visjs_page()` but no `to_image()`, so render routes
individually.

## Distances and clustering

Both need the `[all]` extra (`route-distances`, now folded into
`aizynthmodels` upstream). `RouteCollection.distance_matrix()` returns
`1 - simple_route_similarity`, computed from the route graphs with no model
file:

```python
distances = finder.routes.distance_matrix()          # (n, n), 0 on the diagonal
labels = finder.routes.cluster(n_clusters=0)         # 0 optimizes the count
```

Measured on 6 osimertinib routes: the matrix took 0.1 s, pairwise distances ran
from 0.004 to 0.239, and `n_clusters=0` chose 3 clusters with labels
`[2, 2, 1, 1, 0, 0]`. Distances that small mean the top routes were minor
variants, which is the normal case and the reason to cluster before reading.
Fewer than 3 routes returns an empty array rather than raising. `post_processing.route_distance_model` looks like a switch to the
LSTM tree-edit-distance model, but nothing in 4.4.1 reads it, so clustering
always uses the structural similarity above.

## Single-step expansion without a search

`AiZynthExpander` applies the policy once, which is the right tool for "what
disconnections does the model see here" and for scoring a chemist's proposed
step:

```python
import copy, yaml
from aizynthfinder.aizynthfinder import AiZynthExpander

expander = AiZynthExpander(configdict=copy.deepcopy(yaml.safe_load(open("config.yml"))))
expander.expansion_policy.select("uspto")
expander.filter_policy.select("uspto")
groups = expander.do_expansion("CC(=O)Nc1ccc(O)cc1", return_n=5)
for group in groups:
    reaction = group[0]
    print([m.smiles for m in reaction.reactants[0]], reaction.metadata["policy_probability"])
```

Measured for paracetamol, 0.88 s for five groups, `expander.stats` reporting 22
templates that did not apply:

| Precursors | `policy_probability` | `feasibility` | `library_occurence` |
| --- | --- | --- | --- |
| acetic anhydride + 4-aminophenol | 0.467 | 0.9998 | 1706 |
| acetic anhydride + 4-nitrophenol | 0.132 | 0.163 | 170 |
| 4-methoxyacetanilide | 0.084 | 0.054 | 13100 |
| acetyl chloride + 4-aminophenol | 0.072 | 0.9999 | 5220 |
| 4-acetamidophenyl acetate | 0.070 | 0.559 | 964 |

The two rankings disagree. Policy probability puts the nitro compound second,
while the filter scores that step 0.163 and the acetyl chloride route, fourth by
policy probability, 0.9999. All five are chemistry a chemist can name, the
O-demethylation of 4-methoxyacetanilide at 0.054 included, so a low feasibility
score is the model's opinion about how usual a step is, not a verdict. What the
numbers do decide is survival inside a search: the filter rejects a reaction
when `prob < filter_cutoff` (default 0.05), so 0.054 passes by a small margin
and the 0.163 nitro route passes comfortably. In the expander the filter only
annotates and removes nothing.

`do_expansion` returns a list of tuples, where each tuple groups reactions that
give the same reactants, so `len(groups)` is a count of distinct precursor sets
and not of templates.

## Validating a route before trusting it

`scripts/summarize_routes.py` runs the mechanical checks on every route:

- every SMILES parses under RDKit;
- every heavy element in a product appears in at least the same count across
  that step's reactants, which catches a template that dropped atoms;
- a step whose product has more defined tetrahedral centres than its reactants
  is reported, because that is a step claiming to set stereochemistry.

Measured: of 47 routes over paracetamol, ibuprofen, osimertinib and
sitagliptin, none were flagged for element loss or unparsable SMILES. Of 72
routes over five chiral drugs, one naproxen route had a step that creates the
alpha-methyl centre from an achiral precursor. That is a legitimate asymmetric
step to propose and an unreasonable one to assume: the flag exists to put it in
front of a chemist, not to reject it.

What none of this checks: conditions, protecting-group compatibility,
chemoselectivity between similar sites, functional-group tolerance, scale, cost
and safety. Those stay with the chemist.
