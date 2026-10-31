"""Tests for the DNAnexus integration scripts.

`validate_dxapp` is an offline linter for `dxapp.json`, so the tests start from
one manifest that must be clean and mutate a single field per test. That shape
matters: a validator is only useful if a valid manifest stays silent, and a
suite built only from broken inputs never proves that.

`inspect_dxpy` introspects the installed `dxpy` SDK. Its report-shaping and
version-comparison logic is pure and tested here; anything needing the SDK
itself skips unless `dxpy` is installed, which it is under
`tests/run_all.py --isolated`.
"""

from __future__ import annotations

import copy
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "dnanexus-integration"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import inspect_dxpy  # noqa: E402
import validate_dxapp  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def valid_app_manifest() -> dict:
    """A minimal dxapp.json that must produce no errors and no warnings."""
    return {
        "name": "my-analysis-app",
        "title": "My Analysis App",
        "version": "1.2.3",
        "inputSpec": [
            {"name": "reads", "class": "file"},
            {"name": "threads", "class": "int", "optional": True},
        ],
        "outputSpec": [{"name": "report", "class": "file"}],
        "runSpec": {
            "file": "src/code.sh",
            "interpreter": "bash",
            "distribution": "Ubuntu",
            "release": "24.04",
            "version": "0",
        },
    }


def issue_codes(manifest: dict, kind: str = "auto") -> set[str]:
    _, issues = validate_dxapp.Validator(manifest, kind).validate()
    return {issue.code for issue in issues}


class ValidBaselineTests(unittest.TestCase):
    def test_a_correct_app_manifest_produces_nothing(self) -> None:
        kind, issues = validate_dxapp.Validator(valid_app_manifest(), "auto").validate()
        self.assertEqual(kind, "app")
        self.assertEqual([f"{i.code} at {i.path}" for i in issues], [])

    def test_kind_is_inferred_from_the_presence_of_version(self) -> None:
        manifest = valid_app_manifest()
        del manifest["version"]
        kind, _ = validate_dxapp.Validator(manifest, "auto").validate()
        self.assertEqual(kind, "applet")

        kind, _ = validate_dxapp.Validator(manifest, "app").validate()
        self.assertEqual(kind, "app")

    def test_an_applet_only_gets_a_warning_for_missing_specs(self) -> None:
        applet = {
            "name": "my-applet",
            "runSpec": {
                "file": "src/code.sh",
                "interpreter": "bash",
                "distribution": "Ubuntu",
                "release": "24.04",
                "version": "0",
            },
        }
        _, issues = validate_dxapp.Validator(applet, "applet").validate()
        severities = {issue.code: issue.severity for issue in issues}
        self.assertEqual(severities.get("missing-spec"), "warning")

        # The same omission is an error for an app.
        _, issues = validate_dxapp.Validator(applet, "app").validate()
        severities = {issue.code: issue.severity for issue in issues}
        self.assertEqual(severities.get("missing-spec"), "error")

    def test_a_non_object_root_is_rejected_without_further_checks(self) -> None:
        kind, issues = validate_dxapp.Validator(["not", "an", "object"], "auto").validate()
        self.assertEqual(kind, "unknown")
        self.assertEqual([issue.code for issue in issues], ["root-type"])

    def test_malformed_enum_types_are_reported_without_crashing(self) -> None:
        for value in ([], {}):
            manifest = valid_app_manifest()
            manifest["inputSpec"][0]["class"] = value
            manifest["runSpec"].update({
                "interpreter": value, "release": value, "restartableEntryPoints": value,
            })
            manifest["httpsApp"] = {"ports": [value]}
            codes = issue_codes(manifest)
            self.assertTrue({
                "parameter-class", "interpreter", "release",
                "restartable-entry-points", "https-ports",
            }.issubset(codes))


