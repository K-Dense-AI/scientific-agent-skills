# Runtime and assay verification

## CellProfiler 4.2.8

The pipeline targets the full **CellProfiler 4.2.8**, not merely `cellprofiler-core`:
IdentifyPrimaryObjects and measurement modules live in the full package. The official image
`cellprofiler/cellprofiler:4.2.8` is a Linux amd64 environment. Its digest, rechecked against
the official registry on 2026-09-30, is
`sha256:fec440caa2b44edf80f9bd440a3d8c6b214d72437332ad2586a32d79e2eae2a4`.
Apple Silicon runs that image with `--platform linux/amd64` under emulation.
The image is about 1.54 GB compressed; allow space for its expanded layers before pulling.

The application download and manual still advertise 4.2.8, while PyPI offers **4.2.8.1**
(2026-03-09). Released wheels were inspected without installing their native stack. All seven
pipeline modules, plus Threshold, are byte-identical to the tagged 4.2.8 source. The CLI source
diff adds Wayland display detection; `-c -r -p`, `--data-file`, `-o`, and `--done-file` are
unchanged. This source comparison is not a 4.2.8.1 engine execution test.

For containers, run the helper **inside** a mounted working directory or mount input images,
manifest, pipeline, and outputs at the same absolute paths as the host. LoadData CSV file URLs
must resolve inside the container. A relative path inside a manifest is resolved before export;
a host file URL does not automatically become `/work/...` when mounted there.

Example container pattern, from a working directory containing `images.csv`, `images/`, and a
copy of this skill directory called `cellprofiler-skill/`:

```bash
docker run --rm --platform linux/amd64 --entrypoint python \
  -v "$PWD:/work" -w /work cellprofiler/cellprofiler:4.2.8 \
  cellprofiler-skill/scripts/nuclei_assay.py run images.csv results
```

The image supplies its own numpy and tifffile versions. Do not upgrade those in place to the
helper test versions. Native helper-only verification uses Python 3.12, `numpy==2.5.3`, and
`tifffile==2026.9.20` in a separate environment. Full native CellProfiler has additional Java,
GUI/build, and database client dependencies; follow the
[official installation instructions](https://github.com/CellProfiler/CellProfiler/wiki).
The current 4.2.8.1 PyPI metadata still pins `mysqlclient==1.4.6`, `scipy==1.9.0`,
`scikit-image==0.18.3`, `scikit-learn<1`, and `tifffile<2022.4.22`. A previous development
installation stopped on missing `mysql_config`; a fresh native installation was not attempted
in this review. The container command above is an execution pattern requiring an available
Docker engine and image; it was not rerun during this review.

## Input and output contracts

The released LoadData implementation accepts `URL_DNA` with `file:` URLs and
`Metadata_Sample/Plate/Well/Site`. `--data-file` overrides its configured CSV. It infers metadata
types across each column; quote marks in CSV do not force strings. Prefix sample and plate
identifiers with text when leading zeros matter. Use canonical site numbers and well names
such as `A01` to keep acquisition identities unambiguous.

The starter sets LoadData `Rescale intensities?` to `No`, which ignores camera-range metadata
and divides unsigned image pixels by their integer storage maximum. It does not preserve raw
integer intensity units in measurements. The TIFF helper rejects additional pages/series and
pyramids so a reader cannot silently choose the first image or level.

ExportToSpreadsheet's single-object CSV uses `ImageNumber` and `ObjectNumber` as keys; object
numbers run from 1 to `Count_Nuclei` within each image. The helper rejects duplicate keys,
orphan rows, missing object indices, fractional counts, nonfinite mean/integrated intensities,
and nonpositive/nonfinite areas. An image with zero nuclei remains present, with `null` means
and an explicit warning. Shape area is in square pixels, not square micrometres.

In the released CLI, `--done-file` records the pipeline's `Exit_Status`. Without that switch,
some non-complete statuses can still produce exit code zero. The helper therefore requests
the marker and requires `Complete`, then separately checks `ModuleError_*` and table contents.
`status: complete` means these execution/consistency checks passed; it does not assert that
segmentation is biologically accurate. The log and `assay_qc.json` remain available after a
process or output-validation failure. If the helper itself is killed, a `running` report is
incomplete evidence and must not be treated as success.

## Scientific checks

- Establish a manually counted set of fields across the acquisition range. Assess precision,
  missed objects, splits, and merges, not only mean count correlation.
- Compare nuclear area distributions with plausible biology. Inflated area may indicate merges
  or illumination background; many tiny objects may be debris or threshold noise.
- Check boundary policy. This starter excludes objects touching an image edge; overlapping
  acquisition tiles need a deliberate deduplication/edge policy.
- Flat-field correction uses a separately estimated illumination function. Do not independently
  normalize each image to its own minimum/maximum before intensity comparisons.
- Review out-of-focus and saturated fields. A >1% saturation warning is a triage heuristic,
  not a universal acceptance limit; set acceptance criteria for the assay.
- Preserve field identities and experimental replicates when aggregating cells to wells.

## Verification scope

The original development record reports that the asset was serialized by CellProfiler 4.2.8
module APIs and executed headlessly on a synthetic
uint16 TIFF with three separated disks (radius 10 pixels; intensities 20,000, 30,000, 40,000).
The regression asserts three nuclei, mean normalized intensity near 30,000/65,535, and a saved
outline PNG. That engine run was **not repeated** in the 2026-09-30 review. Current tests execute
manifest/TIFF handling and CSV QC with synthetic data, and simulate the subprocess contract to
test completion and failure reporting. These tests do not execute CellProfiler segmentation.

To repeat the real integration test in a repository checkout, set
`CELLPROFILER_TEST_EXECUTABLE` to an installed `cellprofiler` executable or a launcher that forwards
all arguments and mounts the paths unchanged. Run only `tests/cellprofiler/` in that pytest
process. The test is explicitly skipped without that executable; helper tests still run.

## Review sources

- [Official application release](https://cellprofiler.org/releases),
  [4.2.8.1 PyPI metadata](https://pypi.org/pypi/cellprofiler/4.2.8.1/json), and
  [official container tags](https://hub.docker.com/r/cellprofiler/cellprofiler/tags).
- [Tagged CLI source](https://github.com/CellProfiler/CellProfiler/blob/v4.2.8/cellprofiler/__main__.py):
  command flags and completion semantics; compared with the current PyPI wheel.
- [Tagged LoadData source](https://github.com/CellProfiler/core/blob/v4.2.8/cellprofiler_core/modules/loaddata.py):
  URL input, type inference, and storage-range rescaling.
- [File-processing manual](https://cellprofiler-manual.s3.amazonaws.com/CellProfiler-4.2.8/modules/fileprocessing.html):
  CSV and single-object exports, metadata, and 2D LoadData restriction.
- [Measurement manual](https://cellprofiler-manual.s3.amazonaws.com/CellProfiler-4.2.8/modules/measurement.html)
  and [object-processing manual](https://cellprofiler-manual.s3.amazonaws.com/CellProfiler-4.2.8/modules/objectprocessing.html):
  mean versus integrated intensity, pixel area, and nuclear identification assumptions.
- [tifffile documentation](https://www.cgohlke.com/docs/tifffile/): TIFF pages, series, levels,
  `TiffFile`, and array reading.
