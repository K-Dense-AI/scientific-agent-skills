"""Unnamed nonempty cells must not silently disappear before numeric analysis."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pkpd-modeling"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _common


class TestDelimitedFieldCounts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def read(self, content, suffix=".csv"):
        path = self.root / ("input" + suffix)
        path.write_text(content, encoding="utf-8")
        return _common.read_table(path)

    def test_unquoted_separator_cannot_truncate_concentration(self):
        with self.assertRaisesRegex(_common.InputError, "data record 1.*beyond the header"):
            self.read("time,conc\n0,8,000\n")

    def test_later_surplus_field_is_not_hidden_by_empty_field(self):
        with self.assertRaisesRegex(_common.InputError, "data record 2.*beyond the header"):
            self.read("time,conc\n0,8,\n1,4,,lost\n")

    def test_tsv_surplus_fields_are_rejected(self):
        with self.assertRaisesRegex(_common.InputError, "data record 1.*beyond the header"):
            self.read("time\tconc\n0\t8000\t4000\n", ".tsv")

    def test_record_number_is_not_a_physical_line_number(self):
        with self.assertRaisesRegex(_common.InputError, "data record 2.*beyond the header"):
            self.read('# provenance\n\ntime,conc,note\n0,8,"first\nrecord"\n1,4,note,lost\n')

    def test_declared_extra_columns_and_quoted_comma_are_preserved(self):
        self.assertEqual(
            self.read('time,conc,note\n0,8000,"sample, baseline"\n'),
            [{"time": "0", "conc": "8000", "note": "sample, baseline"}],
        )

    def test_quoted_numeric_comma_keeps_existing_numeric_policy(self):
        row = self.read('time,conc\n0,"8,000"\n')[0]
        self.assertEqual(row["conc"], "8,000")
        with self.assertRaises(_common.InputError):
            _common.parse_float(row["conc"], "conc")

    def test_empty_trailing_fields_remain_accepted(self):
        for suffix, delimiter in ((".csv", ","), (".tsv", "\t")):
            with self.subTest(suffix=suffix):
                self.assertEqual(
                    self.read(f"time{delimiter}conc\n0{delimiter}8000{delimiter}{delimiter} \n", suffix),
                    [{"time": "0", "conc": "8000"}],
                )

    def test_short_rows_keep_existing_missing_cells(self):
        self.assertEqual(
            self.read("time,conc,note\n0,8000\n1\n"),
            [{"time": "0", "conc": "8000", "note": ""},
             {"time": "1", "conc": "", "note": ""}],
        )

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "NCA needs NumPy")
    def test_nca_rejects_surplus_before_emitting_any_result(self):
        path = self.root / "profile.csv"
        path.write_text("time,conc\n0,8,000\n1,4,000\n2,2,000\n3,1,000\n")
        for output_format in ("json", "table", "tsv"):
            with self.subTest(output_format=output_format):
                result = subprocess.run(
                    [sys.executable, str(SCRIPTS / "nca.py"), "-i", str(path),
                     "--dose", "8000", "--route", "iv-bolus", "--format", output_format],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("data record 1", result.stderr)
                self.assertIn("beyond the header", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "NCA needs NumPy")
    def test_valid_nca_profile_keeps_its_concentration_scale(self):
        path = self.root / "profile.csv"
        path.write_text("time,conc\n0,8000\n1,4000\n2,2000\n3,1000\n")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "nca.py"), "-i", str(path),
             "--dose", "8000", "--route", "iv-bolus", "--format", "json"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        row = json.loads(result.stdout)["tables"][0]["rows"][0]
        self.assertEqual(row["cmax"], 8000.0)
        self.assertAlmostEqual(row["auc_inf_obs"], 11541.560327111705)
