# AiZynthFinder 4.4.1 configuration reference

Every setting below was read from the AiZynthFinder 4.4.1 source and
documentation; the behaviour notes marked "measured" come from CPU runs with
the public USPTO models and the ZINC stock (see `SKILL.md` for the hardware).

## Minimal configuration

`download_public_data <dir>` writes exactly this shape, with absolute paths:

```yaml
expansion:
  uspto:
    - uspto_model.onnx
    - uspto_templates.csv.gz
  ringbreaker:
    - uspto_ringbreaker_model.onnx
    - uspto_ringbreaker_templates.csv.gz
filter:
  uspto: uspto_filter_model.onnx
stock:
  zinc: zinc_stock.hdf5
```

A two-item list under an `expansion` key is the shorthand for
`{type: template-based, model: ..., template: ...}`. A bare string under
`filter` or `stock` is the shorthand for the single required file. Relative
paths are resolved against the process working directory, not the config file,
so prefer absolute paths or always launch from the same directory.

Values may reference environment variables as `${NAME}`. A missing variable
raises `ValueError` at config load, which is a useful way to force an explicit
choice in a pipeline.

## search

| Key | Default | Notes |
| --- | --- | --- |
| `algorithm` | `mcts` | Or a `package.module.ClassName` path to another search tree. |
| `max_transforms` | 6 | Maximum depth, in reactions, of the search tree. |
| `iteration_limit` | 100 | Iterations, not expansions; MCTS does one selection, expansion, rollout and update per iteration. |
| `time_limit` | 120 | Seconds. The loop checks both limits and stops at whichever comes first. |
| `return_first` | False | Stop at the first solved route. Useful for triage, not for route comparison. |
| `exclude_target_from_stock` | True | If the target itself is purchasable it is excluded, so the search still produces a route. |
| `break_bonds` / `freeze_bonds` | `[]` | Lists of atom-index pairs in the target; used for disconnection-aware search. |
| `break_bonds_operator` | `and` | `and` requires every listed bond broken, `or` any one of them. |

`algorithm_config` (MCTS):

| Key | Default | Notes |
| --- | --- | --- |
| `C` | 1.4 | Exploration constant in the upper confidence bound. Higher explores more. |
| `default_prior` | 0.5 | Used only when `use_prior` is False. |
| `use_prior` | True | Use the policy probability as the node prior. |
| `prune_cycles_in_search` | True | Blocks re-creating a molecule already seen on the path. |
| `search_rewards` | `[state score]` | More than one entry turns on multi-objective MCTS. |
| `search_rewards_weights` | `[]` | Weights for the combined scorer. |
| `immediate_instantiation` | `[]` | Expansion policies whose children are instantiated at expansion time; intended for expensive remote models. |
| `mcts_grouping` | unset | `partial` or `full`; groups expansions that lead to the same state. |

## expansion (template-based)

| Key | Default | Notes |
| --- | --- | --- |
| `template_column` | `retro_template` | Column in the template file. |
| `cutoff_cumulative` | 0.995 | Keep templates until their cumulative probability passes this. |
| `cutoff_number` | 50 | Hard cap on templates returned per expansion. The main cost knob. |
| `use_rdchiral` | True | Apply templates with RDChiral, which preserves stereochemistry better than plain RDKit template application. |
| `use_remote_models` | False | Try a TensorFlow Serving endpoint first; needs the `tf` extra and `TF_SERVING_HOST`, `TF_SERVING_REST_PORT`, `TF_SERVING_GRPC_PORT`. |
| `rescale_prior` | False | Softmax the kept priors. |
| `mask` | `""` | Path to an `.npz` boolean vector masking templates, for example to disable chemistry your lab will not run. |

## filter (quick-filter)

| Key | Default | Notes |
| --- | --- | --- |
| `filter_cutoff` | 0.05 | Reactions the feasibility model scores below this are rejected. |
| `exclude_from_policy` | `[]` | Filter names to skip. |
| `use_remote_models` | False | As above. |

The filter policy only removes reactions during search. In
`AiZynthExpander.do_expansion` it does not remove anything: it adds a
`feasibility` value to each reaction's metadata.

## post_processing

| Key | Default | Notes |
| --- | --- | --- |
| `min_routes` | 5 | Lower bound on extracted routes. |
| `max_routes` | 25 | Upper bound, unless `all_routes`. |
| `all_routes` | False | Extract every solved route; falls back to the min/max window when nothing is solved. |
| `route_scorer` / `route_scorers` | `state score` | Scorer used to rank extracted routes. Defaults to `search.algorithm_config.search_rewards` when unset. |
| `route_distance_model` | unset | Checkpoint for the LSTM route-distance model used by clustering. |

