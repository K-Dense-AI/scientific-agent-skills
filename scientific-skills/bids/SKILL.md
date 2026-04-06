---
name: bids
description: >
  Use this skill when working with Brain Imaging Data Structure (BIDS) datasets:
  organizing neuroimaging data, querying BIDS layouts, validating compliance,
  converting DICOM to BIDS, writing metadata sidecars, or creating BIDS derivatives.
license: https://creativecommons.org/licenses/by/4.0/
metadata:
    skill-author: Yaroslav Halchenko
---

# Brain Imaging Data Structure (BIDS)

## Overview

The Brain Imaging Data Structure (BIDS) is a community standard for organizing and describing neuroimaging datasets. It defines a consistent file naming convention, directory hierarchy, and metadata schema so that datasets are immediately understandable by humans and software tools alike. BIDS is governed by the BIDS Specification (currently v1.10.x) and is maintained by the community via the BIDS-Standard GitHub organization.

BIDS originated for MRI but now covers EEG, MEG, iEEG, PET, microscopy, NIRS, motion capture, and other modalities. Adoption is required or strongly encouraged by major data repositories (OpenNeuro, DANDI, LORIS), most neuroimaging journals (NeuroImage, Human Brain Mapping), and funding agencies (NIH, ERC).

The Python ecosystem for BIDS centers on **PyBIDS** (`pybids`) for querying and indexing BIDS datasets, and the **bids-validator** (Deno-based, available as PyPI package `bids-validator-deno` or via Deno directly) for compliance checking. Conversion from DICOM is typically done with **HeuDiConv**, **dcm2bids**, or **BIDScoin**.

## When to Use This Skill

Apply this skill when:
- Organizing raw neuroimaging data into BIDS-compliant directory structures
- Querying an existing BIDS dataset to find specific files by subject, session, task, run, or modality
- Validating a dataset against the BIDS specification before sharing or submission
- Converting DICOM data from scanners into BIDS format
- Writing or editing JSON sidecar metadata files
- Creating BIDS-compliant derivatives (preprocessed data, analysis outputs)
- Setting up a `dataset_description.json` for a new dataset
- Working with BIDS entities (subject, session, task, acquisition, run, etc.)
- Configuring `.bidsignore` to exclude files from validation
- Preparing data for upload to OpenNeuro, DANDI, or other BIDS-aware repositories

## Installation

```bash
# Core BIDS querying library
uv pip install pybids

# BIDS validator (Deno-based, installed via PyPI wrapper)
uv pip install bids-validator-deno
# Alternative: install directly via Deno
# deno install -g -A npm:bids-validator

# DICOM-to-BIDS converters (install as needed)
uv pip install heudiconv       # HeuDiConv - heuristic-based DICOM conversion
uv pip install dcm2bids        # dcm2bids - config-file-based conversion
# BIDScoin: uv pip install bidscoin

# Useful companions
uv pip install nibabel          # NIfTI/other neuroimaging file I/O
uv pip install pydicom          # DICOM file reading (used by converters)
```

## Core Workflows

### 1. BIDS Directory Structure

A minimal BIDS dataset follows this layout:

```
my_dataset/
  dataset_description.json      # Required: name, BIDSVersion, etc.
  participants.tsv              # Recommended: subject-level phenotypic data
  participants.json             # Recommended: column descriptions
  README                        # Recommended: dataset documentation
  CHANGES                       # Recommended: version history
  .bidsignore                   # Optional: patterns to exclude from validation
  sub-01/
    anat/
      sub-01_T1w.nii.gz
      sub-01_T1w.json           # Sidecar metadata
    func/
      sub-01_task-rest_bold.nii.gz
      sub-01_task-rest_bold.json
      sub-01_task-rest_events.tsv     # Event timing for task fMRI
      sub-01_task-rest_events.json
    dwi/
      sub-01_dwi.nii.gz
      sub-01_dwi.json
      sub-01_dwi.bvec
      sub-01_dwi.bval
    fmap/
      sub-01_phasediff.nii.gz
      sub-01_phasediff.json
      sub-01_magnitude1.nii.gz
    perf/
      sub-01_asl.nii.gz
      sub-01_asl.json
  sub-01/
    ses-pre/
      anat/
        sub-01_ses-pre_T1w.nii.gz
      func/
        sub-01_ses-pre_task-nback_bold.nii.gz
    ses-post/
      ...
```

