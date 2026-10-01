"""Scientific regression tests, using analytical cases and a published EMU result."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
import skill_contract

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
pytest.importorskip("mfapy")

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "13c-metabolic-flux"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.dont_write_bytecode = True
from _mfa_model import InputError, Network, Observations, read_json
from _mfa_fit import FluxSpace, diagnostics, fit, profile

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def asset(name):
    return read_json(SKILL_ROOT / "assets" / name)


def branch(data="branch-identifiable.json"):
    network = Network(asset("branch-model.json"))
    return network, Observations(asset(data), network)


def test_published_emu_reference_and_positional_bit_order():
    network = Network(asset("tca-model.json"))
    data = asset("tca-tracer.json")
    vector = network.check_flux(asset("tca-fluxes.json"))
    result = network.predict(vector, data["experiments"][0])["GluWhole"]
    # Independently published values, NOT generated as the expected result by this engine.
    np.testing.assert_allclose(result, [.3464, .2695, .2708, .0807, .0286, .0039], atol=5e-5)
    data["experiments"][0]["substrates"]["AcCoA"] = {"00": .5, "10": .25, "11": .25}
    changed = network.predict(vector, data["experiments"][0])["GluWhole"]
    assert abs(changed[0] - result[0]) > .03


def test_analytical_split_recovery_and_profile_cutoff():
    network, obs = branch()
    fitted = fit(obs, starts=4)
    result = diagnostics(obs, fitted)
    assert result["fluxes"]["straight"] == pytest.approx(70., abs=2e-5)
    assert result["fluxes"]["swap"] == pytest.approx(30., abs=2e-5)
    assert result["local_sensitivity_rank"] == 1
    assert result["max_mass_balance_error"] < 1e-9
    p = profile(obs, fitted, "straight", points=41, starts=2)
    assert p["status"] == "threshold_crossings_bracketed"
    # y = 0.8*v/100, SEM = 0.01: exact Gaussian 95% interval.
    expected = [70 - 1.9599639845 * .01 / .008, 70 + 1.9599639845 * .01 / .008]
    assert all(any(a <= value <= b for a, b in p["threshold_crossing_brackets"]) for value in expected)
    for point in p["points"]:
        assert point["rss"] == pytest.approx(((point["flux"] - 70) * .8) ** 2, abs=1e-7)


def test_whole_molecule_data_cannot_resolve_positional_routes():
    _, obs = branch("branch-unresolved.json")
    fitted = fit(obs, starts=3)
    result = diagnostics(obs, fitted)
    assert result["rss"] < 1e-15
    assert result["local_sensitivity_rank"] == 0
    assert result["goodness_of_fit"]["approximate_p_value"] is None
    assert result["weak_flux_directions"]
    p = profile(obs, fitted, "straight", points=7, starts=2)
    assert p["status"] == "unresolved_within_bounds"
    assert p["lower_bound_accepted"] and p["upper_bound_accepted"]


def test_realistic_tca_exchange_is_not_recovered_from_an_uninformative_fragment():
    network = Network(asset("tca-model.json"))
    obs = Observations(asset("tca-reference-mdv.json"), network)
    fitted = fit(obs, starts=4)
    result = diagnostics(obs, fitted)
    assert result["fluxes"]["v3"] == pytest.approx(50, abs=.03)
    assert result["free_flux_dimensions"] == 2
    assert result["local_sensitivity_rank"] == 1
    # A different exchange flux has the same labeled-carbon prediction.
    flux1 = asset("tca-fluxes.json")
    flux2 = {**flux1, "v6": 250, "v7": 200}
    for exp in obs.spec["experiments"]:
        np.testing.assert_allclose(network.predict(network.check_flux(flux1), exp)["GluWhole"],
                                   network.predict(network.check_flux(flux2), exp)["GluWhole"], atol=1e-10)
    p = profile(obs, fitted, "v7", points=7, starts=3)
    assert p["status"] in {"bound_limited", "unresolved_within_bounds"}
    # The upper feasible bound may force branch flux v3 away from its optimum.
    assert p["lower_bound_accepted"] is True


def test_correlated_mdv_likelihood_invariant_to_omitted_bin():
    n, _ = branch()
    spec = asset("branch-unresolved.json")
    spec["experiments"][0]["measurements"][0]["mdv"] = [.21, .78, .01]
    scores = []
    for omit in range(3):
        spec["experiments"][0]["measurements"][0]["omit"] = omit
        residual = Observations(copy.deepcopy(spec), n).residuals(n.check_flux(asset("branch-fluxes.json")))
        scores.append(float(residual @ residual))
    np.testing.assert_allclose(scores, [2., 2., 2.], atol=1e-10)


def test_heteroscedastic_covariance_preserves_omitted_bin_invariance():
    n, _ = branch()
    data = asset("branch-unresolved.json")
    measurement = data["experiments"][0]["measurements"][0]
    measurement["mdv"] = [.1999995, .7999995, .000001]
    measurement["covariance"] = [[1e-4 + 1e-12, -1e-4, -1e-12],
                                 [-1e-4, 1e-4 + 1e-12, -1e-12],
                                 [-1e-12, -1e-12, 2e-12]]
    scores = []
    for omit in range(3):
        measurement["omit"] = omit
        residual = Observations(copy.deepcopy(data), n).residuals(n.check_flux(asset("branch-fluxes.json")))
        scores.append(float(residual @ residual))
    np.testing.assert_allclose(scores, [.5, .5, .5], rtol=1e-7)


@pytest.mark.parametrize("omit", [0, 1, 2])
def test_rare_bin_covariance_error_is_rejected(omit):
    n, _ = branch()
    data = asset("branch-unresolved.json")
    measurement = data["experiments"][0]["measurements"][0]
    measurement["omit"] = omit
    measurement["covariance"] = [[1e-4, -1e-4 + 1e-12, -1e-12],
                                 [-1e-4 + 1e-12, 1e-4, -1e-12],
                                 [-1e-12, -1e-12, 1e-12]]
    with pytest.raises(InputError, match="zero row/column sums"):
        Observations(data, n)


def test_mdv_rounding_cannot_dominate_measurement_error():
    n, _ = branch()
    data = asset("branch-identifiable.json")
    measurement = data["experiments"][0]["measurements"][0]
    measurement["mdv"][0] += 1e-8
    with pytest.raises(InputError, match="normalization error"):
        Observations(data, n)


def test_parallel_tracers_share_fluxes_and_measured_flux_can_anchor_scale():
    spec = asset("branch-model.json")
    del spec["reactions"][0]["fixed"]
    network = Network(spec)
    data = asset("branch-identifiable.json")
    first = data["experiments"][0]
    first["flux_measurements"] = [{"reaction": "uptake", "value": 100., "sem": .2}]
    second = copy.deepcopy(first)
    second["id"] = "C2label"
    second["substrates"]["S"] = {"01": .8, "00": .2}
    second["measurements"][0]["mdv"] = [.76, .24]
    second.pop("flux_measurements")
    data["experiments"].append(second)
    obs = Observations(data, network)
    result = diagnostics(obs, fit(obs, starts=5))
    assert result["fluxes"]["straight"] == pytest.approx(70., abs=.01)
    assert result["fluxes"]["uptake"] == pytest.approx(100., abs=.01)
    assert result["local_sensitivity_rank"] == 2
    assert result["goodness_of_fit"]["approximate_p_value"] > .99


def test_condensation_of_repeated_substrate_matches_binomial():
    spec = dict(schema_version=1, name="Condensation", flux_unit="relative", provenance="Analytical binomial test",
                metabolites=[dict(id="S", carbons=1, boundary="source"),
                             dict(id="A", carbons=2, boundary="internal"),
                             dict(id="Out", carbons=2, boundary="sink")],
                reactions=[dict(id="join", substrates=[["S", "A"], ["S", "B"]], products=[["A", "AB"]],
                                lower=.001, upper=200., fixed=100.),
                           dict(id="export", substrates=[["A", "AB"]], products=[["Out", "AB"]], lower=.001, upper=200.)],
                fragments=[dict(id="Awhole", metabolite="A", carbons=[1, 2], provenance="All carbons")])
    n = Network(spec)
    p = n.predict(n.check_flux(dict(join=100., export=100.)), dict(substrates={"S": {"0": .75, "1": .25}}))
    np.testing.assert_allclose(p["Awhole"], [.5625, .375, .0625], atol=1e-12)


def test_symmetric_pool_averages_reversed_positions():
    spec = asset("branch-model.json")
    spec["metabolites"][2]["symmetric"] = True
    n = Network(spec)
    p = n.predict(n.check_flux(asset("branch-fluxes.json")), asset("branch-identifiable.json")["experiments"][0])
    np.testing.assert_allclose(p["Bfirst"], [.6, .4], atol=1e-12)


def test_unlabeled_and_fully_labeled_limits():
    n, _ = branch()
    for bits, expected in [("00", [1., 0., 0.]), ("11", [0., 0., 1.])]:
        p = n.predict(n.check_flux(asset("branch-fluxes.json")), dict(substrates={"S": {bits: 1.}}))
        np.testing.assert_allclose(p["Bwhole"], expected, atol=1e-12)


def test_forward_prediction_is_invariant_to_uniform_flux_units():
    n = Network(asset("tca-model.json"))
    exp = asset("tca-tracer.json")["experiments"][0]
    v = n.check_flux(asset("tca-fluxes.json"))
    expected = n.predict(v, exp)["GluWhole"]
    for factor in [1e-10, 1e-5, 1e5]:
        np.testing.assert_allclose(n.predict(v * factor, exp)["GluWhole"], expected, atol=1e-10)


def test_small_turnover_profile_endpoint_does_not_drop_emu_rows():
    n = Network(asset("tca-model.json"))
    space = FluxSpace(n, {"v7": 299.999})
    assert space.dimension == 0
    p = n.predict(space.base, asset("tca-tracer.json")["experiments"][0])["GluWhole"]
    assert p.sum() == pytest.approx(1, abs=1e-10)


@pytest.mark.parametrize("mutation,match", [
    (lambda s: s["reactions"][1]["products"][0].__setitem__(1, "AC"), "lost or created"),
    (lambda s: s["reactions"][1]["products"][0].__setitem__(1, "AA"), "Duplicate carbon"),
    (lambda s: s["reactions"][1].__setitem__("id", "bad_name"), "Invalid identifier"),
    (lambda s: s["reactions"][1].__setitem__("lower", -1), "lower"),
    (lambda s: s["fragments"][0].__setitem__("carbons", [0]), "1-based"),
    (lambda s: s["fragments"][0].__setitem__("carbons", [1, 1]), "Duplicate positions"),
    (lambda s: s["metabolites"][0].__setitem__("carbons", 0), "carbon count"),
    (lambda s: s["reactions"][0].__setitem__("upper", float("nan")), "finite"),
])
def test_invalid_networks_rejected(mutation, match):
    spec = asset("branch-model.json")
    mutation(spec)
    with pytest.raises(InputError, match=match):
        Network(spec)


@pytest.mark.parametrize("mutation,match", [
    (lambda s: s["steady_state"].__setitem__("isotopic", False), "steady state"),
    (lambda s: s.__setitem__("mdv_basis", "raw"), "natural abundance"),
    (lambda s: s.__setitem__("shared_fluxes", False), "same flux state"),
    (lambda s: s["experiments"][0].__setitem__("substrates", {}), "every source"),
    (lambda s: s["experiments"][0]["substrates"]["S"].__setitem__("00", .1), "sum to one"),
    (lambda s: s["experiments"][0]["measurements"][0].__setitem__("mdv", [.2, .3]), "sum to one"),
    (lambda s: s["experiments"][0]["measurements"][0].__setitem__("mdv", [-.1, 1.1]), "nonnegative"),
    (lambda s: s["experiments"][0]["measurements"][0].__setitem__("covariance", [[1., 0.], [0., 1.]]), "zero row"),
    (lambda s: s["experiments"][0]["measurements"][0].__setitem__("covariance", [[0., 0.], [0., 0.]]), "positive definite"),
    (lambda s: s["experiments"][0]["measurements"].append(copy.deepcopy(s["experiments"][0]["measurements"][0])), "Duplicate fragment"),
])
def test_invalid_observations_rejected(mutation, match):
    network, _ = branch()
    data = asset("branch-identifiable.json")
    mutation(data)
    with pytest.raises(InputError, match=match):
        Observations(data, network)


def test_sem_approximation_disclosed():
    n, _ = branch()
    data = asset("branch-identifiable.json")
    m = data["experiments"][0]["measurements"][0]
    m.pop("covariance")
    m["sem"] = [.01, .01]
    assert "approximate" in Observations(data, n).warnings[0]


def test_infeasible_fixed_fluxes_and_unbalanced_simulation():
    spec = asset("branch-model.json")
    spec["reactions"][-1]["fixed"] = 99.
    with pytest.raises(InputError, match="infeasible"):
        FluxSpace(Network(spec))
    network, _ = branch()
    with pytest.raises(InputError, match="mass balance"):
        network.check_flux({**asset("branch-fluxes.json"), "export": 99.})


def test_loose_bound_on_fixed_reaction_does_not_fix_free_fluxes():
    spec = asset("branch-model.json")
    spec["reactions"][0]["upper"] = 1e12
    network = Network(spec)
    obs = Observations(asset("branch-identifiable.json"), network)
    fitted = fit(obs, starts=3)
    assert fitted["space"].dimension == 1
    assert fitted["vector"][network.ids.index("straight")] == pytest.approx(70, abs=1e-4)
    assert profile(obs, fitted, "straight", points=7, starts=2)["status"] != "fixed_by_constraints"


@pytest.mark.parametrize("factor", [1e-10, 1e-8, 1e5])
def test_fitting_profiles_and_infeasibility_are_invariant_to_flux_units(factor):
    spec = asset("branch-model.json")
    for reaction in spec["reactions"]:
        for key in ("lower", "upper", "fixed"):
            if key in reaction:
                reaction[key] *= factor
    network = Network(spec)
    obs = Observations(asset("branch-identifiable.json"), network)
    fitted = fit(obs, starts=3)
    result = diagnostics(obs, fitted)
    assert result["free_flux_dimensions"] == result["local_sensitivity_rank"] == 1
    assert result["fluxes"]["straight"] / factor == pytest.approx(70, abs=1e-4)
    assert profile(obs, fitted, "straight", points=7, starts=2)["status"] == "threshold_crossings_bracketed"
    spec["reactions"][-1]["fixed"] = 99 * factor
    with pytest.raises(InputError, match="infeasible"):
        FluxSpace(Network(spec))


def test_all_fixed_model_and_fixed_profile():
    spec = asset("branch-model.json")
    spec["reactions"][1]["fixed"] = 70.
    network = Network(spec)
    obs = Observations(asset("branch-identifiable.json"), network)
    fitted = fit(obs)
    assert fitted["rss"] < 1e-20
    assert profile(obs, fitted, "straight")["status"] == "fixed_by_constraints"


def test_duplicate_json_keys_are_rejected(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"S": 1, "S": 2}')
    with pytest.raises(InputError, match="Duplicate JSON"):
        read_json(path)


def test_cli_end_to_end_and_input_protection(tmp_path):
    command = [sys.executable, str(SKILL_ROOT / "scripts" / "mfa.py"), "fit",
               "--model", str(SKILL_ROOT / "assets" / "branch-model.json"),
               "--data", str(SKILL_ROOT / "assets" / "branch-identifiable.json"), "--starts", "3"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["fluxes"]["straight"] == pytest.approx(70., abs=.001)
    assert len(payload["input_sha256"]) == 2
    data = tmp_path / "data.json"
    data.write_text(json.dumps(asset("branch-identifiable.json")))
    original = data.read_bytes()
    bad = subprocess.run(command + ["--data", str(data), "--output", str(data)], capture_output=True, text=True)
    assert bad.returncode == 2 and data.read_bytes() == original


def test_optimizer_failure_not_reported_as_a_fit():
    _, obs = branch()
    with pytest.raises(InputError, match="No converged feasible fit"):
        fit(obs, starts=1, maxiter=1)