## stock

Three input shapes are accepted by the default `inchiset` query
(`InMemoryInchiKeyQuery`):

- `.h5` / `.hdf5`: a pandas frame stored under the key `table` with an
  `inchi_key` column.
- `.csv`: a column named `inchi_key` (`inchi_key_col` renames it), plus an
  optional `price_col`.
- anything else: a plain text file with one InChIKey per line.

**The text form holds InChIKeys, not SMILES.** A file of SMILES loads without
error and matches nothing, because lookup is `mol.inchi_key in keys`. Measured:
a four-SMILES file loaded as a stock reported 0 in-stock precursors for
paracetamol, while the same four molecules as InChIKeys solved it in one step.

Other query types: `mongodb` (`MongoDbInchiKeyQuery`, needs the `all` extra and
a collection with `inchi_key` and `source` fields) and `bloom`
(`MolbloomFilterQuery`, a `.bloom` file; `smiles_based: true` switches lookup to
SMILES). A path ending in `.bloom` selects the bloom query automatically. Any
class subclassing `StockQueryMixin` and implementing `__contains__` can be
named under `type:`.

`stop_criteria` ends a branch on price, amount, weight or element counts:

```yaml
stock:
  inhouse: inhouse_inchikeys.txt
  stop_criteria:
    price: 10
    counts:
      C: 10
```

Price and amount criteria require a query that can answer those queries;
`InMemoryInchiKeyQuery` answers prices only when built from a frame with
`price_col`, and raises `StockException` otherwise.

## Search algorithms

`mcts` is the default and the only one addressed by name; the others are given
as class paths:

| `algorithm` value | Character |
| --- | --- |
| `mcts` | Monte Carlo tree search, prior-guided, anytime. Measured: the best-supported path, and the only one with multi-objective rewards. |
| `aizynthfinder.search.retrostar.search_tree.SearchTree` | Retro\* AND/OR search with an optional learned molecule cost. Measured: found a solved osimertinib route at iteration 4 against MCTS's iteration 1, and a two-step solved ibuprofen route at iteration 6 where MCTS needed 127 iterations. |
| `aizynthfinder.search.dfpn.search_tree.SearchTree` | Depth-first proof-number search. Measured: 100 iterations in 8.8 s on osimertinib but no solved route, and it is slow to extract routes from large trees. Each iteration expands at most two nodes, so iteration counts are not comparable with MCTS. |
| `aizynthfinder.search.breadth_first.search_tree.SearchTree` | Breadth-first AND/OR expansion. Exhaustive at shallow depth, and the iteration cost grows quickly with `max_transforms`. |

Retro\* with a learned cost needs the value-model pickle from the PaRoutes
repository:

```yaml
search:
  algorithm: aizynthfinder.search.retrostar.search_tree.SearchTree
  algorithm_config:
    molecule_cost:
      cost: aizynthfinder.search.retrostar.cost.RetroStarCost
      model_path: retrostar_value_model.pickle
      fingerprint_length: 2048
      fingerprint_radius: 2
      dropout_rate: 0.1
```

Without `molecule_cost`, Retro\* uses a constant oracle. Loading a pickle
executes code from it, so only load one you fetched yourself from the
publishing repository.

## Multiple expansion policies

```yaml
expansion:
  uspto:
    - uspto_model.onnx
    - uspto_templates.csv.gz
  ringbreaker:
    - uspto_ringbreaker_model.onnx
    - uspto_ringbreaker_templates.csv.gz
  multi_expansion_strategy:
    type: aizynthfinder.context.policy.MultiExpansionStrategy
    expansion_strategies: [uspto, ringbreaker]
    additive_expansion: true
    cutoff_number: 50
```

Then `aizynthcli --policy multi_expansion_strategy`. Selecting two policy keys
on the command line (`--policy uspto ringbreaker`) also works and is what the
measured ringbreaker run used. Expect roughly double the expansion cost:
measured 58.8 s for 300 MCTS iterations with both policies against 46.5 s for
500 iterations with the USPTO policy alone, same target and machine. The
ringbreaker model is trained for ring-forming disconnections, so it earns its
cost on targets whose rings have to be built rather than substituted.
