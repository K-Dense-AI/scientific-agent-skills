"""Numerical invariants and input-boundary checks for marine carbonate chemistry."""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "marine-carbonate-chemistry"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import solve_carbonate as solver

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)
pyco2 = pytest.importorskip("PyCO2SYS")
np = pytest.importorskip("numpy")

BASE = {"sample_id": "reference", "par1": 2300, "par2": 2000, "salinity": 35,
        "temperature": 25, "pressure": 0, "total_phosphate": 0, "total_silicate": 0}


def write_csv(tmp_path, rows):
    path = tmp_path / "samples.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def run(tmp_path, rows=None, **options):
    path = write_csv(tmp_path, rows or [BASE])
    output = tmp_path / "output"
    settings = dict(par1_type="alkalinity", par2_type="dic", k_carbonic=10)
    settings.update(options)
    manifest = solver.solve(path, output, **settings)
    with (output / "carbonate.csv").open() as handle:
        result = list(csv.DictReader(handle))
    return manifest, result


def direct(**kwargs):
    settings = dict(par1=2300, par2=2000, par1_type=1, par2_type=2, salinity=35,
                    temperature=25, pressure=0, total_phosphate=0, total_silicate=0,
                    opt_k_carbonic=10, opt_total_borate=1, opt_pH_scale=1, **solver.SETTINGS)
    settings.update(kwargs)
    return pyco2.sys(**settings)


def test_pinned_regression_and_carbon_species_balance(tmp_path):
    _, rows = run(tmp_path)
    row = rows[0]
    # Fixed regression values from PyCO2SYS 1.8.3.4, not independent reference chemistry.
    assert float(row["pH_total"]) == pytest.approx(8.045886180900592, abs=1e-9)
    assert float(row["pCO2"]) == pytest.approx(396.9581630249643, rel=1e-9)
    assert float(row["saturation_aragonite"]) == pytest.approx(3.3862008130878753, rel=1e-9)
    assert sum(float(row[key]) for key in ("aqueous_CO2", "bicarbonate", "carbonate")) == pytest.approx(2000)
    assert "pH_total_out" not in row
    assert row["qc_flags"] == ""


PAIRS = [pair for pair in itertools.combinations(solver.TYPES, 2)
         if set(pair) != {"pco2", "fco2"}]


@pytest.mark.parametrize("pair", PAIRS)
def test_every_supported_independent_pair_recovers_same_system(tmp_path, pair):
    reference = direct(total_phosphate=2, total_silicate=15)
    keys = {"alkalinity": "alkalinity", "dic": "dic", "ph": "pH_total", "pco2": "pCO2", "fco2": "fCO2"}
    row = {**BASE, "par1": float(reference[keys[pair[0]]]), "par2": float(reference[keys[pair[1]]]),
           "total_phosphate": 2, "total_silicate": 15}
    _, results = run(tmp_path, [row], par1_type=pair[0], par2_type=pair[1], ph_scale="total")
    assert float(results[0]["alkalinity"]) == pytest.approx(2300, rel=1e-8)
    assert float(results[0]["dic"]) == pytest.approx(2000, rel=1e-8)
    assert float(results[0]["pH_total"]) == pytest.approx(float(reference["pH_total"]), abs=1e-8)


@pytest.mark.parametrize("scale,key", [("total", "pH_total"), ("seawater", "pH_sws"),
                                      ("free", "pH_free"), ("nbs", "pH_nbs")])
def test_declared_ph_scales_yield_same_dic(tmp_path, scale, key):
    reference = direct()
    _, rows = run(tmp_path, [{**BASE, "par2": float(reference[key])}], par2_type="ph", ph_scale=scale)
    assert float(rows[0]["dic"]) == pytest.approx(2000, rel=1e-8)
    assert float(rows[0]["pH_total"]) == pytest.approx(float(reference["pH_total"]), abs=1e-8)


