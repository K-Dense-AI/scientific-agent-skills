# Heart-rate variability and RSA

Checked **2026-10-01** against NeuroKit2 0.2.13 stable runtime/source,
the official HRV API/tutorial, and HRV/RSA measurement guidance.

## Define the interval series

HRV analysis needs beat timing plus a defensible classification/correction policy.
Distinguish:

- **RR/RRI**: intervals between detected R peaks;
- **NN**: intervals between beats judged normal sinus beats; and
- **PP/PRV**: intervals between peripheral pulse peaks.

Do not relabel automatically corrected RR or PPG intervals as NN. Preserve raw waveform,
raw peaks, corrected peaks, excluded segments, correction categories, and interval units.

Accepted NeuroKit2 inputs include:

- a list/array of peak sample indices;
- marker/info objects from `ecg_peaks()`, `ppg_peaks()`, `ecg_process()`, or
  `bio_process()`; and
- a dict with `RRI` (milliseconds) and `RRI_Time` (seconds).

Always pass the sampling rate of the continuous signal in which peak indices were
defined.

## Current functions and schemas

```python
time = nk.hrv_time(peaks, sampling_rate=250)
frequency = nk.hrv_frequency(peaks, sampling_rate=250)
nonlinear = nk.hrv_nonlinear(peaks, sampling_rate=250)
all_domains = nk.hrv(peaks, sampling_rate=250)
```

All four return one-row DataFrames. `hrv()` concatenates the available domains and can
append RSA when its input contains processed respiration data. Columns vary with data
length, kwargs, available modalities, and release.

Pinned 0.2.13 observations:

- `hrv_time()` returned 25 columns, including `HRV_MeanNN`, `HRV_SDNN`,
  `HRV_RMSSD`, `HRV_SDSD`, `HRV_CVNN`, `HRV_CVSD`, robust interval summaries,
  `HRV_pNN50`, `HRV_pNN20`, `HRV_HTI`, and `HRV_TINN`. Long-segment indices
  (`SDANN*`, `SDNNI*`) can be NaN when duration is insufficient.
- `hrv_frequency()` returned exactly `HRV_ULF`, `HRV_VLF`, `HRV_LF`, `HRV_HF`,
  `HRV_VHF`, `HRV_TP`, `HRV_LFHF`, `HRV_LFn`, `HRV_HFn`, and `HRV_LnHF` in the
  default probe.
- `hrv_nonlinear()` returned Poincaré, asymmetry, fragmentation, DFA/MFDFA,
  entropy/fractal, Lempel–Ziv, and symbolic-dynamics columns. Stable 0.2.13 added
  default `HRV_Symbolic_EqualProb4_*` features.

Do not hard-code a “complete” HRV column list. Persist `list(result.columns)` and map
only prespecified outputs.

## Units and interval helpers

Time-domain metrics are milliseconds where applicable. For absolute band power in ms²,
use `hrv_frequency(..., normalize=False)`. The default `normalize=True` divides the
PSD by its maximum before band integration, so those powers must not be labeled ms².

```python
processed_rri, processed_time, interpolation_rate = nk.intervals_process(
    rri_ms,
    intervals_time=time_s,
    interpolate=True,
    interpolation_rate=4,
    detrend=None,
)
peaks = nk.intervals_to_peaks(rri_ms, sampling_rate=1000)
```

`intervals_process()` returns three objects: intervals in milliseconds, timestamps in
seconds, and interpolation rate. `intervals_to_peaks()` returns integer peak indices,
with a constructed first peak. Verify external-device interval definitions and dropped
beats before conversion.

## Recording duration

Duration requirements are metric-, population-, protocol-, and estimator-specific.
Use these conservative planning principles:

- Five minutes is the conventional standardized short-term HRV window.
- RMSSD can be computed on shorter windows, but ultra-short estimates require
  endpoint- and population-specific reliability/validity evidence.
- A spectral segment should contain enough cycles of the lowest frequency interpreted.
  Five minutes is a practical reference for conventional LF/HF short-term analysis.
- Do not interpret ULF from a short recording; it is conventionally associated with
  long, often 24-hour recordings.
- VLF physiological interpretation in short recordings is uncertain.
- Entropy, DFA, MFDFA, correlation dimension, and RQA need enough beats for stable
  estimation; defaults returning a number do not establish adequacy.

Do not compare metrics estimated from unequal durations without a validated strategy.
Report exact usable duration and beat count after exclusions, not nominal acquisition
duration.

## Ectopy and artifact policy

1. Inspect ECG/PPG quality and peak overlays.
2. Review the tachogram and interval histogram.
3. Identify non-sinus beats separately from detector errors when possible.
4. Report raw and corrected beat counts and percentage.
5. Limit interpolation/correction according to a prespecified exclusion rule.
6. Repeat key analyses under plausible correction choices.

`ecg_process()` requests artifact correction automatically in 0.2.13. If that is not
the planned policy, run `ecg_clean()` and `ecg_peaks()` explicitly.

