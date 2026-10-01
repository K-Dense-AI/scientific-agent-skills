# Signal processing (pyOpenMS 3.6.0)

## Decide what the signal represents

Use `spec.getType()` and acquisition/conversion provenance. Its enum is
`ms.SpectrumSettings.SpectrumType.PROFILE`, `CENTROID`, or `UNKNOWN`.
`isSorted()` tests m/z ordering only. `getType(True)` can estimate type from the
signal when metadata is insufficient, but an estimate is not acquisition proof.

`process_spectra.py` applies smoothing, picking, normalization, S/N filtering,
then intensity thresholding to selected MS levels; chromatograms pass through.
It rejects centroid spectra for smoothing/picking and requires
`--assume-profile` for independently verified unknown-type spectra.
The native tests check a synthetic Gaussian profile, selected-level isolation,
metadata/peak-array retention and writeback of filtered spectra.

```bash
python scripts/process_spectra.py profile.mzML picked.mzML --ms-level 1 --pick
python scripts/process_spectra.py spectra.mzML scaled.mzML --ms-level 2 --normalize to_one --threshold 0.01
```

These are file-dependent templates. Parameters need representative instrument
QC; smoothing can distort narrow peaks. `PeakPickerHiRes` is for well sampled
high-resolution profile peaks. Do not repeatedly centroid already picked data.

## API patterns

```python
import pyopenms as ms
import numpy as np
spec = ms.MSSpectrum()
spec.setType(ms.SpectrumSettings.SpectrumType.PROFILE)
mz = np.linspace(499.9, 500.1, 101)
spec.set_peaks((mz, 1000 * np.exp(-0.5 * ((mz - 500) / 0.01) ** 2)))
spec.sortByPosition()
picker = ms.PeakPickerHiRes()
picked = ms.MSSpectrum()
picker.pick(spec, picked)
assert len(picked) == 1
assert abs(picked[0].getMZ() - 500) < 0.001
```

`GaussFilter.filter(spec)` uses `gaussian_width` in m/z units for a
spectrum; `use_ppm_tolerance` selects `ppm_tolerance` instead. Chromatogram
widths use seconds. The 3.6 `filterSpectrum` compatibility alias is broken for these two smoothers;
use their native `filter(spec)` method. `SavitzkyGolayFilter` uses a point-count `frame_length` and
`polynomial_order`; validate sampling regularity and window size.
`PeakPickerIterative` has `signal_to_noise_`, `peak_width`, and
`nr_iterations_` parameters; this alternative was signature/parameter checked,
not benchmarked on low-resolution instrument data.

Normalization (`Normalizer.filterSpectrum`) supports `to_one` and `to_TIC`.
Thresholds afterwards are on normalized intensities; a threshold of 10 after
unit-TIC normalization removes all nonnegative peaks. Within-scan normalization
usually destroys the abundance information needed for label-free quantification.

For filtering, use `spec.select(indices)` to keep float/integer/string data
arrays synchronized. `set_peaks()` alone does not filter associated arrays.
Spectra read with `getSpectrum`, indexing or iteration may be copies: explicitly
replace the full spectrum list with `exp.setSpectra(processed)`.

## Other algorithms and alignment

`ThresholdMower`, `WindowMower`, `NLargest`, and `MorphologicalFilter` expose
parameters through `getParameters()`; inspect their installed `filterSpectrum`
signatures before use. Their particular noise/baseline assumptions are not
validated by a successful call. For `SpectraMerger`, block-wise merging uses
`block_method:*` options; setting `average_gaussian:*` while calling
`mergeSpectraBlockWise` does not configure Gaussian averaging.

`Deisotoper.deisotopeAndSingleCharge` acts on a sorted centroided spectrum;
record tolerance units, charge range, isotope count, and whether intensity is
summed or masses are converted to singly charged ions. This is not calibration.
For feature deconvolution use a `FeatureMap` and `FeatureDeconvolution.compute`
with output map/groups/edges; there is no `potential_charge_states` parameter.

For RT alignment, call `aligner.setReference(reference_map)`,
`aligner.align(sample_map, trafo)`, then
`MapAlignmentTransformer().transformRetentionTimes(sample_map, trafo, True)`.
See the feature reference and bundled alignment script. Retention alignment
does not correct mass errors.

## Calibration: verified signature, illustrative workflow

`InternalCalibration.calibrate(exp, reference_masses)` is not a valid API.
First collect calibrants using `fillCalibrants`, then fit/apply a model. The
following is a template requiring independently established ion m/z values and
a representative run; it was not validated on instrument data:

```python
calibration = ms.InternalCalibration()
locks = [ms.InternalCalibration_LockMass(500.0, 1, 1),
         ms.InternalCalibration_LockMass(1000.0, 1, 1)]
found, failed = calibration.fillCalibrants(exp, locks, 20.0, False, False, False)
if found < 2:
    raise ValueError("Insufficient calibrants; do not fit")
ok = calibration.calibrate(exp, [1], ms.MZTrafoModel.MODELTYPE.LINEAR,
                           -1.0, False, 5.0, 5.0)
if not ok:
    raise ValueError("Calibration residual criteria failed")
```

Lock masses include adducts and require correct MS level and charge. Two points
are merely a minimal algebraic requirement for a line; use adequate mass/RT
coverage, independent validation ions, outlier diagnostics, isotope checks and
before/after ppm residuals. Do not calibrate on unverified accurate-mass database
candidates and then use the reduced error as independent identification evidence.
Negative `rt_chunk` selects one global model; positive windows are seconds.
R is needed only for requested calibration plot output, not this no-plot template.

Sources: [InternalCalibration release source](https://github.com/OpenMS/OpenMS/blob/5d5cbff4053b281763a1a79bf69e81c27967cfdf/src/openms/include/OpenMS/PROCESSING/CALIBRATION/InternalCalibration.h),
[OpenMS changes](https://openms.de/documentation/html/ChangeLog.html), and installed
3.6.0 binding docstrings/defaults.
