# Preprocessing pipelines, masks, stain handling, and QC

This reference describes **PathML 3.0.8 stable**. It corrects older examples that
called nonexistent `Pipeline.run()`, omitted required mask/label names, or passed
unsupported transform arguments.

## Pipeline execution model

A `Pipeline` is an ordered list of `Transform` objects. `Pipeline.apply(tile)`
modifies one `Tile` in place and returns it. A slide or dataset owns execution:

```python
from pathml.core import HESlide
from pathml.preprocessing import BoxBlur, Pipeline, TissueDetectionHE

slide = HESlide("data/slide-001.svs", backend="openslide")
pipeline = Pipeline(
    [
        BoxBlur(kernel_size=5),
        TissueDetectionHE(mask_name="tissue"),
    ]
)

slide.run(
    pipeline,
    distributed=False,
    tile_size=512,
    tile_stride=512,
    level=0,
    tile_pad=False,
)
```

Stable facts:

- `Pipeline(transform_sequence=None)` and `Pipeline.apply(tile)` are public.
- `Pipeline` has no `run()` method.
- `SlideData.run()` and `SlideDataset.run()` apply pipelines.
- `distributed=True` is the default and may create a local Dask cluster using
  available cores. Start with `distributed=False`.
- Existing tiles are protected unless `overwrite_existing_tiles=True`.
- `write_dir` causes a `<slide.name>.h5path` write after processing.
- `Pipeline.save()` writes a pickle. A pickle is executable on load; never use a
  pipeline file from an untrusted source.

## Stable transform imports

```python
from pathml.preprocessing import (
    AdaptiveHistogramEqualization,
    BinaryThreshold,
    BoxBlur,
    CollapseRunsCODEX,
    CollapseRunsVectra,
    ForegroundDetection,
    GaussianBlur,
    HistogramEqualization,
    LabelArtifactTileHE,
    LabelWhiteSpaceHE,
    MedianBlur,
    MorphClose,
    MorphOpen,
    NucleusDetectionHE,
    Pipeline,
    QuantifyMIF,
    RescaleIntensity,
    SegmentMIF,
    SegmentMIFRemote,
    StainNormalizationHE,
    SuperpixelInterpolation,
    TissueDetectionHE,
)
```

There is no stable `transform='...'` registry and no safe reason to construct
transforms from arbitrary Python expressions. Parse a strict allowlisted config,
then instantiate known classes explicitly.

## Tissue detection

```python
from pathml.preprocessing import TissueDetectionHE

tissue = TissueDetectionHE(
    mask_name="tissue",
    use_saturation=True,
    blur_ksize=17,
    threshold=None,          # Otsu when None
    morph_n_iter=3,
    morph_k_size=7,
    min_region_size=5000,
    max_hole_size=1500,
    outer_contours_only=False,
)
```

The transform expects an H&E `uint8` tile. It:

1. uses HSV saturation or greyscale;
2. median-blurs;
3. applies Otsu or the explicit threshold;
4. performs morphological opening and closing;
5. keeps foreground regions under the configured area/hole policy; and
6. writes `tile.masks["tissue"]`.

`mask_name` is required in practice; `None` fails when `apply()` runs.
`min_region_size`, `max_hole_size`, and morphology kernels are measured in pixels
at the processing level. Re-tune if level or MPP changes.

Tissue detection is tile-local. It can disagree at tile edges, and PathML does not
automatically remove background tiles from the pipeline. Compute and record tissue
coverage after the mask exists:

```python
coverage = float((tile.masks["tissue"] > 0).mean())
keep = coverage >= 0.50
```

Choose the coverage rule on training data and preserve rejected-tile counts.

## Whitespace and artifact QC

These transforms write **tile labels**, not pixel masks:

```python
from pathml.preprocessing import LabelArtifactTileHE, LabelWhiteSpaceHE

whitespace = LabelWhiteSpaceHE(
    label_name="mostly_white",
    greyscale_threshold=230,
    proportion_threshold=0.5,
)
artifact = LabelArtifactTileHE(label_name="artifact")
```

- `LabelWhiteSpaceHE` labels a tile when the proportion of greyscale pixels above
  the threshold exceeds `proportion_threshold`.
