# FlowIO Workflows

These patterns target `flowio==1.4.0`. Keep raw files immutable and write
derived outputs to a separate location.

## 1. Inventory a File Without Loading Events

Use `only_text=True` when the goal is file structure, labels, or acquisition
metadata:

```python
from pathlib import Path

from flowio import FlowData

path = Path("sample.fcs")
flow = FlowData(path, only_text=True)

summary = {
    "file": path.name,
    "size_bytes": path.stat().st_size,
    "fcs_version": flow.version,
    "data_type": flow.data_type,
    "event_count": flow.event_count,
    "channel_count": flow.channel_count,
    "pnn_labels": flow.pnn_labels,
    "pns_labels": flow.pns_labels,
    "date": flow.text.get("date"),
    "instrument": flow.text.get("cyt"),
}
print(summary)
```

Do not call `as_array()` on this object.
`only_text=True` skips DATA loading but still parses ANALYSIS.

For an inventory that also handles multi-dataset files and emits JSON, use:

```bash
FLOWIO_SKILL_DIR="skills/flowio"  # Set to the installed skill directory.
uv run --no-project --with "flowio==1.4.0" \
  python "$FLOWIO_SKILL_DIR/scripts/inspect_fcs.py" sample.fcs
```

## 2. Load Encoded or Metadata-Scaled Events

```python
from flowio import FlowData

flow = FlowData("sample.fcs")

# Gain/log/time scaling from FCS metadata.
scaled = flow.as_array(preprocess=True)

# Values reshaped as encoded in DATA.
encoded = flow.as_array(preprocess=False)

assert scaled.shape == (flow.event_count, flow.channel_count)
assert encoded.shape == scaled.shape
```

Neither array is compensated or gated. Name output variables to preserve this
distinction; avoid generic names such as `processed`.

## 3. Build a DataFrame

This example assumes pandas is already present in the project environment.
Add and lock an environment-compatible pandas release only when tabular
integration is required; FlowIO itself does not depend on pandas.

FCS files can contain duplicate or empty labels. Make DataFrame names unique
instead of silently assuming PnN values are valid columns:

```python
from collections import Counter

import pandas as pd
from flowio import FlowData


def unique_labels(labels):
    counts = Counter()
    result = []
    for index, value in enumerate(labels):
        base = value.strip() or f"channel_{index + 1}"
        counts[base] += 1
        suffix = "" if counts[base] == 1 else f"__{counts[base]}"
        result.append(f"{base}{suffix}")
    return result


flow = FlowData("sample.fcs")
columns = unique_labels(flow.pnn_labels)
frame = pd.DataFrame(
    flow.as_array(preprocess=True),
    columns=columns,
)

frame.attrs.update(
    {
        "flowio_version": "1.4.0",
        "fcs_version": flow.version,
        "event_semantics": "gain/log/time scaled; uncompensated; ungated",
        "source_pnn_labels": flow.pnn_labels,
        "source_pns_labels": flow.pns_labels,
    }
)
```

DataFrame attributes are not preserved by every export format. Store a
sidecar JSON provenance record for durable pipelines.

## 4. Export CSV Safely

CSV loses most FCS metadata and type information. Export a sidecar record:

```python
import json
from pathlib import Path

import pandas as pd
from flowio import FlowData

source = Path("sample.fcs")
flow = FlowData(source)
values = flow.as_array(preprocess=False)

frame = pd.DataFrame(
    values,
    columns=unique_labels(flow.pnn_labels),  # Helper from the previous workflow.
)
csv_path = Path("sample.events.csv")
with csv_path.open("x", encoding="utf-8", newline="") as handle:
    frame.to_csv(handle, index=False)

provenance = {
    "source_file": source.name,
    "flowio_version": "1.4.0",
    "fcs_version": flow.version,
    "event_semantics": "encoded DATA values reshaped; preprocess=False",
    "pnn_labels": flow.pnn_labels,
    "pns_labels": flow.pns_labels,
    "event_count": flow.event_count,
    "channel_count": flow.channel_count,
}
with Path("sample.events.json").open("x", encoding="utf-8") as handle:
    handle.write(json.dumps(provenance, indent=2) + "\n")
```

Before sharing either output, review labels and metadata for subject or sample
identifiers.

## 5. Batch Metadata Inventory

This pattern reads no event arrays:

```python
from pathlib import Path

from flowio import read_multiple_data_sets
from flowio.exceptions import FlowIOException

records = []
failures = []

for path in sorted(Path("fcs").rglob("*.fcs")):
    try:
        datasets = read_multiple_data_sets(path, only_text=True)
        for dataset_index, flow in enumerate(datasets):
            records.append(
                {
                    "file": str(path),
                    "dataset_index": dataset_index,
                    "fcs_version": flow.version,
                    "event_count": flow.event_count,
                    "channel_count": flow.channel_count,
                    "pnn_labels": flow.pnn_labels,
                }
            )
    except (FlowIOException, OSError, ValueError) as error:
        failures.append({"file": str(path), "error": str(error)})
```

Do not automatically retry failed files with every relaxed offset option.
Triage each error type and file source.

## 6. Read Legacy Multi-Dataset Files

