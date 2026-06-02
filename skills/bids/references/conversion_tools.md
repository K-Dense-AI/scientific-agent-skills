# BIDS Conversion Tools Reference

This reference covers detailed workflows for converting DICOM and other raw data formats to BIDS using the three main conversion tools.

## HeuDiConv

HeuDiConv is the most flexible DICOM-to-BIDS converter. It supports three usage modes — from fully automatic turnkey conversion to fully custom heuristics — and handles duplicates, provenance tracking, and sourcedata archiving out of the box.

**Repository**: https://github.com/nipy/heudiconv
**Docs**: https://heudiconv.readthedocs.io/
**Tutorials**: https://heudiconv.readthedocs.io/en/latest/tutorials.html

### Installation

```bash
uv pip install heudiconv

# HeuDiConv wraps dcm2niix for the actual conversion
# dcm2niix is usually installed as a dependency, but can also be installed via:
# conda install -c conda-forge dcm2niix
# or: apt-get install dcm2niix
```

### Mode 1: ReproIn (Turnkey Conversion — Recommended for New Studies)

If scanner protocol names follow the [ReproIn naming convention](https://github.com/repronim/reproin), conversion is fully automatic with no heuristic file to write. ReproIn is a setup for automatic generation of sharable, version-controlled BIDS datasets directly from MR scanners.

```bash
# Turnkey conversion — just point at DICOMs, HeuDiConv does the rest
heudiconv --files dicom/001 -o data -f reproin --bids --minmeta
```

#### ReproIn Protocol Naming Rules

Protocol names encode BIDS entities directly. Format: `<seqtype>[-<suffix>][_<entity>-<label>]...`

| Protocol name at scanner | BIDS output |
|--------------------------|-------------|
| `anat-T1w` or just `anat` | `sub-XX/anat/sub-XX_T1w.nii.gz` |
| `func-bold_task-rest` or `func_task-rest` | `sub-XX/func/sub-XX_task-rest_bold.nii.gz` |
| `dwi_dir-AP` | `sub-XX/dwi/sub-XX_dir-AP_dwi.nii.gz` |
| `fmap_dir-PA` or `fmap-epi_dir-PA` | `sub-XX/fmap/sub-XX_dir-PA_epi.nii.gz` |
| `fmap_acq-4mm` | `sub-XX/fmap/sub-XX_acq-4mm_epi.nii.gz` |

**Key features:**
- **Default suffixes**: `anat` defaults to `T1w`, `func` to `bold`, `fmap` to `epi` — so they can be omitted
- **Subject ID**: extracted automatically from DICOM metadata (Patient ID)
- **Session**: set once on any sequence (e.g., `anat-scout_ses-pre`) and ReproIn propagates it to all sequences in that scanner Program/Patient
- **Duplicate runs**: automatically numbered (`run-01`, `run-02`, ...) when the same protocol is run multiple times
- **Locator hierarchy**: output is nested under Region/Exam from the scanner's Study Description (customizable with `--locator`)
- **sourcedata**: original DICOMs are archived as `.tgz` files under `sourcedata/` for reproducibility
- **Dashes in names**: scanners may strip dashes from protocol names during DICOM export — ReproIn handles this gracefully

#### ReproIn Overview

See also:
- [ReproIn Walkthrough](https://github.com/repronim/reproin#walkthrough) for scanner setup
- [ReproNim Webinar slides and recording](https://github.com/repronim/reproin#presentations) on HeuDiConv + ReproIn

### Mode 2: Custom Heuristic Mapping into ReproIn (For Existing Data)

If you already have collected data with non-ReproIn protocol names (or cannot control scanner naming), you can write a thin heuristic that maps your protocol names into ReproIn conventions. This gives you all ReproIn benefits (automatic entity handling, duplicate management, sourcedata archiving) while accommodating arbitrary scanner naming.

See https://github.com/repronim/reproin/issues/18 for a brief HOWTO on this approach.

The idea is to write a heuristic whose `infotodict` returns keys that follow ReproIn naming patterns, so the ReproIn machinery handles the rest.

### Mode 3: Custom Heuristic (Full Flexibility)

For studies with complex mappings or non-standard requirements, write a full Python heuristic file. This is the most common workflow for retrospective conversion of existing datasets.

#### Step 1: Reconnaissance — Discover DICOM series

```bash
# -f convertall: built-in heuristic that lists all series without converting
# -c none: don't convert, just generate dicominfo.tsv
heudiconv \
    --files dicom/219/itbs/*/*.dcm \
    -s 219 \
    -f convertall \
    -c none \
    -o Nifti/
```

This creates `.heudiconv/219/info/dicominfo.tsv` containing one row per DICOM series with columns:
- `series_id`, `sequence_name`, `protocol_name`, `series_description`
- `dim1`-`dim4` (image dimensions), `TR`, `TE`, `image_type`
- `is_derived`, `is_motion_corrected` — important for filtering

Review this TSV (open in a spreadsheet) to understand what was acquired and plan the mapping to BIDS names. Step 1 only needs to be done once per project.

#### Step 2: Write a heuristic file

```python
"""HeuDiConv heuristic for a typical fMRI study.

Study design:
- T1w MPRAGE anatomical
- Resting-state BOLD
- Task BOLD (n-back working memory)
- DWI with two phase-encoding directions
- Fieldmap (phase-difference)
"""

def create_key(template, outtype=('nii.gz',), annotation_classes=None):
    if template is None or not template:
        raise ValueError('Template must be a valid format string')
    return template, outtype, annotation_classes


def infotodict(seqinfo):
    """Heuristic evaluator for determining which runs belong where.

    Parameters
    ----------
    seqinfo : list of namedtuples
        Each namedtuple has fields: .series_id, .sequence_name,
        .protocol_name, .series_description, .dim1, .dim2, .dim3, .dim4,
        .TR, .TE, .is_derived, .is_motion_corrected, .image_type, etc.

    Returns
    -------
    info : dict
        Keys are tuples from create_key(), values are lists of series_id
    """
    # Define BIDS output templates
    t1w = create_key(
        'sub-{subject}/{session}/anat/sub-{subject}_{session}_T1w'
    )
    rest_bold = create_key(
        'sub-{subject}/{session}/func/sub-{subject}_{session}_task-rest_bold'
    )
    # {item:02d} auto-numbers runs when the same protocol is run multiple times
    nback_bold = create_key(
        'sub-{subject}/{session}/func/sub-{subject}_{session}_task-nback_run-{item:02d}_bold'
    )
    dwi_AP = create_key(
        'sub-{subject}/{session}/dwi/sub-{subject}_{session}_dir-AP_dwi'
    )
    dwi_PA = create_key(
        'sub-{subject}/{session}/dwi/sub-{subject}_{session}_dir-PA_dwi'
    )
    fmap_phasediff = create_key(
        'sub-{subject}/{session}/fmap/sub-{subject}_{session}_phasediff'
    )
    fmap_mag1 = create_key(
        'sub-{subject}/{session}/fmap/sub-{subject}_{session}_magnitude1'
    )
    fmap_mag2 = create_key(
        'sub-{subject}/{session}/fmap/sub-{subject}_{session}_magnitude2'
    )

    info = {
        t1w: [], rest_bold: [], nback_bold: [],
        dwi_AP: [], dwi_PA: [],
        fmap_phasediff: [], fmap_mag1: [], fmap_mag2: [],
    }

    for s in seqinfo:
        protocol = s.protocol_name.lower()
        series_desc = s.series_description.lower() if s.series_description else ''

        # Anatomical — filter by dim3 to exclude localizers
        if ('mprage' in protocol or 't1w' in protocol) and s.dim3 > 100:
            info[t1w].append(s.series_id)

        # Functional — filter by dim4 and exclude MOCO series
        elif 'rest' in protocol and s.dim4 > 10 and not s.is_motion_corrected:
            info[rest_bold].append(s.series_id)
        elif 'nback' in protocol and s.dim4 > 10 and not s.is_motion_corrected:
            info[nback_bold].append(s.series_id)

        # Diffusion
        elif ('dti' in protocol or 'dwi' in protocol) and s.dim4 > 1:
            if 'ap' in protocol or 'ap' in series_desc:
                info[dwi_AP].append(s.series_id)
            elif 'pa' in protocol or 'pa' in series_desc:
                info[dwi_PA].append(s.series_id)

        # Fieldmaps
        elif 'field' in protocol or 'fmap' in protocol:
            if 'ph' in s.image_type_text.lower():
                info[fmap_phasediff].append(s.series_id)
            elif s.series_description and 'e1' in s.series_description.lower():
                info[fmap_mag1].append(s.series_id)
            elif s.series_description and 'e2' in s.series_description.lower():
                info[fmap_mag2].append(s.series_id)

    return info
```

#### Step 3: Convert

```bash
# Convert with custom heuristic
heudiconv \
    --files dicom/219/itbs/*/*.dcm \
    -s 219 \
    -ss itbs \
    -f Nifti/code/heuristic.py \
    -c dcm2niix \
    --bids \
    --minmeta \
    -o Nifti/

# Or using -d template for batch conversion of multiple subjects
heudiconv \
    -d /path/to/dicoms/{subject}/*/*/*.dcm \
    -s 01 02 03 04 05 \
    -f my_heuristic.py \
    -c dcm2niix \
    --bids \
    --minmeta \
    -o /path/to/bids_output

# Key flags:
# --files : point to specific DICOM files/directories
# -d : DICOM path template ({subject}, {session} are replaced)
# -s : subject label(s)
# -ss : session label
# -f : heuristic file path, or built-in name (reproin, convertall)
# -c : converter (dcm2niix, none)
# --bids / -b : output BIDS structure (creates JSON sidecars, etc.)
# --minmeta : prevent excess DICOM metadata from overflowing JSON sidecars
# -o : output directory
# --overwrite : re-run conversion overwriting existing files
```

### The .heudiconv Directory

Every conversion creates/updates a `.heudiconv/` hidden directory alongside the output:
- `.heudiconv/<subject>/info/dicominfo.tsv` — DICOM series metadata
- `.heudiconv/<subject>/info/<heuristic>.py` — copy of the heuristic used
- Conversion records for each subject/session

**Important**: If you re-run conversion for a subject/session that was already processed, HeuDiConv silently reuses cached conversion info from `.heudiconv/`. If troubleshooting, delete the subject's entry from `.heudiconv/` (or the whole directory) and re-run.

Keep `.heudiconv/` with your data — together with `code/` it provides valuable provenance information.

### HeuDiConv Tips

1. **Always use `--minmeta`** to prevent excess DICOM metadata from overflowing JSON sidecars — fMRIPrep and MRIQC may crash on bloated JSON files
2. **Use `{item:02d}` in templates** for auto-numbering runs: if multiple series match, they get `run-01`, `run-02`, etc. Without this, later runs silently overwrite earlier ones
3. **Filter by `dim3`/`dim4`** to exclude localizers (small `dim3`) and single-volume scouts (`dim4 == 1`)
4. **Check `s.is_motion_corrected`** to exclude scanner-generated MOCO series (e.g., `if not s.is_motion_corrected`)
5. **Check `s.is_derived`** to skip other derived/processed series
6. **Store heuristic with dataset** under `code/` for reproducibility
7. **Use `--files`** when DICOM organization doesn't follow a clean `{subject}` template pattern
8. **For new studies**: prefer ReproIn protocol naming from the start — it eliminates the need for custom heuristics entirely
9. **For existing data with arbitrary names**: consider the "map into reproin" approach rather than writing a fully custom heuristic — you get duplicate handling, session propagation, and other ReproIn features for free

## dcm2bids (Configuration-File-Based)

dcm2bids uses JSON configuration files instead of Python heuristics. Simpler for straightforward datasets.

**Repository**: https://github.com/UNFmontreal/Dcm2Bids
**Docs**: https://unfmontreal.github.io/Dcm2Bids/

### Installation

```bash
uv pip install dcm2bids
# Also installs dcm2niix
```

### Workflow

#### Step 1: Scaffold a BIDS directory

```bash
dcm2bids_scaffold -o /path/to/bids_output
```

Creates the basic BIDS structure with `dataset_description.json`, `README`, `.bidsignore`, etc.

#### Step 2: Run helper to inspect DICOM metadata

```bash
dcm2bids_helper -d /path/to/dicom_dir -o /path/to/bids_output
```

Creates `tmp_dcm2bids/helper/` with converted NIfTI files and JSON sidecars. Review the JSON files to find distinguishing metadata fields.

#### Step 3: Write configuration file

```json
{
    "descriptions": [
        {
            "id": "id_t1w",
            "datatype": "anat",
            "suffix": "T1w",
            "criteria": {
                "SeriesDescription": "*MPRAGE*",
                "ImageType": ["ORIGINAL", "PRIMARY", "M", "ND", "NORM"]
            }
        },
        {
            "id": "id_bold_rest",
            "datatype": "func",
            "suffix": "bold",
            "custom_entities": "task-rest",
            "criteria": {
                "SeriesDescription": "*REST*BOLD*",
                "ImageType": ["ORIGINAL", "PRIMARY", "M", "ND", "MOSAIC"]
            },
            "sidecar_changes": {
                "TaskName": "rest"
            }
        },
        {
            "id": "id_bold_nback",
            "datatype": "func",
            "suffix": "bold",
            "custom_entities": "task-nback",
            "criteria": {
                "SeriesDescription": "*NBACK*",
                "EchoTime": 0.03
            },
            "sidecar_changes": {
                "TaskName": "nback"
            }
        },
        {
            "id": "id_dwi",
            "datatype": "dwi",
            "suffix": "dwi",
            "custom_entities": "dir-AP",
            "criteria": {
                "SeriesDescription": "*DTI*AP*"
            }
        },
        {
            "id": "id_fmap_phasediff",
            "datatype": "fmap",
            "suffix": "phasediff",
            "criteria": {
                "SeriesDescription": "*field*map*",
                "EchoTime1": 0.00492,
                "EchoTime2": 0.00738
            },
            "sidecar_changes": {
                "IntendedFor": [
                    "bids::sub-{subject}/func/sub-{subject}_task-rest_bold.nii.gz",
                    "bids::sub-{subject}/func/sub-{subject}_task-nback_bold.nii.gz"
                ]
            }
        }
    ]
}
```

**Configuration file fields:**
- `datatype`: BIDS datatype (`anat`, `func`, `dwi`, `fmap`, etc.)
- `suffix`: BIDS suffix (`T1w`, `bold`, `dwi`, etc.)
- `custom_entities`: additional BIDS entities (`task-rest`, `dir-AP`, `acq-highres`, etc.)
- `criteria`: dictionary of DICOM/JSON metadata fields to match (supports wildcards `*`)
- `sidecar_changes`: fields to add/modify in the output JSON sidecar
- `id`: arbitrary identifier for the description (for logging)

#### Step 4: Convert

```bash
# Single subject
dcm2bids -d /path/to/dicom_dir -p 01 -c dcm2bids_config.json -o /path/to/bids_output

# With session
dcm2bids -d /path/to/dicom_dir -p 01 -s pre -c dcm2bids_config.json -o /path/to/bids_output

# Flags:
# -d : DICOM source directory
# -p : participant label
# -s : session label (optional)
# -c : configuration file
# -o : output BIDS directory
# --auto_extract_entities : auto-detect run numbers from DICOM
# --force_dcm2bids : overwrite existing conversions
```

### dcm2bids Tips

1. **Use `dcm2bids_helper` first** to see exactly what metadata dcm2niix extracts
2. **Criteria matching uses wildcards** (`*`) and is case-sensitive
3. **Multiple criteria** are ANDed together; use the most specific combination
4. **`sidecar_changes`** can inject any BIDS metadata (useful for `TaskName`, `IntendedFor`)
5. **Store config file** under `code/dcm2bids_config.json` for reproducibility

## BIDScoin (GUI + YAML Configuration)

BIDScoin provides a graphical interface and YAML-based configuration. Good for users who prefer visual mapping.

**Repository**: https://github.com/Donders-Institute/bidscoin
**Docs**: https://bidscoin.readthedocs.io/

### Installation

```bash
uv pip install bidscoin
# Optional: install with all plugin dependencies
uv pip install "bidscoin[all]"
```

### Workflow

```bash
# Step 1: Create a bidsmap template by scanning DICOMs
bidsmapper /path/to/raw /path/to/bids

# Step 2: Edit the bidsmap (launches GUI)
bidseditor /path/to/bids

# Step 3: Convert using the finalized bidsmap
bidscoiner /path/to/raw /path/to/bids
```

### BIDScoin Tips

1. **GUI-based editing** is BIDScoin's strength - the `bidseditor` shows DICOM metadata alongside BIDS mapping
2. **YAML bidsmap** can be edited manually if preferred
3. **Plugin architecture** supports custom conversion backends beyond dcm2niix
4. **Good for multi-site studies** where protocol names vary - visual mapping makes differences obvious

## Comparison

| Feature | HeuDiConv | dcm2bids | BIDScoin |
|---------|-----------|----------|----------|
| Configuration | Python heuristic | JSON config | YAML + GUI |
| Flexibility | Highest (full Python) | Medium (criteria matching) | Medium (plugin system) |
| Learning curve | Steeper (Python) | Moderate | Gentlest (GUI) |
| Batch processing | Excellent | Good | Good |
| ReproIn support | Built-in | No | No |
| DataLad integration | Built-in | No | No |
| Best for | Complex studies, automation | Simple-to-moderate studies | Visual learners, multi-site |
| Active development | Yes | Yes | Yes |

## Post-Conversion Checklist

After converting DICOM to BIDS with any tool:

1. **Run the BIDS validator**: `bids-validator /path/to/bids_output`
2. **Check JSON sidecars** for critical fields (`RepetitionTime`, `TaskName`, `SliceTiming`, `PhaseEncodingDirection`)
3. **Verify NIfTI headers** match expectations (dimensions, voxel sizes, orientation)
4. **Add missing metadata** that dcm2niix couldn't extract from DICOM
5. **Create `participants.tsv`** with demographic data
6. **Write events files** for task fMRI
7. **Write `README`** describing the dataset
8. **Deface anatomical images** if sharing data
9. **Run `bids-validator` again** after any manual modifications

## Common DICOM-to-BIDS Pitfalls

### Multiband/SMS sequences
- dcm2niix may split slices incorrectly for multiband data
- Check `dim4` (number of volumes) matches expectations
- Verify `SliceTiming` is correct for the multiband factor

### Dual-echo fieldmaps
- Siemens stores both echoes in one series; dcm2niix splits them
- GE/Philips may store them as separate series
- Verify `EchoTime1` < `EchoTime2` in the phasediff sidecar

### Phase encoding direction
- DICOM `InPlanePhaseEncodingDirection` → BIDS `PhaseEncodingDirection`
- Mapping depends on acquisition orientation and NIfTI axis conventions
- **Always verify** by checking the actual distortion pattern in the images

### Multi-run numbering
- Ensure runs are numbered sequentially (`run-01`, `run-02`)
- HeuDiConv: use `{item:02d}` placeholder
- dcm2bids: use `--auto_extract_entities` or manually specify runs

### Derived/processed series
- Scanners may export inline-processed data (e.g., motion-corrected, distortion-corrected)
- These should NOT be converted to BIDS raw data
- Filter by `ImageType` containing `DERIVED` or `is_derived` flag in HeuDiConv
