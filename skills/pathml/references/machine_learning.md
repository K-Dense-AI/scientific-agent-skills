# Machine learning, inference batching, and model trust

This reference targets **PathML 3.0.8 from PyPI**, reviewed 2026-10-01.
The architecture/inference examples are illustrative and checked against the
released source; no model weights or native inference stack were run.

## Stable ML exports

```python
from pathml.ml import (
    GNNLayer,
    HACTNet,
    HoVerNet,
    TileDataset,
    loss_hovernet,
    post_process_batch_hovernet,
)
```

The documented dataset import is usually:

```python
from pathml.datasets import TileDataset
```

PathML provides model architectures and helpers. Stable constructors do not
accept `pretrained=True`, do not expose `mode="fast"`, and do not download
official HoVer-Net/HACTNet checkpoints automatically.

## HoVer-Net

Stable constructor:

```python
from pathml.ml import HoVerNet

model = HoVerNet(n_classes=6)
```

- `n_classes=None` creates nucleus-pixel (NP) and horizontal/vertical (HV)
  branches for segmentation.
- An integer adds a nucleus-classification (NC) branch.
- Forward output is a list `[np_logits, hv]` or
  `[np_logits, hv, nc_logits]`.
- The architecture initializes weights; it is not a pretrained model loader.

Use the class count and label order from the exact dataset schema. PanNuke's
stable PathML representation can use five nucleus categories plus background;
do not silently map labels from another implementation.

Training helpers:

```python
from pathml.ml import loss_hovernet, post_process_batch_hovernet

outputs = model(images)
loss = loss_hovernet(
    outputs=outputs,
    ground_truth=[nucleus_mask, horizontal_vertical_map],
    n_classes=6,
)

instances, classified_instances = post_process_batch_hovernet(
    outputs=outputs,
    n_classes=6,
    small_obj_size_thresh=10,
    kernel_size=21,
    h=0.5,
    k=0.5,
)
```

Verify tensor shapes from the stable API:

```text
NP logits: (batch, 2, height, width)
HV maps:   (batch, 2, height, width)
NC logits: (batch, n_classes, height, width)
```

For `n_classes=6`, `nucleus_mask` above is a six-channel target with background
in the **last** channel, matching PathML's PanNuke representation. A single
binary mask is only appropriate when `n_classes=None`. Preserve the label
ordering; the loss derives foreground by inverting the final target channel.

`post_process_batch_hovernet` returns instance maps with 0 as background and
positive object IDs. The classification output uses one channel per class with
instance IDs in the selected class channel.

## Evaluation mode is not dynamic evaluation

PyTorch's `model.eval()` method switches module behavior such as dropout and
batch normalization to evaluation mode. It is **not** Python's dangerous built-in
expression evaluator and does not execute a string.

To avoid ambiguity in executable examples, the equivalent explicit form is:

```python
import torch

model.train(False)
with torch.inference_mode():
    outputs = model(images)
```

Never use Python dynamic evaluation or execution to load a model, transform,
configuration, metric, or class name. Use an allowlist and normal constructors.

## PanNuke training data

```python
from pathml.datasets import PanNukeDataModule

data = PanNukeDataModule(
    data_dir="approved_data/pannuke",
    download=False,
    shuffle=True,
    nucleus_type_labels=True,
    split=1,
    batch_size=8,
    hovernet_preprocess=True,
)

train_loader = data.train_dataloader
validation_loader = data.valid_dataloader
test_loader = data.test_dataloader
```

The dataloaders are properties, not methods. `hovernet_preprocess=True` adds the
HV target. Set `download=True` only after explicit consent to the Warwick
download, storage estimate, license review, and endpoint disclosure.

Do not assume the published folds satisfy every patient/source-slide grouping
claim. Audit the dataset's provenance and duplicates for the intended study.

## HACTNet

Stable signature:

```python
from pathml.ml import HACTNet

model = HACTNet(
    cell_params=cell_gnn_parameters,
    tissue_params=tissue_gnn_parameters,
    classifier_params=classifier_parameters,
)
```

HACTNet consumes a batched `HACTPairData` object with cell and tissue features,
their edge indices, a cell-to-tissue assignment, and a target. Parameter
dictionaries configure PathML `GNNLayer` and its classifier; use the v3.0.8
tutorial/API rather than copying a configuration from another PyG release.

Before training, validate:

- feature dimensions match each dictionary;
- assignment indices are valid tissue-node indices;
- graph batches carry the expected `x_cell_batch`/`x_tissue_batch`;
- targets are slide/patient-level as intended;
- all graphs from a patient remain in one split.

