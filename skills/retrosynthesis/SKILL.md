---
name: retrosynthesis
description: Plans multi-step retrosynthetic routes to a small molecule with AiZynthFinder, using template-based expansion policies, a feasibility filter, and a purchasable-compound stock. Covers config files, MCTS and Retro* search settings, batch planning with aizynthcli, custom building-block stocks, route scores, solved flags, route export and clustering, and RDKit validation of targets and proposed routes. Use for retrosynthesis, synthesis planning, computer-aided synthesis planning (CASP), route scouting, synthetic accessibility by explicit route search, precursor or building-block selection, or when deciding between template-based and template-free single-step models.
license: MIT
compatibility: Requires Python 3.10-3.12 and aizynthfinder 4.4.1 (tested on 3.12 with pyarrow pinned below 26). Needs network access once to download public models and stock (about 0.8 GB), then runs offline on CPU. A search with the public ZINC stock holds about 5.8 GB of RAM per process. No credentials.
metadata:
  version: "1.0"
  skill-author: Arunkumar Eli
  tested-package-version: "4.4.1"
  last-reviewed: "2026-10-31"
---

# Retrosynthesis route planning with AiZynthFinder

## When to use

Use when a target molecule needs a **route to purchasable starting materials**:
route scouting for a hit or a lead, checking whether an analogue series is
reachable from what is already on the shelf, or turning a generated structure
into something a chemist can cost. Also use to decide between template-based
and template-free single-step models.

Do not use for single reaction outcome (forward) prediction, for yield
prediction, or as a synthetic-accessibility score on its own: SA-style scores
and `medchem` complexity filters are cheaper if no route is wanted. Property
prediction belongs to `deepchem` or `molfeat`, structure handling to `rdkit`.

A solved route is a **hypothesis supported by reaction precedent**, not a
validated procedure. It carries no conditions, no stoichiometry, no yield, and
no safety assessment, and the proposing policy was trained on patent reactions
whose own success is not guaranteed. Every route needs a chemist before it
reaches a bench.

## Install and get the public models

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install "aizynthfinder[all]==4.4.1" "pyarrow==25.0.1"
python -m aizynthfinder.tools.download_public_data ./aizynth-data
```

The `pyarrow` pin is required, not cosmetic: aizynthfinder 4.4.1 pins
`numpy<2.0`, and pyarrow 26 raises `ImportError: pyarrow requires NumPy 2.0 or
newer` on the first `import aizynthfinder.aizynthfinder`, because the import
chain reaches `rxnutils -> swifter -> dask.dataframe -> pyarrow`. Install the
`[all]` extra rather than the bare package: on a plain
`uv pip install aizynthfinder==4.4.1` the resolver chose `six==1.7.3` and the
import failed with `ModuleNotFoundError: No module named 'six.moves'`.

The download is about 0.8 GB (2 min 32 s here) and writes `config.yml` with
absolute paths to five artifacts: the USPTO expansion policy ONNX model and its
template file, the RingBreaker policy and templates, the quick-filter model,
and `zinc_stock.hdf5` (17,422,831 InChIKeys). All of it is CPU; the published
`onnxruntime` wheel exposes only `CPUExecutionProvider`, and AiZynthFinder sets
`intra_op_num_threads` to the physical core count per session. A GPU helps only
if you serve a template-free model separately, see
[references/alternatives.md](references/alternatives.md).

## Workflow

1. **Validate the targets first.** `scripts/prepare_targets.py` canonicalizes,
   strips salts, neutralizes, de-duplicates, and flags undefined stereocentres
   and uncommon elements, keeping a CSV row per input so a batch can be joined
   back to the submitted IDs. A target AiZynthFinder cannot sanitize raises
   `ValueError("Target molecule unsanitizable")` from `prepare_tree`, and an
   unparsable one raises a bare `AttributeError` on `NoneType.GetNumAtoms`.
2. **Decide what counts as purchasable before searching.** `is_solved` means
   "every leaf of the top-ranked route is in the selected stock", so the stock
   defines the answer. Use
   the lab's own building-block list for decisions about the lab, and the public
   ZINC stock only for a sanity check. See the stock section below.
3. **Search.** Start with MCTS defaults (`iteration_limit: 100`,
   `time_limit: 120`). If the target is unsolved, raise `iteration_limit`
   before touching anything else, and consider Retro\*.
4. **Read the statistics, not just the picture.** `is_solved`,
   `number_of_steps`, `number_of_solved_routes`, `top_score`,
   `precursors_not_in_stock` and `first_solution_iteration` together say whether
   the search had room to work.
5. **Check the routes mechanically.** `scripts/summarize_routes.py` flattens
   `aizynthcli` output into one row per route and flags steps whose product
   contains a heavy element absent from its reactants, unparsable SMILES, and
   steps that create a stereocentre no reactant had.
6. **Cluster before reading.** Top-k routes are often the same disconnection;
   `routes.cluster(n_clusters=0)` groups them so a chemist reviews distinct
   options.
7. **Report the stock, the model, the settings and the limits** with any route.

## Minimal runs, as executed

Single target, Python API:

```python
from aizynthfinder.aizynthfinder import AiZynthFinder

