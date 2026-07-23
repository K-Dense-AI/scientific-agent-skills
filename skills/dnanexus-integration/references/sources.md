# Sources and Version Baseline

## Verification

Last verified: **2026-07-23**

| Component | Verified baseline |
|---|---|
| DNAnexus Platform docs | 2026 documentation and release notes through 2026-07-21 |
| dx-toolkit / dxpy | 0.410.0, released 2026-07-14 |
| Python requirement | Python 3.8+ on PyPI |
| App Execution Environment | Ubuntu 24.04 and 20.04, version `0` |
| dxCompiler | 2.17.0 |
| Upload Agent | 1.5.33 |
| Download Agent | 0.6.3 |
| dxFUSE | 1.6.1 |
| Nextaur | 1.13.0 |
| Nextflow engines exposed by dx-toolkit 0.410.0 | 25.10 and 24.10 |
| Nextflow 25.10 asset baseline | Nextflow 25.10.4 with nf-amazon 3.4.4 |

Version-specific examples in this skill are pinned for reproducibility. Before
upgrading, inspect release notes, run `scripts/inspect_dxpy.py`, and rebuild/test
apps in a non-production project.

## Documentation Index and Releases

- [DNAnexus documentation index (`llms.txt`)](https://documentation.dnanexus.com/llms.txt)
- [DNAnexus 2026 release notes](https://documentation.dnanexus.com/release-notes.md)
- [Downloads](https://documentation.dnanexus.com/downloads.md)
- [Index of `dx` commands](https://documentation.dnanexus.com/user/helpstrings-of-sdk-command-line-utilities.md)
- [dx-toolkit GitHub repository](https://github.com/dnanexus/dx-toolkit)
- [dx-toolkit changelog](https://github.com/dnanexus/dx-toolkit/blob/master/CHANGELOG.md)
- [dxpy on PyPI](https://pypi.org/project/dxpy/)
- [Generated Python API reference](https://autodoc.dnanexus.com/bindings/python/current/)

The release notes are date-versioned by platform deployment. The skill
baseline incorporates:

- 2026-07-21: dx-toolkit 410.0 malicious-file download warning
- 2026-07-14: strengthened session/password controls
- 2026-06-23: dxCompiler 2.17.0 authenticated WDL imports
- 2026-06-09: file download API `securityStatus`
- 2026-05-19: dxCompiler resource-retry support
- 2026-03-17: automatic upgrade on insufficient-resource retry
- 2026-02-03: retired instance type validation
- 2026-01-27: dynamic instance type selection

## Authentication

- [Login and Logout](https://documentation.dnanexus.com/user/login-and-logout.md)
- [Environment Variables](https://documentation.dnanexus.com/user/environment-variables.md)
- [dx-toolkit environment bootstrap](https://github.com/dnanexus/dx-toolkit/blob/master/environment)
- [API Authentication](https://documentation.dnanexus.com/developer/api/authentication.md)
- [API Protocols and Errors](https://documentation.dnanexus.com/developer/api/protocols.md)

Key current points:

- Environment variables override saved CLI configuration.
- `dx env` displays token material.
- Tokens without explicit expiry default to one month.
- Token revocation terminates associated active jobs/transfers.
- New interactive sessions use an 18-hour inactivity timeout.

## Apps and Applets

- [Introduction to Building Apps](https://documentation.dnanexus.com/developer/apps/intro-to-building-apps.md)
- [Developer Quickstart](https://documentation.dnanexus.com/getting-started/developer-quickstart.md)
- [App Metadata (`dxapp.json`)](https://documentation.dnanexus.com/developer/apps/app-metadata.md)
- [I/O and Run Specifications](https://documentation.dnanexus.com/developer/api/running-analyses/io-and-run-specifications.md)
- [App Execution Environment](https://documentation.dnanexus.com/developer/apps/execution-environment.md)
- [App Permissions](https://documentation.dnanexus.com/developer/apps/app-permissions.md)
- [Types of Errors](https://documentation.dnanexus.com/developer/apps/error-information.md)
- [Developing Apps and Applets FAQ](https://documentation.dnanexus.com/faqs/developing-apps-and-applets.md)

Dependencies:

- [Dependency management](https://documentation.dnanexus.com/developer/apps/dependency-management.md)
- [Python packages in Ubuntu 24.04 AEE](https://documentation.dnanexus.com/developer/apps/dependency-management/python-package-installation-in-ubuntu-24-04-aee.md)
- [Asset Build Process](https://documentation.dnanexus.com/developer/apps/dependency-management/asset-build-process.md)
- [Docker Images](https://documentation.dnanexus.com/developer/apps/dependency-management/using-docker-images.md)

## Data and Projects

- [Uploading and Downloading Files](https://documentation.dnanexus.com/user/objects/uploading-and-downloading-files.md)
- [`dx upload`](https://documentation.dnanexus.com/user/objects/uploading-and-downloading-files/small-sets-of-files/uploading-using-dx.md)
- [`dx download`](https://documentation.dnanexus.com/user/objects/uploading-and-downloading-files/small-sets-of-files/downloading-using-dx.md)
- [Upload Agent](https://documentation.dnanexus.com/user/objects/uploading-and-downloading-files/batch/upload-agent.md)
- [Download Agent](https://documentation.dnanexus.com/user/objects/uploading-and-downloading-files/batch/download-agent.md)
- [Download Agent repository](https://github.com/dnanexus/dxda)
- [Download Agent 0.6.3 release](https://github.com/dnanexus/dxda/releases/tag/v0.6.3)
- [dxFUSE 1.6.1 release](https://github.com/dnanexus/dxfuse/releases/tag/v1.6.1)
- [Data Object Lifecycle](https://documentation.dnanexus.com/developer/api/data-object-lifecycle.md)
- [Files API](https://documentation.dnanexus.com/developer/api/introduction-to-data-object-classes/files.md)
- [Data Object Metadata](https://documentation.dnanexus.com/developer/api/introduction-to-data-object-metadata.md)
- [Folders and Deletion](https://documentation.dnanexus.com/developer/api/data-containers/folders-and-deletion.md)
- [Cloning](https://documentation.dnanexus.com/developer/api/data-containers/cloning.md)
- [Project Permissions and Sharing](https://documentation.dnanexus.com/developer/api/data-containers/project-permissions-and-sharing.md)
- [Project API Methods](https://documentation.dnanexus.com/developer/api/data-containers/projects.md)
- [Project Data Access Controls](https://documentation.dnanexus.com/getting-started/key-concepts/projects.md#project-data-access-controls)
- [Search API](https://documentation.dnanexus.com/developer/api/search.md)
- [Service Limits](https://documentation.dnanexus.com/developer/api/service-limits.md)

## Execution and Workflows

- [Running Apps and Workflows](https://documentation.dnanexus.com/user/running-apps-and-workflows.md)
- [Running Apps and Applets](https://documentation.dnanexus.com/user/running-apps-and-workflows/running-apps-and-applets.md)
- [Running Workflows](https://documentation.dnanexus.com/user/running-apps-and-workflows/running-workflows.md)
- [Monitoring Executions](https://documentation.dnanexus.com/user/running-apps-and-workflows/monitoring-executions.md)
- [Job Lifecycle](https://documentation.dnanexus.com/user/running-apps-and-workflows/job-lifecycle.md)
- [Execution Cost and Spending Limits](https://documentation.dnanexus.com/user/running-apps-and-workflows/jobs-and-cost-and-spending-limits.md)
- [Running Analyses API](https://documentation.dnanexus.com/developer/api/running-analyses.md)
- [Workflows and Analyses API](https://documentation.dnanexus.com/developer/api/running-analyses/workflows-and-analyses.md)
- [Building and Running Workflows](https://documentation.dnanexus.com/developer/workflows/building-and-running-workflows.md)
- [Importing Workflows](https://documentation.dnanexus.com/developer/workflows/importing-workflows.md)

## WDL, CWL, and Nextflow

- [dxCompiler repository](https://github.com/dnanexus/dxCompiler)
- [dxCompiler 2.17.0 release](https://github.com/dnanexus/dxCompiler/releases/tag/2.17.0)
- [dxCompiler release notes](https://github.com/dnanexus/dxCompiler/blob/develop/RELEASE_NOTES.md)
- [Running Nextflow Pipelines](https://documentation.dnanexus.com/user/running-apps-and-workflows/running-nextflow-pipelines.md)

Check these sources together. Platform documentation describes supported
integration behavior; compiler/tool release notes describe version-specific
language and runtime changes.

## Corrected Legacy Patterns

The previous skill version contained examples that should not be copied:

| Legacy pattern | Current guidance |
|---|---|
| `license: Unknown` | Skill is MIT; dxpy upstream is Apache-2.0 |
| Declaring `DX_SECURITY_CONTEXT` in skill metadata | Authenticate through CLI/named secret injection; never expose token |
| `dx build --app` only | `--app` remains an alias; current help documents `--create-app` |
| `dxapi` described as required | `dxapi` is optional |
| `runSpec.systemRequirements` | Deprecated in source manifests; use `regionalOptions.<region>.systemRequirements` |
| Top-level `resources` | Deprecated; use region-specific `resources` |
| Static instance list | Discover current regional types; retired types are rejected |
| `DXFile.open_file()` | Use `dxpy.open_dxfile()` |
| `name="*.bam"` without mode | Add `name_mode="glob"` |
| `ResourceNotFound` imported as dxpy exception | Inspect `DXAPIError.name` |
| `job.wait_on_done()` followed by state branch | It raises `DXJobFailureError` on failure |
| Runtime `pip install` as primary dependency strategy | Prefer pinned venv/assets/saved images |
| Pulling floating Docker tags | Pin digest and preferably store `docker save` tarball |
| `dxpy.dxlink(job.get_output_ref(...))` | Pass `get_output_ref()` directly |

## Refresh Procedure

When updating this skill:

1. Check [PyPI](https://pypi.org/project/dxpy/) for the current dxpy release and
   Python requirement.
2. Read platform release notes since the verification date.
3. Read dx-toolkit and dxCompiler release notes.
4. Run:

   ```bash
   uv run --with "dxpy==<new-version>" \
     "skills/dnanexus-integration/scripts/inspect_dxpy.py" --strict
   ```

5. Compare `dx build --help`, `dx run --help`, and search command help.
6. Test `dxapp.json` validation and a minimal build in a sandbox project.
7. Test representative file, job, analysis, WDL/CWL, and Nextflow workflows.
8. Update the date/version table and skill `metadata.version`.

Do not update examples from memory alone.
