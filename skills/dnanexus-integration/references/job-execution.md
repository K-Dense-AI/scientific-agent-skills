# Jobs, Analyses, and Execution

## Concepts

- **Job** (`job-...`): execution of one app or applet entry point.
- **Analysis** (`analysis-...`): execution of a workflow and its stages.
- **Origin execution**: user-initiated root of an execution tree.
- **Master job**: app/appet run with its own temporary workspace.
- **Subjob**: another entry point created with `/job/new`; normally shares its
  parent job's workspace.
- **Job-based object reference (JBOR)**: dependency on a field of another
  execution's future output.

Do not treat `analysis-...` as a job. Use `DXAnalysis` and
`find_analyses()` for workflow runs.

## Preflight for a Launch

Before a billable run:

1. Resolve executable to an immutable ID/version.
2. Inspect current input names and types.
3. Resolve every data path to a project-qualified link.
4. Confirm output project/folder.
5. Confirm billing entity and available permission.
6. Review instance/resource policy.
7. Review job reuse and forced reruns.
8. Set an appropriate timeout and cost limit.
9. Confirm tags/properties contain no sensitive values.
10. Obtain user approval unless the exact run was already requested.

Inspect CLI inputs:

```bash
dx run "applet-xxxx" -h
dx pwd
```

## Launch an App or Applet

Interactive confirmation is safest:

```bash
dx run "applet-xxxx" \
  --input-json-file "inputs.json" \
  --destination "project-xxxx:/runs/run-001" \
  --cost-limit 25
```

Use `--yes` only after automation has resolved and validated all targets.

With dxpy:

```python
import dxpy

job = dxpy.DXApplet(
    "applet-xxxx",
    project="project-xxxx",
).run(
    {
        "reads": dxpy.dxlink(
            "file-xxxx",
            "project-xxxx",
        ),
        "min_quality": 20,
    },
    project="project-xxxx",
    folder="/runs/run-001",
    name="S001 QC",
    priority="normal",
    tags=["qc"],
    properties={"sample_id": "S001"},
    cost_limit=25,
)

print(job.get_id())
```

Never launch by an ambiguous app name when version stability matters. Use an
app ID/version or an applet ID.

## Launch a Workflow

CLI:

```bash
dx run "workflow-xxxx" \
  --input-json-file "workflow-inputs.json" \
  --destination "project-xxxx:/runs/run-002" \
  --cost-limit 50
```

This returns an `analysis-...` ID.

Python:

```python
import dxpy

analysis = dxpy.DXWorkflow(
    "workflow-xxxx",
    project="project-xxxx",
).run(
    {
        "0.reads": dxpy.dxlink(
            "file-xxxx",
            "project-xxxx",
        )
    },
    project="project-xxxx",
    folder="/runs/run-002",
    cost_limit=50,
)
```

Workflow input keys can use:

- `"<stage-index>.<input-name>"`
- `"<stage-name>.<input-name>"`
- `"<stage-id>.<input-name>"`
- A promoted workflow-level input name

Use `dx run workflow-xxxx -h` rather than guessing stage keys.

## Lifecycle

Successful jobs normally pass:

```text
idle → runnable → running → done
```

Additional states:

- `waiting_on_input`: dependency, JBOR, or file closure not ready
- `waiting_on_output`: descendant/output closure not ready
- `restartable`: eligible for another try
- `restarted`: prior try was restarted
- `terminating`: teardown underway
- `debug_hold`: failed worker held for approved debugging
- `failed`: terminal failure
- `terminated`: terminal user/system termination

Analyses begin `in_progress` and finish `done`, `failed`, or `terminated`.
`partially_failed` means at least one stage failed while other stages remain
non-terminal.

Jobs normally have a 30-day runtime limit.

## Monitor

Recent executions:

```bash
dx find executions --created-after=-2h
dx find jobs --created-after=-2h
dx find analyses --created-after=-2h
```

Failures:

```bash
dx find jobs --state failed --created-after=-7d
dx find executions --include-restarted --created-after=-7d
```

Watch a job:

```bash
dx watch "job-xxxx"
dx watch "job-xxxx" --get-stdout
dx watch "job-xxxx" --get-stderr
dx watch "job-xxxx" --get-streams
dx watch "job-xxxx" --tree
```

`dx watch` is job-focused. Inspect workflow analyses through `dx find
executions`, `dx describe analysis-xxxx`, the Monitor UI, and individual stage
jobs.

Do not copy logs into public issues without checking for patient identifiers,
project names, signed URLs, or secrets written by app code.

## Wait Safely with dxpy

```python
from dxpy.exceptions import DXError, DXJobFailureError

try:
    job.wait_on_done(interval=10, timeout=6 * 60 * 60)
except DXJobFailureError:
    failure = job.describe(
        fields={
            "state": True,
            "failureReason": True,
            "failureMessage": True,
        }
    )
    print(
        failure.get("failureReason"),
        failure.get("failureMessage"),
    )
    raise
except DXError:
    # Timeout or SDK/API failure; execution may still be running.
    raise
```

A local wait timeout does not terminate the remote execution. Re-describe it
before deciding whether to continue waiting or request termination.

`DXAnalysis.wait_on_done()` follows the same pattern and raises
`DXJobFailureError` when a stage fails.

## Outputs

After success:

```python
description = job.describe(fields={"state": True, "output": True})
outputs = description["output"]
```

Output files may still briefly be closing before the job reaches `done`; the
platform waits for required outputs to resolve.

For a future output:

```python
reference = job.get_output_ref("aligned_bam")
```

This is a JBOR. Pass it directly as downstream input:

```python
index_job = dxpy.DXApplet("applet-index").run(
    {"bam": reference},
    project="project-xxxx",
    folder="/runs/run-001/index",
    cost_limit=10,
)
```

