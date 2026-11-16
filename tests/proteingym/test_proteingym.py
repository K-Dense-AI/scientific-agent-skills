from __future__ import annotations

import csv
import importlib.util
import json
import math
from pathlib import Path
import sys

import pytest
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "proteingym"
SCRIPT_PATH = SKILL_ROOT / "scripts" / "evaluate_dms.py"

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def _load_evaluator():
    spec = importlib.util.spec_from_file_location("proteingym_evaluate_dms", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_and_validate_mutants_and_demo():
    mod = _load_evaluator()
    assert mod.run_demo() == 0
    assert mod.parse_mutant("WT") == []
    assert mod.parse_mutant("D2N:A1P") == [("A", 1, "P"), ("D", 2, "N")]
    mod.validate_mutant_against_wt([("A", 1, "P"), ("D", 2, "N")], "ADKLMNP")

    with pytest.raises(ValueError, match="WT mismatch"):
        mod.validate_mutant_against_wt([("G", 1, "P")], "ADKLMNP")
    with pytest.raises(ValueError, match="Duplicate mutated position"):
        mod.parse_mutant("A1P:A1G")


def test_five_proteingym_metrics_exact_and_ties():
    mod = _load_evaluator()
    y_true = [2.5, 1.8, 1.2, 0.5, 0.1, -0.3, -0.8, -1.2, -1.9, -2.4]
    y_pred_perfect = [10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0]
    y_bin = [1, 1, 1, 1, 0, 0, 0, 0, 0, 0]

    assert math.isclose(mod.spearman_rho(y_true, y_pred_perfect), 1.0, abs_tol=1e-9)
    assert math.isclose(mod.spearman_rho(y_true, list(reversed(y_pred_perfect))), -1.0, abs_tol=1e-9)
    assert math.isclose(mod.roc_auc_binary(y_bin, y_pred_perfect), 1.0, abs_tol=1e-9)
    assert math.isclose(mod.mcc_at_prevalence(y_bin, y_pred_perfect), 1.0, abs_tol=1e-9)
    assert math.isclose(mod.ndcg_at_quantile(y_true, y_pred_perfect, quantile=0.20), 1.0, abs_tol=1e-9)
    assert math.isclose(mod.top_k_recall(y_true, y_pred_perfect, quantile=0.20), 1.0, abs_tol=1e-9)
    assert mod.midranks([1.0, 2.0, 2.0, 4.0]) == [1.0, 2.5, 2.5, 4.0]


def test_pairwise_epistasis_and_reciprocal_sign_detection():
    mod = _load_evaluator()
    records = [
        {"mutant": "A1G", "mutations": [("A", 1, "G")], "dms_score": 0.4, "pred_score": 0.35},
        {"mutant": "Y2F", "mutations": [("Y", 2, "F")], "dms_score": 0.5, "pred_score": 0.45},
        {"mutant": "A1G:Y2F", "mutations": [("A", 1, "G"), ("Y", 2, "F")], "dms_score": 1.3, "pred_score": 1.25},
        {"mutant": "K5R", "mutations": [("K", 5, "R")], "dms_score": -0.6, "pred_score": -0.5},
        {"mutant": "D8E", "mutations": [("D", 8, "E")], "dms_score": -0.5, "pred_score": -0.4},
        {"mutant": "K5R:D8E", "mutations": [("K", 5, "R"), ("D", 8, "E")], "dms_score": 0.4, "pred_score": 0.3},
    ]
    report = mod.compute_pairwise_epistasis(records, wt_score=0.0, wt_pred=0.0, noise_tol=0.05)
    assert report["n_complete_cycles"] == 2
    assert report["regime_counts"]["positive_magnitude"] == 1
    assert report["regime_counts"]["reciprocal_sign"] == 1
    assert math.isclose(report["epistasis_spearman_rho"], 1.0, abs_tol=1e-9)


def test_position_disjoint_splits_and_end_to_end_cli(tmp_path: Path):
    mod = _load_evaluator()
    csv_path = tmp_path / "dms.csv"
    dist_path = tmp_path / "dist.csv"
    split_path = tmp_path / "splits.csv"
    json_path = tmp_path / "report.json"

    rows = [
        {"mutant": "WT", "DMS_score": "0.0", "DMS_score_bin": "1", "ddg": "0.0"},
        {"mutant": "M1A", "DMS_score": "0.8", "DMS_score_bin": "1", "ddg": "-1.5"},
        {"mutant": "M1V", "DMS_score": "0.6", "DMS_score_bin": "1", "ddg": "-1.1"},
        {"mutant": "K2R", "DMS_score": "0.3", "DMS_score_bin": "1", "ddg": "-0.4"},
        {"mutant": "T3P", "DMS_score": "-0.9", "DMS_score_bin": "0", "ddg": "2.2"},
        {"mutant": "A4D", "DMS_score": "-1.4", "DMS_score_bin": "0", "ddg": "3.1"},
        {"mutant": "M1A:K2R", "DMS_score": "1.5", "DMS_score_bin": "1", "ddg": "-2.6"},
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["mutant", "DMS_score", "DMS_score_bin", "ddg"])
        writer.writeheader()
        writer.writerows(rows)

    with dist_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["position", "distance_angstrom"])
        writer.writeheader()
        writer.writerows(
            [
                {"position": "1", "distance_angstrom": "3.8"},
                {"position": "2", "distance_angstrom": "4.2"},
                {"position": "3", "distance_angstrom": "7.5"},
                {"position": "4", "distance_angstrom": "14.0"},
            ]
        )

    rc = mod.main(
        [
            "--input",
            str(csv_path),
            "--pred-col",
            "ddg",
            "--negate-pred",
            "--wt-seq",
            "MKTA",
            "--epistasis",
            "--residue-distances",
            str(dist_path),
            "--split-scheme",
            "modulo",
            "--n-folds",
            "2",
            "--split-out",
            str(split_path),
            "--json-out",
            str(json_path),
        ]
    )
    assert rc == 0
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert math.isclose(report["overall"]["spearman_rho"], 1.0, abs_tol=1e-9)
    assert "first_shell_lt_5A" in report["by_active_site_shell"]
    assert report["epistasis"]["n_complete_cycles"] == 1

    with split_path.open("r", encoding="utf-8", newline="") as f:
        split_rows = list(csv.DictReader(f))
    m1_folds = {r["cv_fold"] for r in split_rows if r["mutant"] in ("M1A", "M1V")}
    assert len(m1_folds) == 1
    cross_fold = next(r["cv_fold"] for r in split_rows if r["mutant"] == "M1A:K2R")
    assert cross_fold == "-1"
