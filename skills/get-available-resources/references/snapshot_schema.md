# Snapshot Schema 1.1

The detector emits one JSON object with sorted keys. Values vary by observation,
but field names and meanings are stable for schema `1.1`.

## Top-level contract

- `schema_version`: `"1.1"`.
- `snapshot_kind`: `"effective_resource_snapshot"`.
- `observed_at`: UTC observation time.
- `completeness`: `complete`, `complete_with_informational_notes`, or
  `partial`.
- `platform`: OS family, architecture, and Python version. Hostname is omitted.
- `privacy`: explicit redaction flags.
- `cpu`, `memory`, `disk`, `accelerators`: resource observations.
- `cgroup_v2`, `container`, `scheduler`: execution-context observations.
- `warnings`: bounded sorted warning records.
- `provenance`: bounded sorted source/status records.

Null means unavailable, not zero and not unlimited. Zero is used only when a
source explicitly establishes zero (for example, a named accelerator visibility
variable that hides all devices).

## CPU

`cpu.host`:

- `logical`: system-visible logical CPUs.
- `physical`: system-visible physical cores, or null. This value is not
  converted into an effective process count.

`cpu.process`:

- `affinity_logical`: size of the current affinity set when supported.
- `python_available_logical`: `os.process_cpu_count()` when supported.

`cpu.cgroup_v2`:

- `cpuset_logical`: count from `cpuset.cpus.effective`.
- `quota_cores`: most restrictive finite ancestor `cpu.max` ratio. This may be
  fractional.

`cpu.effective`:

- `capacity_cores`: minimum positive host/process/cgroup/scheduler capacity.
- `worker_ceiling`: conservative bounded floor for CPU process workers.
- `limiting_sources`: sources tied at that minimum.

The effective value is intentionally not called a physical-core count.

## Memory

`memory.host` preserves system-visible `total_bytes` and `available_bytes`.

`memory.cgroup_v2` preserves current-cgroup usage and hierarchical effective
limits:

- `current_bytes`
- `available_bytes`
- `high_bytes`
- `max_bytes`

`memory.effective`:

- `hard_limit_bytes`: minimum of finite host total, cgroup hard limit, and
  interpretable scheduler allocation.
- `available_bytes`: minimum of host available, hierarchical cgroup remaining,
  and scheduler upper bound.
- `pressure_threshold_bytes`: cgroup `memory.high`; it is not relabeled as a
  hard limit.
- `hard_limit_sources` and `available_limiting_sources`: tied minimum sources.

`memory.model` is `unified_cpu_gpu` on Apple silicon and `system_ram`
otherwise. Unified GPU memory is not added again as dedicated VRAM.

## Disk

- `capacity_bytes`: total working-filesystem capacity.
- `free_bytes`: filesystem free blocks.
- `user_available_bytes`: user-available blocks where the OS exposes them.
- `writable`: result of a non-writing access check.
- `writability_check`: makes clear that no write probe occurred.
- `scope`: `working_filesystem_path_redacted`.

None of these values proves that a filesystem or project quota permits a write
of the same size.

## Accelerators

`accelerators.devices` contains management-visible or explicitly
platform-inferred candidates:

- `vendor`: hardware vendor (`nvidia`, `amd`, `apple`, `intel`, or `unknown`).
  macOS display discovery retains the actual vendor while offering Metal as
  a backend candidate.
- `device_class`: keeps integrated and discrete GPU concepts distinct.
- `backend_candidate`: `cuda`, `rocm`, or `metal`.
- `management_query`: visibility evidence.
- `device_permission`: `not_tested`; a query does not prove device-node access.
- `runtime_compatibility`: `not_tested` in detector output.
- `memory.model`: dedicated, unified, device-reported pool, or unknown.
  AMD records use `reported_total_bytes`; `dedicated_total_bytes` stays null
  because a management query does not resolve shared-memory topology.
- `local_index`: local query index; stable UUIDs and PCI addresses are omitted.

`candidate_counts` is a query count, not a usable-device count.
`candidate_upper_bounds` conservatively intersects query count with parsed
visibility/allocation counts when available. These bounds concern management
records, not MIG/partition/runtime-device enumeration. `runtime_usable_devices` remains
null because no framework runtime is loaded.

`visibility_environment` includes only four allowlisted variable names. Raw
values are never emitted.

## Scheduler and cgroup

`scheduler.fields_read` lists allowlisted Slurm names that were present.
`scheduler.allocation` contains parsed bounded values and scopes.
`scheduler.enforcement` remains `unknown`; variables alone do not prove
confinement.

`cgroup_v2.scope` says only `root`, `non_root`, `unknown`, or `not_applicable`.
The cgroup path is not emitted. Scope is relative to the visible cgroup2 mount;
hidden ancestors and cgroup v1 constraints are outside this observation.
Unreadable or invalid membership keeps scope unknown.

`container.detected` requires a known marker. A `cgroup_limit` can appear as
evidence without asserting that the process is in a container.

## Warnings and provenance

Warnings use:

```json
{
  "code": "STABLE_MACHINE_CODE",
  "component": "cpu",
  "message": "Human-readable, sanitized explanation.",
  "severity": "info"
}
```

Probe exception text, stderr, paths, hostnames, device UUIDs, and broad
environment content are excluded.

Provenance uses:

```json
{
  "component": "cpu.process.affinity_logical",
  "source": "os.sched_getaffinity",
  "status": "ok"
}
```

Possible status values include `ok`, `unavailable`, `absent`, `skipped`,
`not_found`, `timeout`, `truncated`, `error`, and `parse_error`.

## Validation and diff

Validate:

```bash
python scripts/snapshot_tools.py validate resource-snapshot.json
```

Diff while ignoring `observed_at`:

```bash
python scripts/snapshot_tools.py diff before.json after.json
```

Use `--include-volatile` only when timestamp changes matter. Diff output is
bounded to 512 changes.

All helper inputs are regular, non-symlink JSON files no larger than 1 MiB.
Output defaults to stdout. Explicit file output is restricted to a `.json`
filename in the current directory, refuses overwrite unless `--force` is used,
and is opened with mode 0600 on POSIX. Windows privacy also depends on directory
ACLs. Forced output refuses non-regular files and hard links.

The planner retains schema version 1.1 and adds `recommendation.status`. A
known budget that cannot fit one worker yields `insufficient_memory`, zero
workers, and zero threads; no job should be launched. `review_required` means
CPU capacity or available RAM is unknown. `provisional` is still an estimate.