The downstream job remains `waiting_on_input` until the upstream field
resolves. If the upstream execution fails, the dependency fails rather than
silently receiving a missing value.

## Scatter/Gather with Subjobs

```python
import dxpy


@dxpy.entry_point("main")
def main(input_files):
    children = [
        dxpy.new_dxjob(
            fn_input={"input_file": item},
            fn_name="process",
        )
        for item in input_files
    ]

    gather = dxpy.new_dxjob(
        fn_input={
            "results": [
                child.get_output_ref("result")
                for child in children
            ]
        },
        fn_name="gather",
    )
    return {"combined": gather.get_output_ref("combined")}
```

Avoid creating thousands of tiny subjobs. Current default account service
limits include 100 running workers per user, and organizations can impose
additional limits.

## Job Reuse

DNAnexus can reuse prior successful jobs with equivalent executable, inputs,
instance request, and other relevant settings.

Reuse is desirable for deterministic workloads. Disable it only for a reviewed
reason:

```python
job = applet.run(
    inputs,
    project="project-xxxx",
    ignore_reuse=True,
    cost_limit=25,
)
```

For workflows, `rerun_stages` or `ignore_reuse_stages` can target specific
stages.

Forced recomputation can multiply cost. Confirm it before using:

```bash
dx run --clone "analysis-xxxx" \
  --rerun-stage "*" \
  --destination "project-xxxx:/reruns/run-003"
```

Quote `"*"` so the shell does not expand it.

## Instance Selection

Runtime override:

```python
job = applet.run(
    inputs,
    project="project-xxxx",
    instance_type="mem2_ssd1_v2_x8",
    cost_limit=25,
)
```

Workflow stages can use `stage_instance_types`.

Prefer manifest-level policies for maintained apps. Runtime overrides are
useful for diagnosis but reduce reproducibility and may change cost
substantially.

Dynamic instance selection uses an ordered
`instanceTypeSelector.allowedInstanceTypes` list in the executable's system
requirements. It is license-gated and mutually exclusive with a fixed instance
or cluster for that entry point. Provisioning initially tries each allowed
type for 10 minutes, then repeats the list with doubled windows.

## Automatic Restarts

Restartable failure reasons include:

- `UnresponsiveWorker`
- `ExecutionError`
- `JMInternalError`
- `AppInternalError`
- `AppInsufficientResourceError`
- `JobTimeoutExceeded`
- `SpotInstanceInterruption`

Do not blindly retry all failures. Input, output, and deterministic app errors
normally require a fix.

`executionPolicy.maxRestarts` caps total restarts across reasons. It must be a
non-negative integer below 10 and defaults to 9; choose a smaller explicit
bound to limit cost.

For insufficient memory/disk, automatic instance upgrade requires the
organization policy plus a `restartOn` count for
`AppInsufficientResourceError` (or applicable wildcard). The platform upgrades
within the same instance family until success, retry limit, or no larger
instance.

Use:

```bash
dx find executions --include-restarted
dx watch "job-xxxx" --try 0
```

to inspect prior tries.

## Cost Controls

`cost_limit` / `--cost-limit` terminates an execution when accumulated charges
exceed the threshold. For a workflow, it applies to the entire analysis tree.
It is separate from billing-account spending limits and licensed monthly
project compute/egress limits; any one of these can stop or block work.

Also control:

- Destination and preserved intermediate outputs
- Instance family/size
- Priority and Spot/on-demand behavior
- Timeout
- Retry count
- Reuse
- Number of subjobs
- Data egress

A failed or terminated user job can still be billable. Current platform errors
such as `InputError`, `OutputError`, `AppInternalError`,
`CostLimitExceeded`, and `JobTimeoutExceeded` may incur charges.

## Failure Triage

Describe a failed job:

```bash
dx describe "job-xxxx"
dx watch "job-xxxx" --get-streams
```

Triage by `failureReason`:

- `AppError`: expected input/data issue; follow app message
- `AppInternalError`: application defect or nonzero command
- `AppInsufficientResourceError`: memory/disk shortage
- `AuthError`: expired/revoked root authorization
- `CostLimitExceeded`: configured execution limit reached
- `SpendingLimitExceeded`: billing account limit
- `ExecutionError`: worker/platform/dependency setup issue
- `IncompleteUploads`: one or more input uploads incomplete
- `InputError`: invalid or unresolved input contract
- `OutputError`: invalid/missing output contract
- `JobTimeoutExceeded`: configured/platform runtime exceeded
- `SpotInstanceInterruption`: Spot worker reclaimed

Diagnosis sequence:

1. Capture execution ID, try number, state, reason, and request ID.
2. Inspect root and failing child in the execution tree.
3. Check inputs are closed, live, and accessible.
4. Check exact executable version and app metadata.
5. Check instance metrics and disk/memory.
6. Check dependency and network setup.
7. Decide whether failure is deterministic or transient.
8. Estimate rerun cost and obtain approval.
9. Clone/rerun with only the justified changes.

## Rerun

CLI:

```bash
dx run "applet-xxxx" \
  --clone "job-xxxx" \
  --destination "project-xxxx:/reruns/run-004"
```

Arguments supplied with `--clone` override copied settings. Debug and SSH
settings are not copied and should not be enabled casually.

Do not rerun until:

- Original cause is understood.
- Input/output targets remain correct.
- Reuse implications are understood.
- New instance or dependency changes are documented.
- Cost is approved.

## Termination

Termination is disruptive and billable work already performed is not refunded.
Confirm exact ID and affected execution tree:

```bash
dx terminate "job-xxxx"
```

Terminate an analysis using the appropriate analysis operation/UI after
confirming which stages and descendants are still active.

After termination, verify final states and identify incomplete outputs or open
files that require cleanup.
