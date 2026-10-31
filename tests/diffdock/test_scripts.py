"""Tests for the DiffDock helper scripts.

Docking itself needs the upstream repository and downloaded
checkpoints, so nothing here runs inference. What these scripts do around a run
is what the tests cover, and each group guards a specific way the surrounding
work goes wrong:

* `analyze_results` turns a directory of pose files into a ranked table. Get the
  confidence bands wrong and a low-confidence pose is reported as trustworthy;
  parse `rank10_...sdf` before `rank2_...sdf` and the "top" pose is not the top
  one. The published bands (> 0 high, -1.5 to 0 moderate, < -1.5 low, from
  DiffDock's README and `references/confidence_and_limitations.md`) are asserted
  literally, including their boundaries.
* `prepare_batch_csv` is a validator, so both directions matter: a usable CSV
  must pass silently, and each malformed row must be named. A CSV missing a
  required column used to raise KeyError instead of reporting it.
* `setup_check` only reports; the tests stub the interpreter, the import
  machinery, and the working directory so its verdicts are checked against a
  known environment rather than this machine's.
"""

from __future__ import annotations

import contextlib
import csv
import io
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "diffdock"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

# Only prepare_batch_csv needs a third-party package; the other two scripts are
# standard library, but a module-scope skip keeps the guard in one place.
pytest.importorskip("pandas", reason="diffdock's prepare_batch_csv needs pandas")

import analyze_results  # noqa: E402
import prepare_batch_csv  # noqa: E402
import setup_check  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

#: Aspirin, the SMILES the bundled template ships as its first example.
ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"


def quietly(function, *args, **kwargs):
    """Call `function`, returning (result, everything it printed)."""
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        result = function(*args, **kwargs)
    return result, stream.getvalue()


class TemporaryDirectoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)


class ConfidenceClassificationTests(unittest.TestCase):
    """The bands come from DiffDock upstream, so they are asserted literally."""

    def test_the_three_published_bands(self) -> None:
        self.assertEqual(analyze_results.classify_confidence(1.2), "High")
        self.assertEqual(analyze_results.classify_confidence(-0.7), "Moderate")
        self.assertEqual(analyze_results.classify_confidence(-3.0), "Low")

    def test_the_band_boundaries_fall_on_the_documented_side(self) -> None:
        # Exactly 0 is not "High" -- the high band is strictly above zero -- and
        # exactly -1.5 is "Low", so the moderate band is (-1.5, 0].
        self.assertEqual(analyze_results.classify_confidence(0.0), "Moderate")
        self.assertEqual(analyze_results.classify_confidence(-1.5), "Low")
        self.assertEqual(analyze_results.classify_confidence(-1.4999), "Moderate")

    def test_a_missing_score_is_unknown_rather_than_low(self) -> None:
        # A pose whose score could not be parsed must not be reported as bad.
        self.assertEqual(analyze_results.classify_confidence(None), "Unknown")


class ConfidenceExtractionTests(TemporaryDirectoryTestCase):
    def test_the_score_is_read_from_the_current_filename_format(self) -> None:
        path = self.root / "rank1_confidence0.87.sdf"
        path.write_text("")
        self.assertEqual(
            analyze_results.extract_confidence_score(path, self.root), 0.87
        )

    def test_a_negative_score_keeps_its_sign(self) -> None:
        # Most real poses score below zero; dropping the minus sign would turn
        # every low-confidence pose into a high-confidence one.
        path = self.root / "rank3_confidence-2.35.sdf"
        path.write_text("")
        self.assertEqual(
            analyze_results.extract_confidence_score(path, self.root), -2.35
        )

    def test_a_legacy_run_falls_back_to_confidence_scores_txt(self) -> None:
        # Older DiffDock wrote rank_1.sdf plus one score per line, in rank order.
        (self.root / "confidence_scores.txt").write_text("0.5\n-0.25\n-2.0\n")
        path = self.root / "rank_2.sdf"
        path.write_text("")
        self.assertEqual(
            analyze_results.extract_confidence_score(path, self.root), -0.25
        )

    def test_a_rank_past_the_end_of_the_legacy_file_is_not_invented(self) -> None:
        (self.root / "confidence_scores.txt").write_text("0.5\n")
        path = self.root / "rank_4.sdf"
        path.write_text("")
        self.assertIsNone(analyze_results.extract_confidence_score(path, self.root))

    def test_an_sdf_data_item_is_the_last_resort(self) -> None:
        # The SDF data-item spelling: a `> <tag>` line, then the value.
        path = self.root / "rank_1.sdf"
        path.write_text("  1  0  0\nM  END\n>  <confidence>\n-1.75\n\n$$$$\n")
        self.assertEqual(
            analyze_results.extract_confidence_score(path, self.root), -1.75
        )

    def test_an_inline_confidence_property_is_also_read(self) -> None:
        path = self.root / "rank_1.sdf"
        path.write_text("M  END\nconfidence: 0.31\n$$$$\n")
        self.assertEqual(
            analyze_results.extract_confidence_score(path, self.root), 0.31
        )

    def test_a_file_with_no_score_anywhere_yields_none(self) -> None:
        path = self.root / "rank_1.sdf"
        path.write_text("no properties here\n")
        self.assertIsNone(analyze_results.extract_confidence_score(path, self.root))


