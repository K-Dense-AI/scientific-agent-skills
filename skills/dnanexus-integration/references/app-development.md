# App and Applet Development

## Model

- **Applet**: immutable executable data object in one project; best for
  development, testing, and project-local tools.
- **App**: versioned executable that can be authorized, published, and run
  across projects/regions; best for maintained reusable products.
- **Job**: execution of an app or applet.
- **Entry point**: named function within an executable. `main` is used for a
  normal app/appet run; other entry points can be launched as subjobs.

Develop as an applet, test in a non-production project, then create and publish
an app only after reviewing code, permissions, dependencies, and regions.

## Source Layout

```text
my-app/
├── dxapp.json
├── src/
│   └── my_app.py
├── resources/
│   └── requirements.txt
└── test/
    ├── input.json
    └── expected.json
```

`resources/` is bundled into the executable. Never place tokens, private keys,
registry passwords, or patient data in it.

## Create a Skeleton

```bash
dx-app-wizard
```

The wizard supports templates such as:

- `basic`
- `parallelized`
- `scatter-process-gather`

The generated code is a starting point, not a production security boundary.
Review all access and dependency fields.

## Python Entry Point

```python
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import dxpy


@dxpy.entry_point("main")
def main(reads: dict[str, Any], min_quality: int = 20) -> dict[str, Any]:
    if not 0 <= min_quality <= 93:
        raise dxpy.AppError("min_quality must be between 0 and 93")

    input_path = Path("reads.fastq.gz")
    output_path = Path("filtered.fastq.gz")

    reads_file = dxpy.get_handler(reads)
    if not isinstance(reads_file, dxpy.DXFile):
        raise dxpy.AppError("reads must reference a DNAnexus file")

    dxpy.download_dxfile(reads_file, str(input_path))

    # Fixed executable + argv list; no shell interpretation of user input.
    subprocess.run(
        [
            "quality-filter",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--min-quality",
            str(min_quality),
        ],
        check=True,
    )

    report = dxpy.upload_local_file(
        str(output_path),
        wait_on_close=True,
    )
    return {"filtered_reads": dxpy.dxlink(report.get_id())}


dxpy.run()
```

Key points:

- `dxpy.get_handler()` accepts an ID or DNAnexus link.
- Pass subprocess arguments as a list. Do not use `shell=True` with inputs.
- Return a mapping whose keys exactly match `outputSpec`.
- Return file/record outputs as DNAnexus links.
- Use `AppError` for an expected, actionable user/input error.
- Do not catch every exception and convert it to success.

The Python execution template reads `job_input.json`, calls the selected entry
point with keyword arguments, and writes the returned mapping to
`job_output.json`.

## Bash Entry Point

```bash
#!/usr/bin/env bash

main() {
  dx download "$reads" --output "reads.fastq.gz"

  quality-filter \
    --input "reads.fastq.gz" \
    --output "filtered.fastq.gz" \
    --min-quality "$min_quality"

  filtered_reads="$(dx upload "filtered.fastq.gz" --brief)"
  dx-jobutil-add-output \
    "filtered_reads" "$filtered_reads" --class=file
}
```

The platform invokes Bash with error-exit behavior. Still quote variables,
validate scalar inputs, and avoid building command strings. Input values are
untrusted even when provided by a trusted platform user.

## Execution Environment

Current AEEs:

- Ubuntu 24.04, version `0`
- Ubuntu 20.04, version `0`

Jobs run on ephemeral workers. The platform:

1. Provisions the worker and app container.
2. Installs `execDepends`.
3. Configures API, networking, and logs.
4. Unpacks bundled dependencies and assets.
5. Runs the selected interpreter/entry point.
6. Captures `stdout` and `stderr`.
7. Processes `job_output.json` or `job_error.json`.
8. Destroys the workspace unless a supported debugging hold is requested.

Useful system-provided values include:

- `DX_JOB_ID`
- `DX_WORKSPACE_ID`
- `DX_PROJECT_CONTEXT_ID`
- `DX_RESOURCES_ID`
- `DX_SECURITY_CONTEXT`

Use `dxpy` rather than parsing these directly where possible. Never print the
security context.

Network access is restricted unless requested in app metadata. Prefer a domain
allowlist; do not request `["*"]` solely to install dependencies at runtime.

## Separate Pure Logic from Platform I/O

