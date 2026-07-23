# FlowIO 1.4.0 API Reference

This reference records the public API and behavior of the stable
`flowio==1.4.0` release. Prefer the exact parameter names shown here.

## Public Imports

```python
from flowio import (
    FlowData,
    create_fcs,
    fcs_keywords,
    read_multiple_data_sets,
)
from flowio.exceptions import (
    DataOffsetDiscrepancyError,
    FCSParsingError,
    FlowIOException,
    FlowIOWarning,
    MultipleDataSetsError,
    PnEWarning,
)
```

Exception classes are not re-exported at the top-level `flowio` namespace.
Import them from `flowio.exceptions`.

## `FlowData`

### Signature

```python
FlowData(
    fcs_file,
    ignore_offset_error=False,
    ignore_offset_discrepancy=False,
    use_header_offsets=False,
    only_text=False,
    nextdata_offset=None,
    null_channel_list=None,
)
```

### Parameters

- `fcs_file`: Local path string, `pathlib.Path`, or readable binary file
  handle. `FlowData` closes the handle after parsing, including a
  caller-provided handle.
- `ignore_offset_error`: Permit a DATA end offset that is off by one byte.
  FlowIO emits a warning because event values still require review.
- `ignore_offset_discrepancy`: Suppress the error raised when HEADER and TEXT
  DATA offsets disagree. FlowIO uses the TEXT offsets unless
  `use_header_offsets=True`.
- `use_header_offsets`: Use DATA offsets from HEADER. This also suppresses the
  HEADER/TEXT discrepancy error.
- `only_text`: Parse metadata without loading the DATA segment. `events` is
  `None`, so `as_array()` must not be called. HEADER, TEXT, and ANALYSIS are
  still parsed.
- `nextdata_offset`: Internal/careful-use byte offset for one dataset in a
  multi-dataset file. Prefer `read_multiple_data_sets()`.
- `null_channel_list`: PnN labels for channels not intended for analysis.
  Matching channels are omitted from `fluoro_indices`, `scatter_indices`, and
  `time_index`. The supplied label list is stored unchanged in
  `null_channels`; it is not converted to indices and may include labels that
  were not present.

### File support

- FCS versions: 2.0, 3.0, and 3.1
- DATA mode: list mode (`$MODE=L`)
- Event types used in practice: integer (`I`), single precision (`F`), and
  double precision (`D`)
- Correlated and uncorrelated histogram modes (`C` and `U`) raise
  `NotImplementedError`

The FCS standard defines ASCII (`A`) DATA, but FlowIO 1.4.0 does not provide a
reliable ASCII parser path. Do not claim ASCII event-data support without a
fixture-specific test.

### Core attributes

- `name`: Source file name, or `"InMemoryFile"` for a nameless handle.
- `file_size`: Source size in bytes.
- `version`: FCS version string.
- `header`: Parsed HEADER values.
- `text`: Parsed TEXT keyword/value mapping.
- `analysis`: Parsed ANALYSIS keyword/value mapping, or an empty mapping when
  absent.
- `data_type`: `$DATATYPE` value from the file.
- `channel_count`: Number of parameters/channels (`$PAR`).
- `event_count`: Number of events (`$TOT`).
- `events`: Flattened one-dimensional sequence of encoded event values, usually
  `array.array`. Mixed-width integer channels use a Python `list`.
  `events` is `None` when `only_text=True`.
- `channels`: Mapping whose keys are one-based FCS parameter numbers. Each value
  contains:
  - `pnn`: required PnN label
  - `pns`: optional PnS label, or `""`
  - `pne`: `(decades, log_zero)` tuple
  - `png`: gain as `float`, defaulting to `1.0`
  - `pnr`: range as `float`
- `pnn_labels`: Required channel labels in array-column order.
- `pns_labels`: Optional channel labels in array-column order; missing values
  are empty strings.
- `pnr_values`: Channel ranges in array-column order.
- `fluoro_indices`: Zero-based fluorescence-channel indices inferred by
  FlowIO.