Heavy correction can manufacture smooth HRV. A segment with excessive ectopy,
detachment, or motion may need exclusion rather than interpolation.

## Frequency domain

Stable signature:

```text
hrv_frequency(
  peaks, sampling_rate=1000,
  ulf=(0, 0.0033), vlf=(0.0033, 0.04),
  lf=(0.04, 0.15), hf=(0.15, 0.4), vhf=(0.4, 0.5),
  psd_method="welch", normalize=True, interpolation_rate=100, ...
)
```

Set `interpolation_rate=4` to approximate a common Kubios interpolation choice; set it
to `None` for already-interpolated intervals or Lomb–Scargle. Record detrending,
interpolation, PSD method, window/order, frequency bands, and normalization.

Stable `HRV_LFn` and `HRV_HFn` divide LF and HF by `HRV_TP`, which sums all five
requested bands (ULF, VLF, LF, HF, VHF). They are not the conventional LF/(LF+HF) and
HF/(LF+HF) definitions. Report the exact denominator rather than importing a textbook
interpretation from the column names. Zero/NaN band power does not prove absent
physiological modulation.

The bundled pipeline deliberately uses `normalize=False`, Welch, and 4 Hz
interpolation, records these choices, and gates frequency analysis on the span
between first and last corrected peaks. This span still does not certify that every
interval is usable: inspect exclusions, non-sinus beats, and correction burden.

Do **not** interpret `HRV_LFHF` as a direct “sympathovagal balance.” LF contains mixed
influences; HF depends on breathing frequency/depth and can miss respiratory variation
outside the default 0.15–0.4 Hz band.

## PPG-derived variability

PPG pulse timing includes pre-ejection and pulse-transit effects, and varies with site,
vascular state, posture, temperature, motion, contact pressure, and sensor design.
Label results PRV/PPG-derived HRV and validate against synchronized ECG for the endpoint,
conditions, sites, and population. Agreement at rest does not imply agreement during
exercise or stress.

## Respiratory sinus arrhythmia

Stable signature:

```text
hrv_rsa(
  ecg_signals, rsp_signals=None, rpeaks=None,
  sampling_rate=1000, continuous=False,
  window=None, window_number=None
)
```

Use synchronized processed ECG and respiration DataFrames:

```python
rsa = nk.hrv_rsa(
    ecg_signals,
    rsp_signals,
    rpeaks=ecg_info,
    sampling_rate=100,
    continuous=False,
)
```

The pinned summary returned a dict with P2T and Gates statistics, including
`RSA_P2T_Mean`, `RSA_P2T_SD`, `RSA_P2T_NoRSA`, `RSA_PorgesBohrer`, and Gates
mean/SD/log fields. `continuous=True` returned a same-length DataFrame with
`RSA_P2T` and `RSA_Gates`.

Requirements:

- shared clock, sampling grid, and defined lag/drift policy;
- valid R peaks and respiration cycles;
- enough cycles/windows for the chosen method;
- measured respiration rate and context; and
- reporting of P2T/Gates method and all window parameters.

RSA/HF-HRV is often related to cardiac vagal modulation but is not a direct,
context-free vagal-tone assay. Respiration, activity, beta-adrenergic influence, age,
posture, and within- versus between-person contrasts can change interpretation.

## Analysis/report checklist

- package version and observed output schema;
- ECG/PPG source, sensor/site, sampling, clock, units, and raw-data access;
- duration, usable duration, beat count, and exclusions;
- peak detector, quality method, ectopy/artifact criteria, and correction percentage;
- RRI/NN/PRV terminology;
- PSD/interpolation/detrending/bands/normalization;
- respiration measurement and rate/depth context;
- prespecified metrics and multiplicity control; and
- no diagnostic, monitoring, or medical-device claim without separate validation.

## Sources checked 2026-10-01

- [Official HRV API](https://neuropsychology.github.io/NeuroKit/functions/hrv.html)
- [Official HRV example](https://neuropsychology.github.io/NeuroKit/examples/ecg_hrv/ecg_hrv.html)
- [Pham et al. (2021), NeuroKit2 HRV review/tutorial](https://doi.org/10.3390/s21123998)
- [Quigley et al. (2024), current SPR HR/HRV guidelines](https://doi.org/10.1111/psyp.14604)
- [ESC/NASPE Task Force (1996)](https://pubmed.ncbi.nlm.nih.gov/8598068/)
- [Berntson et al. (1997), interpretive caveats](https://doi.org/10.1111/j.1469-8986.1997.tb02140.x)
- [Laborde et al. (2017), planning/reporting](https://doi.org/10.3389/fpsyg.2017.00213)
- [Grossman & Taylor (2007), RSA caveats](https://doi.org/10.1016/j.biopsycho.2005.11.014)

- [Stable `hrv_frequency.py` implementation](https://github.com/neuropsychology/NeuroKit/blob/v0.2.13/neurokit2/hrv/hrv_frequency.py)
