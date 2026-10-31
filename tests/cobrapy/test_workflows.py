"""Execute documented local workflows and check their scientific output contracts."""
from pathlib import Path
import re
import runpy

import pytest

pytest.importorskip("cobra")
matplotlib = pytest.importorskip("matplotlib")
pytest.importorskip("seaborn")
matplotlib.use("Agg")
import cobra
from cobra.io import load_model, read_sbml_model, write_sbml_model

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "cobrapy"


def blocks(path):
    return re.findall(r"```python\n(.*?)```", path.read_text(), flags=re.DOTALL)


def run_example(tmp_path, code):
    path = tmp_path / "example.py"
    path.write_text(code)
    return runpy.run_path(str(path), run_name="__main__")


@pytest.mark.parametrize("number", range(1, 6))
def test_workflow(tmp_path, monkeypatch, number):
    monkeypatch.chdir(tmp_path)
    snippets = blocks(SKILL_ROOT / "references" / "workflows.md")
    namespace = run_example(tmp_path, snippets[0] + "\n" + snippets[number])
    assert list((tmp_path / "cobrapy_output").glob("*.csv"))
    if number == 1:
        single = namespace["single_results"]
        doubles = namespace["double_results"]
        assert len(single) == 137
        assert all(isinstance(ids, set) for ids in doubles.ids)
        assert {len(ids) for ids in doubles.ids} == {1, 2}
        assert all(len(ids) == 2 for ids in namespace["synthetic_lethals"].ids)
        assert namespace["model"].slim_optimize() == pytest.approx(namespace["baseline"])
    elif number == 2:
        assert len(namespace["minimal_media"]) == 4
        for fraction, growth in namespace["rechecked_growth"].items():
            assert growth >= fraction * namespace["baseline"] - 1e-6
        assert namespace["custom_growth"] > 0
    elif number == 3:
        samples = namespace["samples"]
        assert samples.shape == (500, 95)
        assert samples.Biomass_Ecoli_core.min() >= 0.9 * namespace["baseline"] - 1e-6
        assert namespace["model"].reactions.Biomass_Ecoli_core.lower_bound == 0
    elif number == 4:
        assert len(namespace["knockout_results"]) == 137
        feasible = namespace["feasible"]
        assert (feasible.max_growth >= namespace["growth_floor"] - 1e-6).all()
        assert (feasible.product_min <= feasible.product_max + 1e-6).all()
        assert (feasible.product_max <= namespace["wt_range"].maximum + 1e-6).all()
        assert namespace["envelope"].flux_maximum.notna().any()
    else:
        report = namespace["report"]
        assert report["status"] == "optimal"
        assert report["objective_value"] == pytest.approx(0.87392150696843)
        assert report["missing_chemistry"] == 0
        assert report["unbalanced_internal"] == 0
        assert report["blocked_in_current_medium"] >= 0


def test_main_examples(tmp_path):
    cobra.Configuration().solver = "glpk"
    cobra.Configuration().processes = 1
    ns = run_example(tmp_path, "\n".join(blocks(SKILL_ROOT / "SKILL.md")))
    assert ns["baseline"] == pytest.approx(0.87392150696843)
    assert ns["parsimonious"].fluxes.Biomass_Ecoli_core == pytest.approx(ns["baseline"])
    assert ns["parsimonious"].objective_value > ns["baseline"]
    assert {"flux_minimum", "flux_maximum"} <= set(ns["envelope"].columns)


def test_quick_reference_local_examples(tmp_path):
    cobra.Configuration().solver = "glpk"
    cobra.Configuration().processes = 1
    snippets = blocks(SKILL_ROOT / "references" / "api_quick_reference.md")
    # The second block is the separately live-tested public download example.
    ns = run_example(tmp_path, "\n".join(s for i, s in enumerate(snippets) if i != 1))
    assert ns["min_medium"] is not None
    assert (ns["validation"] == "v").all()


def test_infeasibility_is_not_zero_growth():
    model = load_model("textbook")
    with model:
        model.medium = {}
        assert model.optimize().status == "infeasible"
        with pytest.raises(cobra.exceptions.OptimizationError):
            model.slim_optimize(error_value=None)
    assert model.slim_optimize(error_value=None) > 0


def test_sbml_round_trip_preserves_objective_bounds_and_growth(tmp_path):
    model = load_model("textbook")
    model.reactions.EX_glc__D_e.lower_bound = -5
    expected = model.slim_optimize(error_value=None)
    path = tmp_path / "model.xml"
    write_sbml_model(model, path)
    loaded = read_sbml_model(path)
    assert {r.id: r.bounds for r in loaded.reactions} == {r.id: r.bounds for r in model.reactions}
    assert str(loaded.objective.expression) == str(model.objective.expression)
    assert loaded.slim_optimize(error_value=None) == pytest.approx(expected)