class MetadataTests(unittest.TestCase):
    def test_name_is_required_and_character_restricted(self) -> None:
        manifest = valid_app_manifest()
        del manifest["name"]
        self.assertIn("missing-name", issue_codes(manifest))

        for bad in ("has space", "slash/name", "quote'name"):
            with self.subTest(name=bad):
                manifest = valid_app_manifest()
                manifest["name"] = bad
                self.assertIn("invalid-name", issue_codes(manifest))

    def test_app_versions_follow_api_freeform_character_contract(self) -> None:
        for bad in ("", "release/1", "release 1", "release:1", "α"):
            with self.subTest(version=bad):
                manifest = valid_app_manifest()
                manifest["version"] = bad
                self.assertIn("invalid-version", issue_codes(manifest))

        for good in ("0.0.1", "1.2.3-beta.1", "1.2.3+build5", "v1", "1.2", "release_2026"):
            with self.subTest(version=good):
                manifest = valid_app_manifest()
                manifest["version"] = good
                self.assertNotIn("invalid-version", issue_codes(manifest))

    def test_app_names_cannot_use_the_reserved_id_prefix(self) -> None:
        manifest = valid_app_manifest()
        manifest["name"] = "app-qc"
        self.assertIn("invalid-name", issue_codes(manifest))

    def test_top_level_resources_is_flagged_as_deprecated(self) -> None:
        manifest = valid_app_manifest()
        manifest["resources"] = ["project-xxxx:/assets"]
        self.assertIn("deprecated-resources", issue_codes(manifest))


class ParameterSpecTests(unittest.TestCase):
    def test_parameter_names_follow_the_identifier_rule(self) -> None:
        for bad in ("2reads", "has-dash", "has space", ""):
            with self.subTest(name=bad):
                manifest = valid_app_manifest()
                manifest["inputSpec"][0]["name"] = bad
                self.assertIn("parameter-name", issue_codes(manifest))

    def test_duplicate_parameter_names_are_rejected(self) -> None:
        manifest = valid_app_manifest()
        manifest["inputSpec"][1]["name"] = "reads"
        self.assertIn("duplicate-parameter", issue_codes(manifest))

    def test_unknown_and_array_classes(self) -> None:
        manifest = valid_app_manifest()
        manifest["inputSpec"][0]["class"] = "array:file"
        self.assertNotIn("parameter-class", issue_codes(manifest))

        manifest["inputSpec"][0]["class"] = "array:blob"
        self.assertIn("parameter-class", issue_codes(manifest))

        manifest["inputSpec"][0]["class"] = "array:hash"
        self.assertIn("parameter-class", issue_codes(manifest))
        manifest["inputSpec"][0]["class"] = "hash"
        self.assertNotIn("parameter-class", issue_codes(manifest))

    def test_optional_must_be_a_boolean(self) -> None:
        manifest = valid_app_manifest()
        manifest["inputSpec"][1]["optional"] = "yes"
        self.assertIn("optional-type", issue_codes(manifest))

    def test_input_only_fields_are_rejected_in_the_output_spec(self) -> None:
        for field in ("default", "suggestions", "choices"):
            with self.subTest(field=field):
                manifest = valid_app_manifest()
                manifest["outputSpec"][0][field] = "x"
                self.assertIn("output-only-field", issue_codes(manifest))

        # ...and accepted in the input spec.
        manifest = valid_app_manifest()
        manifest["inputSpec"][1]["default"] = 4
        self.assertNotIn("output-only-field", issue_codes(manifest))

    def test_a_spec_that_is_not_a_list_is_reported_once(self) -> None:
        manifest = valid_app_manifest()
        manifest["inputSpec"] = {"reads": "file"}
        self.assertIn("spec-type", issue_codes(manifest))


