# Runtime and assay verification

## CellProfiler 4.2.8

The pipeline targets the full **CellProfiler 4.2.8**, not merely `cellprofiler-core`:
IdentifyPrimaryObjects and measurement modules live in the full package. The official image
`cellprofiler/cellprofiler:4.2.8` is a Linux amd64 environment. Its tested digest is
`sha256:fec440caa2b44edf80f9bd440a3d8c6b214d72437332ad2586a32d79e2eae2a4`.
Apple Silicon runs that image with `--platform linux/amd64` under emulation.

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

The image already supplies numpy and tifffile. Native helper-only installation can use a
separate environment with `numpy` and `tifffile`. Full native CellProfiler has additional Java,
GUI/build, and database client dependencies; follow the
[official installation instructions](https://github.com/CellProfiler/CellProfiler/wiki).
A local isolated PyPI installation attempted during development stopped on
`mysqlclient==1.4.6` because `mysql_config` was absent; the container provides the tested runtime.

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

The asset was serialized by CellProfiler 4.2.8 module APIs and executed headlessly on a synthetic
uint16 TIFF with three separated disks (radius 10 pixels; intensities 20,000, 30,000, 40,000).
The regression asserts three nuclei, mean normalized intensity near 30,000/65,535, and a saved
outline PNG. Unit tests reject constant/RGB/float images, duplicate acquisition fields,
nonfinite measurements, and mismatched output samples.

To repeat the real integration test in a repository checkout, set
`CELLPROFILER_TEST_EXECUTABLE` to an installed `cellprofiler` executable or a launcher that forwards
all arguments and mounts the paths unchanged. Run only `tests/cellprofiler/` in that pytest
process. The test is explicitly skipped without that executable; helper tests still run.
