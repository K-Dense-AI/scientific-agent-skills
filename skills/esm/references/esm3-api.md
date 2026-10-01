# ESM3 generation: esm 3.4.1.post1

## Model and interface

Local `ESM3.from_pretrained("esm3-sm-open-v1", device=torch.device("cpu"))`
loads the open 1.4B checkpoint. Hosted `esm.sdk.client()` uses Biohub, with
`esm3-small-2024-08`, `esm3-medium-2024-08` (7B), and `esm3-large-2024-03`
(98B) listed in the current ESM3 README. Access depends on the account; model
listing is not an authenticated availability test. Do not rely on the old
unverified `esm3-medium-multimer-2024-09` example.

`ESMProtein` contains optional sequence, secondary-structure, SASA, function and
coordinate tracks. Sequence masking uses `_`. Use consistent track lengths and
explicit chain/residue mappings; plain single-chain recipes here exclude `|`
chain breaks. Coordinates are `torch.Tensor` atom37 arrays `(L,37,3)` in angstroms,
with missing atoms represented by NaN, not Python `None` entries in a tensor.

`ESMProtein.from_pdb(path, chain_id="A")` selects an author chain. The current
default `chain_id="all"` combines chains, so specify the desired chain explicitly.
`to_pdb(path)` writes a file; `to_pdb_string()` returns text. Preserve original
residue numbers/insertion codes externally when sequence indices differ.

## Generation controls

`GenerationConfig` supports tracks `sequence`, `structure`,
`secondary_structure`, `sasa`, and `function`. Relevant released defaults are
`num_steps=20`, `temperature=1.0`, `temperature_annealing=True`, `top_p=1.0`,
`strategy="random"`, `schedule="cosine"`, and
`condition_on_coordinates_only=True`. Source comments about earlier defaults
can differ from the actual field values; record explicit settings.

- Use a positive step count suited to the missing positions. Local generation
  caps excessive steps at the number of masks; the hosted client also caps by
  sequence length and can mutate the config. Create a separate config per request.
- `top_p` is a float; `1.0` disables nucleus restriction. Do not pass `None`.
- Temperature has no maximum of 1.0. At zero, sampling can select argmax, but
  default annealing has a positive floor and random unmasking remains stochastic.
  Temperature zero alone is not a reproducibility guarantee.
- `condition_on_coordinates_only` selects coordinates instead of discrete
  structure tokens as structure conditioning. It does **not** clear the sequence
  or every other track. For inverse folding, remove the sequence explicitly.
- `.generate()` fills masked positions. It does not resample all fixed residues;
  a temperature schedule made from repeated calls on completed sequences is not
  refinement. Remask intended sites, or use the SDK's actual annealing option.

The unified low-level inference path is `encoded = model.encode(protein)` then
`output = model.logits(encoded, LogitsConfig(...))`. Inspect `output.logits.sequence`
for sequence logits. `model.forward(encoded)` followed by `model.decode(output)`
is invalid: `forward` has lower-level batched tensor arguments and `decode`
expects an `ESMProteinTensor`, not a logits object.

## Inverse folding and independent checking

Illustrative pretrained inference; `model` is a loaded ESM3 inference client.

```python
from esm.sdk.api import ESMProtein, ESMProteinError, GenerationConfig

original = ESMProtein.from_pdb("target.pdb", chain_id="A")
assert original.coordinates is not None and original.sequence
prompt = ESMProtein(coordinates=original.coordinates.clone())
design = model.generate(prompt, GenerationConfig(
    track="sequence", num_steps=min(20, len(original.sequence)),
    temperature=0.7, condition_on_coordinates_only=True,
))
if isinstance(design, ESMProteinError):
    raise design
assert design.sequence is not None and len(design.sequence) == len(original.sequence)

# Sequence-only input avoids conditioning the structural check on the target.
predicted = model.generate(ESMProtein(sequence=design.sequence), GenerationConfig(
    track="structure", num_steps=min(20, len(design.sequence)),
))
if isinstance(predicted, ESMProteinError):
    raise predicted
predicted.to_pdb("independently_predicted.pdb")
```

Compare matched, finite atoms after structural superposition; report alignment
coverage and confidence, not just an RMSD number. Successful coordinate generation
is not evidence that a design is stable or functional. A same-model round trip
also is not independent experimental validation.

## Function conditioning

`FunctionAnnotation` is exported from `esm.sdk.api` and defined in
`esm.utils.types`. Its `start` and `end` are **1-based, inclusive**. Labels must
occur in the selected function/residue-annotation tokenizer vocabulary: supported
InterPro IDs or exact keyword entries, not invented natural-language underscored
labels. A range specifies where a function annotation applies; it is not a
constraint fixing a catalytic residue or GFP chromophore.

For a local loaded ESM3 model, inspect the supported vocabulary before constructing
annotations (illustrative; vocabulary assets were not downloaded in this review):

```python
from esm.sdk.api import ESMProtein, FunctionAnnotation, GenerationConfig

label = selected_supported_label  # Chosen from this model's vocabulary.
tokenizer = model.tokenizers.function
assert label in tokenizer.interpro_labels or label in tokenizer.keyword_vocabulary
annotation = FunctionAnnotation(label=label, start=1, end=150)
prompt = ESMProtein(sequence="_" * 150, function_annotations=[annotation])
result = model.generate(prompt, GenerationConfig(track="sequence", num_steps=20))
```

Function-track predictions are annotation hypotheses. Low temperature is not
calibrated confidence. Confirm with curated evidence and task-specific assays;
function conditioning alone cannot guarantee fluorescence or enzyme activity.

## Multitrack designs

A useful sequence is: complete masked sequence -> predict structure -> optionally
remask selected sequence positions while retaining chosen structural conditions
-> create a fresh sequence-only prompt for structural checking. Explicitly clear
`coordinates` before predicting a new structure on an existing protein object.
Keep the initial prompt, each generated candidate and the exact mutations.
Avoid splitting long proteins into arbitrary independent chunks and claiming a
coherent full-length fold.

Sources: [ESM3 README](https://github.com/Biohub/esm/blob/main/_assets/ESM3_README.md),
[SDK types](https://github.com/Biohub/esm/blob/main/esm/sdk/api.py),
[generation](https://github.com/Biohub/esm/blob/main/esm/utils/generation.py),
[annotation coordinates](https://github.com/Biohub/esm/blob/main/esm/utils/types.py),
[function tokenizer](https://github.com/Biohub/esm/blob/main/esm/tokenization/function_tokenizer.py).