- `LabelArtifactTileHE` is a fixed rule-based HSI heuristic for whitespace,
  dark regions, and pen-like colors. It exposes only `label_name`; older examples
  with `pen_threshold` or `bubble_threshold` are invalid.

Neither is a complete slide-quality system. Review representative overlays and
track blur, folds, bubbles, pen, tissue coverage, clipping, color drift, missing
channels, and focus separately. Do not convert a heuristic QC flag into a clinical
quality judgment.

The dependency-free helper provides a deliberately simple synthetic/local check,
not a replacement for PathML:

```bash
python scripts/image_qc.py synthetic --width 256 --height 256
python scripts/image_qc.py inspect --image tests/fixtures/synthetic.ppm --root .
```

It reports brightness/saturation and a coarse tissue-like mask using bounded
pixels. PNG/JPEG/TIFF input needs Pillow, imported only after argument validation.

## H&E stain normalization and separation

```python
from pathml.preprocessing import StainNormalizationHE

normalizer = StainNormalizationHE(
    target="normalize",             # normalize | hematoxylin | eosin
    stain_estimation_method="macenko",  # macenko | vahadane
    optical_density_threshold=0.15,
    regularizer=0.1,
    angular_percentile=0.01,
    background_intensity=245,
)
```

Stable `StainNormalizationHE` does **not** accept `tissue_mask_name`,
`target_od`, or `target_concentrations`. It accepts `stain_matrix_target_od` and
`max_c_target`, and supplies fixed defaults.

To fit a reference:

```python
normalizer.fit_to_reference(training_reference_rgb)
normalized_rgb = normalizer.F(source_rgb)
```

Leakage controls:

- Select the reference and tune OD parameters using training slides only.
- Freeze the fitted stain matrix and target concentration before validation/test.
- Do not choose a reference because test performance looks better.
- Record source slide pseudonym, region coordinates, level, MPP, method, and all
  fitted arrays without direct identifiers.
- Fit on tissue-rich, artifact-free RGB regions. Stable API does not consume a
  tissue mask directly, so crop/filter the reference beforehand.

Macenko and Vahadane are model-based color standardization methods, not guarantees
that biological staining becomes comparable. Preserve raw inputs and assess
whether normalization removes task-relevant signal or amplifies artifacts.

## Simple H&E nucleus mask

```python
from pathml.preprocessing import NucleusDetectionHE

nuclei = NucleusDetectionHE(
    mask_name="nuclei",
    stain_estimation_method="vahadane",
    superpixel_region_size=10,
    n_iter=30,
)
```

This is a simple transform: hematoxylin separation, superpixel interpolation, and
Otsu thresholding. It writes a binary tile mask. It is not HoVer-Net, does not
assign nucleus classes, and should not be treated as a validated cell count.
Inspect touching objects, fragments, necrosis, stain failure, and tile boundaries.

## Binary and morphology building blocks

Useful stable signatures:

```python
from pathml.preprocessing import BinaryThreshold, MorphClose, MorphOpen

threshold = BinaryThreshold(
    mask_name="foreground",
    use_otsu=True,
    threshold=0,
    inverse=False,
)
opened = MorphOpen(mask_name="foreground", kernel_size=5, n_iterations=1)
closed = MorphClose(mask_name="foreground", kernel_size=5, n_iterations=1)
```

`BinaryThreshold.apply()` creates a named mask. `MorphOpen` and `MorphClose`
modify the named mask. Match dtype, polarity, and dimensions explicitly.

## Recommended pilot pipeline

```python
from pathml.preprocessing import (
    BoxBlur,
    LabelArtifactTileHE,
    LabelWhiteSpaceHE,
    Pipeline,
    StainNormalizationHE,
    TissueDetectionHE,
)

pipeline = Pipeline(
    [
        LabelWhiteSpaceHE(
            label_name="mostly_white",
            greyscale_threshold=230,
            proportion_threshold=0.8,
        ),
        LabelArtifactTileHE(label_name="artifact"),
        BoxBlur(kernel_size=3),
        TissueDetectionHE(
            mask_name="tissue",
            min_region_size=5000,
            outer_contours_only=False,
        ),
        StainNormalizationHE(
            target="normalize",
            stain_estimation_method="macenko",
        ),
    ]
)
```

