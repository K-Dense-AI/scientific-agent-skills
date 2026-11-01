# Choosing a retrosynthesis method

Repository status below was read from GitHub on 2026-10-31. Only AiZynthFinder
was installed and run for this skill; everything else here is a pointer, not a
tested claim. Check each project's license before using its weights: several
release models trained on data with noncommercial terms.

## Single-step model families

**Template-based** (the AiZynthFinder USPTO policy, ASKCOS template relevance,
MHNreact, LocalRetro in its own way). A neural network ranks reaction templates
extracted from a reaction corpus, and the template is applied with RDChiral or
RDKit. Every proposal is a chemically valid molecule and carries a precedent,
the template, that a chemist can inspect. Coverage is bounded by the template
library, so chemistry absent from the corpus is unreachable, and rare templates
are poorly ranked.

**Template-free sequence models** (Chemformer, RootAligned, Graph2Edits, MEGAN).
A transformer or graph-edit model generates reactant SMILES directly. These
generalize past a fixed template set and usually score better on single-step
top-k benchmarks, at the cost of possible invalid or non-mass-balanced outputs
and no precedent attached to a proposal. They are also much more expensive per
call, which matters inside a tree search that issues thousands of expansions.

Use template-based models as the default for multi-step planning on CPU. Reach
for a template-free model when the target's chemistry is outside the template
library, when you need disconnections at specific bonds, or when a published
single-step comparison on your own reaction set says so.

## Multi-step planners and services

- **AiZynthFinder** (MolecularAI, MIT, active, last push 2026-04-13). MCTS plus
  Retro*, DFPN and breadth-first; template-based ONNX policies run on CPU;
  public USPTO models and a ZINC stock download with one command. Reference:
  Genheden et al., *J. Cheminform.* 12, 70 (2020),
  <https://doi.org/10.1186/s13321-020-00472-1>.
- **syntheseus** (Microsoft, MIT, active, last push 2026-10-30). A benchmarking
  layer with one interface over several search algorithms and wrappers for
  Chemformer, LocalRetro, RootAligned, GLN, MEGAN, MHNreact, RetroKNN and
  Graph2Edits. Use it to compare single-step models or search algorithms on the
  same footing rather than as a production planner. Reference: Maziarz et al.,
  *Faraday Discuss.* (2024), <https://doi.org/10.1039/D4FD00093E>.
- **ASKCOS** (MIT/MLPDS). The original `ASKCOS/ASKCOS` GitHub repository ended
  at v0.4.1 and its README directs users to the v2 GitLab deployment at
  <https://gitlab.com/mlpds_mit/askcosv2/askcos2_core>. Its README also states
  that the repository license does not cover the data and trained models, which
  are released for noncommercial use. Deployment is a Docker stack, not a pip
  install, so it is a service to call rather than a library to embed.
- **IBM RXN for Chemistry** (`rxn4chemistry`, MIT, active). A Python client for
  a hosted API, so it needs an API key, sends structures off the machine, and
  has rate limits. Convenient for a second opinion on a disconnection; not
  suitable where structures cannot leave the environment.
- **SynPlanner** (Laboratoire de Chemoinformatique, MIT, active). Template
  extraction, policy training and MCTS in one package, with its own
  documentation; worth a look if you need to retrain templates end to end.

## Where Chemformer and LocalRetro stand

`MolecularAI/Chemformer` is **archived** (read-only since 2026-02-11). Its
README states the repository has been replaced by
[`MolecularAI/aizynthmodels`](https://github.com/MolecularAI/aizynthmodels),
which carries a refactored Chemformer along with the former `aizynthtrain`,
`route-distances` and `pysmilesutils` code, and it documents a checkpoint
migration step (`vocab_size` renamed to `vocabulary_size`) for old weights.
`MolecularAI/route-distances` is archived for the same reason, so the LSTM
route-distance model also now lives in `aizynthmodels`. Both archived
repositories still work, but file bug reports against `aizynthmodels` and
expect conda plus poetry rather than a wheel: `aizynthmodels` documents Python
3.8 to 3.10, below the 3.10 to 3.12 that AiZynthFinder 4.4.1 requires, so plan
on two environments and a REST boundary between them.

`kaist-amsg/LocalRetro` is not archived (last push 2026-01-27) but is research
code built on DGL with its own data preparation scripts; it has no PyPI
package. The pre-packaged wrapper in `syntheseus` is usually the faster route
to a runnable LocalRetro.

## Serving a template-free model to AiZynthFinder

AiZynthFinder keeps expensive models out of process and calls them over HTTP, so
a GPU-served model fits without changing the planner. `plugins/expansion_strategies.py`
in the AiZynthFinder repository ships `ChemformerBasedExpansionStrategy` and
`DisconnectionAwareExpansionStrategy`; both take a `url` and are selected by
putting the `plugins` directory on `PYTHONPATH`:

```yaml
expansion:
  standard:
    type: template-based
    model: uspto_model.onnx
    template: uspto_templates.csv.gz
  chemformer:
    type: expansion_strategies.ChemformerBasedExpansionStrategy
    url: http://localhost:8000/chemformer-api/predict
  multi_expansion:
    type: aizynthfinder.context.policy.MultiExpansionStrategy
    expansion_strategies: [chemformer, standard]
    additive_expansion: true
    cutoff_number: 50
search:
  algorithm_config:
    immediate_instantiation: [chemformer]
  time_limit: 300
```

The upstream how-to raises `time_limit` for exactly this reason: each expansion
now costs a network round trip plus a beam search, so the same iteration count
takes far longer. `immediate_instantiation` instantiates children as soon as
the node is expanded, which avoids paying for the remote call twice.

Two practical notes, neither verified here:

- The service is the model's own REST wrapper, not something AiZynthFinder
  starts. Chemformer's service script lives in its repository, and the plugin
  only posts SMILES to the URL you give it.
- A vLLM or SGLang deployment serves token generation for a chat or completion
  API, which is not the interface these plugins post to. Pointing the plugin at
  such an endpoint requires a shim that converts a SMILES request into the
  server's request format and the generated text back into reactant SMILES,
  including validity filtering with RDKit.
