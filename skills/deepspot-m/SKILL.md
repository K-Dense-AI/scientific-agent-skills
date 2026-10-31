---
name: deepspot-m
description: Generates transcriptome-wide virtual spatial transcriptomics from H&E histology with DeepSpot-M. Used for predicted log1p-CPM expression from 224x224 tiles at about 20x, querying the released protein-coding gene panel by symbol, and whole-slide prediction after resolution-aware tiling with histolab.
license: PolyForm-Noncommercial-1.0.0
compatibility: Requires deepspotm 1.0.0, Python >=3.10 and PyTorch; network and approved Hugging Face access for initial gated weight download. CPU supported; CUDA optional. Optional histolab 0.7.0 tiling requires a separate Python 3.10/3.11 environment and OpenSlide. AnnData is needed for H5AD export.
allowed-tools: Read Write Edit Bash
metadata:
  version: "1.2"
  skill-author: Ratschlab, ETH Zurich
  last-reviewed: "2026-09-30"
---

# DeepSpot-M

## Overview

DeepSpot-M is a multimodal foundation model that maps a 224x224 H&E histology tile to
spatial gene expression in log1p-CPM. The output is virtual spatial transcriptomics: one
value per queried gene per tile, laid out on the grid the tiles came from.

A LoRA-adapted pathology foundation backbone (Midnight) tokenises the tile. A
cross-attention gene decoder lets each gene query attend to the patch tokens, and a gene
router hypernetwork builds gene-specific projections from frozen biological embeddings
(Evo 2, Orthrus, ProtT5, scGPT, Apertus). Genes enter the model as queryable embeddings
rather than fixed output slots, so the released model covers a ~19k protein-coding gene
panel including genes unseen in training. The panel ships with the weights as
`tokens.csv` and is exposed as `model.gene_names`; genes outside it cannot be queried in
this release.

Applied to TCGA, the model produced a virtual spatial transcriptomics atlas of 28,664
slides across 32 cancer types.

## Licensing

The code is PolyForm Noncommercial 1.0.0 and the weights are CC-BY-NC-SA-4.0.
The current model access form additionally restricts eligibility to academic/public
nonprofit researchers without concurrent commercial affiliations and excludes
commercially funded/collaborative use. Read the live declarations before requesting
access; a noncommercial intention alone does not establish eligibility. Research use
only, not clinical or diagnostic use. Preserve the applicable attribution and licenses.

## Installation

```bash
uv pip install deepspotm==1.0.0
```

PyPI 1.0.0 declares Python >=3.10 without an upper bound; that is not proof of
compatibility with every future dependency release. Use an isolated environment.
Install the PyTorch build that matches your CUDA runtime if using a GPU.
The optional histolab 0.7.0 tiler requires Python <3.12 and an older scientific stack:
run tiling separately and exchange PNG tiles plus a coordinate manifest.

## Model access

The weights are gated:

1. Open <https://huggingface.co/ratschlab/DeepSpotM> and request access.
2. Once access is granted, authenticate the machine that will download them:

```bash
hf auth login
```

The Hugging Face downloader uses cached credentials or `HF_TOKEN`; approval and
authentication are separate. Set `HF_HOME` before importing Hub libraries if choosing
a cache location. Do not put tokens in code. An approved local model directory can
be loaded offline.

## Quick start

Illustrative gated inference; the loading/query API and local preprocessing were
checked without downloading the weights:

```python
import torch
from PIL import Image
from deepspotm import DeepSpotM

device = "cuda" if torch.cuda.is_available() else "cpu"
revision = "48be27af436a50e5c74175680ac2b7b2596a506b"
model, image_processor = DeepSpotM.from_pretrained(
    "ratschlab/DeepSpotM", source="scgpt", device=device, revision=revision
)

with Image.open("tile.png") as image:
    if image.size != (224, 224):
        raise ValueError("Expected a pre-tiled 224x224 image at verified ~0.5 um/px")
    batch = image_processor(image.convert("RGB")).unsqueeze(0).to(device)
genes = ["EPCAM", "CD3D"]
vals = model.predict_genes(batch, genes).cpu()  # shape (1, 2)
```

`image_processor` turns a PIL image into a tensor; `unsqueeze(0)` adds the batch
dimension, and `predict_genes` takes the batch plus a
list of HGNC gene symbols. Values come back in log1p-CPM, aligned with the gene list you
passed, so keep that list beside the output to keep the columns labelled. Symbols must be
in the released ~19k-gene panel (`model.gene_names`); an unknown symbol raises `KeyError`
naming the offending genes.

## Tile requirements

Tiles must be 224x224 RGB at roughly 20x magnification (about 0.5 microns per pixel). Check
the size at the boundary of your pipeline rather than passing an unchecked crop through:

