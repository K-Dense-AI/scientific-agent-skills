#!/usr/bin/env python3
"""Synthetic, network-free tests for the uncertainty-and-units helper CLIs."""

from __future__ import annotations

import ast
import json
import math
import stat
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "uncertainty-and-units"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _common  # noqa: E402
import audit_units  # noqa: E402
import check_plausibility  # noqa: E402
import convert_units  # noqa: E402
import format_result  # noqa: E402
import propagate_uncertainty  # noqa: E402
import uncertainty_budget  # noqa: E402

MODULES = (
    audit_units,
    check_plausibility,
    convert_units,
    format_result,
    propagate_uncertainty,
    uncertainty_budget,
)


def _available(name: str) -> bool:
    """Report whether an optional scientific package can be imported."""

    try:
        __import__(name)
    except ImportError:
        return False
    return True


HAS_NUMPY = _available("numpy")
HAS_SCIPY = _available("scipy")
HAS_PINT = _available("pint")
HAS_UNCERTAINTIES = _available("uncertainties")


HAZARD_SOURCE = '''
import math
import numpy as np
import pint
from scipy.optimize import curve_fit
from uncertainties import ufloat

ureg = pint.UnitRegistry()
spare = pint.UnitRegistry()

R_GAS = 8.314462618


def analyse(readings, xs, ys, sigma):
    spread = np.std(readings)
    length = (12.7 * ureg.mm).magnitude
    safe = (12.7 * ureg.mm).to("m").magnitude
    bath = ureg.Quantity(37.0, "degC")
    gain = ureg.Quantity(3.0, "dB")
    popt, pcov = curve_fit(lambda x, a, b: a * x + b, xs, ys, sigma=sigma)
    slope = ufloat(popt[0], 0.1)
    copy = ufloat(slope.nominal_value, slope.std_dev)
    return math.log(2.0) + spread + length + safe + R_GAS + bath + gain + copy
'''

CLEAN_SOURCE = '''
import numpy as np
import pint
from scipy.optimize import curve_fit

ureg = pint.get_application_registry()


def analyse(readings, xs, ys, sigma):
    spread = np.std(readings, ddof=1)
    length = (12.7 * ureg.mm).m_as("m")
    popt, pcov = curve_fit(lambda x, a, b: a * x + b, xs, ys, sigma=sigma,
                           absolute_sigma=True)
    return spread + length + popt[0] + pcov[0, 0]
'''


class CommonSafetyTests(unittest.TestCase):
    def test_json_output_is_private_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            _common.emit_json({"ok": True}, output=output)
            self.assertEqual(json.loads(output.read_text()), {"ok": True})
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            with self.assertRaises(_common.CliError):
                _common.emit_json({"ok": False}, output=output)
            _common.emit_json({"ok": False}, output=output, force=True)
            self.assertEqual(json.loads(output.read_text()), {"ok": False})

    def test_local_paths_reject_urls_and_symlinks(self) -> None:
        with self.assertRaises(_common.CliError):
            _common.checked_input_file(
                "https://example.invalid/model.json", suffixes={".json"}
            )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "model.json"
            real.write_text("{}", encoding="utf-8")
            link = root / "link.json"
            try:
                link.symlink_to(real)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaises(_common.CliError):
                _common.checked_input_file(link, suffixes={".json"})

    def test_no_shadow_modules_network_or_environment_reads(self) -> None:
        filenames = {path.name for path in SCRIPTS.glob("*.py")}
        for shadowed in ("pint.py", "uncertainties.py", "numpy.py", "scipy.py"):
            self.assertNotIn(shadowed, filenames)
        banned = {"aiohttp", "httpx", "requests", "socket", "urllib", "subprocess"}
        for path in SCRIPTS.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots = {alias.name.split(".", 1)[0] for alias in node.names}
                    self.assertFalse(roots & banned, path.name)
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split(".", 1)[0], banned, path.name)
                if isinstance(node, ast.Attribute):
                    self.assertFalse(
                        isinstance(node.value, ast.Name)
                        and node.value.id == "os"
                        and node.attr in {"environ", "getenv"},
                        path.name,
                    )

    def test_skill_directory_ships_no_bytecode_or_tests(self) -> None:
        self.assertEqual(list(SKILL_ROOT.rglob("*.pyc")), [])
        self.assertEqual(list(SKILL_ROOT.rglob("__pycache__")), [])
        self.assertEqual(list(SKILL_ROOT.rglob("test_*.py")), [])
        self.assertFalse((SKILL_ROOT / "tests").exists())

    def test_help_is_available_without_running_workflows(self) -> None:
        for module in MODULES:
            with self.subTest(module=module.__name__):
                help_text = module.build_parser().format_help()
                self.assertIn("usage:", help_text)
                self.assertIn("--help", help_text)