class RunSpecTests(unittest.TestCase):
    def test_runspec_is_required(self) -> None:
        manifest = valid_app_manifest()
        del manifest["runSpec"]
        self.assertIn("missing-runspec", issue_codes(manifest))

    def test_an_entry_source_is_required_and_should_not_be_doubled(self) -> None:
        manifest = valid_app_manifest()
        del manifest["runSpec"]["file"]
        self.assertIn("missing-entry-source", issue_codes(manifest))

        manifest = valid_app_manifest()
        manifest["runSpec"]["code"] = "echo hi"
        self.assertIn("multiple-entry-sources", issue_codes(manifest))

    def test_interpreter_distribution_release_and_aee_version_are_pinned(self) -> None:
        checks = {
            "interpreter": ("perl", "interpreter"),
            "distribution": ("Debian", "distribution"),
            "release": ("22.04", "release"),
            "version": ("1", "aee-version"),
        }
        for field, (value, code) in checks.items():
            with self.subTest(field=field):
                manifest = valid_app_manifest()
                manifest["runSpec"][field] = value
                self.assertIn(code, issue_codes(manifest))

    def test_ubuntu_2004_is_supported_but_flagged_as_legacy(self) -> None:
        manifest = valid_app_manifest()
        manifest["runSpec"]["release"] = "20.04"
        codes = issue_codes(manifest)
        self.assertNotIn("release", codes)
        self.assertIn("legacy-release", codes)

    def test_deprecated_system_requirements_location_is_flagged(self) -> None:
        manifest = valid_app_manifest()
        manifest["runSpec"]["systemRequirements"] = {"*": {"instanceType": "mem1_ssd1_v2_x4"}}
        self.assertIn("deprecated-system-requirements", issue_codes(manifest))

    def test_restartable_entry_points_are_constrained_and_warned_about(self) -> None:
        manifest = valid_app_manifest()
        manifest["runSpec"]["restartableEntryPoints"] = "some"
        self.assertIn("restartable-entry-points", issue_codes(manifest))

        manifest = valid_app_manifest()
        manifest["runSpec"]["restartableEntryPoints"] = "all"
        codes = issue_codes(manifest)
        self.assertNotIn("restartable-entry-points", codes)
        self.assertIn("restart-idempotency", codes)


class PolicyTests(unittest.TestCase):
    def test_unpinned_dependencies_are_warned_about(self) -> None:
        manifest = valid_app_manifest()
        manifest["runSpec"]["execDepends"] = [{"name": "samtools"}]
        self.assertIn("floating-dependency", issue_codes(manifest))

        manifest["runSpec"]["execDepends"] = [{"name": "samtools", "version": "1.19"}]
        self.assertNotIn("floating-dependency", issue_codes(manifest))

    def test_dependency_entries_must_be_named_objects(self) -> None:
        manifest = valid_app_manifest()
        manifest["runSpec"]["execDepends"] = ["samtools"]
        self.assertIn("dependency-type", issue_codes(manifest))

        manifest["runSpec"]["execDepends"] = [{"version": "1.19"}]
        self.assertIn("dependency-name", issue_codes(manifest))

    def test_max_restarts_is_bounded_and_rejects_booleans(self) -> None:
        for bad in (-1, 10, 99, True, "3"):
            with self.subTest(value=bad):
                manifest = valid_app_manifest()
                manifest["runSpec"]["executionPolicy"] = {"maxRestarts": bad}
                self.assertIn("max-restarts", issue_codes(manifest))

        manifest = valid_app_manifest()
        manifest["runSpec"]["executionPolicy"] = {"maxRestarts": 0}
        self.assertNotIn("max-restarts", issue_codes(manifest))

    def test_restart_reasons_are_checked_against_the_documented_set(self) -> None:
        manifest = valid_app_manifest()
        manifest["runSpec"]["executionPolicy"] = {"restartOn": {"MadeUpError": 2}}
        self.assertIn("unknown-restart-reason", issue_codes(manifest))

        manifest["runSpec"]["executionPolicy"] = {"restartOn": {"ExecutionError": 2}}
        self.assertNotIn("unknown-restart-reason", issue_codes(manifest))

        manifest["runSpec"]["executionPolicy"] = {"restartOn": {"ExecutionError": -1}}
        self.assertIn("restart-count", issue_codes(manifest))

    def test_timeout_units_and_values_are_constrained(self) -> None:
        manifest = valid_app_manifest()
        manifest["runSpec"]["timeoutPolicy"] = {"*": {"hours": 12}}
        self.assertEqual(issue_codes(manifest), set())

        manifest["runSpec"]["timeoutPolicy"] = {"*": {"weeks": 1}}
        self.assertIn("timeout-unit", issue_codes(manifest))

        manifest["runSpec"]["timeoutPolicy"] = {"*": {"hours": -1}}
        self.assertIn("timeout-value", issue_codes(manifest))

        manifest["runSpec"]["timeoutPolicy"] = {"*": {}}
        self.assertIn("timeout-duration", issue_codes(manifest))