- `scatter_indices`: Zero-based scatter-channel indices inferred by FlowIO.
- `time_index`: Zero-based time-channel index, or `None`.
- `null_channels`: PnN label strings supplied through `null_channel_list`.

### TEXT and ANALYSIS normalization

FlowIO removes `$` from standard keyword names, converts every key to
lowercase, and retains values as strings:

```python
flow.text["par"]
flow.text.get("date")
flow.text.get("spillover", flow.text.get("spill"))
flow.text.get("nextdata", "0")
```

The same key normalization applies to `analysis`. FlowIO 1.4.0 removes every
`$` character from the decoded segment before splitting keys and values, so a
value such as `"a$b"` is parsed as `"ab"`. Keep the source file when exact
metadata round-trip fidelity matters.

## `FlowData.as_array`

### Signature

```python
flow.as_array(preprocess=True)
```

Returns a two-dimensional NumPy `float64` array with shape:

```python
(flow.event_count, flow.channel_count)
```

With `preprocess=False`, FlowIO reshapes the encoded values without applying
metadata-driven scaling.

With `preprocess=True`, FlowIO:

1. Multiplies the time channel by the `timestep` keyword when available.
2. Converts logarithmically stored channels to linear values from PnE and PnR.
3. Divides channel values by PnG when gain is neither zero nor one.

It does not perform spillover compensation, logicle/biexponential/asinh
transformation, gating, or quality control.

The method materializes a new array in addition to `flow.events`.

## `FlowData.write_fcs`

### Signature

```python
flow.write_fcs(filename, metadata=None)
```

Writes the instance to an FCS 3.1 file.

Metadata behavior:

- `metadata=None`: preserve source `cyt`, `date`, and `spillover`/`spill` when
  present, plus PnR values needed by the writer.
- `metadata={}`: omit those selected defaults.
- Any other dictionary: write the supplied custom metadata instead of merging
  it with the selected defaults.

Required interpretation fields are generated internally. The output is
list-mode, single-precision floating-point data.

If the source `$DATATYPE` is not `F`, FlowIO calls `as_array()` with
preprocessing, flattens the values, changes the output to `F`, resets PnE and
PnG, and removes `timestep`. This is a representation conversion, not a
byte-preserving copy.

`write_fcs()` raises `AttributeError` for a `FlowData` created with
`only_text=True`.

For a floating-point source, `write_fcs()` keeps encoded events but its default
metadata preservation does not retain PnG or `timestep`. Reopening the output
can therefore produce different `as_array(preprocess=True)` values even when
`preprocess=False` values match. Validate both representations.

## `read_multiple_data_sets`

### Signature

```python
read_multiple_data_sets(
    filename_or_handle,
    ignore_offset_error=False,
    ignore_offset_discrepancy=False,
    use_header_offsets=False,
    only_text=False,
)
```

Returns a list of `FlowData` objects, including a one-element list for a
single-dataset file.

Use this function for legacy files whose normalized `nextdata` keyword is
nonzero. FlowIO follows positive relative offsets until it reaches
`nextdata == 0`. Negative offsets raise `MultipleDataSetsError`.

The FCS 3.1 specification deprecated multi-dataset files, but FlowIO retains
reader support for older files.

Pass a filesystem path for multi-dataset input. Although the documented
signature accepts a file handle, each `FlowData` closes that handle; FlowIO
1.4.0 then fails when the utility seeks the closed handle for the next dataset.

## `create_fcs`

### Signature

```python
create_fcs(
    file_handle,
    event_data,
    channel_names,
    opt_channel_names=None,
    metadata_dict=None,
)
```

### Parameters

- `file_handle`: Seekable binary output handle opened in a writable mode such
  as `"xb"` (new file) or `"wb"` (intentional overwrite).
- `event_data`: Flattened one-dimensional event values. Values must be ordered
  event by event, with channels varying within each event. The total number of
  values must be divisible by `len(channel_names)`.