finder = AiZynthFinder(configfile="aizynth-data/config.yml")
finder.stock.select("zinc")
finder.expansion_policy.select("uspto")
finder.filter_policy.select("uspto")          # optional, prunes infeasible steps
finder.target_smiles = "CC(=O)Nc1ccc(O)cc1"   # paracetamol
finder.tree_search()
finder.build_routes()
stats = finder.extract_statistics()
print(stats["is_solved"], stats["number_of_steps"], stats["number_of_solved_routes"])
```

Batch, CLI:

```bash
python skills/retrosynthesis/scripts/prepare_targets.py targets.smi clean.smi --report targets.csv
aizynthcli --config aizynth-data/config.yml --smiles clean.smi \
  --policy uspto --filter uspto --stocks zinc --cluster --output output.json.gz
python skills/retrosynthesis/scripts/summarize_routes.py output.json.gz routes.csv
```

One SMILES on the command line writes `trees.json` (a list of route dicts) and
prints statistics; a file writes `output.json.gz`, read back with
`pandas.read_json(path, orient="table")`.

## Measured behaviour

All on 4 CPU cores of an AMD EPYC (Genoa) host, aizynthfinder 4.4.1,
onnxruntime 1.31.1, RDKit 2023.09.6, numpy 1.26.4, public USPTO policy plus
filter, ZINC stock. Startup is 5.0 s of imports, 0.4 s for the policy and 9.0 s
for the stock (4.6 GB of the 5.8 GB process RSS), so **amortize startup over a
batch** rather than per molecule.

| Target | Settings | Result |
| --- | --- | --- |
| Paracetamol | MCTS, 100 iterations | solved, 1 step, 3.3 s, 23 of 46 search-tree leaves solved, first solution at iteration 1, state score 0.998 |
| Sitagliptin | MCTS, 100 iterations | solved, 1 step, 9.3 s |
| Osimertinib | MCTS, 100 iterations | solved, 4 steps, 10.0 s, all 4 leaves in stock |
| Ibuprofen | MCTS, 100 iterations | **not solved**, 13.3 s, best route 6 steps with one leaf off-stock |
| Ibuprofen | MCTS, 500 iterations | solved, 3 steps, 46.5 s, first solution at iteration 127 (15.7 s) |
| Ibuprofen | MCTS, `return_first: true` | same route, stopped at iteration 128, 15.7 s, 1 solved route only |
| Ibuprofen | Retro\*, 100 iterations | solved, 2 steps, 17.1 s, first solution at iteration 6 |
| Osimertinib | DFPN, 100 iterations | not solved, 8.8 s |
| 5 chiral drugs, 300 iterations | `aizynthcli` batch | 3 of 5 solved, 119.8 s total; atorvastatin and oseltamivir unsolved |

Two readings worth keeping: an unsolved target at the default iteration limit
often just needs more iterations, and the search algorithm changes which
targets are reachable in a fixed budget more than the iteration count does.

## Stocks are the answer, so build them deliberately

The default `inchiset` stock matches on **InChIKey**, so a stock file of SMILES
loads without error and matches nothing. Measured on paracetamol with four
in-house building blocks: as InChIKeys it solved in 1 step with 12 solved
routes; the identical molecules as a SMILES file gave 0 in-stock precursors,
`is_solved: false`, and the target itself reported as not in stock.

```python
from rdkit import Chem
smiles = ["Nc1ccc(O)cc1", "CC(=O)OC(C)=O", "CC(=O)Cl"]
keys = [Chem.MolToInchiKey(Chem.MolFromSmiles(s)) for s in smiles]
open("inhouse_inchikeys.txt", "w").write("\n".join(keys) + "\n")
```

```yaml
stock:
  inhouse: /abs/path/inhouse_inchikeys.txt
  zinc: /abs/path/zinc_stock.hdf5