class RegionalOptionTests(unittest.TestCase):
    def test_region_identifiers_should_be_provider_qualified(self) -> None:
        manifest = valid_app_manifest()
        manifest["regionalOptions"] = {"us-east-1": {}}
        self.assertIn("region-name", issue_codes(manifest))

        manifest["regionalOptions"] = {"aws:us-east-1": {}}
        self.assertNotIn("region-name", issue_codes(manifest))

    def test_system_requirements_must_cover_every_region_or_none(self) -> None:
        manifest = valid_app_manifest()
        manifest["regionalOptions"] = {
            "aws:us-east-1": {"systemRequirements": {"*": {"instanceType": "mem1_ssd1_v2_x4"}}},
            "azure:westus": {},
        }
        self.assertIn("inconsistent-regional-requirements", issue_codes(manifest))

        manifest["regionalOptions"]["azure:westus"] = {
            "systemRequirements": {"*": {"instanceType": "azure:mem1_ssd1_x4"}}
        }
        self.assertNotIn("inconsistent-regional-requirements", issue_codes(manifest))

    def test_fixed_instance_is_valid_with_a_cluster(self) -> None:
        manifest = valid_app_manifest()
        manifest["regionalOptions"] = {
            "aws:us-east-1": {
                "systemRequirements": {
                    "*": {
                        "instanceType": "mem1_ssd1_v2_x4",
                        "clusterSpec": {"type": "generic", "initialInstanceCount": 2},
                    }
                }
            }
        }
        self.assertNotIn("resource-selector-conflict", issue_codes(manifest))
        request = manifest["regionalOptions"]["aws:us-east-1"]["systemRequirements"]["*"]
        request["instanceTypeSelector"] = {"allowedInstanceTypes": ["mem1_ssd1_v2_x4"]}
        self.assertIn("resource-selector-conflict", issue_codes(manifest))
        del request["instanceType"]
        self.assertIn("resource-selector-conflict", issue_codes(manifest))

    def test_regional_and_legacy_system_requirements_cannot_coexist(self) -> None:
        manifest = valid_app_manifest()
        requirements = {"main": {"instanceType": "mem1_ssd1_v2_x4"}}
        manifest["runSpec"]["systemRequirements"] = requirements
        manifest["regionalOptions"] = {"aws:us-east-1": {"systemRequirements": requirements}}
        self.assertIn("conflicting-system-requirements", issue_codes(manifest))

    def test_instance_type_selector_needs_a_non_empty_string_list(self) -> None:
        def with_selector(selector):
            manifest = valid_app_manifest()
            manifest["regionalOptions"] = {
                "aws:us-east-1": {
                    "systemRequirements": {"*": {"instanceTypeSelector": selector}}
                }
            }
            return issue_codes(manifest)

        self.assertIn("allowed-instance-types", with_selector({"allowedInstanceTypes": []}))
        self.assertIn("allowed-instance-types", with_selector({"allowedInstanceTypes": [1]}))
        self.assertIn(
            "duplicate-instance-type",
            with_selector({"allowedInstanceTypes": ["a", "a"]}),
        )
        self.assertNotIn(
            "allowed-instance-types",
            with_selector({"allowedInstanceTypes": ["mem1_ssd1_v2_x4"]}),
        )


