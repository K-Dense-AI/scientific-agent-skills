---
name: deepspot-m
description: Generate transcriptome-wide virtual spatial transcriptomics from H&E histology with DeepSpot-M. Use when you need spatial gene expression in log1p-CPM for 224x224 tiles at about 20x, want to query protein-coding genes by symbol instead of a fixed panel, or want to run prediction across a whole slide after tiling with histolab.
license: PolyForm-Noncommercial-1.0.0
compatibility: Needs deepspotm 1.0.0 from PyPI (Python 3.10 to 3.13) plus PyTorch. Weights at ratschlab/DeepSpotM on Hugging Face are gated and licensed CC-BY-NC-SA-4.0, so request access on the model page and then run huggingface-cli login. A CUDA GPU speeds up batched inference.
allowed-tools: Read Write Edit Bash
metadata:
  version: "1.1"
  skill-author: Ratschlab, ETH Zurich
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

The code is PolyForm Noncommercial 1.0.0 and the weights are CC-BY-NC-SA-4.0. Use it for
noncommercial research and check both licences before redistributing outputs.

## Installation

```bash
uv pip install deepspotm==1.0.0
```

Version 1.0.0 targets Python 3.10 to 3.13 and pulls in PyTorch. Install the PyTorch build
that matches your CUDA version first if you want GPU inference.

## Model access

The weights are gated:

1. Open <https://huggingface.co/ratschlab/DeepSpotM> and request access.
2. Once access is granted, authenticate the machine that will download them:

```bash
huggingface-cli login
```

`from_pretrained` reads that cached token, so a login is needed once per machine.

## Quick start

```python
from deepspotm import DeepSpotM

model, image_processor = DeepSpotM.from_pretrained("ratschlab/DeepSpotM", source="scgpt")

vals = model.predict_genes(image_processor(pil_tile).unsqueeze(0), ["EPCAM", "CD3D"])
```

`pil_tile` is a PIL image of exactly 224x224 pixels. `image_processor` turns it into a
tensor, `unsqueeze(0)` adds the batch dimension, and `predict_genes` takes the batch plus a
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

Extract tiles at the slide level whose resolution is nearest 0.5 microns per pixel, then
crop to 224x224 there. Resampling from a coarser level changes the texture the backbone
reads.

## Keep the dependency optional

`deepspotm` and its weights are a heavy, gated dependency. Import it inside the function
that needs it so the surrounding project installs, imports and tests without it, and turn
an `ImportError` into a message that names every step:

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
through more than one source when the choice matters to your analysis. See
`references/api.md` for the full call surface, batching and device placement, gene symbol
handling and output units.

## Whole slide workflow

Prediction is per tile, so a slide-scale run is a tiling step followed by batched
inference:

1. Extract 224x224 tiles on a grid with the `histolab` skill, keeping each tile's
   coordinates.
2. Process and stack tiles into batches with `torch.stack`.
3. Call `predict_genes` once per batch with the same gene list.
4. Concatenate batches in a recorded tile-ID order; join coordinates by those IDs,
   checking uniqueness and missing tiles rather than assuming file/report row order.

Keep outputs labeled as model predictions, not measured transcript counts. Validate
on held-out slides/patients with paired assays for the intended tissue and processing
conditions; tiles from one slide are not independent biological replicates. The
released base model also differs from cancer-specific fine-tuned TCGA atlas models.

That matrix is the virtual spatial transcriptomics map for the slide, and it drops
straight into `AnnData` for downstream spatial analysis. `references/whole_slide.md` has a
worked loop, batch sizing and an `AnnData` assembly step.

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

- Paper: <https://doi.org/10.64898/2026.06.19.26356060> (medRxiv, posted 22 June 2026)
- Code: <https://github.com/ratschlab/DeepSpotM>
- Weights: <https://huggingface.co/ratschlab/DeepSpotM>
- PyPI: <https://pypi.org/project/deepspotm/>