class ExpressionParsingTests(unittest.TestCase):
    def test_accepts_arithmetic_and_whitelisted_functions(self) -> None:
        tree = _common.parse_expression("sqrt(a**2 + b**2) / (pi * c)")
        self.assertEqual(_common.expression_variables(tree), ["a", "b", "c"])

    def test_rejects_everything_that_is_not_arithmetic(self) -> None:
        hostile = [
            "__import__('os').system('true')",
            "open('secret')",
            "a.b",
            "a if b else c",
            "[x for x in range(3)]",
            "lambda x: x",
            "a == b",
            "os.environ",
            "eval('1')",
            "a; b",
            "(a := 2)",
        ]
        for expression in hostile:
            with self.subTest(expression=expression):
                with self.assertRaises(_common.CliError):
                    _common.parse_expression(expression)

    def test_rejects_unbounded_expressions(self) -> None:
        with self.assertRaises(_common.CliError):
            _common.parse_expression("x" * (_common.MAX_EXPRESSION_CHARS + 1))
        with self.assertRaises(_common.CliError):
            _common.parse_expression("x ** 1000")
        with self.assertRaises(_common.CliError):
            _common.parse_expression("sqrt(" * 40 + "x" + ")" * 40)
        with self.assertRaises(_common.CliError):
            _common.parse_expression("_hidden + 1")

    def test_reduction_uses_supplied_functions_only(self) -> None:
        tree = _common.parse_expression("sqrt(x) + 1")
        value = _common.reduce_expression(tree, {"x": 9.0}, {"sqrt": math.sqrt})
        self.assertAlmostEqual(value, 4.0)
        with self.assertRaises(_common.CliError):
            _common.reduce_expression(tree, {"x": 9.0}, {})
        with self.assertRaises(_common.CliError):
            _common.reduce_expression(tree, {}, {"sqrt": math.sqrt})


class MetrologyMathTests(unittest.TestCase):
    def test_welch_satterthwaite_matches_the_published_formula(self) -> None:
        # Two components of 0.03 with 9 dof each: nu_eff = 4 * 9 / 2 = 18.
        combined = math.sqrt(0.03**2 + 0.03**2)
        dof = _common.welch_satterthwaite(combined, [(0.03, 9), (0.03, 9)])
        self.assertAlmostEqual(dof, 18.0)

    def test_infinite_degrees_of_freedom_drop_out(self) -> None:
        combined = math.sqrt(0.03**2 + 0.04**2)
        dof = _common.welch_satterthwaite(
            combined, [(0.03, math.inf), (0.04, math.inf)]
        )
        self.assertEqual(dof, math.inf)

    def test_coverage_factor_matches_the_normal_limit(self) -> None:
        self.assertAlmostEqual(_common.coverage_factor(math.inf, 0.95), 1.959964, 5)

    @unittest.skipUnless(HAS_SCIPY, "SciPy is required for Student-t quantiles")
    def test_coverage_factor_follows_the_t_distribution(self) -> None:
        self.assertAlmostEqual(_common.coverage_factor(9, 0.95), 2.262157, 5)
        self.assertAlmostEqual(_common.coverage_factor(2, 0.95), 4.302653, 5)

    def test_numerical_tolerance_is_half_the_last_retained_digit(self) -> None:
        self.assertAlmostEqual(_common.numerical_tolerance(0.0472, 2), 0.0005)
        self.assertAlmostEqual(_common.numerical_tolerance(0.0472, 1), 0.005)
        with self.assertRaises(_common.CliError):
            _common.numerical_tolerance(0.0, 2)

    @unittest.skipUnless(HAS_NUMPY, "NumPy is required")
    def test_shortest_interval_finds_the_narrowest_window(self) -> None:
        import numpy as np

        sample = np.sort(np.concatenate([np.linspace(0.0, 1.0, 99), [50.0]]))
        low, high = _common.shortest_coverage_interval(sample, 0.9)
        self.assertLess(high, 2.0)
        self.assertGreaterEqual(low, 0.0)

    def test_distribution_divisors_follow_the_gum(self) -> None:
        self.assertAlmostEqual(_common.DISTRIBUTION_DIVISORS["rectangular"], 3**0.5)
        self.assertAlmostEqual(_common.DISTRIBUTION_DIVISORS["triangular"], 6**0.5)
        self.assertAlmostEqual(_common.DISTRIBUTION_DIVISORS["arcsine"], 2**0.5)


