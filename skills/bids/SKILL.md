---
name: bids
description: >
  Use this skill when working with Brain Imaging Data Structure (BIDS) datasets:
  organizing neuroscience and biomedical data (MRI, EEG, MEG, iEEG, PET, microscopy,
  NIRS, motion capture, EMG, MR spectroscopy, behavioral), querying BIDS layouts,
  validating compliance, converting DICOM to BIDS, writing metadata sidecars, or
  creating BIDS derivatives.
license: https://creativecommons.org/licenses/by/4.0/
metadata:
  version: "1.2"
  skill-author: Yaroslav Halchenko
---

# Brain Imaging Data Structure (BIDS)

## Overview

The Brain Imaging Data Structure (BIDS) is a community standard for organizing and describing neuroscience and biomedical research datasets. It defines a consistent file naming convention, directory hierarchy, and metadata schema so that datasets are immediately understandable by humans and software tools alike. BIDS is governed by the BIDS Specification (currently v1.11.x) and is maintained by the community via the BIDS-Standard GitHub organization.

While BIDS originated for MRI, it has grown well beyond neuroimaging. The specification now covers 11 modalities spanning imaging, electrophysiology, and behavioral data:

- **Imaging**: MRI (structural, functional, diffusion, fieldmaps, perfusion/ASL), PET, microscopy
- **Electrophysiology**: EEG, MEG, iEEG (intracranial EEG), EMG
- **Other**: NIRS (near-infrared spectroscopy), motion capture, behavioral data (without imaging), MR spectroscopy

Active BEPs are extending BIDS further — notably BEP032 (microelectrode electrophysiology) will add support for extracellular recordings including Neuropixels probes, bringing BIDS to a prevalent methodology in animal neuroscience research (see also the neuropixels-analysis skill).

Adoption is required or strongly encouraged by major data repositories (OpenNeuro, DANDI), leading journals (NeuroImage, Human Brain Mapping, Scientific Data), and funding agencies (NIH, ERC).

The Python ecosystem for BIDS centers on **PyBIDS** (`pybids`) for querying and indexing BIDS datasets, and the **bids-validator** (Deno-based, available as PyPI package `bids-validator-deno` or via Deno directly) for compliance checking. Conversion from DICOM is typically done with **HeuDiConv**, **dcm2bids**, or **BIDScoin**.

## When to Use This Skill

Apply this skill when:
- Organizing raw neuroscience data (imaging, electrophysiology, behavioral) into BIDS-compliant directory structures
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

Twelve workflow areas, each with worked code, are documented in
[references/core_workflows.md](references/core_workflows.md):

1. **BIDS directory structure** — the required layout and where each modality belongs.
2. **`dataset_description.json`** — the required fields and how to generate it.
3. **Querying with PyBIDS** — `BIDSLayout`, entity filters, sidecar metadata with
   automatic inheritance, and building paths from entities.
4. **Validation** — `bids-validator` via the PyPI wrapper (recommended), via Deno
   directly, the legacy Node validator, and using `.bidsignore` to exclude files.
5. **Entities and file naming** — the entity order and naming grammar.
6. **DICOM to BIDS conversion** — HeuDiConv (including the turnkey ReproIn path and the
   reconnaissance → heuristic → convert sequence) and dcm2bids (config-file based).
7. **Metadata sidecars** — required and recommended JSON fields per modality.
8. **Events files** — task fMRI event timing and column conventions.
9. **Participants file** — `participants.tsv` and its data dictionary.
10. **Derivatives** — the derivatives layout and its `dataset_description.json`.
11. **Advanced PyBIDS** — index caching, including derivatives, confound regressors, and
    DataFrame output.
12. **BIDS-Apps** — the standard invocation pattern, and fMRIPrep, MRIQC, and QSIPrep.

Validate with the BIDS validator as well as indexing with PyBIDS. Successful indexing
is not a full compliance check; record the validator and BIDS schema versions, and
inspect warnings and metadata inheritance before analysis.

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
**Fix**: Recover actual slice acquisition offsets from scanner metadata or a verified sequence protocol. Slice order alone does not determine timing, especially with multiband acquisition or dead time. Store offsets in seconds in slice-index order, accounting for `SliceEncodingDirection`; document missing timing instead of inventing it.

### 4. Phase encoding direction confusion
**Cause**: Axis labels (i/j/k vs x/y/z vs LR/AP/SI) are confusing.
**Fix**: In BIDS, use NIfTI image axes: `i`=first axis, `j`=second, `k`=third. `-` means negative direction. Anatomical direction depends on the NIfTI affine and converter orientation; do not infer `j` or its sign from an AP/PA series label alone. Verify against scanner metadata and the image orientation.

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

7. **Version your dataset** - Use `CHANGES` to document dataset modifications. Consider DataLad for full version control of large datasets.

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
| 032 | Microelectrode electrophysiology | raw | Has PR (#2307), preview available — covers Neuropixels and other extracellular probes; relates to neuropixels-analysis skill |
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
