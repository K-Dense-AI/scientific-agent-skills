---
name: cellprofiler
description: Runs reproducible CellProfiler microscopy pipelines for nuclear segmentation, cell counts, and per-object fluorescence measurements. Supports image/channel manifests, headless batch execution, segmentation overlays, and measurement QC for 2D fluorescence assays.
license: MIT
compatibility: Python 3.12+ with numpy and tifffile for current helper-only dependencies; a separate CellProfiler 4.2.8 application/container for segmentation. Full CellProfiler has older native dependencies. Network access is needed for installation only. No credentials required.
metadata:
  version: "1.1"
  skill-author: K-Dense Inc.
  upstream-version: "4.2.8"
  last-reviewed: "2026-09-30"
---

# CellProfiler quantitative microscopy

Use this skill when a user needs a repeatable CellProfiler `.cppipe`, nuclear counts, nuclear
fluorescence, or batch microscopy measurements. The bundled assay accepts **one 2D grayscale
TIFF nuclear channel per field**, with black-is-zero (MINISBLACK) pixels and bright nuclei on a
dark background. Palette and white-is-zero TIFFs need an explicit conversion. For volumetric
segmentation, multichannel cell painting, or tissue-specific models, design a separate pipeline
and validate those assumptions rather than silently projecting or splitting the images.

The official application and manual remain **4.2.8**. PyPI publishes **4.2.8.1**; its seven
modules used here and embedded Threshold module match the 4.2.8 source, but this review did
not execute that native distribution. Keep the helper environment separate from CellProfiler's
older dependency stack; see the runtime reference for the verification boundary.

## Workflow

1. Establish the acquisition unit: plate, well, site, time point if present, pixel size, nuclear
   channel identity, camera bit depth, exposure, and biological replicate. Keep original image
   intensities. Convert proprietary formats explicitly with Bio-Formats before using this helper.
2. Create the CSV manifest below. `image_path` is absolute or relative to the manifest; sample IDs use letters, digits, dots, dashes, or underscores; sample IDs
   and plate/well/site combinations are unique. Use a nonnumeric sample ID such as `sample_001`:
   LoadData infers column types and can otherwise turn `001` into `1`. Avoid surrounding
   whitespace in identifiers. TIFFs must be uint8 or uint16, single plane/series/resolution, and
   nonconstant. The helper rejects RGB, z-stacks, and float images rather than guessing channels.
3. Use [assets/nuclei.cppipe](assets/nuclei.cppipe) as a starting pipeline: LoadData →
   IdentifyPrimaryObjects → intensity/size measurements → outline overlay → CSV export.
   The initial diameter range is 8–80 **pixels**, with global Otsu thresholding, no threshold
   smoothing, and border objects excluded. Calibrate this
   range from representative images and acquisition pixel size before comparing conditions.
4. Run a small pilot spanning controls, low/high density, dim images, and plate edges. Inspect
   saved overlays for missed nuclei, splits, merges, and edge exclusions. Adjust thresholding
   and declumping in CellProfiler, export the tuned `.cppipe`, and pass `--pipeline` to preserve
   it. Do not choose settings separately for each treatment to make their counts agree.
5. Freeze the tuned pipeline and analyze the batch. Review input saturation warnings, zero
   counts, count/area distributions, and control behavior. Aggregation for inference belongs at
   the biological replicate level; thousands of cells from one well are not independent wells.

## Run the bounded assay

From this skill directory, create `images.csv`:

```csv
sample_id,image_path,plate,well,site
control_A01_1,images/control_A01_1_DAPI.tif,Plate1,A01,1
```

```bash
python scripts/nuclei_assay.py prepare images.csv load_data.csv
python scripts/nuclei_assay.py run images.csv results --executable cellprofiler
python scripts/nuclei_assay.py summarize results
```

`run` requires a fresh/empty output directory and executes CellProfiler with `-c -r`, a saved
pipeline copy, `--data-file`, output folder, and `--done-file`. Success requires exit code zero,
a `Complete` marker, and valid measurement tables. It records the command, pipeline checksum,
input image checksums, and sample QC in `assay_qc.json` before execution, retaining `failed`
status and the error if execution or output validation fails. CellProfiler output goes to
`cellprofiler.log`. Rerun in a new output folder. `summarize` checks CSV contents independently;
it does not prove an engine run completed.

Custom pipelines must preserve `DNA`, `Nuclei`, `Metadata_Sample`, integer-dtype scaling, and
the unprefixed single-object `Image.csv`/`Nuclei.csv` export contract. Keep the required
intensity/area measurements. A renamed object set or different intensity scale needs a
corresponding helper adaptation, not an unchecked `--pipeline` substitution.

The executable can also be the CellProfiler application launcher or a local container launcher;
see [references/runtime-and-qc.md](references/runtime-and-qc.md) for the container target,
filesystem mapping, and verification evidence. `prepare` and `summarize` work without CellProfiler.

## Interpret the outputs

- `Image.csv`: one image/field row, including `Count_Nuclei` and acquisition metadata.
- `Nuclei.csv`: one accepted object per row, with mean/integrated DNA intensity, area, and shape.
- `*_nuclei.png`: green nuclear boundaries over the input image for visual QC.
- `pipeline.cppipe` and `cellprofiler.done`: the exact pipeline copy and engine completion marker.
- `assay_qc.json`: run status, unique image/object keys, exact counts, finite mean/integrated
  intensity and positive area checks, field mean area in pixels, and storage saturation flags.

LoadData ignores camera metadata for scaling in this asset and divides by the integer storage
maximum: uint8 → 255, uint16 → 65535. A 12-bit camera stored in uint16 therefore has a maximum
near 0.0625. Do not compare intensities across different bit depths, exposures, gains, or staining
batches without an explicit calibration. A saturated image can pass segmentation while its
intensity measurement is unusable. Illumination correction and background subtraction are
assay-specific additions; this starter does neither.

The saturation fraction only counts pixels at the **storage maximum**. A 12-bit detector may
saturate at 4095 while the uint16 storage maximum is 65535; inspect the known acquisition ceiling
separately. Integrated intensity sums pixel values and may exceed 1; only per-pixel mean
intensity is constrained to 0–1. The field's mean nuclear intensity weights each nucleus
equally, rather than weighting each pixel equally.

A count check cannot prove correct segmentation. Inspect overlays and independently annotated
fields; report boundary exclusions and segmentation errors alongside the biological result.
The optional synthetic engine test targets a known three-nucleus example, not assay performance
on unseen cell types. It was skipped in the current review because no engine was configured.

## Sources

- [Official example pipelines](https://cellprofiler.org/examples): choose an assay-specific starting point.
- [CellProfiler 4.2.8 manual](https://cellprofiler-manual.s3.amazonaws.com/CellProfiler-4.2.8/index.html): module settings and interpretation.
- [Headless batch processing](https://cellprofiler-manual.s3.amazonaws.com/CellProfiler-4.2.8/help/other_batch.html): command-line execution.
- [Current application download](https://cellprofiler.org/releases) and [PyPI distribution](https://pypi.org/project/cellprofiler/): distinct release targets.
