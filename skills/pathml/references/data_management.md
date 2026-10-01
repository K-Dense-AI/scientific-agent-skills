# Data management, h5path, manifests, datasets, and provenance

This reference targets **PathML 3.0.8 stable** and a local, de-identified research
workflow.

## Data boundaries

Separate four classes of data:

1. **Source slides** — immutable, access-controlled originals.
2. **Linkage data** — direct identifiers and the pseudonym mapping, held outside
   the analysis workspace by an authorized custodian.
3. **Analysis data** — pseudonymous manifests, tiles, masks, counts, graphs, and
   features.
4. **Reports/models** — potentially identifying derived artifacts that still
   require governance.

Do not assume derived images or embeddings are anonymous. Rare morphology,
scanner metadata, dates, or cohort combinations can re-identify a participant.
Apply the minimum-necessary principle and institutional retention policy.

## Manifest first

Use one row per slide. Recommended columns:

```text
slide_id,patient_id,specimen_id,path,split,stain,backend,site,scanner
```

Rules:

- IDs are pseudonyms, not MRNs, accessions, initials, dates, or names.
- `slide_id` is unique.
- one `patient_id` maps to exactly one split;
- one slide path maps to one slide ID;
- paths are local, relative to a declared root where possible;
- URLs and symlinks are rejected;
- split values are a fixed allowlist such as `train`, `validation`, `test`;
- serial sections, rescans, and multiple blocks from one patient remain together.

Validate before PathML:

```bash
python scripts/slide_manifest.py validate \
  --manifest metadata/manifest.csv \
  --root .
```

The validator checks strict CSV structure, duplicate IDs/paths, missing local
files, unsafe paths, supported suffixes, and patient/slide leakage. It does not
upload data or inspect arbitrary clinical fields.
If the `split` column is present, every row must supply it. Without that column,
the report explicitly leaves patient split isolation unchecked.

## h5path format

PathML processes slides into an HDF5-based `.h5path` file. Stable documentation
describes:

```text
root/
├── fields/
│   ├── labels/          # slide-level attributes
│   └── slide_type/      # stain/platform flags
├── masks/               # slide-level masks
├── counts/              # AnnData-like counts storage
└── tiles/
    ├── attributes       # tile_shape, tile_stride
    └── "(i, j)"/
        ├── array
        ├── masks/
        ├── labels/
        └── attributes   # coords, name
```

Write and reopen through public APIs:

```python
from pathml.core import SlideData

slide.write("derived/slide-001.h5path")
reopened = SlideData("derived/slide-001.h5path")
```

There is no stable `to_hdf5()`, `from_hdf5()`, or
`load_tiles_from_hdf5()` API. `SlideDataset.write(directory, filenames=None)`
calls each slide's `write()`.

Released `h5pathManager.add_tile()` explicitly casts both tile images and tile
masks to `float16`. Integers through 2048 are exact, but 2049 rounds to 2048 and
large values can overflow beyond 65504. Thus distinct instance IDs can merge;
intensity values can also lose precision. This is a storage limitation, even
when Bio-Formats read with `normalize=False`.

Preserve authoritative quantitative images and integer instance maps in a
separate lossless, typed format. Check actual label identity and dtype after a
small h5path round trip before downstream counting. Binary masks are not subject
to the same instance-ID loss. Record tolerances for float measurements, but
require exact equality for categorical labels.

## h5path trust boundary

Treat `.h5path` as a structured binary input, not harmless data:

- HDF5 parsers have a large attack surface; open third-party files in isolation.
- PathML 3.0.8 `TileDataset` and core h5path/tile code dynamically interpret the
  stored `tile_shape` attribute as a Python expression. Never open an untrusted
  `.h5path`, including through `SlideData`.
- Labels can contain sensitive values. Do not copy direct identifiers into HDF5.
- A malformed file can request large allocations. Check file size and schema
  before loading.
- Do not edit HDF5 concurrently from multiple processes unless the access pattern
  is explicitly designed and tested.

Use a sidecar JSON manifest for provenance rather than relying on arbitrary HDF5
labels. Keep the JSON strict, bounded, pseudonymous, and versioned.

## PyTorch tile dataset

The canonical stable import is:

```python
from pathml.datasets import TileDataset
from torch.utils.data import DataLoader

tiles = TileDataset("derived/slide-001.h5path")
loader = DataLoader(
    tiles,
    batch_size=8,
    shuffle=False,
    num_workers=0,
)
```