```

`smiles2stock --files blocks.smi --output stock.hdf5` does the same conversion
and is the better choice for large lists. Select several stocks at once
(`--stocks inhouse zinc`); `precursors_availability` then names the source per
precursor. A small stock does not make the search fail, it makes it return
unsolved routes: the in-house stock above left osimertinib unsolved with 4
off-stock leaves.

## Pitfalls, each observed here

| Symptom | Cause and fix |
| --- | --- |
| `ImportError: pyarrow requires NumPy 2.0 or newer` on import | pyarrow 26 against the pinned `numpy<2`. Install `pyarrow==25.0.1`. |
| `ModuleNotFoundError: No module named 'six.moves'` | bare `aizynthfinder` install resolved `six==1.7.3`. Install the `[all]` extra. |
| Nothing is in stock although the molecules are on the list | stock file holds SMILES, not InChIKeys. Convert with `MolToInchiKey` or `smiles2stock`. |
| A racemic or flat target is "not in stock" while its enantiomers are | lookup is by full InChIKey. ZINC held both ibuprofen enantiomers (`HEFNNWSXXWATRW-JTQLQIEISA-N`, `-SNVBAGLBSA-N`) but not `-UHFFFAOYSA-N`, the undefined-stereo form. Decide explicitly whether stereochemistry matters, and search the defined form if it does. |
| `is_solved: true` with `number_of_steps: 0` | the target is itself in stock and `exclude_target_from_stock` was set to false. Measured: 0 expansion calls, 1 "solved" route. Leave the default true. |
| `KeyError: 'Invalid key specified uspto when selecting expansion policy'` on a second finder | `Configuration.from_dict` pops `expansion`, `filter`, `stock` and `scorer` out of the dict you passed. Pass a fresh `copy.deepcopy` each time, or use `configfile`. |
| `TypeError: Object of type ndarray is not JSON serializable` mid-batch | `--cluster` together with `--checkpoint`: the cluster labels are a numpy array and the checkpoint writer cannot encode them. Either flag alone works. |
| `FileNotFoundError: ... 'aizynthcli'` with `--nproc` | `--nproc` re-invokes the bare command name, so the console script must be on `PATH`. With it set, `--nproc 2` ran 5 targets in 100.6 s against 119.8 s in one process, and each worker loads its own 4.6 GB stock. |
| A search ignores `time_limit` | the limit is checked **between** iterations. With breadth-first and `max_transforms: 6`, one iteration was still running 6 min 40 s into a `time_limit: 120` run; three iterations alone produced 4958 nodes. Bound breadth-first with `max_transforms` and a small `iteration_limit`. |
| Routes look identical | they often are, up to one reagent. Cluster them, and report `number_of_solved_routes` alongside the top route. |
| Memory spikes with parallel batches | each process holds the full stock in memory, about 5.8 GB with ZINC. Size `--nproc` by RAM, not by cores, or use a smaller stock. |

## Depth

- [references/configuration.md](references/configuration.md): every `search`,
  `expansion`, `filter`, `post_processing` and `stock` setting, the search
  algorithms and their measured character, multiple expansion policies.
- [references/analysis.md](references/analysis.md): scorers, the statistics
  columns, route dictionaries, images, distances and clustering, the single-step
  `AiZynthExpander`, and what the metadata on each step means.
- [references/alternatives.md](references/alternatives.md): template-based
  versus template-free, syntheseus, ASKCOS, IBM RXN, where Chemformer and
  LocalRetro stand, and how to attach a served model as an expansion policy.

## Upstream

- Documentation: <https://molecularai.github.io/aizynthfinder/>
- Source: <https://github.com/MolecularAI/aizynthfinder> (MIT)
- Genheden et al., AiZynthFinder: a fast, robust and flexible open-source
  software for retrosynthetic planning, *J. Cheminform.* 12, 70 (2020),
  <https://doi.org/10.1186/s13321-020-00472-1>
- Thakkar et al., Datasets and their influence on the development of computer
  assisted synthesis planning tools, *Chem. Sci.* 11, 154 (2020),
  <https://doi.org/10.1039/C9SC04944D>
