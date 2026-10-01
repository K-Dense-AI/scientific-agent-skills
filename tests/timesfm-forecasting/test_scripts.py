"""Tests for the TimesFM preflight checker and CSV forecasting driver.

Neither script is exercised against real model weights -- the point of
`check_system.py` is to run *before* a 200M-parameter download, and
`forecast_csv.py` only reaches the network in `load_model()`, which nothing here
calls. What the tests cover instead:

* Thresholds. Every RAM, disk, and Python verdict is produced with the host
  stubbed, so the boundaries are checked against the profile tables rather than
  against whatever this machine happens to have: exactly the minimum warns,
  below it fails, exactly the recommendation passes. A missing package must warn
  and not fail, or the checker would refuse to run on a machine it is being used
  to prepare.
* The batch-size ladder. It must be monotonic in VRAM and RAM -- a swapped tier
  would recommend a larger batch for a smaller GPU -- and a value it cannot
  parse must fall back rather than raise.
* The contract between the two scripts: `forecast_csv` reads
  `recommended_batch_size` out of `SystemReport.to_dict()` and refuses to
  continue when the report fails, so both keys and both paths are asserted.
* Quantile indexing. TimesFM's continuous quantile head returns ten columns --
  the mean followed by the nine deciles -- so the 10th, 50th and 90th
  percentiles live at indices 1, 5 and 9. Off-by-one here mislabels a
  prediction interval, which no shape check would catch, so the test feeds an
  array whose values encode their own index.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "timesfm-forecasting"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

np = pytest.importorskip("numpy", reason="forecast_csv needs numpy")
pd = pytest.importorskip("pandas", reason="forecast_csv needs pandas")

import check_system  # noqa: E402
import forecast_csv  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def usage(free_gb: float):
    """A `shutil.disk_usage` result with the requested free space."""
    total = int(100 * 1024**3)
    free = int(free_gb * 1024**3)
    return shutil._ntuple_diskusage(total, total - free, free)


def report_with_gpu(value: str, status: str = "pass") -> check_system.SystemReport:
    report = check_system.SystemReport(model="test")
    report.checks.append(
        check_system.CheckResult(name="GPU", status=status, detail="", value=value)
    )
    return report


class ModelProfileTests(unittest.TestCase):
    def test_the_three_documented_checkpoints_are_offered(self) -> None:
        self.assertEqual(set(check_system.MODEL_PROFILES), {"v2.5", "v2.0", "v1.0"})

    def test_each_profile_points_at_its_published_hugging_face_repo(self) -> None:
        # A wrong repo id is a 404 at download time, long after the check passed.
        expected = {
            "v2.5": "google/timesfm-2.5-200m-pytorch",
            "v2.0": "google/timesfm-2.0-500m-pytorch",
            "v1.0": "google/timesfm-1.0-200m-pytorch",
        }
        for version, repo in expected.items():
            with self.subTest(version=version):
                self.assertEqual(check_system.MODEL_PROFILES[version]["hf_repo"], repo)

    def test_the_five_hundred_million_model_asks_for_the_most_memory(self) -> None:
        # v2.0 is 500M parameters against 200M for the other two.
        by_ram = {
            version: profile["min_ram_gb"]
            for version, profile in check_system.MODEL_PROFILES.items()
        }
        self.assertEqual(max(by_ram, key=by_ram.get), "v2.0")

    def test_no_profile_recommends_less_than_it_requires(self) -> None:
        for version, profile in check_system.MODEL_PROFILES.items():
            with self.subTest(version=version):
                self.assertLessEqual(profile["min_ram_gb"], profile["recommended_ram_gb"])
                self.assertLessEqual(
                    profile["min_vram_gb"], profile["recommended_vram_gb"]
                )
                self.assertGreater(profile["disk_gb"], 0)


class RamCheckTests(unittest.TestCase):
    PROFILE = check_system.MODEL_PROFILES["v2.0"]  # min 8 GB, recommended 16 GB

    def check(self, total: float, available: float = 4.0):
        with mock.patch.object(check_system, "_get_total_ram_gb", return_value=total), \
             mock.patch.object(check_system, "_get_available_ram_gb", return_value=available):
            return check_system.check_ram(self.PROFILE)

    def test_below_the_minimum_fails_and_explains_the_consequence(self) -> None:
        result = self.check(4.0)
        self.assertEqual(result.status, "fail")
        self.assertIn("8 GB", result.detail)

    def test_exactly_the_minimum_warns_rather_than_failing(self) -> None:
        # 8 GB is enough to load the model, just not comfortably.
        self.assertEqual(self.check(8.0).status, "warn")

    def test_just_under_the_recommendation_still_warns(self) -> None:
        result = self.check(15.9)
        self.assertEqual(result.status, "warn")
        self.assertIn("per_core_batch_size", result.detail)

    def test_exactly_the_recommendation_passes(self) -> None:
        self.assertEqual(self.check(16.0).status, "pass")

    def test_the_reported_value_carries_both_totals(self) -> None:
        result = self.check(32.0, available=12.5)
        self.assertIn("32.0 GB", result.value)
        self.assertIn("12.5 GB", result.value)

    def test_the_smaller_model_passes_where_the_larger_one_fails(self) -> None:
        # 4 GB: below v2.0's 8 GB minimum, but at v2.5's recommendation.
        with mock.patch.object(check_system, "_get_total_ram_gb", return_value=4.0), \
             mock.patch.object(check_system, "_get_available_ram_gb", return_value=2.0):
            self.assertEqual(
                check_system.check_ram(check_system.MODEL_PROFILES["v2.5"]).status,
                "pass",
            )
            self.assertEqual(
                check_system.check_ram(check_system.MODEL_PROFILES["v2.0"]).status,
                "fail",
            )


class DiskCheckTests(unittest.TestCase):
    PROFILE = check_system.MODEL_PROFILES["v2.0"]  # 4 GB of weights

    def test_less_free_space_than_the_weights_need_fails(self) -> None:
        with mock.patch("shutil.disk_usage", return_value=usage(1.0)):
            result = check_system.check_disk(self.PROFILE)
        self.assertEqual(result.status, "fail")
        self.assertIn("HF_HOME", result.detail)

    def test_exactly_enough_space_passes(self) -> None:
        with mock.patch("shutil.disk_usage", return_value=usage(4.0)):
            self.assertEqual(check_system.check_disk(self.PROFILE).status, "pass")

    def test_the_cache_directory_is_where_the_space_is_measured(self) -> None:
        # The advice is "set HF_HOME to a larger volume", so that variable has
        # to be what the check actually looks at.
        with tempfile.TemporaryDirectory() as cache:
            with mock.patch.dict(os.environ, {"HF_HOME": cache}), \
                 mock.patch("shutil.disk_usage", return_value=usage(50.0)) as measured:
                result = check_system.check_disk(self.PROFILE)
        self.assertIn(cache, result.value)
        self.assertEqual(measured.call_args.args[0], cache)

    def test_an_absent_cache_directory_falls_back_to_the_home_volume(self) -> None:
        missing = str(Path(tempfile.gettempdir()) / "timesfm-cache-does-not-exist")
        with mock.patch.dict(os.environ, {"HF_HOME": missing}), \
             mock.patch("shutil.disk_usage", return_value=usage(50.0)) as measured:
            check_system.check_disk(self.PROFILE)
        self.assertEqual(measured.call_args.args[0], str(Path.home()))


class PythonCheckTests(unittest.TestCase):
    @staticmethod
    def interpreter(major: int, minor: int):
        return mock.patch.object(sys, "version_info", (major, minor, 0, "final", 0))

    def test_the_documented_minimum_of_three_ten_passes(self) -> None:
        with self.interpreter(3, 10):
            self.assertEqual(check_system.check_python().status, "pass")

    def test_three_nine_fails_and_states_the_requirement(self) -> None:
        with self.interpreter(3, 9):
            result = check_system.check_python()
        self.assertEqual(result.status, "fail")
        self.assertIn(">= 3.10", result.detail)

    def test_a_newer_interpreter_passes(self) -> None:
        with self.interpreter(3, 13):
            self.assertEqual(check_system.check_python().status, "pass")


class PackageCheckTests(unittest.TestCase):
    def test_an_installed_package_reports_its_version(self) -> None:
        module = types.ModuleType("timesfm_probe_present")
        module.__version__ = "2.5.0"
        with mock.patch.dict(sys.modules, {"timesfm_probe_present": module}):
            result = check_system.check_package("probe", "timesfm_probe_present")
        self.assertEqual(result.status, "pass")
        self.assertIn("2.5.0", result.value)

    def test_a_missing_package_warns_instead_of_failing(self) -> None:
        # The whole point is to run this before installing TimesFM, so a missing
        # package must not make the report fail and block the workflow.
        result = check_system.check_package("timesfm_probe_absent_xyz")
        self.assertEqual(result.status, "warn")
        self.assertIn("uv pip install", result.detail)

    def test_a_package_without_a_version_is_still_installed(self) -> None:
        module = types.ModuleType("timesfm_probe_bare")
        with mock.patch.dict(sys.modules, {"timesfm_probe_bare": module}):
            result = check_system.check_package("probe", "timesfm_probe_bare")
        self.assertEqual(result.status, "pass")
        self.assertIn("unknown", result.value)


class GpuCheckTests(unittest.TestCase):
    @staticmethod
    def torch_module(*, cuda: bool, mps: bool = False, vram_gb: float = 24.0):
        module = types.ModuleType("torch")
        module.cuda = types.SimpleNamespace(
            is_available=lambda: cuda,
            get_device_name=lambda index: "NVIDIA A10G",
            get_device_properties=lambda index: types.SimpleNamespace(
                total_memory=int(vram_gb * 1024**3)
            ),
        )
        module.backends = types.SimpleNamespace(
            mps=types.SimpleNamespace(is_available=lambda: mps)
        )
        return module

    def test_a_cuda_device_is_reported_with_its_vram(self) -> None:
        with mock.patch.dict(sys.modules, {"torch": self.torch_module(cuda=True, vram_gb=16.0)}):
            result = check_system.check_gpu()
        self.assertEqual(result.status, "pass")
        self.assertIn("NVIDIA A10G", result.value)
        self.assertIn("VRAM: 16.0 GB", result.value)

    def test_apple_silicon_passes_without_a_vram_figure(self) -> None:
        # MPS uses unified memory, so there is no separate VRAM to report.
        with mock.patch.dict(sys.modules, {"torch": self.torch_module(cuda=False, mps=True)}):
            result = check_system.check_gpu()
        self.assertEqual(result.status, "pass")
        self.assertIn("MPS", result.value)
        self.assertNotIn("VRAM", result.value)

    def test_no_accelerator_warns_because_cpu_still_works(self) -> None:
        with mock.patch.dict(sys.modules, {"torch": self.torch_module(cuda=False)}):
            result = check_system.check_gpu()
        self.assertEqual(result.status, "warn")
        self.assertIn("CPU", result.value)

    def test_torch_missing_entirely_warns_rather_than_raising(self) -> None:
        with mock.patch.dict(sys.modules, {"torch": None}):
            result = check_system.check_gpu()
        self.assertEqual(result.status, "warn")
        self.assertIn("torch not installed", result.value)


class BatchSizeTests(unittest.TestCase):
    def gpu_batch(self, vram_gb: float) -> int:
        return check_system.recommend_batch_size(
            report_with_gpu(f"NVIDIA A100 | VRAM: {vram_gb} GB")
        )

    def cpu_batch(self, ram_gb: float) -> int:
        report = report_with_gpu("None (CPU only)", status="warn")
        with mock.patch.object(check_system, "_get_total_ram_gb", return_value=ram_gb):
            return check_system.recommend_batch_size(report)

    def mps_batch(self, ram_gb: float) -> int:
        report = report_with_gpu("Apple Silicon MPS")
        with mock.patch.object(check_system, "_get_total_ram_gb", return_value=ram_gb):
            return check_system.recommend_batch_size(report)

    def test_the_vram_tiers_are_the_documented_ladder(self) -> None:
        for vram, expected in ((40.0, 256), (24.0, 256), (16.0, 128), (8.0, 64),
                               (4.0, 32), (2.0, 16)):
            with self.subTest(vram=vram):
                self.assertEqual(self.gpu_batch(vram), expected)

    def test_each_tier_boundary_is_inclusive_from_below(self) -> None:
        # 23.9 GB must not be treated as a 24 GB card.
        self.assertEqual(self.gpu_batch(23.9), 128)
        self.assertEqual(self.gpu_batch(15.9), 64)
        self.assertEqual(self.gpu_batch(7.9), 32)
        self.assertEqual(self.gpu_batch(3.9), 16)

    def test_the_recommendation_never_decreases_as_vram_grows(self) -> None:
        # A non-monotonic ladder would hand a smaller card the larger batch.
        sizes = [self.gpu_batch(vram) for vram in (1, 4, 8, 16, 24, 80)]
        self.assertEqual(sizes, sorted(sizes))

    def test_an_unparseable_vram_figure_falls_back_to_a_safe_batch(self) -> None:
        report = report_with_gpu("Mystery GPU | VRAM: lots GB")
        self.assertEqual(check_system.recommend_batch_size(report), 32)

    def test_cpu_only_hosts_are_sized_by_system_memory(self) -> None:
        self.assertEqual(self.cpu_batch(64.0), 64)
        self.assertEqual(self.cpu_batch(16.0), 32)
        self.assertEqual(self.cpu_batch(8.0), 8)
        self.assertEqual(self.cpu_batch(4.0), 4)

    def test_cpu_recommendations_never_decrease_as_memory_grows(self) -> None:
        sizes = [self.cpu_batch(ram) for ram in (2, 8, 16, 32, 128)]
        self.assertEqual(sizes, sorted(sizes))

    def test_unified_memory_hosts_are_sized_by_system_memory(self) -> None:
        self.assertEqual(self.mps_batch(64.0), 64)
        self.assertEqual(self.mps_batch(16.0), 32)
        self.assertEqual(self.mps_batch(8.0), 16)

    def test_every_recommendation_is_a_usable_batch_size(self) -> None:
        for vram in (0.5, 4.0, 80.0):
            with self.subTest(vram=vram):
                self.assertGreaterEqual(self.gpu_batch(vram), 1)


class ReportTests(unittest.TestCase):
    """`run_checks` composes the individual verdicts into one decision."""

    def run_checks(self, *, total_ram=32.0, modules=None, free_gb=100.0,
                   model="v2.5"):
        # `modules` is patched into sys.modules, so a value of None stands for
        # "not installed" -- importing it raises ImportError.
        modules = {} if modules is None else modules
        with mock.patch.object(check_system, "_get_total_ram_gb", return_value=total_ram), \
             mock.patch.object(check_system, "_get_available_ram_gb", return_value=total_ram / 2), \
             mock.patch("shutil.disk_usage", return_value=usage(free_gb)), \
             mock.patch.dict(sys.modules, modules):
            return check_system.run_checks(model)

    def test_a_healthy_cpu_host_passes_in_cpu_mode(self) -> None:
        report = self.run_checks(modules={"torch": GpuCheckTests.torch_module(cuda=False)})
        self.assertTrue(report.passed)
        self.assertEqual(report.mode, "cpu")
        self.assertIn("ready", report.verdict)
        self.assertIn(str(report.recommended_batch_size), report.verdict_detail)

    def test_reports_print_on_cp1252_for_success_warning_and_failure(self) -> None:
        for total_ram in (1.0, 32.0):
            with self.subTest(total_ram=total_ram):
                report = self.run_checks(
                    total_ram=total_ram, modules={"torch": None, "timesfm": None}
                )
                raw = io.BytesIO()
                with io.TextIOWrapper(raw, encoding="cp1252", errors="strict") as stream:
                    with contextlib.redirect_stdout(stream):
                        check_system.print_report(report)
                    stream.flush()
                    output = raw.getvalue().decode("cp1252")
                    self.assertIn("VERDICT", output)
                    self.assertIn("WARN", output)
                    self.assertIn("ready" if report.passed else "does NOT meet", output)

    def test_a_cuda_host_is_reported_in_gpu_mode(self) -> None:
        report = self.run_checks(modules={"torch": GpuCheckTests.torch_module(cuda=True)})
        self.assertEqual(report.mode, "gpu")

    def test_an_apple_silicon_host_is_reported_in_mps_mode(self) -> None:
        report = self.run_checks(
            modules={"torch": GpuCheckTests.torch_module(cuda=False, mps=True)}
        )
        self.assertEqual(report.mode, "mps")

    def test_too_little_memory_fails_the_whole_report(self) -> None:
        report = self.run_checks(
            total_ram=1.0,
            modules={"torch": GpuCheckTests.torch_module(cuda=False)},
        )
        self.assertFalse(report.passed)
        self.assertIn("does NOT meet", report.verdict)
        # The detail must name the failing resource, not just say "failed".
        self.assertIn("RAM", report.verdict_detail)

    def test_a_full_disk_fails_the_whole_report(self) -> None:
        report = self.run_checks(
            free_gb=0.5,
            modules={"torch": GpuCheckTests.torch_module(cuda=False)},
        )
        self.assertFalse(report.passed)

    def test_warnings_alone_do_not_fail_the_report(self) -> None:
        # No GPU and no timesfm installed: both warn, and the run may proceed.
        report = self.run_checks(modules={"torch": None, "timesfm": None})
        statuses = {check.name: check.status for check in report.checks}
        self.assertEqual(statuses["GPU"], "warn")
        self.assertTrue(report.passed)

    def test_every_documented_resource_is_checked(self) -> None:
        report = self.run_checks(modules={"torch": GpuCheckTests.torch_module(cuda=False)})
        self.assertEqual(
            [check.name for check in report.checks],
            ["RAM", "GPU", "Disk", "Python", "timesfm", "torch"],
        )

    def test_the_json_report_is_serialisable_and_keeps_its_keys(self) -> None:
        # forecast_csv consumes this dict, and --json is a documented interface.
        report = self.run_checks(modules={"torch": GpuCheckTests.torch_module(cuda=True)})
        payload = json.loads(json.dumps(report.to_dict()))
        self.assertEqual(
            set(payload),
            {"model", "passed", "mode", "recommended_batch_size", "verdict",
             "verdict_detail", "checks"},
        )
        self.assertEqual(set(payload["checks"][0]), {"name", "status", "detail", "value"})

    def test_an_unknown_model_version_is_not_silently_substituted(self) -> None:
        with self.assertRaises(KeyError):
            check_system.run_checks("v9.9")


class CheckResultFormattingTests(unittest.TestCase):
    def test_each_status_gets_its_own_icon(self) -> None:
        icons = {
            status: check_system.CheckResult(name="x", status=status, detail="").icon
            for status in ("pass", "warn", "fail", "banana")
        }
        self.assertEqual(len(set(icons.values())), 4, icons)

    def test_the_rendered_line_carries_the_name_value_and_status(self) -> None:
        line = str(
            check_system.CheckResult(
                name="RAM", status="warn", detail="tight", value="Total: 8.0 GB"
            )
        )
        self.assertIn("RAM", line)
        self.assertIn("Total: 8.0 GB", line)
        self.assertIn("WARN", line)


class CommandLineTests(unittest.TestCase):
    """The checker is documented as runnable, so run it -- it touches nothing."""

    def invoke(self, *arguments):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "check_system.py"), *arguments],
            capture_output=True,
            text=True,
            timeout=180,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def test_the_json_output_parses_and_names_the_model(self) -> None:
        result = self.invoke("--model", "v1.0", "--json")
        # Exit code follows the verdict for this host, so only the payload is
        # asserted; a crash would show up as unparseable output.
        payload = json.loads(result.stdout)
        self.assertEqual(payload["model"], "TimesFM 1.0 (200M)")
        self.assertIn(payload["mode"], {"cpu", "gpu", "mps"})
        self.assertGreaterEqual(payload["recommended_batch_size"], 1)

    def test_an_unknown_model_is_rejected_by_the_parser(self) -> None:
        result = self.invoke("--model", "v9.9")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

    def test_the_human_report_names_every_check_and_a_verdict(self) -> None:
        result = self.invoke()
        for name in ("RAM", "GPU", "Disk", "Python", "timesfm", "torch"):
            self.assertIn(name, result.stdout)
        self.assertIn("VERDICT", result.stdout)


class PreflightHandoffTests(unittest.TestCase):
    """`forecast_csv` refuses to load a model the host cannot hold."""

    def test_a_failing_report_stops_the_run(self) -> None:
        report = check_system.SystemReport(
            model="test", verdict_detail="only 1 GB of RAM"
        )
        report.checks.append(
            check_system.CheckResult(name="RAM", status="fail", detail="only 1 GB")
        )
        with mock.patch.object(check_system, "run_checks", return_value=report):
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                with self.assertRaises(SystemExit) as raised:
                    forecast_csv.run_preflight()
        self.assertEqual(raised.exception.code, 1)
        # The reason has to reach the user, not just the exit code.
        self.assertIn("only 1 GB of RAM", printed.getvalue())

    def test_a_passing_report_hands_over_the_recommended_batch_size(self) -> None:
        report = check_system.SystemReport(model="test", recommended_batch_size=64)
        report.checks.append(
            check_system.CheckResult(name="RAM", status="pass", detail="fine")
        )
        with mock.patch.object(check_system, "run_checks", return_value=report):
            with contextlib.redirect_stdout(io.StringIO()):
                handed = forecast_csv.run_preflight()
        # The key forecast_csv reads must be the key the report writes.
        self.assertEqual(handed["recommended_batch_size"], 64)


class CsvLoadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)

    def write(self, text: str) -> str:
        path = self.root / "series.csv"
        path.write_text(text)
        return str(path)

    def load(self, path, *args):
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            frame, columns, date_column = forecast_csv.load_csv(path, *args)
        return frame, columns, date_column, printed.getvalue()

    def test_numeric_columns_are_detected_and_the_date_column_excluded(self) -> None:
        path = self.write(
            "date,sales,revenue,region\n"
            "2024-01-01,10,100,north\n"
            "2024-01-02,11,110,north\n"
        )
        frame, columns, date_column, _ = self.load(path, "date")
        self.assertEqual(columns, ["sales", "revenue"])
        self.assertEqual(date_column, "date")
        # The date column must be parsed, not left as text, or no frequency can
        # be inferred for the forecast index.
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(frame["date"]))

    def test_a_string_column_is_never_forecast(self) -> None:
        path = self.write("region,sales\nnorth,10\nsouth,12\n")
        _, columns, _, _ = self.load(path)
        self.assertEqual(columns, ["sales"])

    def test_an_explicit_column_list_is_honoured(self) -> None:
        path = self.write("sales,revenue\n10,100\n11,110\n")
        _, columns, _, _ = self.load(path, None, ["revenue"])
        self.assertEqual(columns, ["revenue"])

    def test_a_column_that_does_not_exist_is_dropped_with_a_warning(self) -> None:
        path = self.write("sales\n10\n11\n")
        _, columns, _, printed = self.load(path, None, ["sales", "profit"])
        self.assertEqual(columns, ["sales"])
        self.assertIn("profit", printed)

    def test_a_missing_date_column_is_reported_and_forgotten(self) -> None:
        path = self.write("day,sales\n2024-01-01,10\n")
        _, _, date_column, printed = self.load(path, "date")
        self.assertIsNone(date_column)
        self.assertIn("not found", printed)

    def test_a_csv_with_nothing_numeric_stops_the_run(self) -> None:
        path = self.write("region\nnorth\nsouth\n")
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            with self.assertRaises(SystemExit) as raised:
                forecast_csv.load_csv(path)
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("No numeric columns", printed.getvalue())

    def test_naming_no_columns_at_all_falls_back_to_autodetection(self) -> None:
        path = self.write("sales,revenue\n10,100\n")
        _, columns, _, _ = self.load(path, None, None)
        self.assertEqual(columns, ["sales", "revenue"])


class ForecastAssemblyTests(unittest.TestCase):
    HORIZON = 4

    class RecordingModel:
        """Stands in for TimesFM: records inputs, returns index-encoded output."""

        def __init__(self, horizon: int) -> None:
            self.horizon = horizon
            self.inputs = None

        def forecast(self, horizon, inputs):
            self.inputs = [np.asarray(series) for series in inputs]
            point = np.zeros((len(inputs), horizon), dtype="float32")
            # quantiles[series, step, q] == q, so any index mix-up is visible.
            quantiles = np.tile(np.arange(10, dtype="float32"), (len(inputs), horizon, 1))
            return point, quantiles

    def setUp(self) -> None:
        self.model = self.RecordingModel(self.HORIZON)
        self.frame = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=5, freq="D"),
                "sales": [1.0, 2.0, 3.0, 4.0, 5.0],
                "revenue": [10.0, np.nan, 30.0, 40.0, 50.0],
            }
        )
        with contextlib.redirect_stdout(io.StringIO()):
            self.results = forecast_csv.forecast_series(
                self.model, self.frame, ["sales", "revenue"], self.HORIZON
            )

    def test_each_series_is_forecast_and_keyed_by_its_column(self) -> None:
        self.assertEqual(set(self.results), {"sales", "revenue"})
        for values in self.results.values():
            self.assertEqual(len(values["forecast"]), self.HORIZON)

    def test_the_quantile_columns_map_to_the_documented_percentiles(self) -> None:
        # TimesFM returns [mean, q0.1 ... q0.9], so the 10th, 50th and 90th
        # percentiles are columns 1, 5 and 9.
        band = self.results["sales"]
        self.assertEqual(band["lower_80"], [1.0] * self.HORIZON)
        self.assertEqual(band["lower_60"], [2.0] * self.HORIZON)
        self.assertEqual(band["median"], [5.0] * self.HORIZON)
        self.assertEqual(band["upper_60"], [8.0] * self.HORIZON)
        self.assertEqual(band["upper_80"], [9.0] * self.HORIZON)

    def test_the_bands_are_ordered_from_low_to_high(self) -> None:
        band = self.results["revenue"]
        for lower, upper in (("lower_80", "lower_60"), ("lower_60", "median"),
                             ("median", "upper_60"), ("upper_60", "upper_80")):
            with self.subTest(pair=(lower, upper)):
                self.assertLess(band[lower][0], band[upper][0])

    def test_gaps_are_dropped_before_the_series_reaches_the_model(self) -> None:
        # A NaN passed through would poison the whole context window.
        sales, revenue = self.model.inputs
        self.assertEqual(len(sales), 5)
        self.assertEqual(len(revenue), 4)
        self.assertFalse(np.isnan(revenue).any())
        self.assertEqual(revenue.dtype, np.float32)


class OutputWritingTests(unittest.TestCase):
    HORIZON = 3

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)
        self.results = {
            name: {
                "forecast": [1.0, 2.0, 3.0],
                "lower_80": [0.1, 0.2, 0.3],
                "lower_60": [0.2, 0.3, 0.4],
                "median": [1.0, 2.0, 3.0],
                "upper_60": [1.8, 2.8, 3.8],
                "upper_80": [1.9, 2.9, 3.9],
            }
            for name in ("sales", "revenue")
        }

    def write_csv(self, frame, date_column):
        destination = self.root / "forecasts.csv"
        with contextlib.redirect_stdout(io.StringIO()):
            forecast_csv.write_csv_output(
                self.results, str(destination), frame, date_column, self.HORIZON
            )
        return pd.read_csv(destination)

    def test_one_row_per_series_and_step(self) -> None:
        frame = pd.DataFrame({"sales": [1.0, 2.0]})
        written = self.write_csv(frame, None)
        self.assertEqual(len(written), 2 * self.HORIZON)
        self.assertEqual(sorted(written["step"].unique()), [1, 2, 3])
        self.assertEqual(sorted(written["series"].unique()), ["revenue", "sales"])

    def test_without_dates_only_the_step_index_is_written(self) -> None:
        written = self.write_csv(pd.DataFrame({"sales": [1.0, 2.0]}), None)
        self.assertNotIn("date", written.columns)

    def test_a_daily_history_continues_past_its_last_observation(self) -> None:
        # Five daily points ending 2024-01-05, horizon 3: the forecast index is
        # the next three days, not a repeat of the last one.
        frame = pd.DataFrame(
            {"date": pd.date_range("2024-01-01", periods=5, freq="D")}
        )
        written = self.write_csv(frame, "date")
        self.assertEqual(
            list(written[written["series"] == "sales"]["date"]),
            ["2024-01-06", "2024-01-07", "2024-01-08"],
        )

    def test_an_irregular_history_falls_back_to_step_numbers(self) -> None:
        # No frequency can be inferred from unevenly spaced dates, so the
        # writer must not invent one.
        frame = pd.DataFrame(
            {"date": pd.to_datetime(["2024-01-01", "2024-01-03", "2024-01-08"])}
        )
        written = self.write_csv(frame, "date")
        self.assertNotIn("date", written.columns)

    def test_every_band_column_survives_the_round_trip(self) -> None:
        written = self.write_csv(pd.DataFrame({"sales": [1.0]}), None)
        for column in ("forecast", "lower_80", "lower_60", "median",
                       "upper_60", "upper_80"):
            self.assertIn(column, written.columns)
        first = written[(written["series"] == "sales") & (written["step"] == 1)]
        self.assertEqual(first["lower_80"].iloc[0], 0.1)

    def test_the_json_output_keeps_the_series_names_and_bands(self) -> None:
        destination = self.root / "forecasts.json"
        with contextlib.redirect_stdout(io.StringIO()):
            forecast_csv.write_json_output(self.results, str(destination))
        payload = json.loads(destination.read_text())
        self.assertEqual(set(payload), {"sales", "revenue"})
        self.assertEqual(payload["sales"]["upper_80"], [1.9, 2.9, 3.9])


if __name__ == "__main__":
    unittest.main()