**Key points:**
- Every NIfTI file should have a corresponding `.json` sidecar
- File names encode entities: `sub-<label>[_ses-<label>][_task-<label>][_acq-<label>][_run-<index>]_<suffix>.<extension>`
- Entity order in filenames is fixed by the specification
- Only `dataset_description.json` is strictly required at the root level

### 2. Creating dataset_description.json

```python
import json

dataset_description = {
    "Name": "My Neuroimaging Study",
    "BIDSVersion": "1.10.0",
    "DatasetType": "raw",
    "License": "CC0",
    "Authors": ["First Author", "Second Author"],
    "Acknowledgements": "Funded by NIH R01-MH123456",
    "HowToAcknowledge": "Please cite: Author et al. (2025) Journal Name.",
    "Funding": ["NIH R01-MH123456", "NSF BCS-7654321"],
    "ReferencesAndLinks": ["https://doi.org/10.xxxx/xxxxx"],
    "DatasetDOI": "10.18112/openneuro.ds000001.v1.0.0",
    "GeneratedBy": [
        {
            "Name": "HeuDiConv",
            "Version": "1.3.1",
            "CodeURL": "https://github.com/nipy/heudiconv"
        }
    ]
}

with open("dataset_description.json", "w") as f:
    json.dump(dataset_description, f, indent=4)
```

For **derivatives**, set `"DatasetType": "derivative"` and add `"GeneratedBy"` listing the pipeline:

```python
deriv_description = {
    "Name": "fMRIPrep - fMRI PREProcessing",
    "BIDSVersion": "1.10.0",
    "DatasetType": "derivative",
    "GeneratedBy": [
        {
            "Name": "fMRIPrep",
            "Version": "24.1.0",
            "CodeURL": "https://github.com/nipreps/fmriprep"
        }
    ]
}
```

### 3. Querying BIDS Datasets with PyBIDS

```python
from bids import BIDSLayout

# Index a BIDS dataset (validates structure on load)
layout = BIDSLayout("/path/to/bids_dataset")

# Basic queries
subjects = layout.get_subjects()          # ['01', '02', '03', ...]
sessions = layout.get_sessions()          # ['pre', 'post'] or []
tasks = layout.get_tasks()                # ['rest', 'nback']
runs = layout.get_runs()                  # [1, 2] or []

# Find specific files
bold_files = layout.get(
    suffix="bold",
    extension=".nii.gz",
    return_type="filename"
)

# Filter by subject, task, session
nback_sub01 = layout.get(
    subject="01",
    task="nback",
    suffix="bold",
    extension=".nii.gz",
    return_type="filename"
)

# Get metadata from JSON sidecars (automatic inheritance)
metadata = layout.get_metadata("/path/to/sub-01/func/sub-01_task-rest_bold.nii.gz")
tr = metadata["RepetitionTime"]

# Get all entities for a file
entities = layout.get_entities()

# Build a path from entities using BIDSLayout
bids_file = layout.get(subject="01", suffix="T1w", extension=".nii.gz")[0]
print(bids_file.path)
print(bids_file.get_entities())
```

**Key points:**
- `BIDSLayout` indexes the entire dataset on initialization; for large datasets use `database_path` to cache the index
- Metadata inheritance: a JSON sidecar at a higher level (e.g., root or subject) is inherited by all files below unless overridden
- Use `return_type="filename"` for paths, `return_type="object"` (default) for `BIDSFile` objects

### 4. Validating BIDS Datasets

#### Using bids-validator via PyPI (recommended)

The `bids-validator-deno` PyPI package bundles the Deno-based validator as a standalone CLI:

```bash
# Install
uv pip install bids-validator-deno

# Validate a dataset
bids-validator /path/to/bids_dataset

# Ignore specific warnings/errors
bids-validator /path/to/bids_dataset --ignoreNiftiHeaders --ignoreSubjectConsistency
```