class FormatResultTests(unittest.TestCase):
    def test_value_is_rounded_to_the_uncertainty_decimal_place(self) -> None:
        rounded = format_result.round_to_uncertainty(12.34567, 0.02345)
        self.assertEqual(str(rounded["value"]), "12.346")
        self.assertEqual(str(rounded["uncertainty"]), "0.023")
        self.assertEqual(rounded["decimal_place"], -3)

    def test_carrying_uncertainty_recomputes_the_decimal_place(self) -> None:
        rounded = format_result.round_to_uncertainty(0.09996, 0.0996)
        self.assertEqual(str(rounded["uncertainty"]), "0.10")
        self.assertEqual(str(rounded["value"]), "0.10")
        self.assertEqual(rounded["decimal_place"], -2)

    def test_one_significant_digit_is_honoured(self) -> None:
        rounded = format_result.round_to_uncertainty(
            12.3456, 0.15, significant_digits=1
        )
        self.assertEqual(str(rounded["uncertainty"]), "0.2")
        self.assertEqual(str(rounded["value"]), "12.3")

    def test_concise_notation_matches_the_plus_minus_form(self) -> None:
        renderings = format_result.render(
            format_result.round_to_uncertainty(12.34567, 0.02345), None
        )
        self.assertEqual(renderings["plusminus"], "12.346 ± 0.023")
        self.assertEqual(renderings["parenthetic"], "12.346(23)")
        self.assertEqual(renderings["ascii"], "12.346 +/- 0.023")

    def test_digits_left_of_the_point_switch_to_scientific(self) -> None:
        renderings = format_result.render(
            format_result.round_to_uncertainty(1234.0, 250.0), None
        )
        self.assertEqual(renderings["plusminus"], "1230 ± 250")
        self.assertEqual(renderings["parenthetic"], "1.23(25)e+03")

    def test_extreme_exponents_avoid_a_run_of_zeros(self) -> None:
        renderings = format_result.render(
            format_result.round_to_uncertainty(9.1093837139e-31, 2.8e-40), "kg"
        )
        self.assertEqual(renderings["parenthetic"], "9.1093837139(28)e-31 kg")

    def test_zero_uncertainty_does_not_claim_exactness(self) -> None:
        renderings = format_result.render(
            format_result.round_to_uncertainty(299792458.0, 0.0), "m/s"
        )
        self.assertIn("zero supplied uncertainty", renderings["plusminus"])

    def test_warnings_cover_the_reporting_traps(self) -> None:
        rounded = format_result.round_to_uncertainty(
            12.3456, 0.15, significant_digits=1
        )
        warnings = format_result.collect_warnings(12.3456, 0.15, 1, rounded)
        self.assertTrue(any("one significant digit" in item for item in warnings))
        rounded = format_result.round_to_uncertainty(0.0012, 0.004)
        warnings = format_result.collect_warnings(0.0012, 0.004, 2, rounded)
        self.assertTrue(any("consistent with zero" in item for item in warnings))

    def test_bad_arguments_are_rejected(self) -> None:
        with self.assertRaises(_common.CliError):
            format_result.round_to_uncertainty(1.0, -1.0)
        with self.assertRaises(_common.CliError):
            format_result.round_to_uncertainty(1.0, 0.1, significant_digits=3)
        with self.assertRaises(_common.CliError):
            format_result.round_to_uncertainty(1.0, 0.1, rounding="up")

    def test_statement_names_the_coverage_factor(self) -> None:
        renderings = format_result.render(
            format_result.round_to_uncertainty(1.0, 0.1), None
        )
        self.assertIn("k = 1", format_result.build_statement(renderings, None, None))
        statement = format_result.build_statement(renderings, 2.26, 0.95)
        self.assertIn("k = 2.26", statement)
        self.assertIn("95%", statement)


class BudgetTests(unittest.TestCase):
    def _spec(self) -> dict:
        return {
            "measurand": "test",
            "unit": "mV",
            "value": 100.0,
            "coverage_probability": 0.95,
            "components": [
                {
                    "label": "repeatability",
                    "type": "A",
                    "distribution": "normal",
                    "value": 0.03,
                    "dof": 9,
                },
                {
                    "label": "certificate",
                    "type": "B",
                    "distribution": "expanded",
                    "value": 0.06,
                    "coverage_factor": 2.0,
                },
            ],
        }

    def test_divisors_follow_the_declared_distribution(self) -> None:
        component = uncertainty_budget.normalize_component(
            {"label": "resolution", "distribution": "rectangular", "value": 0.01},
            0,
            None,
        )
        self.assertAlmostEqual(component["standard_uncertainty"], 0.01 / math.sqrt(3))
        component = uncertainty_budget.normalize_component(
            {
                "label": "certificate",
                "distribution": "expanded",
                "value": 0.10,
                "coverage_factor": 2.0,
            },
            1,
            None,
        )
        self.assertAlmostEqual(component["standard_uncertainty"], 0.05)

    def test_relative_components_need_a_measurand_value(self) -> None:
        with self.assertRaises(_common.CliError):
            uncertainty_budget.normalize_component(
                {"label": "gain", "value": 0.01, "relative": True}, 0, None
            )
        component = uncertainty_budget.normalize_component(
            {"label": "gain", "value": 0.01, "relative": True}, 0, 250.0
        )
        self.assertAlmostEqual(component["standard_uncertainty"], 2.5)

    @unittest.skipUnless(HAS_SCIPY, "SciPy is required for Student-t quantiles")
    def test_combined_uncertainty_and_effective_dof(self) -> None:
        budget = uncertainty_budget.build_budget(self._spec(), None)
        self.assertAlmostEqual(
            budget["combined_standard_uncertainty"], math.sqrt(0.03**2 + 0.03**2)
        )
        self.assertAlmostEqual(budget["effective_degrees_of_freedom"], 36.0)
        self.assertGreater(budget["coverage_factor"], 2.0)
        self.assertLess(budget["coverage_factor"], 2.1)

    @unittest.skipUnless(HAS_SCIPY, "SciPy is required for Student-t quantiles")
    def test_small_sample_warning_and_type_a_dof_warning(self) -> None:
        spec = self._spec()
        spec["components"][0]["dof"] = 1
        budget = uncertainty_budget.build_budget(spec, None)
        self.assertLess(budget["effective_degrees_of_freedom"], 6.0)
        self.assertTrue(
            any("degrees of freedom" in item for item in budget["warnings"])
        )
        spec = self._spec()
        del spec["components"][0]["dof"]
        budget = uncertainty_budget.build_budget(spec, None)
        self.assertTrue(any("Type A" in item for item in budget["warnings"]))

    @unittest.skipUnless(HAS_SCIPY, "SciPy is required for Student-t quantiles")
    def test_undivided_type_b_normal_component_is_flagged(self) -> None:
        spec = self._spec()
        spec["components"][1] = {
            "label": "certificate",
            "type": "B",
            "distribution": "normal",
            "value": 0.06,
        }
        budget = uncertainty_budget.build_budget(spec, None)
        self.assertTrue(any("expanded" in item for item in budget["warnings"]))

    @unittest.skipUnless(HAS_SCIPY, "SciPy is required for Student-t quantiles")
    def test_report_is_strict_json_and_renders_markdown(self) -> None:
        budget = uncertainty_budget.build_budget(self._spec(), None)
        payload = json.dumps(budget, allow_nan=False)
        self.assertIn("combined_standard_uncertainty", payload)
        report = uncertainty_budget.render_markdown(budget)
        self.assertIn("| Component |", report)
        self.assertIn("Combined result", report)

    def test_malformed_specs_are_rejected(self) -> None:
        with self.assertRaises(_common.CliError):
            uncertainty_budget.build_budget({"components": []}, None)
        with self.assertRaises(_common.CliError):
            uncertainty_budget.build_budget({"components": ["nope"]}, None)
        with self.assertRaises(_common.CliError):
            uncertainty_budget.build_budget(
                {"components": [{"value": 1.0, "divisor": 0.0}]}, None
            )