Each item is:

```text
(tile_image, tile_masks, tile_labels, slide_labels)
```

Shapes:

- RGB/multichannel 3-D input becomes `(C, H, W)`.
- 5-D PathML input `(i, j, z, c, t)` becomes `(T, C, Z, W, H)` in stable
  source; verify axis semantics before use.
- masks are stacked as `(n_masks, tile_height, tile_width)` when present.
- values returned by the dataset are NumPy arrays; the PyTorch loader collates
  them to tensors. Missing masks are `None`, which default collation cannot
  handle; use a custom `collate_fn` for missing masks or nonstandard labels.

`TileDataset` does not return coordinates explicitly. Keep a parallel mapping
from sample index to its stored tile key/coords (HDF5 iteration is not a numeric
row/column sort), or include validated coordinate metadata in a custom dataset.

Do not assume mask dictionary order carries semantics. Persist ordered mask names
in a separate schema and assert them when loading.

`pathml.ml.TileDataset` is also exported in 3.0.8, but
`pathml.datasets.TileDataset` is the documented dataset API.

## SlideDataset

`SlideDataset(slides)` accepts a list of already constructed `SlideData` objects:

```python
from pathml.core import HESlide, SlideDataset

slides = [
    HESlide("data/slide-001.svs", backend="openslide"),
    HESlide("data/slide-002.svs", backend="openslide"),
]
cohort = SlideDataset(slides)
cohort.run(pipeline, distributed=False, tile_size=512, level=0)
cohort.write("derived")
```

It does not accept a glob/path list plus tiling arguments as a constructor.
Preserve a deterministic manifest order and map output filenames explicitly.

## Public data modules

Stable `pathml.datasets` exports:

```python
from pathml.datasets import DeepFocusDataModule, PanNukeDataModule
```

### PanNuke

```python
pannuke = PanNukeDataModule(
    data_dir="approved_data/pannuke",
    download=False,
    shuffle=True,
    nucleus_type_labels=True,
    split=1,
    batch_size=8,
    hovernet_preprocess=True,
)
```

- 7,901 256-pixel patches, 19 tissue types, five nucleus categories plus
  background.
- `download=False` is the safe default.
- `download=True` downloads three ZIPs from
  `https://warwick.ac.uk/fac/cross_fac/tia/data/pannuke/fold_{1,2,3}.zip` and
  extracts them. These are binary GETs, without authentication or pagination.
- `split` must be 1, 2, 3, or `None`; each integer rotates the three published
  folds across train/validation/test.
- `split=None` exposes the whole dataset; do not use it for performance
  estimation.

Published folds are not a substitute for verifying patient/source-slide
independence for the intended claim.

### DeepFocus

```python
deepfocus = DeepFocusDataModule(
    data_dir="approved_data/deepfocus",
    download=False,
    shuffle=True,
    batch_size=8,
)
```

- focus classification patches derived from four slides/patients and four stains;
- `download=True` GETs
  `https://zenodo.org/record/1134848/files/outoffocus2017_patches5Classification.h5`
  without authentication/pagination;
- the integrity method checks a fixed MD5 before reusing a local file, but the
  download method does not perform a second post-download check. Verify the
  completed file independently before use.

MD5 here is an upstream integrity check, not a modern provenance guarantee.
Record a SHA-256 and dataset license/source separately.

PathML 3.0.8 does **not** export `TCGADataModule`. Use a separately governed data
acquisition process for TCGA/GDC and document its API/version/consent terms.

## Download consent

Before changing any `download` flag to `True`, tell the user:

- exact host and expected dataset;
- approximate transfer and expanded sizes (review-time HEAD responses for the
  three PanNuke ZIPs total 2,077,087,715 bytes; processing/expansion needs much
  more disk, with upstream docs estimating ~37.33 GB; the DeepFocus HDF5 is
  10,027,826,144 bytes);
- destination and available disk;
- dataset license/terms and citation;
- whether the environment logs outbound IP/account metadata; and
- that no local slide or clinical data will be uploaded.

Require explicit opt-in. Never place downloaded archives inside the repository.

Review-time HEAD checks reached all four source URLs; DeepFocus redirected from
`/record/` to `/records/`. No bodies were downloaded, so this establishes endpoint
availability, not content integrity, license acceptance, or working extraction.
The common download helper skips any existing file by name, including a partial
one; independently verify size/checksum before treating such a file as complete.

