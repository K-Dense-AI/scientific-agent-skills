"""Synthetic, network-free tests for resource detection and planning."""

from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "get-available-resources"
SCRIPTS = SKILL_ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "resource_cases.json"
sys.path.insert(0, str(SCRIPTS))

import _common  # noqa: E402
import accelerator_diagnostics  # noqa: E402
import detect_resources  # noqa: E402
import plan_workload  # noqa: E402
import snapshot_tools  # noqa: E402

import skill_contract


CASES = json.loads(FIXTURES.read_text(encoding="utf-8"))
GIB = 1024**3


def canonical_snapshot() -> dict:
    return {
        "accelerators": {
            "candidate_counts": {"cuda": 1, "metal": 0, "rocm": 0},
            "candidate_upper_bounds": {"cuda": 1, "metal": None, "rocm": None},
            "devices": [
                {
                    "backend_candidate": "cuda",
                    "device_class": "gpu",
                    "device_permission": "not_tested",
                    "local_index": 0,
                    "management_query": "visible",
                    "memory": {
                        "dedicated_free_bytes": 20 * GIB,
                        "dedicated_total_bytes": 40 * GIB,
                        "model": "dedicated",
                    },
                    "name": "Synthetic GPU",
                    "runtime_compatibility": "not_tested",
                    "vendor": "nvidia",
                }
            ],
            "runtime_usable_devices": None,
            "visibility_environment": {},
        },
        "cgroup_v2": {"detected": True, "scope": "non_root"},
        "completeness": "complete_with_informational_notes",
        "container": {
            "detected": True,
            "evidence": ["cgroup_limit", "docker_marker"],
            "runtime": "docker_or_compatible",
        },
        "cpu": {
            "cgroup_v2": {"cpuset_logical": 4, "quota_cores": 3.5},
            "effective": {
                "capacity_cores": 3.5,
                "limiting_sources": ["cgroup_quota"],
                "worker_ceiling": 3,
            },
            "host": {"logical": 32, "physical": 16},
            "process": {
                "affinity_logical": 4,
                "python_available_logical": 4,
            },
        },
        "disk": {
            "capacity_bytes": 100 * GIB,
            "free_bytes": 60 * GIB,
            "scope": "working_filesystem_path_redacted",
            "user_available_bytes": 50 * GIB,
            "writable": True,
            "writability_check": "os_access_only_no_write_probe",
        },
        "memory": {
            "cgroup_v2": {
                "available_bytes": 8 * GIB,
                "current_bytes": 8 * GIB,
                "high_bytes": 14 * GIB,
                "max_bytes": 16 * GIB,
            },
            "effective": {
                "available_bytes": 8 * GIB,
                "available_limiting_sources": ["cgroup_memory_remaining"],
                "hard_limit_bytes": 16 * GIB,
                "hard_limit_sources": ["cgroup_memory_max"],
                "pressure_threshold_bytes": 14 * GIB,
            },
            "host": {"available_bytes": 32 * GIB, "total_bytes": 64 * GIB},
            "model": "system_ram",
            "swap": {"free_bytes": 2 * GIB, "total_bytes": 4 * GIB},
        },
        "observed_at": "2026-07-23T12:00:00Z",
        "platform": {
            "machine": "x86_64",
            "python_version": "3.13.5",
            "system": "Linux",
        },
        "privacy": {
            "absolute_paths_included": False,
            "environment_values_included": False,
            "hostnames_included": False,
            "identifiers_redacted_by_default": True,
        },
        "provenance": [
            {
                "component": "cpu.host.logical",
                "source": "os.cpu_count",
                "status": "ok",
            }
        ],
        "scheduler": {
            "allocation": {
                "cpu_per_process": 4,
                "cpus_on_node": 4,
                "gpus_per_process": 1,
                "gpus_on_node": 1,
                "memory_effective_bytes": 16 * GIB,
                "memory_scope": "shared_per_node",
                "tasks": 1,
            },
            "detected": True,
            "enforcement": "unknown",
            "fields_read": ["SLURM_CPUS_PER_TASK"],
            "kind": "slurm",
        },
        "schema_version": "1.1",
        "snapshot_kind": "effective_resource_snapshot",
        "warnings": [
            {
                "code": "ACCELERATOR_RUNTIME_NOT_TESTED",
                "component": "accelerators",
                "message": "Synthetic informational warning.",
                "severity": "info",
            }
        ],
    }


