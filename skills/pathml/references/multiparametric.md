# Multiparametric imaging, spatial data, and Mesmer integration

This reference targets **PathML 3.0.8 stable**. It distinguishes generic loading
support from a dedicated analysis implementation and corrects older examples that
invented MERFISH decoders, spectral unmixing options, named-channel arguments, or
a DeepCell cloud prediction endpoint.

## Stable slide types and array order

```python
from pathml.core import CODEXSlide, MultiparametricSlide, VectraSlide

codex = CODEXSlide(
    "data/codex_region.tif",
    name="slide-001",
    backend="bioformats",
)
vectra = VectraSlide(
    "data/vectra_component_data.tif",
    name="slide-002",
)
generic = MultiparametricSlide(
    "data/multiplex.ome.tiff",
    name="slide-003",
)
```

Bio-Formats returns PathML arrays as:

```text
(i, j, z, c, t) = (row, column, z-plane, channel, time/cycle)
```

Generic Bio-Formats support means a format may be readable. It does not mean
PathML implements registration, decoding, spectral unmixing, compensation,
autofluorescence correction, cell phenotyping, or platform-specific QC for that
format.

Stable PathML has convenience classes for CODEX and Vectra. It can load examples
of MERFISH/Visium-like image data through generic backends, but it has no
`MERFISHSlide`, `DecodeMERFISH`, or `AssignTranscripts` stable API.

## Channel manifest

Create a local, versioned channel manifest before processing:

```text
channel_index,channel_name,marker,cycle,z_plane,role,exposure,batch
0,DAPI,DAPI,0,2,nuclear,100,run-01
1,CD45,CD45,0,2,membrane,150,run-01
2,CD3,CD3,1,2,measurement,200,run-01
```

Validate:

- channel index is zero-based, unique, and matches array order;
- DAPI/nuclear and membrane/cytoplasm choices are biologically and technically
  appropriate;
- cycle and Z-plane mappings are documented;
- blank, autofluorescence, isotype, and positive controls are identified;
- saturation, clipping, hot pixels, bleed-through, exposure, registration, and
  missing channels are assessed;
- marker names are not inferred from position alone.

Do not include patient names, accession numbers, or other direct identifiers.

## CODEX collapse

Stable signature:

```python
from pathml.preprocessing import CollapseRunsCODEX, Pipeline

pipeline = Pipeline([CollapseRunsCODEX(z=2)])
```

`CollapseRunsCODEX(z)` expects `(i, j, z, c, t)`, combines `c` and `t` into one
channel axis, selects the zero-based Z-plane, and produces `(i, j, c*t)`.

It does **not**:

- register cycles;
- choose a focal plane automatically;
- subtract background;
- reorder markers from a manifest;
- aggregate with max/mean/median; or
- correct illumination or bleed-through.

Perform and validate those operations upstream with a protocol appropriate to the
acquisition system. Record the exact flattened `(cycle, channel) → output index`
mapping.

The actual C-order reshape maps `(channel, cycle)` to
`output_index = channel * n_cycles + cycle` (cycle varies fastest). Verify it
with a channel-coded synthetic array; do not assume cycle-major order. The
released Z-index assertion checks the flattened channel axis by mistake, so
validate `0 <= z < image.shape[2]` yourself before calling it.

## Vectra collapse

Stable signature:

```python
from pathml.preprocessing import CollapseRunsVectra

collapse = CollapseRunsVectra()
```

It applies `numpy.squeeze` to coerce the image toward `(i, j, c)`. It does not
accept wavelengths and does not perform spectral unmixing or autofluorescence
correction. Supply already unmixed component data or perform those steps with
validated upstream software. Verify that squeezing singleton axes did not remove
an axis whose semantics must be retained.

## Segmentation choices

### Preferred no-network posture

For sensitive images, use an institution-approved local segmenter with a
reviewed, checksummed local model and network disabled. PathML's generic local
ONNX `Inference` can run compatible models, but Mesmer-specific pre/postprocessing
must match the model card exactly.

PathML 3.0.8 has no fully offline, nondeprecated Mesmer convenience class that
accepts a pre-provisioned model without trying a network download. Plan this
constraint before choosing PathML's Mesmer wrapper.

### `SegmentMIFRemote`: local inference after a model download

Stable signature:

```text
SegmentMIFRemote(
    model_path="temp.onnx",
    nuclear_channel=<integer index>,
    cytoplasm_channel=<integer index>,
    image_resolution=0.5,
    preprocess_kwargs=None,
    postprocess_kwargs_nuclear=None,
    postprocess_kwargs_whole_cell=None,
)
```