@unittest.skipUnless(
    HAS_NUMPY and HAS_SCIPY and HAS_UNCERTAINTIES,
    "NumPy, SciPy, and uncertainties are required",
)
class PropagationTests(unittest.TestCase):
    def _framework(self, expression: str, variables, correlations=None):
        tree = _common.parse_expression(expression)
        records = propagate_uncertainty.normalize_variables(variables)
        return propagate_uncertainty.gum_framework(
            tree, records, correlations or {}, 0.95
        )

    def test_linear_model_matches_quadrature(self) -> None:
        framework = self._framework(
            "a + b",
            [
                {"name": "a", "value": 1.0, "standard_uncertainty": 0.3},
                {"name": "b", "value": 2.0, "standard_uncertainty": 0.4},
            ],
        )
        self.assertAlmostEqual(framework["value"], 3.0)
        self.assertAlmostEqual(framework["combined_standard_uncertainty"], 0.5)
        self.assertEqual(framework["covariance_term"], 0.0)

    def test_sensitivity_coefficients_are_analytic_partials(self) -> None:
        framework = self._framework(
            "a * b",
            [
                {"name": "a", "value": 3.0, "standard_uncertainty": 0.1},
                {"name": "b", "value": 5.0, "standard_uncertainty": 0.2},
            ],
        )
        sensitivities = {
            item["name"]: item["sensitivity"] for item in framework["inputs"]
        }
        self.assertAlmostEqual(sensitivities["a"], 5.0)
        self.assertAlmostEqual(sensitivities["b"], 3.0)

    def test_correlation_reduces_the_uncertainty_of_a_difference(self) -> None:
        framework = self._framework(
            "a - b",
            [
                {"name": "a", "value": 10.0, "standard_uncertainty": 0.3},
                {"name": "b", "value": 9.5, "standard_uncertainty": 0.3},
            ],
            {("a", "b"): 0.9},
        )
        expected = math.sqrt(0.3**2 + 0.3**2 - 2 * 0.9 * 0.3 * 0.3)
        self.assertAlmostEqual(framework["combined_standard_uncertainty"], expected)
        self.assertLess(framework["covariance_term"], 0.0)

    def test_monte_carlo_agrees_with_the_framework_on_a_linear_model(self) -> None:
        tree = _common.parse_expression("a + b")
        records = propagate_uncertainty.normalize_variables(
            [
                {"name": "a", "value": 1.0, "standard_uncertainty": 0.3},
                {"name": "b", "value": 2.0, "standard_uncertainty": 0.4},
            ]
        )
        framework = propagate_uncertainty.gum_framework(tree, records, {}, 0.95)
        sampling = propagate_uncertainty.monte_carlo(
            tree, records, {}, 0.95, _common.RECOMMENDED_TRIALS, 7
        )
        self.assertAlmostEqual(sampling["standard_uncertainty"], 0.5, places=2)
        validation = propagate_uncertainty.validate_linearization(
            framework, sampling, 2
        )
        self.assertTrue(validation["endpoint_agreement"])
        self.assertIsNone(validation["gum_framework_validated"])
        self.assertEqual(
            propagate_uncertainty.collect_warnings(framework, sampling, {}), []
        )

    def test_nonlinear_model_fails_the_clause_eight_check(self) -> None:
        tree = _common.parse_expression("x ** 2")
        records = propagate_uncertainty.normalize_variables(
            [{"name": "x", "value": 1.0, "standard_uncertainty": 0.5}]
        )
        framework = propagate_uncertainty.gum_framework(tree, records, {}, 0.95)
        sampling = propagate_uncertainty.monte_carlo(
            tree, records, {}, 0.95, 200_000, 11
        )
        validation = propagate_uncertainty.validate_linearization(
            framework, sampling, 2
        )
        self.assertFalse(validation["endpoint_agreement"])
        self.assertIsNone(validation["gum_framework_validated"])
        self.assertLess(framework["coverage_interval"][0], 0.0)
        self.assertGreaterEqual(sampling["shortest_coverage_interval"][0], 0.0)
        warnings = propagate_uncertainty.collect_warnings(framework, sampling, {})
        self.assertTrue(any("nonlinear" in item for item in warnings))

    def test_correlated_sampling_needs_normal_inputs(self) -> None:
        tree = _common.parse_expression("a - b")
        records = propagate_uncertainty.normalize_variables(
            [
                {
                    "name": "a",
                    "value": 1.0,
                    "standard_uncertainty": 0.1,
                    "distribution": "rectangular",
                },
                {"name": "b", "value": 1.0, "standard_uncertainty": 0.1},
            ]
        )
        with self.assertRaises(_common.CliError):
            propagate_uncertainty.monte_carlo(
                tree, records, {("a", "b"): 0.5}, 0.95, 1_000, 3
            )

    def test_impossible_correlation_matrix_is_rejected(self) -> None:
        tree = _common.parse_expression("a + b + c")
        records = propagate_uncertainty.normalize_variables(
            [
                {"name": name, "value": 1.0, "standard_uncertainty": 0.1}
                for name in ("a", "b", "c")
            ]
        )
        with self.assertRaises(_common.CliError):
            propagate_uncertainty.monte_carlo(
                tree,
                records,
                {("a", "b"): 0.99, ("a", "c"): 0.99, ("b", "c"): -0.99},
                0.95,
                1_000,
                3,
            )

    def test_variable_specification_parsing(self) -> None:
        record = propagate_uncertainty.parse_variable("d=20.0,0.02,rectangular,inf")
        self.assertEqual(record["name"], "d")
        self.assertEqual(record["distribution"], "rectangular")
        self.assertIsNone(record["dof"])
        with self.assertRaises(_common.CliError):
            propagate_uncertainty.parse_variable("d 20.0")
        with self.assertRaises(_common.CliError):
            propagate_uncertainty.parse_variable("d=20.0")
        with self.assertRaises(_common.CliError):
            propagate_uncertainty.normalize_variables(
                [{"name": "pi", "value": 1.0, "standard_uncertainty": 0.1}]
            )
        with self.assertRaises(_common.CliError):
            propagate_uncertainty.normalize_variables(
                [
                    {"name": "a", "value": 1.0, "standard_uncertainty": 0.1},
                    {"name": "a", "value": 2.0, "standard_uncertainty": 0.1},
                ]
            )

    def test_cli_rejects_a_model_with_missing_or_unused_inputs(self) -> None:
        parser = propagate_uncertainty.build_parser()
        arguments = parser.parse_args(
            ["--expression", "a + b", "--variable", "a=1.0,0.1"]
        )
        with self.assertRaises(_common.CliError):
            propagate_uncertainty.run(arguments)
        arguments = parser.parse_args(
            [
                "--expression",
                "a",
                "--variable",
                "a=1.0,0.1",
                "--variable",
                "b=1.0,0.1",
            ]
        )
        with self.assertRaises(_common.CliError):
            propagate_uncertainty.run(arguments)

    def test_end_to_end_report_is_strict_json(self) -> None:
        parser = propagate_uncertainty.build_parser()
        arguments = parser.parse_args(
            [
                "--expression",
                "m / (pi * (d / 2) ** 2 * h)",
                "--variable",
                "m=250.0,0.05",
                "--variable",
                "d=20.0,0.02,rectangular",
                "--variable",
                "h=40.0,0.05,rectangular",
                "--trials",
                "20000",
            ]
        )
        document = propagate_uncertainty.run(arguments)
        json.dumps(document, allow_nan=False)
        self.assertIn("validation", document)
        report = propagate_uncertainty.render_markdown(document)
        self.assertIn("Uncertainty budget", report)


