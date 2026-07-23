# Operations and Troubleshooting

## Non-Secret Baseline

Start with:

```bash
dx --version
dx whoami
dx pwd
```

Do not run `dx env`, `dx env --bash`, or `ua --env` in captured output; they
display credentials.

Record:

- dx-toolkit/dxpy version
- User ID
- Project ID and region
- Exact object/execution ID
- UTC time window
- Operation attempted
- API request ID, if available

Do not record tokens, whole environments, signed URLs, or unredacted PHI.

## First Questions

1. Is the failure local, API-side, or inside a job?
2. Is the object a file, record, applet, workflow, job, or analysis?
3. Is the ID project-qualified?
4. Is the file closed and live?
5. Does the user have the required access?
6. Is an environment variable overriding saved CLI state?
7. Did the operation cross a region, billing entity, TRE, or restricted
   project boundary?
8. Is the execution using the intended app version and instance?
9. Is the failure deterministic or transient?
10. Would retrying incur charges without changing the cause?

## Authentication and Context

### Symptom

- `AuthError`
- `PermissionDenied`
- Unexpected user/project after `dx login`
- An object visible in the UI is invisible to the CLI

### Checks

```bash
dx whoami
dx pwd
```

Shell variables override `~/.dnanexus_config/environment.json`. If the saved
CLI state should win:

```bash
source "$HOME/.dnanexus_config/unsetenv"
dx whoami
dx pwd
```

If saved state should be discarded:

```bash
dx clearenv
```

Then authenticate again. Do not compare token values.

Also check:

- Token expiration/revocation
- Project membership and access level
- Organization license/policy
- Download restrictions
- TRE/Data Access Request association
- Whether the project/object is in another region

Do not solve a context error by broadening permissions automatically.

## Path and Object Resolution

### Symptom

- Ambiguous path
- Wrong object selected
- `ResourceNotFound`
- A script sees different data than the UI

### Checks

```bash
dx ls "project-xxxx:/folder"
dx find data \
  --path "project-xxxx:/folder" \
  --name "sample.bam" \
  --name-mode exact \
  --json
```

DNAnexus permits duplicate object names. For mutation, select by ID after
reviewing all matches.

Use project-qualified links:

```python
dxpy.dxlink("file-xxxx", "project-xxxx")
```

## Upload Problems

### File remains open/closing

Possible causes:

- Interrupted multipart upload
- A part never completed
- Upload process exited before closure
- Network loss

For Upload Agent, repeat the same command to resume. Use `--wait-on-close` for
automation that needs a closed file.

Inspect state by ID. A dependent job can be submitted while an input is open
or closing, but it remains `waiting_on_input`; do not expect compute to start
until the file closes.

Abandoned files can remain billable until platform cleanup or explicit
removal. Confirm the exact incomplete object before deleting it.

### Upload Agent creates `.gz`

This is expected for uncompressed inputs. Upload Agent compresses by default.
Use `--do-not-compress` when preserving original bytes or naming is required.

### Upload retries create duplicates

Upload Agent identifies resumable files from a signature that includes path,
size, modification time, compression mode, and chunk size. Changing those
inputs can create a new object.

Review incomplete/closed matches before using `--do-not-resume`.

## Download Problems

### Archived file

Archived files cannot be downloaded until unarchive completes. Confirm
retrieval cost and timing before requesting unarchive.

### Malicious-file warning

Current dx-toolkit warns when a file or generated download URL has been flagged
as malicious. Treat this as a stop condition:

1. Do not execute or preview the content.
2. Confirm the file ID and security status.
3. Ask whether an approved malware-containment environment exists.
4. Download only into that environment if explicitly authorized.

### Large batch is slow or fragile

Use Download Agent with a reviewed manifest. Check free space, run `progress`,
and use `inspect` after completion. Rerun the same manifest to repair missing
or checksum-mismatched parts.

## Job State Problems

### `waiting_on_input`

Check:

