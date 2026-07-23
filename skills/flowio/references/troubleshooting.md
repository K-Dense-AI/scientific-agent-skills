# FlowIO Troubleshooting and Safety

Use the narrowest remedy that matches the observed failure. Keep the original
file unchanged and record every recovery option used.

## Confirm the Runtime First

```bash
uv run python -c "import flowio; print(flowio.__version__)"
```

This skill targets `1.4.0`. If the runtime differs, inspect that release's API
and changelog before assuming examples are compatible.

## Import Errors for Exceptions

Symptom:

```text
ImportError: cannot import name 'FCSParsingError' from 'flowio'
```

Cause: Exception classes are not top-level exports.

Correct:

```python
from flowio import FlowData
from flowio.exceptions import FCSParsingError
```

## `MultipleDataSetsError`

Symptom: Opening a file with `FlowData(...)` reports that it contains multiple
datasets.

Use:

```python
from flowio import read_multiple_data_sets

datasets = read_multiple_data_sets("legacy.fcs")
```

Do not manually treat `text["nextdata"]` as an absolute offset. The legacy
format uses relative offsets, and FCS 3.1 deprecated this representation.

## `DataOffsetDiscrepancyError`

Symptom: HEADER and TEXT identify different DATA byte locations.

Default behavior is correct: stop rather than guessing.

Triage:

1. Preserve the source file and calculate a checksum.
2. Confirm the file came directly from a known instrument/exporter.
3. Check vendor documentation or a known-good file from the same software.
4. Prefer TEXT offsets only when evidence supports them:

   ```python
   flow = FlowData(
       "known-file.fcs",
       ignore_offset_discrepancy=True,
   )
   ```

5. Use HEADER offsets only when evidence supports HEADER:

   ```python
   flow = FlowData(
       "known-file.fcs",
       use_header_offsets=True,
   )
   ```

6. Validate event count, channel ranges, distributions, and controls.

Do not set both options reflexively or make them global defaults.

## Off-by-One DATA Offset

Some producers report the final DATA byte as exclusive rather than inclusive.
For a known instance:

```python
flow = FlowData(
    "known-off-by-one.fcs",
    ignore_offset_error=True,
)
```

FlowIO emits a warning stating that event data should be reviewed. Preserve
that warning in logs and perform distribution/control checks.

## Large Files With Zero HEADER DATA Offsets

FCS 3.1 requires HEADER DATA offsets to be zero when a segment extends beyond
the eight-digit HEADER limit; real offsets remain in TEXT. FlowIO recognizes
this case.

Do not enable `use_header_offsets=True` merely because the file is large.
Doing so can select zeros instead of the valid TEXT values.

## `only_text=True` Followed by Array Failure

Symptom: `as_array()` fails after metadata-only parsing.

Cause: `only_text=True` intentionally leaves `events` unset.

Reopen normally:

```python
metadata_only = FlowData("sample.fcs", only_text=True)
# ...decide whether full loading is safe...
with_events = FlowData("sample.fcs")
events = with_events.as_array()
```

## Unexpected Metadata Lookup Results

Symptom: `flow.text.get("$DATE")` returns `None`.

Use normalized keys:

```python
flow.text.get("date")
flow.text.get("cyt")
flow.text.get("spillover", flow.text.get("spill"))
```

All parsed keys are lowercase and omit `$`.

FlowIO 1.4.0 also removes literal `$` characters inside values. If exact TEXT
fidelity is required, inspect the source bytes with a standards-aware tool
rather than reconstructing metadata from `flow.text`.

## Unexpected Event Values

Compare both representations:

```python
encoded = flow.as_array(preprocess=False)
scaled = flow.as_array(preprocess=True)
```

Then inspect:

- `flow.data_type`
- `flow.channels[n]["pne"]`
- `flow.channels[n]["png"]`
- `flow.channels[n]["pnr"]`
- `flow.text.get("timestep")`
- `flow.time_index`

FlowIO preprocessing divides by gain; it does not multiply by gain. It also
does not apply compensation. If values differ from a higher-level application,
check whether that application applied compensation, display transforms, or
vendor-specific scaling.

## Channel Classification Looks Wrong

`scatter_indices`, `fluoro_indices`, and `time_index` are label-based
conveniences. Instrument/vendor labels can be unusual.

Inspect all channel metadata:

```python
for parameter_number, channel in flow.channels.items():
    print(parameter_number, channel)
```

Use an explicit, provenance-backed mapping for downstream analysis. Do not
rename columns solely from guessed channel type.

`flow.null_channels` contains PnN labels supplied through
`null_channel_list`, not integer indices. Matching labels are omitted from the
derived index lists but remain in the event array.

## Closed File Handle

`FlowData` closes a file handle passed by the caller. Do not expect to reuse it:

```python
with open("sample.fcs", "rb") as handle:
    flow = FlowData(handle)
    # handle is already closed here by FlowIO 1.4.0
```

Prefer a path. In particular, pass a path to `read_multiple_data_sets()`;
passing one handle fails when the utility tries to read the second dataset
after the first `FlowData` closed it.

## Duplicate or Empty DataFrame Columns