class AccessAndSecretTests(unittest.TestCase):
    def test_broad_and_privileged_access_is_warned_about(self) -> None:
        manifest = valid_app_manifest()
        manifest["access"] = {"network": ["*"]}
        self.assertIn("broad-network", issue_codes(manifest))

        manifest["access"] = {"network": ["api.example.invalid"]}
        self.assertNotIn("broad-network", issue_codes(manifest))

        manifest["access"] = {"project": "ADMINISTER"}
        self.assertIn("admin-project-access", issue_codes(manifest))

        manifest["access"] = {"allProjects": "VIEW"}
        self.assertIn("all-projects-access", issue_codes(manifest))

        manifest["access"] = {"developer": True}
        self.assertIn("developer-access", issue_codes(manifest))

    def test_access_levels_are_checked_against_the_documented_set(self) -> None:
        manifest = valid_app_manifest()
        for field in ("project", "allProjects"):
            for invalid in ("READWRITE", "NONE", [], {}):
                with self.subTest(field=field, invalid=invalid):
                    manifest["access"] = {field: invalid}
                    self.assertIn("access-level", issue_codes(manifest))

    def test_embedded_credentials_are_found_at_any_depth(self) -> None:
        manifest = valid_app_manifest()
        manifest["runSpec"]["assetDepends"] = [{"api_token": "sk-live-abc123"}]
        self.assertIn("embedded-secret", issue_codes(manifest))

        manifest = valid_app_manifest()
        manifest["details"] = {"nested": {"private-key": "-----BEGIN..."}}
        self.assertIn("embedded-secret", issue_codes(manifest))

    def test_placeholder_credentials_are_not_flagged(self) -> None:
        for placeholder in ("", "changeme", "PLACEHOLDER", "<token>", "  redacted  "):
            with self.subTest(value=placeholder):
                manifest = valid_app_manifest()
                manifest["details"] = {"password": placeholder}
                self.assertNotIn("embedded-secret", issue_codes(manifest))

    def test_a_secret_key_holding_false_is_a_setting_not_a_credential(self) -> None:
        manifest = valid_app_manifest()
        manifest["details"] = {"use_token": False}
        self.assertNotIn("embedded-secret", issue_codes(manifest))

    def test_secret_detection_matches_whole_words_only(self) -> None:
        # SECRET_KEY_RE anchors on word boundaries so `tokenizer` is not a token.
        manifest = valid_app_manifest()
        manifest["details"] = {"tokenizer": "bpe"}
        self.assertNotIn("embedded-secret", issue_codes(manifest))

    def test_https_ports_are_restricted(self) -> None:
        manifest = valid_app_manifest()
        manifest["httpsApp"] = {"ports": [443]}
        self.assertNotIn("https-ports", issue_codes(manifest))

        for bad in ([], [22], [443, 9000], "443"):
            with self.subTest(ports=bad):
                manifest["httpsApp"] = {"ports": bad}
                self.assertIn("https-ports", issue_codes(manifest))


class CommandLineTests(unittest.TestCase):
    def _run(self, manifest, *flags) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dxapp.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPTS / "validate_dxapp.py"), str(path), *flags],
                capture_output=True,
                text=True,
                timeout=60,
            )

    def test_a_clean_manifest_exits_zero(self) -> None:
        result = self._run(valid_app_manifest())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Errors: 0", result.stdout)

    def test_errors_exit_one(self) -> None:
        manifest = valid_app_manifest()
        del manifest["name"]
        self.assertEqual(self._run(manifest).returncode, 1)

    def test_strict_promotes_warnings_to_a_failure(self) -> None:
        manifest = valid_app_manifest()
        manifest["runSpec"]["release"] = "20.04"  # warning only
        self.assertEqual(self._run(manifest).returncode, 0)
        self.assertEqual(self._run(manifest, "--strict").returncode, 1)

    def test_json_output_is_machine_readable(self) -> None:
        manifest = valid_app_manifest()
        manifest["access"] = {"network": ["*"]}
        result = self._run(manifest, "--json")
        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertEqual(report["kind"], "app")
        self.assertEqual(report["warnings"], 1)
        self.assertEqual(report["issues"][0]["code"], "broad-network")

    def test_unreadable_manifest_exits_two_with_a_parse_issue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dxapp.json"
            path.write_text("{not json", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "validate_dxapp.py"),
                    str(path),
                    "--json",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertFalse(report["valid"])
        self.assertEqual(report["issues"][0]["code"], "parse")


class SummaryTests(unittest.TestCase):
    def test_summarize_counts_both_severities(self) -> None:
        issues = [
            validate_dxapp.Issue("error", "a", "$", "m"),
            validate_dxapp.Issue("warning", "b", "$", "m"),
            validate_dxapp.Issue("warning", "c", "$", "m"),
        ]
        self.assertEqual(validate_dxapp.summarize(issues), {"error": 1, "warning": 2})

    def test_summarize_of_nothing_is_zeroed_not_empty(self) -> None:
        self.assertEqual(validate_dxapp.summarize([]), {"error": 0, "warning": 0})


