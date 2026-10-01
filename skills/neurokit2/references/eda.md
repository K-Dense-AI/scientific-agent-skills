# Electrodermal activity

Checked **2026-10-01** against NeuroKit2 0.2.13 stable runtime/source,
the official EDA API/examples, and Society for Psychophysiological Research guidance.

## Measurement contract

Record:

- conductance versus resistance, physical unit, range, and calibration;
- constant-voltage/current system and electrode material/area;
- palmar/plantar or other site, laterality, placement, and skin preparation;
- sampling rate, hardware filters, temperature, humidity, acclimation, and movement;
- missing/detached/saturated intervals; and
- participant/task factors and response definition.

Do not infer microsiemens from `EDA` or compare arbitrary sensor units with published
µS thresholds. Sensor site, hardware, environment, and population require validation.

## Default stable pipeline

```python
signals, info = nk.eda_process(
    eda,
    sampling_rate=100,
    method="neurokit",
)
```

In stable 0.2.13 the NeuroKit pipeline performs cleaning, **high-pass**
tonic/phasic decomposition, and NeuroKit SCR detection. It does not use cvxEDA by
default.

The pinned default schema observed:

```text
EDA_Raw, EDA_Clean, EDA_Tonic, EDA_Phasic,
SCR_Onsets, SCR_Peaks, SCR_Height, SCR_Amplitude,
SCR_RiseTime, SCR_Recovery, SCR_RecoveryTime
```

`info` was a flat dict containing SCR arrays plus `sampling_rate`. Treat this as a
default 0.2.13 observation, not a universal schema.

There is no public `eda_quality()` in stable 0.2.13. Quality must combine acquisition
metadata, missing/flat/clipped/motion checks, raw/clean overlays, decomposition
plausibility, and response review.

## Make decomposition explicit

```python
clean = nk.eda_clean(eda, sampling_rate=100, method="neurokit")
components = nk.eda_phasic(
    clean,
    sampling_rate=100,
    method="highpass",
)
```

`eda_clean()` options include `neurokit`, `biosppy`, and `none`. The NeuroKit path
uses a 3 Hz low-pass, and skips it below 7 Hz.

`eda_phasic()` returns a DataFrame with `EDA_Tonic` and `EDA_Phasic`. Methods include:

- `highpass`: default stable method; phasic high-pass separation;
- `smoothmedian`: median-smoothed tonic estimate;
- `cvxeda`: convex optimization; needs optional `cvxopt`;
- `sparseda`: sparse decomposition.

These methods estimate different latent components and are not interchangeable.
Report method, all kwargs, optional dependency versions, convergence/failure behavior,
and sensitivity. Do not call one decomposition “physiologically true” without
appropriate validation.

## SCR detection

```python
markers, peak_info = nk.eda_peaks(
    components["EDA_Phasic"],
    sampling_rate=100,
    method="neurokit",
    amplitude_min=0.1,
)
```

Stable methods include `neurokit`, `gamboa2008`, `kim2004`, `vanhalem2020`, and
`nabian2018`. For `neurokit` and `kim2004`, `amplitude_min` is a fraction relative to
the largest detector-specific candidate in the analyzed signal—not an absolute µS
threshold. In stable source, `neurokit` thresholds peak prominence, whereas `kim2004`
thresholds phasic peak height. Neither is a common absolute onset-to-peak amplitude
cutoff. Other supported methods ignore `amplitude_min`.

`eda_peaks()` returns `(signals, info)`:

- marker/feature DataFrame: `SCR_Onsets`, `SCR_Peaks`, `SCR_Height`,
  `SCR_Amplitude`, `SCR_RiseTime`, `SCR_Recovery`, `SCR_RecoveryTime`;
- info dict: event-indexed arrays and sampling rate.

Marker columns are same-length arrays; feature values are placed at relevant marker
locations and are otherwise **zero**, not missing, in stable 0.2.13. Invalid feature
values at a detected response can still be NaN. Use `info` for event-level arrays. Do not average
same-length feature columns as if every sample were an independent response.

`eda_fixpeaks()` is documented as a placeholder that does not currently correct EDA
peaks.

## Missingness and artifacts

