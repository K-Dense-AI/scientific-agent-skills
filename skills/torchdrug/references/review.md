# TorchDrug review evidence — 2026-10-01

## Release and environment

The latest published TorchDrug remains **0.2.1**, released July 16, 2023. The
published wheel requires Python `>=3.7,<3.11`; release notes claim PyTorch
1.8–2.0 compatibility. Its unconstrained `torch>=1.8` dependency is not proof
that current PyTorch works. This review used the published wheel and current
0.2.1 documentation, including all five tutorials referenced by the skill.

Native CPU tests ran on macOS ARM64 with Python 3.10.20, TorchDrug 0.2.1,
PyTorch 2.0.0, NumPy 1.26.4, SciPy 1.13.1, rdkit-pypi 2022.9.5,
torch-scatter 2.1.2, torch-cluster 1.6.3, fair-esm 2.0.0, decorator 5.1.1,
and setuptools 80.10.2. This is a legacy compatibility environment, not a
recommendation to upgrade unrelated projects to these pins.

Native builds need a working C++ compiler/SDK. On Apple Silicon the tested
scatter/cluster build was staged after installing PyTorch:

```bash
uv pip install "torch==2.0.0" "numpy==1.26.4" "setuptools==80.10.2" wheel
uv pip install --no-build-isolation "torch-scatter==2.1.2" "torch-cluster==1.6.3"
uv pip install "torchdrug==0.2.1" "numpy==1.26.4" "scipy==1.13.1" \
  "rdkit-pypi==2022.9.5" "fair-esm==2.0.0" "decorator==5.1.1"
```

The unmodified build command initially failed under the audit host's current
Apple Clang: PyTorch 2.0 headers specialize `std::is_arithmetic`, which the newer
SDK diagnoses as `-Winvalid-specialization`. For this audit only, compilation
used `-Wno-invalid-specialization`: `CXXFLAGS` for the two package builds and a
compiler wrapper passed through `CXX` for TorchDrug's just-in-time C++ extensions.
No library source, operators, or model results were replaced. Use a compatible
compiler/SDK or explicitly validate such a workaround on the target host; this
is not an upstream support claim. `ninja` must be available on `PATH`, so activate
the environment before executing workflows. The available SciPy 1.15.3 macOS
CPython 3.10 wheel also failed `dlopen` on this host; 1.13.1 passed.

The official PyG PyTorch 2.0 CPU wheel index has no macOS ARM64 binaries. A fresh
one-command dependency resolver can fail because scatter/cluster's source build
needs PyTorch in its build environment. A successful run against cached locally
built wheels does not prove that a fresh resolver can install this stack.

For uv's isolated source builds, its documented `extra-build-dependencies`
setting can supply the missing build requirements without installing scientific
packages in the repository environment. Use these exact build pins in `uv.toml`
and select it with `--config-file` (the repository carries the same configuration
under `tests/torchdrug/uv.toml`):

```toml
[extra-build-dependencies]
torch-scatter = ["torch==2.0.0", "numpy==1.26.4", "setuptools==80.10.2"]
torch-cluster = ["torch==2.0.0", "numpy==1.26.4", "setuptools==80.10.2"]
```

This supplies Python build dependencies; it does not provide a compiler/SDK or
remove the host-specific Clang incompatibility above. Exact pins avoid assuming
that a dynamically generated package's metadata supports `match-runtime`.

## Executed checks

The repository suite `tests/torchdrug/test_workflows.py` uses small local inputs
and covers molecule packing/conversion, GIN forward, an Engine optimizer step,
binary prediction, checkpoint/configuration restoration, regression output
scale, scaffold separation, AttributeMasking and InfoGraph loss/encoder transfer,
protein residue views and vector targets, unknown-residue behavior, GCPN and
GraphAF NLL, filtered all-entity knowledge-graph ranking, and retrosynthesis
checkpoint loading. Synthetic training verifies execution, not predictive quality.

The ClinTox HTTPS gzip was downloaded in full (19,870 bytes), its checksum
matched the release MD5, and native loading retained 1,478 molecules from 1,484
raw rows. A small GIN performed one optimizer step and predicted an 8-by-2 batch.
This verifies the cache-repair workflow; it is not a ClinTox benchmark result.
All 68 Python documentation fences parsed; the 73 direct TorchDrug calls had
compatible released signatures, excluding the explicitly marked negative example.

## Source and endpoint findings

- The released `PropertyPrediction` source supports more metrics than its
  docstring lists, including `acc`, `mcc`, `r2`, `spearmanr`, and `pearsonr`.
- EnzymeCommission/GO expose vector `targets`, not named scalar target keys.
  Residue-only construction changes unknown symbols to glycine, and `to_sequence`
  inserts dots between disconnected residues; preserve source sequence identity.
- InfoGraph and AttributeMasking store encoders under different key prefixes.
  `strict=False` alone cannot certify a transfer.
- Retrosynthesis's `predict_synthon` returns one dictionary despite its stale
  `list of dict` annotation. The composite checkpoint loader accepts one
  subtask's exact keys at a time and rejects `strict=False` and combined states.
- `KnowledgeGraphCompletion.num_negative` controls evaluation chunk size when
  `full_batch_eval=False`; evaluation still ranks every entity.
- `ordered_scaffold_split` in 0.2.1 ignores its `lengths` argument and uses
  hardcoded 80/10/10 cutoffs. Use `scaffold_split` or a validated benchmark splitter.

A source-based inventory covered 103 public dataset/checkpoint URLs across the
named dataset classes and ESM models. HEAD probes are transport checks only:
89 initially returned 200, 11 legacy DeepChem routes returned 400, FreeSolv's S3
route returned an unresolved 301, one historical AlphaFoldDB zebrafish archive
returned 404, and WN18RR test data timed out before a successful retry. These
failures are not claims that the underlying datasets are retired. Large archive
and checkpoint contents, checksums, and parsing remain unverified. No credentials,
private queries, or authenticated endpoints are involved.

## Limits

No CUDA/MPS, distributed training, pretrained ESM inference, full protein
archives, USPTO training/beam search, generated-molecule quality, PPO optimization,
or benchmark convergence was tested. Protein-structure models need verified
coordinate/graph construction; the review does not supply a complete GearNet
experiment. Examples involving those operations are illustrative and must pass a
small native check in the intended environment before scaling.

## Primary sources

- [PyPI release and dependency metadata](https://pypi.org/project/torchdrug/0.2.1/)
- [Official release notes](https://github.com/DeepGraphLearning/torchdrug/releases/tag/v0.2.1)
- [Official installation guide](https://torchdrug.ai/docs/installation.html)
- [Released source tree](https://github.com/DeepGraphLearning/torchdrug/tree/v0.2.1/torchdrug)
- [Data API](https://torchdrug.ai/docs/api/data.html)
- [Task API](https://torchdrug.ai/docs/api/tasks.html)
- [Model API](https://torchdrug.ai/docs/api/models.html)
- [Engine API](https://torchdrug.ai/docs/api/core.html)
- [DeepChem ClinTox source](https://github.com/deepchem/deepchem/blob/master/deepchem/molnet/load_function/clintox_datasets.py)
- [PyG PyTorch 2.0 CPU wheels](https://data.pyg.org/whl/torch-2.0.0+cpu.html)
- [uv build dependency configuration](https://docs.astral.sh/uv/concepts/projects/config/#augmenting-build-dependencies)