class ComplexParsingTests(TemporaryDirectoryTestCase):
    @staticmethod
    def write(directory: Path, *names: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        for name in names:
            (directory / name).write_text("")

    def test_ranks_are_ordered_numerically_not_lexicographically(self) -> None:
        # "rank10" sorts before "rank2" as text; the top pose would be wrong.
        self.write(
            self.root,
            "rank1_confidence0.90.sdf",
            "rank2_confidence0.10.sdf",
            "rank10_confidence-2.00.sdf",
        )
        parsed = analyze_results.parse_single_complex(self.root)
        self.assertEqual([p["rank"] for p in parsed["predictions"]], [1, 2, 10])

    def test_the_scored_filename_wins_over_the_bare_one_for_the_same_rank(self) -> None:
        # A run can leave both spellings behind; keeping the unscored one would
        # silently drop the confidence for that rank.
        self.write(self.root, "rank_1.sdf", "rank1_confidence0.42.sdf")
        parsed = analyze_results.parse_single_complex(self.root)
        self.assertEqual(len(parsed["predictions"]), 1)
        self.assertEqual(parsed["predictions"][0]["confidence"], 0.42)

    def test_a_directory_without_pose_files_parses_to_nothing(self) -> None:
        self.write(self.root, "log.txt")
        self.assertIsNone(analyze_results.parse_single_complex(self.root))

    def test_a_single_complex_directory_is_reported_under_one_key(self) -> None:
        self.write(self.root, "rank1_confidence0.5.sdf")
        results = analyze_results.parse_confidence_scores(self.root)
        self.assertEqual(list(results), ["single_complex"])

    def test_a_batch_directory_is_keyed_by_subdirectory_name(self) -> None:
        self.write(self.root / "complex_a", "rank1_confidence0.5.sdf")
        self.write(self.root / "complex_b", "rank1_confidence-1.0.sdf")
        self.write(self.root / "failed_run", "log.txt")
        results = analyze_results.parse_confidence_scores(self.root)
        # The subdirectory with no poses is omitted rather than listed empty.
        self.assertEqual(sorted(results), ["complex_a", "complex_b"])

    def test_an_input_sdf_in_the_batch_root_does_not_hide_nested_poses(self) -> None:
        self.write(self.root, "ligand.sdf")
        self.write(self.root / "complex_a", "rank1_confidence0.5.sdf")
        results = analyze_results.parse_confidence_scores(self.root)
        self.assertEqual(list(results), ["complex_a"])
        self.assertEqual(results["complex_a"]["predictions"][0]["confidence"], 0.5)

    def test_mixed_pose_layout_is_rejected_instead_of_dropping_complexes(self) -> None:
        self.write(self.root, "rank1_confidence0.5.sdf")
        self.write(self.root / "complex_a", "rank1_confidence-1.0.sdf")
        with self.assertRaisesRegex(ValueError, "Mixed single-complex and batch"):
            analyze_results.parse_confidence_scores(self.root)


class TopPredictionTests(unittest.TestCase):
    @staticmethod
    def results(*entries):
        """Build the {complex: {'predictions': [...]}} shape the parsers return."""
        built = {}
        for name, predictions in entries:
            built[name] = {
                "predictions": [
                    {"rank": rank, "file": f"rank{rank}.sdf", "path": f"{name}/rank{rank}.sdf",
                     "confidence": confidence}
                    for rank, confidence in predictions
                ]
            }
        return built

    def test_the_best_poses_are_ranked_across_every_complex(self) -> None:
        results = self.results(
            ("a", [(1, -0.5), (2, -2.0)]),
            ("b", [(1, 0.9), (2, 0.2)]),
        )
        top = analyze_results.get_top_predictions(results, n=3)
        self.assertEqual(
            [(entry["complex"], entry["confidence"]) for entry in top],
            [("b", 0.9), ("b", 0.2), ("a", -0.5)],
        )

    def test_unscored_poses_are_excluded_rather_than_sorted_as_zero(self) -> None:
        results = self.results(("a", [(1, None), (2, -1.0)]))
        top = analyze_results.get_top_predictions(results, n=10)
        self.assertEqual([entry["rank"] for entry in top], [2])

    def test_asking_for_more_than_exists_returns_what_exists(self) -> None:
        results = self.results(("a", [(1, 0.5)]))
        self.assertEqual(len(analyze_results.get_top_predictions(results, n=50)), 1)


class CsvExportTests(TemporaryDirectoryTestCase):
    def test_every_pose_becomes_one_row_with_its_band(self) -> None:
        results = {
            "kinase_1": {
                "predictions": [
                    {"rank": 1, "file": "r1.sdf", "path": "/x/r1.sdf", "confidence": 0.8},
                    {"rank": 2, "file": "r2.sdf", "path": "/x/r2.sdf", "confidence": -2.5},
                    {"rank": 3, "file": "r3.sdf", "path": "/x/r3.sdf", "confidence": None},
                ]
            }
        }
        destination = self.root / "summary.csv"
        quietly(analyze_results.export_to_csv, results, destination)

        with destination.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            [row["confidence_class"] for row in rows], ["High", "Low", "Unknown"]
        )
        # An unscored pose must leave the numeric column empty, not write "None",
        # which would parse as a string and break any downstream aggregation.
        self.assertEqual(rows[2]["confidence"], "")
        self.assertEqual(rows[0]["complex_name"], "kinase_1")
        self.assertEqual(rows[0]["file_path"], "/x/r1.sdf")