def test_output_conditions_match_independent_closed_system_solution(tmp_path):
    _, rows = run(tmp_path, [{**BASE, "temperature_out": 10, "pressure_out": 1000}])
    reference = direct(temperature=10, pressure=1000)
    for key in ("pH_total", "pCO2", "saturation_aragonite", "revelle_factor"):
        assert float(rows[0][key + "_out"]) == pytest.approx(float(reference[key]), rel=1e-9)
    assert sum(float(rows[0][key + "_out"]) for key in ("aqueous_CO2", "bicarbonate", "carbonate")) == pytest.approx(2000)


def test_added_dic_lowers_ph_and_saturation_at_fixed_alkalinity(tmp_path):
    _, rows = run(tmp_path, [BASE, {**BASE, "sample_id": "added", "par2": 2100}])
    first, second = rows
    assert float(second["pH_total"]) < float(first["pH_total"])
    assert float(second["saturation_aragonite"]) < float(first["saturation_aragonite"])
    assert float(second["pCO2"]) > float(first["pCO2"])
    assert float(second["dic"]) == pytest.approx(2100)


def test_input_uncertainties_agree_with_central_difference_quadrature(tmp_path):
    row = {**BASE, "u_par1": 2, "u_par2": 2, "temperature_out": 10, "pressure_out": 1000}
    manifest, rows = run(tmp_path, [row])
    for suffix in ("", "_out"):
        for key in solver.UNCERTAINTY_RESULTS:
            terms = []
            for parameter, center in (("par1", 2300), ("par2", 2000)):
                plus = direct(**{parameter: center + 0.01}, temperature_out=10, pressure_out=1000)
                minus = direct(**{parameter: center - 0.01}, temperature_out=10, pressure_out=1000)
                derivative = float(plus[key + suffix] - minus[key + suffix]) / 0.02
                terms.append((derivative * 2) ** 2)
            assert float(rows[0]["u_" + key + suffix]) == pytest.approx(sum(terms) ** 0.5, rel=0.002)
    assert manifest["uncertainty_sources"] == ["par1", "par2"]


def test_nonzero_nutrients_are_used(tmp_path):
    _, rows = run(tmp_path, [BASE, {**BASE, "sample_id": "nutrients", "total_phosphate": 3,
                                  "total_silicate": 50}])
    assert float(rows[1]["pH_total"]) < float(rows[0]["pH_total"])


def test_nutrient_and_borate_settings_change_the_solution(tmp_path):
    row = {**BASE, "total_phosphate": 3, "total_silicate": 50, "total_ammonia": 2, "total_sulfide": 1}
    manifest, rows = run(tmp_path, [row], k_carbonic=15, total_borate=2)
    expected = direct(total_phosphate=3, total_silicate=50, total_ammonia=2, total_sulfide=1,
                      opt_k_carbonic=15, opt_total_borate=2)
    assert float(rows[0]["pH_total"]) == pytest.approx(float(expected["pH_total"]))
    assert float(rows[0]["pH_total"]) != pytest.approx(float(direct()["pH_total"]))
    assert manifest["assumptions"] == []
    assert manifest["settings"]["opt_total_borate"] == 2


def test_range_flags_cover_input_and_output_conditions(tmp_path):
    manifest, rows = run(tmp_path, [{**BASE, "salinity": 15, "temperature_out": 1, "pressure_out": 1000}])
    assert rows[0]["qc_flags"] == "outside_k_carbonic_input_range;outside_k_carbonic_output_range"
    assert manifest["warnings"][0]["sample_id"] == "reference"


def test_only_output_range_is_flagged(tmp_path):
    _, rows = run(tmp_path, [{**BASE, "temperature_out": 1, "pressure_out": 1000}])
    assert rows[0]["qc_flags"] == "outside_k_carbonic_output_range"


