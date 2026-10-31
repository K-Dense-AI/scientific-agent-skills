# General signal processing

Checked **2026-10-01** against NeuroKit2 0.2.13, its stable wheel, tagged
source, and the live signal API page (`0.2.13.dev214`).

## Start with a signal contract

For every channel retain:

- sensor/channel identity and physical unit;
- native sampling rate and timestamps;
- polarity, gain, acquisition filters, and ADC range;
- missing/discontinuous intervals and artifact annotations;
- expected physiological bandwidth; and
- the exact NeuroKit2 function, method, parameters, and package version.

`signal_sanitize()` does **not** clean artifacts or interpolate missing values. In
0.2.13 it resets an indexed pandas Series to a default index.

## Safe preprocessing order

1. Preserve the original samples and time axis.
2. Check timestamp order, rate, clipping, flatlines, non-finite values, and gaps.
3. Split at long gaps. Interpolate only short, prespecified gaps and retain a mask.
4. Remove offsets/trends only when justified.
5. Apply a modality/method-specific filter at the native rate.
6. Trim or flag filter transients.
7. Detect/correct peaks or derive features.
8. Resample continuous outputs only when alignment or modeling requires it.

Do not use a filter to “fix” clipping, sensor detachment, dropped packets, or motion.
Do not interpolate event markers, quality flags, or peak indicator vectors as
continuous amplitudes.

## Verified 0.2.13 interfaces

| Function | Stable behavior relevant to schemas |
|---|---|
| `signal_filter()` | Returns one array. Default is order-2 Butterworth; available behavior depends on `method`, cutoffs, and sampling rate. |
| `signal_sanitize()` | Resets pandas Series indexing; it is not a NaN/artifact cleaner. |
| `signal_fillmissing()` | Forward, backward, or both-direction fill only (`method="forward"`, `"backward"`, or `"both"`). |
| `signal_resample()` | Returns one array; accepts target length or source/target rates. Methods include interpolation, FFT, polyphase, NumPy, and pandas paths. |
| `signal_interpolate()` | Returns interpolated values; explicitly provide source and target coordinates for irregular time. |
| `signal_findpeaks()` | Returns a dict. The pinned default synthetic probe observed `Peaks`, `Height`, `Distance`, `Onsets`, `Offsets`, and `Width`; keys can change with input/method. |
| `signal_fixpeaks()` | Returns `(info, corrected_peaks)` in stable source. Default Kubios `info` includes artifact categories and diagnostics. |
| `signal_period()` | Takes peak locations and returns period in seconds, optionally interpolated to a requested sample length. |
| `signal_rate()` | Takes peak locations and returns events/minute, optionally interpolated. |
| `signal_psd()` | Returns a DataFrame; the pinned Welch probe observed `Frequency` and `Power`. |
| `signal_power()` | Returns a one-row DataFrame with band-derived names such as `Hz_0.5_2`; names depend on requested bands. |
| `signal_timefrequency()` | Returns `(frequency, time, representation)`; frequency is the first object. |
| `signal_synchrony()` | Returns an array; supported methods are Hilbert phase synchrony and rolling correlation. |
| `signal_decompose()` | Returns a component array; stable methods are EMD and SSA, not a component dictionary. |
| `signal_changepoints()` | Implements PELT and returns change-point sample indices. |

Never unpack `signal_psd()` into `(psd, frequencies)` in 0.2.13:

```python
psd = nk.signal_psd(
    signal,
    sampling_rate=250,
    method="welch",
    normalize=False,
    show=False,
)
frequency_hz = psd["Frequency"]
power = psd["Power"]
```

`normalize=True` scales by maximum PSD power. It is not physical calibration. Use
`normalize=False` when absolute spectral units are required and derive those units from
the acquisition and estimator.

## Filtering and resampling

Cutoffs are in Hz and must lie below Nyquist. Report:

- filter family and implementation (`butterworth`, FIR, Savitzky–Golay, powerline);
- order, low/high cutoff, notch frequency, and whether processing is zero phase;
- padding/edge handling and samples discarded; and
- source and target sampling rates plus resampling method.

Example:

```python
filtered = nk.signal_filter(
    signal,
    sampling_rate=250,
    lowcut=0.5,
    highcut=40,
    method="butterworth",
    order=2,
)
resampled = nk.signal_resample(
    filtered,
    sampling_rate=250,
    desired_sampling_rate=100,
    method="poly",
)
```

Downsampling requires anti-alias filtering. In 0.2.13 the default `interpolation`
method uses spline interpolation (`scipy.ndimage.zoom`), not an anti-alias low-pass
filter. Use a suitable explicit filter before decimation or a validated filtered
resampler such as `poly`; check attenuation above the new Nyquist frequency.
Resampling cannot recover timing precision or
bandwidth absent from the acquisition. For multimodal data, preserve native processing
and timestamps first; choose a common grid only after clock alignment.

## Missing data

Forward/backward fill can create artificial constant segments. Generic interpolation can
create smooth but fictional morphology and peaks. Record:

- count and maximum run of missing samples;
- gap durations in seconds;
- whether each gap was segmented, excluded, padded, or interpolated;
- interpolation method and maximum allowed gap; and
- whether downstream quality and uncertainty include the imputed mask.

Most modality pipelines may warn and internally forward-fill some missing samples. That
convenience is not a study-level missing-data policy.

## Peak correction

```python
info, corrected = nk.signal_fixpeaks(
    peaks,
    sampling_rate=250,
    method="Kubios",
    iterative=True,
)
```

The Kubios/Lipponen–Tarvainen path is intended for ECG/PPG beats. `method="neurokit"`
supports explicit interval limits and can be used more generically. Always retain raw
and corrected peaks, counts by artifact category, affected time ranges, and results with
and without correction. Do not call corrected beat intervals “normal-to-normal” unless
the study actually identifies non-sinus/ectopic beats.

## Quality and reproducibility

Useful QC is multimodal and method-specific:

- raw/clean overlays and filter-edge review;
- missing, flatline, clipping, and saturation fractions;
- peak/onset overlays and interval distributions;
- quality values with their method-specific direction and scale;
- sensitivity to plausible filter/detector settings; and
- synthetic fixtures plus labeled empirical validation data.

The bundled inspector is dependency-free:

```bash
python skills/neurokit2/scripts/inspect_signal.py \
  --input signal.csv --root . --deidentified \
  --columns ECG --time-column time_s --units ECG=mV
```

## Sources checked 2026-10-01

- [Official signal API](https://neuropsychology.github.io/NeuroKit/functions/signal.html)
- [Stable v0.2.13 source tag](https://github.com/neuropsychology/NeuroKit/tree/v0.2.13/neurokit2/signal)
- [NeuroKit2 main paper](https://doi.org/10.3758/s13428-020-01516-y)
- [Lipponen & Tarvainen (2019), peak correction](https://doi.org/10.1080/03091902.2019.1640306)
