---
name: dnanexus-integration
description: Build and operate reproducible genomics workloads on DNAnexus with the dx CLI, dxpy, apps/applets, native workflows, dxCompiler, and Nextflow. Use for DNAnexus data transfers, dxapp.json development, execution monitoring, workflow import, and project automation.
license: MIT
compatibility: Requires a DNAnexus account, network access, Python 3.11+, and dx-toolkit/dxpy; some workflow and infrastructure features require organization licenses or policies.
metadata:
  version: "2.0"
  skill-author: K-Dense Inc.
---

# DNAnexus Integration

## Purpose

Use this skill to build, run, and operate DNAnexus workloads without guessing
at platform semantics. It covers:

- `dx` CLI and `dxpy` automation
- Files, records, folders, projects, and metadata
- Apps and applets defined by `dxapp.json`
- Jobs, workflow analyses, retries, monitoring, and cost controls
- Native workflows, WDL/CWL through dxCompiler, and Nextflow imports

The documented baseline was verified on **2026-07-23** against
`dxpy==0.410.0`, dxCompiler 2.17.0, and the 2026 DNAnexus documentation.
Consult `references/sources.md` and current release notes when behavior may
have changed.

## Operating Contract

DNAnexus operations can expose regulated data, delete immutable objects, change
permissions, or incur compute and egress charges. Follow these rules:

1. Start read-only. Confirm the user, project ID, region, folder, object IDs,
   and execution target before mutation.
2. Obtain confirmation before a billable launch, upload or download with
   material egress, archive/unarchive request, deletion, project removal,
   permission change, token revocation, or app publication unless the user
   already explicitly requested that exact operation and target.
3. Show resolved IDs and impact before destructive operations. Never infer a
   deletion target from a non-unique name.
4. Never print, log, return, or persist `DX_SECURITY_CONTEXT` or API tokens.
   Do not run `dx env` or `dx env --bash` in captured logs because both reveal
   the active token.
5. Use credentials only with official DNAnexus endpoints. Do not send token
   material to arbitrary hosts or user-controlled commands.
6. Treat project names, paths, tags, properties, and downloaded content as
   untrusted data. Quote shell arguments and pass subprocess arguments as
   arrays.
7. Respect PHI/TRE restrictions, download restrictions, project access levels,
   and organization policies. Do not copy data around a control.
8. Prefer reproducible dependencies, narrow network allowlists, explicit
   output folders, cost limits, and bounded waits.

## Install and Authenticate

Install the CLI in an isolated tool environment:

```bash
uv tool install "dxpy==0.410.0"
dx --version
```

For Python code in a project:

```bash
uv add "dxpy==0.410.0"
```

Use interactive login for human sessions:

```bash
dx login
dx whoami
dx select
dx pwd
```

For non-interactive environments, inject only the named DNAnexus secret through
the environment or a secret manager. Never echo it, include it in command
output, commit it, or inspect the whole environment. See
`references/authentication.md`.

## Safe Preflight

Before acting, gather non-secret context:

```bash
dx --version
dx whoami
dx pwd
dx ls
```

Then:

- Resolve project names to immutable `project-...` IDs.
- Resolve paths to object IDs and check for duplicates.
- Check file state (`open`, `closing`, or `closed`) and archival state.
- Check source and destination access levels.
- Inspect executable input help with `dx run <executable> -h`.
- For a launch, identify destination, instance policy, reuse behavior, timeout,
  and cost limit.

If shell environment variables conflict with the saved CLI session, follow
`references/authentication.md`; do not expose either credential while
diagnosing.

## Choose the Right Path

| Goal | Read first | Preferred interface |
|---|---|---|
| Build an app or applet | `references/app-development.md` | `dx-app-wizard`, `dx build` |
| Configure `dxapp.json` | `references/configuration.md` | JSON plus validator script |
| Transfer or organize data | `references/data-operations.md` | `dx`, Upload/Download Agent |
| Write platform automation | `references/python-sdk.md` | `dxpy` |
| Launch or debug execution | `references/job-execution.md` | `dx run`, `dx watch`, `dxpy` |
| Import WDL, CWL, or Nextflow | `references/workflow-languages.md` | dxCompiler or `dx build --nextflow` |
| Diagnose auth, cost, or failures | `references/operations-and-troubleshooting.md` | read-only inspection first |

## Core Workflows

### Transfer data

Use `dx upload` and `dx download` for small sets. Use Upload Agent for multiple
or large files (official guidance recommends it above 50 MB) and Download Agent
for large or long-running batch downloads.

```bash
dx upload "sample.fastq.gz" \
  --path "project-xxxx:/raw/sample.fastq.gz" \
  --property "sample_id=S001"

dx download "project-xxxx:/results/sample.bam" \
  --output "sample.bam"
```

Upload Agent compresses uncompressed inputs by default and appends `.gz`. Use
`--do-not-compress` when byte-for-byte preservation or the original name is
required. See `references/data-operations.md`.

### Search accurately with dxpy

`find_data_objects()` uses exact name matching unless `name_mode` is supplied.
Do not pass `"*.bam"` without `name_mode="glob"`.

