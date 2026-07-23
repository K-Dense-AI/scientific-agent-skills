# FCS Semantics for FlowIO

Use this reference when the task depends on what values or metadata mean, not
just how to call the API.

## Scope

FlowIO reads FCS 2.0, 3.0, and 3.1 and writes a constrained FCS 3.1
representation. It is a file-format library, not a complete flow-cytometry
analysis system.

Before downstream biological interpretation, decide whether the workflow also
requires:

- Spillover compensation
- Logicle, biexponential, or arcsinh transformation
- Quality-control filtering
- Singlet, viability, or population gating
- Batch correction or normalization

FlowIO does none of these. Its optional preprocessing is limited to scaling
defined by FCS acquisition metadata.

## File Segments

An FCS dataset can contain:

- **HEADER**: Version and byte offsets for other segments.
- **TEXT**: Required and optional keyword/value metadata.
- **DATA**: Event values.
- **ANALYSIS**: Optional keyword/value results.

FlowIO exposes these through `header`, `text`, `events`, and `analysis`.

FCS 3.1 deprecated storing multiple datasets in one file through `$NEXTDATA`,
but FlowIO can read legacy multi-dataset files with
`read_multiple_data_sets()`.

## TEXT Keyword Normalization

The FCS standard treats keyword names as case-insensitive. Standard keywords
are written with `$`, but FlowIO normalizes parsed keys:

1. Strip the leading `$`.
2. Convert the key to lowercase.
3. Keep the value as a string.

Examples:

- `$DATE` becomes `text["date"]`
- `$P1N` becomes `text["p1n"]`
- `$SPILLOVER` becomes `text["spillover"]`
- `$NEXTDATA` becomes `text["nextdata"]`

Use:

```python
date = flow.text.get("date")
spill = flow.text.get("spillover", flow.text.get("spill"))
nextdata = int(flow.text.get("nextdata", "0"))
```

Avoid:

```python
date = flow.text.get("$DATE")  # Always misses in FlowIO's normalized mapping.
```

Custom, non-standard keys are also lowercased. The normalized mapping may
contain subject, sample, operator, institution, instrument serial-number, and
free-text fields. Treat an unrestricted metadata dump as potentially
identifying.

FlowIO 1.4.0 implements the first step by removing every `$` character from the
decoded segment before splitting keys and values. A literal `$` inside a value
is therefore lost (`"a$b"` becomes `"ab"`). Do not use the parsed mapping as a
lossless metadata archive.

## Parameters, Labels, and Indices

FCS parameter numbers begin at 1:

- P1N, P2N, ... are required primary labels.
- P1S, P2S, ... are optional descriptive/stain labels.
- PnR records a parameter range.
- PnE records logarithmic amplification information.
- PnG records gain.

FlowIO presents these through two index systems:

- `flow.channels[1]`, `flow.channels[2]`, ... use one-based parameter numbers.
- NumPy columns and all `*_indices` attributes use zero-based indices.

When reporting a channel, label both values if ambiguity matters:

```python
for array_index, pnn in enumerate(flow.pnn_labels):
    parameter_number = array_index + 1
    pns = flow.pns_labels[array_index]
    print(parameter_number, array_index, pnn, pns)
```

PnS is optional. FlowIO inserts `""` for missing PnS entries so that
`pns_labels` and `pnn_labels` have the same length.

FlowIO infers scatter, fluorescence, and time indices from channel labels.
Treat these as conveniences, not a substitute for checking the instrument
panel. Vendor-specific labels may not classify as expected.

`null_channel_list` accepts PnN labels and excludes matching channels from the
derived fluorescence/scatter/time index lists. It does not remove columns from
the event data. `flow.null_channels` stores the supplied labels unchanged; it
does not contain zero-based indices and can retain labels that did not match a
channel.

## Encoded and Preprocessed Event Values

### Encoded representation

`flow.events` is a flattened one-dimensional sequence, ordered by event and
then channel. It is usually an `array.array`; mixed-width integer channels use
a Python `list`:

```text
event_1_channel_1, event_1_channel_2, ..., event_2_channel_1, ...
```

`flow.as_array(preprocess=False)` reshapes that representation to:

```text
(event_count, channel_count)
```

The returned NumPy array is `float64`, even when the encoded file uses integer
or single-precision event data.

### FlowIO preprocessing

`flow.as_array(preprocess=True)` performs the following operations.

#### Time scaling

When a time channel and nonempty `timestep` keyword exist:

```text
time_scaled = time_encoded * timestep
```

An empty or whitespace-only `timestep` is treated as `1.0` in FlowIO 1.4.0.

#### Logarithmically stored channels

For PnE `(decades, log_zero)` and PnR `range`:

```text
linear_value = 10 ** (decades * encoded_value / range) * log_zero
```

The conversion is applied when `decades > 0`.

