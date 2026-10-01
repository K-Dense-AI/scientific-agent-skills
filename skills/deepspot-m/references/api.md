# DeepSpot-M API reference

Reviewed against the released `deepspotm==1.0.0` wheel and matching current
upstream `model.py` on 2026-09-30. Weight-dependent examples are illustrative;
see the verification scope in `SKILL.md`.

## Loading and reproducibility

```python
from deepspotm import DeepSpotM

model, image_processor = DeepSpotM.from_pretrained(
    "ratschlab/DeepSpotM",
    source="scgpt",
    device="cpu",
    revision="48be27af436a50e5c74175680ac2b7b2596a506b",
)
```

Exact signature: `from_pretrained(repo_id_or_path, *, source=None, device=None,
revision=None)`. It downloads `config.json`, `model.safetensors` and `tokens.csv`
from the specified Hub revision, returns `(model, image_processor)`, puts the
model in evaluation mode and uses center-crop evaluation transforms. The Midnight
backbone is built from a bundled configuration; it does not separately download
`kaiko-ai/midnight` weights for this route.

- `device=None` chooses CUDA when available, otherwise CPU. The processor returns a
  CPU tensor; move the batch to the same device. `predict_genes` does not do this.
- `source` selects a loaded embedding pathway. Supply one of `evo2`, `orthrus`,
  `prott5`, `scgpt`, `apertus` for the published multi-source model. Omitting it
  with several pathways raises `ValueError`.
- `revision` is a Hub branch/tag/commit; record an immutable commit for reproducibility.
  It has no effect when loading a local directory.
- A local directory must contain the three compatible files above. There are no
  `token`, `cache_dir`, `local_files_only`, or arbitrary Hub keyword arguments on
  this method. Use Hub authentication/environment settings, or download an approved
  snapshot separately and load its directory.

Authenticate with `hf auth login` only after the manual access request is approved.
The current gate also requires eligibility declarations; consult the live model page.
Cached credentials or `HF_TOKEN` are read by `hf_hub_download`. Configure `HF_HOME`
before imports, and keep access-limited caches restricted to approved users. Setting
`HF_HOME` alone does not guarantee offline operation: use a complete local directory
on a node without network access. Never mirror weights to bypass the gate.

Do not translate every exception into an authentication error. Distinguish an absent
package, a denied Hub request, missing local files, invalid source, incompatible
checkpoint and device/memory errors; retain the original exception as the cause.
An import error can arise from a broken transitive dependency even when DeepSpot-M
itself is installed.

## Gene queries and device placement

```python
import torch

# pil_tiles have already passed size, RGB and physical-resolution validation.
genes = ["EPCAM", "CD3D", "PTPRC"]
if not genes or len(genes) != len(set(genes)):
    raise ValueError("Use a nonempty list of unique gene symbols")
missing = [g for g in genes if g not in set(model.gene_names)]
if missing:
    raise ValueError(f"Not in the DeepSpot-M panel: {missing}")

batch = torch.stack([image_processor(t) for t in pil_tiles]).to(model.device)
vals = model.predict_genes(batch, genes).cpu()
if vals.shape != (len(pil_tiles), len(genes)) or not torch.isfinite(vals).all():
    raise ValueError("Unexpected prediction shape or nonfinite values")
```

`predict_genes(pixel_values, genes)` accepts processed `(B, 3, 224, 224)` tensors
and either one gene string or an ordered sequence. It returns `(B, G)` on the input/model
device, preserving requested order; a single string yields `(B, 1)`. The method uses
`torch.no_grad()` internally. It does not change the model's training/evaluation mode.
`from_pretrained` already calls `.eval()`; retain that setting for inference.

The checkpoint's `model.gene_names` is authoritative for membership and spelling.
Resolve HGNC aliases explicitly, preserve the alias-to-panel mapping, and do not
assume every modern symbol is present. Unknown symbols raise `KeyError`. The
released panel covers approximately 19,000 protein-coding genes; zero-shot prediction
refers to panel genes unseen during training, not arbitrary novel query symbols.
Duplicate queries repeat output columns; reject them when assembling unique variables.

`model(batch)` returns three values `(expression, pooled, attention_weights)`;
full-panel expression column `i` maps to `model.gene_names[i]`. The skill uses
`predict_genes` to avoid computing unneeded queries. A single query call reuses one
backbone pass across the requested genes. If memory requires gene chunking, repeated
`predict_genes` calls also repeat that backbone pass; do not assume a public token cache.

## Source comparisons

| `source` | Embedding origin |
| --- | --- |
| `evo2` | Genomic sequence |
| `orthrus` | RNA |
| `prott5` | Protein sequence |
| `scgpt` | Single-cell expression |
| `apertus` | Language model |

The published multi-source model exposes `model.sources`, `model.current_source`
and `model.set_source(name)`. Changing the source does not require reloading the
processor or weights. Run sequentially; this mutates the shared model and is not
safe to switch concurrently between requests.

```python
per_source = {}
for source in ("scgpt", "prott5", "evo2"):
    model.set_source(source)
    per_source[source] = model.predict_genes(batch, genes).cpu()
model.set_source("scgpt")
```

Keep one source fixed for a primary cohort analysis; treat alternative sources as
sensitivity analyses, not automatically exchangeable measurements or uncertainty estimates.

## Memory and output scale

Start with a few tiles and a short gene list, then measure peak memory before increasing
batch size. A batch of 32 tiles and all ~19k queries can be much larger than a marker
panel; no universally safe batch size is established here. Persist slide outputs as
you go. Dense float32 expression alone costs `4 * n_tiles * n_genes` bytes, before
intermediate tensors or duplicate arrays during concatenation.

Values are predicted **log1p-CPM**, not observed counts. Preserve this in metadata;
do not normalize/log them again or pass them to count likelihoods. Inverse-transform
only when needed for interpretation:

```python
import numpy as np

cpm_scale = np.expm1(vals.numpy())  # vals was moved to CPU above
```

The decoder has an unconstrained regression output; inspect negative predictions,
nonfinite values and overflow rather than silently clipping them. Inverted values
are not guaranteed nonnegative or to sum to one million, especially for a subset
of genes. Report any postprocessing separately. Validate slide/patient-held-out
performance for the tissue, stain and processing conditions of interest.

## Primary sources

- [Released package metadata](https://pypi.org/pypi/deepspotm/1.0.0/json)
- [Reviewed upstream model source](https://github.com/ratschlab/DeepSpotM/blob/4d7793c890c500f51033444cc755f02b9d523628/src/deepspotm/model.py)
- [Model card and access declarations](https://huggingface.co/ratschlab/DeepSpotM)
- [Hub authentication CLI](https://huggingface.co/docs/huggingface_hub/en/guides/cli)
- [Hub environment variables](https://huggingface.co/docs/huggingface_hub/en/package_reference/environment_variables)
- [Study preprint](https://doi.org/10.64898/2026.06.19.26356060)
