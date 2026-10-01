# Molecular generation and PyTDC oracles

This reference targets **PyTDC 1.1.15**, verified 2026-10-01. Oracle names and
behavior are heterogeneous. Discover the installed registry and classify side
effects before constructing an `Oracle`.

## PyTDC's role

Core PyTDC provides:

- molecular corpora through `tdc.generation.MolGen`;
- `Evaluator` functions for generated sets;
- scalar, composite, checkpoint-backed, remote-service, and docking oracles.

It does not supply one universal trainable molecule generator. Users bring or
implement the generative model and must define a scientifically justified
objective, constraints, validation protocol, and experimental follow-up.

## Discover names without calling an oracle

```bash
uv run --no-project --isolated --python 3.11 --with "setuptools==80.9.0" --with "PyTDC==1.1.15" \
  python scripts/discover_metadata.py --kind oracles --limit 100
```

This reads `tdc.metadata.oracle_names`; it does not instantiate an oracle, download
a checkpoint/receptor, or transmit a SMILES string.

Use exact names. PyTDC fuzzy matching can silently normalize approximate input,
which is undesirable for expensive or remote operations.

## Side-effect categories in the stable metadata

### Local scalar property

Verified direct local scalar name:

```text
qed
```

`qed` requires RDKit but no PyTDC model artifact. It is the quantitative estimate
of drug-likeness; higher is more drug-like on its documented 0–1 scale.

Although upstream metadata groups `logp` and `sa` with “trivial” oracles, source
and execution verification show that both call `calculateScore`, which downloads
the `fpscores` artifact when absent. Treat both as download-backed.

### Local composite/GuacaMol-style objectives

The registry contains rediscovery, similarity, isomer, median, MPO, SMARTS, and hop
objectives. Some names use fixed targets; `*_meta` variants require constructor
arguments such as `target_smiles`.

Do not infer a constructor signature or score direction from the name. Read the
matching official oracle section and stable source before use. The bundled CLI does
not execute these objectives.

### Checkpoint-backed models

Stable download metadata includes:

```text
drd2, gsk3b, jnk3, cyp3a4_veith, fpscores,
drd2_current, gsk3b_current, jnk3_current
```

Constructing one can call Harvard Dataverse and write a model file beneath
`./oracle`. For DRD2/GSK3B/JNK3, PyTDC may normalize the request to a `_current`
checkpoint according to the installed scikit-learn version.

Checkpoint files are serialized model artifacts. Review source, origin, local path,
size, and trust boundary before download/loading. The bundled CLI supports only
bounded LogP/SA/DRD2/GSK3B/JNK3/CYP3A4_Veith calls and requires both `--execute`
and `--download`.

The 1.1.15 `LogP` oracle is not raw octanol/water partition alone. It implements
the normalized **penalized logP** objective: RDKit MolLogP plus a normalized
negative synthetic-accessibility term and a large-cycle penalty. Higher is the
objective's optimization direction. `SA` returns synthetic accessibility, for
which lower conventionally means easier synthesis. Do not combine either with
other scores without documenting transformation, scale, and direction.

### Distribution evaluators

The Oracle/Evaluator registries include:

```text
novelty, diversity, uniqueness, validity, fcd_distance, kl_divergence
```

These operate on collections, and several need a training/reference set. They are
not interchangeable scalar objectives:

- validity/uniqueness/novelty/diversity are higher by their documented definitions;
- `kl_divergence` returns mean `exp(-KL)`, so higher means closer distributions;
- `fcd_distance` returns transformed similarity with TensorFlow/FCD but raw distance
  with PyTorch/fcd_torch in 1.1.15; record backend and transformation before ranking;
- unpatched KL fails on modern SciPy because of removed `scipy.histogram`; see
  [utilities.md](utilities.md) for the verified compatibility limitation;
- novelty and distribution comparisons depend on the exact reference corpus and
  canonicalization;
- optional chemical-model dependencies may be substantial.

Use `Evaluator` and the official input signature. Do not send these through the
bundled scalar-scoring helper.

### Remote synthesis services

Metadata includes `askcos` and `ibm_rxn`. Official documentation describes extra
host/API inputs. Calling them can transmit molecular structures and credentials to
an external service.

Before any call:

1. identify the exact service operator and current terms;
2. determine whether the molecule is confidential or patent-sensitive;
3. obtain explicit user approval for transmission and cost;
4. read only the named credential required by that service;
5. never print or save the credential in JSON, logs, or command arguments;
6. enforce request/time/call limits.

The bundled script intentionally refuses these remote services. The 1.1.15 docs may
show historical endpoints or token flows; verify them with the service provider.

### Receptor and docking oracles