#### Gain

For PnG `gain`:

```text
gain_scaled = value / gain
```

FlowIO skips division when gain is zero or one.

The operations are metadata-driven. Bad metadata can therefore produce bad
scaled values even when the DATA bytes were parsed correctly.

### What preprocessing does not do

FlowIO does not:

- Parse and apply `$SPILL`/`$SPILLOVER` compensation
- Perform logicle, biexponential, hyperlog, or arcsinh transformation
- Normalize between files
- Identify acquisition anomalies
- Remove debris, doublets, or dead cells
- Gate populations

For compensation/transformation/gating, use a higher-level package such as
FlowKit and preserve a record of the matrix and transform parameters.

## Spillover Metadata

FlowIO can expose or write a spillover keyword as a string. It does not validate
the matrix scientifically or apply it.

A standard spillover string begins with:

1. Number of compensated fluorescence parameters
2. Matching PnN labels
3. Flattened matrix values

Items are comma-delimited with no newline characters.

Before passing the matrix downstream:

- Confirm the labels exactly map to the event columns.
- Confirm the matrix dimensions match the declared parameter count.
- Confirm whether values are a compensation matrix or spillover matrix as
  expected by the downstream API.
- Keep the uncompensated values and original metadata for provenance.

## Offset Semantics

FCS 3.0/3.1 DATA offsets can appear in HEADER and TEXT. FlowIO normally uses
TEXT offsets and checks that HEADER agrees.

Some files have known defects:

- The last DATA byte is reported as exclusive rather than inclusive, creating
  an off-by-one error.
- HEADER and TEXT report different offsets.
- Large FCS 3.1 files put zero in HEADER DATA offsets when a segment extends
  beyond the eight-digit HEADER limit and store the real offsets in TEXT.

FlowIO accounts for the FCS 3.1 large-file rule. Do not use relaxed flags merely
because a file is large.

Recovery options:

- `ignore_offset_error=True`: tolerate the documented off-by-one case.
- `ignore_offset_discrepancy=True`: use TEXT despite a HEADER/TEXT mismatch.
- `use_header_offsets=True`: use HEADER and suppress the mismatch error.

Each option changes which bytes are interpreted as events. Use one only when
the file's provenance or vendor behavior justifies it, and validate event count,
channel distributions, and known controls afterward.

## Memory Model

Normal `FlowData` construction reads the full DATA segment into memory.
`as_array()` then allocates a second `float64` representation.

Approximate additional memory for the 2-D array is:

```text
event_count * channel_count * 8 bytes
```

This excludes the original event array, Python objects, temporary arrays, and
downstream DataFrames.

Use `only_text=True` for inventory. FlowIO 1.4.0 does not expose chunked,
streaming, lazy, or memory-mapped event reads. If a file does not fit safely in
memory, use a different parser/workflow or process it in a resource-limited
environment; do not claim FlowIO can chunk it.

`only_text=True` skips DATA loading but still parses ANALYSIS. Also prefer paths
over open handles: `FlowData` closes caller-provided handles, and the
multi-dataset helper cannot reuse a closed handle for its second dataset in
FlowIO 1.4.0.

## Writer Representation

`create_fcs()` and `write_fcs()` produce:

- FCS 3.1
- List mode
- Single-precision 32-bit float event values
- Little-endian byte order
- No ANALYSIS segment
- A single dataset

The float32 representation has roughly 6-7 decimal digits of precision.
Round-trip comparisons should use tolerances rather than exact equality.

Passing a NumPy array makes `create_fcs()` allocate an `array('f')` copy. An
existing `array('f')` is written directly, so retain that representation when
large writer memory is a concern.

`create_fcs()` needs flattened event data. Flatten a two-dimensional array in
C order:

```python
flat = events_2d.astype("float32", copy=False).ravel(order="C")
```

Validate:

```python
if events_2d.ndim != 2:
    raise ValueError("expected events x channels")
if events_2d.shape[1] != len(channel_names):
    raise ValueError("channel label count mismatch")
```

Required keywords and channel interpretation fields are generated by FlowIO.
Do not rely on `metadata_dict` to override `$PAR`, `$TOT`, `$MODE`,
`$DATATYPE`, PnB, or PnN.

For floating-point sources, `write_fcs()` can keep encoded values while
dropping PnG and `timestep`. This changes the interpretation returned by
`as_array(preprocess=True)`. Validate both encoded and metadata-scaled values,
not just event counts.

## Scientific Provenance

For any converted or rewritten file, record:

- Source file name and checksum
- FlowIO version
- FCS version and source `$DATATYPE`
- Whether `preprocess` was true or false
- Any relaxed offset option and its justification
- Channel order and label mapping
- Metadata removed, added, or renamed
- Whether compensation or another transform occurred elsewhere
- Output representation and float32 precision
- Round-trip validation results