Despite the name, v3.0.8 does not send images to a DeepCell prediction service.
At construction it performs an HTTP GET from:

```text
https://huggingface.co/pathml/test/resolve/main/mesmer.onnx
```

It writes the response to `temp.onnx`, loads that ONNX model, and runs pixels
locally with ONNX Runtime. The outbound request discloses ordinary connection
metadata (for example IP address and request headers) to Hugging Face; image
pixels, channel data, and PathML metadata are not uploaded by this stable source.

Security and reproducibility limitations:

- construction has a network side effect;
- there is no built-in checksum, signature, offline flag, timeout, or size cap;
- inherited `local=False` forces `temp.onnx`, even if `SegmentMIFRemote` receives
  a different `model_path`; a supplied destination does not prevent overwriting
  that working-directory file;
- the model supports 256×256 input and 0.5 µm/pixel in stable code;
- `nuclear_channel` and `cytoplasm_channel` are integer indices, not names.

Validate HWC input (despite a contradictory channel-first wrapper docstring),
both spatial dimensions equal to 256, distinct valid channel indices, and
0.5 µm/pixel before constructing/running the wrapper. The source only prints for
other resolutions and its shape check uses `and`, so one incorrect spatial axis
can escape that check; it does not resample to the model resolution for you.

Do not instantiate it until the user explicitly consents to that endpoint and
download. Do not use it in a network-disabled workflow.

On 2026-10-01 the public Hugging Face model metadata listed both artifacts and
HEAD requests followed download redirects successfully (Mesmer 104,218,552 bytes;
HoVer-Net test model 151,068,601 bytes). These were unauthenticated metadata/HEAD
probes only, not weight downloads, checksum verification, or inference tests.

### Deprecated `SegmentMIF`

`SegmentMIF` imports `deepcell.applications.Mesmer` and calls its prediction API
locally. PathML emits a deprecation warning directing users to
`SegmentMIFRemote`. `deepcell` is not a PathML extra and is not declared in
PathML's PyPI dependencies. Depending on the DeepCell version/cache, model
initialization may fetch weights.

Do not silently install an unpinned DeepCell stack or assume compatibility with
PathML's pinned Python/TensorFlow ecosystem. If legacy replication requires it,
lock the complete environment, pre-provision and verify artifacts, test with
synthetic data, disable network during sensitive runs, and document the
deprecation.

## Explicit network consent template

Before any download or hosted inference, present:

```text
Action: download model | download public dataset | upload image for prediction
Destination: exact HTTPS host and path
Outbound data: exact pixels/channels/metadata/identifiers, or "none; GET only"
Inbound artifact: name, expected bytes, version, SHA-256/signature
Local destination: approved path
Retention/logging: vendor and institutional policy
Authorization: data-use agreement/consent/waiver and user approval
Alternative: local, network-disabled method
```

Only proceed after explicit opt-in. A future hosted endpoint that receives image
data needs a new disclosure; do not infer permission from consent to download a
model. Never upload PHI by default.

## Quantification

Read Bio-Formats tiles with `normalize=False` for measurement. Its default
normalization casts to 8-bit and can destroy quantitative dynamic range; h5path
then separately stores images/masks as float16. Keep authoritative raw channels
and integer instance maps outside that lossy storage path.

Stable transform:

```python
from pathml.preprocessing import QuantifyMIF

quantify = QuantifyMIF(segmentation_mask="cell_segmentation")
```

Input requirements:

- tile image `(i, j, channels)`;
- instance segmentation `(i, j)` or `(i, j, 1)`;
- 0 is background and each object has a unique positive integer;
- tile slide type has fluorescence stain;
- `tile.coords` is present.

`QuantifyMIF.apply(tile)` writes an `AnnData` object to `tile.counts`.
Stable output contains:

- `X`: per-object mean intensity for each channel;
- `layers["min_intensity"]` and `layers["max_intensity"]`;
- `obs["label"]`, `filled_area`, `euler_number`, `x`, and `y`;
- `obsm["spatial"]`: `(x, y)` centroids.

Channel variables are generated from numeric positions. Assign marker names only
after matching the validated channel manifest:

```python
counts = tile.counts
assert counts.n_vars == len(channel_names)
counts.var_names = channel_names
```

Do not interpret raw intensity as abundance without validated background,
normalization, exposure, compensation/unmixing, segmentation, and batch policies.

## Coordinate conversion

`Tile.coords` uses selected-level `(i, j)`. `QuantifyMIF` adds tile offsets to
region centroids, then stores:

- `obs["y"]`: row coordinate;
- `obs["x"]`: column coordinate;
- `obsm["spatial"]`: `[x, y]`.

