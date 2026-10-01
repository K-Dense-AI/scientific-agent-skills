# Biohub and ESMFold2: esm 3.4.1.post1

## Released support and access

The released SDK includes ESMFold2; a floating GitHub installation is unnecessary.
Use the isolated environment in `SKILL.md`. Current Biohub ESMC6B and ESMFold2
weights are public with MIT model-card labels; ESMC also links third-party
license notices. Availability of weights
does not imply a small memory footprint or access to every hosted model.

ESMFold2 combines ESMC representations with all-atom diffusion prediction. It
returns a molecular complex, unlike ESM3's `ESMProtein` structure track. Use
`result.complex.to_mmcif()` for mixed polymers/ligands and preserve chain IDs,
modifications and chemical components. A predicted static structure is not a
binding-energy, activity or dynamics assay.

## Hosted example

Illustrative; requires an authorized key and sends the input to Biohub.

```python
import os
from esm.sdk import esmfold2_client
from esm.sdk.api import ESMProteinError, FoldingConfig
from esm.utils.structure.input_builder import ProteinInput, StructurePredictionInput

input_data = StructurePredictionInput(
    sequences=[ProteinInput(id="A", sequence="MPRTKEINDAGLIVHSPQWFYK")]
)
config = FoldingConfig(num_loops=20, num_sampling_steps=100, include_pae=True)
with esmfold2_client(model="esmfold2-fast-2026-05", url="https://biohub.ai",
                     token=os.environ["ESM_API_KEY"], request_timeout=300) as client:
    result = client.fold_all_atom(input_data, config=config)
if isinstance(result, ESMProteinError):
    raise result
with open("predicted.cif", "w") as handle:
    handle.write(result.complex.to_mmcif())
```

`fold_all_atom` posts `/api/v1/fold_all_atom`; settings are passed by keyword
because the second positional argument of the synchronous method is
`model_name`, not `config`. The released deserializer returns one
`MolecularComplexResult`, despite an annotation allowing a list.

The response exposes `plddt`, `ptm`, `iptm` (mapped from `interface_ptm`), `pae`,
and optional embeddings. Some values may be absent; inspect their shape and
units for the actual result before summarizing. Chain/atom arrays may require
mapping to polymer residues; do not assume every complex token is one amino acid.
Keep low-confidence regions and alignment coverage visible. No numerical
accuracy or confidence calibration was measured in this refresh.

## MSA and configuration limits

- `esmfold2-fast-2026-05` is the documented single-sequence hosted example and
  **ignores supplied MSAs**, with an SDK warning. Current constants also name
  `esmfold2-2026-05`; confirm account availability before using another model.
- `ProteinInput.msa` accepts an SDK `MSA` object or `None`, not a raw A3M string.
  Keep the query sequence, row alignment and chain assignment consistent. The
  client rejects an over-limit MSA for the MSA-enabled model; inspect the released
  `ESMFOLD2_MAX_MSA_SEQS` and current service limits rather than inventing a depth.
- `FoldingConfig` defaults to 20 loops and 100 sampling steps. Lower values trade
  computation for quality; they are not validated accuracy-equivalent settings.
  `lm_mask_pct=None` resolves to 0.1 for the fast model, 0.0 for the full model.
- Hosted `include_distogram=True` is rejected by the released client. Although
  `include_pair_chains_iptm` exists in `FoldingConfig`, the released
  `fold_all_atom` serializer does not send it. Do not promise pair-chain IPTM
  output through that path.
- `FoldingConfig` has no seed field. Record settings and returned identifiers;
  a local seed is not transmitted by this hosted API.

## Local ESMFold2

The following is an official-API illustration, not an executed pretrained run:

```python
from esm.models.esmfold2 import EsmFold2Model, ESMFold2InputBuilder

model = EsmFold2Model.from_pretrained("biohub/ESMFold2", device="cuda").eval()
result = ESMFold2InputBuilder().fold(
    model, input_data, num_loops=20, num_sampling_steps=100,
    num_diffusion_samples=1, seed=0,
)
with open("local_prediction.cif", "w") as handle:
    handle.write(result.complex.to_mmcif())
```

This needs large model weights and suitable GPU resources. Do not download them
for a signature check. The repository also documents longer-sequence Fold-CP
and an independent Transformers implementation; those deployment paths were not
executed here and require their own dependency/parallelism review.

## Complex input conventions

`ProteinInput`, `DNAInput`, `RNAInput`, and `LigandInput` belong in
`StructurePredictionInput.sequences`. IDs must preserve chain identity.
`LigandInput(ccd=["SAH"], id="L")` uses a **list** of CCD codes; a bare string is
rejected. Use a CCD list or SMILES deliberately rather than providing ambiguous
competing representations. `Modification.position`, covalent-bond residue
indices and atom indices are **0-based**; they do not share the 1-based ESM3
`FunctionAnnotation` convention. Validate molecule chemistry and all residue/atom
mappings before inference. Prediction availability does not validate them.

Sources: [official README](https://github.com/Biohub/esm),
[ESMFold2 card](https://huggingface.co/biohub/ESMFold2),
[folding SDK](https://github.com/Biohub/esm/blob/main/esm/sdk/forge.py),
[input types](https://github.com/Biohub/esm/blob/main/esm/utils/structure/input_builder.py),
[API configs](https://github.com/Biohub/esm/blob/main/esm/sdk/api.py).