class CommonSafetyTests(unittest.TestCase):
    def test_force_does_not_truncate_another_hard_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target.json"
            alias = Path(directory) / "alias.json"
            target.write_text('{"keep":true}')
            os.link(target, alias)
            with mock.patch.object(_common.Path, "cwd", return_value=Path(directory)):
                with self.assertRaises(_common.ResourceToolError):
                    _common.emit_json({"keep": False}, "alias.json", force=True)
            self.assertEqual(target.read_text(), '{"keep":true}')

    def test_extreme_integer_is_rejected_without_overflow(self) -> None:
        self.assertIsNone(_common.bounded_number(10**1000))

    def test_stdout_is_default_and_file_output_is_private(self) -> None:
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            _common.emit_json({"ok": True})
        self.assertEqual(json.loads(captured.getvalue()), {"ok": True})

        old_cwd = Path.cwd()
        try:
            with tempfile.TemporaryDirectory() as directory:
                os.chdir(directory)
                _common.emit_json({"ok": True}, "resource-snapshot.json")
                output = Path("resource-snapshot.json")
                self.assertEqual(json.loads(output.read_text()), {"ok": True})
                self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
                with self.assertRaises(_common.ResourceToolError):
                    _common.emit_json({"ok": False}, "resource-snapshot.json")
                with self.assertRaises(_common.ResourceToolError):
                    _common.emit_json({"ok": False}, "../escape.json")
        finally:
            os.chdir(old_cwd)

    def test_snapshot_reader_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            real = Path(directory) / "snapshot.json"
            link = Path(directory) / "link.json"
            real.write_text("{}", encoding="utf-8")
            try:
                link.symlink_to(real)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaises(_common.ResourceToolError):
                _common.read_json_file(str(link))


class ParserTests(unittest.TestCase):
    def test_current_amd_smi_nested_units_preserve_memory(self) -> None:
        devices = detect_resources.parse_amd_json(json.dumps(CASES["amd_smi_current"]))
        self.assertEqual(devices[0]["memory"]["reported_total_bytes"], 192 * GIB)
        self.assertIsNone(devices[0]["memory"]["dedicated_total_bytes"])
        self.assertNotIn("private-synthetic-serial", json.dumps(devices))
        self.assertIsNone(detect_resources._amd_memory_bytes({"vram": {"size": "N/A"}}))
        self.assertIsNone(detect_resources._mib_to_bytes("1e308"))

    def test_intel_mac_display_keeps_actual_vendor(self) -> None:
        devices = detect_resources.parse_apple_profiler_json(json.dumps({
            "SPDisplaysDataType": [{"sppci_model": "AMD Radeon Pro", "spdisplays_vendor": "AMD"}]
        }), machine="x86_64")
        self.assertEqual(devices[0]["vendor"], "amd")
        self.assertEqual(devices[0]["backend_candidate"], "metal")
        self.assertEqual(devices[0]["memory"]["model"], "unknown")

    def test_cpu_list_is_counted_without_expansion(self) -> None:
        self.assertEqual(detect_resources.parse_cpu_list("0-3,6,8-9"), 7)
        self.assertEqual(detect_resources.parse_cpu_list("0-3,2-5"), 6)
        self.assertIsNone(detect_resources.parse_cpu_list("0-99999999"))
        self.assertIsNone(detect_resources.parse_cpu_list("0-3;echo unsafe"))

    def test_nvidia_csv_is_typed_and_does_not_expose_uuid(self) -> None:
        devices = detect_resources.parse_nvidia_csv(CASES["nvidia_csv"])
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["backend_candidate"], "cuda")
        self.assertEqual(devices[0]["compute_capability"], "9.0")
        self.assertEqual(devices[0]["runtime_compatibility"], "not_tested")
        self.assertNotIn("uuid", json.dumps(devices).lower())

    def test_amd_and_apple_accelerators_are_not_cuda(self) -> None:
        amd = detect_resources.parse_amd_json(
            json.dumps(CASES["amd_rocm_smi"])
        )
        apple = detect_resources.parse_apple_profiler_json(
            json.dumps(CASES["macos"]["profiler"]),
            machine="arm64",
        )
        self.assertEqual(amd[0]["backend_candidate"], "rocm")
        self.assertEqual(amd[0]["memory"]["reported_total_bytes"], 68702699520)
        self.assertEqual(apple[0]["backend_candidate"], "metal")
        self.assertEqual(apple[0]["memory"]["model"], "unified")
        self.assertEqual(apple[0]["device_class"], "integrated_gpu")

    def test_accelerator_probe_timeout_is_a_partial_warning(self) -> None:
        def fake_run(command: tuple[str, ...], timeout: float) -> dict:
            if command[0] == "nvidia-smi":
                return {"status": "timeout", "stdout": "", "stderr": ""}
            return {"status": "not_found", "stdout": "", "stderr": ""}

        warnings: list[dict[str, str]] = []
        provenance: list[dict[str, str]] = []
        result = detect_resources._detect_accelerators(
            system="Linux",
            machine="x86_64",
            environ={},
            scheduler={"allocation": {}},
            run_command=fake_run,
            warnings=warnings,
            provenance=provenance,
        )
        self.assertEqual(result["devices"], [])
        self.assertIn(
            "NVIDIA_QUERY_FAILED",
            {item["code"] for item in warnings},
        )
        self.assertIn(
            "timeout",
            {item["status"] for item in provenance},
        )


