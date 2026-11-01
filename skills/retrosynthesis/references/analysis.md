# Reading AiZynthFinder results

Everything below was run with aizynthfinder 4.4.1, the public USPTO expansion
and filter policies, and the ZINC stock, on CPU.

## Statistics

`finder.extract_statistics()` after `build_routes()`, and every column of a
batch `output.json.gz`, carry these fields. The ones that decide whether a
result is usable:

| Field | What it actually says |
| --- | --- |
| `is_solved` | Every leaf of the **top-ranked** route is in the selected stock, and nothing about the other routes. It is the top-ranked node's state, so under multi-objective ranking it can be false while `number_of_solved_routes` is positive. |
| `number_of_steps` | Reactions in the top-scored route. |
| `number_of_solved_routes` / `number_of_routes` | Leaf nodes of the **search tree**, not the extracted set: 23 solved of 46 for paracetamol, 0 of 150 for ibuprofen at 100 iterations, while `len(finder.routes)` for that ibuprofen run was 8. `post_processing.min_routes` and `max_routes` govern extraction. |
| `top_score` | The top-ranked route's score under the active scorer, `state score` by default. Not a probability of success, and `None` under multi-objective ranking, where the per-route scores in `trees` are the ones to read. |
| `first_solution_iteration`, `first_solution_time` | 0 when nothing was solved. A value close to the iteration limit means the budget was the binding constraint. |
| `precursors_in_stock`, `precursors_not_in_stock` | Comma-separated SMILES. The second is the shopping list, or the reason the target is unsolved. |
| `precursors_availability` | Semicolon-separated per precursor, naming each stock that holds it, which is how you tell an in-house hit from a catalogue hit. |
| `number_of_nodes`, `max_transforms`, `max_children` | Shape of the search tree, useful to see whether the search explored or thrashed. |
| `profiling` | `expansion_calls`, `reactants_generations`, `iterations`. Measured: 284 expansion calls and 2433 reactant generations for a 100-iteration paracetamol search against a small stock, 33 and 479 against ZINC, because a solved node stops being expanded. |
| `policy_used_counts` | Expansion calls per policy, the check that a second policy is really contributing. |
| `stock_info`, `trees` | Per-leaf availability and the route dictionaries. Batch output only. |

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
score` combines the fraction of precursors in stock with route length, and it
is what guides MCTS; the other scorers only rank afterwards. Additional
scorers in the package include average template occurrence, sum of prices,
route cost (Badowski et al., *Chem. Sci.* 2019, 10, 4640), stock availability,
broken bonds, reaction-class membership, delta synthetic complexity, and route
similarity to reference routes. Rank with the one that matches the decision:
price if the question is cost, template occurrence if the question is how well
precedented the steps are.

```yaml
post_processing:
  route_scorer: number of reactions   # or a list under route_scorers
```

## Route dictionaries

A route is a nested dict alternating molecule and reaction nodes, which is what
`trees.json`, the `trees` column, and `ReactionTree.to_dict()` all contain:

```python
from aizynthfinder.reactiontree import ReactionTree
tree = ReactionTree.from_dict(route_dict)
tree.is_branched()                      # convergent route or linear
[r.smiles for r in tree.reactions()]    # mapped retro SMILES, product>>reactants
[(m.smiles, tree.in_stock(m)) for m in tree.leafs()]
tree.depth(tree.root)                   # 0 at the target
tree.hash_key()                         # stable identity for de-duplication
tree.metadata                           # {'created_at_iteration': 1, 'is_solved': True}
```

Molecule nodes carry `in_stock`; reaction nodes carry metadata the policy
produced. Measured keys on a USPTO expansion: `template_hash`,
`classification`, `library_occurence`, `policy_probability`,
`policy_probability_rank`, `policy_name`, `template_code`, `template`,
`mapped_reaction_smiles`, and `feasibility` when a filter policy ran.

Three of those are the ones to read:

- `policy_probability` is the model's confidence in the **template**, not in
  the reaction working. 0.74 for the top osimertinib amide coupling.
- `library_occurence` is how often the template appears in the training corpus.
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
Fewer than 3 routes returns an empty array rather than raising. Setting
`post_processing.route_distance_model` switches to the LSTM tree-edit-distance
model, which needs a checkpoint you supply.

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

The ranking by policy probability and the ranking by feasibility disagree: the
second and third proposals are plausible templates applied to the wrong
oxidation state or protecting pattern, and the filter model is what separates
them. In the expander the filter only annotates; inside a tree search a
reaction below `filter_cutoff` (default 0.05) is dropped, which is why the
third proposal would not survive a search.

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
