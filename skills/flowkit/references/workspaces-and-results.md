# Workspaces and result interpretation

## Match samples before interpreting results

Use explicit FCS files and inspect the workspace's sample groups. Retaining
missing-file metadata is essential: otherwise missing samples may be removed
from group membership during construction and a partial analysis can look
complete. `load_missing_file_data=True` retains workspace metadata for missing
FCS files; it does not supply those files' events.

The following example is exercised with the repository's synthetic FlowJo
fixture. Replace paths, group name, and sample identity for real work:

```python
import flowkit as fk

workspace = fk.Workspace(
    "study.wsp",
    fcs_samples=["data_set_simple_line_100.fcs"],
    load_missing_file_data=True,
    find_fcs_files_from_wsp=False,
)
print(workspace.get_sample_groups())
group = "my_group"
expected = set(workspace.get_sample_ids(group_name=group, loaded_only=False))
loaded = set(workspace.get_sample_ids(group_name=group, loaded_only=True))
if not expected or expected != loaded:
    raise ValueError(f"Empty group or missing FCS samples: {sorted(expected - loaded)}")
workspace.analyze_samples(group_name=group, use_mp=False)
print(workspace.get_analysis_report(group_name=group))
```

FCS `$FIL`, filesystem basename, and workspace sample name can disagree after
renaming/export. Inspect these identities rather than matching by position.
`filename_as_id=True` is useful only when current basenames match the workspace.
When an explicit, reviewed mapping is necessary, construct
`fk.Sample(path, sample_id=workspace_id, use_flowjo_labels=True)` objects and
pass those to `Workspace`. Check uniqueness before building the list.

For an intentionally partial group, use `analyze_samples(sample_id=...)` for
the explicitly selected IDs and report included and missing IDs. The bundled
CLI deliberately requires the complete named group.

## Report paths and denominators

FlowKit 1.3.2 reports individual quadrants with `gate_path` equal to the
owning `QuadrantGate`'s path and puts that gate's name in `quadrant_parent`.
For example, quadrant `High` in `Split` below `Cells` has report path
`("root", "Cells")`, but strategy path `("root", "Cells", "Split")`.
Its percentage denominator is the `Cells` count; `Split` is a collection of
quadrants, not another population. A gate below `High` uses the full parent
path `("root", "Cells", "Split", "High")`.

The CLI adds a full `population_path`, including the population's own name
and any quadrant owner, plus `sample_event_count` and `parent_event_count`.
Use sample ID plus that path to join results. An empty parent gives an
undefined percentage even when the child count is zero: the helper writes a
blank `relative_percent` and `relative_percent_defined=False`. A zero-count
gate under a nonempty parent retains its valid 0% value.

The 1.3.2 membership API cannot disambiguate a repeated quadrant name across
different owning QuadrantGates, even with a path; it raises `ValueError`.
Use unique quadrant names when constructing strategies. For imported
strategies, inspect the report and preserve its owner column; do not silently
rename gates or use the wrong population's mask. The CLI's report export does
not call this membership API and retains both populations correctly.

## FlowJo compatibility

FlowKit supports a subset of FlowJo 10: documented transformations and
polygon, rectangle, ellipse, quadrant, and Boolean gates. Plugins, derived
parameters, specialized models, or other unsupported workspace features may
not reproduce. Review parser warnings and imported gate inventories. Compare
counts, percentages, and overlays against the original FlowJo export on
representative samples, including sample-specific overrides and rare gates.
Record both software versions and any mismatch; importing without an
exception is insufficient.

Prefer the original workspace for reproduction. A single GatingML template
does not encode all custom sample gates. FlowKit's WSP exporter is not a
guaranteed round-trip: in the tested 1.3.2 environment, re-importing a synthetic
compensated `Session.export_wsp` result failed to resolve a `Comp-FL1-A`
channel. Native FlowJo fixture import was tested separately. Validate any
conversion independently before relying on it.

## Fluorescence summaries

Choose mean or median explicitly, retain sample and gate path, and report the
number of events. For a programmatic `Session`, obtain the gate mask, then
apply the intended matrix to the Sample and summarize the desired detector
from `source="comp"`. This keeps compensation separate from display transforms.

For a `Workspace`, `get_gate_events(sample_id, gate_name, gate_path=path,
source="comp")` applies the workspace matrix without display transforms.
If `workspace.get_comp_matrix(sample_id)` is `None`, this silently returns
raw events instead; confirm that this is the intended analysis provenance.
Its default `source=None` uses the workspace's compensation **and transforms**,
so choose the source explicitly for an untransformed intensity summary.
The returned DataFrame has a string `sample_id` column and channel columns
formed by joining PnN and PnS labels. Inspect those labels and select the
intended detector before calculating a numeric summary.

There is an API asymmetry: `Session.get_gate_events(...)` defaults to raw
events unless `matrix` and/or `transform` are supplied. It does not
automatically choose the preprocessing of the gate's dimensions. Therefore,
identical-looking calls on Session and Workspace can summarize different
numbers. Do not compare them until their coordinate systems agree.

Empty gates have no defined mean/median; return missing values with count zero.
Negative compensated values make geometric means inappropriate without a
separately justified method. Across samples, account for panel, instrument,
batch, controls, and calibration before interpreting intensity differences.

## Primary sources

- [Workspace API](https://flowkit.readthedocs.io/en/latest/workspace.html)
- [Session API](https://flowkit.readthedocs.io/en/latest/session.html)
- [GatingResults API](https://flowkit.readthedocs.io/en/latest/gating_results.html)
- [Released report implementation](https://github.com/whitews/FlowKit/blob/1.3.2/src/flowkit/_models/gating_results.py)
- [Released gating and percentage implementation](https://github.com/whitews/FlowKit/blob/1.3.2/src/flowkit/_models/gating_strategy.py)
- [Upstream feature scope](https://github.com/whitews/FlowKit)