- Input files and linked hidden objects are closed.
- Upstream JBORs resolve.
- `depends_on` jobs reached `done`.
- The upstream execution did not fail.
- Input objects can be cloned into the execution context.

### `runnable` for a long time

Check:

- Instance availability in the region
- Spot wait policy and priority
- Retired or unavailable instance type
- Dynamic instance selector transitions
- User/org worker limits

Do not immediately switch to a larger/on-demand instance without estimating
cost.

### `waiting_on_output`

Check:

- Descendant jobs still running
- Output files still closing
- Unresolved output JBORs
- A child failed but the tree is still settling

## Failure Reasons

### `InputError`

- Inspect executable help and current input spec.
- Confirm classes and array shapes.
- Confirm required fields.
- Confirm files are closed and accessible.
- Use DNAnexus links, not local paths.

### `OutputError`

- Compare returned keys to `outputSpec`.
- Check every file output is a valid DNAnexus link.
- Check array versus scalar class.
- Check descendant output references.
- Ensure `job_output.json` contains `{}` when there are no outputs.

### `AppError`

Expected app-recognized problem. Follow the actionable message and fix input or
configuration. Do not retry unchanged.

### `AppInternalError`

Unexpected application failure or nonzero process exit:

1. Review `stdout`/`stderr`.
2. Identify the first failing command.
3. Check deterministic reproduction with a small fixture.
4. Fix and rebuild a new applet/app version.

### `AppInsufficientResourceError`

Review detailed metrics and determine whether memory or storage was exhausted.

Options:

- Increase the correct resource dimension.
- Reduce batch/scatter size.
- Stream data instead of loading it all.
- Use an automatic restart policy if idempotent.

Automatic instance upgrade requires the organization policy and a matching
restart count. It upgrades within the same family; it is not a substitute for
profiling.

### `ExecutionError` / dependency installation failure

Check:

- APT package exists in the selected Ubuntu release.
- `execDepends` package manager/name/version is valid.
- Ubuntu 24.04 Python dependency conflicts.
- Network host is allowlisted if a runtime download is unavoidable.
- Asset distribution/release matches the app.

Prefer a pinned asset, virtual environment, or saved container image over
runtime installation.

### `SpotInstanceInterruption`

This can be transient. Confirm the app is restartable/idempotent. Use a bounded
retry policy. For critical runs, consider high priority/on-demand after cost
approval.

### `JobTimeoutExceeded`

Check configured `timeoutPolicy` and platform 30-day limit. Splitting a
workflow is often safer than simply increasing the timeout.

### `CostLimitExceeded`

The configured cost limit terminated the execution. Review:

- Actual tree cost
- Retry count
- Intermediate outputs
- Instance sizes
- Number of subjobs
- Whether reuse was disabled

Do not raise the limit until the cause and new maximum are approved.

### `SpendingLimitExceeded` / `OrgExpired`

These are account/organization controls. Report the exact billing entity and
stop. Do not attempt to route charges to another account or project without
explicit authorization.

### `AuthError` in a long job

Job credentials inherit root authorization and have a limited lifetime. A
revoked/expired token can terminate the tree. Re-running requires a new
authorized launch; it does not resurrect the old job.

## Workflow Analysis Failures

For `partially_failed`:

1. Describe the analysis.
2. Identify failed and still-active stages.
3. Inspect the failing stage job and its tries.
4. Let independent stages finish only if useful and cost-approved.
5. Decide whether to terminate the remainder.
6. Rerun only required stages after fixing the cause.

Example:

```bash
dx find jobs --root-execution "analysis-xxxx" --all-jobs
dx watch "job-failed" --get-streams
```

For a rerun:

```bash
dx run --clone "analysis-xxxx" \
  --rerun-stage "stage-name" \
  --destination "project-xxxx:/reruns/run-001"
```

Review reuse and output-folder behavior before launch.

## Nextflow

### Import/build failure

- Confirm the organization has the Nextflow feature/license.
- Use current dx-toolkit.
- Pin repository tag/commit.
- Confirm only supported Nextflow versions are requested.
- Confirm private Git credential file is accessible.
- Inspect the remote builder job log.