- `channel_names`: PnN labels, one per channel.
- `opt_channel_names`: Optional PnS labels. Its length must match
  `channel_names`; `None` and empty-string entries are omitted.
- `metadata_dict`: Extra FCS metadata with string values.

### Correct pattern

```python
from pathlib import Path

import numpy as np
from flowio import create_fcs

events_2d = np.asarray(source_values, dtype=np.float32)
if events_2d.ndim != 2:
    raise ValueError("source_values must be events x channels")

labels = ["FSC-A", "SSC-A", "FITC-A"]
if events_2d.shape[1] != len(labels):
    raise ValueError("channel count does not match labels")

with Path("created.fcs").open("xb") as handle:
    create_fcs(
        handle,
        events_2d.ravel(order="C"),
        labels,
        metadata_dict={"date": "23-JUL-2026", "src": "Example"},
    )
```

### Writer rules

`create_fcs()` writes:

- FCS version 3.1
- List mode (`$MODE=L`)
- Single-precision 32-bit float values (`$DATATYPE=F`)
- Little-endian byte order
- No ANALYSIS segment
- No additional datasets (`$NEXTDATA=0`)

The output stores about 6-7 decimal digits of precision.

Big-endian portability is unverified: FlowIO declares little-endian metadata
but writes native-endian `array('f')` bytes.

NumPy input is copied into an `array('f')` before writing. If event data is
already available as `array('f')`, pass it directly to avoid that internal
copy. Large writers must budget for the float32 output buffer in addition to
the source array.

FlowIO owns required fields such as `$PAR`, `$TOT`, `$MODE`, `$DATATYPE`,
PnB, PnN, and output offsets. Custom attempts to override required fields are
ignored or normalized.

Writer-specific metadata behavior:

- Keys are treated case-insensitively and leading `$` is removed.
- Use strings for all values.
- Nonzero PnE values are invalid for floating-point output; FlowIO writes
  `0,0` and emits `PnEWarning`.
- PnG can be supplied; otherwise it defaults to `1.0`.
- PnR can be supplied; otherwise it defaults to `262144`.
- The number of PnS labels must equal the number of PnN labels.
- Empty event data is supported when at least one channel is defined.

For a spillover string, the first item is the number of compensated
fluorescence channels, followed by matching PnN labels and then matrix values,
all comma-delimited with no newline characters. FlowIO stores this metadata but
does not apply compensation.

## Exceptions and Warnings

Import from `flowio.exceptions`.

- `FlowIOWarning`: Base warning for FlowIO warnings.
- `PnEWarning`: Invalid PnE supplied while creating floating-point FCS.
- `FlowIOException`: Base FlowIO exception.
- `FCSParsingError`: Parse or structural errors.
- `DataOffsetDiscrepancyError`: HEADER and TEXT DATA offsets disagree. It is a
  subclass of `FCSParsingError`.
- `MultipleDataSetsError`: A normal `FlowData` open encountered multiple
  datasets, or multi-dataset offsets were invalid.

Do not use `except Exception` to retry with every relaxed option. Catch the
specific error, inspect provenance, and choose one justified recovery path.

## Public FCS Keyword Lists

FlowIO 1.4.0 exposes:

```python
from flowio import fcs_keywords

fcs_keywords.FCS_STANDARD_KEYWORDS
fcs_keywords.FCS_STANDARD_REQUIRED_KEYWORDS
fcs_keywords.FCS_STANDARD_OPTIONAL_KEYWORDS
```

These lists contain normalized names without `$`. They are useful for
validation and separating standard from custom TEXT fields.

## Changes Introduced in FlowIO 1.4.0

The 1.4.0 release:

- Added Python 3.13 support and dropped 3.7/3.8
- Added NumPy and `FlowData.as_array()`
- Renamed the `FlowData` constructor argument from `filename_or_handle` to
  `fcs_file`
- Added the convenience attributes documented above
- Made `fcs_keywords` public
- Added `pathlib.Path` support for `FlowData`
- Reduced writer memory use for `array.array` inputs
- Accepted empty `timestep` values
- Added the official tutorial notebook