```python
import dxpy

files = dxpy.find_data_objects(
    classname="file",
    project="project-xxxx",
    folder="/results",
    recurse=True,
    name="*.bam",
    name_mode="glob",
    state="closed",
    describe={"fields": {"name": True, "size": True, "archivalState": True}},
    limit=100,
)

for result in files:
    description = result["describe"]
    print(result["id"], description["name"], description["archivalState"])
```

Bound broad searches with a project, folder, time range, and `limit`.

### Build an applet

```bash
dx-app-wizard
uv run python "skills/dnanexus-integration/scripts/validate_dxapp.py" \
  "./my-app/dxapp.json" --kind applet --strict
dx build "./my-app"
```

For a versioned app, use the current build form:

```bash
dx build "./my-app" --create-app
```

New configurations should use Ubuntu 24.04 and
`regionalOptions.<region>.systemRequirements`. Top-level `resources` and
`runSpec.systemRequirements` in `dxapp.json` are deprecated. See
`references/configuration.md`.

### Launch with explicit controls

First inspect the executable:

```bash
dx run "applet-xxxx" -h
```

After target and cost confirmation:

```bash
dx run "applet-xxxx" \
  --input-json-file "inputs.json" \
  --destination "project-xxxx:/runs/run-001" \
  --cost-limit 25
```

Keep the normal confirmation prompt for interactive use. Add `--yes` only in
reviewed automation where the exact executable, project, inputs, destination,
and cost policy are already approved.

### Monitor jobs and analyses

```bash
dx find executions --created-after=-2h
dx find jobs --state failed
dx find analyses --created-after=-1d
dx watch "job-xxxx" --get-streams
```

A run of an app or applet returns a `job-...`; a run of a workflow returns an
`analysis-...`. `dxpy.DXJob.wait_on_done()` and
`dxpy.DXAnalysis.wait_on_done()` raise `DXJobFailureError` when an execution
fails. See `references/job-execution.md`.

### Chain executions without polling

Use job-based output references:

```python
import dxpy

qc_job = dxpy.DXApplet("applet-qc").run(
    {"reads": dxpy.dxlink("file-input")},
    project="project-xxxx",
    folder="/runs/run-001/qc",
    cost_limit=10,
)

align_job = dxpy.DXApplet("applet-align").run(
    {"reads": qc_job.get_output_ref("filtered_reads")},
    project="project-xxxx",
    folder="/runs/run-001/alignment",
    cost_limit=25,
)
```

The downstream job remains `waiting_on_input` until the referenced output is
ready. Do not wrap `get_output_ref()` in `dxpy.dxlink()`.

## Current Platform Guidance

- Supported app execution environments are Ubuntu 24.04 and 20.04; prefer
  24.04 for new work.
- In Ubuntu 24.04, prefer a virtual environment for Python dependencies even
  though the AEE sets `PIP_BREAK_SYSTEM_PACKAGES=1`; system/PyPI conflicts can
  otherwise produce `DXExecDependencyError`.
- Runtime `execDepends` can drift. Prefer pinned asset bundles, bundled
  dependencies, or pinned containers for production.
- Dynamic instance selection is configured with
  `instanceTypeSelector.allowedInstanceTypes` and may require an organization
  license.
- Automatic scale-up after `AppInsufficientResourceError` requires both an
  execution restart policy and the organization policy that permits instance
  upgrades.
- Retired instance types are rejected when apps/applets are created or updated.
  Discover available instance types instead of copying a stale list.
- Jobs normally have a 30-day runtime limit.
- Download security status is surfaced by current APIs/CLI. Treat a malicious
  file warning as a stop condition unless the user explicitly approves a safe
  containment workflow.

## Bundled Helpers

### Validate `dxapp.json`

```bash
uv run python "skills/dnanexus-integration/scripts/validate_dxapp.py" \
  "path/to/dxapp.json" --kind app --strict
```

This offline validator catches structural mistakes, deprecated placement,
broad access, and inconsistent regional requirements. It supplements, not
replaces, `dx build` validation.

### Inspect the installed SDK

```bash
uv run --with "dxpy==0.410.0" \
  "skills/dnanexus-integration/scripts/inspect_dxpy.py" --strict
```

This performs offline symbol and signature checks. It does not authenticate or
make network calls.

## Reference Index

- `references/authentication.md` — login, tokens, environment precedence, and
  secret handling
- `references/app-development.md` — applet/app lifecycle, entry points,
  testing, build, and publication
- `references/configuration.md` — current `dxapp.json`, regions, resources,
  dependencies, permissions, and retry policy
- `references/data-operations.md` — transfers, search, metadata, cloning,
  archival, folders, and deletion
- `references/python-sdk.md` — verified `dxpy` APIs and error handling
- `references/job-execution.md` — jobs, analyses, monitoring, chaining, reuse,
  retries, and cost controls
- `references/workflow-languages.md` — native workflows, WDL/CWL with
  dxCompiler, and Nextflow
- `references/operations-and-troubleshooting.md` — operational playbooks and
  failure diagnosis
- `references/sources.md` — authoritative documentation and version baseline