class SdkInspectionTests(unittest.TestCase):
    """`inspect_dxpy`'s pure helpers; the SDK-dependent report needs dxpy."""

    def test_version_comparison_is_numeric_not_lexicographic(self) -> None:
        parse = inspect_dxpy.numeric_version
        self.assertEqual(parse("0.410.0"), (0, 410, 0))
        # The bug this guards: "0.99" > "0.410" as strings, but not as versions.
        self.assertLess(parse("0.99.0"), parse("0.410.0"))
        self.assertGreater(parse("1.0.0"), parse("0.410.0"))

    def test_version_comparison_tolerates_non_numeric_segments(self) -> None:
        # Never raise on an unexpected version string -- the script's job is to
        # report, not to crash on a pre-release tag.
        self.assertIsInstance(inspect_dxpy.numeric_version("0.410.0rc1"), tuple)
        self.assertIsInstance(inspect_dxpy.numeric_version(""), tuple)

    def test_documented_baseline_is_a_parseable_version(self) -> None:
        self.assertRegex(inspect_dxpy.DOCUMENTED_BASELINE, r"^\d+\.\d+\.\d+$")
        self.assertTrue(inspect_dxpy.numeric_version(inspect_dxpy.DOCUMENTED_BASELINE))

    def test_required_symbols_are_dxpy_qualified_names(self) -> None:
        self.assertTrue(inspect_dxpy.REQUIRED_SYMBOLS)
        for name in inspect_dxpy.REQUIRED_SYMBOLS:
            with self.subTest(symbol=name):
                self.assertTrue(name.startswith("dxpy."))

    def test_missing_symbol_detection_reads_the_report_not_the_sdk(self) -> None:
        symbol = "dxpy.upload_local_file"
        self.assertIn(symbol, inspect_dxpy.REQUIRED_SYMBOLS)

        # An empty report means nothing was observed, so everything is missing.
        self.assertEqual(
            inspect_dxpy.missing_required_symbols({}),
            sorted(inspect_dxpy.REQUIRED_SYMBOLS),
        )

        report = {
            "symbols": {
                "dxpy": [{"qualified_name": symbol, "available": False}],
            }
        }
        self.assertIn(symbol, inspect_dxpy.missing_required_symbols(report))

        report["symbols"]["dxpy"][0]["available"] = True
        self.assertNotIn(symbol, inspect_dxpy.missing_required_symbols(report))

    def test_missing_method_detection_reads_the_report(self) -> None:
        missing = inspect_dxpy.missing_required_methods({})
        self.assertIn("DXFile.describe", missing)
        self.assertEqual(missing, sorted(missing))

        report = {"methods": {"DXFile": {"describe": {"available": True}}}}
        self.assertNotIn("DXFile.describe", inspect_dxpy.missing_required_methods(report))

    def test_report_generation_needs_the_sdk(self) -> None:
        try:
            importlib.import_module("dxpy")
        except ImportError:
            self.skipTest("dxpy is not installed; run under --isolated")

        report = inspect_dxpy.build_report()
        self.assertEqual(
            set(report),
            {
                "schema_version",
                "python",
                "platform",
                "documented_baseline",
                "dxpy_version",
                "version_meets_baseline",
                "symbols",
                "methods",
                "known_legacy_checks",
            },
        )
        self.assertEqual(
            report["documented_baseline"], inspect_dxpy.DOCUMENTED_BASELINE
        )
        # The report must be usable by the two consumers below.
        self.assertEqual(inspect_dxpy.missing_required_symbols(report), [])
        self.assertEqual(inspect_dxpy.missing_required_methods(report), [])

    def test_the_installed_sdk_meets_the_documented_baseline(self) -> None:
        try:
            importlib.import_module("dxpy")
        except ImportError:
            self.skipTest("dxpy is not installed; run under --isolated")

        report = inspect_dxpy.build_report()
        # Recomputed independently of the script's own comparison.
        self.assertEqual(
            report["version_meets_baseline"],
            inspect_dxpy.numeric_version(report["dxpy_version"])
            >= inspect_dxpy.numeric_version(inspect_dxpy.DOCUMENTED_BASELINE),
        )

    def test_the_report_is_json_serialisable(self) -> None:
        try:
            importlib.import_module("dxpy")
        except ImportError:
            self.skipTest("dxpy is not installed; run under --isolated")
        # --json is the documented machine-readable path.
        json.dumps(inspect_dxpy.build_report())


if __name__ == "__main__":
    unittest.main()