class LinuxCgroupTests(unittest.TestCase):
    def test_broad_mount_preserves_ancestors_over_nested_bind_mount(self) -> None:
        mountinfo = (
            "50 20 0:27 / /sys/fs/cgroup rw - cgroup2 cgroup rw\n"
            "51 20 0:27 /parent /run/cg rw - cgroup2 cgroup rw\n"
        )
        root, relative = detect_resources._resolve_cgroup_mount(mountinfo, ("parent", "task"))
        self.assertEqual(root, Path("/sys/fs/cgroup"))
        self.assertEqual(relative, ("parent", "task"))

    def test_delegated_mount_uses_mount_root(self) -> None:
        files = {
            "/proc/self/cgroup": "0::/parent/task\n",
            "/proc/self/mountinfo": "50 20 0:27 /parent /run/cg rw - cgroup2 cgroup rw\n",
            "/run/cg/cgroup.controllers": "cpu memory\n",
            "/run/cg/task/cgroup.controllers": "\n",
            "/run/cg/task/cpu.max": "50000 100000\n",
            "/run/cg/task/memory.max": "104857600\n",
            "/run/cg/task/memory.current": "20971520\n",
        }
        def reader(path):
            if str(path) not in files:
                raise FileNotFoundError()
            return files[str(path)]
        report = detect_resources.detect_cgroup_v2(read_text=reader)
        self.assertEqual(report["cpu_quota_cores"], 0.5)
        self.assertEqual(report["memory_available_bytes"], 80 * 1024**2)

    def test_bad_membership_does_not_substitute_root(self) -> None:
        files = {"/proc/self/cgroup": "0::/../other\n",
                 "/sys/fs/cgroup/cgroup.controllers": "cpu memory\n",
                 "/sys/fs/cgroup/cpu.max": "800000 100000\n"}
        def reader(path):
            if str(path) not in files:
                raise FileNotFoundError()
            return files[str(path)]
        warnings = []
        report = detect_resources.detect_cgroup_v2(read_text=reader, warnings=warnings)
        self.assertIsNone(report["cpu_quota_cores"])
        self.assertEqual(report["scope"], "unknown")
        self.assertIn("CGROUP_MEMBERSHIP_UNKNOWN", {item["code"] for item in warnings})

    def test_hierarchical_limits_use_most_restrictive_ancestor(self) -> None:
        case = CASES["linux_cgroup_v2"]
        files = case["files"]

        def reader(path: Path) -> str:
            try:
                return files[str(path)]
            except KeyError as exc:
                raise FileNotFoundError(str(path)) from exc

        report = detect_resources.detect_cgroup_v2(read_text=reader)
        for key, expected in case["expected"].items():
            self.assertEqual(report[key], expected, key)

    def test_cpu_quota_is_capacity_not_a_topology_count(self) -> None:
        effective = detect_resources._effective_cpu(
            {"logical": 64, "physical": 32},
            {"affinity_logical": 8, "python_available_logical": 8},
            {"cpuset_logical": 4, "cpu_quota_cores": 1.5},
            {"allocation": {"cpu_per_process": 2}},
        )
        self.assertEqual(effective["capacity_cores"], 1.5)
        self.assertEqual(effective["worker_ceiling"], 1)
        self.assertEqual(effective["limiting_sources"], ["cgroup_quota"])


