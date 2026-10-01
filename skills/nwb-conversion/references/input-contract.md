# Input contract and clock evidence

Use `assets/session-template.json` as a shape template only. Every experimental field is synthetic.
The helper requires timezone-aware ISO 8601 `session_start_time`, a stable unique `identifier`,
session description, experimenter list, lab, institution and a PyNWB Subject mapping. Keep subject
IDs pseudonymous where the dataset requires it. Do not confuse wall-clock time with elapsed sample
seconds or infer a timezone from the computer running the conversion.

`imaging.modality` must explicitly equal `two-photon`; other or missing modalities are rejected.
`imaging` supplies device name/description, series/plane description, indicator, anatomical location,
intensity unit, excitation and emission wavelengths in **nanometers**, and optical-channel description.
The helper implements a two-photon series; optical metadata must describe that actual acquisition.
Subject fields are passed through to PyNWB and retained in the full provenance config.
The optional `subject.date_of_birth` uses timezone-aware ISO 8601 text, converted to a datetime for
PyNWB. Session and position descriptions, optical text fields, and every experimenter name must be
nonempty. The position reference frame must describe the calibrated coordinates actually supplied.

Set integer `imaging.num_channels: 1` and `imaging.num_planes: 1` only after checking the acquisition
layout. The helper rejects multiple TIFF series, color/palette samples, or explicit non-singleton
channel/depth axes. Missing TIFF layout metadata does not prove a single channel or plane: a stack
of interleaved grayscale pages can look identical to a time sequence. Resolve that from microscope
metadata before conversion. OME multi-channel or volumetric input needs a separately tested reader.

Image timestamps CSV has exactly one column:

```csv
time_s
0.0
0.1
0.203
```

There must be one row per grayscale TIFF page. Dropped frames are represented by gaps in the actual
timestamps, not by silently reindexing to a nominal rate. The nominal rate supplied internally to
NeuroConv is only an initial reader parameter; every recorded frame receives its explicit timestamp.
A reordered TIFF must be paired with correspondingly reordered acquisition timestamps before use.

Position CSV has exactly these columns:

```csv
time_s,x,y
0.0,10.0,20.0
0.2,10.3,20.2
0.4,10.8,20.1
```

Every CSV row must have exactly the header's number of fields. Extra values, missing fields,
nonfinite values and nonincreasing time values are rejected rather than silently discarded.

`position_unit` is `m`, `cm` or `mm`; `position_reference_frame` describes origin and axis directions,
and `position_description` records measurement/calibration context. Pixel inputs are rejected because
a scale, lens correction and coordinate transform cannot be inferred from the CSV alone. Coordinates
are converted once to meters and written with `unit="meters"` and default conversion 1.0.

For a real shared clock, record the acquisition evidence, for example a shared DAQ counter that
actually timestamps both streams. Similar nominal sampling rates and matching file creation dates
are not evidence of shared timing.

```json
"synchronization": {
  "shared_clock_evidence": "Both vectors are acquisition DAQ counter timestamps, converted with its recorded tick rate"
}
```

For separate clocks, provide **already matched** pulse pairs; this helper does not discover
correspondences or correct missing pulses. The CSV columns are `device_time_s,reference_time_s`.
At least three distinct, increasing pairs must span the entire behavior interval. Specify the
maximum acceptable residual in seconds from the experiment's timing precision requirement:

```json
"synchronization": {
  "pulse_pairs_csv": "sync.csv",
  "max_residual_s": 0.001
}
```

The fitted map is `reference_seconds = slope * device_seconds + offset_seconds`.
Evaluation centers device times at the first pulse to reduce loss of numerical precision. The
report preserves that origin, the centered intercept, each pulse residual and both clocks' support
intervals. All reference seconds use the explicit NWB `timestamps_reference_time`, equal to this
converter's `session_start_time`; device seconds must use the same device origin in behavior and
pulse CSVs. A shared clock requires a shared epoch as well as a shared tick rate.
Inspect residuals and drift over the session before choosing the tolerance. A small least-squares
residual from only three pulses does not rule out unobserved clock jumps between them; record pulse
coverage and acquisition interruptions. Pulse extrapolation is rejected even when a linear fit is
excellent. If pulses fail the model, segment on evidence or use dense event timestamps with an
independently tested converter; do not loosen the tolerance just to make validation pass.
