"""Input and output failure shields for the Arboreto inference wrapper.

The wrapper tests mock inference. A separate synthetic smoke test below executes
both released algorithms in the pinned compatibility environment.
"""

from __future__ import annotations

import sys
import subprocess
from importlib.metadata import PackageNotFoundError, version
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "arboreto"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

pd = pytest.importorskip("pandas", reason="arboreto needs pandas")

import basic_grn_inference  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

NETWORK = pd.DataFrame(
    {
        "TF": ["TF1", "TF1", "TF2"],
        "target": ["G1", "G2", "G1"],
        "importance": [9.5, 4.2, 1.1],
    }
)


class InferenceWrapperTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)

        self.expression = self.root / "expression.tsv"
        self.expression.write_text(
            "TF1\tTF2\tG1\tG2\n"
            "1.0\t2.0\t3.0\t4.0\n"
            "1.5\t2.5\t3.5\t4.5\n"
            "2.0\t3.0\t4.0\t5.0\n",
            encoding="utf-8",
        )
        self.output = self.root / "network.tsv"

    def run_inference(self, **kwargs):
        with mock.patch.object(
            basic_grn_inference, "infer_network", return_value=NETWORK
        ) as algorithm:
            basic_grn_inference.run_grn_inference(
                str(self.expression), str(self.output), **kwargs
            )
        return algorithm

    def test_the_expression_matrix_is_read_with_genes_as_columns(self) -> None:
        algorithm = self.run_inference()
        passed = algorithm.call_args.args[0]
        self.assertEqual(list(passed.columns), ["TF1", "TF2", "G1", "G2"])
        self.assertEqual(len(passed), 3)  # three observations

    def test_without_a_tf_file_every_gene_is_a_candidate_regulator(self) -> None:
        # The sentinel is the string 'all'; an empty list is invalid upstream.
        algorithm = self.run_inference()
        self.assertEqual(algorithm.call_args.args[1], "all")

    def test_a_tf_file_restricts_the_candidate_regulators(self) -> None:
        tf_file = self.root / "tfs.txt"
        tf_file.write_text("TF1\nTF2\n", encoding="utf-8")
        algorithm = self.run_inference(tf_file=str(tf_file))
        self.assertEqual(list(algorithm.call_args.args[1]), ["TF1", "TF2"])

    def test_the_seed_is_forwarded_so_runs_are_reproducible(self) -> None:
        self.assertEqual(self.run_inference().call_args.args[2], 777)
        self.assertEqual(self.run_inference(seed=42).call_args.args[2], 42)

    def test_the_link_limit_is_forwarded_and_defaults_to_unlimited(self) -> None:
        self.assertIsNone(self.run_inference().call_args.args[3])
        self.assertEqual(self.run_inference(limit=100).call_args.args[3], 100)

    def test_the_network_is_written_headerless_and_tab_separated(self) -> None:
        # This wrapper uses the upstream example's headerless TSV format.
        self.run_inference()
        lines = self.output.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 3)
        self.assertNotIn("importance", lines[0])
        self.assertEqual(lines[0].split("\t"), ["TF1", "G1", "9.5"])

    def test_no_index_column_is_written(self) -> None:
        self.run_inference()
        for line in self.output.read_text(encoding="utf-8").strip().splitlines():
            with self.subTest(line=line):
                self.assertEqual(len(line.split("\t")), 3)

    def test_row_identifiers_are_only_removed_explicitly(self):
        self.expression.write_text("cell\tTF1\tTF2\na\t1\t2\nb\t3\t4\n")
        with self.assertRaisesRegex(ValueError, "numeric"):
            self.run_inference()
        algorithm = self.run_inference(index_col=0)
        self.assertEqual(list(algorithm.call_args.args[0].columns), ["TF1", "TF2"])

    def test_duplicate_headers_are_rejected_before_pandas_renames_them(self):
        self.expression.write_text("TF1\tTF1\n1\t2\n3\t4\n")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.run_inference()

    def test_missing_and_nonfinite_expression_is_rejected(self):
        for value in ("NaN", "inf", ""):
            with self.subTest(value=value):
                self.expression.write_text(f"TF1\tTF2\n1\t{value}\n3\t4\n")
                with self.assertRaisesRegex(ValueError, "nonfinite"):
                    self.run_inference()

    def test_blank_or_nonmatching_tf_file_is_rejected(self):
        tf_file = self.root / "tfs.txt"
        for value in ("\n", "other\n"):
            tf_file.write_text(value)
            with self.assertRaisesRegex(ValueError, "no names matching"):
                self.run_inference(tf_file=tf_file)

    def test_tf_names_are_deduplicated_and_intersected(self):
        tf_file = self.root / "tfs.txt"
        tf_file.write_text("TF1\nTF1\n\nmissing\nTF2\n")
        algorithm = self.run_inference(tf_file=tf_file)
        self.assertEqual(algorithm.call_args.args[1], ["TF1", "TF2"])

    def test_nonpositive_limits_and_workers_are_rejected(self):
        for kwargs in ({"limit": 0}, {"limit": -1}, {"workers": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.run_inference(**kwargs)

    def test_empty_network_is_not_reported_as_success(self):
        with mock.patch.object(basic_grn_inference, "infer_network", return_value=NETWORK.iloc[:0]):
            with self.assertRaisesRegex(RuntimeError, "no links"):
                basic_grn_inference.run_grn_inference(self.expression, self.output)
        self.assertFalse(self.output.exists())


class ParserTests(unittest.TestCase):
    def test_the_documented_flags_are_all_accepted(self) -> None:
        source = (SCRIPTS / "basic_grn_inference.py").read_text(encoding="utf-8")
        for flag in ("--tf-file", "--seed", "--limit", "--workers", "--index-col"):
            with self.subTest(flag=flag):
                self.assertIn(flag, source)

    def test_the_positional_arguments_are_required(self) -> None:
        result = skill_contract.cli.run_help(SCRIPTS / "basic_grn_inference.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("expression_file", result.stdout)
        self.assertIn("output_file", result.stdout)


class SyntheticRuntimeTests(unittest.TestCase):
    """Run real regressions in isolated interpreter processes, not mocked imports."""

    def setUp(self):
        try:
            compatible = version("arboreto") == "0.1.6" and version("dask") == "2024.7.1"
        except PackageNotFoundError:
            compatible = False
        if not compatible:
            self.skipTest("Run tests/run_all.py --isolated arboreto for the tested runtime")

    def test_dense_sparse_and_genie3_produce_valid_candidate_edges(self):
        for algorithm, sparse_input in (("grnboost2", False), ("grnboost2", True), ("genie3", False)):
            with self.subTest(algorithm=algorithm, sparse_input=sparse_input):
                code = f"""
import dask
dask.config.set({{"dataframe.query-planning": False}})
import numpy as np
import pandas as pd
from scipy.sparse import csc_matrix
from distributed import Client, LocalCluster
from arboreto.algo import {algorithm}
rng = np.random.default_rng(123)
values = rng.normal(size=(32, 4))
values[:, 2] = 3 * values[:, 0] + rng.normal(scale=.1, size=32)
genes = ["TF1", "TF2", "G1", "G2"]
expression = csc_matrix(values) if {sparse_input!r} else pd.DataFrame(values, columns=genes)
with LocalCluster(n_workers=1, threads_per_worker=1, processes=False,
                  dashboard_address=None, memory_limit=0) as cluster, Client(cluster) as client:
    network = {algorithm}(expression_data=expression, gene_names=genes,
                           tf_names=["TF1", "TF2"], seed=777, client_or_address=client)
assert list(network.columns) == ["TF", "target", "importance"]
assert len(network) == 6
assert set(network.TF) == {{"TF1", "TF2"}}
assert set(network.target) == set(genes)
assert not (network.TF == network.target).any()
assert np.isfinite(network.importance).all() and (network.importance > 0).all()
assert network.importance.is_monotonic_decreasing
assert ((network.TF == "TF1") & (network.target == "G1")).any()
"""
                result = subprocess.run([sys.executable, "-c", code], capture_output=True,
                                        text=True, timeout=90)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_completes_real_inference_with_explicit_row_ids(self):
        import numpy as np

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = pd.DataFrame(np.random.default_rng(123).normal(size=(32, 4)),
                                columns=["TF1", "TF2", "G1", "G2"])
            data.index = [f"cell{i}" for i in range(len(data))]
            data.to_csv(root / "input.tsv", sep="\t")
            (root / "tfs.txt").write_text("TF1\nTF2\n")
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "basic_grn_inference.py"),
                 str(root / "input.tsv"), str(root / "output.tsv"),
                 "--tf-file", str(root / "tfs.txt"), "--index-col", "0",
                 "--limit", "3", "--workers", "1"],
                capture_output=True, text=True, timeout=90,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = pd.read_csv(root / "output.tsv", sep="\t", header=None)
            self.assertEqual(output.shape, (3, 3))
            self.assertTrue(set(output[0]) <= {"TF1", "TF2"})


if __name__ == "__main__":
    unittest.main()