`pathml.datasets.EntityDataset` loads `.pt` graph objects with unrestricted
PyTorch deserialization. Use it only for trusted project-generated artifacts.

## Checkpoint trust

Never load an untrusted `.pt`, `.pth`, `.ckpt`, pickle, joblib, or saved pipeline.
Such formats can execute code during deserialization.

For a trusted checkpoint:

1. obtain it from the model owner or an approved registry;
2. verify exact SHA-256/signature before opening;
3. record architecture source revision, dependency lock, license, training data,
   preprocessing, class order, and expected tensor schema;
4. inspect in a disposable network-disabled environment;
5. load only the minimal weights-only representation when the producing PyTorch
   version supports it;
6. enforce file, tensor, RAM, time, and device limits; and
7. validate on synthetic tensors before any pathology data.

The bundled planner refuses checkpoint/model extensions and never imports Torch,
ONNX, PathML, or a model class.

## Local ONNX inference

Stable exports:

```python
from pathml.inference import (
    HaloAIInference,
    Inference,
    check_onnx_clean,
    convert_pytorch_onnx,
    remove_initializer_from_input,
)
```

For a reviewed local model:

```python
import numpy as np
from pathml.inference import Inference

inference = Inference(
    model_path="models/reviewed_model.onnx",
    input_name="data",
    num_classes=4,
    model_type="segmentation",
    local=True,
)
# Illustrative: supply a reviewed model expecting [1, 3, 256, 256] float32.
# Real preprocessing/range must come from that model's card.
image_hwc = np.zeros((256, 256, 3), dtype=np.float32)
prediction = inference.F(image_hwc)
assert prediction.shape == (1, 4, 256, 256)
```

Stable `Inference.apply()` replaces `tile.image` with model output. If the raw
image must be preserved, write a custom reviewed transform that stores
predictions separately or use a separate inference loop.

`Inference`:

- checks a local ONNX model for initializers also exposed as inputs;
- verifies the model with ONNX;
- reloads the model and creates an ONNX Runtime session on every call;
- requires the named input and fixed spatial dimensions (symbolic dimensions
  appear as zero in its check), and casts inputs to float32;
- reshapes 3-D HWC to a batch of NCHW;
- concatenates multiple same-spatial-size outputs along channels.

It does not normalize intensities, apply softmax, select a device provider, or
check the entire channel/batch schema for you. Validate all inputs and outputs
against the model card. Generic `Inference.apply()` can leave NCHW output in
`tile.image`; do not feed that into HWC preprocessing, masks, or a tile dataset
without an explicit adapter. For throughput, use a reviewed ONNX Runtime loop
with one reused session and separately stored predictions/coordinates.

`remove_initializer_from_input(source, destination)` rewrites the model. Do not
overwrite the original; verify the destination hash and outputs. ONNX parsing is
not a guarantee of safety—malformed models can exploit parser/runtime bugs or
request excessive resources.

## Current ONNX export/runtime boundary

PyPI 3.0.8 declares Torch 2.12.0, torch-geometric 2.8.0, ONNX 1.22.0 and
onnxscript 0.7.1, while retaining ONNX Runtime `>=1.17,<1.18`. TorchVision is not
a declared wheel dependency; provision a compatible version separately if a
chosen feature requires it.

`convert_pytorch_onnx(model, dummy_tensor, model_name, opset_version=10,
input_name="data")` explicitly sets `dynamo=False` and supplies no dynamic axes.
Put the model in evaluation mode before export. The helper does not establish
compatibility with the older runtime: ONNX Runtime 1.17 supports ONNX opset up to
20 and IR up to 9 per its official table. Check **both** the emitted IR/opset and
operators, then compare outputs against the source framework on synthetic
inputs. Do not merely edit the IR number to bypass an incompatible model.

## Remote model classes

Do not instantiate without explicit network consent:

- `RemoteMesmer` / `SegmentMIFRemote` downloads
  `https://huggingface.co/pathml/test/resolve/main/mesmer.onnx`.
- `RemoteTestHoverNet` downloads
  `https://huggingface.co/pathml/test/resolve/main/hovernet_fast_tiatoolbox_fixed.onnx`.

Stable code downloads model bytes and performs inference locally; it does not
upload slide pixels. The GET still discloses connection metadata and lacks a
built-in checksum/size/timeout policy. Prefer approved local artifacts.

See `multiparametric.md` for the full consent template.

## Bounded inference planning

Plan without opening a model:

```bash
python scripts/plan_inference.py \
  --tile-count 4000 \
  --batch-size 16 \
  --channels 3 \
  --height 256 \
  --width 256 \
  --dtype float32 \
  --activation-multiplier 8 \
  --max-memory-mib 4096
```