### Process failure

The head job supervises subjobs. Find the failed child:

```bash
dx find jobs --root-execution "job-head" --all-jobs
dx watch "job-child" --get-streams
```

Check:

- Docker image digest and registry access
- Process `cpus`, `memory`, and `disk`
- Queue size (current maximum 1000)
- Output path and work directory
- Resume/cache session

### Resume failure

Current guidance allows at most 20 preserved sessions per project. Confirm the
target session exists and no other job is writing it. Clean old work/cache
folders only after explicit review.

## dxCompiler

### Compile failure

- Confirm dxCompiler and Java versions.
- Validate WDL with matching wdlTools.
- Upgrade, pack, and validate CWL 1.2.
- Check globally unique task/workflow names.
- Check strict type conversions.
- Pin imported source.

### Protected WDL import failure

Check per-domain token configuration without printing
`DXCOMPILER_WDL_IMPORT_BEARER_TOKENS`. Confirm:

- Host exactly matches the approved import domain.
- Token has not expired.
- Token can only read required source.
- Redirects do not send authorization to an unapproved domain.

## Debug Access

DNAnexus supports approved SSH/debug-hold workflows. These settings can expose
live job data and extend workspace lifetime.

Before enabling:

- Confirm organization policy.
- Restrict source IP/host masks.
- Use non-sensitive test data where possible.
- Do not copy credentials from the worker.
- Record who accessed the job and why.
- Clean up held workspaces.

`--clone` does not preserve SSH/debug flags. This is a safety property; do not
automatically add them back.

## Service Limits

Current documented defaults include:

- 200 API calls/second
- 100 running workers/user
- 10,000 objects/deletion request
- 100,000 objects/move request
- 400,000 objects/list request
- 255,000 project folders mounted in Linux
- 5 TB/file in AWS regions
- 4.75 TB/file in Azure regions

Limits can vary by region/account and change. Bound searches, paginate, use
batch APIs, and back off on throttling.

## Cost Review

Distinguish three independent controls:

1. **Execution cost limit** — optional per root execution tree; reaching it
   terminates that tree.
2. **Billing-account spending limit** — cumulative across billed projects;
   reaching it can terminate jobs and block new executions.
3. **Monthly project compute and egress limits** — separate licensed controls;
   compute limits can stop/block jobs, while egress limits can block transfers.

Increasing one limit does not bypass another. Project monthly behavior can also
depend on the billing organization's policy.

Before rerun or scale-up, report:

- Billing project/org
- Current accrued cost if visible
- Proposed instance and priority
- Number of workers/stages
- Retry and reuse settings
- Cost limit
- Expected data egress
- Preserved intermediate storage

Failed and terminated user jobs can still be billed. Platform-internal
failure billing differs by reason and customer contract.

## Destructive Operations

Require exact IDs and confirmation for:

- `dx rm` / object removal
- Recursive folder removal
- Project deletion
- Permission/member changes
- Archive/unarchive
- Token revocation
- App publication or authorized-user replacement

Never recursively remove `/`. Removal can also delete orphaned hidden linked
objects and cannot be undone.

`protected` and `destroyProtected` serve different purposes:

- `protected` raises project-data deletion from `CONTRIBUTE` to `ADMINISTER`.
- `destroyProtected` prevents whole-project destruction until an authorized
  administrator explicitly clears it.

Project destruction removes all objects and refuses to proceed with active
jobs unless `terminateJobs=true`. Never clear deletion protection or force
job termination as part of a generic cleanup request.

## Support Bundle

Provide only:

- dx-toolkit/dxpy version
- UTC timestamp
- User ID (if appropriate)
- Project ID/region
- Object, job, or analysis ID
- App/appet/workflow ID and version
- Failure reason/message
- API request ID
- Minimal redacted log excerpt
- Reproduction steps using non-sensitive data

Exclude:

- Tokens/security contexts
- Environment dumps
- Private registry/Git credentials
- Signed URLs
- PHI or proprietary filenames unless required and approved