## Graph datasets and unsafe `.pt` files

`pathml.datasets.EntityDataset` assembles cell graphs, tissue graphs, and
assignment matrices. Stable source opens `.pt` files using PyTorch object
deserialization with unrestricted object loading.

Consequences:

- only load artifacts created by the trusted project;
- never load an emailed/downloaded `.pt` file merely to inspect it;
- verify SHA-256, producer, code revision, PyTorch/PyG versions, and schema;
- prefer non-executable interchange formats for exchange;
- run legacy artifacts in a disposable, network-disabled environment if review is
  unavoidable.

The bundled inference planner and graph validator never load `.pt`, `.pth`,
`.ckpt`, pickle, ONNX, or other model/graph binaries.

## Split design and leakage

Create the split column once, before tiling:

```text
patient → specimen/block → slide/rescan/serial section → region → tile
```

Everything below a patient follows the patient's split unless the scientific
design explicitly requires a stricter grouping.

Common leakage paths:

- overlapping tiles from one slide in different splits;
- serial sections or rescans assigned separately;
- stain reference fitted on all slides;
- QC threshold chosen after viewing test failures;
- normalization/scaling fit before split;
- graph neighborhoods crossing a split boundary;
- duplicated public patches;
- institution/scanner confounding;
- selecting a checkpoint on the test metric.

The manifest validator reports patient and slide leakage, but it cannot discover
unknown biological relatedness. Document grouping assumptions.

## Provenance sidecar

Recommended strict JSON fields:

```json
{
  "schema_version": "1.0",
  "pathml_version": "3.0.8",
  "source_sha256": "hex-digest",
  "slide_id": "slide-001",
  "patient_id": "patient-001",
  "split": "train",
  "backend": "openslide",
  "level": 0,
  "downsample": 1.0,
  "mpp_x": null,
  "mpp_y": null,
  "tile_size_ij": [512, 512],
  "tile_stride_ij": [512, 512],
  "tile_pad": false,
  "pipeline_id": "he-v1",
  "code_revision": "project-commit",
  "created_utc": "RFC3339 timestamp"
}
```

Do not put a direct identifier in these fields. Add:

- ordered transform parameters and fitted stain arrays;
- mask/label schema;
- QC counts and exclusion reasons;
- dependency lock hash;
- model artifact SHA-256 and license;
- random seed manifest;
- coordinate units and conversion;
- output hashes and software/hardware details.

Use SHA-256 for provenance:

```python
import hashlib
from pathlib import Path

def sha256_file(path: Path, chunk_bytes: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_bytes), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

Hash only authorized local files and expect full-slide hashing to be I/O-heavy.
Do not print paths containing identifiers.

## Storage and lifecycle checklist

- Estimate raw, temporary, `.h5path`, mask, count, graph, and model storage.
- Write to a same-filesystem temporary destination, validate, then atomically
  rename where possible.
- Do not overwrite source slides.
- Use private permissions and encrypted storage/backups.
- Verify output counts, shapes, dtypes, coordinates, and hashes.
- Record partial failures and retry policy.
- Test disaster recovery and retention/deletion.
- Do not commit slide data, model binaries, linkage files, or manifests with PHI.

## Sources and further reading

API baseline reviewed 2026-10-01 using the released wheel/tag; hosted docs may lag.

- Stable h5path guide:
  https://pathml.readthedocs.io/en/stable/h5path.html
- Stable datasets guide:
  https://pathml.readthedocs.io/en/stable/datasets.html
- Stable datasets API:
  https://pathml.readthedocs.io/en/stable/api_datasets_reference.html
- Stable `TileDataset`/`EntityDataset` source:
  https://github.com/Dana-Farber-AIOS/pathml/blob/v3.0.8/pathml/datasets/datasets.py
- Stable PanNuke source:
  https://github.com/Dana-Farber-AIOS/pathml/blob/v3.0.8/pathml/datasets/pannuke.py
- Stable DeepFocus source:
  https://github.com/Dana-Farber-AIOS/pathml/blob/v3.0.8/pathml/datasets/deepfocus.py
- PanNuke extension paper: https://arxiv.org/abs/2003.10778
- DeepFocus paper: https://doi.org/10.1371/journal.pone.0205387