Do not use `python src/my_app.py` as the only local test. `dxpy.run()` expects
the platform execution contract.

Instead:

1. Put scientific logic in ordinary functions/modules.
2. Unit-test those functions with local files.
3. Keep the entry point as a thin download → validate → compute → upload
   adapter.
4. Test the packaged applet on DNAnexus with small non-sensitive fixtures.

Example:

```python
def build_command(
    input_path: str,
    output_path: str,
    min_quality: int,
) -> list[str]:
    if not 0 <= min_quality <= 93:
        raise ValueError("min_quality must be between 0 and 93")
    return [
        "quality-filter",
        "--input",
        input_path,
        "--output",
        output_path,
        "--min-quality",
        str(min_quality),
    ]
```

Test `build_command()` locally without credentials.

## Build

Validate offline:

```bash
uv run python "skills/dnanexus-integration/scripts/validate_dxapp.py" \
  "my-app/dxapp.json" --kind applet --strict
```

Build an applet:

```bash
dx build "my-app"
```

Build a versioned app:

```bash
dx build "my-app" --create-app
```

Use `dx build --help` from the installed toolkit for destination, overwrite,
regional, and advanced flags; these evolve with dx-toolkit.

After build:

```bash
dx describe "applet-xxxx"
dx run "applet-xxxx" -h
```

Verify:

- Input/output fields and defaults
- AEE release
- Regions and instance requirements
- Access and network requirements
- Dependency records/files
- Timeout and restart policy

## Test on Platform

Use a dedicated test project and explicit destination:

```bash
dx run "applet-xxxx" \
  --input-json-file "test/input.json" \
  --destination "project-test:/test-runs/run-001"
```

Keep interactive confirmation. Set a small cost limit for automation:

```bash
dx run "applet-xxxx" \
  --input-json-file "test/input.json" \
  --destination "project-test:/test-runs/run-002" \
  --cost-limit 5
```

Monitor:

```bash
dx watch "job-xxxx"
dx describe "job-xxxx"
```

Test:

- Required and optional inputs
- Malformed and incompatible inputs
- Empty and boundary-size data
- Output classes, names, and closed states
- Retry behavior and idempotency
- Network-denied behavior
- Resource exhaustion behavior
- Duplicate execution and reuse

## Subjobs and Parallelism

Only use subjobs for independent work large enough to justify worker startup.

```python
import dxpy


@dxpy.entry_point("main")
def main(items):
    jobs = [
        dxpy.new_dxjob(
            fn_input={"item": item},
            fn_name="process_item",
        )
        for item in items
    ]
    return {
        "results": [
            job.get_output_ref("result")
            for job in jobs
        ]
    }


@dxpy.entry_point("process_item")
def process_item(item):
    result = process_one(item)
    return {"result": result}


dxpy.run()
```

Do not wait synchronously for child jobs when output references can express the
dependency. Ensure every restartable entry point is idempotent before setting
`restartableEntryPoints` to `all`.

## Reuse and Idempotency

DNAnexus can reuse identical completed jobs. Preserve reuse for deterministic
workloads to save time and cost.

Disable reuse only when:

- The executable intentionally depends on untracked external state.
- A debugging run must execute again.
- The user explicitly requires recomputation.

If an app writes outside its output folder, uses the current time, downloads
floating resources, or mutates a shared record, document that behavior and
reconsider whether it is suitable for reuse/restarts.

## Errors

Use failure categories deliberately:

- `AppError`: expected user/data problem with an actionable message
- `AppInternalError`: unexpected application defect or nonzero process exit
- `AppInsufficientResourceError`: insufficient memory/storage condition
- `InputError` / `OutputError`: platform contract mismatch
- `DXExecDependencyError`: dependency installation failure

Do not mark partial scientific output as success. If safe partial results are
valuable, publish them under explicitly named diagnostic outputs and still
return the appropriate failure.

## Publish Checklist

- Source and dependency licenses reviewed
- App version incremented
- Inputs/outputs backward compatible or breaking change documented
- Reproducible assets/images pinned
- No embedded credentials or sensitive fixtures
- Network and project access minimized
- Supported regions tested
- Instance types currently available
- Timeouts, retries, and cost behavior tested
- Output metadata and scientific provenance included
- App source visibility (`openSource`) chosen intentionally
- Authorized users/orgs reviewed
- Applet test evidence retained