Convert selected-level pixels to level-0 and physical units:

```text
x_um = x_selected_level * level_downsample * mpp_x
y_um = y_selected_level * level_downsample * mpp_y
```

Record whether coordinates are pixel centers, integer-rounded centroids, or
continuous region centroids. Preserve source level and MPP. Do not combine slides
with different resolutions in a shared coordinate space without conversion.
The scalar-downsample formula assumes a validated series/pyramid transform and
correct region origins; Bio-Formats series need not form a pyramid, and PathML's
OpenSlide fractional-downsample origin issue must be excluded first.

## Spatial/multiplex schema

For exchange, use one row per cell:

```text
cell_id,patient_id,slide_id,tile_i,tile_j,x,y,coordinate_unit,level,
segmentation_label,area,marker:DAPI,marker:CD3,marker:CD8,...
```

Required invariants:

- `(slide_id, cell_id)` is unique;
- coordinates are finite and nonnegative;
- `coordinate_unit` is explicit (`level_pixels`, `level0_pixels`, or `um`);
- all rows for a slide agree on level/unit/channel schema;
- marker values are finite or use one documented missing-value policy;
- instance IDs do not collide when tiles are merged;
- overlapping-tile duplicate cells are reconciled before counts;
- patient/slide split is included or joinable without PHI.

Validate bounded local CSV:

```bash
python scripts/validate_spatial_schema.py multiplex \
  --input derived/cells.csv \
  --root . \
  --marker-columns marker:DAPI,marker:CD3,marker:CD8
```

## Segmentation and marker QC

Review representative training regions:

- nuclear and whole-cell overlays;
- object count, area, eccentricity, border-touching fraction, holes/fragments;
- merge/split errors and compartment consistency;
- negative/blank controls and background distributions;
- per-channel saturation and dynamic range;
- spatial striping, illumination, cycle registration, and tissue folds;
- cell density by tissue compartment and slide;
- marker distributions by batch/site/scanner;
- effects of image resolution and channel choice.

Freeze QC thresholds before the test set. Report exclusions and sensitivity
analyses rather than hiding failed tiles.

## Combining AnnData safely

Before concatenation:

- make `obs_names` globally unique with pseudonymous slide and cell IDs;
- store `patient_id`, `slide_id`, `site`, `batch`, and `split` in `obs`;
- enforce identical marker identity/order or perform an explicit outer join;
- record raw versus transformed layers;
- preserve coordinate unit/level per slide;
- never batch-correct using held-out test data;
- keep spatial neighbors within slides unless a cross-slide graph is scientifically
  defined.

Threshold cell typing from markers is a research annotation procedure, not a
diagnosis. Use controls and domain review, and report ambiguous/unassigned cells.

## Stable versus absent APIs

Present in stable:

- `MultiparametricSlide`, `VectraSlide`, `CODEXSlide`
- `CollapseRunsCODEX(z)`
- `CollapseRunsVectra()`
- `SegmentMIFRemote(...)`
- deprecated `SegmentMIF(...)`
- `QuantifyMIF(segmentation_mask)`

Not present as stable APIs:

- named-channel arguments such as `"DAPI"` or `"CD45"` for segmentation;
- `CollapseRunsCODEX(method=..., background_subtract=...)`;
- `CollapseRunsVectra(wavelengths=..., unmix=True)`;
- `MERFISHSlide`, `DecodeMERFISH`, or `AssignTranscripts`;
- a DeepCell image-upload URL in PathML;
- automatic marker names in `QuantifyMIF`;
- automatic cell-type annotation.

## Sources and further reading

API baseline reviewed 2026-10-01 using the released wheel/tag; hosted docs may lag.

- Stable loading guide:
  https://pathml.readthedocs.io/en/stable/loading_slides.html
- Stable preprocessing API:
  https://pathml.readthedocs.io/en/stable/api_preprocessing_reference.html
- Stable transforms source:
  https://github.com/Dana-Farber-AIOS/pathml/blob/v3.0.8/pathml/preprocessing/transforms.py
- Stable inference source:
  https://github.com/Dana-Farber-AIOS/pathml/blob/v3.0.8/pathml/inference/inference.py
- Stable multiplex tutorial:
  https://pathml.readthedocs.io/en/stable/examples/link_multiplex_if.html
- Stable CODEX tutorial:
  https://pathml.readthedocs.io/en/stable/examples/link_codex.html
- Greenwald et al. (2022), Mesmer:
  https://doi.org/10.1038/s41587-021-01094-0
- Omar et al. (2025), antibody-based multiplex workflows:
  https://doi.org/10.1016/j.labinv.2025.104220
