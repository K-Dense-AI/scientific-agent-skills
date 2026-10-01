# Microscopy and Scientific Imaging Formats

**Reviewed:** 2026-09-30
**Executable scope:** Metadata-only PNG/JPEG and TIFF/OME-TIFF inspection.
Pixels are never decoded by bundled tools.

## Exact capability matrix

| Format | Bundled inspection | Depth |
|---|---|---|
| `.png`, `.jpg`, `.jpeg` | Optional, `pillow==12.3.0` | Width, height, mode, frame count, format, and metadata-entry count |
| `.tif`, `.tiff` | Optional, `tifffile==2026.9.20` | Bounded pages and generic series, shape/dtype, BigTIFF/OME flags |
| `.ome.tif`, `.ome.tiff` | Optional, `tifffile==2026.9.20` | Same structural metadata; OME-XML values are not emitted or semantically validated |
| ND2/CZI/LIF and other vendor microscopy | No | Reference-only vendor/Bio-Formats workflow |
| DICOM/NIfTI/MRC | No | Reference-only medical/neuro/EM workflow |
| SVS/NDPI and other whole-slide formats | No | Reference-only WSI workflow |
| OME-Zarr/Zarr | No | Directory/store formats are outside the regular-file boundary |

No bundled script supports “all Pillow formats” or “all tifffile formats.”
Only the registered suffixes above are accepted. Unknown formats fail closed.

## Metadata-only safety model

Images and metadata can contain protected health information, accession
numbers, specimen labels, GPS/EXIF fields, user comments, XML, external
references, or adversarial text. The inspectors:

- accept only bounded local regular files inside `--root`;
- reject URLs, traversal, symlinks, special files, and suffix/signature
  mismatches;
- reject declared element counts above 100,000,000 and excessive TIFF
  pages/series;
- make Pillow decompression-bomb warnings fatal;
- never call `load()`, `asarray()`, `imread()`, image codecs, or thumbnail
  generation;
- report metadata counts and structural facts, not EXIF/tag/OME-XML values;
- never follow metadata links or embedded instructions; and
- do not claim full corruption, codec, or semantic validation.

Metadata-only access reduces decompression risk but is not a sandbox. Keep
libraries pinned and inspect untrusted images in an isolated, resource-limited
process when risk warrants it.

## PNG and JPEG

Pillow's `Image.open()` is lazy: it identifies the container and reads enough
header information to construct an image object. The bundled inspector closes
the object without decoding pixels.

### Interpret carefully

- PNG may be palette, grayscale, RGB/RGBA, 8/16-bit, multi-frame/APNG, or carry
  textual/profile chunks.
- JPEG is lossy and normally unsuitable as a quantitative raw measurement
  source. Repeated saves change pixels.
- Width/height/mode do not establish bit-depth fidelity, calibration, channel
  identity, linearity, saturation, or acquisition settings.
- Metadata may be stale after image processing.

For quantitative EDA, retain the acquisition-native image and compare
container metadata to instrument records. Do not compute intensity statistics
from display/export JPEGs.

## TIFF

TIFF is a flexible container, not a single pixel organization. It can contain
multiple pages, tiles/strips, pyramids, SubIFDs, private/vendor tags, external
storage, and many compression schemes. A `.tif` suffix alone does not imply
microscopy or OME conformance.

The bundled tifffile inspector reports:

- main-page and generic-series counts, bounded to 1,000 and 128;
- per-series shape, axes, element count, and dtype kind/item size;
- classic TIFF versus BigTIFF; and
- whether tifffile identifies OME metadata.

The current public `tiff.series(kind="generic")` API groups local pages without
reconstructing OME/vendor dimensions or discovering companion files. The pinned
`_multifile=False` argument adds an upstream internal safeguard; recheck it when
upgrading tifffile. Shape and axes describe generic page groups, not validated
OME XYZCT dimensions. Main pages plus declared immediate SubIFDs share the
1,000-entry limit. Nested pyramids are not exhaustively validated.

The reader necessarily parses structural tag values internally but never emits
raw tags or OME-XML. It does not decode compressed segments, validate every IFD,
open companion storage, or establish scientifically correct axis semantics.

## OME-TIFF

OME-TIFF stores one or more image planes in TIFF and embeds an OME-XML metadata
block. Multi-file datasets can use UUID-based references. The OME specification
is richer than a filename convention.

Before quantitative analysis, use OME-aware validation to confirm:

- OME-XML schema/version and UUID/file references;
- dimension order and sizes for X/Y/Z/C/T;
- `TiffData` plane-to-IFD mapping;
- physical pixel sizes and units;
- channel names, wavelengths, detector/objective settings, and acquisition
  times; and