@unittest.skipUnless(HAS_PINT, "pint is required")
class ConversionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = convert_units.build_registry()

    def test_plain_conversion_reports_a_factor(self) -> None:
        parser = convert_units.build_parser()
        arguments = parser.parse_args(["--value", "1", "--unit", "mm", "--to", "m"])
        document = convert_units.run(arguments)
        self.assertAlmostEqual(document["value"], 0.001)
        self.assertAlmostEqual(document["conversion_factor"], 0.001)

    def test_context_is_required_and_named_in_the_error(self) -> None:
        parser = convert_units.build_parser()
        arguments = parser.parse_args(["--value", "532", "--unit", "nm", "--to", "eV"])
        with self.assertRaises(_common.CliError) as caught:
            convert_units.run(arguments)
        self.assertIn("spectroscopy", str(caught.exception))

    def test_spectroscopy_context_converts_and_propagates(self) -> None:
        parser = convert_units.build_parser()
        arguments = parser.parse_args(
            [
                "--value",
                "532",
                "--unit",
                "nm",
                "--to",
                "eV",
                "--context",
                "spectroscopy",
                "--uncertainty",
                "0.5",
            ]
        )
        document = convert_units.run(arguments)
        self.assertAlmostEqual(document["value"], 2.3305300457, places=7)
        # E = hc/lambda, so u(E) = E * u(lambda) / lambda.
        self.assertAlmostEqual(
            document["uncertainty"], 2.3305300457 * 0.5 / 532.0, places=7
        )

    def test_offset_units_convert_the_value_and_the_difference_apart(self) -> None:
        parser = convert_units.build_parser()
        arguments = parser.parse_args(
            [
                "--value",
                "20",
                "--unit",
                "degC",
                "--to",
                "degF",
                "--uncertainty",
                "0.5",
            ]
        )
        document = convert_units.run(arguments)
        self.assertAlmostEqual(document["value"], 68.0, places=6)
        self.assertAlmostEqual(document["uncertainty"], 0.9, places=6)
        self.assertTrue(any("offset unit" in item for item in document["warnings"]))
        self.assertNotIn("conversion_factor", document)

    def test_unit_strings_are_bounded_and_screened(self) -> None:
        for hostile in ["", "m; import os", "m" * 200, "__class__", "lambda"]:
            with self.subTest(unit=hostile):
                with self.assertRaises(_common.CliError):
                    convert_units.checked_unit(hostile, label="--unit")

    def test_unknown_units_raise_a_cli_error(self) -> None:
        parser = convert_units.build_parser()
        arguments = parser.parse_args(
            ["--value", "1", "--unit", "smoots", "--to", "m"]
        )
        with self.assertRaises(_common.CliError):
            convert_units.run(arguments)


