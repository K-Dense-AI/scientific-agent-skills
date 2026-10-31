"""Scientific regressions found while checking Q2(R2) and M10 primary sources."""
from __future__ import annotations

import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "analytical-method-validation"
SCRIPTS = SKILL_ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))
import _common as common
from _catalog import M10_CRITERIA
from check_bioanalytical_run import check_run


def cli(script, *args, data=None):
    return subprocess.run([sys.executable, str(SCRIPTS / f"{script}.py"), *args],
                          input=data, capture_output=True, text=True, check=False)


class TestScientificRefresh(unittest.TestCase):
    def run_rows(self, rows, modality="chromatographic"):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            path.write_text(json.dumps(rows))
            return check_run(str(path), M10_CRITERIA[modality])

    @staticmethod
    def complete_run():
        rows = [{"type": "calibrator", "nominal": x, "measured": x,
                 "label": "LLOQ" if x == 1 else "ULOQ" if x == 6 else ""}
                for x in range(1, 7)]
        rows += [{"type": "qc", "nominal": x, "measured": x, "label": label}
                 for x, label in [(1.5, "low"), (3, "medium"), (5, "high")] for _ in range(2)]
        return rows

    def test_complete_run_passes_supported_checks(self):
        self.assertEqual(self.run_rows(self.complete_run())[1], [])

    def test_failed_sixth_calibrator_does_not_count_as_passing_level(self):
        rows = self.complete_run()
        rows[3]["measured"] = 10
        _, findings = self.run_rows(rows)
        self.assertTrue(any("5 passing concentration" in f for f in findings))
        self.assertTrue(any("refitted" in f for f in findings))

    def test_qc_relabelling_cannot_create_levels(self):
        rows = self.complete_run()
        for row in rows[6:]:
            row["nominal"] = row["measured"] = 3
        self.assertTrue(any("1 QC levels" in f for f in self.run_rows(rows)[1]))

    def test_missing_calibrators_or_qcs_is_incomplete(self):
        for rows in [self.complete_run()[:6], self.complete_run()[6:]]:
            self.assertTrue(any("incomplete" in f for f in self.run_rows(rows)[1]))

    def test_one_qc_at_each_level_is_not_duplicate_qcs(self):
        rows = self.complete_run()[:6] + self.complete_run()[6::2]
        self.assertTrue(any("two QC samples" in f for f in self.run_rows(rows)[1]))

    def test_anchor_exclusion_does_not_apply_to_chromatography(self):
        rows = self.complete_run() + [{"type":"calibrator", "label":"ANCHOR", "nominal":10, "measured":1}]
        with self.assertRaisesRegex(common.InputError, "LBA only"):
            self.run_rows(rows)

    def test_internal_lba_anchor_rejected(self):
        rows = self.complete_run() + [{"type":"calibrator", "label":"ANCHOR", "nominal":3.5, "measured":1}]
        with self.assertRaisesRegex(common.InputError, "outside"):
            self.run_rows(rows, "lba")

    def test_mislabeled_calibrator_boundary_rejected(self):
        rows = self.complete_run()
        rows[2]["label"] = "LLOQ"
        with self.assertRaisesRegex(common.InputError, "boundary"):
            self.run_rows(rows)

    def test_lba_selectivity_sources_are_not_chromatographic(self):
        self.assertEqual(M10_CRITERIA["lba"]["selectivity_min_sources"], 10)
        self.assertEqual(M10_CRITERIA["chromatographic"]["selectivity_min_sources"], 6)

    def test_grouped_accuracy_uses_group_count_for_interval(self):
        rows = [{"level":100,"measured":value,"group":day}
                for day, value in [("a",99), ("b",100), ("c",101)] for _ in range(4)]
        result = cli("check_accuracy_precision", "-i", "-", "--format", "json", data=json.dumps(rows))
        acc = json.loads(result.stdout)[0]["accuracy"][0]
        self.assertEqual(acc["n_independent_for_ci"], 3)
        self.assertAlmostEqual(acc["ci95_high"], 100 + 4.3026527299 / math.sqrt(3), places=7)

    def test_single_observation_cannot_satisfy_ci_requirement(self):
        result = cli("check_accuracy_precision", "-i", "-", "--accuracy-limit", "2",
                     "--require-ci-within-limit", data="level,measured\n100,100\n")
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_six_at_wrong_concentration_does_not_satisfy_design(self):
        data = "level,measured\n" + "80,80\n" * 6
        result = cli("check_accuracy_precision", "-i", "-", "--design-check", "assay",
                     "--test-concentration", "100", data=data)
        self.assertEqual(result.returncode, 1)

    def test_single_group_rsd_limit_is_checked(self):
        data = "level,measured,group\n100,80,a\n100,100,a\n100,120,a\n"
        result = cli("check_accuracy_precision", "-i", "-", "--rsd-limit", "1", data=data)
        self.assertEqual(result.returncode, 1)

    def test_unreplicated_groups_do_not_become_repeatability(self):
        data = "level,measured,group\n100,80,a\n100,100,b\n100,120,c\n"
        result = cli("check_accuracy_precision", "-i", "-", data=data)
        self.assertEqual(result.returncode, 1)
        self.assertIn("unidentifiable", result.stderr)

    def test_ql_requires_explicit_protocol_limits(self):
        result = cli("check_detection_limits", "--calibration", str(FIXTURES / "lowrange_calibration.csv"),
                     "--confirm-ql", "0.05", "--confirm-data", str(FIXTURES / "ql_confirmation.csv"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("pre-stated", result.stderr)

    def test_intercept_sd_uses_independent_curves(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "intercepts.csv"
            path.write_text("intercept\n1\n3\n5\n")
            result = cli("check_detection_limits", "--calibration", str(FIXTURES / "lowrange_calibration.csv"),
                         "--intercepts", str(path), "--format", "json")
            estimates = json.loads(result.stdout)[0]["estimates"]
            intercept = next(e for e in estimates if "intercepts" in e["approach"])
            self.assertAlmostEqual(intercept["sigma"], 2)
            self.assertAlmostEqual(intercept["QL"], 20 / abs(intercept["slope"]))

    def test_weighted_residual_scale_not_used_for_detection_limits(self):
        result = cli("check_detection_limits", "--calibration", str(FIXTURES / "lowrange_calibration.csv"),
                     "--weight", "1/x2")
        self.assertEqual(result.returncode, 2)

    def test_weighted_lack_of_fit_matches_hand_computation(self):
        xs=[1,1,2,2,3,3,4,4]
        ys=[2,4,4,8,8,10,13,17]
        weights=[1 / x**2 for x in xs]
        fit=common.fit_linear(xs,ys,weights)
        result=common.lack_of_fit(xs,ys,fit)
        pure=2 + 8/4 + 2/9 + 8/16
        residual=sum(w*r*r for w,r in zip(weights,fit.residuals))
        expected=((residual-pure)/2)/(pure/4)
        self.assertAlmostEqual(result["f_statistic"],expected,places=10)

    def test_calibration_order_does_not_change_concentration_runs(self):
        data=(FIXTURES / "calibration_curved.csv").read_text().splitlines()
        reversed_rows=data[0] + "\n" + "\n".join(reversed(data[1:])) + "\n"
        original=cli("check_response","-i",str(FIXTURES / "calibration_curved.csv"),"--format","json")
        reverse=cli("check_response","-i","-","--format","json",data=reversed_rows)
        self.assertAlmostEqual(json.loads(original.stdout)[0]["summary"]["runs test p"],
                               json.loads(reverse.stdout)[0]["summary"]["runs test p"])

    def test_nonfinite_values_are_rejected(self):
        for value in ("nan","inf","-inf"):
            with self.assertRaises(common.InputError):
                common.to_float(value,"response",0)
            result=cli("compare_methods","--margin",value)
            self.assertEqual(result.returncode,2)

    def test_ragged_json_names_missing_row(self):
        with self.assertRaisesRegex(common.InputError,"row 2"):
            common.require_columns([{"level":"1","response":"1"},{"level":"2"}], ["level","response"])

    def test_json_unavailable_statistics_use_null(self):
        output=io.StringIO()
        common.emit([{"values":[float("nan"),float("inf")]}],"json",output)
        self.assertEqual(json.loads(output.getvalue()),[{"values":[None,None]}])

    def test_passing_bablok_unsupported_ties_are_not_silently_dropped(self):
        with self.assertRaisesRegex(common.InputError,"tied"):
            common.passing_bablok([1,1,2,3,4],[1,2,2,3,4])

    def test_compendial_protocol_does_not_import_q2_design(self):
        result=cli("plan_validation","--framework","usp-1225","--attribute","assay","--protocol")
        self.assertNotIn("| response |",result.stdout)