class SummaryFilterTests(unittest.TestCase):
    RESULTS = {
        "a": {
            "predictions": [
                {"rank": 1, "file": "r1.sdf", "path": "a/r1.sdf", "confidence": 0.5},
                {"rank": 2, "file": "r2.sdf", "path": "a/r2.sdf", "confidence": -1.0},
                {"rank": 3, "file": "r3.sdf", "path": "a/r3.sdf", "confidence": None},
            ]
        }
    }

    def test_without_a_threshold_every_pose_is_listed(self) -> None:
        _, output = quietly(analyze_results.print_summary, self.RESULTS)
        for rank in ("Rank  1", "Rank  2", "Rank  3"):
            self.assertIn(rank, output)

    def test_a_threshold_keeps_the_poses_at_or_above_it(self) -> None:
        # Inclusive at the boundary: -1.0 survives a threshold of -1.0.
        _, output = quietly(
            analyze_results.print_summary, self.RESULTS, None, -1.0
        )
        self.assertIn("Rank  1", output)
        self.assertIn("Rank  2", output)

    def test_a_threshold_drops_lower_and_unscored_poses(self) -> None:
        _, output = quietly(analyze_results.print_summary, self.RESULTS, None, 0.0)
        self.assertIn("Rank  1", output)
        self.assertNotIn("Rank  2", output)
        # An unscored pose cannot be shown to clear a threshold.
        self.assertNotIn("Rank  3", output)

    def test_top_n_truncates_the_listing(self) -> None:
        _, output = quietly(analyze_results.print_summary, self.RESULTS, 1)
        self.assertIn("Rank  1", output)
        self.assertNotIn("Rank  2", output)

    def test_an_empty_complex_is_reported_rather_than_skipped(self) -> None:
        _, output = quietly(analyze_results.print_summary, {"a": {"predictions": []}})
        self.assertIn("No predictions found", output)


class SmilesValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        if not prepare_batch_csv.RDKIT_AVAILABLE:
            self.skipTest("RDKit is not installed; SMILES validation is a no-op")

    def test_a_real_drug_smiles_is_accepted(self) -> None:
        valid, message = prepare_batch_csv.validate_smiles(ASPIRIN)
        self.assertTrue(valid, message)

    def test_a_malformed_smiles_is_rejected(self) -> None:
        # An unclosed ring bond: RDKit returns None rather than raising.
        valid, message = prepare_batch_csv.validate_smiles("C1CCCC")
        self.assertFalse(valid)
        self.assertIn("Invalid SMILES", message)

    def test_an_impossible_valence_is_rejected(self) -> None:
        valid, _ = prepare_batch_csv.validate_smiles("C(C)(C)(C)(C)C")
        self.assertFalse(valid)