PnN values may be duplicated or malformed, and PnS is optional. Validate and
make names unique before constructing a DataFrame. Retain the original PnN/PnS
lists in provenance.

See `workflows.md` for a deterministic `unique_labels()` helper.

## `create_fcs()` Receives a Path

Incorrect:

```python
create_fcs("output.fcs", values, labels)
```

Correct:

```python
with open("output.fcs", "xb") as handle:
    create_fcs(handle, values.ravel(order="C"), labels)
```

The first argument is a binary file handle, not a path.

## `create_fcs()` Receives a 2-D Array

The writer expects flattened event data. Validate before flattening:

```python
if values.ndim != 2:
    raise ValueError("expected events x channels")
if values.shape[1] != len(labels):
    raise ValueError("label count mismatch")

flat = values.astype("float32", copy=False).ravel(order="C")
```

A wrong flattening order silently changes event/channel alignment. Use C order,
where all channel values for one event are adjacent.

## Number of Data Points Is Not a Multiple of Channels

Cause: The flattened event-data length does not divide evenly by the channel
label count.

Check:

```python
if flat.size % len(labels) != 0:
    raise ValueError("incomplete event row")
```

Prefer checking the original two-dimensional shape before flattening.

## PnN and PnS Count Mismatch

`opt_channel_names` must have the same length as `channel_names`. Use `None` or
`""` for an individual missing PnS label, or omit the whole argument.

## `PnEWarning` During Creation

FlowIO writes floating-point FCS output, which requires PnE `0,0`. Supplying
nonzero PnE metadata produces a warning and FlowIO writes `0,0`.

Do not suppress the warning and assume encoded log-amplified semantics were
preserved. Export the desired numerical representation explicitly and document
it.

## Metadata Missing After `write_fcs()`

`write_fcs(metadata=...)` does not merge the supplied dictionary with all source
TEXT metadata.

- `metadata=None` preserves selected defaults (`cyt`, `date`,
  `spillover`/`spill`).
- `metadata={}` writes the minimum generated metadata.
- A custom dictionary writes those custom fields instead of the selected
  defaults.

Reopen the output and inspect `text`.

For floating-point input, also compare:

```python
source_raw = source.as_array(preprocess=False)
source_scaled = source.as_array(preprocess=True)
output_raw = output.as_array(preprocess=False)
output_scaled = output.as_array(preprocess=True)
```

Default `write_fcs()` preservation does not retain PnG or `timestep`. Raw
values can match while scaled values differ.

## Output Values Differ Slightly

FlowIO writes single-precision floats. Small round-trip differences are
expected.

Use:

```python
import numpy as np

np.testing.assert_allclose(
    reopened.as_array(preprocess=False),
    expected,
    rtol=1e-6,
    atol=1e-6,
)
```

Set tolerances according to the data scale and scientific requirements.

## Big-Endian Writer Portability

FlowIO 1.4.0 declares little-endian output but writes `array('f')` bytes in the
runtime's native byte order. This skill has not verified export behavior on
big-endian hardware. Treat big-endian writing as unverified and validate with
an independent reader before relying on the output.

## Memory Exhaustion

FlowIO loads the DATA segment, and `as_array()` allocates another float64 array.
It has no chunked reader.

Before loading:

```python
estimated_array_bytes = event_count * channel_count * 8
```

This estimate covers only the `as_array()` result.

`create_fcs()` also converts NumPy inputs to an `array('f')` buffer. For large
writes, include roughly four bytes per flattened value for that buffer, unless
the input is already `array('f')`.

Mitigations:

- Use `only_text=True` for inventory.
- Reject unexpectedly large files before parsing.
- Avoid creating multiple full arrays simultaneously.
- Delete references to no-longer-needed arrays before the next file.
- Use a resource-limited worker or a different streaming-capable tool when the
  file cannot fit safely.

Do not advertise "processing in chunks" as a FlowIO feature.

## Untrusted FCS Files

An FCS file is structured binary input. A malformed file can consume excessive
memory/CPU or exploit defects in any parser.

For files from untrusted uploaders:

1. Enforce an input-size limit before `FlowData`.
2. Parse in an isolated, resource-limited process/container.
3. Keep strict offset checks.
4. Use a read-only copy and a dedicated output directory.
5. Do not overwrite the source.
6. Log parser version, warnings, and a cryptographic checksum.
7. Keep dependencies patched and test upgrades against representative files.

The bundled inspector defaults to metadata-only parsing and a size limit, but
it is not a malware sandbox.

## Privacy and Clinical Metadata

TEXT and ANALYSIS can include:

- Subject or patient identifiers
- Sample/tube identifiers
- Acquisition dates and times
- Operator names
- Institution and instrument identifiers
- Free-text comments

Before logging, exporting, or sharing:

- Use an allowlist of metadata keys.
- Avoid `--include-text` unless necessary.
- Keep identifiers out of filenames where possible.
- Apply the project's de-identification and access-control policy.
- Verify the rewritten file, CSV, JSON, logs, and error messages.

Removing selected TEXT fields does not by itself establish regulatory
de-identification.

## Minimal Integrity Record

```python
import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

Record the checksum alongside FlowIO version, parse flags, warnings, event
semantics, and validation results.
