---
name: flowkit
description: Analyzes flow cytometry data with FlowKit, including spillover compensation, logicle and biexponential transforms, hierarchical gating, GatingML strategies, and supported FlowJo 10 workspaces. Use for reproducible gate counts, population percentages, gated fluorescence summaries, or reproducing a FlowJo analysis in Python. For FCS metadata inspection or file-format repair alone, use FlowIO.
license: MIT
compatibility: Requires Python 3.13 with flowkit==1.3.2 for the tested environment. Dependencies include FlowIO, FlowUtils, NumPy, pandas, SciPy, lxml, and Bokeh. Installation needs network access; analysis uses local FCS/XML/WSP files without credentials. FlowUtils needs a C compiler if a compatible wheel is unavailable.
metadata:
  version: "1.1"
  skill-author: K-Dense Inc.
  last-reviewed: "2026-09-30"
---

# FlowKit

## When to use

Use FlowKit to apply or build cytometry gating strategies, analyze batches of
FCS samples, or reproduce supported FlowJo workspace analyses. It supports
GatingML 2.0 and a **subset of FlowJo 10 features**. Import success alone does
not establish agreement with FlowJo.

The examples and bundled helper target **FlowKit 1.3.2 on Python 3.13**.
Upstream supports additional Python versions; those were not exercised here.
The helper and examples were tested on synthetic FCS data, including a public
FlowJo 10.7.1 synthetic workspace fixture. They are not biological validation.

## Install

Use a separate environment; FlowKit 1.3.2 requires NumPy >2 and pandas <3:

```bash
uv venv --python 3.13 .venv-flowkit
uv pip install --python .venv-flowkit/bin/python "flowkit==1.3.2"
.venv-flowkit/bin/python -c "import flowkit; print(flowkit.__version__)"
```

The scientific package is BSD-3-Clause licensed; this skill is MIT licensed.

## Workflow

1. **Identify the analysis definition.** Use `Session` for a programmatic or
   GatingML strategy; use `Workspace` for FlowJo sample-specific gates,
   compensation, and transforms. Request the actual strategy or controls when
   biological thresholds have not been supplied.
2. **Inspect samples and channel identities.** Match detector/PnN labels to
   compensation matrices and gate dimensions; PnS marker names may be empty or
   repeated. Verify sample IDs: the default is FCS `$FIL`, which can differ
   from the current filename. Reject ID collisions before loading a batch.
3. **Establish the coordinate system.** Determine whether the supplied events
   are already compensated. Apply compensation before nonlinear transforms;
   match gate thresholds to the same transformed or untransformed coordinates.
   See [compensation and gating](references/compensation-and-gating.md).
4. **Check the hierarchy.** Preserve parent gates and full gate paths, including
   `root`. For a study, review acquisition/time stability, debris exclusion,
   singlets, viability, and phenotype gates as appropriate to its panel. Use
   single-stain controls for compensation and suitable negative/FMO controls
   for positivity; demonstration thresholds are not transferable biology.
5. **Analyze and inspect.** Run on all events, then check gate overlays and
   sample-level QC. A plot's subsample is not the population denominator.
   Review warnings and compare representative imported results to FlowJo.
6. **Export counts with denominators and provenance.** Keep gate paths,
   sample IDs, total event counts, input hashes, package versions, and the
   analysis definition. Keep biological replicates identifiable; events from
   one specimen are not independent experimental replicates.

## Apply an existing strategy

Set `FLOWKIT_SKILL_DIR` to this skill's installed directory. From the repository
root it is `skills/flowkit`. Paths below represent the user's local inputs.

```bash
FLOWKIT_SKILL_DIR="skills/flowkit"
uv run --no-project --python 3.13 --with "flowkit==1.3.2" \
  python "$FLOWKIT_SKILL_DIR/scripts/analyze_gates.py" \
  --gatingml gates.xml --fcs sample.fcs --output-dir results-gatingml
```

For a FlowJo workspace, supply **every FCS file in the selected group**:

```bash
uv run --no-project --python 3.13 --with "flowkit==1.3.2" \
  python "$FLOWKIT_SKILL_DIR/scripts/analyze_gates.py" \
  --workspace study.wsp --group "Study" \
  --fcs sample-a.fcs sample-b.fcs --output-dir results-workspace
```

