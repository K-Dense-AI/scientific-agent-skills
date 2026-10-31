"""Numerical regression checks for the 2026-10 API and metrology review."""
from pathlib import Path
import json
import math
import sys
import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "uncertainty-and-units"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import _common
import audit_units
import format_result
import uncertainty_budget


def test_duplicate_spec_keys_cannot_silently_replace_uncertainty(tmp_path):
    source = tmp_path / "model.json"
    source.write_text('{"u": 1, "u": 0}')
    with pytest.raises(_common.CliError, match="duplicate"):
        _common.load_json(source)


@pytest.mark.parametrize("expression", ["x + True", "x + 1e309", "sin(x,x)", "atan2(x)"])
def test_invalid_expression_semantics_rejected(expression):
    with pytest.raises(_common.CliError):
        _common.parse_expression(expression)


def test_tolerance_handles_rounding_carry():
    assert _common.numerical_tolerance(0.0996, 2) == pytest.approx(0.005)


@pytest.mark.parametrize("component", [
    {"value": 1, "distribution": "expanded"},
    {"value": 1, "distribution": "exact"},
    {"value": 1, "relative": "false"},
])
def test_budget_cannot_invent_missing_factor_or_exactness(component):
    with pytest.raises(_common.CliError):
        uncertainty_budget.normalize_component(component, 0, 2)


def test_budget_cannot_silently_ignore_covariance():
    with pytest.raises(_common.CliError, match="independent"):
        uncertainty_budget.build_budget({"components": [{"value": 1}], "covariance": [[1]]}, None)


def test_numpy_correction_alias_is_accepted_by_auditor():
    assert audit_units.audit_source("import numpy as np\nx = np.std(y, correction=1)", "analysis.py")["findings"] == []


def test_zero_uncertainty_is_not_exactness_certificate():
    report = format_result.run(format_result.build_parser().parse_args(["--value", "2", "--uncertainty", "0"]))
    assert "(exact)" not in report["renderings"]["plusminus"]
    assert report["warnings"]


def numerical_modules():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    pytest.importorskip("uncertainties")
    import propagate_uncertainty as propagation
    return np, propagation


def test_all_expression_functions_match_scalar_and_array_paths():
    np, _ = numerical_modules()
    from uncertainties import nominal_value, ufloat
    arguments = {"acos": [0.3], "acosh": [2.], "asin": [0.3], "atanh": [0.3],
                 "atan2": [0.3, 0.7], "hypot": [0.3, 0.7], "log": [2., 10.]}
    scalar, array = _common.scalar_functions(), _common.array_functions()
    for name in _common.ALLOWED_FUNCTIONS:
        args = arguments.get(name, [0.7])
        actual = array[name](*[np.array([v]) for v in args])
        expected = scalar[name](*[ufloat(v, .01) for v in args])
        assert float(actual[0]) == pytest.approx(nominal_value(expected)), name


@pytest.mark.parametrize("rho,expression", [(1., "a-b"), (-1., "a+b")])
def test_perfect_correlation_cancels_in_both_paths(rho, expression):
    _, propagation = numerical_modules()
    records = propagation.normalize_variables([{"name": v, "value": 1., "u": .1} for v in ("a", "b")])
    tree = _common.parse_expression(expression)
    corr = {("a", "b"): rho}
    gum = propagation.gum_framework(tree, records, corr, .95)
    mc = propagation.monte_carlo(tree, records, corr, .95, 10000, 1)
    assert gum["combined_standard_uncertainty"] == pytest.approx(0, abs=1e-12)
    assert mc["standard_uncertainty"] == pytest.approx(0, abs=1e-12)


def test_invalid_matrix_rejected_even_without_monte_carlo():
    _, propagation = numerical_modules()
    records = propagation.normalize_variables([{"name": v, "value": 1., "u": .1} for v in "abc"])
    with pytest.raises(_common.CliError, match="semidefinite"):
        propagation.gum_framework(_common.parse_expression("a+b+c"), records,
            {("a", "b"): .99, ("a", "c"): .99, ("b", "c"): -.99}, .95)


def test_correlated_finite_dof_not_given_invalid_welch_factor():
    _, propagation = numerical_modules()
    records = propagation.normalize_variables([{"name": v, "value": 1., "u": .1, "dof": 5} for v in "ab"])
    with pytest.raises(_common.CliError, match="finite degrees"):
        propagation.gum_framework(_common.parse_expression("a+b"), records, {("a", "b"): .5}, .95)


