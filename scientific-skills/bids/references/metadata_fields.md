# BIDS Metadata Fields Reference

This reference lists the required and recommended JSON sidecar fields for each BIDS modality.

**Legend:**
- **R** = Required
- **REC** = Recommended
- **OPT** = Optional

## Common MRI Fields (All MRI Modalities)

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `MagneticFieldStrength` | REC | number | Field strength in Tesla |
| `Manufacturer` | REC | string | Scanner manufacturer |
| `ManufacturersModelName` | REC | string | Scanner model |
| `DeviceSerialNumber` | REC | string | Scanner serial number |
| `StationName` | REC | string | Scanner station name |
| `SoftwareVersions` | REC | string | Scanner software version |
| `InstitutionName` | REC | string | Name of institution |
| `InstitutionAddress` | REC | string | Address of institution |
| `InstitutionalDepartmentName` | REC | string | Department name |

## Anatomical MRI (anat/)

### T1w, T2w, FLAIR, T2star, PDw

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `RepetitionTime` | REC | number | TR in seconds |
| `EchoTime` | REC | number | TE in seconds |
| `InversionTime` | REC | number | TI in seconds (if applicable) |
| `FlipAngle` | REC | number | Flip angle in degrees |
| `SequenceName` | REC | string | Pulse sequence name |
| `SequenceVariant` | REC | string | Variant of the sequence |
| `ScanningSequence` | REC | string | General description |
| `PulseSequenceType` | REC | string | Type of pulse sequence |
| `NonlinearGradientCorrection` | REC | boolean | Whether applied |
| `ParallelReductionFactorInPlane` | REC | number | iPAT/GRAPPA factor |
| `ContrastBolusIngredient` | REC | string | Active contrast ingredient |

### Quantitative MRI (T1map, T2map, etc.)

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `RepetitionTimeExcitation` | R | number | Excitation TR in seconds |
| `RepetitionTimePrepration` | R | number | Preparation TR in seconds |
| `FlipAngle` | R | number/array | Flip angle(s) in degrees |
| `MTState` | R | boolean | Magnetization transfer on/off |
| `SpoilingState` | REC | boolean | Whether RF spoiling applied |
| `SpoilingType` | REC | string | `RF`, `GRADIENT`, or `COMBINED` |
| `SpoilingRFPhaseIncrement` | REC | number | Phase increment in degrees |

## Functional MRI (func/)

### BOLD

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `RepetitionTime` | R | number | TR in seconds (volume acquisition time) |
| `TaskName` | R | string | Name of the task (must match `task-<label>`) |
| `SliceTiming` | REC | array | Time each slice was acquired, in seconds |
| `EchoTime` | REC | number | TE in seconds |
| `FlipAngle` | REC | number | Flip angle in degrees |
| `PhaseEncodingDirection` | REC | string | `i`, `i-`, `j`, `j-`, `k`, `k-` |
| `EffectiveEchoSpacing` | REC | number | Effective echo spacing in seconds |
| `TotalReadoutTime` | REC | number | Total readout time in seconds |
| `MultibandAccelerationFactor` | REC | number | Multiband/SMS factor |
| `NumberOfVolumesDiscardedByScanner` | REC | integer | Dummy scans removed |
| `NumberOfVolumesDiscardedByUser` | REC | integer | Volumes removed post-hoc |
| `TaskDescription` | REC | string | Longer description of the task |
| `CogAtlasID` | REC | string | Cognitive Atlas ID for the task |
| `CogPOID` | REC | string | Cognitive Paradigm Ontology ID |
| `Instructions` | REC | string | Instructions given to participants |

### Multi-echo BOLD

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `EchoTime` | R | number | TE for this echo (each echo in separate file) |
| `EchoTime1`, `EchoTime2` | - | - | NOT used; use `echo-<index>` entity |

### BOLD Timing Details

**SliceTiming** - Array of times (in seconds) at which each slice was acquired relative to the start of volume acquisition. Length must equal the number of slices.

Example for ascending sequential (3 slices, TR=2s):
```json
{"SliceTiming": [0.0, 0.667, 1.333]}
```

Example for interleaved (odd-first, 6 slices, TR=2s):
```json
{"SliceTiming": [0.0, 0.667, 1.333, 0.333, 1.0, 1.667]}
```

**PhaseEncodingDirection** values:
- `i` / `i-` : along first image axis (typically left-right)
- `j` / `j-` : along second image axis (typically anterior-posterior)
- `k` / `k-` : along third image axis (typically inferior-superior)
- The `-` suffix indicates the negative direction along that axis

## Diffusion-Weighted Imaging (dwi/)

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `PhaseEncodingDirection` | R | string | Phase encoding direction |
| `TotalReadoutTime` | R | number | Total readout time in seconds |
| `EchoTime` | REC | number | TE in seconds |
| `RepetitionTime` | REC | number | TR in seconds |
| `FlipAngle` | REC | number | Flip angle in degrees |
| `EffectiveEchoSpacing` | REC | number | Effective echo spacing in seconds |
| `MultibandAccelerationFactor` | REC | number | SMS/multiband factor |
| `SliceTiming` | REC | array | Slice timing |

