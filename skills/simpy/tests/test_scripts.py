#!/usr/bin/env python3
"""Synthetic, network-free tests for the SimPy skill scripts."""

from __future__ import annotations

import ast
import json
import math
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import simpy


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _common  # noqa: E402
import basic_simulation_template  # noqa: E402
import bounded_queue_scenario  # noqa: E402
import event_trace_summary  # noqa: E402
import replication_runner  # noqa: E402
import resource_monitor  # noqa: E402
import validate_simulation_config  # noqa: E402


class SafetyTests(unittest.TestCase):
    def test_scripts_parse_and_do_not_use_dangerous_features(self) -> None:
        banned_imports = {
            "aiohttp",
            "httpx",
            "importlib",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
        banned_calls = {"eval", "exec", "compile", "__import__"}
        for path in sorted(SCRIPTS.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots = {alias.name.split(".", 1)[0] for alias in node.names}
                    self.assertFalse(roots & banned_imports, path.name)
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(
                        node.module.split(".", 1)[0], banned_imports, path.name
                    )
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, banned_calls, path.name)
                if isinstance(node, ast.Attribute):
                    self.assertFalse(
                        isinstance(node.value, ast.Name)
                        and node.value.id == "os"
                        and node.attr in {"environ", "getenv"},
                        path.name,
                    )

    def test_local_json_rejects_urls_symlinks_duplicates_and_nan(self) -> None:
        with self.assertRaises(_common.CliError):
            _common.load_json_object("https://example.invalid/config.json")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            duplicate = root / "duplicate.json"
            duplicate.write_text('{"horizon": 1, "horizon": 2}', encoding="utf-8")
            with self.assertRaises(_common.CliError):
                _common.load_json_object(duplicate)
            nonstandard = root / "nan.json"
            nonstandard.write_text('{"horizon": NaN}', encoding="utf-8")
            with self.assertRaises(_common.CliError):
                _common.load_json_object(nonstandard)
            real = root / "real.json"
            real.write_text("{}", encoding="utf-8")
            link = root / "link.json"
            try:
                link.symlink_to(real)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaises(_common.CliError):
                _common.load_json_object(link)

    def test_private_output_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            _common.emit_json({"ok": True}, output=output)
            self.assertEqual(json.loads(output.read_text()), {"ok": True})
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            with self.assertRaises(_common.CliError):
                _common.emit_json({"ok": False}, output=output)

    def test_every_cli_has_side_effect_free_help(self) -> None:
        modules = (
            basic_simulation_template,
            bounded_queue_scenario,
            event_trace_summary,
            replication_runner,
            resource_monitor,
            validate_simulation_config,
        )
        for module in modules:
            with self.subTest(module=module.__name__):
                help_text = module.build_parser().format_help()
                self.assertIn("usage:", help_text)
                self.assertIn("--help", help_text)

    def test_every_script_help_succeeds_without_site_packages(self) -> None:
        for path in sorted(SCRIPTS.glob("*.py")):
            with self.subTest(script=path.name):
                result = subprocess.run(
                    [sys.executable, "-S", str(path), "--help"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                if path.name != "_common.py":
                    self.assertIn("usage:", result.stdout)

    def test_simulation_clis_report_missing_dependency_without_traceback(self) -> None:
        for name in (
            "basic_simulation_template.py",
            "bounded_queue_scenario.py",
            "replication_runner.py",
            "resource_monitor.py",
        ):
            with self.subTest(script=name):
                result = subprocess.run(
                    [sys.executable, "-S", str(SCRIPTS / name)],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(_common.PINNED_INSTALL, result.stderr)
                self.assertIn("SimPy 4.1.2 is required", result.stderr)
                self.assertNotIn("Traceback", result.stderr)


class CoreSemanticsTests(unittest.TestCase):
    def test_same_time_events_are_fifo_deterministic(self) -> None:
        env = simpy.Environment()
        order: list[str] = []

        def process(label: str):
            yield env.timeout(1)
            order.append(label)

        env.process(process("first"))
        env.process(process("second"))
        env.run()
        self.assertEqual(order, ["first", "second"])

    def test_numeric_until_excludes_boundary_and_event_until_returns_value(self) -> None:
        env = simpy.Environment()
        boundary = env.timeout(5, value="done")
        env.run(until=5)
        self.assertEqual(env.now, 5)
        self.assertFalse(boundary.processed)

        event_env = simpy.Environment()
        target = event_env.timeout(5, value="done")
        self.assertEqual(event_env.run(until=target), "done")
        self.assertEqual(event_env.now, 5)
        # SimPy 4.1.2 preserves remaining callbacks by rescheduling the target;
        # the run criterion has fired, but one more step marks it processed.
        self.assertFalse(target.processed)
        event_env.step()
        self.assertTrue(target.processed)

    def test_process_return_and_condition_mapping(self) -> None:
        env = simpy.Environment()

        def worker():
            yield env.timeout(1)
            return 7

        process = env.process(worker())
        first = env.timeout(2, value="a")
        second = env.timeout(3, value="b")

        def coordinator():
            process_value = yield process
            condition_value = yield first & second
            return process_value, list(condition_value.items())

        result = env.run(until=env.process(coordinator()))
        self.assertEqual(result[0], 7)
        self.assertEqual(result[1], [(first, "a"), (second, "b")])

    def test_preemption_interrupt_cause_identifies_request_and_usage(self) -> None:
        env = simpy.Environment()
        resource = simpy.PreemptiveResource(env, capacity=1)
        observed: dict[str, object] = {}

        def low_priority():
            with resource.request(priority=5) as request:
                try:
                    yield request
                    yield env.timeout(10)
                except simpy.Interrupt as interrupt:
                    observed["by"] = interrupt.cause.by
                    observed["usage_since"] = interrupt.cause.usage_since

        def high_priority():
            yield env.timeout(2)
            with resource.request(priority=0, preempt=True) as request:
                yield request
                yield env.timeout(1)

        low = env.process(low_priority())
        high = env.process(high_priority())
        env.run()
        self.assertIs(observed["by"], high)
        self.assertEqual(observed["usage_since"], 0)
        self.assertTrue(low.processed)

    def test_priority_resource_orders_queued_requests(self) -> None:
        env = simpy.Environment()
        resource = simpy.PriorityResource(env, capacity=1)
        order: list[str] = []

        def user(name: str, priority: int, delay: float, duration: float):
            yield env.timeout(delay)
            with resource.request(priority=priority) as request:
                yield request
                order.append(name)
                yield env.timeout(duration)

        env.process(user("holder", 0, 0, 3))
        env.process(user("routine", 10, 1, 1))
        env.process(user("urgent", 1, 1, 1))
        env.run()
        self.assertEqual(order, ["holder", "urgent", "routine"])

    def test_container_and_store_variants(self) -> None:
        env = simpy.Environment()
        container = simpy.Container(env, capacity=10, init=5)
        store = simpy.Store(env, capacity=2)
        filtered = simpy.FilterStore(env, capacity=2)
        priority = simpy.PriorityStore(env)
        observed: list[object] = []

        def exercise():
            yield container.put(3)
            observed.append((yield container.get(4)))
            yield store.put("fifo")
            observed.append((yield store.get()))
            yield filtered.put({"kind": "keep"})
            observed.append(
                (yield filtered.get(lambda item: item["kind"] == "keep"))
            )
            yield priority.put(simpy.PriorityItem(2, "later"))
            yield priority.put(simpy.PriorityItem(1, "first"))
            observed.append((yield priority.get()).item)

        env.process(exercise())
        env.run()
        self.assertEqual(container.level, 4)
        self.assertEqual(observed, [None, "fifo", {"kind": "keep"}, "first"])


class MonitoringTests(unittest.TestCase):
    def test_resource_monitor_uses_time_weighting(self) -> None:
        env = simpy.Environment()
        resource = simpy.Resource(env, capacity=1)
        monitor = resource_monitor.ResourceMonitor(env, resource)

        def user(delay: float, duration: float):
            yield env.timeout(delay)
            with resource.request() as request:
                yield request
                yield env.timeout(duration)

        env.process(user(0, 2))
        env.process(user(1, 1))
        env.run(until=4)
        monitor.finalize(at=4)
        self.assertAlmostEqual(
            monitor.average_utilization(start=0, end=4), 0.75
        )
        self.assertAlmostEqual(
            monitor.average_queue_length(start=0, end=4), 0.25
        )
        self.assertEqual(len(monitor.wait_times), 2)

    def test_pending_request_cancellation_is_recorded(self) -> None:
        env = simpy.Environment()
        resource = simpy.Resource(env, capacity=1)
        monitor = resource_monitor.ResourceMonitor(env, resource)

        def holder():
            with resource.request() as request:
                yield request
                yield env.timeout(3)

        def impatient():
            yield env.timeout(0.5)
            with resource.request() as request:
                result = yield request | env.timeout(0.5)
                self.assertNotIn(request, result)

        env.process(holder())
        env.process(impatient())
        env.run(until=4)
        monitor.finalize(at=4)
        self.assertEqual(len(resource.queue), 0)
        self.assertEqual(monitor.summary(end=4)["pending_requests"], 0)
        self.assertIn("cancel", [sample.event for sample in monitor.samples])

    def test_trace_round_trip_and_order_summary(self) -> None:
        env = simpy.Environment()
        trace = resource_monitor.EventTraceRecorder(env, max_records=20)
        env.timeout(2)
        env.timeout(1)
        env.run()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "trace.jsonl"
            trace.export_jsonl(str(output))
            summary = event_trace_summary.summarize_event_trace(
                output, max_records=20
            )
        self.assertEqual(summary["records"], 2)
        self.assertEqual(summary["ordering_violations"], 0)
        self.assertEqual(summary["first_time"], 1)


class ScenarioTests(unittest.TestCase):
    def test_queue_run_is_reproducible_and_bounded(self) -> None:
        config = basic_simulation_template.QueueConfig.from_mapping(
            {
                "horizon": 80,
                "max_entities": 200,
                "max_events": 5000,
                "mean_interarrival": 1,
                "mean_service": 3,
                "queue_capacity": 2,
                "servers": 1,
            }
        )
        first = basic_simulation_template.run_simulation(config)
        second = basic_simulation_template.run_simulation(config)
        self.assertEqual(first, second)
        self.assertGreater(first["counters"]["rejected"], 0)
        self.assertLessEqual(first["event_processing"]["processed"], 5000)
        self.assertLessEqual(first["counters"]["arrivals"], 200)

    def test_unknown_config_and_invalid_modes_are_rejected(self) -> None:
        with self.assertRaises(_common.CliError):
            basic_simulation_template.QueueConfig.from_mapping(
                {"plugin": "untrusted.module"}
            )
        with self.assertRaises(_common.CliError):
            basic_simulation_template.QueueConfig.from_mapping(
                {"analysis_mode": "steady_state", "warm_up": 0}
            )
        with self.assertRaises(_common.CliError):
            basic_simulation_template.QueueConfig.from_mapping(
                {"analysis_mode": "terminating", "warm_up": 1}
            )

    def test_event_limit_stops_run(self) -> None:
        config = basic_simulation_template.QueueConfig.from_mapping(
            {
                "horizon": 100,
                "max_entities": 100,
                "max_events": 10,
                "mean_interarrival": 0.1,
                "mean_service": 1,
            }
        )
        with self.assertRaises(_common.CliError):
            basic_simulation_template.run_simulation(config)


class ReplicationTests(unittest.TestCase):
    def test_student_t_interval_and_quantile(self) -> None:
        interval = _common.mean_confidence_interval(
            [1.0, 2.0, 3.0, 4.0], confidence=0.95
        )
        self.assertAlmostEqual(interval["mean"], 2.5)
        self.assertAlmostEqual(
            _common.student_t_quantile(0.975, 3), 3.182446, places=5
        )
        self.assertGreater(interval["upper"], interval["mean"])
        self.assertLess(interval["lower"], interval["mean"])
        with self.assertRaises(_common.CliError):
            _common.mean_confidence_interval([1.0])

    def test_replication_config_requires_multiple_bounded_runs(self) -> None:
        with self.assertRaises(_common.CliError):
            replication_runner.ExperimentConfig.from_mapping(
                {"replications": 1}
            )
        with self.assertRaises(_common.CliError):
            replication_runner.ExperimentConfig.from_mapping(
                {
                    "replications": 1000,
                    "model": {"max_events": 1_000_000},
                }
            )

    def test_small_replication_experiment_has_replication_level_ci(self) -> None:
        config = replication_runner.ExperimentConfig.from_mapping(
            {
                "confidence": 0.9,
                "model": {
                    "horizon": 60,
                    "max_entities": 100,
                    "max_events": 5000,
                },
                "replications": 4,
            }
        )
        report = replication_runner.run_experiment(config)
        self.assertFalse(report["analysis"]["single_run_interval"])
        self.assertEqual(
            report["intervals"]["throughput_per_time_unit"]["replications"], 4
        )
        seeds = {
            run["seed_manifest"]["arrival_seed"]
            for run in report["replications"]
        }
        self.assertEqual(len(seeds), 4)


class ValidatorTests(unittest.TestCase):
    def test_validator_normalizes_both_schemas_without_running(self) -> None:
        queue = validate_simulation_config.validate_document(
            {"horizon": 12}, schema="queue"
        )
        self.assertEqual(queue["schema"], "queue")
        self.assertTrue(queue["validation"]["no_code_execution"])
        replication = validate_simulation_config.validate_document(
            {
                "model": {
                    "horizon": 12,
                    "max_entities": 20,
                    "max_events": 100,
                },
                "replications": 3,
            }
        )
        self.assertEqual(replication["schema"], "replication")
        self.assertEqual(replication["budgets"]["events"], 300)


if __name__ == "__main__":
    unittest.main()
