# Current `dxapp.json` Configuration

## What `dxapp.json` Controls

`dxapp.json` is the source manifest consumed by `dx build` and
`dx build --create-app`. It describes:

- App metadata and version
- Input and output contracts
- Entry-point interpreter and source file
- Application Execution Environment (AEE)
- Dependencies
- Timeout and restart policies
- Requested project, network, and developer permissions
- Region-specific resources

Do not confuse the source manifest with the canonical API payload produced by
the build tool. For field constraints, the API methods `/applet/new`,
`/app/new`, and the I/O and Run Specifications are authoritative.

## Applets Versus Apps

| Requirement | Applet | App |
|---|---|---|
| `name` | Required | Required |
| `runSpec` | Required | Required |
| `version` | Optional | Required |
| `inputSpec` | Recommended | Required |
| `outputSpec` | Recommended | Required |
| Region | Build project region | Declare supported regions |
| Lifecycle | Project data object | Versioned, publishable executable |

An applet without both input and output specifications cannot be added as a
workflow stage.

## Minimal Applet

This is valid JSON; comments are intentionally omitted.

```json
{
  "name": "qc-fastq",
  "inputSpec": [
    {
      "name": "reads",
      "class": "file",
      "patterns": ["*.fastq", "*.fastq.gz"],
      "help": "Input FASTQ file"
    }
  ],
  "outputSpec": [
    {
      "name": "report",
      "class": "file",
      "patterns": ["*.html"]
    }
  ],
  "runSpec": {
    "interpreter": "python3",
    "file": "src/qc_fastq.py",
    "distribution": "Ubuntu",
    "release": "24.04",
    "version": "0"
  }
}
```

The `dxapi` field is optional; it is not a required manifest field.

## Production App Skeleton

Replace the region and instance type with values available to the target
project. Do not copy a static instance list from old documentation.

```json
{
  "name": "qc-fastq",
  "title": "FASTQ quality control",
  "summary": "Creates a quality-control report for one FASTQ file",
  "version": "1.0.0",
  "inputSpec": [
    {
      "name": "reads",
      "label": "Reads",
      "class": "file",
      "patterns": ["*.fastq.gz"],
      "help": "A gzip-compressed FASTQ file"
    }
  ],
  "outputSpec": [
    {
      "name": "report",
      "label": "QC report",
      "class": "file",
      "patterns": ["*.html"]
    }
  ],
  "runSpec": {
    "interpreter": "python3",
    "file": "src/qc_fastq.py",
    "distribution": "Ubuntu",
    "release": "24.04",
    "version": "0",
    "timeoutPolicy": {
      "main": {"hours": 4}
    },
    "executionPolicy": {
      "restartOn": {
        "ExecutionError": 1,
        "UnresponsiveWorker": 2,
        "SpotInstanceInterruption": 2
      },
      "maxRestarts": 3
    }
  },
  "access": {
    "network": []
  },
  "regionalOptions": {
    "aws:us-east-1": {
      "systemRequirements": {
        "main": {
          "instanceType": "mem2_ssd1_v2_x4"
        }
      }
    }
  }
}
```

Run the bundled offline check before building:

```bash
uv run python "skills/dnanexus-integration/scripts/validate_dxapp.py" \
  "path/to/dxapp.json" --kind app --strict
```

## Input and Output Specifications

Common classes:

- Primitives: `string`, `int`, `float`, `boolean`, `hash`
- Data objects: `file`, `record`, `applet`
- Arrays: `array:string`, `array:int`, `array:file`, and so on

Every parameter needs a unique `name` and a `class`. Useful optional fields
include:

- `label`
- `help`
- `optional`
- `default`
- `choices`
- `patterns`
- `suggestions`
- `group`

Use `patterns` as a user-interface hint, not as a security or content
validation boundary. Validate actual content in app code.

Defaults must match the declared class. File and record defaults use DNAnexus
links, not raw local paths.

## `runSpec`

For the source manifest, set:

```json
{
  "runSpec": {
    "interpreter": "python3",
    "file": "src/main.py",
    "distribution": "Ubuntu",
    "release": "24.04",
    "version": "0"
  }
}
```

Supported combinations at the current baseline:

- Ubuntu 24.04, environment version `0`, `python3` or `bash`
- Ubuntu 20.04, environment version `0`, `python3` or `bash`

Prefer Ubuntu 24.04 for new development. Use 20.04 only for a tested
compatibility requirement and plan migration.

## Regional Resources

### Current placement

For new manifests, place resource requirements under:

```text
regionalOptions.<region>.systemRequirements.<entry-point>
```

The older locations below are deprecated:

- `runSpec.systemRequirements`
- top-level `resources`

They remain accepted for some single-region compatibility cases but should not
be used in new apps.

If one region declares `systemRequirements`, declare it for every region
listed in `regionalOptions`. Region-bound asset and resource IDs must also be
available in the corresponding region.

### Fixed instance type

```json
{
  "regionalOptions": {
    "aws:us-east-1": {
      "systemRequirements": {
        "main": {"instanceType": "mem2_ssd1_v2_x4"},
        "process": {"instanceType": "mem3_ssd1_v2_x8"}
      }
    }
  }
}
```

Available instance types differ by cloud and region. Retired types are rejected
when an app or applet is created or updated.

### Dynamic instance selection

Where licensed, provide an ordered fallback list:

```json
{
  "regionalOptions": {
    "aws:us-east-1": {
      "systemRequirements": {
        "main": {
          "instanceTypeSelector": {
            "allowedInstanceTypes": [
              "mem1_ssd1_v2_x4",
              "mem1_ssd1_v2_x8",
              "mem2_ssd1_v2_x4"
            ]
          }
        }
      }
    }
  }
}
```