### DWI Gradient Files

`.bvec` file (3 rows x N columns, N = number of volumes):
```
0 0.707 -0.707 0 0.577
0 0.707 0.707 0 0.577
0 0 0 1 0.577
```

`.bval` file (1 row x N columns):
```
0 1000 1000 1000 2000
```

- b=0 volumes have zero-vectors in `.bvec`
- Gradient directions are in the image coordinate system
- Values are space-separated (not tab-separated)
- Number of columns must match number of volumes in the NIfTI

## Fieldmaps (fmap/)

### Case 1: Phase-difference map (`_phasediff`)

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `EchoTime1` | R | number | TE of the first echo (shorter) |
| `EchoTime2` | R | number | TE of the second echo (longer) |
| `IntendedFor` | R | string/array | BIDS URI(s) of files to correct |
| `B0FieldIdentifier` | REC | string | Identifier for this B0 field |

### Case 2: Two phase maps (`_phase1`, `_phase2`)

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `EchoTime` | R | number | TE for this phase image |
| `IntendedFor` | R | string/array | Files to correct |

### Case 3: Direct fieldmap (`_fieldmap`)

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `Units` | R | string | Must be `Hz` or `rad/s` |
| `IntendedFor` | R | string/array | Files to correct |

### Case 4: "Pepolar" fieldmaps (`_epi`)

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `PhaseEncodingDirection` | R | string | PE direction for this image |
| `TotalReadoutTime` | R | number | Total readout time |
| `IntendedFor` | R | string/array | Files to correct |
| `B0FieldIdentifier` | REC | string | Identifier for this B0 field |
| `B0FieldSource` | REC | string | Which B0 field to use |

### IntendedFor Syntax

**BIDS URI format** (recommended, v1.7+):
```json
{
    "IntendedFor": [
        "bids::sub-01/func/sub-01_task-rest_bold.nii.gz",
        "bids::sub-01/dwi/sub-01_dwi.nii.gz"
    ]
}
```

**Relative path format** (legacy):
```json
{
    "IntendedFor": [
        "func/sub-01_task-rest_bold.nii.gz",
        "dwi/sub-01_dwi.nii.gz"
    ]
}
```

**B0FieldIdentifier/B0FieldSource** (preferred in v1.9+):
```json
// In the fieldmap sidecar
{"B0FieldIdentifier": "pepolar_fmap0"}

// In the BOLD sidecar
{"B0FieldSource": "pepolar_fmap0"}
```

## Perfusion Imaging (perf/)

### ASL

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `ArterialSpinLabelingType` | R | string | `CASL`, `PCASL`, or `PASL` |
| `PostLabelingDelay` | R | number/array | PLD in seconds |
| `BackgroundSuppression` | R | boolean | Whether applied |
| `MagneticFieldStrength` | R | number | In Tesla |
| `M0Type` | R | string | `Separate`, `Included`, `Estimate`, `Absent` |
| `RepetitionTimePreparation` | R | number | Time between ASL pulses |
| `LabelingDuration` | R | number | Duration of labeling pulse |
| `BackgroundSuppressionNumberPulses` | REC | integer | Number of suppression pulses |
| `BackgroundSuppressionPulseTime` | REC | array | Timing of suppression pulses |
| `VascularCrushing` | REC | boolean | Whether applied |
| `LabelingOrientation` | REC | string | Orientation of labeling plane |
| `LabelingDistance` | REC | number | Distance from isocenter (mm) |
| `BolusCutOffFlag` | R (PASL) | boolean | Whether QUIPSS applied |
| `BolusCutOffTimingSequence` | R (PASL) | string | QUIPSS sequence type |
| `BolusCutOffDelayTime` | R (PASL) | number | QUIPSS delay time |

### aslcontext.tsv

Required file listing the order of volumes (label/control/m0scan):
```
volume_type
control
label
control
label
m0scan
```

## EEG (eeg/)

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `TaskName` | R | string | Name of the task |
| `SamplingFrequency` | R | number | In Hz |
| `EEGReference` | R | string | Reference electrode(s) |
| `PowerLineFrequency` | R | number | 50 or 60 Hz (or `n/a`) |
| `SoftwareFilters` | R | object | Online filters applied |
| `EEGPlacementScheme` | REC | string | e.g., `10-20`, `10-10` |
| `CapManufacturer` | REC | string | Cap manufacturer |
| `CapManufacturersModelName` | REC | string | Cap model |
| `EEGChannelCount` | REC | integer | Number of EEG channels |
| `EOGChannelCount` | REC | integer | Number of EOG channels |
| `ECGChannelCount` | REC | integer | Number of ECG channels |
| `EMGChannelCount` | REC | integer | Number of EMG channels |
| `MiscChannelCount` | REC | integer | Number of misc channels |
| `TriggerChannelCount` | REC | integer | Number of trigger channels |
| `RecordingDuration` | REC | number | In seconds |
| `RecordingType` | REC | string | `continuous`, `epoched`, `discontinuous` |

### channels.tsv (EEG)