class SchedulerTests(unittest.TestCase):
    def test_heterogeneous_slurm_node_does_not_inherit_first_node_tasks(self) -> None:
        env = {"SLURM_CPUS_ON_NODE": "16", "SLURM_TASKS_PER_NODE": "1(x2),4"}
        for index, expected in ((None, None), ("0", 16), ("2", None), ("10", None)):
            with self.subTest(index=index):
                current = dict(env)
                if index is not None:
                    current["SLURM_NODEID"] = index
                allocation = detect_resources.detect_scheduler(current)["allocation"]
                self.assertEqual(allocation["cpu_per_process"], expected)
        self.assertIsNone(detect_resources._parse_node_count("1junk", 0))

    def test_slurm_named_allocation_is_bounded_and_redacted(self) -> None:
        environment = dict(CASES["slurm"]["environment"])
        environment["UNRELATED_SECRET"] = "must-not-be-read"
        warnings: list[dict[str, str]] = []
        report = detect_resources.detect_scheduler(
            environment,
            warnings=warnings,
        )
        expected = CASES["slurm"]["expected"]
        for key, value in expected.items():
            self.assertEqual(report["allocation"][key], value, key)
        serialized = json.dumps(report)
        self.assertNotIn("12345", serialized)
        self.assertNotIn("must-not-be-read", serialized)
        self.assertNotIn("UNRELATED_SECRET", report["fields_read"])
        self.assertEqual(report["enforcement"], "unknown")

    def test_visibility_values_are_summarized_not_returned(self) -> None:
        value = "GPU-private-uuid,GPU-other-private-uuid"
        summary = detect_resources._visibility_summary(
            {"CUDA_VISIBLE_DEVICES": value}
        )
        serialized = json.dumps(summary)
        self.assertNotIn("GPU-private", serialized)
        self.assertEqual(
            summary["CUDA_VISIBLE_DEVICES"]["entry_count"],
            2,
        )