EDA motion/electrode artifacts can resemble fast responses, while detachment can look
flat. Before decomposition:

1. inspect raw units, range, clipping, steps, flatlines, and missing runs;
2. segment long discontinuities;
3. annotate motion, temperature changes, and contact problems;
4. avoid broad interpolation across SCR morphology; and
5. keep an artifact/validity mask through epoching.

Filtering cannot restore a detached or saturated channel. A low response count can be
physiological, methodological, or a sensor failure; it is not automatically a
“non-responder.”

## Event-related EDA

Create epochs only after event and signal clocks are aligned:

```python
epochs = nk.epochs_create(
    signals,
    events,
    sampling_rate=100,
    epochs_start=-1,
    epochs_end=10,
    baseline_correction=False,
)
features = nk.eda_eventrelated(epochs)
```

Stable event-related output is conditional on available columns. Documented features
include `EDA_SCR`, first-response amplitude/time/rise/recovery fields, tonic/phasic
summaries, labels, conditions, and event onset. Inspect `features.columns`.

Prespecify response latency/window, overlap handling, baseline approach, minimum
amplitude definition, non-response coding, and trial artifact rules. Slow responses can
overlap adjacent events; a peak in a window is not automatically elicited by that event.

## Interval analysis and sympathetic index

```python
features = nk.eda_intervalrelated(signals, sampling_rate=100)
```

The pinned official example showed six columns, including SCR count/amplitude,
`EDA_Tonic_SD`, `EDA_Sympathetic`, `EDA_SympatheticN`, and
`EDA_Autocorrelation`; output depends on duration and available columns.

`eda_sympathetic()` supports `posada` and `ghiasi`, with a default 0.045–0.25 Hz
band. Stable `posada` returns NaN when duration is **64 seconds or less**, despite a
warning referring to 60 seconds. `ghiasi` uses 60-second STFT windows with 59-second
overlap. The helper conservatively requires more than 64 seconds for either method;
this is a software guard, not a universal validity threshold. Report exact usable
duration, frequency band, estimator, normalization, and
units. Do not turn this index into a direct clinical sympathetic-state measure.

## Bounded pipeline

```bash
python skills/neurokit2/scripts/eda_pipeline.py \
  --input deidentified.csv --column EDA --root . --deidentified \
  --sampling-rate 100 --unit uS \
  --clean-method neurokit --phasic-method highpass \
  --peak-method neurokit --amplitude-min 0.1
```

The helper rejects missing/non-finite samples, records the observed schema, and makes
decomposition/threshold semantics explicit.

Only `neurokit` and `kim2004` apply `--amplitude-min`; the report marks it inactive
for other detectors. Synthetic generation passes both duration and integer sample
count: supplying `length` alone does not update NeuroKit2's default 10-second time
axis, drift, or SCR placement. Flat/no-response inputs can raise a detector error;
do not reinterpret that failure as a validated physiological zero-response count.

## Interpretation boundary

EDA indexes eccrine sweat-gland activity under the recording conditions. It does not
uniquely identify stress, emotion, deception, pain, diagnosis, or intent. Compare
within a theory-driven design with contextual measures and validated preprocessing.
Do not use this workflow for clinical/driver/workplace monitoring or medical-device
validation.

## Sources checked 2026-10-01

- [Official EDA API](https://neuropsychology.github.io/NeuroKit/functions/eda.html)
- [Official SCR example](https://neuropsychology.github.io/NeuroKit/examples/eda_peaks/eda_peaks.html)
- [Stable v0.2.13 EDA source](https://github.com/neuropsychology/NeuroKit/tree/v0.2.13/neurokit2/eda)
- [SPR Ad Hoc Committee (2012), publication recommendations](https://doi.org/10.1111/j.1469-8986.2012.01384.x)
- [Greco et al. (2016), cvxEDA](https://doi.org/10.1109/TBME.2015.2474131)
- [NeuroKit2 main paper](https://doi.org/10.3758/s13428-020-01516-y)

- [Stable `eda_simulate.py` implementation](https://github.com/neuropsychology/NeuroKit/blob/v0.2.13/neurokit2/eda/eda_simulate.py)