| Column | Status | Description |
|--------|--------|-------------|
| `name` | R | Channel name |
| `type` | R | `EEG`, `EOG`, `ECG`, `EMG`, `MISC`, `TRIG`, etc. |
| `units` | R | `V`, `mV`, `uV` |
| `sampling_frequency` | OPT | Per-channel if different |
| `low_cutoff` | REC | High-pass filter frequency (Hz) |
| `high_cutoff` | REC | Low-pass filter frequency (Hz) |
| `notch` | REC | Notch filter frequency (Hz) |
| `reference` | REC | Reference electrode name |
| `status` | REC | `good` or `bad` |
| `status_description` | OPT | Reason for bad status |

### electrodes.tsv (EEG)

| Column | Status | Description |
|--------|--------|-------------|
| `name` | R | Electrode name |
| `x` | R | X coordinate |
| `y` | R | Y coordinate |
| `z` | R | Z coordinate |
| `type` | OPT | Electrode type |
| `material` | OPT | Electrode material |
| `impedance` | OPT | Impedance in kOhm |

## MEG (meg/)

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `TaskName` | R | string | Name of the task |
| `SamplingFrequency` | R | number | In Hz |
| `PowerLineFrequency` | R | number | 50 or 60 Hz |
| `DewarPosition` | R | string | Position of the dewar |
| `SoftwareFilters` | R | object | Online filters |
| `DigitizedLandmarks` | R | boolean | Fiducials digitized |
| `DigitizedHeadPoints` | R | boolean | Head shape digitized |
| `MEGChannelCount` | REC | integer | Number of MEG channels |
| `MEGREFChannelCount` | REC | integer | Reference channels |
| `ContinuousHeadLocalization` | REC | boolean | HPI on |
| `HeadCoilFrequency` | REC | array | HPI coil frequencies |
| `InstitutionName` | REC | string | Institution name |

## PET (pet/)

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `TracerName` | R | string | Name of the radiotracer |
| `TracerRadionuclide` | R | string | e.g., `C11`, `F18`, `O15` |
| `InjectedRadioactivity` | R | number | In MBq |
| `InjectedRadioactivityUnits` | R | string | Must be `MBq` |
| `InjectedMass` | R | number | Mass of tracer injected |
| `InjectedMassUnits` | R | string | e.g., `ug` |
| `ModeOfAdministration` | R | string | `bolus`, `infusion`, `bolus-infusion` |
| `TimeZero` | R | string | Time of injection (HH:MM:SS) |
| `ScanStart` | R | number | Start time relative to TimeZero |
| `InjectionStart` | R | number | Injection time relative to TimeZero |
| `FrameTimesStart` | R | array | Frame start times in seconds |
| `FrameDuration` | R | array | Frame durations in seconds |
| `Units` | R | string | Unit of voxel values (e.g., `Bq/mL`) |
| `TracerRadLex` | REC | string | RadLex ID for tracer |
| `BodyWeight` | REC | number | In kg |
| `BodyPart` | REC | string | Imaged body part |
| `AttenuationCorrection` | REC | string | Method description |
| `ReconMethodName` | REC | string | Reconstruction method |
| `ReconMethodParameterLabels` | REC | array | Parameter names |
| `ReconMethodParameterValues` | REC | array | Parameter values |
| `ReconFilterType` | REC | string | Post-recon filter type |
| `ReconFilterSize` | REC | number | Filter FWHM in mm |

## Microscopy (micr/)

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `Manufacturer` | R | string | Microscope manufacturer |
| `ManufacturersModelName` | R | string | Microscope model |
| `PixelSize` | R | array | [X, Y] or [X, Y, Z] in micrometers |
| `PixelSizeUnits` | R | string | `um` (micrometers) |
| `Magnification` | REC | number | Objective magnification |
| `SampleEnvironment` | R | string | `in vivo`, `ex vivo`, `in vitro` |
| `SampleFixation` | REC | string | Fixation method |
| `SampleStaining` | REC | string | Staining protocol |
| `SliceThickness` | REC | number | In micrometers |
| `TissueDeformationScaling` | REC | number | Scaling factor |

## NIRS (nirs/)

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `TaskName` | R | string | Name of the task |
| `SamplingFrequency` | R | number | In Hz |
| `NIRSSourceOptodeCount` | R | integer | Number of sources |
| `NIRSDetectorOptodeCount` | R | integer | Number of detectors |
| `ACCELChannelCount` | REC | integer | Accelerometer channels |
| `NIRSPlacementScheme` | REC | string | e.g., `10-20` |

## Motion (motion/)

| Field | Status | Type | Description |
|-------|--------|------|-------------|
| `TaskName` | R | string | Name of the task |
| `SamplingFrequency` | R | number | In Hz |
| `TrackingSystemName` | R | string | Name of tracking system |
| `ACCELChannelCount` | REC | integer | Accelerometer channels |
| `GYROChannelCount` | REC | integer | Gyroscope channels |
| `MAGNChannelCount` | REC | integer | Magnetometer channels |
| `RotationOrder` | REC | string | e.g., `XYZ` |
| `RotationRule` | REC | string | `left-hand` or `right-hand` |
| `SpatialAxes` | REC | string | e.g., `ALS` |
