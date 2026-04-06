# BIDS Specification Reference

> **Note**: The canonical, machine-readable source of truth is `bids_schema.json` (in this directory), exported from the [BIDS Schema](https://github.com/bids-standard/bids-specification/tree/master/src/schema). The tables below are a human-readable summary. When the two disagree, trust the schema.

## Entity Table

Complete list of BIDS entities, their keys, and where they apply. **Rows are listed in the required filename ordering** — entities must appear in this order in BIDS filenames. This order is defined in the schema at `rules.entities` (see `bids_schema.json`).

| # | Entity | Key | Format | Applies to |
|---|--------|-----|--------|------------|
| 1 | Subject | `sub-` | `<label>` (alphanumeric) | All files (required) |
| 2 | Template | `tpl-` | `<label>` | derivatives (template-based) |
| 3 | Session | `ses-` | `<label>` | All datatypes |
| 4 | Cohort | `cohort-` | `<label>` | derivatives (template cohorts) |
| 5 | Sample | `sample-` | `<label>` | microscopy |
| 6 | Task | `task-` | `<label>` | func, eeg, meg, ieeg, beh, pet, nirs, motion |
| 7 | Tracking system | `tracksys-` | `<label>` | motion |
| 8 | Acquisition | `acq-` | `<label>` | All datatypes |
| 9 | Nucleus | `nuc-` | `<label>` | MR spectroscopy |
| 10 | Volume | `voi-` | `<label>` | MR spectroscopy |
| 11 | Contrast enhancing agent | `ce-` | `<label>` | anat |
| 12 | Tracer | `trc-` | `<label>` | pet |
| 13 | Stain | `stain-` | `<label>` | microscopy |
| 14 | Reconstruction | `rec-` | `<label>` | anat, func, pet |
| 15 | Direction | `dir-` | `<label>` | fmap, dwi, perf, func |
| 16 | Run | `run-` | `<index>` (integer) | All datatypes |
| 17 | Modality | `mod-` | `<label>` | fieldmaps |
| 18 | Echo | `echo-` | `<index>` | func, fmap |
| 19 | Flip | `flip-` | `<index>` | anat (quantitative MRI) |
| 20 | Inversion | `inv-` | `<index>` | anat (quantitative MRI) |
| 21 | Magnetization transfer | `mt-` | `on`/`off` | anat (quantitative MRI) |
| 22 | Part | `part-` | `mag`/`phase`/`real`/`imag` | anat, func |
| 23 | Processing | `proc-` | `<label>` | eeg, meg, ieeg |
| 24 | Hemisphere | `hemi-` | `L`/`R` | derivatives (surface data) |
| 25 | Space | `space-` | `<label>` | derivatives |
| 26 | Split | `split-` | `<index>` | func, dwi, eeg, meg, ieeg |
| 27 | Recording | `recording-` | `<label>` | physio, stim, eeg, meg |
| 28 | Chunk | `chunk-` | `<index>` | large files split across chunks |
| 29 | Atlas | `atlas-` | `<label>` | derivatives (atlas-based) |
| 30 | Segmentation | `seg-` | `<label>` | derivatives |
| 31 | Scale | `scale-` | `<label>` | derivatives |
| 32 | Resolution | `res-` | `<label>` | derivatives |
| 33 | Density | `den-` | `<label>` | derivatives (surface meshes) |
| 34 | Label | `label-` | `<label>` | derivatives (segmentation labels) |
| 35 | Description | `desc-` | `<label>` | derivatives only |

## Datatypes (Top-Level Directories)

| Datatype | Description | Common Suffixes |
|----------|-------------|-----------------|
| `anat` | Structural MRI | `T1w`, `T2w`, `FLAIR`, `T2star`, `inplaneT1`, `inplaneT2`, `PDw`, `T1map`, `T2map`, `T1rho`, `UNIT1`, `MP2RAGE`, `MTR`, `MTS` |
| `func` | Functional MRI | `bold`, `cbv`, `sbref` |
| `dwi` | Diffusion-weighted imaging | `dwi`, `sbref` |
| `fmap` | Fieldmaps | `phasediff`, `phase1`, `phase2`, `magnitude1`, `magnitude2`, `fieldmap`, `epi` |
| `perf` | Perfusion imaging (ASL) | `asl`, `m0scan`, `aslcontext` |
| `eeg` | Electroencephalography | `eeg`, `channels`, `electrodes`, `events`, `coordsystem` |
| `meg` | Magnetoencephalography | `meg`, `channels`, `coordsystem`, `events`, `headshape` |
| `ieeg` | Intracranial EEG | `ieeg`, `channels`, `electrodes`, `events`, `coordsystem` |
| `pet` | Positron Emission Tomography | `pet`, `blood` |
| `micr` | Microscopy | `2PE`, `BF`, `CARS`, `CONF`, `DIC`, `DF`, `FLUO`, `MPE`, `NLO`, `OCT`, `PC`, `PLI`, `SRS`, `TL` |
| `beh` | Behavioral data (no imaging) | `events`, `beh`, `physio`, `stim` |
| `motion` | Motion capture | `motion`, `channels`, `events` |
| `nirs` | Near-infrared spectroscopy | `nirs`, `channels`, `optodes`, `coordsystem`, `events` |

## File Extensions

| Extension | Description |
|-----------|-------------|
| `.nii.gz` | Compressed NIfTI (standard for MRI/fMRI/DWI) |
| `.nii` | Uncompressed NIfTI |
| `.json` | JSON sidecar metadata |
| `.tsv` | Tab-separated values (events, participants, etc.) |
| `.bvec` | b-vectors (DWI gradient directions) |
| `.bval` | b-values (DWI gradient strengths) |
| `.edf` | European Data Format (EEG) |
| `.bdf` | BioSemi Data Format (EEG) |
| `.vhdr`/`.vmrk`/`.eeg` | BrainVision format (EEG) |
| `.set` | EEGLAB format (EEG) |
| `.fif` | Elekta/MEGIN format (MEG) |
| `.ds` | CTF dataset (MEG) |
| `.sqd`/`.con` | KIT/Yokogawa (MEG) |

## Required Files

### Dataset-level (always required)
- `dataset_description.json`

### Dataset-level (recommended)
- `README` or `README.md`
- `CHANGES`
- `participants.tsv` + `participants.json`
- `LICENSE`

### Run-level (recommended)
- `sub-<label>/[ses-<label>/]sub-<label>[_ses-<label>]_scans.tsv` - per-run acquisition metadata

### Modality-specific required files
- **func/bold**: corresponding `_events.tsv` for task data; `TaskName` in JSON sidecar
- **dwi**: `.bvec` and `.bval` files
- **eeg/meg/ieeg**: `_channels.tsv`, `_events.tsv`
- **perf/asl**: `_aslcontext.tsv`

## Directory Structure Rules

1. Subject directories are named `sub-<label>` and sit at dataset root
2. Session directories `ses-<label>` are optional; if used, must be used for ALL subjects
3. Datatype directories (`anat/`, `func/`, etc.) sit inside subject (or session) directories
4. `sourcedata/` stores raw unprocessed data (DICOM, etc.) - not validated
5. `derivatives/` stores processed outputs - each pipeline in its own subdirectory
6. `code/` stores analysis scripts
7. `stimuli/` stores stimulus files used during acquisition
8. `phenotype/` stores questionnaire/behavioral data not tied to specific imaging

## Metadata Inheritance

JSON metadata cascades from higher to lower directories. If the same key appears at multiple levels, the most specific (closest to the data file) wins.

**Resolution order** (highest priority first):
1. File-level sidecar: `sub-01/func/sub-01_task-rest_bold.json`
2. Subject-level sidecar: `sub-01/sub-01_task-rest_bold.json`
3. Dataset-level sidecar: `task-rest_bold.json`

This avoids duplicating metadata that is constant across subjects (e.g., `RepetitionTime`, `TaskName`).

## Standard Template Spaces

Common `space-` values used in derivatives:

| Space Label | Description |
|-------------|-------------|
| `MNI152NLin2009cAsym` | MNI 2009c nonlinear asymmetric (fMRIPrep default) |
| `MNI152NLin6Asym` | MNI 6th-generation nonlinear asymmetric (FSL default) |
| `MNI152Lin` | MNI linear registration |
| `MNIPediatricAsym` | Pediatric MNI templates |
| `T1w` | Individual subject's T1w native space |
| `fsnative` | FreeSurfer individual surface space |
| `fsaverage` | FreeSurfer average surface (164k vertices) |
| `fsaverage5` | FreeSurfer average surface (10k vertices) |
| `fsaverage6` | FreeSurfer average surface (40k vertices) |
| `fsLR` | HCP fs_LR surface space |
| `OASIS30ANTs` | OASIS-30 ANTs template |
| `UNCInfant` | UNC infant templates |

Full list managed by TemplateFlow: https://www.templateflow.org/

## Specification Changelog (Selected)

| Version | Key Changes |
|---------|-------------|
| 1.10.0 | Motion capture modality; refined derivative entity rules |
| 1.9.0 | NIRS modality; Python-based validator reference implementation |
| 1.8.0 | Microscopy modality; `chunk-` entity for large files |
| 1.7.0 | PET modality fully specified |
| 1.6.0 | EEG/MEG/iEEG matured; `_coordsystem.json` |
| 1.5.0 | Genetic descriptors; ASL perfusion |
| 1.4.0 | `dataset_description.json` expanded; derivatives framework |
| 1.0.0 | Initial release: MRI only (anat, func, dwi, fmap) |

## Entity Label Rules

- **Labels** (`<label>`): alphanumeric only, no special characters, no leading zeros (except `run-`)
- **Indices** (`<index>`): non-negative integers, zero-padded to equal width within a dataset (e.g., `run-01`, `run-02`)
- Subject labels: typically numeric (`01`, `02`) but can be alphanumeric (`CON01`, `PAT01`)
- Session labels: descriptive (`pre`, `post`, `baseline`, `followup`) or numeric
- Task labels: brief, descriptive, no spaces (`rest`, `nback`, `faces`, `gonogo`)
