# Review evidence — 2026-09-30

## Release and primary sources

The target is the published `esm==3.4.1.post1` wheel (uploaded 2026-09-16),
not the earlier 3.2.3 API or an unpinned GitHub checkout. The wheel's SHA-256
was checked against official PyPI metadata. Current upstream `main` documentation
was cross-checked against that released source before adopting its examples.

| Primary source | What was verified |
| --- | --- |
| [PyPI release](https://pypi.org/project/esm/3.4.1.post1/) and [release JSON](https://pypi.org/pypi/esm/3.4.1.post1/json) | Python >=3.12; Torch >=2.11,<2.12; Transformers >=4.57.6,<5; Linux x86_64 GPU dependency markers |
| [Biohub repository](https://github.com/Biohub/esm) | Current local ESMC/ESMFold2 interfaces, Biohub migration, open ESMC6B weights |
| [ESM3 README](https://github.com/Biohub/esm/blob/main/_assets/ESM3_README.md) | Local/hosted model IDs, masked generation, clearing tracks before a round trip |
| [SDK factories](https://github.com/Biohub/esm/blob/main/esm/sdk/__init__.py) | Distinct ESM3/ESMC/folding factories, Biohub defaults, import-time token capture |
| [SDK types](https://github.com/Biohub/esm/blob/main/esm/sdk/api.py) | Generation/Folding/Logits configs, per-track output containers, PDB methods |
| [Hosted clients](https://github.com/Biohub/esm/blob/main/esm/sdk/forge.py) | Exact endpoint names, request and response fields, ESMProteinError values, MSA warning, omitted pair-chain IPTM flag |
| [HTTP transport](https://github.com/Biohub/esm/blob/main/esm/sdk/base_forge_client.py) and [retry](https://github.com/Biohub/esm/blob/main/esm/sdk/retry.py) | Bearer auth, `/api/v1/`, httpx, timeout semantics, bounded retries and response decoding |
| [Native ESMC](https://github.com/Biohub/esm/blob/main/esm/models/esmc/model.py), [tokenizer](https://github.com/Biohub/esm/blob/main/esm/models/esmc/tokenizer.py), [compatibility](https://github.com/Biohub/esm/blob/main/esm/models/esmc/compatibility.py) | Batched token API, special tokens, hidden states, deprecated wrapper differences |
| [Generation implementation](https://github.com/Biohub/esm/blob/main/esm/utils/generation.py), [function tokenizer](https://github.com/Biohub/esm/blob/main/esm/tokenization/function_tokenizer.py), [annotation type](https://github.com/Biohub/esm/blob/main/esm/utils/types.py) | Track masking, temperature annealing, supported-label validation, 1-based inclusive annotations |
| [Complex input types](https://github.com/Biohub/esm/blob/main/esm/utils/structure/input_builder.py) | Typed polymer/ligand inputs, list-valued CCD IDs, zero-based modification indices |
| [ESMC300M](https://huggingface.co/biohub/ESMC-300M), [ESMC600M](https://huggingface.co/biohub/ESMC-600M), [ESMC6B](https://huggingface.co/biohub/ESMC-6B), [ESMFold2](https://huggingface.co/biohub/ESMFold2) | Model cards, 2048-token ESMC context, weight availability and license notices |
| [Legacy Meta ESM](https://github.com/facebookresearch/esm) | Separate `fair-esm` distribution and ESM2/ESMFold APIs |
| [scikit-learn pitfalls](https://scikit-learn.org/stable/common_pitfalls.html), [PCA](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html), [KMeans](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html) | Leakage boundaries, PCA dimension bounds, explicit clustering settings |

Public Hugging Face model metadata and the three small ESMC `config.json` files
were fetched without authentication or weights. Configs reported dimensions
960/1152/2560, layers 30/36/80, and 2048 maximum position metadata. All parsed
with the released `EsmcConfig`. Public access metadata does not test weight
loading, hosted account access or model quality. ESMC cards list MIT plus
`other` with a third-party-notice link; retain those notices rather than treating
all dependency licenses as MIT.

## Executed checks

The suite in `tests/esm/` exercises a two-layer, 32-dimensional random ESMC model
on CPU. It checks native batch/individual equivalence, token axes and hidden
states, residue-only pooling including NaN padding, malformed inputs and context
length, legacy SDK output containers, tiny saved-checkpoint reload, and a
synthetic two-residue PDB round trip. Random weights establish software behavior,
not learned scientific performance.

`httpx.MockTransport` exercises actual released ESM3 generation, ESMC
encode/logits/decode, and folding transport paths with synthetic responses. It
checks host/path, bearer-header construction, request timeout, payload fields,
response envelopes, and returned 400/401 error values. Folding serialization
checks reproduce the unsupported distogram flag and absent pair-chain IPTM
request field. These checks do not call Biohub or use real keys.

The isolated suite uses Python 3.12, esm 3.4.1.post1, Torch 2.11.0 and
Transformers 4.57.6. The documentation's tiny native ESMC example, small-dataset
clustering recipe (2 and 12 synthetic rows), and variant bookkeeping with a fake
generator were also run. Every Python code fence was syntax-checked. The PDB
fixture warns about absent entity metadata, expected for its minimal synthetic
input; sequence and coordinates round-trip correctly.

## Verification boundaries

No pretrained model weights, full protein datasets or CUDA toolchains were
downloaded. Pretrained ESM3/ESMC/ESMFold2 inference, fine tuning, function-vocabulary
assets, Flash Attention, multi-GPU/Fold-CP, authenticated service availability,
rate limits, pricing, and scientific performance were not executed. Examples
requiring these are explicitly illustrative. The skill does not claim tested
SageMaker deployment, direct submitted batch-job workflows, or an API-compatible
migration from `fair-esm`.

The old workflow diagram connected ESMC/t-SNE output to ESMFold2 and labeled
folding as `esm.sdk.client()`. Those relationships are incorrect: ESMC features,
ESM3 generation and ESMFold2 folding are distinct routes. A replacement must
show their separate input/output contracts and prediction/validation boundary.