class FilePathValidationTests(TemporaryDirectoryTestCase):
    def test_an_existing_file_passes(self) -> None:
        (self.root / "protein.pdb").write_text("")
        valid, _ = prepare_batch_csv.validate_file_path("protein.pdb", self.root)
        self.assertTrue(valid)

    def test_a_missing_file_is_named_in_the_message(self) -> None:
        valid, message = prepare_batch_csv.validate_file_path("absent.pdb", self.root)
        self.assertFalse(valid)
        self.assertIn("absent.pdb", message)

    def test_a_relative_path_resolves_against_the_base_directory(self) -> None:
        # Without the base directory the same path is looked up in the process
        # working directory, where it does not exist.
        (self.root / "sub").mkdir()
        (self.root / "sub" / "protein.pdb").write_text("")
        self.assertTrue(
            prepare_batch_csv.validate_file_path("sub/protein.pdb", self.root)[0]
        )
        self.assertFalse(prepare_batch_csv.validate_file_path("sub/protein.pdb")[0])

    def test_an_empty_path_is_allowed_because_a_sequence_may_replace_it(self) -> None:
        for value in ("", float("nan")):
            with self.subTest(value=value):
                valid, message = prepare_batch_csv.validate_file_path(value, self.root)
                self.assertTrue(valid)
                self.assertIn("protein_sequence", message)


class BatchCsvValidationTests(TemporaryDirectoryTestCase):
    HEADER = "complex_name,protein_path,ligand_description,protein_sequence"

    def write_csv(self, *rows: str) -> Path:
        path = self.root / "batch.csv"
        path.write_text("\n".join([self.HEADER, *rows]) + "\n")
        return path

    def test_a_usable_csv_passes_without_complaint(self) -> None:
        (self.root / "protein.pdb").write_text("")
        path = self.write_csv(f"target_1,protein.pdb,{ASPIRIN},")
        valid, messages = prepare_batch_csv.validate_csv(path, base_dir=self.root)
        self.assertTrue(valid, "\n".join(messages))
        joined = "\n".join(messages)
        self.assertIn("All required columns present", joined)
        self.assertIn("PASSED", joined)
        # A clean CSV must not accumulate per-row complaints.
        self.assertNotIn("Row 1", joined)

    def test_a_sequence_only_row_needs_no_protein_file(self) -> None:
        path = self.write_csv(f"target_1,,{ASPIRIN},MSKGEELFTG")
        valid, messages = prepare_batch_csv.validate_csv(path, base_dir=self.root)
        self.assertTrue(valid, "\n".join(messages))

    def test_a_row_with_neither_protein_input_is_rejected(self) -> None:
        path = self.write_csv(f"target_1,,{ASPIRIN},")
        valid, messages = prepare_batch_csv.validate_csv(path, base_dir=self.root)
        self.assertFalse(valid)
        self.assertIn("Must provide either protein_path or protein_sequence",
                      "\n".join(messages))

    def test_a_missing_complex_name_is_reported(self) -> None:
        path = self.write_csv(f",protein.pdb,{ASPIRIN},")
        (self.root / "protein.pdb").write_text("")
        valid, messages = prepare_batch_csv.validate_csv(path, base_dir=self.root)
        self.assertFalse(valid)
        self.assertIn("Missing complex_name", "\n".join(messages))

    def test_a_missing_protein_file_is_reported_with_its_row(self) -> None:
        path = self.write_csv(f"target_1,gone.pdb,{ASPIRIN},")
        valid, messages = prepare_batch_csv.validate_csv(path, base_dir=self.root)
        self.assertFalse(valid)
        joined = "\n".join(messages)
        self.assertIn("Row 1", joined)
        self.assertIn("Protein file issue", joined)

    def test_a_missing_ligand_description_is_reported(self) -> None:
        (self.root / "protein.pdb").write_text("")
        path = self.write_csv("target_1,protein.pdb,,")
        valid, messages = prepare_batch_csv.validate_csv(path, base_dir=self.root)
        self.assertFalse(valid)
        self.assertIn("Missing ligand_description", "\n".join(messages))

    def test_a_ligand_path_is_checked_as_a_file_not_as_smiles(self) -> None:
        # Anything containing a separator is treated as a path, so a missing
        # SDF must be reported as a file problem rather than as bad chemistry.
        (self.root / "protein.pdb").write_text("")
        path = self.write_csv("target_1,protein.pdb,ligands/gone.sdf,")
        valid, messages = prepare_batch_csv.validate_csv(path, base_dir=self.root)
        self.assertFalse(valid)
        self.assertIn("Ligand file issue", "\n".join(messages))

    def test_both_protein_inputs_together_warn_but_still_validate(self) -> None:
        (self.root / "protein.pdb").write_text("")
        path = self.write_csv(f"target_1,protein.pdb,{ASPIRIN},MSKGEELFTG")
        valid, messages = prepare_batch_csv.validate_csv(path, base_dir=self.root)
        self.assertTrue(valid, "\n".join(messages))
        self.assertIn("will use protein_path", "\n".join(messages))

    def test_a_missing_column_is_reported_instead_of_raising(self) -> None:
        # Regression: the per-row checks index protein_path directly, so a CSV
        # without that column used to abort with KeyError.
        path = self.root / "partial.csv"
        path.write_text(f"complex_name,ligand_description\ntarget_1,{ASPIRIN}\n")
        valid, messages = prepare_batch_csv.validate_csv(path, base_dir=self.root)
        self.assertFalse(valid)
        joined = "\n".join(messages)
        self.assertIn("Missing required columns", joined)
        self.assertIn("protein_path", joined)
        self.assertIn("protein_sequence", joined)

    def test_an_unreadable_csv_is_reported_not_raised(self) -> None:
        valid, messages = prepare_batch_csv.validate_csv(self.root / "absent.csv")
        self.assertFalse(valid)
        self.assertIn("Error reading CSV", messages[0])

    def test_a_header_only_csv_is_rejected(self) -> None:
        path = self.write_csv()
        valid, messages = prepare_batch_csv.validate_csv(path, base_dir=self.root)
        self.assertFalse(valid)
        self.assertIn("0 rows", messages[0])

    def test_an_invalid_smiles_row_fails_validation(self) -> None:
        if not prepare_batch_csv.RDKIT_AVAILABLE:
            self.skipTest("RDKit is not installed; SMILES validation is a no-op")
        (self.root / "protein.pdb").write_text("")
        path = self.write_csv("target_1,protein.pdb,C1CCCC,")
        valid, messages = prepare_batch_csv.validate_csv(path, base_dir=self.root)
        self.assertFalse(valid)
        self.assertIn("SMILES issue", "\n".join(messages))


