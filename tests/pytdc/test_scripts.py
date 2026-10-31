#!/usr/bin/env python3
"""Synthetic, network-free tests for the bundled PyTDC command-line helpers."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "pytdc" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _common as common  # noqa: E402
import benchmark_evaluation as benchmark  # noqa: E402
import cache_audit  # noqa: E402
import discover_metadata as discover  # noqa: E402
import load_and_split_data as loader  # noqa: E402
import molecular_generation as molecular  # noqa: E402

import skill_contract


class WorkingDirectoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = Path.cwd()
        self._temporary = tempfile.TemporaryDirectory()
        os.chdir(self._temporary.name)

    def tearDown(self) -> None:
        os.chdir(self._previous)
        self._temporary.cleanup()


class CommonTests(WorkingDirectoryTestCase):
    def test_safe_paths_reject_escape_and_absolute_paths(self) -> None:
        with self.assertRaises(common.CliError):
            common.safe_relative_path("../escape.json", label="output")
        with self.assertRaises(common.CliError):
            common.safe_relative_path("/tmp/escape.json", label="output")

    def test_emit_json_writes_atomically_and_refuses_overwrite(self) -> None:
        common.emit_json({"ok": True}, "reports/result.json")
        result = json.loads(Path("reports/result.json").read_text(encoding="utf-8"))
        self.assertEqual(result, {"ok": True})
        with self.assertRaises(common.CliError):
            common.emit_json({"ok": False}, "reports/result.json")

    def test_fraction_validation(self) -> None:
        self.assertEqual(
            common.validate_fractions([0.7, 0.1, 0.2]), (0.7, 0.1, 0.2)
        )
        with self.assertRaises(common.CliError):
            common.validate_fractions([0.7, 0.1, 0.3])


class DiscoveryTests(unittest.TestCase):
    def test_dataset_registry_is_bounded_without_loader(self) -> None:
        metadata = SimpleNamespace(
            dataset_names={"ADME": ["caco2_wang", "hia_hou"]},
            benchmark_names={"admet_group": {"ADME": ["caco2_wang"]}},
            evaluator_name=["mae", "roc-auc"],
            oracle_names=["qed", "sa"],
        )
        result = discover.collect_metadata(
            metadata,
            "1.1.15",
            kind="datasets",
            task="adme",
            offset=0,
            limit=1,
        )
        self.assertFalse(result["download_performed"])
        self.assertEqual(result["task_filter"], "ADME")
        self.assertEqual(result["datasets"]["returned"], 1)
        self.assertTrue(result["datasets"]["truncated"])


class LoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metadata = SimpleNamespace(
            dataset_names={
                "ADME": ["caco2_wang"],
                "DTI": ["bindingdb_patent"],
                "DrugSyn": ["drugcomb"],
                "MolGen": ["moses"],
            }
        )

    def test_scaffold_request_uses_exact_registry_name(self) -> None:
        task, dataset = loader.validate_request(
            task_query="adme",
            dataset_query="Caco2_Wang",
            method="scaffold",
            columns=[],
            time_column=None,
            metadata=self.metadata,
        )
        self.assertEqual((task, dataset), ("ADME", "caco2_wang"))

    def test_cold_split_requires_columns(self) -> None:
        with self.assertRaises(common.CliError):
            loader.validate_request(
                task_query="DTI",
                dataset_query="bindingdb_patent",
                method="cold_split",
                columns=[],
                time_column=None,
                metadata=self.metadata,
            )

    def test_verified_time_split(self) -> None:
        task, dataset = loader.validate_request(
            task_query="DTI",
            dataset_query="BindingDB_Patent",
            method="time",
            columns=[],
            time_column="Year",
            metadata=self.metadata,
        )
        self.assertEqual((task, dataset), ("DTI", "bindingdb_patent"))


class BenchmarkTests(unittest.TestCase):
    def test_duplicate_normalized_benchmarks_are_rejected(self) -> None:
        with self.assertRaises(common.CliError):
            benchmark.normalize_predictions(
                {"Caco2_Wang": [1], "caco2_wang": [2]}, mode="single",
                available=["caco2_wang"], selected_dataset=None,
            )

    def test_each_run_requires_same_benchmarks_and_lengths(self) -> None:
        for last in ({"hia_hou": [1]}, {"caco2_wang": [1, 2]}):
            with self.assertRaises(common.CliError):
                benchmark.normalize_predictions(
                    [{"caco2_wang": [1]}] * 4 + [last], mode="many",
                    available=["caco2_wang", "hia_hou"], selected_dataset=None,
                )

    def test_many_run_prediction_schema(self) -> None:
        payload = {
            "runs": [
                {"seed": seed, "predictions": {"caco2_wang": [0.1, 0.2]}}
                for seed in range(1, 6)
            ]
        }
        runs, seeds = benchmark.normalize_predictions(
            payload,
            mode="many",
            available=["caco2_wang"],
            selected_dataset="caco2_wang",
        )
        self.assertEqual(len(runs), 5)
        self.assertEqual(seeds, [1, 2, 3, 4, 5])

    def test_many_run_requires_five_runs(self) -> None:
        with self.assertRaises(common.CliError):
            benchmark.normalize_predictions(
                [{"caco2_wang": [0.1]}] * 4,
                mode="many",
                available=["caco2_wang"],
                selected_dataset=None,
            )

    def test_non_finite_predictions_are_rejected(self) -> None:
        with self.assertRaises(common.CliError):
            benchmark.normalize_predictions(
                {"caco2_wang": [float("nan")]},
                mode="single",
                available=["caco2_wang"],
                selected_dataset=None,
            )


class MolecularTests(WorkingDirectoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.metadata = SimpleNamespace(
            oracle_names=[
                "qed",
                "sa",
                "drd2",
                "fpscores",
                "novelty",
                "askcos",
                "3pbl_docking",
            ],
            download_oracle_names=["drd2", "fpscores"],
            distribution_oracles=["novelty"],
            download_receptor_oracle_name=["3pbl_docking"],
            synthetic_oracle_name=["askcos"],
        )

    def test_oracle_classification_is_explicit(self) -> None:
        self.assertEqual(
            molecular.classify_oracle(self.metadata, "QED"),
            ("qed", "local_scalar"),
        )
        self.assertEqual(
            molecular.classify_oracle(self.metadata, "DRD2"),
            ("drd2", "checkpoint_download"),
        )
        self.assertEqual(
            molecular.classify_oracle(self.metadata, "SA"),
            ("sa", "checkpoint_download"),
        )
        self.assertEqual(
            molecular.classify_oracle(self.metadata, "ASKCOS"),
            ("askcos", "remote_service"),
        )

    def test_smiles_input_is_bounded(self) -> None:
        self.assertEqual(
            molecular.load_smiles(["CCO"], None, max_molecules=1), ["CCO"]
        )
        with self.assertRaises(common.CliError):
            molecular.load_smiles(["CCO", "CCC"], None, max_molecules=1)


class CacheAuditTests(WorkingDirectoryTestCase):
    def test_file_limit_at_directory_boundary_is_not_complete(self) -> None:
        root = Path("cache")
        (root / "nested").mkdir(parents=True)
        (root / "one.csv").write_text("a")
        (root / "nested" / "two.csv").write_text("b")
        result = cache_audit.audit_cache(root, max_files=1, largest_limit=1)
        self.assertFalse(result["scan_complete"])
        self.assertEqual(result["file_count"], 1)

    def test_manifest_is_bounded_and_skips_symlinks(self) -> None:
        root = Path("data")
        root.mkdir()
        (root / "small.csv").write_bytes(b"123")
        (root / "large.pkl").write_bytes(b"123456")
        (root / "link").symlink_to(root / "small.csv")
        result = cache_audit.audit_cache(root.resolve(), max_files=10, largest_limit=1)
        self.assertEqual(result["file_count"], 2)
        self.assertEqual(result["total_bytes"], 9)
        self.assertEqual(result["largest_files"][0]["path"], "large.pkl")
        self.assertEqual(result["symlink_count_skipped"], 1)


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SCRIPTS.parent)

if __name__ == "__main__":
    unittest.main()