def test_self_correlation_rejected_in_json_spec(tmp_path):
    _, propagation = numerical_modules()
    source = tmp_path / "model.json"
    source.write_text(json.dumps({"expression": "a", "variables": [{"name": "a", "value": 1., "u": .1}], "correlations": [["a", "a", .5]]}))
    with pytest.raises(_common.CliError, match="itself"):
        propagation.run(propagation.build_parser().parse_args(["--spec", str(source)]))


def test_zero_linear_derivative_does_not_hide_nonlinear_spread():
    _, propagation = numerical_modules()
    tree = _common.parse_expression("x**2")
    records = propagation.normalize_variables([{"name": "x", "value": 0., "u": 1.}])
    gum = propagation.gum_framework(tree, records, {}, .95)
    mc = propagation.monte_carlo(tree, records, {}, .95, 100000, 2)
    assert gum["combined_standard_uncertainty"] == 0
    assert mc["mean"] == pytest.approx(1., abs=.02)
    assert mc["standard_uncertainty"] == pytest.approx(math.sqrt(2), abs=.04)
    diagnostic = propagation.validate_linearization(gum, mc, 2)
    assert diagnostic["endpoint_agreement"] is False
    assert diagnostic["gum_framework_validated"] is None


def convert(args):
    pytest.importorskip("pint")
    import convert_units
    return convert_units.run(convert_units.build_parser().parse_args(args))


def test_reciprocal_uncertainty_is_invariant_to_metre_vs_nanometre_inputs():
    common = ["--to", "eV", "--context", "spectroscopy"]
    nano = convert(["--value", "532", "--unit", "nm", "--uncertainty", ".5"] + common)
    metre = convert(["--value", "5.32e-7", "--unit", "m", "--uncertainty", "5e-10"] + common)
    expected = nano["value"] * .5 / 532
    assert metre["uncertainty"] == pytest.approx(expected, rel=1e-8)
    assert nano["uncertainty"] == pytest.approx(expected, rel=1e-8)


def test_kelvin_uncertainty_does_not_get_nonexistent_delta_unit():
    report = convert(["--value", "20", "--unit", "degC", "--to", "K", "--uncertainty", ".5"])
    assert report["uncertainty_unit"] == "K"
    assert report["uncertainty"] == pytest.approx(.5, rel=1e-8)


def test_logarithmic_level_difference_has_correct_unit():
    report = convert(["--value", "10", "--unit", "mW", "--to", "dBm", "--uncertainty", ".1"])
    assert report["uncertainty_unit"] == "dB"
    assert report["uncertainty"] == pytest.approx(10/math.log(10)*.1/10, rel=1e-8)


def test_unknown_context_has_controlled_error():
    with pytest.raises(_common.CliError, match="context"):
        convert(["--value", "1", "--unit", "nm", "--to", "eV", "--context", "missing_context"])


def plausibility(args):
    pytest.importorskip("pint")
    pytest.importorskip("scipy")
    import check_plausibility
    return check_plausibility.run(check_plausibility.build_parser().parse_args(args))


def test_celsius_thermal_energy_converts_to_absolute_temperature():
    report = plausibility(["--quantity", "temperature=26.85 degC", "--scale", "thermal_energy"])
    from scipy.constants import k
    assert report["scales"][0]["value"] == pytest.approx(300*k)


@pytest.mark.parametrize("value", ["-1 K", "-280 degC"])
def test_negative_absolute_temperature_rejected(value):
    with pytest.raises(_common.CliError, match="positive"):
        plausibility(["--quantity", "temperature="+value, "--scale", "thermal_energy"])


def test_zero_flow_is_a_valid_reynolds_limit():
    report = plausibility(["--quantity", "density=1000 kg/m**3", "--quantity", "velocity=0 m/s", "--quantity", "length=1 m", "--quantity", "viscosity=1 mPa*s", "--group", "reynolds"])
    assert report["groups"][0]["value"] == 0
    assert not report["warnings"]


def test_molar_mass_band_uses_mass_per_amount():
    report = plausibility(["--quantity", "mass=50 kg/mol", "--band", "protein_molar_mass=mass"])
    assert report["bands"][0]["verdict"] == "plausible"
    with pytest.raises(_common.CliError):
        plausibility(["--quantity", "mass=50 kDa", "--band", "protein_molar_mass=mass"])
