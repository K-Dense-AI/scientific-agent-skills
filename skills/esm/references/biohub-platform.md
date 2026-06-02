# Biohub Platform and ESMFold2

## Overview

EvolutionaryScale is migrating hosted inference from [Forge](https://forge.evolutionaryscale.ai) to the [Biohub platform](https://biohub.ai). The Python SDK still uses `esm.sdk.forge` client classes and "Forge" naming in many places, but newer structure-prediction APIs (ESMFold2) run on Biohub endpoints.

Use this reference when you need **all-atom structure prediction** (ESMFold2) or when upstream docs point to `biohub.ai` instead of `forge.evolutionaryscale.ai`.

## Authentication

Create API keys in the [Biohub developer console](https://biohub.ai/developer-console/api-keys). Store the key in `ESM_API_KEY` (same env var used by `esm.sdk.client()` on Forge).

```python
import os

token = os.environ["ESM_API_KEY"]
```

Never commit API keys or paste them into notebooks checked into git.

## Installation

For ESMFold2 and latest Biohub SDK features, upstream may recommend installing from the Biohub GitHub repo (pin a specific commit for reproducibility):

```bash
uv pip install "esm@git+https://github.com/Biohub/esm.git@c94ed8d"
```

For ESM3/ESM C workflows on PyPI, `uv pip install "esm==3.2.3"` remains the standard path. Confirm which install source your task requires before mixing both in one environment.

## ESMFold2 Structure Prediction

ESMFold2 is a structure prediction model built on ESMC 6B, available through `SequenceStructureForgeInferenceClient` with Biohub as the API host.

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

### Model IDs

| Model ID | Use case |
|----------|----------|
| `esmfold2-fast-2026-05` | Fast single-sequence folding |
| Check Biohub docs for additional variants | MSA-augmented or higher-accuracy modes |

## Relationship to Forge (ESM3 / ESM C)

| Capability | Typical endpoint | Client |
|------------|------------------|--------|
| ESM3 generation | `https://forge.evolutionaryscale.ai` | `esm.sdk.client()` or `ESM3ForgeInferenceClient` |
| ESM C 6B embeddings (hosted) | Forge | `ESM3ForgeInferenceClient` with `esmc-6b-2024-12` |
| ESMFold2 structure prediction | `https://biohub.ai` | `SequenceStructureForgeInferenceClient` |

For ESM3 and ESM C cloud usage patterns, see `forge-api.md`. For local open-weight models, see `esm3-api.md` and `esm-c-api.md`.

## Additional Resources

- **Biohub:** https://biohub.ai
- **Biohub/esm repository:** https://github.com/Biohub/esm
- **Tutorials:** https://github.com/Biohub/esm/tree/main/cookbook/tutorials
- **ESMC & ESMFold2 preprint:** https://biohub.ai/papers/esm_protein.pdf
