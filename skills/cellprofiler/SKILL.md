---
name: cellprofiler
description: Runs reproducible CellProfiler microscopy pipelines for nuclear segmentation, cell counts, and per-object fluorescence measurements. Supports image/channel manifests, headless batch execution, segmentation overlays, and measurement QC for 2D fluorescence assays.
license: MIT
compatibility: Python 3.10+ with numpy and tifffile for bundled helpers; CellProfiler 4.2.8 executable or its Linux container for segmentation. Network access is needed for installation only. No credentials required.
metadata:
  version: "1.0"
  skill-author: K-Dense Inc.
  upstream-version: "4.2.8"
---

# CellProfiler quantitative microscopy

Use this skill when a user needs a repeatable CellProfiler `.cppipe`, nuclear counts, nuclear
fluorescence, or batch microscopy measurements. The bundled assay accepts **one 2D grayscale
TIFF nuclear channel per field**, with bright nuclei on a dark background. For volumetric
segmentation, multichannel cell painting, or tissue-specific models, design a separate pipeline
and validate those assumptions rather than silently projecting or splitting the images.

## Workflow

1. Establish the acquisition unit: plate, well, site, time point if present, pixel size, nuclear
   channel identity, camera bit depth, exposure, and biological replicate. Keep original image
   intensities. Convert proprietary formats explicitly with Bio-Formats before using this helper.
2. Create the CSV manifest below. `image_path` is absolute or relative to the manifest; sample IDs use letters, digits, dots, dashes, or underscores; sample IDs
   and plate/well/site combinations are unique. TIFFs must be uint8 or uint16, single plane, and
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

`run` requires a fresh/empty output directory and executes CellProfiler with `-c -r`, an explicit
pipeline, `--data-file`, and output folder. It records the command, pipeline checksum, input image
checksums, and sample QC in `assay_qc.json`; CellProfiler output goes to `cellprofiler.log`.
A failed process stays failed, with its log available for diagnosis. Rerun in a new output folder.

The executable can also be the CellProfiler application launcher or a local container launcher;
see [references/runtime-and-qc.md](references/runtime-and-qc.md) for the tested container,
filesystem mapping, and verification evidence. `prepare` and `summarize` work without CellProfiler.

## Interpret the outputs

- `Image.csv`: one image/field row, including `Count_Nuclei` and acquisition metadata.
- `Nuclei.csv`: one accepted object per row, with mean/integrated DNA intensity, area, and shape.
- `*_nuclei.png`: green nuclear boundaries over the input image for visual QC.
- `assay_qc.json`: count consistency and finite normalized intensity checks, plus saturation flags.

LoadData ignores camera metadata for scaling in this asset and divides by the integer storage
maximum: uint8 → 255, uint16 → 65535. A 12-bit camera stored in uint16 therefore has a maximum
near 0.0625. Do not compare intensities across different bit depths, exposures, gains, or staining
batches without an explicit calibration. A saturated image can pass segmentation while its
intensity measurement is unusable. Illumination correction and background subtraction are
assay-specific additions; this starter does neither.

A count check cannot prove correct segmentation. Inspect overlays and independently annotated
fields; report boundary exclusions and segmentation errors alongside the biological result.
The synthetic integration test validates a known three-nucleus example, not assay performance
on unseen cell types.

## Sources

- [Official example pipelines](https://cellprofiler.org/examples): choose an assay-specific starting point.
- [CellProfiler 4.2.8 manual](https://cellprofiler-manual.s3.amazonaws.com/CellProfiler-4.2.8/index.html): module settings and interpretation.
- [Headless batch processing](https://cellprofiler-manual.s3.amazonaws.com/CellProfiler-4.2.8/help/other_batch.html): command-line execution.