- whether pyramids, labels, ROIs, or companion files are expected.

The bundled inspector deliberately does not emit OME-XML because it may contain
identifiers or prompt-like text. `is_ome_tiff=true` is not a validation result.

## Reference-only vendor microscopy

ND2, CZI, LIF, VSI, proprietary whole-slide files, and similar formats require
a version-aware vendor reader or Bio-Formats. Capabilities vary by library,
native dependency, file generation version, and series type. Do not choose a
reader only from a suffix.

Workflow:

1. Preserve the original and capture instrument/software versions.
2. Open a small approved file with a pinned reader in an isolated environment.
3. Inventory scenes/series and XYZCT axes before loading pixels.
4. Compare dimensions, calibration, channels, stage positions, and timestamps
   to acquisition records.
5. Bound tile/plane reads and never eagerly materialize a whole slide or 5-D
   image.
6. Convert a derived copy to OME-TIFF/OME-Zarr only with provenance and
   round-trip checks.

## Reference-only medical and whole-slide imaging

### DICOM

DICOM is a clinical standard with extensive metadata and possible PHI. A
single `.dcm` may be one instance in a study/series. Use institutional policy,
approved de-identification, and DICOM-aware tools. Do not print patient, study,
series, accession, date, burned-in annotation, or private-tag values.

### NIfTI

Validate dimensions, voxel sizes, affine/qform/sform, units, orientation,
scaling, and time axis with neuroimaging tooling. `.nii.gz` is compressed and
is not decompressed by bundled scripts.

### Whole-slide imaging

SVS, NDPI, and related formats are large tiled pyramids and may contain label or
macro images with identifiers. Use OpenSlide/tiffslide or a validated vendor
reader, inspect associated images, and sample bounded tiles. Split by patient
before tile generation to prevent leakage.

## Imaging EDA rigor

1. Define the independent unit: pixel, object, field, well, section, specimen,
   subject, or acquisition session.
2. Separate biological from technical replication and avoid treating tiles or
   cells from one specimen as independent subjects.
3. Record calibration, units, bit depth, detector response, exposure, gain,
   illumination, objective, channel, Z/T spacing, and processing history.
4. Audit missing/corrupt planes, saturation, clipping, background, focus,
   illumination, registration, segmentation, and batch/site effects.
5. Preserve raw pixels. Do not automatically rescale, denoise, background
   subtract, discard fields, or remove objects.
6. Fit normalization, segmentation thresholds, feature selection, and models
   on training specimens only; split subjects/specimens before tiling.
7. Report object/field/specimen-level sensitivity, not only pooled pixels.
8. Do not infer biological mechanism, diagnosis, or treatment effect from
   descriptive image patterns.

## Pinned optional snapshot

```bash
uv pip install \
  "pillow==12.3.0" \
  "tifffile==2026.9.20" \
  "numpy==2.5.3"
```

Pillow 12.3.0 was released 2026-07-01 and requires Python 3.10+.
tifffile 2026.9.20 was released 2026-09-21 and requires Python 3.12+.
Imagecodecs is not installed or invoked by the metadata-only inspector.

## Authoritative sources

Current parser APIs and format guidance reviewed 2026-09-30. Historical
methodology citations are retained as source context.

- Pillow, [`Image` module and decompression-bomb protection](https://pillow.readthedocs.io/en/stable/reference/Image.html).
- [Pillow PyPI](https://pypi.org/project/pillow/), version 12.3.0,
  released 2026-07-01.
- tifffile, [current API and generic-series examples](https://www.cgohlke.com/docs/tifffile/).
- [tifffile PyPI](https://pypi.org/project/tifffile/), version 2026.9.20,
  released 2026-09-21; upstream notes that codecs are required for decoding
  compressed segments.
- Library of Congress, [TIFF, Revision 6.0 format description](https://www.loc.gov/preservation/digital/formats/fdd/fdd000022.shtml)
  and the ITU-hosted [TIFF 6.0 specification](https://www.itu.int/itudoc/itu-t/com16/tiff-fx/docs/tiff6.pdf).
- OME, [OME-TIFF specification](https://ome-model.readthedocs.io/en/stable/ome-tiff/specification.html).
- OME, [OME Data Model and File Formats](https://ome-model.readthedocs.io/en/stable/).
- DICOM Standards Committee, [current DICOM standard](https://www.dicomstandard.org/current).
- OpenSlide, [supported formats and Python API](https://openslide.org/api/python/).
- National Academies (2019), [reproducibility and provenance](https://doi.org/10.17226/25303).
