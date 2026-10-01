# Setup and deployment

Reviewed against LaminDB 2.10.0, lamin-cli 1.19.3, and lamindb-setup 1.25.7.
Python 3.12 was executed; lamindb-core supports Python >=3.10,<3.15. Do not infer
compatibility only from the less restrictive lamindb metapackage metadata.

## Install a dedicated environment

```bash
uv venv --python 3.12
uv pip install 'lamindb==2.10.0' 'bionty==2.5.0' 'ipython==9.17.1'
source .venv/bin/activate
```

`lamindb` installs the data-science dependencies plus `bionty` and `pertdb`.
`lamindb-core==2.10.0` installs the namespace with fewer dependencies and is not
sufficient for the DataFrame/AnnData examples by itself. The reviewed full
release constrains AnnData <=0.13.2. Lock the resolved environment for production.

Optional extras are `gcp`, `zarr-v2` (normalized from `zarr_v2`), and `fcs`:

```bash
# Illustrative optional installs; choose only the needed formats/providers.
uv pip install 'lamindb[gcp,zarr-v2,fcs]==2.10.0'
```

Do not install `lamindb-wetlab` as a Lamin Labs module. The official `wetlab`
documentation redirects to `pertdb`, whose source belongs to `laminlabs/pertdb`.
The reviewed PyPI `lamindb-wetlab==0.0.1` metadata points elsewhere and does not
establish Lamin Labs provenance. Use `Record` for flexible lab entities and
`pertdb` for its documented perturbation registries; neither implies an
`Experiment` registry in an invented `lamindb_wetlab` namespace.

## Initialize and connect

Run initialization only in the intended new project/storage:

```bash
lamin init --storage ./storage --name biology-demo --modules bionty
lamin info
```

A local anonymous SQLite instance needs no login. A cloud storage location without
`--db` stores the SQLite database in that storage location; it is not a local-only
metadata database. Cloud SQLite uses synchronization/locking and has different
concurrency constraints from PostgreSQL.

For an existing instance:

```bash
lamin login                       # interactive API-key entry when private access is needed
lamin connect account/name --here # scope the default to this development directory
lamin info
lamin disconnect --here           # remove the local connection marker
```

Without `--here`, connect/disconnect changes the environment-wide default.
A running Python interpreter has its own connection state; use fresh processes
when testing different databases. Read-only discovery can use
`db = ln.DB("account/name")` and `db.Artifact...` without choosing a new global
default. This does not grant access to private data.

## Cloud storage and PostgreSQL

Source-verified examples, not cloud-write tests. Set `LAMIN_DB_URL` securely
outside the commands below; never display its value:

```bash
lamin init --storage s3://my-bucket/project --db "$LAMIN_DB_URL" --modules bionty
# Requires GCP extras and configured workload identity/application-default credentials:
lamin init --storage gs://my-bucket/project --db "$LAMIN_DB_URL" --modules bionty
# Custom S3-compatible endpoint, quoted to preserve the query string:
lamin init --storage 's3://my-bucket?endpoint_url=https://storage.example.org'
```

Authentication/authorization is separate at the Hub, database, and storage
layers. Prefer workload identity or a secret manager. Grant only the needed
bucket/prefix permissions, verify region/endpoint configuration, and use TLS.
Do not assume a PostgreSQL server alone enforces every desired user permission.
There is no universal PostgreSQL version claim in this skill; check the actual
Django/database deployment requirements and Lamin configuration.

## Cache, development directory, and modules

```bash
lamin settings cache-dir get
lamin settings cache-dir set /path/to/cache
lamin settings dev-dir set .
lamin settings modules get
```

In Python, `ln.settings.cache_dir` reports the cache path. `LAMIN_CACHE_DIR` can
override it and must be an absolute path. `LAMIN_SETTINGS_DIR` selects a base
under which `.lamin` settings are written; set it **before imports/CLI startup**.
Do not replace HOME to isolate Lamin settings.

For a disposable test, create fresh settings/cache/storage and run from a fresh
working directory so no parent `.lamin` marker selects a real instance. Never
use a production instance as a health-check write target. A metadata read such
as `ln.Artifact.filter().count()` checks database access only, not storage writes.

`lamin settings cache-dir clear` exists but deletes cached content; review the
cache ownership and active jobs first. `Artifact.delete_cache()` and
`is_cached()` are absent. Do not use recursive shared-cache deletion as a
standard repair. System-wide settings location is shown by `lamin info`; it is
not a fixed `/system/settings` path.

## Upgrades, backups, and transfer

Before an upgrade inspect the changelog, installed modules, and database
compatibility matrix; take a tested database/storage backup. After installing
the reviewed package set, the supported deployment command is:

```bash
lamin migrate deploy
```

This mutates the connected database. `lamin migrate check`, `history`, and
`plan` are not commands in lamin-cli 1.19.3. `lamin backup`, `lamin export`, and
`lamin instance invite/set-visibility/details` are not documented CLI commands
here either. Use your actual database backup tooling and LaminHub controls.
A raw export/re-import of files loses metadata and lineage; use the official
[transfer guide](https://docs.lamin.ai/transfer) for cross-database records and
storage policy, then verify both metadata and bytes.

Deletion is not a metadata-only cleanup guarantee. The actual CLI accepts
`lamin delete account/name` with confirmation and constraints on stored data;
inspect `lamin delete --help` and backups before destructive work. Do not add
`--force` as a routine troubleshooting step.

## Git source tracking

Set `LAMINDB_SYNC_GIT_REPO` outside the script, or set
`ln.settings.sync_git_repo` to the intended repository URL. Configure dev-dir
with the current syntax above. Inspect the captured transform/source metadata
instead of assuming `transform.hash` is a Git commit SHA; it is a content hash.
Only commit reviewed project files through the project's normal workflow.

Sources: [setup](https://docs.lamin.ai/setup), [CLI](https://docs.lamin.ai/cli),
[release dependencies](https://github.com/laminlabs/lamindb/blob/2.10.0/pyproject.toml),
[pertdb](https://docs.lamin.ai/pertdb).