class AuditTests(unittest.TestCase):
    def _findings(self, source: str) -> list[dict]:
        return audit_units.audit_source(source, "sample.py")["findings"]

    def _rules(self, source: str) -> set[str]:
        return {finding["rule"] for finding in self._findings(source)}

    def test_every_rule_fires_on_the_hazard_fixture(self) -> None:
        rules = self._rules(HAZARD_SOURCE)
        for expected in (
            "UNIT001",
            "UNIT002",
            "UNIT003",
            "UNIT004",
            "UNC001",
            "UNC002",
            "UNC003",
            "UNC004",
            "CONST001",
        ):
            with self.subTest(rule=expected):
                self.assertIn(expected, rules)

    def test_clean_source_produces_no_findings(self) -> None:
        self.assertEqual(self._findings(CLEAN_SOURCE), [])

    def test_the_skills_own_scripts_are_clean(self) -> None:
        for path in sorted(SCRIPTS.glob("*.py")):
            with self.subTest(script=path.name):
                audited = audit_units.audit_source(
                    path.read_text(encoding="utf-8"), path.name
                )
                self.assertEqual(audited["findings"], [])

    def test_magnitude_after_an_explicit_conversion_is_accepted(self) -> None:
        self.assertEqual(self._findings('q = thing.to("m").magnitude\n'), [])
        findings = self._findings("q = thing.magnitude\n")
        self.assertEqual([item["rule"] for item in findings], ["UNIT003"])

    def test_directive_comments_suppress_and_are_counted(self) -> None:
        audited = audit_units.audit_source(
            "q = thing.magnitude  # audit-units: ignore UNIT003\n", "sample.py"
        )
        self.assertEqual(audited["findings"], [])
        self.assertEqual(audited["suppressed"], 1)

        audited = audit_units.audit_source(
            "q = thing.magnitude  # audit-units: ignore CONST001\n", "sample.py"
        )
        self.assertEqual([item["rule"] for item in audited["findings"]], ["UNIT003"])
        self.assertEqual(audited["suppressed"], 0)

        audited = audit_units.audit_source(
            "q = thing.magnitude  # audit-units: ignore\n", "sample.py"
        )
        self.assertEqual(audited["findings"], [])

        audited = audit_units.audit_source(
            "# audit-units: ignore-file UNIT003\nq = thing.magnitude\n", "sample.py"
        )
        self.assertEqual(audited["findings"], [])
        self.assertEqual(audited["suppressed"], 1)

    def test_suppression_parsing(self) -> None:
        per_line, whole_file = audit_units.parse_suppressions(
            "a = 1  # audit-units: ignore UNIT003, CONST001\n"
            "# audit-units: ignore-file UNC001\n"
            "b = 2  # audit-units: ignore\n"
        )
        self.assertEqual(per_line[1], {"UNIT003", "CONST001"})
        self.assertEqual(per_line[3], {"*"})
        self.assertEqual(whole_file, {"UNC001"})

    def test_a_standalone_directive_covers_the_next_line(self) -> None:
        audited = audit_units.audit_source(
            "# audit-units: ignore UNIT003\nq = thing.magnitude\n", "sample.py"
        )
        self.assertEqual(audited["findings"], [])
        self.assertEqual(audited["suppressed"], 1)
        audited = audit_units.audit_source(
            "# audit-units: ignore UNIT003\n\nq = thing.magnitude\n", "sample.py"
        )
        self.assertEqual([item["rule"] for item in audited["findings"]], ["UNIT003"])

    def test_delta_units_silence_the_offset_warning(self) -> None:
        self.assertIn("UNIT002", self._rules('bath = Q(37.0, "degC")\n'))
        self.assertNotIn(
            "UNIT002",
            self._rules('bath = Q(37.0, "degC") + Q(1.0, "delta_degC")\n'),
        )

    def test_constant_detection_needs_three_significant_digits(self) -> None:
        self.assertIn("CONST001", self._rules("g = 9.81\n"))
        self.assertNotIn("CONST001", self._rules("g = 9.8\n"))
        self.assertIn("CONST001", self._rules("c = 299792458\n"))
        self.assertNotIn("CONST001", self._rules("scale = 4.2\n"))

    def test_significant_digit_counting(self) -> None:
        self.assertEqual(audit_units.significant_digits(9.8), 2)
        self.assertEqual(audit_units.significant_digits(9.81), 3)
        self.assertEqual(audit_units.significant_digits(273.0), 3)
        self.assertEqual(audit_units.significant_digits(0.00012), 2)
        self.assertEqual(audit_units.significant_digits(299792458), 9)

    def test_findings_are_ordered_and_carry_a_remedy(self) -> None:
        findings = self._findings(HAZARD_SOURCE)
        lines = [finding["line"] for finding in findings]
        self.assertEqual(lines, sorted(lines))
        for finding in findings:
            self.assertIn(finding["severity"], {"low", "medium", "high"})
            self.assertTrue(finding["remedy"])
            self.assertGreaterEqual(finding["column"], 1)

    def test_exit_code_respects_the_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "hazards.py"
            target.write_text(HAZARD_SOURCE, encoding="utf-8")
            parser = audit_units.build_parser()
            arguments = parser.parse_args(["--input", str(target)])
            document = audit_units.run(arguments)
            self.assertEqual(audit_units.exit_code(document, "high"), 1)
            self.assertEqual(audit_units.exit_code(document, "none"), 0)
            report = audit_units.render_markdown(document)
            self.assertIn("Unit and uncertainty audit", report)
            json.dumps(document, allow_nan=False)

    def test_unparsable_source_is_reported_not_executed(self) -> None:
        with self.assertRaises(_common.CliError):
            audit_units.audit_source("def broken(:\n", "sample.py")