```python
TILE_PX = 224

def require_tile(tile):
    """Return an RGB 224x224 tile, or raise if the crop is the wrong size."""
    if tile.size != (TILE_PX, TILE_PX):
        raise ValueError(
            f"DeepSpot-M expects a {TILE_PX}x{TILE_PX} tile at about 20x "
            f"(~0.5 microns per pixel); got {tile.size[0]}x{tile.size[1]}. "
            "Re-tile at the matching level or resample the crop."
        )
    return tile.convert("RGB")
```

Pixel size alone does not verify magnification. Read both MPP axes and the actual
level downsample factors; use a native level only if its physical resolution is
close enough to the chosen target. Otherwise explicitly resample from sufficiently
fine source pixels and record the transform. Never infer 20x from a level number.
The returned processor resizes/crops images but cannot establish their physical MPP.

## Keep the dependency optional

`deepspotm` and its weights are a heavy, gated dependency. Import it inside the function
that needs it so the surrounding project installs, imports and tests without it, and turn
an `ImportError` into a message that names every step:

```python
DEEPSPOTM_HELP = (
    "DeepSpot-M is unavailable. Install it with `uv pip install deepspotm==1.0.0`, request "
    "access to the gated weights at https://huggingface.co/ratschlab/DeepSpotM, then "
    "authenticate with `hf auth login`."
)

def load_deepspotm(source="scgpt"):
    try:
        from deepspotm import DeepSpotM
    except ImportError as exc:
        raise RuntimeError(DEEPSPOTM_HELP) from exc
    return DeepSpotM.from_pretrained("ratschlab/DeepSpotM", source=source)
```

## Embedding sources

`source` selects which frozen gene embedding the router builds projections from. It is one
of five values:

| `source`  | Gene embedding                    |
| --------- | --------------------------------- |
| `evo2`    | genomic sequence                  |
| `orthrus` | RNA                               |
| `prott5`  | protein sequence                  |
| `scgpt`   | single-cell expression            |
| `apertus` | language model                    |

Each gives a different view of gene identity. Pick one per run, and run the same tiles
through more than one source when the choice matters to your analysis. The released
multi-source model can switch using `model.set_source(name)`; no reload is required.
See
`references/api.md` for the inference call surface, batching and device placement, gene symbol
handling and output units.

## Whole slide workflow

Prediction is per tile, so a slide-scale run is a tiling step followed by batched
inference:

1. Verify slide MPP, extract 224x224 tiles on a tissue grid with the `histolab` skill,
   and keep each tile's level-0 bounding box and measured output MPP.
2. Process and stack tiles into batches with `torch.stack`.
3. Call `predict_genes` once per batch with the same gene list.
4. Concatenate batches in a recorded tile-ID order; join coordinates by those IDs,
   checking uniqueness and missing tiles rather than assuming file/report row order.

Keep outputs labeled as model predictions, not measured transcript counts. Validate
on held-out slides/patients with paired assays for the intended tissue and processing
conditions; tiles from one slide are not independent biological replicates. The
released base model also differs from cancer-specific fine-tuned TCGA atlas models.

That matrix is the virtual spatial transcriptomics map for the slide, and it drops
into `AnnData` for downstream analysis. [Whole-slide workflow](references/whole_slide.md)
has a worked loop, batch sizing and an `AnnData` assembly step.

## Verification scope

Reviewed the current PyPI 1.0.0 wheel and matching upstream model source on
2026-09-30. CPU checks used Python 3.12.10, Torch 2.7.1, Torchvision 0.22.1,
Transformers 5.18.0, PEFT 0.21.1, Lightning 2.6.6 and Hugging Face Hub 1.33.0.
Synthetic checks cover loading/query contracts, normalization, resolution rejection,
coordinate joins and H5AD round-trip. Gated weights, CUDA, real-slide tiling and
biological prediction accuracy were not tested; full inference examples are illustrative.

## Common use cases

- Spatial expression maps for marker genes across a tumour section.
- Transcriptome-wide prediction over a slide cohort with no matching assay run.
- Querying any of the ~19k panel genes by symbol, including genes unseen in training —
  far beyond the few hundred genes of a typical spatial assay panel.
- Adding an expression channel to a morphology-only histology pipeline.
- Building a slide-level cohort atlas, as done for TCGA.

## Detailed references

- `references/api.md`: `from_pretrained` and `predict_genes` in full, the five embedding
  sources and how to choose, batching, device placement, gene symbol handling, and
  converting log1p-CPM output.
- `references/whole_slide.md`: tiling with histolab, a slide-scale prediction loop,
  assembling and storing a tiles-by-genes matrix, and cohort-scale runs.

## Primary sources

- Paper: <https://doi.org/10.64898/2026.06.19.26356060> (medRxiv, 2026)
- Code: <https://github.com/ratschlab/DeepSpotM>
- Weights: <https://huggingface.co/ratschlab/DeepSpotM>
- PyPI: <https://pypi.org/project/deepspotm/>
