# Biohub Platform and ESMFold2

## Overview

EvolutionaryScale and Forge now surface current hosted ESM workflows through the [Biohub platform](https://biohub.ai). The Python SDK still uses `esm.sdk.forge` client classes and "Forge" naming in some places, but current Biohub APIs use `https://biohub.ai` endpoints.

Use this reference when you need **all-atom structure prediction** (ESMFold2) or when upstream docs point to `biohub.ai` instead of `forge.evolutionaryscale.ai`.

## Authentication

Create API keys in the [Biohub developer console](https://biohub.ai/developer-console/api-keys). Store the key in `ESM_API_KEY` (same env var used by `esm.sdk.client()` on Forge).

```python
import os

token = os.environ["ESM_API_KEY"]
```

Never commit API keys or paste them into notebooks checked into git.

## Installation

For ESM3/ESMC workflows on PyPI, `uv pip install "esm==3.2.3"` remains the standard reproducible path.

For ESMFold2 and the newest Biohub SDK features, upstream may recommend installing from the Biohub GitHub repo. Avoid floating branch installs in automated or production instructions. Pin a trusted release or a full 40-character commit SHA from the official Biohub repository, and review the verified GitHub release/commit before installing:

```bash
uv pip install "esm@git+https://github.com/Biohub/esm.git@<full-40-character-commit-sha>"
```

Confirm which install source your task requires before mixing PyPI and GitHub builds in one environment.

## ESMFold2 Structure Prediction

ESMFold2 is a structure prediction model built on ESMC 6B, available through `SequenceStructureForgeInferenceClient` with Biohub as the API host. Biohub lists ESMFold2 as a 2026-04/2026-05 model family and documents `esmfold2-fast-2026-05` for hosted inference.

```python
import os
from esm.sdk.forge import SequenceStructureForgeInferenceClient
from esm.sdk.api import FoldingConfig
from esm.utils.structure.input_builder import ProteinInput, StructurePredictionInput

client = SequenceStructureForgeInferenceClient(
    model="esmfold2-fast-2026-05",
    url="https://biohub.ai",
    token=os.environ["ESM_API_KEY"],
)

sequence = "MSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTFSYGVQCFSRYPDHMKQHDFFKSAMPEGYVQERTIFFKDDGNYKTRAEVKFEGDTLVNRIELKGIDFKEDGNILGHKLEYNYNSHNVYIMADKQKNGIKVNFKIRHNIEDGSVQLADHYQQNTPIGDGPVLLPDNHYLSTQSALSKDPNEKRDHMVLLEFVTAAGITLGMDELYK"

fold_input = StructurePredictionInput(
    sequences=[ProteinInput(id="A", sequence=sequence)]
)

config = FoldingConfig(num_loops=3, num_sampling_steps=32)
result = client.fold_all_atom(fold_input, config=config)

with open("result.cif", "w") as f:
    f.write(result.complex.to_mmcif())
```

## Hosted ESMC Embeddings

Biohub also documents hosted ESMC inference with `esmc_client()` and dated ESMC model IDs:

```python
import os
from esm.sdk import esmc_client
from esm.sdk.api import ESMProtein, LogitsConfig

model = esmc_client(
    model="esmc-600m-2024-12",
    url="https://biohub.ai",
    token=os.environ["ESM_API_KEY"],
)

protein = ESMProtein(sequence="MPRTKEINDAGLIVHSPQWFYK")
protein_tensor = model.encode(protein)
logits_output = model.logits(
    protein_tensor,
    LogitsConfig(sequence=True, return_embeddings=True),
)
embeddings = logits_output.embeddings
```

### Model IDs

| Model ID | Use case |
|----------|----------|
| `esmfold2-fast-2026-05` | Fast single-sequence folding |
| Check Biohub docs for additional variants | MSA-augmented or higher-accuracy modes |

ESMFold2 predicts static all-atom structures. Treat outputs as hypotheses that require experimental validation, especially for therapeutic, clinical, or safety-sensitive uses.

## Relationship to Forge (ESM3 / ESM C)

| Capability | Typical endpoint | Client |
|------------|------------------|--------|
| ESM3 generation | `https://forge.evolutionaryscale.ai` | `esm.sdk.client()` or `ESM3ForgeInferenceClient` |
| ESM C 6B embeddings (hosted) | Forge | `ESM3ForgeInferenceClient` with `esmc-6b-2024-12` |
| ESMC hosted embeddings | `https://biohub.ai` | `esmc_client()` with dated ESMC model IDs |
| ESMFold2 structure prediction | `https://biohub.ai` | `SequenceStructureForgeInferenceClient` |

For ESM3 and ESM C cloud usage patterns, see `forge-api.md`. For local open-weight models, see `esm3-api.md` and `esm-c-api.md`.

## Additional Resources

- **Biohub:** https://biohub.ai
- **Biohub/esm repository:** https://github.com/Biohub/esm
- **Tutorials:** https://github.com/Biohub/esm/tree/main/cookbook/tutorials
- **ESMC & ESMFold2 preprint:** https://biohub.ai/papers/esm_protein.pdf
