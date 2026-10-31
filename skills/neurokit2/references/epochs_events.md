# Events and epochs

Checked **2026-10-01** against NeuroKit2 0.2.13 stable source/runtime and
the live Events and Epochs API pages.

## Event coordinate contract

Choose one canonical representation before analysis:

- absolute time with a named clock and unit;
- zero-based sample index on a named stream; and
- event duration and condition/label metadata.

`events_find()` uses zero-based sample positions. Its `start_at`, `end_at`,
`duration_min`, `duration_max`, and `inter_min` arguments are sample counts, not
seconds.

```python
events = nk.events_find(
    trigger,
    threshold=0.5,
    threshold_keep="above",
    duration_min=2,
    inter_min=5,
    event_conditions=["A", "B", "A"],
)
```

Stable signature:

```text
events_find(
  event_channel, threshold="auto", threshold_keep="above",
  start_at=0, end_at=None, duration_min=1, duration_max=None,
  inter_min=0, discard_first=0, discard_last=0,
  event_labels=None, event_conditions=None
)
```

The default return is a dict containing `onset`, `duration`, and `label`; optional
conditions use the singular key `condition`. Multi-channel input can add
`events_channel` and generates conditions from the digital combination.

Do not infer trigger semantics from amplitude alone. Verify polarity, threshold,
debouncing, pulse width, dropped triggers, device latency, and whether simultaneous
digital inputs are encoded as expected.

## Build events explicitly when possible

```python
events = nk.events_create(
    event_onsets=[1000, 2500, 4000],
    event_durations=[100, 100, 100],
    event_labels=["1", "2", "3"],
    event_conditions=["A", "B", "A"],
)
```

Labels must be unique. Keep experimental trial IDs outside participant-identifying
names.

## `epochs_create()` semantics in 0.2.13

```text
epochs_create(
  data, events=None, sampling_rate=1000,
  epochs_start=0, epochs_end="from_events",
  event_labels=None, event_conditions=None,
  baseline_correction=False
)
```

- `epochs_start` and `epochs_end` are seconds relative to each event.
- The data slice is `[start_sample, end_sample)` (end-exclusive).
- Each epoch is a DataFrame in a dict keyed by label.
- The original sample coordinate is stored in `Index`.
- The DataFrame index is rebuilt with `numpy.linspace(..., endpoint=True)`, so the
  displayed last index equals `epochs_end` even though the end sample is excluded.
- `Label` and optional `Condition` are added as columns.
- Events near a boundary are padded by internal buffers. Floating columns receive
  NaN; integer columns can receive zero because of dtype preservation.

The pinned probe for one signal, `-0.2` to `0.5` s at 100 Hz, produced 70 rows with
an index from exactly `-0.2` through `0.5`. Do not derive sample count from that
floating index. Use `Index`, the known sampling rate, and explicit half-open bounds.

## Boundary policy

Decide before analysis:

- `drop`: remove incomplete trials and report condition-wise counts;
- `pad`: retain them with an explicit validity mask; or
- `error`: stop and repair event/window definitions.

Do not let NaN padding or integer zero padding silently become a physiological
baseline. The dependency-free planner reports affected trials:

```bash
python skills/neurokit2/scripts/plan_epochs.py \
  --events 1000,2500,4000 --event-unit samples \
  --sampling-rate 100 --recording-samples 5000 \
  --epoch-start -0.2 --epoch-end 0.8 \
  --baseline-start -0.2 --baseline-end 0
```

For events supplied in seconds, use `--event-unit seconds`; the planner rejects
onsets/windows that do not map exactly to samples.

## Baseline correction

`baseline_correction=True` subtracts the mean from epoch start through `t=0`
(inclusive in the rebuilt time index). If the epoch starts after zero, it uses the
epoch start. The operation is applied broadly to numeric columns present at that
point, including marker/index columns.

Prefer selective, manual correction:

```python
epochs = nk.epochs_create(
    processed,
    events,
    sampling_rate=100,
    epochs_start=-0.2,
    epochs_end=0.8,
    baseline_correction=False,
)

amplitude_columns = ["EDA_Phasic"]
onsets_by_label = dict(zip(events["label"], events["onset"]))
for label, epoch in epochs.items():
    relative_samples = epoch["Index"] - onsets_by_label[label]
    baseline = epoch.loc[(relative_samples >= -20) & (relative_samples < 0), amplitude_columns]
    if len(baseline) != 20 or baseline.isna().any().any():
        raise ValueError("Incomplete or missing baseline; apply the trial exclusion policy")
    epoch.loc[:, amplitude_columns] = (
        epoch.loc[:, amplitude_columns] - baseline.mean()
    )
```

This uses original sample coordinates rather than the stretched floating time index.
Prespecify baseline interval and estimand. Baseline subtraction is not universally
appropriate for rates, binary peaks, phase, quality, or absolute tonic levels.
Reject/flag a trial if its baseline has missing data or artifact rather than quietly
using fewer samples.

## Conversions

`epochs_to_df()` stacks epochs and adds a `Time` column; the stable probe observed
`Signal`, `Index`, `Label`, `Condition`, and `Time`.

`epochs_to_array()` does not take a `column` argument in 0.2.13. Equal-length,
single-signal epochs produced shape `(time, epochs)` in the pinned probe. Multiple
signal columns add an intermediate dimension. Unequal epochs are not supported.

`epochs_average()` signature is:

```text
epochs_average(epochs, which=None, indices=["mean", "std", "ci"], show=False)
```

For `which="Signal"`, the pinned schema contained `Time`, `Signal_Mean`,
`Signal_SD`, `Signal_CI_low`, and `Signal_CI_high` (plus a reset-index column).
This is not a universal event-related feature schema.

## Signal-specific analysis

Functions such as `ecg_eventrelated()`, `eda_eventrelated()`,
`rsp_eventrelated()`, `ppg_eventrelated()`, `emg_eventrelated()`, and
`eog_eventrelated()` inspect available processed columns. Their output changes when
quality, phase, amplitude, condition, or trend columns are absent.

Use explicit dispatch:

```python
ecg_features = nk.ecg_analyze(
    epochs, sampling_rate=100, method="event-related"
)
```

`method="auto"` chooses event-related analysis when mean duration is under 10 seconds.
That software threshold is not scientific justification for a window or analysis.

## Trial QC and statistics

Before averaging:

1. inspect trigger detection against the raw marker channel;
2. quantify boundary padding and missing baseline/post-event samples;
3. apply modality-specific artifact rules without looking at condition outcomes;
4. report retained trials per participant and condition;
5. avoid threshold tuning on the same effects being tested; and
6. model participant/trial hierarchy rather than treating epochs as independent.

There is no universal minimum number of trials or universal epoch window. Determine
both from the expected response, acquisition, study design, reliability, and power
analysis.

## Sources checked 2026-10-01

- [Official Events API](https://neuropsychology.github.io/NeuroKit/functions/events.html)
- [Official Epochs API](https://neuropsychology.github.io/NeuroKit/functions/epochs.html)
- [Official event-related example](https://neuropsychology.github.io/NeuroKit/examples/bio_eventrelated/bio_eventrelated.html)
- [Stable v0.2.13 epoch source](https://github.com/neuropsychology/NeuroKit/blob/v0.2.13/neurokit2/epochs/epochs_create.py)
- [SPR EEG/ERP guideline index](https://sprweb.org/guidelines-papers)
