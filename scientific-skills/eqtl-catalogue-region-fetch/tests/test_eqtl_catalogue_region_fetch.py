"""Unit tests for the eqtl-catalogue-region-fetch skill.

These tests exercise the pure helpers and CLI plumbing without making any
network calls. The tabix fetch path (which requires `pysam`) is not
exercised here; that integration is covered by the bundled `--demo` smoke
test which fetches against the live EBI FTP.

Run from the skill root:

    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "eqtl_catalogue_region_fetch.py"


def _load_module():
    """Load the skill script as a module regardless of cwd."""
    spec = importlib.util.spec_from_file_location("eqtl_catalogue_region_fetch", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["eqtl_catalogue_region_fetch"] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


class TestPureHelpers(unittest.TestCase):
    def test_ftp_url_for_constructs_canonical_path(self):
        url = MODULE.ftp_url_for("QTS000015", "QTD000276")
        self.assertEqual(
            url,
            "https://ftp.ebi.ac.uk/pub/databases/spot/eQTL/sumstats/QTS000015/QTD000276/QTD000276.all.tsv.gz",
        )

    def test_ftp_url_for_honours_custom_base(self):
        url = MODULE.ftp_url_for("QTS000015", "QTD000276", ftp_base="https://example.test/sumstats")
        self.assertTrue(url.startswith("https://example.test/sumstats/QTS000015/QTD000276/"))

    def test_build_variant_id_format(self):
        self.assertEqual(
            MODULE._build_variant_id("1", 108775337, "C", "T"),
            "1_108775337_C_T",
        )

    def test_maybe_float_returns_none_for_blank_and_invalid(self):
        self.assertIsNone(MODULE._maybe_float(None))
        self.assertIsNone(MODULE._maybe_float(""))
        self.assertIsNone(MODULE._maybe_float("not a number"))
        self.assertIsNone(MODULE._maybe_float(float("nan")))

    def test_maybe_float_parses_numeric_strings_and_floats(self):
        self.assertEqual(MODULE._maybe_float("1.5"), 1.5)
        self.assertEqual(MODULE._maybe_float(2), 2.0)
        self.assertEqual(MODULE._maybe_float("0"), 0.0)


class TestNormaliseRow(unittest.TestCase):
    def test_strips_chr_prefix_from_variant_id(self):
        row = {
            "variant": "chr1_108775337_C_T",
            "chromosome": "1",
            "position": 108775337,
            "ref": "C",
            "alt": "T",
            "beta": "0.07773",
            "se": "0.11226",
            "pvalue": "0.4898",
            "maf": "0.3125",
        }
        v = MODULE._normalise_row(row)
        self.assertEqual(v.variant_id, "1_108775337_C_T")
        self.assertEqual(v.chromosome, "1")
        self.assertEqual(v.position, 108775337)
        self.assertEqual(v.ref, "C")
        self.assertEqual(v.alt, "T")
        self.assertAlmostEqual(v.beta, 0.07773, places=4)
        self.assertAlmostEqual(v.se, 0.11226, places=4)
        self.assertAlmostEqual(v.p_value, 0.4898, places=4)
        self.assertAlmostEqual(v.maf, 0.3125, places=4)

    def test_uppercases_alleles(self):
        row = {
            "variant": "1_500_a_g",
            "chromosome": "1",
            "position": 500,
            "ref": "a",
            "alt": "g",
        }
        v = MODULE._normalise_row(row)
        self.assertEqual(v.ref, "A")
        self.assertEqual(v.alt, "G")

    def test_handles_missing_optional_numeric_fields(self):
        row = {
            "variant": "1_500_A_G",
            "chromosome": "1",
            "position": 500,
            "ref": "A",
            "alt": "G",
        }
        v = MODULE._normalise_row(row)
        self.assertIsNone(v.beta)
        self.assertIsNone(v.se)
        self.assertIsNone(v.p_value)
        self.assertIsNone(v.maf)

    def test_builds_variant_id_when_variant_field_absent(self):
        row = {
            "chromosome": "1",
            "position": 500,
            "ref": "A",
            "alt": "G",
        }
        v = MODULE._normalise_row(row)
        self.assertEqual(v.variant_id, "1_500_A_G")


class TestExamplesAndConfigLoader(unittest.TestCase):
    def test_examples_dir_resolves_to_real_path(self):
        d = MODULE._examples_dir()
        self.assertTrue(d.is_dir(), f"expected examples dir at {d}")

    def test_list_demos_returns_bundled_examples(self):
        demos = MODULE._list_demos()
        names = sorted(p.stem for p in demos)
        # At minimum the three biology demos must ship; convenience aliases
        # (default / input) are nice-to-have but not asserted on.
        for required in (
            "sort1_gtex_minor_salivary_gland",
            "il6r_gtex_small_intestine",
            "irf5_gtex_adipose_visceral",
        ):
            self.assertIn(required, names)

    def test_resolve_demo_path_finds_known_demo(self):
        p = MODULE._resolve_demo_path("sort1_gtex_minor_salivary_gland")
        self.assertTrue(p.is_file(), f"expected demo file at {p}")

    def test_resolve_demo_path_raises_for_unknown_demo(self):
        with self.assertRaises(FileNotFoundError):
            MODULE._resolve_demo_path("not_a_real_demo_name_12345")

    def test_load_config_parses_bundled_demo_json(self):
        p = MODULE._resolve_demo_path("sort1_gtex_minor_salivary_gland")
        cfg = MODULE._load_config(p)
        self.assertEqual(cfg["dataset_id"], "QTD000276")
        self.assertEqual(cfg["molecular_trait_id"], "ENSG00000134243")
        self.assertEqual(cfg["chromosome"], "1")
        self.assertIsInstance(cfg["start_bp"], int)
        self.assertIsInstance(cfg["end_bp"], int)
        self.assertLess(cfg["start_bp"], cfg["end_bp"])

    def test_load_config_round_trips_arbitrary_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "cfg.json"
            payload = {"dataset_id": "QTD999999", "chromosome": "X", "start_bp": 1, "end_bp": 2}
            p.write_text(json.dumps(payload))
            self.assertEqual(MODULE._load_config(p), payload)


class TestCLIPlumbing(unittest.TestCase):
    def test_list_demos_prints_to_stdout(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            MODULE._print_available_demos()
        out = buf.getvalue()
        self.assertIn("sort1_gtex_minor_salivary_gland", out)

    def test_main_with_list_demos_exits_zero(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = MODULE.main(["--list-demos"])
        self.assertEqual(rc, 0)
        self.assertIn("sort1_gtex_minor_salivary_gland", buf.getvalue())

    def test_main_help_exits_zero(self):
        # argparse --help raises SystemExit(0) by convention.
        with self.assertRaises(SystemExit) as ctx:
            buf = io.StringIO()
            with redirect_stdout(buf):
                MODULE.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