`instanceTypeSelector` is mutually exclusive with `instanceType` and
`clusterSpec` for the same entry point. The platform initially gives each
allowed type 10 minutes in list order. If none provisions, it repeats the list
with doubled windows (20 minutes, then 40, and so on); normal-priority jobs
apply the same sequence to on-demand fallback after Spot wait expires. The job
description records attempts in `instanceTypeTransitions`.

### Clusters

Cluster requests use `clusterSpec` in an entry point's system requirements.
Current cluster types are `dxspark`, `apachespark`, and `generic`. Spark
versions and instance availability change; consult the live I/O and Run
Specifications instead of hardcoding an old value.

## Retry and Timeout Policy

Example:

```json
{
  "runSpec": {
    "executionPolicy": {
      "restartOn": {
        "AppInsufficientResourceError": 2,
        "ExecutionError": 1,
        "JMInternalError": 1,
        "UnresponsiveWorker": 2,
        "SpotInstanceInterruption": 3,
        "*": 0
      },
      "maxRestarts": 4
    },
    "timeoutPolicy": {
      "main": {"hours": 12},
      "process": {"hours": 2}
    },
    "restartableEntryPoints": "all"
  }
}
```

Use retries only for failures that can plausibly recover. Retrying
deterministic `AppError` or invalid input wastes money.

`maxRestarts` is the total restart ceiling across failure reasons. It must be a
non-negative integer below 10 and defaults to 9; set a smaller explicit bound
for cost control.

Automatic upgrade after `AppInsufficientResourceError` requires:

1. An applicable `restartOn` count.
2. The organization policy that permits instance upgrade on restart.
3. A larger instance in the same family.

If dynamic selection was used initially, an insufficient-resource retry uses
the platform's upgrade decision rather than the original selector list.

Jobs normally have a 30-day maximum runtime. Set a shorter workload-specific
timeout whenever possible.

## Dependencies

Choose the most reproducible workable option:

1. **Bundled source/resources** for small, version-controlled files.
2. **Asset bundles** for reusable system and Python environments.
3. **Saved Docker image tarballs** stored as project data or assets.
4. **`execDepends`** for simple APT dependencies when drift is acceptable.
5. **Runtime downloads** only when unavoidable and integrity-checked.

### Bundled resources

Files under `resources/` are packaged by `dx build` and unpacked into the AEE.
Do not bundle secrets, private keys, or mutable credentials.

### `execDepends`

Runtime package repositories can change between executions. Pin versions where
the package manager supports it and do not rely on floating packages for
regulated or production workloads.

On Ubuntu 24.04 AEE, `PIP_BREAK_SYSTEM_PACKAGES=1` is set for compatibility,
but PyPI packages can still conflict with APT-managed Python packages and cause
`DXExecDependencyError`.

Prefer a virtual environment:

```bash
python3 -m venv "/home/dnanexus/venv"
source "/home/dnanexus/venv/bin/activate"
python3 -m pip install --requirement "requirements.txt"
```

Pin the requirements and build them into an asset for repeated production use.
For a Python command-line application, `pipx` can isolate the tool.

### Asset bundles

Asset source layout:

```text
my-asset/
├── dxasset.json
├── Makefile
└── resources/
```

Build it in an isolated platform worker:

```bash
dx build_asset "my-asset"
```

Set the asset distribution and release to match the app. For multi-region apps,
provide an asset available in each target region.

### Docker images

The Ubuntu 24.04 and 20.04 AEEs support the native Docker CLI. For production,
prefer:

1. Pin an image by immutable digest.
2. `docker save` it to a tarball.
3. Upload the tarball or include it in an asset.
4. Use `docker load` in the app.

This avoids a runtime registry dependency and can eliminate broad network
access. If a private registry must be used, provide credentials as an explicit
input or protected project object. Anyone with `VIEW` access to that project
may be able to read those credentials, so use a narrowly scoped pull-only
credential and confirm the project's membership.

## Access Requirements

Start with no external network:

```json
{
  "access": {
    "network": []
  }
}
```

For an app with default permissions, the platform clones declared inputs into
its temporary workspace, grants the job `CONTRIBUTE` only there, and clones
declared outputs back to the launch project. Omit `project` and `allProjects`
unless the app must directly read, modify, or delete existing project objects.
Applet defaults differ (`project` defaults to `VIEW`), so still declare only
the minimum access its behavior requires.

Request only what the app needs:

- `network`: explicit host allowlist; avoid `["*"]`
- `project`: launch-project level
- `allProjects`: access to other user projects
- `developer`: ability to create/modify or use unpublished apps

Effective project access never exceeds the launching user's access. Broad
`allProjects`, `ADMINISTER`, `developer`, and unrestricted network permissions
need explicit justification.

For an HTTPS app, configure `httpsApp` separately and define the required
shared access. Do not expose a service that returns credentials or protected
data without its own authorization checks.

## Validation Checklist

- JSON parses and contains no comments.
- `name` and app `version` follow platform constraints.
- Inputs and outputs have unique names and correct classes.
- App manifests include `version`, `inputSpec`, and `outputSpec`.
- AEE is Ubuntu 24.04 or intentionally retained 20.04.
- No deprecated top-level resource placement is used.
- Every configured region has compatible assets and resources.
- Instance types are available now in each region.
- Retry policy targets transient/recoverable errors.
- Timeout and launch-time cost limits are defined.
- Dependencies are pinned and integrity-controlled.
- Network and project access are least privilege.
- `dx build` succeeds in a non-production project before publication.