The helper writes `gate_report.csv` and `provenance.json` to a new directory.
Each row includes `sample_event_count`, `parent_event_count`, and a full
`population_path`; empty-parent percentages are blank and flagged with
`relative_percent_defined=False`.
It rejects duplicate sample IDs, missing/extra workspace-group samples,
zero-event samples, and strategies without gates. It uses explicit input files,
does not follow paths embedded in the workspace, and runs without
multiprocessing or transformed-event caching. It still loads each sample into
memory; use manageable batches via the Python API for large studies.

`--filename-as-id` deliberately switches from `$FIL` to file basenames. Use it
only when those names match the analysis definition. See
[workspace analysis](references/workspaces-and-results.md) for partial-group
analysis, result interpretation, and fluorescence summaries.

## Build a strategy in Python

This runnable example uses `sample.fcs` with `FSC-A`, `FL1-A`, and `FL2-A`.
The matrix, thresholds, and transform parameters are **synthetic teaching
values**. Replace them with the study's validated settings.

```python
import flowkit as fk
import numpy as np

sample = fk.Sample("sample.fcs")
strategy = fk.GatingStrategy()
strategy.add_comp_matrix(
    "spill", fk.Matrix(
        np.array([[1.0, 0.1], [0.2, 1.0]]), ["FL1-A", "FL2-A"],
        fluorochromes=["FITC", "PE"],
    )
)
logicle = fk.transforms.LogicleTransform(
    param_t=262144, param_w=0.5, param_m=4.5, param_a=0
)
strategy.add_transform("logicle", logicle)
strategy.add_gate(
    fk.gates.RectangleGate("Cells", [
        fk.Dimension("FSC-A", range_min=50, range_max=300)
    ]),
    gate_path=("root",),
)
thresholds = logicle.apply(np.array([50.0, 600.0]))
strategy.add_gate(
    fk.gates.RectangleGate("Positive", [
        fk.Dimension(
            "FL1-A", compensation_ref="spill", transformation_ref="logicle",
            range_min=float(thresholds[0]), range_max=float(thresholds[1]),
        )
    ]),
    gate_path=("root", "Cells"),
)
session = fk.Session(gating_strategy=strategy, fcs_samples=[sample])
session.analyze_samples(use_mp=False)
report = session.get_analysis_report()
print(report[["sample_id", "gate_path", "gate_name", "count",
              "absolute_percent", "relative_percent"]])
with open("gates.xml", "xb") as handle:
    session.export_gml(handle)
```

GatingML exports a template by default. When custom per-sample gates exist,
use `session.export_gml(handle, sample_id=sample.id)` for that sample's strategy.
A single template export does not preserve every sample-specific override.

## Interpretation checks

- `count` is the number of events passing the gate and its ancestors.
- `absolute_percent` is percent of all sample events; `relative_percent` is
  percent of the immediate parent. These are percentages, not fractions.
- Gate names can repeat under different parents. In the helper's output use
  `(sample_id, population_path)` as the identifier. Paths are JSON arrays
  inside CSV cells. FlowKit's native report stores a quadrant's owner
  separately in `quadrant_parent`; its `gate_path` alone omits that owner.
- A zero-event parent makes a child percentage biologically undefined;
  FlowKit 1.3.2 reports zero for ordinary children and NaN for quadrants.
  The helper exports both as blank with an explicit false flag. This differs
  from a defined 0% for an empty gate whose parent contains events.
- Compensated negative fluorescence is legitimate. Do not clip it to zero or
  discard those events merely to permit a logarithmic transform.
- Define whether “MFI” means mean or median and name the event source.
  A transformed display value is not an intensity on the original scale.

## References

- [Compensation and gating](references/compensation-and-gating.md): event
  sources, detector order, transform semantics, gate paths, and plotting.
- [Workspaces and results](references/workspaces-and-results.md): sample
  matching, missing FCS files, FlowJo limits, and gated fluorescence summaries.
- [FlowKit API](https://flowkit.readthedocs.io/en/latest/api.html) and
  [versioned source](https://github.com/whitews/FlowKit/tree/1.3.2): consult
  signatures when moving beyond the tested release.
- [FlowKit publication](https://doi.org/10.3389/fimmu.2021.768541): cite the
  software and version in scientific methods when used for analysis.