Or supply a bounded strict JSON model card containing only metadata:

```json
{
  "schema_version": "1.0",
  "model_id": "reviewed-hovernet",
  "artifact_sha256": "hex-digest",
  "input_shape": [3, 256, 256],
  "dtype": "float32",
  "output_elements_per_tile": 589824,
  "activation_multiplier": 8.0
}
```

```bash
python scripts/plan_inference.py \
  --model-card models/reviewed_model_card.json \
  --root . \
  --tile-count 4000 \
  --batch-size 16
```

The estimate is a planning bound, not a GPU profiler. Include model parameters,
runtime workspace, framework caches, graph memory, postprocessing, and stitching
headroom. Pilot at a smaller batch and monitor actual peak memory.

## Batch execution

For local PyTorch architecture code:

```python
import torch

model.train(False)
for tile_images, tile_masks, tile_labels, slide_labels in loader:
    inputs = tile_images.to(device, non_blocking=True)
    with torch.inference_mode():
        outputs = model(inputs)
    # Move bounded outputs to CPU and attach the original slide/tile coordinates.
```

PathML's label dictionaries may need a custom `collate_fn`; never lose coordinate
keys. Avoid collecting all prediction maps in RAM. Stream bounded batches to a
structured local output and flush per slide.

For ONNX, stable `Inference` operates one PathML tile at a time because its
reshape method adds a batch dimension. For true batch inference, build a separate
reviewed ONNX Runtime loop around `TileDataset`, validate the model's dynamic or
fixed batch axis, and retain coordinates.

## Overlap and stitching

For dense outputs:

- use context overlap to reduce edge artifacts;
- emit only a central crop, or blend with a documented weight window;
- map every output pixel to selected-level and level-0 coordinates;
- account for padding;
- avoid counting an object more than once;
- record output stride/resolution and interpolation;
- test a synthetic object crossing tile boundaries.

PathML includes tile-stitching utilities, but verify their stable signature and
output semantics for the exact task rather than assuming `average`, `max`, or
weighted options from unrelated examples.

## Evaluation

PathML 3.0.8 does not export the broad
`pathml.ml.metrics.dice_coefficient`/`panoptic_quality` API shown in older
references. Implement or import metrics from a pinned, validated package and
record the exact definition.

For segmentation/classification:

- Dice/IoU for semantic masks;
- detection precision/recall/F1 with a fixed matching rule;
- AJI/PQ for instances with explicit implementation/version;
- per-class confusion, calibration, and uncertainty;
- slide/patient-level bootstrap or hierarchical confidence intervals;
- external site/scanner/stain evaluation.

Choose thresholds on training/validation only. Keep the test set sealed until the
analysis plan is frozen. Do not treat tiles/nuclei as independent patients.

## Model provenance card

Record:

- model ID, architecture, code revision, and framework versions;
- artifact SHA-256/signature, size, license, and source URL/owner;
- training/validation cohorts and patient-level split;
- stain, scanner, MPP, level, tile/context size, normalization, channel order;
- class names/order, output schema, postprocessing, and thresholds;
- expected dtype/range and batch support;
- hardware/runtime, deterministic settings, seeds, and known limitations;
- subgroup/site performance and intended research use;
- statement that the model is not for diagnostic use.

Never include direct patient identifiers or sensitive example tiles in a model
card.

## Sources and further reading

API baseline reviewed 2026-10-01 using the released wheel/tag; hosted docs may lag.

- Stable ML API:
  https://pathml.readthedocs.io/en/stable/api_ml_reference.html
- Stable inference API:
  https://pathml.readthedocs.io/en/stable/api_inference_reference.html
- Stable HoVer-Net source:
  https://github.com/Dana-Farber-AIOS/pathml/blob/v3.0.8/pathml/ml/models/hovernet.py
- Stable HACTNet source:
  https://github.com/Dana-Farber-AIOS/pathml/blob/v3.0.8/pathml/ml/models/hactnet.py
- Stable inference source:
  https://github.com/Dana-Farber-AIOS/pathml/blob/v3.0.8/pathml/inference/inference.py
- ONNX Runtime compatibility table:
  https://onnxruntime.ai/docs/reference/compatibility.html
- GitHub v3.0.7 release:
  https://github.com/Dana-Farber-AIOS/pathml/releases/tag/v3.0.7
- Graham et al. (2019), HoVer-Net:
  https://doi.org/10.1016/j.media.2019.101563
- Pati et al. (2022), HACT:
  https://doi.org/10.1016/j.media.2021.102264