class TemplateCsvTests(TemporaryDirectoryTestCase):
    def test_the_template_carries_the_four_columns_diffdock_requires(self) -> None:
        destination = self.root / "template.csv"
        frame = prepare_batch_csv.create_template_csv(destination)
        self.assertEqual(
            list(frame.columns),
            ["complex_name", "protein_path", "ligand_description", "protein_sequence"],
        )
        self.assertTrue(destination.is_file())

    def test_the_requested_number_of_example_rows_is_written(self) -> None:
        frame = prepare_batch_csv.create_template_csv(self.root / "t.csv", 2)
        self.assertEqual(len(frame), 2)

    def test_only_three_examples_exist_so_larger_requests_are_capped(self) -> None:
        # The CLI advertises 1-3; asking for more must not produce empty rows.
        frame = prepare_batch_csv.create_template_csv(self.root / "t.csv", 9)
        self.assertEqual(len(frame), 3)
        self.assertFalse(frame["complex_name"].isna().any())

    def test_the_first_example_ligand_is_a_parseable_molecule(self) -> None:
        frame = prepare_batch_csv.create_template_csv(self.root / "t.csv", 1)
        self.assertEqual(frame["ligand_description"][0], ASPIRIN)
        if prepare_batch_csv.RDKIT_AVAILABLE:
            self.assertTrue(prepare_batch_csv.validate_smiles(ASPIRIN)[0])