class PlausibilityCatalogueTests(unittest.TestCase):
    """Structural checks that need no scientific packages."""

    def test_every_expression_declares_the_inputs_it_uses(self) -> None:
        constants = {name for name, _, _ in check_plausibility.CONSTANT_UNITS}
        entries = check_plausibility.GROUPS + check_plausibility.SCALES
        for entry in entries:
            with self.subTest(entry=entry["name"]):
                tree = _common.parse_expression(entry["expression"])
                used = set(_common.expression_variables(tree)) - constants
                self.assertEqual(
                    used,
                    set(entry["inputs"]),
                    "declared inputs must match the free variables of the formula",
                )

    def test_regimes_are_ordered_and_cover_the_line(self) -> None:
        for entry in check_plausibility.GROUPS:
            with self.subTest(group=entry["name"]):
                regimes = entry["regimes"]
                self.assertIsNone(regimes[0][0])
                self.assertIsNone(regimes[-1][1])
                for lower, upper in zip(regimes, regimes[1:]):
                    self.assertEqual(lower[1], upper[0], "regimes must be contiguous")

    def test_bands_are_ordered_positive_and_cited(self) -> None:
        for entry in check_plausibility.BANDS:
            with self.subTest(band=entry["name"]):
                self.assertGreater(entry["low"], 0)
                self.assertGreater(entry["high"], entry["low"])
                self.assertTrue(entry["source"])

    def test_catalogue_names_are_unique(self) -> None:
        for kind in ("groups", "scales", "bands"):
            table = getattr(check_plausibility, kind.upper())
            names = [entry["name"] for entry in table]
            self.assertEqual(len(names), len(set(names)), kind)

    def test_quantity_specifications_are_screened(self) -> None:
        for hostile in ["", "1 m", "_hidden=1 m", "a b=1 m", "x=", "x=nan m"]:
            with self.subTest(text=hostile):
                with self.assertRaises(_common.CliError):
                    check_plausibility.parse_quantity(hostile, None)

    def test_orders_of_magnitude_has_no_infinities(self) -> None:
        self.assertIsNone(check_plausibility.orders_of_magnitude(0.0, 1.0))
        self.assertIsNone(check_plausibility.orders_of_magnitude(-2.0, 1.0))
        self.assertAlmostEqual(
            check_plausibility.orders_of_magnitude(100.0, 1.0), 2.0
        )

    def test_exit_code_respects_the_threshold(self) -> None:
        for verdict, threshold, expected in (
            ("implausible", "implausible", 1),
            ("questionable", "implausible", 0),
            ("questionable", "questionable", 1),
            ("plausible", "questionable", 0),
            ("implausible", "none", 0),
        ):
            with self.subTest(verdict=verdict, threshold=threshold):
                code = check_plausibility.exit_code({"verdict": verdict}, threshold)
                self.assertEqual(code, expected)


