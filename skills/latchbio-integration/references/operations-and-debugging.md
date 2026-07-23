# Operations, Registration, Debugging, and Execution

This reference targets the current stable CLI and SDK (`latch==2.76.8`).

## Authenticate and Select a Workspace

```bash
latch login
latch workspace
```

Select a known workspace by numeric ID:

```bash
latch workspace --id 12345
```

The active workspace controls unqualified `latch:///` paths, Registry access,
workflow registration, and programmatic execution. Surface it before a
destructive or costly action.

Do not read or print `~/.latch/token`. Use the CLI's supported login and token
handling.

## Registration

Basic remote registration:

```bash
latch register --yes --open .
```

Remote builds are the default:

```bash
latch register --remote .
```

Use a local Docker build only when intentional:

```bash
latch register --no-remote .
```

Important options:

```bash
# Register into another workspace
latch register --workspace-id 12345 .

# Mark the version as a release
latch register --mark-as-release .

# Register workflows from a non-default Python module
latch register --workflow-module wf.custom_entrypoint .

# Use a specific Dockerfile
latch register --dockerfile Dockerfile.release .

# Plain build output for CI logs
latch register --docker-progress plain .
```

### Version behavior

Registration combines the project `version` with automatic content/version
information unless disabled. Do not disable automatic versioning merely to
force an overwrite.

A duplicate workflow registration exits with status `2`. CI should distinguish
that from status `1`, which indicates registration failure.

### Release behavior

Before `--mark-as-release`:

- Pin SDK, Python, system, and scientific dependencies.
- Record tool and database versions.
- Run a representative launch plan.
- Confirm result links and metadata.
- Verify the source commit is clean and reproducible.

## Staging and Development Shell

Build an image without publishing a workflow version:

```bash
latch register --staging .
```

Open a remote interactive shell in that image:

```bash
latch develop .
```

Choose a development instance:

```bash
latch develop . --instance-size small_gpu_task
```

Use `latch develop --help` to inspect the installed version's supported sizes.

### Sync behavior

- Local files under the workflow root are synced into the container.
- Files outside that root are not synced.
- Local updates overwrite corresponding container files.
- Local deletions do not remove existing container files.
- Container-side edits are not synced back and can be overwritten.
- `.gitignore` and `.dockerignore` are respected.
- Re-run staging registration after changing the Dockerfile or dependencies.

Place small test fixtures under the project root and exclude private or large
data from registration archives.

## Debug a Running Task

Open an interactive shell for an execution or task:

```bash
latch exec --execution-id <execution-id>
```

For a Nextflow work directory:

```bash
latch nextflow attach --execution-id <execution-id>
```

Use interactive access for diagnosis, not for modifying the source of record.
Reproduce and fix the issue locally, then register a new version.

## Programmatic Execution

The old `latch launch` CLI is deprecated. Use
`latch_cli.services.launch.launch_v2`.

### Launch with Python parameters

```python
import asyncio

from latch.types import LatchFile
from latch_cli.services.launch.launch_v2 import launch

execution = launch(
    wf_name="my_workflow",
    version="1.2.3-abcd12",
    params={
        "reads": LatchFile("latch:///test-data/reads.fastq.gz"),
        "minimum_quality": 20,
    },
)

completed = asyncio.run(execution.wait())
if completed is None:
    raise RuntimeError("execution polling ended without a result")
if completed.status != "SUCCEEDED":
    raise RuntimeError(
        f"execution {completed.id} ended with {completed.status}"
    )

print(completed.output)
print([path.path for path in completed.ingress_data])
```

`wf_name` is the registered workflow name (check `.latch/workflow_name` or the
Console), not the human-readable metadata display name.

`launch` defaults `best_effort=True`, allowing compatible dictionaries,
dataclasses, strings for enum values, and other schema-guided conversions.
Set `best_effort=False` only when the caller imports exactly the same Python
types as the registered workflow.

Compatibility:

- Programmatic launch requires workflows registered with SDK 2.62.0+.
- Typed output decoding requires workflows registered with SDK 2.65.1+.
- Python versions and imported classes must remain compatible for strict
  serialized type decoding.

### Launch a registered launch plan

```python
import asyncio

from latch_cli.services.launch.launch_v2 import launch_from_launch_plan

execution = launch_from_launch_plan(
    wf_name="my_workflow",
    version="1.2.3-abcd12",
    lp_name="Small public example",
)

completed = asyncio.run(execution.wait())
if completed is None or completed.status != "SUCCEEDED":
    raise RuntimeError("launch-plan execution did not succeed")
```

### Poll or abort

`Execution` exposes:

- `id`
- `status`
- `poll()`
- async `wait()`
- `abort()`

Abort only the intended active execution:

```python
if execution.status not in {"SUCCEEDED", "FAILED", "ABORTED"}:
    execution.abort()
```

## Interactive Execution Through MCP

When Latch MCP is available:

1. List workspaces.
2. List workflows.
3. Fetch the selected workflow schema.
4. Validate parameters.
5. Obtain confirmation for paid compute.
6. Launch.
7. Poll execution state.
8. Fetch task logs only for relevant failed or running nodes.

MCP authorization is separate from SDK login. See
`references/latch-mcp.md`.

## Monitoring

Console execution monitoring provides:

- Overall execution status
- Graph and task-node status
- Inputs and outputs
- Logs
- Provenance and result files
- Resource monitoring

The 2.76.8 CLI still provides the following deprecated command:

```bash
latch get-executions
```

The official CLI guide says it will be removed in a future version. Prefer the
Console or Latch MCP for new monitoring integrations.

For every production workflow, emit:

- Concise `message()` calls for actionable warnings and errors
- Result links for high-value outputs
- Normal structured logs for detailed diagnostics

Do not log secrets or signed URLs.

## Troubleshooting

### Authentication failure

```bash
latch login
latch workspace
```

Confirm the workspace is the one containing the data, workflow, and Registry
objects. Do not attempt to repair authentication by modifying token files.

### Registration cannot find the workflow

- Confirm the workflow root and `wf` package.
- Check `--workflow-module`.
- Compile the Python package.
- Verify metadata imports do not perform network calls.
- Inspect task-specific Dockerfile arguments; they must be string literals.

### Build failure

- Reproduce through staging registration.
- Use `--docker-progress plain`.
- Check `.dockerignore` did not omit required files.
- Confirm system packages and architecture.
- Use `--no-remote` only when the local Docker environment is known-good.

### Runtime import or executable failure

- Enter `latch develop`.
- Check `which python3`, installed packages, `$PATH`, and executable permissions.
- Run the task-level test script inside the image.
- Rebuild staging after dependency changes.

### Out of memory or storage

- Inspect resource monitoring.
- Measure peak rather than average use.
- Adjust one resource dimension at a time.
- See `references/resource-configuration.md`.

### Programmatic launch type error

- Fetch the workflow's current schema/version.
- Verify every required parameter.
- Use `best_effort=True` for compatible external representations.
- Re-register old workflows with a current SDK when typed outputs are needed.

## Official Sources

- CLI commands: https://wiki.latch.bio/workflows/sdk/cli/commands
- Development and debugging: https://wiki.latch.bio/workflows/sdk/testing-and-debugging-a-workflow/development-and-debugging
- Programmatic execution: https://wiki.latch.bio/workflows/sdk/testing-and-debugging-a-workflow/programmatic-execution
- Execution monitoring: https://wiki.latch.bio/workflows/sdk/console/execution-monitoring
- Resource monitoring: https://wiki.latch.bio/workflows/sdk/console/resource-monitoring
- Versioning: https://wiki.latch.bio/workflows/sdk/console/versioning
- CLI source in the 2.76.8 release commit: https://github.com/latchbio/latch/blob/0faa9dcd8186444ac008f50adf95d43f0fa30e06/src/latch_cli/main.py