#### Using bids-validator via Deno directly

If Deno is already available, you can install or run the validator without PyPI:

```bash
# Install globally via Deno
deno install -g -A npm:bids-validator

# Or run without installing
deno run -A npm:bids-validator /path/to/bids_dataset
```

#### Legacy Node.js validator

The older Node.js-based validator (`npm install -g bids-validator`) is deprecated in favor of the Deno-based version. The Deno version is the reference implementation for BIDS Specification v1.9+.

#### Using .bidsignore

Create `.bidsignore` at the dataset root to exclude files from validation (gitignore syntax):

```
# Exclude sourcedata and extra files
sourcedata/
extra_data/
*.log
*_sbref.nii.gz
**/.DS_Store
```

### 5. BIDS Entities and File Naming

The authoritative, machine-readable source of truth for entities, their ordering, allowed suffixes, and all filename rules is the **BIDS Schema** — a structured YAML/JSON representation of the specification. A JSON export is shipped with this skill at `references/bids_schema.json`. The schema is defined in the [bids-specification `src/schema/`](https://github.com/bids-standard/bids-specification/tree/master/src/schema) directory and published at https://bids-specification.readthedocs.io/en/stable/schema.json. BEP-specific schema previews are available at https://github.com/bids-standard/bids-schema/tree/main/BEPs.

Run `scripts/update_schema.py` to refresh the schema and BEPs list from upstream (no dependencies beyond stdlib).

The tables below are a convenient summary; when in doubt, consult the schema.

BIDS filenames are built from ordered key-value entity pairs:

| Entity | Key | Example | Required for |
|--------|-----|---------|--------------|
| Subject | `sub-` | `sub-01` | All files |
| Session | `ses-` | `ses-pre` | Multi-session studies |
| Task | `task-` | `task-rest` | func (bold, cbv, phase), eeg, meg |
| Acquisition | `acq-` | `acq-highres` | Distinguishing acquisition parameters |
| Contrast enhancing agent | `ce-` | `ce-gadolinium` | Contrast-enhanced images |
| Reconstruction | `rec-` | `rec-magnitude` | Reconstruction variants |
| Direction | `dir-` | `dir-AP` | Fieldmaps, DWI, phase-encoding |
| Run | `run-` | `run-01` | Multiple identical acquisitions |
| Echo | `echo-` | `echo-1` | Multi-echo sequences |
| Part | `part-` | `part-mag` | Magnitude/phase splits |
| Space | `space-` | `space-MNI152NLin2009cAsym` | Derivatives in template space |
| Description | `desc-` | `desc-preproc` | Derivatives only |

**Entity ordering in filenames** is fixed by the spec (defined in `rules.entities` in `bids_schema.json`). See `references/bids_specification.md` for the complete numbered ordering table. A common subset:
`sub-<label>[_ses-<label>][_task-<label>][_acq-<label>][_ce-<label>][_rec-<label>][_dir-<label>][_run-<index>][_echo-<index>][_part-<label>][_space-<label>][_desc-<label>]_<suffix>.<extension>`

**Common suffixes by datatype:**

| Datatype | Suffixes |
|----------|----------|
| anat | `T1w`, `T2w`, `FLAIR`, `T2star`, `T1map`, `T2map`, `defacemask` |
| func | `bold`, `cbv`, `sbref`, `events`, `physio`, `stim` |
| dwi | `dwi`, `sbref` |
| fmap | `phasediff`, `phase1`, `phase2`, `magnitude1`, `magnitude2`, `fieldmap`, `epi` |
| perf | `asl`, `m0scan`, `aslcontext` |
| eeg | `eeg`, `channels`, `electrodes`, `events` |
| meg | `meg`, `channels`, `coordsystem`, `events` |
| ieeg | `ieeg`, `channels`, `electrodes`, `coordsystem`, `events` |
| pet | `pet`, `blood` |

### 6. DICOM to BIDS Conversion

#### HeuDiConv

HeuDiConv is the most flexible DICOM-to-BIDS converter. It supports three usage modes — from fully automatic to fully custom — and handles duplicates, provenance tracking, and sourcedata archiving out of the box.

**Mode 1: ReproIn (turnkey, recommended for new studies)**

If scanner protocol names follow the [ReproIn naming convention](https://github.com/repronim/reproin), conversion is fully automatic — no heuristic file to write:

```bash
# Turnkey conversion: HeuDiConv maps ReproIn protocol names to BIDS automatically
heudiconv --files dicom/001 -o /path/to/bids -f reproin --bids --minmeta
```

ReproIn protocol names encode BIDS entities directly:
- `anat-T1w` → `sub-XX/anat/sub-XX_T1w.nii.gz`
- `func-bold_task-rest` → `sub-XX/func/sub-XX_task-rest_bold.nii.gz`
- `dwi_dir-AP` → `sub-XX/dwi/sub-XX_dir-AP_dwi.nii.gz`
- `fmap_dir-PA` → `sub-XX/fmap/sub-XX_dir-PA_epi.nii.gz`

Session can be set once on the localizer (e.g., `anat-scout_ses-pre`) and ReproIn propagates it to all sequences in that Program. Subject ID is extracted from DICOM metadata. Duplicate runs are numbered automatically.

**Mode 2: Custom heuristic mapping into ReproIn (for existing data)**

If you already have data with non-ReproIn protocol names, you can write a thin heuristic that maps your names into ReproIn conventions, gaining all ReproIn benefits (automatic entity handling, duplicate management, etc.). See https://github.com/repronim/reproin/issues/18 for a HOWTO.

**Mode 3: Custom heuristic (full flexibility)**

For complex mappings, write a Python heuristic file:

```bash
# Step 1: Reconnaissance — discover DICOM series
heudiconv --files dicom/219/itbs/*/*.dcm -o Nifti/ -f convertall -s 219 -c none

# This creates .heudiconv/219/info/dicominfo.tsv — inspect it to understand
# what was acquired and map series to BIDS names.

# Step 2: Write a heuristic file (see references/conversion_tools.md)

# Step 3: Convert
heudiconv --files dicom/219/itbs/*/*.dcm -s 219 -ss itbs \
  -f Nifti/code/heuristic.py -c dcm2niix --bids --minmeta -o Nifti/
```

See `references/conversion_tools.md` for complete heuristic file examples.

**Key points:**
- HeuDiConv wraps `dcm2niix` for the actual DICOM-to-NIfTI conversion
- **`--minmeta`**: always use this flag to prevent excess DICOM metadata from overflowing JSON sidecars (can crash fMRIPrep/MRIQC)
- **Duplicate handling**: use `{item:03d}` in templates for auto-numbering when the same protocol is run multiple times; without it, later runs overwrite earlier ones
- **`.heudiconv/` directory**: created alongside output, stores provenance (heuristic used, dicominfo.tsv, conversion records). Keep it with your data for reproducibility
- **`sourcedata/`**: HeuDiConv archives original DICOMs as `.tgz` files under `sourcedata/` for reproducibility
- **`is_motion_corrected` filter**: use in heuristics to exclude scanner-generated MOCO series (e.g., `if not s.is_motion_corrected`)
- Both `--files` (explicit paths) and `-d` (template with `{subject}`, `{session}` placeholders) are supported for specifying DICOM input

#### dcm2bids (Configuration-file-based)

```bash
# Step 1: Generate helper output to inspect series
dcm2bids_helper -d /path/to/dicom

# Step 2: Create config file (dcm2bids_config.json)
# Step 3: Convert
dcm2bids -d /path/to/dicom -p 01 -c dcm2bids_config.json -o /path/to/bids_output
```

See `references/conversion_tools.md` for detailed configuration examples.

### 7. Metadata Sidecars

Every BIDS data file should have a JSON sidecar with acquisition parameters. Metadata fields follow the inheritance principle: a sidecar at a higher directory level applies to all matching files below.

**Inheritance example:**
```
my_dataset/
  task-rest_bold.json           # Applies to ALL rest BOLD files
  sub-01/
    func/
      sub-01_task-rest_bold.json  # Overrides/extends for sub-01 only
```

**Critical metadata fields by modality:**

For **func (BOLD)**:
```json
{
    "RepetitionTime": 2.0,
    "TaskName": "rest",
    "PhaseEncodingDirection": "j-",
    "TotalReadoutTime": 0.05,
    "SliceTiming": [0, 0.5, 1.0, 1.5],
    "EffectiveEchoSpacing": 0.00058,
    "EchoTime": 0.03
}
```

For **anat**:
```json
{
    "MagneticFieldStrength": 3,
    "Manufacturer": "Siemens",
    "ManufacturersModelName": "Prisma",
    "RepetitionTime": 2.3,
    "EchoTime": 0.00293,
    "FlipAngle": 8
}
```

For **DWI**:
```json
{
    "PhaseEncodingDirection": "j-",
    "TotalReadoutTime": 0.05,
    "EchoTime": 0.089,
    "RepetitionTime": 3.4,
    "MultipartID": "dwi_1"
}
```

**Key points:**
- `dcm2niix` auto-generates most sidecar fields from DICOM headers
- `RepetitionTime` and `TaskName` are required for BOLD
- `SliceTiming` is essential for slice-timing correction in fMRI preprocessing
- `PhaseEncodingDirection` and `TotalReadoutTime` (or `EffectiveEchoSpacing`) are needed for distortion correction
- See `references/metadata_fields.md` for comprehensive field reference

### 8. Events Files for Task fMRI

Task-based fMRI requires `_events.tsv` files:

```
onset	duration	trial_type	response_time
0.0	0.5	face	0.435
2.5	0.5	house	0.367
5.0	0.5	face	0.512
7.5	0.5	scrambled	0.298
```

**Required columns:**
- `onset` - onset time in seconds relative to the start of the acquisition
- `duration` - duration in seconds (use `n/a` for instantaneous events)

**Recommended columns:**
- `trial_type` - categorical label for condition
- `response_time` - RT in seconds
- Custom columns as needed (with descriptions in corresponding `.json` sidecar)

### 9. Participants File

```
participant_id	age	sex	group	handedness
sub-01	25	M	control	right
sub-02	30	F	patient	left
sub-03	28	M	control	right
```

The `participants.json` sidecar describes columns:

```json
{
    "age": {
        "Description": "Age of the participant at time of scanning",
        "Units": "years"
    },
    "sex": {
        "Description": "Biological sex",
        "Levels": {
            "M": "male",
            "F": "female"
        }
    },
    "group": {
        "Description": "Experimental group",
        "Levels": {
            "control": "Healthy control",
            "patient": "Patient group"
        }
    },
    "handedness": {
        "Description": "Dominant hand",
        "Levels": {
            "right": "Right-handed",
            "left": "Left-handed",
            "ambidextrous": "Ambidextrous"
        }
    }
}
```

### 10. BIDS Derivatives

Processed outputs go under a `derivatives/` directory:

```
my_dataset/
  derivatives/
    fmriprep-24.1.0/
      dataset_description.json      # DatasetType: "derivative"
      sub-01/
        anat/
          sub-01_space-MNI152NLin2009cAsym_desc-preproc_T1w.nii.gz
          sub-01_space-MNI152NLin2009cAsym_desc-brain_mask.nii.gz
        func/
          sub-01_task-rest_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz
          sub-01_task-rest_desc-confounds_timeseries.tsv
    mriqc-24.0.0/
      dataset_description.json
      sub-01/
        anat/
          sub-01_T1w.html
        func/
          sub-01_task-rest_bold.html
      group_T1w.tsv
      group_bold.tsv
```

**Derivative conventions:**
- `space-<label>` - template/reference space (e.g., `MNI152NLin2009cAsym`, `T1w`)
- `desc-<label>` - description of processing (e.g., `preproc`, `brain`, `smoothed`)
- `res-<label>` - resolution (e.g., `2` for 2mm isotropic)
- Each pipeline gets its own directory under `derivatives/`
- Must have its own `dataset_description.json` with `GeneratedBy`

### 11. PyBIDS: Advanced Usage

```python
from bids import BIDSLayout
from bids.layout import BIDSLayoutIndexer

# Cache the layout index for faster repeated access
layout = BIDSLayout("/path/to/dataset", database_path="/path/to/cache.db")

# Include derivatives
layout = BIDSLayout(
    "/path/to/dataset",
    derivatives=["/path/to/dataset/derivatives/fmriprep-24.1.0"]
)

# Get derivative files
preproc = layout.get(
    subject="01",
    task="rest",
    desc="preproc",
    suffix="bold",
    space="MNI152NLin2009cAsym",
    extension=".nii.gz",
    return_type="filename"
)

# Get confound regressors
confounds = layout.get(
    subject="01",
    task="rest",
    desc="confounds",
    suffix="timeseries",
    extension=".tsv",
    return_type="filename"
)

# Build BIDS path from entities
from bids import BIDSLayout
layout = BIDSLayout("/path/to/dataset")
path = layout.build_path(
    {
        "subject": "01",
        "session": "pre",
        "task": "rest",
        "suffix": "bold",
        "extension": ".nii.gz",
        "datatype": "func"
    },
    validate=True
)

# Get all files for a subject as a DataFrame
import pandas as pd
files_df = layout.to_df()
sub01_df = files_df[files_df["subject"] == "01"]
```

### 12. BIDS-Apps

BIDS-Apps are containerized analysis pipelines that accept BIDS datasets as input:

```bash
# General BIDS-App invocation pattern
docker run -v /path/to/bids:/data:ro -v /path/to/output:/out \
    <bids-app-image> /data /out participant --participant_label 01

# Common BIDS-Apps:
# fMRIPrep - fMRI preprocessing
docker run nipreps/fmriprep /data /out participant \
    --participant-label 01 --fs-license-file /license.txt

# MRIQC - MRI quality control
docker run nipreps/mriqc /data /out participant \
    --participant-label 01

# QSIPrep - diffusion MRI preprocessing
docker run pennbbl/qsiprep /data /out participant \
    --participant-label 01
```

**BIDS-App interface convention:**
```
bids-app input_dataset output_dir {participant|group} [options]
```

- `participant` level: runs per-subject
- `group` level: runs across all subjects (aggregation/group stats)

## Reference Materials

This skill includes detailed reference documentation:

- **bids_schema.json**: Machine-readable BIDS schema (from https://bids-specification.readthedocs.io/en/stable/schema.json). This is the authoritative source for entity definitions, ordering rules, filename templates, allowed suffixes per datatype, and metadata field requirements. BEP-specific schemas are at https://github.com/bids-standard/bids-schema/tree/main/BEPs.
- **beps.yml**: Current list of all BIDS Extension Proposals with titles, leads, status, and links (from [bids-website](https://github.com/bids-standard/bids-website/blob/main/data/beps/beps.yml))
- **bids_specification.md**: Human-readable summary of the entity table, datatype reference, directory structure rules, template spaces, and specification changelog
- **metadata_fields.md**: Required and recommended JSON sidecar fields for every BIDS modality (anat, func, dwi, fmap, eeg, meg, pet, etc.)
- **conversion_tools.md**: Detailed workflows for HeuDiConv, dcm2bids, and BIDScoin including heuristic/config examples and troubleshooting

Update schema and BEPs with: `python scripts/update_schema.py`

## Common Issues and Solutions

### 1. Validator reports "Not a BIDS dataset"
**Cause**: Missing `dataset_description.json` at the root.
**Fix**: Create the file with at minimum `{"Name": "...", "BIDSVersion": "1.10.0"}`.

### 2. Inconsistent subjects warning
**Cause**: Not all subjects have the same set of files (some missing sessions, runs, etc.).
**Fix**: This is a warning, not an error. Use `--ignoreSubjectConsistency` if intentional. Document missing data in `participants.tsv` or a `scans.tsv`.

### 3. Missing SliceTiming
**Cause**: `dcm2niix` couldn't extract slice timing from DICOM headers.
**Fix**: Determine slice order from the scan protocol and add manually to the JSON sidecar. Common patterns: ascending, descending, interleaved (odd-first or even-first).

### 4. Phase encoding direction confusion
**Cause**: Axis labels (i/j/k vs x/y/z vs LR/AP/SI) are confusing.
**Fix**: In BIDS, use NIfTI image axes: `i`=first axis, `j`=second, `k`=third. `-` means negative direction. For standard axial acquisitions: `j` is typically anterior-posterior. Verify with the acquisition protocol.

### 5. PyBIDS is slow on large datasets
**Cause**: Full filesystem indexing on every `BIDSLayout()` call.
**Fix**: Use `database_path` to cache the index to an SQLite file:
```python
layout = BIDSLayout("/data", database_path="/data/.pybids_cache.db")
```

### 6. Derivatives not found by PyBIDS
**Cause**: Derivatives directory missing its own `dataset_description.json`.
**Fix**: Every derivatives directory must have `dataset_description.json` with `"DatasetType": "derivative"`.

### 7. Events file timing is off
**Cause**: `onset` times are relative to the wrong reference (e.g., trigger time vs first volume).
**Fix**: Onsets must be in seconds relative to the first volume of that run's acquisition. Account for dummy scans if they were discarded.

### 8. TSV files fail validation
**Cause**: Encoding or delimiter issues (spaces instead of tabs, BOM characters, Windows line endings).
**Fix**: Ensure tab-separated values with UTF-8 encoding and Unix line endings (`\n`). Use `n/a` (not `NA`, `NaN`, or empty) for missing values.

## Best Practices

1. **Validate early and often** - Run the BIDS validator after every conversion or modification. Fix errors before they compound.

2. **Use metadata inheritance** - Place shared metadata (e.g., `TaskName`, scanner parameters) in top-level sidecar files rather than duplicating in every subject's directory.

3. **Keep sourcedata** - Store the original DICOM (or other raw) data under `sourcedata/` so conversions are reproducible. Add `sourcedata/` to `.bidsignore`.

4. **Use consistent naming from the start** - Define your BIDS naming scheme before data collection. Use the ReproIn naming convention for scan protocols to enable automatic conversion.

5. **Document your dataset** - Write a thorough `README` describing the study design, acquisition parameters, known issues, and any deviations from BIDS.

6. **Use scans.tsv for run-level metadata** - Record per-run acquisition times and quality notes:
   ```
   filename	acq_time	quality
   func/sub-01_task-rest_bold.nii.gz	2025-01-15T10:30:00	good
   ```

7. **Version your dataset** - Use `CHANGES` to document dataset modifications. Consider DataLad for full version control of large neuroimaging datasets.

8. **Deface anatomical images** - Remove facial features from T1w/T2w images before sharing (e.g., using `pydeface`, `mri_deface`, or `afni_refacer`). Store defaced versions as the primary data or use `_defacemask` files.

9. **Use BIDS URIs for provenance** - In derivatives, reference source files using BIDS URIs: `bids::sub-01/anat/sub-01_T1w.nii.gz`.

10. **Prefer community tools** - Use established BIDS-Apps (fMRIPrep, MRIQC, QSIPrep) rather than custom pipelines when possible. They handle BIDS I/O correctly and produce BIDS-compliant derivatives.

11. **Study bids-examples** - The [bids-examples](https://github.com/bids-standard/bids-examples) repository is the canonical collection of prototypical BIDS datasets covering different modalities and use cases (MRI, fMRI, DWI, EEG, MEG, iEEG, PET, ASL, genetics, derivatives, and more). Use it as a reference when structuring your own dataset, as test data for BIDS tools, or to understand how a specific modality should be organized. Each example passes the BIDS validator.

## BIDS Extension Proposals (BEPs)

BEPs are community-driven proposals to extend BIDS to new modalities, derivatives, or metadata. The full list with status, leads, and links is in `references/beps.yml` (fetched from the [bids-website](https://github.com/bids-standard/bids-website/blob/main/data/beps/beps.yml)). BEP-specific schema previews are rendered at https://github.com/bids-standard/bids-schema/tree/main/BEPs.

**Current BEPs** (as of schema update):

| BEP | Title | Content | Status |
|-----|-------|---------|--------|
| 004 | Susceptibility Weighted Imaging | raw | Seeking new leader |
| 011 | Structural preprocessing derivatives | derivative | Has PR (#518) |
| 012 | Functional preprocessing derivatives | derivative | Has PR (#519), schema implemented |
| 014 | Affine transforms and nonlinear field warps | derivative | X5 format development |
| 016 | Diffusion weighted imaging derivatives | derivative | Has PR (#2211) |
| 017 | Generic BIDS connectivity data schema | derivative | In development |
| 021 | Common Electrophysiological Derivatives | derivative | In development |
| 023 | PET Preprocessing derivatives | derivative | In development |
| 024 | Computed Tomography scan | raw | Seeking contributors |
| 026 | Microelectrode Recordings | raw | Seeking new leader |
| 028 | Provenance | metadata | Has PR (#2099) |
| 032 | Microelectrode electrophysiology | raw | Has PR (#2307), preview available |
| 033 | Advanced Diffusion Weighted Imaging | raw | Seeking contributors |
| 034 | Computational modeling | derivative | Has PR (#967) |
| 035 | Mega-analyses with non-compliant derivatives | derivative | In development |
| 036 | Phenotypic Data Guidelines | raw | Community review |
| 037 | Non-Invasive Brain Stimulation | raw | In development |
| 039 | Dimensionality reduction-based networks | raw | In development |
| 040 | Functional Ultrasound | raw | In development |
| 041 | Statistical Model Derivatives | derivative | Collecting feedback |
| 043 | BIDS Term Mapping | metadata | Collecting feedback |
| 044 | Stimuli | raw | Has PR (#2022), community review |
| 045 | Peripheral Physiological Recordings | raw | Has PR (#2267) |
| 046 | Diffusion Tractography | derivative | In development |
| 047 | Audio/video recordings for behavioral experiments | raw | Has PR (#2231) |

**Related standards:**
- **BIDS-Stats Models**: JSON specification for defining GLM-based neuroimaging analyses
- **BIDS-Derivatives** (BEP003): Standard for preprocessed/analysis outputs (partially merged into spec)

## Related Tools Ecosystem

| Tool | Purpose |
|------|---------|
| **fMRIPrep** | fMRI preprocessing (produces BIDS derivatives) |
| **MRIQC** | MRI quality control (produces BIDS derivatives) |
| **QSIPrep** | Diffusion MRI preprocessing |
| **TemplateFlow** | Neuroimaging templates and atlases with BIDS-like naming |
| **Fitlins** | BIDS Stats Models implementation |
| **DataLad** | Version control for large datasets, integrates with BIDS |
| **OpenNeuro** | Free BIDS dataset repository |
| **DANDI** | Neurophysiology data archive (uses BIDS for some modalities) |
| **HeuDiConv** | DICOM-to-BIDS with heuristic Python files |
| **dcm2bids** | DICOM-to-BIDS with JSON config |
| **BIDScoin** | DICOM-to-BIDS with GUI and YAML config |
| **nwb2bids** | Convert NWB (Neurodata Without Borders) files to BIDS |
| **CuBIDS** | BIDS dataset curation and harmonization |
| **bids2table** | Efficient tabular indexing of BIDS datasets |
| **bids-examples** | Canonical collection of prototypical BIDS datasets for all modalities |

## Documentation

- **BIDS Specification**: https://bids-specification.readthedocs.io/
- **BIDS Website**: https://bids.neuroimaging.io/
- **PyBIDS Documentation**: https://bids-standard.github.io/pybids/
- **BIDS Validator**: https://github.com/bids-standard/bids-validator
- **BIDS Starter Kit**: https://bids-standard.github.io/bids-starter-kit/
- **BIDS Examples**: https://github.com/bids-standard/bids-examples — canonical reference datasets for every BIDS modality; use as templates and test data
- **HeuDiConv Docs**: https://heudiconv.readthedocs.io/
- **Original BIDS paper**: Gorgolewski et al. (2016) Scientific Data, doi:10.1038/sdata.2016.44
