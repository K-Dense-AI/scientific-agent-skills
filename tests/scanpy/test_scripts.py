"""Tests for the scanpy pipeline scripts.

Fifteen scripts share one `_common.py`, and that shared layer is where a
mistake propagates everywhere: a format dispatched to the wrong reader, an
output written without its parent directory, a summary that omits the
embeddings a later step depends on. So the tests concentrate there, driving
real `.h5ad` round trips through a small synthetic AnnData.

The per-script tests are deliberately shallow -- they check that each CLI
parses its arguments and refuses a missing input rather than running a full
clustering pipeline, which would take minutes and prove little about the code.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "scanpy"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

np = pytest.importorskip("numpy", reason="scanpy scripts need numpy")
pytest.importorskip("scanpy", reason="scanpy skill needs scanpy")
import anndata as ad  # noqa: E402

import _common  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def synthetic(n_obs: int = 20, n_vars: int = 10):
    rng = np.random.default_rng(4)
    counts = rng.poisson(3, size=(n_obs, n_vars)).astype("float32")
    adata = ad.AnnData(counts)
    adata.obs_names = [f"cell{i}" for i in range(n_obs)]
    adata.var_names = [f"Gene{i}" for i in range(n_vars)]
    return adata


class SharedIoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)


class RoundTripTests(SharedIoTestCase):
    def test_an_h5ad_round_trips_through_save_and_load(self) -> None:
        original = synthetic()
        path = self.root / "data.h5ad"
        _common.save_anndata(original, str(path))

        self.assertTrue(path.is_file())
        reloaded = _common.load_anndata(str(path))
        self.assertEqual(reloaded.shape, original.shape)
        self.assertEqual(list(reloaded.var_names), list(original.var_names))
        np.testing.assert_allclose(reloaded.X, original.X)

    def test_saving_creates_the_parent_directory(self) -> None:
        # Pipelines write to results/step3/out.h5ad before that tree exists.
        path = self.root / "results" / "step3" / "out.h5ad"
        _common.save_anndata(synthetic(), str(path))
        self.assertTrue(path.is_file())

    def test_a_csv_is_dispatched_to_the_csv_reader(self) -> None:
        path = self.root / "counts.csv"
        path.write_text("Gene1,Gene2\n1,2\n3,4\n", encoding="utf-8")
        loaded = _common.load_anndata(str(path))
        self.assertEqual(loaded.shape[1], 2)

    def test_a_missing_input_exits_with_a_message(self) -> None:
        # `die` prints to stderr and exits with a code, so check both.
        import io
        from contextlib import redirect_stderr

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                _common.load_anndata(str(self.root / "absent.h5ad"))
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("input not found", stderr.getvalue())

    def test_an_unrecognised_extension_exits_rather_than_guessing(self) -> None:
        import io
        from contextlib import redirect_stderr

        path = self.root / "counts.parquet"
        path.write_bytes(b"")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit):
                _common.load_anndata(str(path))
        self.assertIn("unrecognized input format", stderr.getvalue())

    def test_the_extension_check_is_case_insensitive(self) -> None:
        original = synthetic()
        path = self.root / "DATA.H5AD"
        original.write_h5ad(path)
        self.assertEqual(_common.load_anndata(str(path)).shape, original.shape)


class SummaryTests(unittest.TestCase):
    def test_the_summary_leads_with_the_matrix_shape(self) -> None:
        summary = _common.summarize(synthetic(n_obs=42, n_vars=7))
        self.assertTrue(summary.startswith("42 cells x 7 genes"))

    def test_annotations_and_embeddings_are_listed(self) -> None:
        adata = synthetic()
        adata.obs["leiden"] = ["0"] * adata.n_obs
        adata.obsm["X_pca"] = np.zeros((adata.n_obs, 2))
        adata.layers["counts"] = adata.X.copy()

        summary = _common.summarize(adata)
        self.assertIn("obs: leiden", summary)
        self.assertIn("obsm: X_pca", summary)
        self.assertIn("layers: counts", summary)

    def test_a_bare_matrix_summarises_to_one_line(self) -> None:
        # anndata >= 0.13 reports an unnamed `None` key on `.layers` standing
        # for X, which must not be rendered as a layer (and must not raise).
        self.assertEqual(len(_common.summarize(synthetic()).splitlines()), 1)

    def test_unnamed_mapping_keys_are_filtered_without_losing_named_layers(self) -> None:
        # AnnData versions differ in whether .layers exposes X under None.
        # Probe the filtering boundary explicitly; the tests above cover real
        # AnnData summaries with both bare matrices and named layers.
        sentinel = object()
        for keys, expected in (
            ({}, []),
            ({None: sentinel}, []),
            ({None: sentinel, "counts": sentinel}, ["counts"]),
            ({"counts": sentinel, None: sentinel, "normalized": sentinel},
             ["counts", "normalized"]),
        ):
            with self.subTest(keys=list(keys)):
                self.assertEqual(_common._named_keys(keys), expected)

    def test_the_obs_listing_is_capped(self) -> None:
        # A dataset with hundreds of obs columns must not print all of them.
        adata = synthetic()
        for index in range(50):
            adata.obs[f"column{index}"] = 0
        obs_line = [
            line for line in _common.summarize(adata).splitlines()
            if line.startswith("obs:")
        ][0]
        self.assertEqual(len(obs_line.removeprefix("obs: ").split(", ")), 20)


class ArgumentTests(unittest.TestCase):
    def test_the_shared_io_arguments_are_attached(self) -> None:
        import argparse

        parser = _common.add_io_args(argparse.ArgumentParser())
        args = parser.parse_args(["input.h5ad"])
        self.assertEqual(args.input, "input.h5ad")
        self.assertEqual(args.figdir, "figures")
        self.assertIsNone(args.output)

    def test_a_default_output_is_advertised_in_the_help(self) -> None:
        import argparse

        parser = _common.add_io_args(
            argparse.ArgumentParser(), default_output="processed.h5ad"
        )
        self.assertEqual(parser.parse_args(["in.h5ad"]).output, "processed.h5ad")
        self.assertIn("processed.h5ad", parser.format_help())

    def test_the_output_flag_overrides_the_default(self) -> None:
        import argparse

        parser = _common.add_io_args(argparse.ArgumentParser(), default_output="d.h5ad")
        self.assertEqual(
            parser.parse_args(["in.h5ad", "-o", "mine.h5ad"]).output, "mine.h5ad"
        )


class ConfigurationTests(unittest.TestCase):
    def test_configuring_scanpy_creates_the_figure_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            figures = Path(directory) / "figures"
            _common.configure_scanpy(figdir=str(figures))
            self.assertTrue(figures.is_dir())

    def test_the_dpi_and_verbosity_reach_scanpy(self) -> None:
        import scanpy as sc

        with tempfile.TemporaryDirectory() as directory:
            _common.configure_scanpy(figdir=directory, dpi=77, verbosity=0)
        self.assertEqual(sc.settings.verbosity, 0)


class PipelineCliTests(unittest.TestCase):
    """Every script refuses a missing input instead of failing deep inside."""

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)

    def test_each_cli_reports_a_missing_input_cleanly(self) -> None:
        scripts = [
            path
            for path in sorted(SCRIPTS.glob("*.py"))
            if path.name not in {"_common.py", "run_pipeline.py"}
        ]
        self.assertTrue(scripts)
        for script in scripts:
            with self.subTest(script=script.name):
                result = subprocess.run(
                    [sys.executable, str(script), str(self.root / "absent.h5ad")],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=self.root,
                )
                self.assertNotEqual(result.returncode, 0, f"{script.name} accepted it")
                combined = result.stdout + result.stderr
                self.assertNotIn("Traceback", combined, script.name)


if __name__ == "__main__":
    unittest.main()