@pytest.mark.parametrize("change,match", [
    ({"par1": "NaN"}, "finite"), ({"par2": "inf"}, "finite"),
    ({"par1": ""}, "numeric"), ({"salinity": -1}, "nonnegative"),
    ({"pressure": -1}, "nonnegative"), ({"total_phosphate": -1}, "nonnegative"),
    ({"temperature": -274}, "absolute zero"), ({"u_par1": -1}, "nonnegative"),
    ({"par2": 0}, "positive"), ({"temperature_out": 10}, "both"),
    ({"u_pressure_out": 1}, "corresponding"), ({"phosphate": 1}, "Unknown"),
])
def test_bad_inputs_fail_before_creating_outputs(tmp_path, change, match):
    with pytest.raises(ValueError, match=match):
        run(tmp_path, [{**BASE, **change}])
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("options,match", [
    ({"par2_type": "alkalinity"}, "independent"),
    ({"par1_type": "pco2", "par2_type": "fco2"}, "independent"),
    ({"par2_type": "ph"}, "explicit"), ({"k_carbonic": 8}, "Unsupported"),
])
def test_ambiguous_or_unsupported_configuration_fails(tmp_path, options, match):
    with pytest.raises(ValueError, match=match):
        run(tmp_path, **options)


@pytest.mark.parametrize("identifier", ["reference", " reference ", ""])
def test_sample_identity_is_preserved(tmp_path, identifier):
    with pytest.raises(ValueError, match="sample_id"):
        run(tmp_path, [BASE, {**BASE, "sample_id": identifier}])


@pytest.mark.parametrize("kind", ["duplicate", "short", "long", "empty", "missing"])
def test_malformed_csv(tmp_path, kind):
    path = write_csv(tmp_path, [BASE])
    lines = path.read_text().splitlines()
    if kind == "duplicate":
        lines[0] += ",par1"
        lines[1] += ",2300"
    elif kind == "short":
        lines[1] = lines[1].rsplit(",", 1)[0]
    elif kind == "long":
        lines[1] += ",1"
    elif kind == "empty":
        lines = lines[:1]
    else:
        lines[0] = lines[0].replace("salinity", "salinitty")
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError):
        solver.read_samples(path)


def test_provenance_hash_and_no_clobber(tmp_path):
    manifest, _ = run(tmp_path)
    assert manifest == json.loads((tmp_path / "output/provenance.json").read_text())
    assert manifest["input_sha256"] == hashlib.sha256((tmp_path / "samples.csv").read_bytes()).hexdigest()
    assert manifest["software"]["PyCO2SYS"] == "1.8.3.4"
    original = (tmp_path / "output/carbonate.csv").read_bytes()
    with pytest.raises(FileExistsError):
        run(tmp_path)
    assert (tmp_path / "output/carbonate.csv").read_bytes() == original


@pytest.mark.parametrize("mode,match", [("nan", "Non-finite"), ("balance", "mass balance")])
def test_invalid_solver_output_is_not_published(tmp_path, monkeypatch, mode, match):
    real_sys = pyco2.sys

    def broken_sys(**kwargs):
        result = real_sys(**kwargs)
        if mode == "nan":
            result["pH_total"] = np.nan
        else:
            result["carbonate"] = result["carbonate"] + 50
        return result

    monkeypatch.setattr(pyco2, "sys", broken_sys)
    with pytest.raises(ValueError, match=match):
        run(tmp_path)
    assert not (tmp_path / "output").exists()


def test_different_library_version_requires_revalidation(tmp_path, monkeypatch):
    monkeypatch.setattr(pyco2, "__version__", "2.0.0")
    with pytest.raises(ValueError, match="pinned environment"):
        run(tmp_path)
    assert not (tmp_path / "output").exists()


def test_documented_csv_and_cli(tmp_path):
    text = (SKILL_ROOT / "SKILL.md").read_text()
    example = re.search(r"```csv\n(.*?)\n```", text, re.S).group(1)
    path = tmp_path / "samples.csv"
    path.write_text(example + "\n")
    result = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts/solve_carbonate.py"), str(path),
         "--par1-type", "alkalinity", "--par2-type", "dic", "--k-carbonic", "10",
         "--output-dir", str(tmp_path / "cli-results")],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "Solved 2 samples; 0 with range flags" in result.stdout
    with (tmp_path / "cli-results/carbonate.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert float(rows[0]["pH_total_out"]) == pytest.approx(8.241241, abs=5e-7)
    assert float(rows[0]["u_pH_total"]) == pytest.approx(0.004580, abs=5e-7)