class PlatformMockTests(unittest.TestCase):
    def test_reserved_blocks_remain_distinct_from_user_available_space(self) -> None:
        with mock.patch.object(detect_resources.shutil, "disk_usage", return_value=SimpleNamespace(
            total=100 * GIB, free=50 * GIB
        )), mock.patch.object(detect_resources.os, "statvfs", return_value=SimpleNamespace(
            f_bfree=60, f_bavail=50, f_frsize=GIB
        ), create=True):
            disk = detect_resources._detect_disk([], [])
        self.assertEqual(disk["free_bytes"], 60 * GIB)
        self.assertEqual(disk["user_available_bytes"], 50 * GIB)

    def test_psutil_access_denied_does_not_discard_snapshot(self) -> None:
        class ProbeDenied(Exception):
            pass
        def fail(*args, **kwargs):
            raise ProbeDenied()
        fake = SimpleNamespace(Error=ProbeDenied, cpu_count=fail,
                               Process=lambda: SimpleNamespace(cpu_affinity=fail),
                               virtual_memory=fail, swap_memory=fail)
        snapshot = detect_resources.collect_snapshot(skip_accelerators=True, environ={}, psutil_module=fake)
        self.assertTrue(snapshot_tools.validate_snapshot(snapshot)["valid"])

    def test_host_count_does_not_inherit_python_override(self) -> None:
        with mock.patch.object(detect_resources.os, "cpu_count", return_value=1):
            cpu = detect_resources._detect_cpu_inventory(
                system="Darwin", psutil_module=None, mac_sysctl={"logical": 14, "physical": 14},
                read_text=lambda p: "", warnings=[], provenance=[])
        self.assertEqual(cpu["logical"], 14)

    def test_macos_sysctl_and_unified_memory(self) -> None:
        result = {
            "status": "ok",
            "stdout": CASES["macos"]["sysctl_stdout"],
            "stderr": "",
        }
        values = detect_resources._mac_sysctl_values(
            lambda command, timeout: result,
            [],
            [],
        )
        memory = detect_resources._detect_memory(
            system="Darwin",
            machine="arm64",
            psutil_module=None,
            mac_sysctl=values,
            cgroup={
                "memory_available_bytes": None,
                "memory_current_bytes": None,
                "memory_high_bytes": None,
                "memory_max_bytes": None,
            },
            scheduler={"allocation": {"memory_effective_bytes": None}},
            read_text=lambda path: (_ for _ in ()).throw(FileNotFoundError()),
            warnings=[],
            provenance=[],
        )
        self.assertEqual(values["logical"], 14)
        self.assertEqual(values["physical"], 14)
        self.assertEqual(memory["host"]["total_bytes"], 48 * GIB)
        self.assertEqual(memory["model"], "unified_cpu_gpu")

    def test_windows_psutil_affinity_and_processor_groups(self) -> None:
        case = CASES["windows"]

        class FakeProcess:
            def cpu_affinity(self) -> list[int]:
                return case["affinity"]

        fake_psutil = SimpleNamespace(Process=FakeProcess)
        provenance: list[dict[str, str]] = []
        with mock.patch.object(
            detect_resources.os,
            "sched_getaffinity",
            new=None,
            create=True,
        ), mock.patch.object(
            detect_resources.os,
            "process_cpu_count",
            return_value=4,
            create=True,
        ):
            process = detect_resources._detect_process_cpu_count(
                psutil_module=fake_psutil,
                warnings=[],
                provenance=provenance,
            )
        self.assertEqual(process["affinity_logical"], 4)
        self.assertEqual(process["python_available_logical"], 4)

    def test_windows_psutil_memory_is_kept_separate_from_limits(self) -> None:
        case = CASES["windows"]
        fake_psutil = SimpleNamespace(
            virtual_memory=lambda: SimpleNamespace(
                total=case["memory_total"],
                available=case["memory_available"],
            ),
            swap_memory=lambda: SimpleNamespace(total=8 * GIB, free=4 * GIB),
        )
        memory = detect_resources._detect_memory(
            system="Windows",
            machine="AMD64",
            psutil_module=fake_psutil,
            mac_sysctl={},
            cgroup={
                "memory_available_bytes": None,
                "memory_current_bytes": None,
                "memory_high_bytes": None,
                "memory_max_bytes": None,
            },
            scheduler={
                "allocation": {"memory_effective_bytes": 16 * GIB}
            },
            read_text=lambda path: (_ for _ in ()).throw(FileNotFoundError()),
            warnings=[],
            provenance=[],
        )
        self.assertEqual(memory["host"]["total_bytes"], 64 * GIB)
        self.assertEqual(memory["host"]["available_bytes"], 32 * GIB)
        self.assertEqual(memory["effective"]["hard_limit_bytes"], 16 * GIB)
        self.assertEqual(memory["effective"]["available_bytes"], 16 * GIB)

    def test_linux_partial_failure_still_returns_valid_snapshot(self) -> None:
        meminfo = (
            "MemTotal:       16777216 kB\n"
            "MemAvailable:    8388608 kB\n"
            "SwapTotal:       2097152 kB\n"
            "SwapFree:        1048576 kB\n"
        )

        def reader(path: Path) -> str:
            if str(path) == "/proc/meminfo":
                return meminfo
            raise FileNotFoundError(str(path))

        with mock.patch.object(
            detect_resources.platform, "system", return_value="Linux"
        ), mock.patch.object(
            detect_resources.platform, "machine", return_value="x86_64"
        ), mock.patch.object(
            detect_resources.platform, "python_version", return_value="3.13.5"
        ), mock.patch.object(
            detect_resources.os, "cpu_count", return_value=8
        ), mock.patch.object(
            detect_resources.os,
            "sched_getaffinity",
            return_value={0, 1},
            create=True,
        ), mock.patch.object(
            detect_resources.shutil,
            "disk_usage",
            return_value=SimpleNamespace(
                total=100 * GIB,
                used=40 * GIB,
                free=60 * GIB,
            ),
        ), mock.patch.object(
            detect_resources.os,
            "statvfs",
            return_value=SimpleNamespace(f_bavail=50, f_bfree=60, f_frsize=GIB),
            create=True,
        ):
            snapshot = detect_resources.collect_snapshot(
                skip_accelerators=True,
                observed_at="2026-07-23T12:00:00Z",
                environ={},
                psutil_module=None,
                read_text=reader,
            )
        validation = snapshot_tools.validate_snapshot(snapshot)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(snapshot["cpu"]["effective"]["capacity_cores"], 2.0)
        self.assertEqual(snapshot["memory"]["effective"]["available_bytes"], 8 * GIB)
        serialized = json.dumps(snapshot)
        self.assertNotIn(str(Path.cwd()), serialized)
        self.assertNotIn("hostname", serialized.lower().replace("hostnames", ""))