Pass a path, not an open handle. FlowIO 1.4.0 closes caller-provided handles,
so the utility cannot reuse one for the second dataset.

```python
from flowio import read_multiple_data_sets

datasets = read_multiple_data_sets(
    "legacy.lmd",
    only_text=False,
)

for dataset_index, flow in enumerate(datasets):
    encoded = flow.as_array(preprocess=False)
    print(dataset_index, encoded.shape, flow.text.get("nextdata"))
```

If a known off-by-one vendor file requires recovery:

```python
datasets = read_multiple_data_sets(
    "known-vendor-file.lmd",
    ignore_offset_error=True,
)
```

Capture the FlowIO warning and validate event values before using them.

## 7. Write a New FCS File From a 2-D Array

```python
from pathlib import Path

import numpy as np
from flowio import create_fcs

events = np.asarray(source_events, dtype=np.float32)
channel_names = ["FSC-A", "SSC-A", "FITC-A"]
stain_names = ["Forward scatter", "Side scatter", "CD3"]

if events.ndim != 2:
    raise ValueError("source_events must be a 2-D events x channels array")
if events.shape[1] != len(channel_names):
    raise ValueError("array columns and channel_names differ")
if len(stain_names) != len(channel_names):
    raise ValueError("PnS and PnN label counts differ")
if not np.isfinite(events).all():
    raise ValueError("decide how to handle NaN/inf before FCS export")

destination = Path("derived.fcs")
if destination.exists():
    raise FileExistsError(destination)

with destination.open("xb") as handle:
    create_fcs(
        handle,
        events.ravel(order="C"),
        channel_names,
        opt_channel_names=stain_names,
        metadata_dict={
            "date": "23-JUL-2026",
            "src": "Derived event matrix",
        },
    )
```

Mode `"xb"` prevents accidental overwrite. Use `"wb"` only when replacement
is intentional and controlled.

## 8. Rewrite Metadata Without Changing Event Count

`write_fcs()` is useful for selected metadata replacement:

```python
from pathlib import Path

from flowio import FlowData

source = Path("source.fcs")
destination = Path("deidentified.fcs")
if destination.exists():
    raise FileExistsError(destination)

flow = FlowData(source)
flow.write_fcs(
    destination,
    metadata={
        "src": "Deidentified derivative",
        "cyt": flow.text.get("cyt", "Unknown instrument"),
    },
)
```

Passing a metadata dictionary replaces FlowIO's default selected metadata. It
does not merge with all source TEXT fields. This is useful for minimizing
metadata, but inspect the reopened file rather than assuming which fields
remain.

`write_fcs()` converts the representation to FCS 3.1 single-precision float.
It is not a lossless metadata patcher. For floating-point sources it can retain
encoded values while dropping PnG or `timestep`, so compare both
`preprocess=False` and `preprocess=True` arrays after reopening.

## 9. Round-Trip Validation

Validate every file you create:

```python
import numpy as np
from flowio import FlowData

check = FlowData("derived.fcs")

assert check.version == "3.1"
assert check.data_type == "F"
assert check.event_count == events.shape[0]
assert check.channel_count == events.shape[1]
assert check.pnn_labels == channel_names

roundtrip = check.as_array(preprocess=False)
np.testing.assert_allclose(
    roundtrip,
    events,
    rtol=1e-6,
    atol=1e-6,
)
```

Also verify:

- Expected PnS labels
- Expected custom metadata
- No unintended subject identifiers
- Representative channel distributions
- Spillover label order, if stored
- Readability in the intended downstream tool

## 10. Compute Inspection Statistics

The bundled inspector computes finite-value statistics only when explicitly
requested:

```bash
FLOWIO_SKILL_DIR="skills/flowio"  # Set to the installed skill directory.

# Metadata-scaled values
uv run --no-project --with "flowio==1.4.0" \
  python "$FLOWIO_SKILL_DIR/scripts/inspect_fcs.py" sample.fcs --stats

# Encoded values
uv run --no-project --with "flowio==1.4.0" \
  python "$FLOWIO_SKILL_DIR/scripts/inspect_fcs.py" sample.fcs --stats --raw

# Save JSON without overwriting an existing file
uv run --no-project --with "flowio==1.4.0" \
  python "$FLOWIO_SKILL_DIR/scripts/inspect_fcs.py" sample.fcs \
  --output sample.inspect.json
```

Statistics require full event loading and another float64 array. Estimate
memory before using `--stats` on a large file. The inspector's
`--max-array-bytes` guard limits the estimated float64 array; this estimate
does not include the encoded event container.

## 11. Hand Off to Higher-Level Analysis

Use FlowIO to preserve file semantics, then hand the data to a cytometry
analysis library when the task includes compensation or gating.

A defensible handoff records:

- Whether FlowIO preprocessing was used
- Whether the compensation matrix came from `spill`/`spillover` or an external
  control
- Channel/PnN order used for matrix alignment
- Transform names and parameters
- Gate definitions and software version

Do not apply FlowIO preprocessing blindly before a higher-level library. Check
whether that library expects encoded, compensated, or already transformed
values to avoid double scaling.