QC labels do not short-circuit later transforms. If expensive stages should run
only on accepted tiles, write an explicit custom transform or bounded manual loop
with a documented policy. Keep the logic deterministic and test it.

## Bounded dry run

PathML has no `max_tiles` argument. Use `islice` for a local pilot:

```python
from itertools import islice

sampled = []
for tile in islice(
    slide.generate_tiles(shape=512, stride=512, pad=False, level=0),
    16,
):
    pipeline.apply(tile)
    sampled.append(
        {
            "coords_ij": tile.coords,
            "shape": tuple(tile.image.shape),
            "tissue_fraction": float((tile.masks["tissue"] > 0).mean()),
            "mostly_white": bool(tile.labels["mostly_white"]),
            "artifact": bool(tile.labels["artifact"]),
        }
    )
```

Plan first:

```bash
python scripts/plan_pipeline.py \
  --width 100000 --height 80000 \
  --tile-size 512 --stride 512 \
  --pipeline TissueDetectionHE,LabelWhiteSpaceHE,StainNormalizationHE \
  --max-tiles 1000000
```

The planner never opens the slide or imports PathML. Supply dimensions from a
trusted technical metadata inspection. Its storage estimate uses h5path's
float16 image/mask payload, excludes counts/labels/metadata, and assumes the
supplied channel count remains unchanged. It is not peak RAM or a guarantee of
available disk. At nonzero levels supply exact `--level-width`/`--level-height`.

## Masks, labels, padding, and overlap

- A tile mask's first two dimensions must match the tile image.
- Use distinct semantic names (`tissue`, `nuclei`, `cell_segmentation`) and record
  whether each mask is binary, semantic, or instance-labeled.
- Instance masks use 0 for background and positive integer object IDs.
- `tile_pad=True` introduces zeros. Document whether padded pixels are ignored in
  QC, stain fitting, loss, and stitching.
- Stable `SlideData.generate_tiles()` cannot slice slide-level masks into padded
  tiles.
- Overlap duplicates tissue/cells. Deduplicate by slide coordinates or use an
  explicit blending/cropping policy before counting.
- Keep masks at the same level as their coordinates. Resampling an instance mask
  requires nearest-neighbor interpolation and relabel/QC.

## Train/validation/test leakage checklist

Do all splitting before:

- choosing stain references;
- estimating QC or tissue thresholds;
- fitting feature scalers;
- learning augmentations or color distributions;
- selecting segmentation parameters;
- extracting overlapping tiles;
- constructing graphs; or
- calibrating model thresholds.

All tiles, regions, serial sections, and repeat scans from one patient belong to
one split. If site/scanner generalization is the target, reserve entire sites or
scanners as designed. Record exclusions before viewing test outcomes.

## Reproducibility record

For each run, retain:

- PathML and dependency lock versions;
- source SHA-256 and pseudonymous IDs;
- backend, level, downsample, MPP, tile size/stride/pad;
- ordered transform names and all constructor values;
- fitted stain arrays and training-only reference provenance;
- QC/mask definitions and per-slide accept/reject totals;
- Dask configuration, worker count, CPU/GPU, and failure/retry policy;
- code revision, random seeds, split manifest hash, and output hashes.

## Sources and further reading

API baseline reviewed 2026-10-01 using the released wheel/tag; hosted docs may lag.

- Stable pipeline guide:
  https://pathml.readthedocs.io/en/stable/creating_pipelines.html
- Stable execution guide:
  https://pathml.readthedocs.io/en/stable/running_pipelines.html
- Stable preprocessing API:
  https://pathml.readthedocs.io/en/stable/api_preprocessing_reference.html
- Stable transforms source:
  https://github.com/Dana-Farber-AIOS/pathml/blob/v3.0.8/pathml/preprocessing/transforms.py
- Stable pipeline source:
  https://github.com/Dana-Farber-AIOS/pathml/blob/v3.0.8/pathml/preprocessing/pipeline.py
- Macenko et al. (2009):
  https://doi.org/10.1109/ISBI.2009.5193250
- Vahadane et al. (2016):
  https://doi.org/10.1109/TMI.2016.2529665