@unittest.skipUnless(HAS_PINT and HAS_SCIPY, "pint and SciPy are required")
class PlausibilityTests(unittest.TestCase):
    def _run(self, argv: list[str]) -> dict:
        return check_plausibility.run(check_plausibility.build_parser().parse_args(argv))

    def test_reynolds_matches_the_hand_computation(self) -> None:
        document = self._run(
            [
                "--quantity", "density=1060 kg/m**3",
                "--quantity", "velocity=0.5 mm/s",
                "--quantity", "length=8 um",
                "--quantity", "viscosity=3.5 mPa*s",
                "--group", "reynolds",
            ]
        )
        group = document["groups"][0]
        self.assertAlmostEqual(group["value"], 1060 * 5e-4 * 8e-6 / 3.5e-3)
        self.assertIn("laminar", group["regime"])
        self.assertEqual(document["verdict"], "plausible")
        json.dumps(document, allow_nan=False)

    def test_thermal_energy_tracks_scipy_constants(self) -> None:
        from scipy import constants

        document = self._run(
            ["--quantity", "temperature=300 K", "--scale", "thermal_energy"]
        )
        self.assertAlmostEqual(
            document["scales"][0]["value"] / (constants.k * 300.0), 1.0, places=9
        )

    def test_debye_length_matches_the_textbook_value(self) -> None:
        # 0.96 nm for a monovalent electrolyte at 100 mM and 25 C.
        document = self._run(
            [
                "--quantity", "temperature=298.15 K",
                "--quantity", "relative_permittivity=78.4",
                "--quantity", "ionic_strength=100 mol/m**3",
                "--scale", "debye_length",
            ]
        )
        self.assertAlmostEqual(document["scales"][0]["value"], 0.96, places=2)

    def test_wrong_dimensionality_is_caught_before_any_number(self) -> None:
        with self.assertRaises(_common.CliError) as caught:
            self._run(
                [
                    "--quantity", "density=1000 kg/m**3",
                    "--quantity", "velocity=1 m/s",
                    "--quantity", "length=0.01 m",
                    # kinematic viscosity where the formula needs dynamic
                    "--quantity", "viscosity=1e-6 m**2/s",
                    "--group", "reynolds",
                ]
            )
        self.assertIn("viscosity", str(caught.exception))
        self.assertIn("dimensionality", str(caught.exception))

    def test_a_dimensional_group_result_is_refused(self) -> None:
        registry = check_plausibility.build_registry()
        constants = check_plausibility.constant_quantities(registry)
        broken = {
            "name": "broken",
            "symbol": "X",
            "expression": "length",
            "inputs": {"length": "[length]"},
            "regimes": [[None, None, "any"]],
            "note": "",
            "source": "",
        }
        supplied = {"length": registry.Quantity(1.0, "m")}
        with self.assertRaises(_common.CliError) as caught:
            check_plausibility.evaluate_group(broken, supplied, constants)
        self.assertIn("dimensionless", str(caught.exception))

    def test_missing_inputs_name_their_dimensionality(self) -> None:
        with self.assertRaises(_common.CliError) as caught:
            self._run(["--quantity", "velocity=1 m/s", "--group", "reynolds"])
        message = str(caught.exception)
        for expected in ("density", "length", "viscosity"):
            self.assertIn(expected, message)

    def test_band_flags_an_order_of_magnitude_error(self) -> None:
        document = self._run(
            [
                "--quantity", "diameter=2 m",
                "--band", "eukaryotic_cell_diameter=diameter",
            ]
        )
        band = document["bands"][0]
        self.assertEqual(band["verdict"], "implausible")
        self.assertGreater(band["orders_of_magnitude_outside"], 4)
        self.assertEqual(document["verdict"], "implausible")
        self.assertTrue(document["warnings"])
        json.dumps(document, allow_nan=False)

    def test_band_accepts_a_value_inside_the_range(self) -> None:
        document = self._run(
            [
                "--quantity", "diameter=15 um",
                "--band", "eukaryotic_cell_diameter=diameter",
            ]
        )
        self.assertEqual(document["bands"][0]["verdict"], "plausible")
        self.assertEqual(document["verdict"], "plausible")

    def test_a_near_miss_is_questionable_not_implausible(self) -> None:
        document = self._run(
            [
                "--quantity", "diameter=140 um",
                "--band", "eukaryotic_cell_diameter=diameter",
            ]
        )
        self.assertEqual(document["bands"][0]["verdict"], "questionable")

    def test_a_non_positive_magnitude_stays_strict_json(self) -> None:
        document = self._run(
            [
                "--quantity", "diameter=-3 um",
                "--band", "eukaryotic_cell_diameter=diameter",
            ]
        )
        band = document["bands"][0]
        self.assertEqual(band["verdict"], "implausible")
        self.assertIsNone(band["orders_of_magnitude_outside"])
        json.dumps(document, allow_nan=False)

    def test_band_refuses_an_incomparable_dimension(self) -> None:
        with self.assertRaises(_common.CliError):
            self._run(
                [
                    "--quantity", "mass=3 kg",
                    "--band", "eukaryotic_cell_diameter=mass",
                ]
            )

    def test_constant_names_are_reserved(self) -> None:
        with self.assertRaises(_common.CliError) as caught:
            self._run(
                [
                    "--quantity", "k_B=1 J/K",
                    "--quantity", "temperature=300 K",
                    "--scale", "thermal_energy",
                ]
            )
        self.assertIn("k_B", str(caught.exception))

    def test_unknown_names_list_the_alternatives(self) -> None:
        with self.assertRaises(_common.CliError) as caught:
            self._run(["--group", "renolds"])
        self.assertIn("reynolds", str(caught.exception))

    def test_an_empty_request_is_rejected(self) -> None:
        with self.assertRaises(_common.CliError):
            self._run(["--quantity", "velocity=1 m/s"])

    def test_every_catalogue_entry_is_listed(self) -> None:
        document = self._run(["--list"])
        self.assertEqual(len(document["groups"]), len(check_plausibility.GROUPS))
        self.assertEqual(len(document["scales"]), len(check_plausibility.SCALES))
        self.assertEqual(len(document["bands"]), len(check_plausibility.BANDS))
        json.dumps(document, allow_nan=False)

    def test_markdown_report_renders(self) -> None:
        document = self._run(
            [
                "--quantity", "temperature=300 K",
                "--quantity", "diameter=15 um",
                "--quantity", "length=10 um",
                "--quantity", "diffusivity=1e-9 m**2/s",
                "--scale", "diffusion_time",
                "--band", "eukaryotic_cell_diameter=diameter",
            ]
        )
        report = check_plausibility.render_markdown(document)
        self.assertIn("Plausibility check", report)
        self.assertIn("Characteristic scales", report)
        self.assertIn("Magnitude bands", report)
        # 10 um across at 1e-9 m^2/s is 0.1 s, not minutes and not microseconds.
        self.assertAlmostEqual(document["scales"][0]["value"], 0.1, places=6)


if __name__ == "__main__":
    unittest.main()