class SnapshotToolTests(unittest.TestCase):
    def test_invalid_accelerator_maps_and_backends_are_reported(self) -> None:
        for value in (None, [], {"cuda": True}, {"cuda": -1}):
            snapshot = canonical_snapshot()
            snapshot["accelerators"]["candidate_upper_bounds"] = value
            self.assertFalse(snapshot_tools.validate_snapshot(snapshot)["valid"])
            with self.assertRaises(_common.ResourceToolError):
                plan_workload.build_plan(snapshot, accelerator="any")
        snapshot = canonical_snapshot()
        snapshot["accelerators"]["devices"][0]["backend_candidate"] = []
        self.assertFalse(snapshot_tools.validate_snapshot(snapshot)["valid"])

    def test_extreme_numeric_and_invalid_timestamp_are_rejected(self) -> None:
        snapshot = canonical_snapshot()
        snapshot["memory"]["effective"]["available_bytes"] = 10**1000
        snapshot["observed_at"] = "not-a-timeZ"
        self.assertFalse(snapshot_tools.validate_snapshot(snapshot)["valid"])

    def test_validator_accepts_canonical_snapshot(self) -> None:
        report = snapshot_tools.validate_snapshot(canonical_snapshot())
        self.assertTrue(report["valid"], report["errors"])

    def test_validator_rejects_impossible_disk_order(self) -> None:
        snapshot = canonical_snapshot()
        snapshot["disk"]["user_available_bytes"] = 70 * GIB
        report = snapshot_tools.validate_snapshot(snapshot)
        self.assertFalse(report["valid"])
        self.assertIn("DISK_ORDER", {item["code"] for item in report["errors"]})

    def test_diff_ignores_timestamp_by_default(self) -> None:
        before = canonical_snapshot()
        after = canonical_snapshot()
        after["observed_at"] = "2026-07-23T12:05:00Z"
        self.assertEqual(
            snapshot_tools.diff_snapshots(before, after)["change_count"],
            0,
        )
        after["cpu"]["effective"]["capacity_cores"] = 2.0
        diff = snapshot_tools.diff_snapshots(before, after)
        self.assertEqual(diff["change_count"], 1)
        self.assertEqual(
            diff["changes"][0]["path"],
            "$.cpu.effective.capacity_cores",
        )


class PlannerTests(unittest.TestCase):
    def test_zero_workers_when_no_worker_fits_known_memory(self) -> None:
        plan = plan_workload.build_plan(canonical_snapshot(), memory_per_worker_mib=16384)
        self.assertEqual(plan["recommendation"]["suggested_workers"], 0)
        self.assertEqual(plan["recommendation"]["threads_per_worker"], 0)
        self.assertEqual(plan["recommendation"]["status"], "insufficient_memory")

    def test_unknown_memory_requires_review(self) -> None:
        snapshot = canonical_snapshot()
        snapshot["memory"]["effective"]["available_bytes"] = None
        plan = plan_workload.build_plan(snapshot, memory_per_worker_mib=1024)
        self.assertEqual(plan["recommendation"]["status"], "review_required")

    def test_worker_plan_uses_cpu_memory_tasks_and_request(self) -> None:
        plan = plan_workload.build_plan(
            canonical_snapshot(),
            workload="cpu",
            task_count=10,
            requested_workers=8,
            memory_per_worker_mib=2048,
            reserve_memory_mib=1024,
            accelerator="cuda",
        )
        self.assertEqual(plan["limits"]["cpu_worker_ceiling"], 3)
        self.assertEqual(plan["limits"]["memory_worker_ceiling"], 3)
        self.assertEqual(plan["recommendation"]["suggested_workers"], 3)
        self.assertEqual(plan["recommendation"]["threads_per_worker"], 1)
        self.assertEqual(plan["accelerator"]["status"], "diagnostic_required")

    def test_io_plan_is_bounded(self) -> None:
        snapshot = canonical_snapshot()
        snapshot["cpu"]["effective"]["worker_ceiling"] = 1024
        snapshot["cpu"]["effective"]["capacity_cores"] = 1024
        plan = plan_workload.build_plan(snapshot, workload="io")
        self.assertEqual(plan["recommendation"]["suggested_workers"], 32)

    def test_accelerator_plan_executes_nothing(self) -> None:
        plan = accelerator_diagnostics.build_diagnostic_plan(
            canonical_snapshot(),
            backend="cuda",
        )
        self.assertEqual(plan["execution"], "not_performed")
        self.assertEqual(plan["selected_backends"], ["cuda"])
        self.assertEqual(plan["checks"][0]["commands"][0][0], "nvidia-smi")
        self.assertIn("stress tests or large allocations", plan["prohibited_actions"])


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

if __name__ == "__main__":
    unittest.main()