The registry contains PDB-specific names ending in `_docking`,
`_docking_normalize`, and `_docking_vina`, plus specialized names such as
`pyscreener`, `docking_score`, `smina`, `rmsd`, and `kabsch_rmsd`.

These paths can involve:

- receptor PDB/PDBQT downloads;
- local executables and substantial CPU/storage;
- user-specified box centers/sizes;
- generated conformers and temporary files;
- license restrictions for docking software;
- remote or proprietary synthesis scoring in benchmark evaluation.

Raw docking energies and normalized variants have different directions. Never infer
direction from a generic “Docking” label. The bundled molecular CLI and benchmark
CLI do not execute docking.

## Bounded local scoring

Plan first:

```bash
python scripts/molecular_generation.py score \
  --oracle QED \
  --smiles "CCO"
```

The JSON plan reports classification, input count, runtime directory, and required
acknowledgement. It does not instantiate `Oracle`.

Execute a local scalar only after review:

```bash
python scripts/molecular_generation.py score \
  --oracle QED \
  --smiles "CCO" \
  --execute
```

Execute a supported checkpoint-backed model only after approving the checkpoint:

```bash
python scripts/molecular_generation.py score \
  --oracle DRD2 \
  --smiles "CCO" \
  --runtime-dir .pytdc-oracles \
  --execute --download
```

The helper:

- accepts at most 500 SMILES and a 1 MiB input file;
- keeps output in input order with a zero-based index and explicit validity flag;
- emits `score: null` for invalid or zero-atom structures without scoring them;
- truncates long strings;
- never ranks candidates or assumes score direction;
- changes into the safe runtime directory so upstream `./oracle` writes remain
  contained;
- refuses remote services, docking, distribution metrics, and composite objectives.

## Direct Oracle API

After side-effect review:

```python
from tdc import Oracle

oracle = Oracle(name="QED", num_max_call=100)
scores = oracle(["CCO", "c1ccccc1"])
```

`num_max_call` bounds accumulated valid scalar calls for supported paths. It is not
a network timeout, memory limit, or cost limit.

For list input, PyTDC validates each SMILES with RDKit. Invalid entries can receive
the oracle's default value (commonly zero) rather than raising. The bundled helper pre-validates
structures and emits an explicit validity flag plus null score for these inputs;
do not interpret an upstream default as a measured low score.

Oracle results are predictions or computed proxies, not experimental evidence.
Applicability domains, model training data, stereochemistry, protonation,
tautomerization, salts, and assay context can materially change interpretation.

## MolGen datasets

Discover the exact stable registry:

```bash
python scripts/discover_metadata.py --kind datasets --task MolGen
```

Plan a random split:

```bash
python scripts/molecular_generation.py dataset \
  --dataset MOSES \
  --seed 42 \
  --data-dir .pytdc-molgen
```

MolGen corpora can contain hundreds of thousands or millions of structures. Review
the official page, per-dataset license, compressed/decompressed size, free disk,
and network budget. Execution intentionally requires both flags:

```bash
python scripts/molecular_generation.py dataset \
  --dataset MOSES \
  --seed 42 \
  --data-dir .pytdc-molgen \
  --execute --download
```

PyTDC 1.1.15's MolGen loader exposes random split only. The supplied seed controls
test sampling, while the generic splitter uses fixed `random_state=1` for
validation sampling.

## Goal-directed optimization safeguards

Before optimizing:

- define whether every objective is maximized, minimized, targeted, or constrained;
- normalize only with justified transformations;
- separate train, validation, and final evaluation budgets;
- cap total unique oracle calls and deduplicate canonical structures;
- record invalid/failed/time-out results rather than silently dropping them;
- retain all candidates and scores needed for audit, but keep chat/CLI output
  bounded;
- monitor exploitation of model artifacts and out-of-domain structures;
- evaluate novelty against the exact declared training/reference set;
- add medicinal-chemistry, synthesizability, selectivity, safety, and diversity
  review rather than relying on a single score;
- treat computational hits as hypotheses requiring expert and experimental
  validation.

Do not claim a weighted sum is scientifically valid merely because every term is
numerical.

## Unsupported historical examples removed

The stable 1.1.15 metadata/public imports do not support old examples that presented
the following as generic ready-to-use APIs:

- `PairMolGen` / `Prodrug`;
- `MolGen(name="GuacaMol")`;
- `evaluate_guacamol(...)`;
- scalar `MW`, `Lipinski`, generic `Docking`, or generic `Vina` oracle names;
- target oracles such as `5HT2A`, `ACE`, `MAPK`, `CDK`, `P38`, `PARP1`, or
  `PIK3CA`.

Do not restore these names without verifying a newer official package registry and
source implementation.
