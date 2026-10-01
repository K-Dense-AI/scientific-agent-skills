"""Tests for the Latch SDK inspector.

`inspect_latch_sdk.py` reports on whichever Latch SDK happens to be installed,
so almost none of it can be asserted against a fixed expectation. What *can* be
pinned is everything around that: the report shape, the exit-code contract, the
address scrubbing that makes two runs comparable, and the graceful degradation
when a module is missing -- which is the normal case in this repo's project
environment, where `latch` is not installed.

`inspect_symbol` is exercised against real standard-library modules rather than
mocks: `json.dumps` is a function that exists, `json.nope` is a symbol that does
not, and `no_such_module` is an import that fails. That covers all three
branches without needing the SDK.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "latchbio-integration"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import inspect_latch_sdk  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


class NormalizeReprTests(unittest.TestCase):
    """Two runs of the inspector must be diffable, so addresses are scrubbed."""

    def test_object_repr_loses_its_address(self) -> None:
        self.assertEqual(
            inspect_latch_sdk.normalize_repr("<latch.types.LatchFile object at 0x7f9c8a1b2c40>"),
            "<latch.types.LatchFile>",
        )

    def test_bare_addresses_are_replaced_everywhere(self) -> None:
        self.assertEqual(
            inspect_latch_sdk.normalize_repr("default=0xdeadBEEF, other=0x01"),
            "default=0x<address>, other=0x<address>",
        )

    def test_text_without_an_address_is_untouched(self) -> None:
        for value in ("(x: int) -> str", "", "no hex here"):
            with self.subTest(value=value):
                self.assertEqual(inspect_latch_sdk.normalize_repr(value), value)

    def test_scrubbing_is_idempotent(self) -> None:
        once = inspect_latch_sdk.normalize_repr("<A object at 0x1234abcd>")
        self.assertEqual(inspect_latch_sdk.normalize_repr(once), once)


class SafeSignatureTests(unittest.TestCase):
    def test_a_signature_is_returned_for_an_ordinary_function(self) -> None:
        signature = inspect_latch_sdk.safe_signature(json.dumps)
        self.assertIsNotNone(signature)
        self.assertTrue(signature.startswith("("))

    def test_objects_without_a_signature_yield_none_rather_than_raising(self) -> None:
        for obj in (42, object(), None):
            with self.subTest(obj=type(obj).__name__):
                self.assertIsNone(inspect_latch_sdk.safe_signature(obj))


class SymbolInspectionTests(unittest.TestCase):
    def test_an_available_symbol_is_reported_with_its_kind_and_signature(self) -> None:
        result = inspect_latch_sdk.inspect_symbol("json", "dumps")
        self.assertEqual(result["qualified_name"], "json.dumps")
        self.assertTrue(result["available"])
        self.assertEqual(result["kind"], "function")
        self.assertIn("obj", result["signature"])
        self.assertNotIn("error", result)

    def test_a_missing_symbol_is_reported_without_raising(self) -> None:
        result = inspect_latch_sdk.inspect_symbol("json", "definitely_not_here")
        self.assertFalse(result["available"])
        self.assertEqual(result["error"], "symbol not found")

    def test_an_unimportable_module_becomes_the_diagnostic(self) -> None:
        result = inspect_latch_sdk.inspect_symbol("latch_module_that_is_absent", "x")
        self.assertFalse(result["available"])
        self.assertIn("ModuleNotFoundError", result["error"])
        self.assertEqual(
            result["qualified_name"], "latch_module_that_is_absent.x"
        )

    def test_plain_symbols_carry_no_workflow_interface(self) -> None:
        # `python_interface` only appears for Latch workflow objects; it must
        # not be invented for ordinary callables.
        self.assertNotIn(
            "python_interface", inspect_latch_sdk.inspect_symbol("json", "dumps")
        )


class MethodInspectionTests(unittest.TestCase):
    def test_present_and_absent_methods_are_distinguished(self) -> None:
        result = inspect_latch_sdk.inspect_methods(
            "pathlib", "Path", ["exists", "iterdir", "not_a_method"]
        )
        self.assertTrue(result["exists"]["available"])
        self.assertTrue(result["iterdir"]["available"])
        self.assertFalse(result["not_a_method"]["available"])
        self.assertIsNone(result["not_a_method"]["signature"])

    def test_an_unimportable_class_reports_one_error_not_per_method(self) -> None:
        result = inspect_latch_sdk.inspect_methods("absent_module", "Thing", ["a", "b"])
        self.assertEqual(set(result), {"error"})
        self.assertIn("ModuleNotFoundError", result["error"])


class CatalogueTests(unittest.TestCase):
    def test_every_symbol_group_is_non_empty_and_latch_scoped(self) -> None:
        self.assertTrue(inspect_latch_sdk.SYMBOL_GROUPS)
        for group, entries in inspect_latch_sdk.SYMBOL_GROUPS.items():
            with self.subTest(group=group):
                self.assertTrue(entries)
                for module_name, symbol_name in entries:
                    self.assertTrue(module_name.startswith("latch"))
                    self.assertTrue(symbol_name)

    def test_no_symbol_is_catalogued_twice(self) -> None:
        qualified = [
            f"{module}.{symbol}"
            for entries in inspect_latch_sdk.SYMBOL_GROUPS.values()
            for module, symbol in entries
        ]
        duplicates = sorted({name for name in qualified if qualified.count(name) > 1})
        self.assertEqual(duplicates, [])

    def test_method_targets_are_also_catalogued_as_symbols(self) -> None:
        # A class whose methods are probed must itself be in SYMBOL_GROUPS, or
        # the report cannot say whether a missing method means a missing class.
        catalogued = {
            f"{module}.{symbol}"
            for entries in inspect_latch_sdk.SYMBOL_GROUPS.values()
            for module, symbol in entries
        }
        for label, (module, class_name, methods) in inspect_latch_sdk.METHODS.items():
            with self.subTest(target=label):
                self.assertIn(f"{module}.{class_name}", catalogued)
                self.assertTrue(methods)


class RequiredSymbolTests(unittest.TestCase):
    def _report(self, availability: dict[str, bool]) -> dict:
        return {
            "symbols": {
                "core": [
                    {"qualified_name": name, "available": available}
                    for name, available in availability.items()
                ]
            }
        }

    REQUIRED = (
        "latch.workflow",
        "latch.resources.tasks.small_task",
        "latch.resources.tasks.custom_task",
        "latch.ldata.path.LPath",
        "latch.registry.table.Table",
        "latch_cli.services.launch.launch_v2.launch",
    )

    def test_a_fully_available_sdk_has_no_required_failures(self) -> None:
        report = self._report({name: True for name in self.REQUIRED})
        self.assertFalse(inspect_latch_sdk.has_required_failures(report))

    def test_any_single_missing_core_symbol_is_a_failure(self) -> None:
        for missing in self.REQUIRED:
            with self.subTest(missing=missing):
                availability = {name: True for name in self.REQUIRED}
                availability[missing] = False
                self.assertTrue(
                    inspect_latch_sdk.has_required_failures(self._report(availability))
                )

    def test_an_empty_report_counts_as_failing(self) -> None:
        self.assertTrue(
            inspect_latch_sdk.has_required_failures({"symbols": {}})
        )

    def test_every_required_symbol_is_one_the_script_catalogues(self) -> None:
        catalogued = {
            f"{module}.{symbol}"
            for entries in inspect_latch_sdk.SYMBOL_GROUPS.values()
            for module, symbol in entries
        }
        for name in self.REQUIRED:
            with self.subTest(symbol=name):
                self.assertIn(name, catalogued)


class ReportShapeTests(unittest.TestCase):
    def test_the_report_describes_the_environment_and_every_group(self) -> None:
        report = inspect_latch_sdk.build_report()
        self.assertEqual(
            set(report),
            {"python", "platform", "latch_version", "symbols", "methods"},
        )
        self.assertEqual(set(report["symbols"]), set(inspect_latch_sdk.SYMBOL_GROUPS))
        self.assertEqual(set(report["methods"]), set(inspect_latch_sdk.METHODS))

    def test_the_report_is_json_serialisable(self) -> None:
        # --json is the documented machine-readable path, so nothing in the
        # report may be a non-serialisable introspection object.
        json.dumps(inspect_latch_sdk.build_report())

    def test_printing_a_report_without_the_sdk_does_not_raise(self) -> None:
        report = inspect_latch_sdk.build_report()
        import io
        from contextlib import redirect_stdout

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            inspect_latch_sdk.print_text(report)
        self.assertIn("Latch SDK:", buffer.getvalue())


class ExitCodeTests(unittest.TestCase):
    def _run(self, *flags: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "inspect_latch_sdk.py"), *flags],
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_a_missing_sdk_exits_two_regardless_of_strict(self) -> None:
        try:
            import latch  # noqa: F401
        except ImportError:
            pass
        else:
            self.skipTest("latch is installed; this asserts the not-installed path")

        for flags in ((), ("--strict",), ("--json",)):
            with self.subTest(flags=flags):
                result = self._run(*flags)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_json_output_parses_even_when_the_sdk_is_absent(self) -> None:
        result = self._run("--json")
        report = json.loads(result.stdout)
        self.assertIn("symbols", report)
        self.assertIn("latch_version", report)

    def test_an_installed_sdk_exits_zero(self) -> None:
        try:
            import latch  # noqa: F401
        except ImportError:
            self.skipTest("latch is not installed; run under --isolated")
        result = self._run()
        self.assertIn(result.returncode, (0, 1), result.stderr)


class WorkflowExampleTests(unittest.TestCase):
    """Exercise documented graphs locally; never register or launch compute."""

    def test_quickstart_workflows_run_without_network(self) -> None:
        try:
            import latch  # noqa: F401
        except ImportError:
            self.skipTest("latch is not installed; run under --isolated")

        examples = (
            (SKILL_ROOT / "SKILL.md", "reverse_complement_workflow(sequence='ACgt')", "acGT"),
            (
                SKILL_ROOT / "references" / "workflow-creation.md",
                "normalize_sample(sample_name=' Sample A ')",
                "Sample_A",
            ),
        )
        for source, invocation, expected in examples:
            with self.subTest(example=source.name), tempfile.TemporaryDirectory() as temp:
                code = re.findall(r"```python\n(.*?)\n```", source.read_text(), re.S)[0]
                # Actual files are necessary because task decorators inspect source.
                script = Path(temp) / "example.py"
                script.write_text(
                    "import socket\n"
                    "from unittest.mock import patch\n"
                    "patch.object(socket.socket, 'connect', "
                    "side_effect=AssertionError('network disabled')).start()\n"
                    + code
                    + f"\nassert {invocation} == {expected!r}\n",
                    encoding="utf-8",
                )
                result = subprocess.run(
                    [sys.executable, str(script)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