class ShippedTemplateAssetTests(unittest.TestCase):
    """`assets/batch_template.csv` is what a user copies, so it must be valid."""

    def setUp(self) -> None:
        with (SKILL_ROOT / "assets" / "batch_template.csv").open(newline="") as handle:
            self.rows = list(csv.DictReader(handle))

    def test_it_declares_the_columns_the_validator_requires(self) -> None:
        self.assertEqual(
            set(self.rows[0]),
            {"complex_name", "protein_path", "ligand_description", "protein_sequence"},
        )

    def test_every_row_supplies_a_protein_by_path_or_by_sequence(self) -> None:
        for row in self.rows:
            with self.subTest(complex_name=row["complex_name"]):
                self.assertTrue(
                    row["protein_path"] or row["protein_sequence"],
                    "row has neither protein_path nor protein_sequence",
                )

    def test_every_smiles_in_the_asset_parses(self) -> None:
        if not prepare_batch_csv.RDKIT_AVAILABLE:
            self.skipTest("RDKit is not installed; SMILES validation is a no-op")
        for row in self.rows:
            ligand = row["ligand_description"]
            if "/" in ligand or ligand.endswith((".sdf", ".mol2")):
                continue  # a file reference, not a molecule
            with self.subTest(ligand=ligand):
                self.assertTrue(prepare_batch_csv.validate_smiles(ligand)[0])


class PythonVersionCheckTests(unittest.TestCase):
    @staticmethod
    def version(major: int, minor: int, micro: int = 0):
        return mock.patch.object(
            sys, "version_info", types.SimpleNamespace(major=major, minor=minor, micro=micro)
        )

    def test_the_upstream_minimum_of_three_nine_passes(self) -> None:
        # DiffDock's environment.yml pins Python 3.9.18, so 3.9 is the floor.
        with self.version(3, 9, 18):
            passed, output = quietly(setup_check.check_python_version)
        self.assertTrue(passed)
        self.assertIn("3.9.18", output)

    def test_anything_older_fails_and_says_what_is_required(self) -> None:
        with self.version(3, 8, 10):
            passed, output = quietly(setup_check.check_python_version)
        self.assertFalse(passed)
        self.assertIn("3.9", output)

    def test_a_newer_interpreter_is_not_claimed_compatible(self) -> None:
        with self.version(3, 13, 1):
            passed, _ = quietly(setup_check.check_python_version)
        self.assertFalse(passed)


class PackageProbeTests(unittest.TestCase):
    def test_a_present_package_reports_its_version(self) -> None:
        module = types.ModuleType("diffdock_probe_present")
        module.__version__ = "1.2.3"
        with mock.patch.dict(sys.modules, {"diffdock_probe_present": module}):
            found, output = quietly(
                setup_check.check_package, "probe", "diffdock_probe_present"
            )
        self.assertTrue(found)
        self.assertIn("1.2.3", output)

    def test_a_nested_version_attribute_is_followed(self) -> None:
        # RDKit's version lives at rdkit.rdBase.__version__, not on the package.
        module = types.ModuleType("diffdock_probe_nested")
        module.rdBase = types.SimpleNamespace(__version__="2024.03.1")
        with mock.patch.dict(sys.modules, {"diffdock_probe_nested": module}):
            found, output = quietly(
                setup_check.check_package,
                "rdkit",
                "diffdock_probe_nested",
                "rdBase.__version__",
            )
        self.assertTrue(found)
        self.assertIn("2024.03.1", output)

    def test_a_package_without_a_version_still_counts_as_installed(self) -> None:
        module = types.ModuleType("diffdock_probe_bare")
        with mock.patch.dict(sys.modules, {"diffdock_probe_bare": module}):
            found, output = quietly(
                setup_check.check_package, "probe", "diffdock_probe_bare"
            )
        self.assertTrue(found)
        self.assertIn("unknown", output)

    def test_an_absent_package_is_reported_as_not_installed(self) -> None:
        found, output = quietly(
            setup_check.check_package, "probe", "diffdock_probe_absent_xyz"
        )
        self.assertFalse(found)
        self.assertIn("not installed", output)

    def test_torch_reports_cuda_separately_from_the_import(self) -> None:
        torch = types.ModuleType("torch")
        torch.__version__ = "2.4.0"
        torch.cuda = types.SimpleNamespace(is_available=lambda: False)
        with mock.patch.dict(sys.modules, {"torch": torch}):
            (installed, has_cuda), output = quietly(setup_check.check_pytorch)
        # Present but CPU-only: the check must pass while flagging no GPU.
        self.assertEqual((installed, has_cuda), (True, False))
        self.assertIn("CUDA not available", output)

    def test_a_visible_gpu_is_named_in_the_report(self) -> None:
        torch = types.ModuleType("torch")
        torch.__version__ = "2.4.0"
        torch.cuda = types.SimpleNamespace(
            is_available=lambda: True,
            get_device_name=lambda index: "NVIDIA A100",
            device_count=lambda: 2,
        )
        torch.version = types.SimpleNamespace(cuda="12.1")
        with mock.patch.dict(sys.modules, {"torch": torch}):
            (installed, has_cuda), output = quietly(setup_check.check_pytorch)
        self.assertEqual((installed, has_cuda), (True, True))
        self.assertIn("NVIDIA A100", output)
        self.assertIn("12.1", output)

    def test_missing_torch_reports_no_gpu_rather_than_raising(self) -> None:
        # None in sys.modules makes `import torch` raise ImportError.
        with mock.patch.dict(sys.modules, {"torch": None}):
            (installed, has_cuda), output = quietly(setup_check.check_pytorch)
        self.assertEqual((installed, has_cuda), (False, False))
        self.assertIn("not installed", output)

    def test_missing_esm_is_reported_as_required(self) -> None:
        with mock.patch.dict(sys.modules, {"esm": None}):
            found, output = quietly(setup_check.check_esm)
        self.assertFalse(found)
        # ESM2 is required for PDB inputs too, not just sequence folding.
        self.assertIn("protein sequence folding", output)
        self.assertIn("fair-esm", output)


