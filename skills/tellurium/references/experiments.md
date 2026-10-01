# Experiment semantics and reproducibility

The JSON accepts exactly these keys:

| Key | Meaning |
| --- | --- |
| `end_time` | Positive end of integration, in the model's time unit; initial and output start are zero |
| `points` | Number of saved samples including both endpoints, integer >=2 |
| `relative_tolerance`, `absolute_tolerance` | Positive CVODE error-control settings |
| `species` | Unique SBML IDs to report as concentrations |
| `scenarios` | Named mappings of constant global parameter IDs to finite numeric values; includes `baseline: {}` |

Scenario names must be SBML-style identifiers. Parameter changes are applied to independent cloned
SBML documents before RoadRunner loads them, and the modified files become the archive models.
The helper rejects nonexistent/nonconstant parameters and parameters with initial assignments,
because setting a numeric field there would not necessarily implement the requested perturbation.
A fresh model per condition avoids ambiguity between RoadRunner reset variants and persistent
parameter changes.

The supplied two-condition first-order model is synthetic. Its units are explicit: time in seconds,
volume in liters, species concentrations in mol/L and k in inverse seconds. Reaction flux is
`k*A*cell` mol/s. Unit annotations describe dimensions; merely changing a unit label does not rescale
a numeric initial value or kinetic constant. Check dimensional consistency and magnitudes together.

For a closed constant-volume A→B model, the conserved amount is compartment volume times A+B.
The example's volume is exactly 1 L, so its concentration sum also stays numerically one. In a
variable-volume model, open system, synthesis/degradation model or chemostatted network, the same
concentration-sum check would be invalid. Choose invariants from the actual stoichiometry and
boundary conditions rather than treating total species sum as universally conserved.

## SBML and solver checks

libSBML parses the source and runs consistency checks before simulation. Errors/fatal diagnostics
stop execution; warnings remain in the report for review. Missing units do not prevent numerical
execution but prevent a claim of dimensional validation. Confirm the units of every reported
concentration and parameter. The helper reports the minimum concentration per scenario rather than
clipping negatives. Small negatives near zero may reflect tolerance; significant negatives require
investigating the equations, initial state and solver behavior.

CVODE uses stiff integration with explicit relative and absolute tolerances. Output samples are not
internal integration steps. Repeat selected scientifically relevant cases at tighter tolerances and
compare outputs, conservation residuals and event timing. For concentrations near zero, absolute
rather than relative tolerance dominates. Very different species scales may require a model-specific
per-species tolerance workflow beyond this scalar-tolerance helper.

The script is scoped to deterministic concentration trajectories. Stochastic counts, amount-only
species, event-rich models, delay equations, external SBML comp references and arbitrary package
extensions require separate verification before extending these guarantees. No model or data is
uploaded to an external solver.

## Archive experiment

The helper writes SED-ML Level 1 Version 3 with one uniform simulation, one model/task per scenario,
and a report with data generators for time and each selected species. It encodes CVODE as
`KISAO:0000019`, relative tolerance as `KISAO:0000209`, and absolute tolerance as `KISAO:0000211`.
SED-ML `numberOfPoints` is **intervals**, so the script writes `points - 1` to retain exactly the
number of samples requested by RoadRunner.

COMBINE entries use local filenames and one master SED-ML. `executeCombineArchive` replays only
this newly generated archive; the helper is not an arbitrary archive extraction interface. Every
replayed data generator is compared to the corresponding direct trajectory before the run reports
success. A baseline-only archive does not represent perturbations, so all condition-specific SBML
files are included. Export/replay was verified without optional PhraSEDML.

Replay tests reproducibility of the represented experiment on this runtime. It does not test
biological plausibility, independent model calibration, cross-simulator numerical agreement or
interoperability of unexercised SED-ML features. Preserve the source model, full config and report
alongside the archive, including warnings and exact runtime versions.
