# BIDS Metadata Fields Reference

Reviewed against [BIDS 1.11.2](https://bids-specification.readthedocs.io/en/stable/)
on 2026-09-30. This is a practical selection, not a complete validator. The bundled
`bids_schema.json` contains field definitions under `objects.metadata`, conditional
requirements under `rules.sidecars`, and cross-file checks under `rules.checks`.
A field can be required only for a particular suffix, acquisition, or dataset context.
Read selectors before interpreting a rule; do not merge every modality's requirements.
Required metadata may be inherited from matching higher-level sidecars.

## MRI: units, timing and orientation

Use seconds for MRI timing fields, degrees for `FlipAngle`, and tesla for
`MagneticFieldStrength`. Convert DICOM millisecond values; do not copy units blindly.
`Manufacturer`, `ManufacturersModelName`, scanner/software identifiers and institution
fields are generally recommended. Check `rules.sidecars.mri` for exceptions, including
ASL and concurrent PET requirements.

- Anatomical MRI: `EchoTime` and `FlipAngle` are generally recommended;
  `RepetitionTimeExcitation` and `RepetitionTimePreparation` are available where applicable.
  Do not present one mandatory qMRI field set for all anatomical suffixes.
- BOLD: `TaskName` is required. It need not equal or be derived from the `task-` label.
  Specify **either** `RepetitionTime` **or** `VolumeTiming`, never both.
  With `VolumeTiming`, provide `SliceTiming` or `FrameAcquisitionDuration`;
  `DelayTime` is not used with `VolumeTiming`. Sparse sequences need the additional
  timing information described in the [MRI timing table](https://bids-specification.readthedocs.io/en/stable/modality-specific-files/magnetic-resonance-imaging-data.html#timing-parameters).
- `EchoTime` is required for multi-echo data, ASL, or where the stated fieldmap
  conditions apply. With an `echo-` entity, record that echo's actual time, not its index.
- `PhaseEncodingDirection` uses NIfTI voxel axes `i`, `j`, `k` with optional `-`.
  Anatomical AP/PA/LR labels do not determine the axis or sign without the affine and
  converter orientation. Verify scanner metadata and image orientation together.
- `PhaseEncodingDirection` and `TotalReadoutTime` are recommended for DWI/BOLD and
  become required under specified fieldmap/opposing-encoding conditions. For pepolar
  `_epi` images, readout timing must be supplied or calculable through supported metadata.
  `EffectiveEchoSpacing` alone is not numerically interchangeable with total readout time.
- `SliceTiming` contains acquisition offsets in seconds, indexed by slice (reversed
  relative to slice index when `SliceEncodingDirection` is negative). It is not a list
  of slice indices. The list length must match the slice dimension. Never infer offsets
  from TR and slice order without accounting for multiband acquisition and dead time.

Illustrative odd-first order 1,3,5,2,4,6 with TR=2 s, equal spacing, no dead time and
positive slice encoding direction:

```json
{"SliceTiming": [0.0, 1.0, 0.333, 1.333, 0.667, 1.667]}
```

qMRI requirements are suffix-specific (`rules.sidecars.qmri`): VFA requires
`FlipAngle`, `PulseSequenceType`, and `RepetitionTimeExcitation`; MP2RAGE additionally
requires `InversionTime`, `RepetitionTimePreparation`, `NumberShots`, and field strength.
`MTState` is required for MT collections, not universally for every quantitative map.
The spelling is **`RepetitionTimePreparation`**.

## Diffusion gradients

Store `.bvec` as 3 rows × N columns and `.bval` as 1 row × N columns, with N equal to
stored image volumes. Use space-separated numbers. b=0 volumes have zero vectors;
diffusion-weighted vectors should be unit length. Preserve dcm2niix's FSL/BIDS image
coordinate convention and verify gradients after any image reorientation (including
the x-component handedness convention); scanner anatomical directions are insufficient.
See the [DWI specification](https://bids-specification.readthedocs.io/en/stable/modality-specific-files/magnetic-resonance-imaging-data.html#diffusion-imaging-data).

## Fieldmaps and association

| Acquisition | Required core fields | Additional checks |
|---|---|---|
| `_phasediff` | `EchoTime1`, `EchoTime2` | Shorter echo first; matching magnitude image |
| `_phase1` / `_phase2` | `EchoTime` per image | Verify echo pairs and magnitude association |
| `_fieldmap` | `Units` | `Hz`, `rad/s`, or `T`; retain actual physical units |
| `_epi` pepolar | `PhaseEncodingDirection` | Readout time or supported inputs to calculate it; complementary encoding scans |

`IntendedFor` is optional for fieldmaps, not universally required. Use meaningful
associations for processing: `B0FieldIdentifier` defines a field estimate and
`B0FieldSource` on a target selects it; `IntendedFor` remains supported. Check the
pipeline's support before choosing the association method.

Fieldmap JSON example for a target in the same raw dataset:

```json
{
  "B0FieldIdentifier": "pepolar_fmap0",
  "IntendedFor": ["bids::sub-01/func/sub-01_task-rest_bold.nii.gz"]
}
```

Target BOLD JSON addition:

```json
{"B0FieldSource": "pepolar_fmap0"}
```

`bids::` is relative to the nearest dataset root, including a derivative's own root.
For cross-dataset sources, use a named BIDS URI and `DatasetLinks`. Legacy subject-relative
`IntendedFor` paths are deprecated. See [BIDS URI resolution](https://bids-specification.readthedocs.io/en/stable/common-principles.html#resolution-of-bids-uris).

## ASL

For `_asl`, core requirements include `ArterialSpinLabelingType` (`CASL`, `PCASL`,
`PASL`), `PostLabelingDelay`, `BackgroundSuppression`, `M0Type`,
`RepetitionTimePreparation`, `TotalAcquiredPairs`, `MagneticFieldStrength`,
`MRAcquisitionType`, and `EchoTime`. Also provide `_aslcontext.tsv` with one volume
label per stored volume, and verify the M0 acquisition/estimate relation.

- CASL/PCASL requires `LabelingDuration`; it is not a universal PASL field.
- PASL requires `BolusCutOffFlag`; when true, also supply `BolusCutOffDelayTime`
  and **`BolusCutOffTechnique`**.
- `M0Type: "Estimate"` requires `M0Estimate`; a separate `_m0scan` has an `IntendedFor` requirement.
- 2D ASL requires `SliceTiming`. Suppression pulse count/times are recommended when
  background suppression is true.

Use the full [ASL specification](https://bids-specification.readthedocs.io/en/stable/modality-specific-files/magnetic-resonance-imaging-data.html#arterial-spin-labeling-perfusion-data)
for acquisition-specific conditions and per-volume arrays.

## Electrophysiology

| Datatype | Core required JSON fields for task recordings |
|---|---|
| EEG | `TaskName`, `SamplingFrequency`, `EEGReference`, `PowerLineFrequency`, `SoftwareFilters` |
| iEEG | `TaskName`, `SamplingFrequency`, `iEEGReference`, `PowerLineFrequency`, `SoftwareFilters` |
| MEG | `TaskName`, `SamplingFrequency`, `PowerLineFrequency`, `DewarPosition`, `SoftwareFilters`, `DigitizedLandmarks`, `DigitizedHeadPoints` |
| EMG | `TaskName`, `EMGPlacementScheme`, `EMGReference`, `SamplingFrequency`, `PowerLineFrequency`, `RecordingType`, `SoftwareFilters` |

`PowerLineFrequency` accepts a numeric frequency or `"n/a"`; `SoftwareFilters` accepts
a filter-description object or `"n/a"` under its field definition. EMG needs
`EMGPlacementSchemeDescription` when the scheme is `"Other"` and `EpochLength` for
epoched recordings. iEEG requires electrode/coordinate metadata; do not conflate
channels (recorded signals) with electrodes (physical contacts).

For EEG channels, `name`, `type`, and `units` are required columns. Coordinate units
and coordinate-system identifiers belong in matching `coordsystem.json`. Consult the
modality's rules for which companion files are required, recommended or conditional.
BrainVision datasets need the complete `.vhdr`, `.vmrk`, `.eeg` triplet with valid links.
Use `MiscChannelCount`; `MISCChannelCount` is a deprecated alias for EEG/motion.

Official modality pages: [EEG](https://bids-specification.readthedocs.io/en/stable/modality-specific-files/electroencephalography.html),
[iEEG](https://bids-specification.readthedocs.io/en/stable/modality-specific-files/intracranial-electroencephalography.html),
[MEG](https://bids-specification.readthedocs.io/en/stable/modality-specific-files/magnetoencephalography.html),
[EMG](https://bids-specification.readthedocs.io/en/stable/modality-specific-files/electromyography.html).

## PET

PET metadata is substantially richer than tracer name and frame timing. Required
raw `_pet` fields cover hardware (`Manufacturer`, `ManufacturersModelName`, `Units`),
radiochemistry (including `SpecificRadioactivity` and its units), timing, and
reconstruction (`AcquisitionMode`, decay correction fields, reconstruction method,
parameter labels, filter type, and attenuation correction). Conditional reconstruction
parameter values/units, filter sizes and infusion fields must also be satisfied.
Use `rules.sidecars.pet` and the [PET specification](https://bids-specification.readthedocs.io/en/stable/modality-specific-files/positron-emission-tomography.html)
for the full inventory; a small example is not a complete PET sidecar.

`TimeZero` defines the reference clock time and is not necessarily injection time.
`ScanStart`, `InjectionStart` and frame timing use the documented relation to that
reference. State measured activity and mass units explicitly; do not relabel numeric
values as MBq without conversion. `ReconFilterSize` accepts a number or an array under its definition.
Blood recordings have separate required columns and availability/correction fields.

## Microscopy, NIRS, motion and spectroscopy

| Datatype | Core metadata and caveats |
|---|---|
| Microscopy | `PixelSize` and `PixelSizeUnits` are required for non-photo microscopy images. `PixelSize` is a two- or three-number array; `PixelSizeUnits` is `"mm"`, `"um"`, or `"nm"`. Manufacturer/model and `SampleEnvironment` are recommended. Validate embedded OME metadata and image dimensions. |
| NIRS | `TaskName`, `SamplingFrequency`, `NIRSChannelCount`, `NIRSSourceOptodeCount`, `NIRSDetectorOptodeCount`; additional channel counts are conditional on channel type. Include channel/optode/coordinate companions according to the rules. |
| Motion | `TaskName` and `SamplingFrequency` are required; `TrackingSystemName` is optional. Spatial-axis/rotation descriptions belong to the coordinate-system rules, not an invented universal motion sidecar requirement. |
| MRS | `ResonantNucleus`, `SpectrometerFrequency`, `SpectralWidth`, and `EchoTime`; NIfTI-MRS also carries a header extension. A `voi-` entity requires body-part metadata. Verify nucleus/frequency arrays and acquisition-specific dimensions. |

Load `rules.sidecars.micr`, `.nirs`, `.motion`, or `.mrs` and corresponding
`objects.metadata` definitions rather than copying scalar types across modalities.
BIDS 1.11.2 adds OME-Zarr imaging support; confirm actual consumer support separately.

## Events and validation

`onset` and `duration` are the first two columns of `_events.tsv`. Times are seconds
relative to the first **stored** data point; negative onset values are allowed.
A zero duration denotes an impulse; `n/a` denotes an unavailable duration.
`trial_type` and `response_time` are optional. Sort rows by onset and describe custom
columns in JSON. Resting-state tasks do not necessarily have recorded events.

Run the full validator including image-header checks. Validation establishes structural
and metadata conformance, not the correctness of acquisition values, gradient orientation,
fieldmap selection, deidentification, or scientific preprocessing choices.