class InstallationProbeTests(TemporaryDirectoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        origin = os.getcwd()
        self.addCleanup(os.chdir, origin)
        os.chdir(self.root)

    def test_an_unrelated_directory_is_not_a_diffdock_checkout(self) -> None:
        found, output = quietly(setup_check.check_diffdock_installation)
        self.assertFalse(found)
        self.assertIn("repository root", output)

    def test_the_upstream_entry_points_are_what_it_looks_for(self) -> None:
        for name in ("inference.py", "default_inference_args.yaml", "environment.yml"):
            (self.root / name).write_text("")
        found, output = quietly(setup_check.check_diffdock_installation)
        self.assertTrue(found)
        self.assertIn("inference.py", output)

    def test_absent_checkpoints_are_a_note_not_a_failure(self) -> None:
        for name in ("inference.py", "default_inference_args.yaml", "environment.yml"):
            (self.root / name).write_text("")
        found, output = quietly(setup_check.check_diffdock_installation)
        # Weights download on first run, so their absence must not fail setup.
        self.assertTrue(found)
        self.assertIn("downloaded on first run", output)

    def test_present_checkpoints_are_recognised_at_the_documented_path(self) -> None:
        (self.root / "inference.py").write_text("")
        for name, checkpoint in (("score_model", "best_ema_inference_epoch_model.pt"), ("confidence_model", "best_model_epoch75.pt")):
            directory = self.root / "workdir" / "v1.1" / name
            directory.mkdir(parents=True)
            (directory / "model_parameters.yml").write_text("fixture")
            (directory / checkpoint).write_text("fixture")
        _, output = quietly(setup_check.check_diffdock_installation)
        self.assertIn("Model checkpoints found", output)


class PerformanceNoteTests(unittest.TestCase):
    def test_the_gpu_and_cpu_guidance_do_not_swap(self) -> None:
        _, with_gpu = quietly(setup_check.print_performance_notes, True)
        _, without = quietly(setup_check.print_performance_notes, False)
        self.assertIn("GPU detected", with_gpu)
        self.assertNotIn("No GPU detected", with_gpu)
        # CPU docking is hours per complex; the warning is the point of the note.
        self.assertIn("No GPU detected", without)
        self.assertIn("SIGNIFICANTLY slower", without)




class RefreshRegressionTests(TemporaryDirectoryTestCase):
    def batch(self, rows, header=None):
        path = self.root / 'batch.csv'
        with path.open('w', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(header or ['complex_name', 'protein_path', 'ligand_description', 'protein_sequence'])
            writer.writerows(rows)
        return path

    def test_stereo_smiles_separators_are_not_paths(self):
        for smiles in ('F/C=C/F', r'F/C=C\F'):
            path = self.batch([['stereo', '', smiles, 'ACDEFGHIK']])
            valid, messages = prepare_batch_csv.validate_csv(path)
            self.assertTrue(valid, messages)

    def test_plain_filename_ligand_is_checked_relative_to_inference_cwd(self):
        (self.root / 'ligand.sdf').write_text('fixture; chemistry not inspected')
        path = self.batch([['file_input', '', 'ligand.sdf', 'ACDEFGHIK']])
        with mock.patch('pathlib.Path.cwd', return_value=self.root):
            valid, messages = prepare_batch_csv.validate_csv(path)
        self.assertTrue(valid, messages)

    def test_csv_parent_does_not_silently_replace_inference_cwd(self):
        (self.root / 'protein.pdb').write_text('fixture')
        path = self.batch([['relative', 'protein.pdb', ASPIRIN, '']])
        elsewhere = self.root / 'other'
        elsewhere.mkdir()
        with mock.patch('pathlib.Path.cwd', return_value=elsewhere):
            self.assertFalse(prepare_batch_csv.validate_csv(path)[0])
        self.assertTrue(prepare_batch_csv.validate_csv(path, self.root)[0])

    def test_duplicate_names_cannot_overwrite_predictions(self):
        path = self.batch([['same', '', 'CCO', 'ACDE'], ['same', '', 'CCN', 'ACDE']])
        valid, messages = prepare_batch_csv.validate_csv(path)
        self.assertFalse(valid)
        self.assertIn('Duplicate complex_name', '\n'.join(messages))

    def test_duplicate_headers_are_detected_before_pandas_mangles_them(self):
        path = self.batch([['a', '', 'CCO', 'ACDE', 'CCC']],
                          ['complex_name', 'protein_path', 'ligand_description', 'protein_sequence', 'ligand_description'])
        self.assertFalse(prepare_batch_csv.validate_csv(path)[0])

    def test_wrong_row_width_is_rejected(self):
        path = self.batch([['a', '', 'CCO', 'ACDE', 'extra']])
        self.assertFalse(prepare_batch_csv.validate_csv(path)[0])

    def test_output_path_traversal_and_numeric_ids_are_rejected(self):
        for name in ('../outside', '/absolute', 'a/b', '42', 'NA'):
            path = self.batch([[name, '', 'CCO', 'ACDE']])
            self.assertFalse(prepare_batch_csv.validate_csv(path)[0], name)

    def test_incomplete_or_truncated_sequences_are_rejected(self):
        for sequence in ('ACDE...', 'A' * 1023, 'ACD E'):
            path = self.batch([['sequence', '', 'CCO', sequence]])
            self.assertFalse(prepare_batch_csv.validate_csv(path)[0], sequence[:20])

    def test_a_directory_is_not_an_input_file(self):
        self.assertFalse(prepare_batch_csv.validate_file_path(self.root)[0])

    def test_missing_rdkit_does_not_claim_smiles_validation(self):
        with mock.patch.object(prepare_batch_csv, 'RDKIT_AVAILABLE', False):
            self.assertFalse(prepare_batch_csv.validate_smiles('CCO')[0])

    def test_two_scored_files_for_one_rank_are_rejected(self):
        for name in ('rank1_confidence0.87.sdf', 'rank1_confidence-1.0.sdf'):
            (self.root / name).write_text('fixture')
        with self.assertRaisesRegex(ValueError, 'Duplicate scored files'):
            analyze_results.parse_single_complex(self.root)

    def test_unrelated_sdf_is_not_a_successful_complex(self):
        (self.root / 'ligand.sdf').write_text('fixture')
        self.assertEqual(analyze_results.parse_confidence_scores(self.root), {})

    def test_exponent_score_is_not_truncated(self):
        path = self.root / 'rank1_confidence-1.2e-3.sdf'
        path.write_text('fixture')
        self.assertEqual(analyze_results.extract_confidence_score(path, self.root), -0.0012)

    def test_nonfinite_score_is_unknown(self):
        for score in (float('nan'), float('inf'), -float('inf')):
            self.assertEqual(analyze_results.classify_confidence(score), 'Unknown')
        (self.root / 'confidence_scores.txt').write_text('nan\n')
        path = self.root / 'rank1.sdf'
        path.write_text('fixture')
        self.assertIsNone(analyze_results.extract_confidence_score(path, self.root))

    def test_empty_checkpoint_directories_are_not_checkpoint_files(self):
        with mock.patch('os.getcwd', return_value=str(self.root)), mock.patch('pathlib.Path.is_file', return_value=False):
            _, output = quietly(setup_check.check_diffdock_installation)
        self.assertNotIn('[OK] Model checkpoints found', output)

    def test_unrelated_esm_distribution_is_rejected(self):
        module = types.ModuleType('esm')
        with mock.patch.dict(sys.modules, {'esm': module}):
            result, output = quietly(setup_check.check_esm)
        self.assertFalse(result)
        self.assertIn('fair-esm==2.0.0', output)


if __name__ == "__main__":
    unittest.main()
