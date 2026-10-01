# DeepSpot-M API reference

Everything here builds on the two calls in `SKILL.md`: `DeepSpotM.from_pretrained` and
`model.predict_genes`.

## Loading a model

```python
from deepspotm import DeepSpotM

model, image_processor = DeepSpotM.from_pretrained("ratschlab/DeepSpotM", source="scgpt")
```

`from_pretrained` returns two objects:

- `model`: the PyTorch model that answers gene queries.
- `image_processor`: the transform that turns one 224x224 PIL tile into the tensor the
  model reads. Always use the processor that came back with the model rather than a
  hand-written transform, so normalisation matches the weights.

Arguments:

- The repository id, `"ratschlab/DeepSpotM"`. It is gated, so request access on the model
  page and run `huggingface-cli login` before the first call.
- `source`: which frozen gene embedding the router builds gene-specific projections from.
  One of `evo2`, `orthrus`, `prott5`, `scgpt`, `apertus`.

The first call downloads weights into the Hugging Face cache. Set `HF_HOME` to place that
cache on a volume with room for it, which matters on a shared cluster where the default
home directory is small.

## Choosing an embedding source

| `source`  | Gene embedding         |
| --------- | ---------------------- |
| `evo2`    | genomic sequence       |
| `orthrus` | RNA                    |
| `prott5`  | protein sequence       |
| `scgpt`   | single-cell expression |
| `apertus` | language model         |

The gene router turns whichever embedding you pick into per-gene projections, which is
what makes genes queryable rather than fixed outputs. Each source describes gene identity
from a different modality, so the same gene is represented differently under each one.

Pick one source per run and keep it fixed across every tile in a slide or cohort, so the
values stay comparable. When the choice matters to a conclusion, run the same tiles
through several sources and report the values side by side:

```python
genes = ["EPCAM", "CD3D", "PTPRC"]

per_source = {}
for source in ("scgpt", "prott5", "evo2"):
    model, image_processor = DeepSpotM.from_pretrained("ratschlab/DeepSpotM", source=source)
    tiles = torch.stack([image_processor(require_tile(t)) for t in pil_tiles])
    per_source[source] = model.predict_genes(tiles, genes)
```

Reload the model when you change `source`, and rebuild the tile batch with the processor
returned alongside it.

## Predicting genes

```python
vals = model.predict_genes(image_processor(pil_tile).unsqueeze(0), ["EPCAM", "CD3D"])
```

The first argument is a batch tensor of processed tiles. The second is a list of gene
symbols. A single tile still needs the batch dimension, which is what `unsqueeze(0)` adds.

### Gene symbols

Pass HGNC gene symbols as uppercase strings, for example `EPCAM`, `CD3D`, `PTPRC`,
`MKI67`. The queryable genes are the ~19k-symbol panel shipped with the weights as
`tokens.csv`, exposed on the loaded model as `model.gene_names`. A symbol outside that
panel raises `KeyError` naming the offending genes, and predicting genes outside the
panel is not part of this release. Check membership up front when a gene list comes from
elsewhere:

```python
panel = set(model.gene_names)
missing = [g for g in genes if g not in panel]
if missing:
    raise ValueError(f"Not in the DeepSpot-M panel: {missing}")
```

Two habits keep a run reproducible:

- Map aliases to current HGNC symbols before querying, so `CD45` becomes `PTPRC`. Reading
  the list from a file keeps the mapping visible in the run.
- Keep the gene list beside the output. Values come back in the order requested, and the
  list is the only label the array carries.

```python
genes = [line.strip() for line in open("genes.txt") if line.strip()]
vals = model.predict_genes(tiles, genes)
```

Ask for every gene you need in one call rather than looping one gene at a time. The tile
tokens are computed once per batch and reused across the gene queries.

## Batching

`image_processor` handles one tile, so build a batch by stacking:

```python
import torch

batch = torch.stack([image_processor(require_tile(t)) for t in pil_tiles])
vals = model.predict_genes(batch, genes)
```

Batch size trades throughput against memory. Start at 32 tiles on a GPU and 8 on CPU, then
raise it while memory allows. Memory grows with both the batch and the number of genes in
one call, so lower one when the other is large.

## Device placement

`from_pretrained` accepts a `device` argument and returns the model already in eval mode
on that device, and `predict_genes` runs under `no_grad` on its own. So device handling
is one argument plus putting each batch on the same device:

```python
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"
model, image_processor = DeepSpotM.from_pretrained(
    "ratschlab/DeepSpotM", source="scgpt", device=device
)

vals = model.predict_genes(batch.to(device), genes)
```

Keeping the model on the device across batches is what makes a slide-scale run practical.
Move results back with `.cpu()` before converting to NumPy.

## Output units

Values are predicted log1p-CPM, not measured counts. Keep this provenance in the
AnnData metadata; do not feed them into count-based likelihoods or normalize/log
them a second time. For clustering or spatial statistics, assess held-out validity,
slide effects, and dependence among neighboring tiles before making biological claims.

To read values as CPM instead, invert the transform:

```python
import numpy as np

cpm = np.expm1(vals.cpu().numpy())
```

Compare values across tiles and slides on the log1p-CPM scale, since that is the scale the
model produces.

## Handling the gated download

`from_pretrained` fails when the machine has no access token or the access request is
still pending. Report the whole path back to a working call rather than the raw error:

```python
DEEPSPOTM_HELP = (
    "DeepSpot-M is unavailable. Install it with `uv pip install deepspotm==1.0.0`, request "
    "access to the gated weights at https://huggingface.co/ratschlab/DeepSpotM, then "
    "authenticate with `huggingface-cli login`."
)

def load_deepspotm(source="scgpt"):
    try:
        from deepspotm import DeepSpotM
    except ImportError as exc:
        raise RuntimeError(DEEPSPOTM_HELP) from exc
    try:
        return DeepSpotM.from_pretrained("ratschlab/DeepSpotM", source=source)
    except Exception as exc:
        raise RuntimeError(DEEPSPOTM_HELP) from exc
```

On a cluster node with no outbound network, download the weights once on a login node and
point `HF_HOME` at the shared cache.

## Primary sources

- Paper: <https://doi.org/10.64898/2026.06.19.26356060> (medRxiv, posted 22 June 2026)
- Code: <https://github.com/ratschlab/DeepSpotM>
- Weights: <https://huggingface.co/ratschlab/DeepSpotM>
- PyPI: <https://pypi.org/project/deepspotm/>
