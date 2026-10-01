"""Tests for the PyDESeq2 analysis driver.

Everything expensive in this script happens inside PyDESeq2; what the script
itself owns is the data handling around it, and each piece of that is a way to
get a plausible-looking but wrong answer:

* orientation -- the counts file is genes x samples and DESeq2 wants samples x
  genes, so a transposition mistake silently analyses genes as if they were
  samples;
* alignment -- counts and metadata must end up on the same index in the same
  order, or every sample is compared against another sample's condition;
* the shrinkage coefficient -- `condition[T.treated]` is a formulaic naming
  convention, and the test below checks it against a design matrix PyDESeq2
  actually built rather than against the string the script composes;
* thresholds -- gene filtering is `>=` and significance is a strict `<`, both
  pinned at the boundary here.

One end-to-end fit runs on a synthetic dataset with a known 8-fold change, so
the pipeline is checked against log2(8) = 3 rather than against itself.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pydeseq2"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

np = pytest.importorskip("numpy", reason="pydeseq2 scripts need numpy")
pd = pytest.importorskip("pandas", reason="pydeseq2 scripts need pandas")
pytest.importorskip("pydeseq2", reason="pydeseq2 skill needs pydeseq2")
anndata = pytest.importorskip("anndata", reason="save_results writes an .h5ad")
matplotlib = pytest.importorskip("matplotlib", reason="create_plots needs matplotlib")

matplotlib.use("Agg")  # never open a window; must precede pyplot import
import matplotlib.pyplot as plt  # noqa: E402

import run_deseq2_analysis as driver  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


class TemporaryDirectoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)

    def write_csv(self, name: str, frame: pd.DataFrame) -> Path:
        path = self.root / name
        frame.to_csv(path)
        return path


class LoadAndValidateTests(TemporaryDirectoryTestCase):
    """The counts file is genes x samples; DESeq2 needs samples x genes."""

    def setUp(self) -> None:
        super().setUp()
        # Two genes, three samples. GENE1 in s3 is 6 -- a unique value, so the
        # orientation of the result can be checked by where it lands.
        self.counts = pd.DataFrame(
            {"s1": [1, 10], "s2": [2, 20], "s3": [6, 30]},
            index=["GENE1", "GENE2"],
        )
        self.metadata = pd.DataFrame(
            {"condition": ["control", "control", "treated"]},
            index=["s1", "s2", "s3"],
        )
        self.counts_path = self.write_csv("counts.csv", self.counts)
        self.metadata_path = self.write_csv("metadata.csv", self.metadata)

    def test_the_counts_matrix_is_transposed_by_default(self) -> None:
        counts, metadata = driver.load_and_validate_data(
            self.counts_path, self.metadata_path
        )
        self.assertEqual(list(counts.index), ["s1", "s2", "s3"])
        self.assertEqual(list(counts.columns), ["GENE1", "GENE2"])
        # The value that was at (GENE1, s3) must now be at (s3, GENE1).
        self.assertEqual(counts.loc["s3", "GENE1"], 6)
        self.assertEqual(list(metadata.index), ["s1", "s2", "s3"])

    def test_an_already_oriented_matrix_is_left_alone(self) -> None:
        path = self.write_csv("oriented.csv", self.counts.T)
        counts, _ = driver.load_and_validate_data(
            path, self.metadata_path, transpose_counts=False
        )
        self.assertEqual(list(counts.index), ["s1", "s2", "s3"])
        self.assertEqual(counts.loc["s3", "GENE1"], 6)

    def test_negative_counts_are_rejected(self) -> None:
        # DESeq2's negative-binomial model has no meaning for negative counts;
        # they indicate the file holds normalised or logged values.
        broken = self.counts.copy()
        broken.loc["GENE1", "s2"] = -5
        with self.assertRaisesRegex(ValueError, "negative values"):
            driver.load_and_validate_data(
                self.write_csv("negative.csv", broken), self.metadata_path
            )

    def test_zero_counts_are_accepted(self) -> None:
        # Zero is a legitimate observation -- only negatives are invalid.
        zeroed = self.counts.copy()
        zeroed.loc["GENE1", "s2"] = 0
        counts, _ = driver.load_and_validate_data(
            self.write_csv("zeroed.csv", zeroed), self.metadata_path
        )
        self.assertEqual(counts.loc["s2", "GENE1"], 0)

    def test_unequal_sample_sets_are_rejected(self) -> None:
        extra = self.metadata.copy()
        extra.loc["s4"] = ["treated"]
        with self.assertRaisesRegex(ValueError, "Sample sets differ"):
            driver.load_and_validate_data(self.counts_path, self.write_csv("extra.csv", extra))
        wider = self.counts.copy()
        wider["s4"] = [7, 40]
        with self.assertRaisesRegex(ValueError, "Sample sets differ"):
            driver.load_and_validate_data(self.write_csv("wider.csv", wider), self.metadata_path)

    def test_fractional_missing_and_infinite_counts_are_rejected(self) -> None:
        for value in [1.5, np.nan, np.inf, 2**53]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                broken = self.counts.astype(float)
                broken.loc["GENE1", "s2"] = value
                driver.load_and_validate_data(self.write_csv("bad.csv", broken), self.metadata_path)

    def test_duplicate_raw_headers_are_rejected_before_pandas_renames_them(self) -> None:
        path = self.root / "duplicate.csv"
        path.write_text("gene,s1,s1,s3\nGENE1,1,2,3\n")
        with self.assertRaisesRegex(ValueError, "duplicate headers"):
            driver.load_and_validate_data(path, self.metadata_path)

    def test_ragged_csv_cannot_shift_columns_into_an_implicit_index(self):
        path = self.root / "ragged.csv"
        path.write_text("gene,s1,s2,s3\nGENE1,1,2,3,4\n")
        with self.assertRaisesRegex(ValueError, "number of fields"):
            driver.load_and_validate_data(path, self.metadata_path)

    def test_duplicate_gene_ids_are_rejected(self) -> None:
        broken = self.counts.copy()
        broken.index = ["GENE1", "GENE1"]
        with self.assertRaisesRegex(ValueError, "unique"):
            driver.load_and_validate_data(self.write_csv("bad.csv", broken), self.metadata_path)

    def test_numeric_looking_identifiers_retain_leading_zeroes(self) -> None:
        counts = self.counts.copy()
        counts.columns = ["001", "002", "003"]
        metadata = self.metadata.copy()
        metadata.index = counts.columns
        loaded, annotations = driver.load_and_validate_data(self.write_csv("ids.csv", counts), self.write_csv("ids_meta.csv", metadata))
        self.assertEqual(list(loaded.index), ["001", "002", "003"])
        self.assertTrue(loaded.index.equals(annotations.index))

    def test_a_reordered_metadata_index_is_realigned_not_left_shuffled(self) -> None:
        # Same samples, different order. If the two frames were handed to
        # DESeq2 as-is, every sample would carry another sample's condition.
        shuffled = self.metadata.loc[["s3", "s1", "s2"]]
        counts, metadata = driver.load_and_validate_data(
            self.counts_path, self.write_csv("shuffled.csv", shuffled)
        )
        self.assertTrue(counts.index.equals(metadata.index))
        self.assertEqual(metadata.loc["s3", "condition"], "treated")

    def test_a_matching_pair_survives_untouched(self) -> None:
        counts, metadata = driver.load_and_validate_data(
            self.counts_path, self.metadata_path
        )
        self.assertEqual(counts.shape, (3, 2))
        self.assertEqual(metadata.shape, (3, 1))


class FilterDataTests(unittest.TestCase):
    def setUp(self) -> None:
        # Column totals: KEEP 30, EDGE 10, DROP 9.
        self.counts = pd.DataFrame(
            {"KEEP": [10, 10, 10], "EDGE": [5, 5, 0], "DROP": [3, 3, 3]},
            index=["s1", "s2", "s3"],
        )
        self.metadata = pd.DataFrame(
            {"condition": ["control", "treated", "treated"]},
            index=["s1", "s2", "s3"],
        )

    def test_genes_below_the_total_count_threshold_are_removed(self) -> None:
        counts, _ = driver.filter_data(self.counts, self.metadata, min_counts=10)
        self.assertEqual(list(counts.columns), ["KEEP", "EDGE"])

    def test_the_threshold_is_inclusive_at_the_boundary(self) -> None:
        # EDGE totals exactly 10; `>=` keeps it and `>` would not.
        counts, _ = driver.filter_data(self.counts, self.metadata, min_counts=10)
        self.assertIn("EDGE", counts.columns)
        counts, _ = driver.filter_data(self.counts, self.metadata, min_counts=11)
        self.assertNotIn("EDGE", counts.columns)

    def test_a_zero_threshold_keeps_every_gene(self) -> None:
        counts, _ = driver.filter_data(self.counts, self.metadata, min_counts=0)
        self.assertEqual(list(counts.columns), ["KEEP", "EDGE", "DROP"])

    def test_missing_condition_requires_explicit_resolution(self) -> None:
        metadata = self.metadata.copy()
        metadata.loc["s2", "condition"] = np.nan
        with self.assertRaisesRegex(ValueError, "Missing contrast annotations"):
            driver.filter_data(self.counts, metadata, condition_col="condition")

    def test_absent_contrast_column_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing contrast column"):
            driver.filter_data(self.counts, self.metadata, condition_col="batch")

    def test_empty_filtered_matrix_or_zero_library_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            driver.filter_data(self.counts, self.metadata, min_counts=1000)
        zero_sample = self.counts.copy()
        zero_sample.loc["s1"] = 0
        with self.assertRaisesRegex(ValueError, "positive total"):
            driver.filter_data(zero_sample, self.metadata)

    def test_gene_filtering_does_not_disturb_the_sample_axis(self) -> None:
        counts, metadata = driver.filter_data(
            self.counts, self.metadata, min_counts=10, condition_col="condition"
        )
        self.assertTrue(counts.index.equals(metadata.index))


class ShrinkageCoefficientTests(unittest.TestCase):
    """Actual formulaic contrast vectors, including non-reference and reverse tests."""

    def setUp(self):
        self.counts = pd.DataFrame(np.full((9, 4), 20), index=[f"s{i}" for i in range(9)])
        self.counts.columns = [f"g{i}" for i in range(4)]
        self.metadata = pd.DataFrame({"condition": pd.Categorical(["control"] * 3 + ["a"] * 3 + ["b"] * 3, categories=["control", "a", "b"])}, index=self.counts.index)
        self.dds = driver.DeseqDataSet(counts=self.counts, metadata=self.metadata, design="~condition", quiet=True)

    def test_real_positive_coefficient_is_inferred(self):
        self.assertEqual(driver.infer_shrink_coeff(self.dds, ["condition", "a", "control"]), "condition[T.a]")

    def test_reverse_or_nonreference_comparison_cannot_shrink_wrong_effect(self):
        for contrast in [["condition", "control", "a"], ["condition", "b", "a"]]:
            with self.subTest(contrast=contrast), self.assertRaisesRegex(ValueError, "--no-shrink"):
                driver.infer_shrink_coeff(self.dds, contrast)

    def test_explicit_wrong_coefficient_cannot_override_contrast(self):
        with self.assertRaisesRegex(ValueError, "mismatch"):
            driver.infer_shrink_coeff(self.dds, ["condition", "a", "control"], "condition[T.b]")

    def test_cli_relevels_before_fitting_for_nonreference_comparison(self):
        contrast = ["condition", "b", "a"]
        metadata = driver.prepare_contrast_metadata(self.metadata, contrast)
        self.assertEqual(metadata["condition"].cat.categories[0], "a")
        dds = driver.DeseqDataSet(counts=self.counts, metadata=metadata, design="~condition", quiet=True)
        self.assertEqual(driver.infer_shrink_coeff(dds, contrast), "condition[T.b]")
        self.assertEqual(self.metadata["condition"].cat.categories[0], "control")


class FakeStats:
    """A `DeseqStats` stand-in exposing only `results_df`."""

    def __init__(self, results: pd.DataFrame) -> None:
        self.results_df = results
        self.alpha = 0.05
        self.contrast = ["condition", "treated", "control"]


class FakeDataSet:
    """A `DeseqDataSet` stand-in whose h5ad export is a real AnnData."""

    def __init__(self, samples: int = 2, genes: int = 3) -> None:
        self._adata = anndata.AnnData(
            X=np.arange(samples * genes, dtype="float32").reshape(samples, genes)
        )

    def to_picklable_anndata(self):
        return self._adata


def results_frame() -> pd.DataFrame:
    """Four genes spanning the significance boundary, plus a filtered-out gene."""
    return pd.DataFrame(
        {
            "baseMean": [500.0, 100.0, 80.0, 60.0],
            "log2FoldChange": [3.0, -2.0, 0.1, 0.5],
            "pvalue": [1e-30, 1e-10, 0.4, np.nan],
            # 0.05 exactly must NOT count as significant: the test is `< 0.05`.
            "padj": [1e-28, 0.01, 0.05, np.nan],
        },
        index=["UP", "DOWN", "BORDERLINE", "FILTERED"],
    )


class SaveResultsTests(TemporaryDirectoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.results = results_frame()
        self.output = self.root / "results"
        driver.save_results(FakeStats(self.results), FakeDataSet(), self.output)

    def test_the_four_documented_artefacts_are_written(self) -> None:
        written = {path.name for path in self.output.iterdir()}
        self.assertEqual(
            written,
            {
                "deseq2_results.csv",
                "significant_genes.csv",
                "results_sorted_by_padj.csv",
                "deseq_dataset.h5ad",
                "deseq2_results_unshrunken.csv",
                "analysis_manifest.json",
            },
        )

    def test_every_gene_is_kept_in_the_full_table(self) -> None:
        full = pd.read_csv(self.output / "deseq2_results.csv", index_col=0)
        self.assertEqual(list(full.index), ["UP", "DOWN", "BORDERLINE", "FILTERED"])

    def test_only_genes_strictly_below_the_fdr_cutoff_are_significant(self) -> None:
        significant = pd.read_csv(self.output / "significant_genes.csv", index_col=0)
        # BORDERLINE sits exactly at 0.05 and FILTERED has no padj at all.
        self.assertEqual(sorted(significant.index), ["DOWN", "UP"])

    def test_the_sorted_table_puts_the_strongest_evidence_first(self) -> None:
        sorted_results = pd.read_csv(
            self.output / "results_sorted_by_padj.csv", index_col=0
        )
        self.assertEqual(list(sorted_results.index)[:2], ["UP", "DOWN"])
        # A gene with no adjusted p-value must sort last, not first.
        self.assertEqual(list(sorted_results.index)[-1], "FILTERED")

    def test_the_dataset_is_exported_as_readable_h5ad_not_a_pickle(self) -> None:
        # Pickles execute arbitrary code on load; h5ad does not.
        loaded = anndata.read_h5ad(self.output / "deseq_dataset.h5ad")
        self.assertEqual(loaded.shape, (2, 3))

    def test_a_missing_output_directory_is_created(self) -> None:
        nested = self.root / "a" / "b" / "c"
        driver.save_results(FakeStats(self.results), FakeDataSet(), nested)
        self.assertTrue((nested / "deseq2_results.csv").is_file())

    def test_no_significant_genes_still_writes_every_file(self) -> None:
        # An empty result set is a valid outcome, not an error.
        nothing = self.results.copy()
        nothing["padj"] = 0.9
        output = self.root / "none"
        driver.save_results(FakeStats(nothing), FakeDataSet(), output)
        significant = pd.read_csv(output / "significant_genes.csv", index_col=0)
        self.assertEqual(len(significant), 0)

    def test_export_uses_the_requested_alpha(self):
        stats = FakeStats(self.results)
        stats.alpha = 0.01
        driver.save_results(stats, FakeDataSet(), self.root / "strict")
        selected = pd.read_csv(self.root / "strict" / "significant_genes.csv", index_col=0)
        self.assertEqual(list(selected.index), ["UP"])


class PlotTests(TemporaryDirectoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.addCleanup(plt.close, "all")
        self.results = results_frame()

    def test_both_plots_are_written_as_non_empty_files(self) -> None:
        driver.create_plots(FakeStats(self.results), self.root)
        for name in ("volcano_plot.png", "ma_plot.png"):
            with self.subTest(name=name):
                path = self.root / name
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 0)

    def test_plotting_does_not_mutate_the_results_table(self) -> None:
        # The volcano plot adds a -log10 column; leaking it into results_df
        # would put a derived column into every file written afterwards.
        stats = FakeStats(self.results)
        driver.create_plots(stats, self.root)
        self.assertEqual(list(stats.results_df.columns), list(results_frame().columns))

    def test_genes_filtered_out_by_deseq2_do_not_break_the_plots(self) -> None:
        # Missing padj remains missing and is omitted from volcano y values.
        only_nan = self.results.copy()
        only_nan["padj"] = np.nan
        driver.create_plots(FakeStats(only_nan), self.root)
        self.assertTrue((self.root / "volcano_plot.png").is_file())


class EndToEndFitTests(unittest.TestCase):
    """One real fit, checked against a fold change that is true by construction."""

    @classmethod
    def setUpClass(cls) -> None:
        rng = np.random.default_rng(0)
        samples = [f"s{i}" for i in range(6)]
        genes = [f"G{j}" for j in range(40)]
        counts = rng.poisson(100, size=(6, 40))
        counts[3:, 0] *= 8  # G0 is exactly 8-fold higher in the treated group
        cls.counts = pd.DataFrame(counts, index=samples, columns=genes)
        cls.metadata = pd.DataFrame(
            {"condition": ["control"] * 3 + ["treated"] * 3}, index=samples
        )
        cls.dds, cls.inference = driver.run_deseq2(
            cls.counts, cls.metadata, "~condition", n_cpus=1
        )
        cls.stats = driver.run_statistical_tests(
            cls.dds,
            contrast=["condition", "treated", "control"],
            alpha=0.05,
            shrink_lfc=True,
            inference=cls.inference,
        )

    def test_the_inferred_coefficient_matches_the_real_design_matrix(self) -> None:
        # The whole point of infer_shrink_coeff: the composed name must exist
        # in the matrix PyDESeq2 built, not merely look plausible.
        self.assertIn(
            driver.infer_shrink_coeff(self.dds, ["condition", "treated", "control"]),
            list(self.dds.obsm["design_matrix"].columns),
        )

    def test_the_planted_eight_fold_change_is_recovered(self) -> None:
        # log2(8) == 3. Shrinkage pulls the estimate in slightly, so allow
        # half a log2 unit -- but the sign and magnitude must be right.
        lfc = self.stats.results_df.loc["G0", "log2FoldChange"]
        self.assertAlmostEqual(lfc, 3.0, delta=0.5)

    def test_the_planted_gene_is_the_only_significant_one(self) -> None:
        significant = self.stats.results_df[self.stats.results_df.padj < 0.05]
        self.assertEqual(list(significant.index), ["G0"])

    def test_every_tested_gene_gets_a_row(self) -> None:
        self.assertEqual(len(self.stats.results_df), 40)

    def test_reverse_wald_contrast_flips_sign_and_retains_pvalues(self):
        reverse = driver.run_statistical_tests(self.dds, ["condition", "control", "treated"], shrink_lfc=False, inference=self.inference)
        original = self.stats.unshrunk_results_df
        np.testing.assert_allclose(reverse.results_df["log2FoldChange"], -original["log2FoldChange"], atol=1e-10)
        np.testing.assert_allclose(reverse.results_df["stat"], -original["stat"], atol=1e-8)
        np.testing.assert_allclose(reverse.results_df["pvalue"], original["pvalue"], equal_nan=True)

    def test_shrinkage_preserves_wald_evidence_and_original_lfc(self):
        original = self.stats.unshrunk_results_df
        pd.testing.assert_frame_equal(self.stats.results_df[["stat", "pvalue", "padj"]], original[["stat", "pvalue", "padj"]])
        self.assertFalse(np.allclose(self.stats.results_df["lfcSE"], original["lfcSE"]))
        self.assertFalse(np.allclose(self.stats.results_df["log2FoldChange"], original["log2FoldChange"]))
        np.testing.assert_allclose(self.dds.varm["LFC"]["condition[T.treated]"] / np.log(2), original["log2FoldChange"])

    def test_real_fitted_anndata_roundtrip_preserves_axes_counts_and_results(self):
        with tempfile.TemporaryDirectory() as directory:
            driver.save_results(self.stats, self.dds, directory)
            loaded = anndata.read_h5ad(Path(directory) / "deseq_dataset.h5ad")
            np.testing.assert_array_equal(loaded.X, self.counts.to_numpy())
            self.assertEqual(list(loaded.obs_names), list(self.counts.index))
            self.assertEqual(list(loaded.var_names), list(self.counts.columns))
            np.testing.assert_allclose(loaded.layers["normed_counts"], self.counts.to_numpy() / loaded.obs["size_factors"].to_numpy()[:, None])
            self.assertIn("dispersions", loaded.var)
            unshrunk = pd.read_csv(Path(directory) / "deseq2_results_unshrunken.csv", index_col=0)
            np.testing.assert_allclose(unshrunk["log2FoldChange"], self.stats.unshrunk_results_df["log2FoldChange"])

    def test_unfiltered_bh_matches_independent_hand_calculation(self):
        stats = driver.DeseqStats(self.dds, contrast=["condition", "treated", "control"], independent_filter=False, cooks_filter=False, inference=self.inference, quiet=True)
        stats.summary()
        result = stats.results_df
        np.testing.assert_allclose(result["stat"], result["log2FoldChange"] / result["lfcSE"])
        pvalues = result["pvalue"].to_numpy()
        order = np.argsort(pvalues)
        adjusted = np.minimum.accumulate((pvalues[order] * len(pvalues) / np.arange(1, len(pvalues) + 1))[::-1])[::-1]
        adjusted = np.minimum(adjusted, 1)
        np.testing.assert_allclose(result["padj"].to_numpy()[order], adjusted)

    def test_invalid_alpha_is_rejected_before_statistics(self):
        for alpha in [0, 1, -0.1, np.nan]:
            with self.subTest(alpha=alpha), self.assertRaisesRegex(ValueError, "alpha"):
                driver.run_statistical_tests(self.dds, ["condition", "treated", "control"], alpha=alpha)


class NumericalContractTests(unittest.TestCase):
    def make_dds(self, counts, **kwargs):
        values = np.asarray(counts)
        frame = pd.DataFrame(values, index=[f"s{i}" for i in range(len(values))], columns=[f"g{i}" for i in range(values.shape[1])])
        metadata = pd.DataFrame({"condition": ["control"] * (len(values)//2) + ["treated"] * (len(values)-len(values)//2)}, index=frame.index)
        return driver.DeseqDataSet(counts=frame, metadata=metadata, design="~condition", inference=driver.DefaultInference(n_cpus=1), quiet=True, **kwargs)

    def test_ratio_normalization_recovers_library_multipliers(self):
        multipliers = np.array([1, 2, 4, 8])
        counts = multipliers[:, None] * np.array([10, 20, 30, 40])
        dds = self.make_dds(counts)
        dds.fit_size_factors()
        expected = multipliers / np.exp(np.log(multipliers).mean())
        np.testing.assert_allclose(dds.obs["size_factors"], expected)
        np.testing.assert_allclose(dds.layers["normed_counts"], counts / expected[:, None])
        self.assertGreater(dds.obs["size_factors"].max(), 2)  # valid factors need not be near one

    def test_control_gene_normalization_uses_only_declared_controls(self):
        counts = np.array([[10, 20, 500], [20, 40, 500], [40, 80, 10], [80, 160, 10]])
        dds = self.make_dds(counts, control_genes=["g0", "g1"])
        dds.fit_size_factors()
        expected = np.array([1, 2, 4, 8]) / np.sqrt(8)
        np.testing.assert_allclose(dds.obs["size_factors"], expected)

    def test_poscounts_matches_positive_log_ratio_convention(self):
        counts = np.array([[0, 8, 12, 3], [2, 0, 6, 3], [4, 4, 0, 6], [8, 2, 3, 0]])
        dds = self.make_dds(counts, size_factors_fit_type="poscounts")
        dds.fit_size_factors()
        logmeans = np.log(np.where(counts > 0, counts, 1)).mean(axis=0)
        sf = np.array([np.exp(np.median(np.log(row[row > 0]) - logmeans[row > 0])) for row in counts])
        sf /= np.exp(np.log(sf).mean())
        np.testing.assert_allclose(dds.obs["size_factors"], sf)

    def test_poscounts_binary_data_has_no_usable_genes_in_054(self):
        # Upstream 0.5.4 additionally requires logmeans > 0, excluding 0/1 genes.
        dds = self.make_dds([[1, 0], [0, 1], [1, 0], [0, 1]], size_factors_fit_type="poscounts")
        with np.errstate(all="ignore"), pytest.warns(RuntimeWarning):
            dds.fit_size_factors()
        self.assertTrue(dds.obs["size_factors"].isna().all())

    def test_confounded_or_saturated_design_is_rejected_before_fit(self):
        dds = self.make_dds(np.full((4, 10), 20))
        metadata = dds.obs.copy()
        metadata["batch"] = metadata["condition"]
        with self.assertRaisesRegex(ValueError, "full rank"):
            driver.run_deseq2(pd.DataFrame(dds.X, index=dds.obs_names, columns=dds.var_names), metadata, "~batch + condition")
        metadata["sample"] = metadata.index
        with self.assertRaisesRegex(ValueError, "residual"):
            driver.run_deseq2(pd.DataFrame(dds.X, index=dds.obs_names, columns=dds.var_names), metadata, "~sample")

    def test_missing_adjustment_annotation_is_rejected(self):
        dds = self.make_dds(np.full((6, 10), 20))
        metadata = dds.obs.copy()
        metadata["age"] = [20., 30., 40., np.nan, 50., 60.]
        with self.assertRaises(ValueError):
            driver.run_deseq2(pd.DataFrame(dds.X, index=dds.obs_names, columns=dds.var_names), metadata, "~age + condition")


class OutlierContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fits = {}
        for n in [6, 16]:
            values = np.random.default_rng(50).poisson(100, size=(n, 60))
            values[0, 0] = 1000000
            values[:, -1] = 0
            counts = pd.DataFrame(values, index=[f"s{i}" for i in range(n)], columns=[f"g{i}" for i in range(60)])
            metadata = pd.DataFrame({"condition": ["control"] * (n//2) + ["treated"] * (n//2)}, index=counts.index)
            dds = driver.DeseqDataSet(counts=counts, metadata=metadata, design="~condition", n_cpus=1, quiet=True)
            dds.deseq2()
            stats = driver.DeseqStats(dds, contrast=["condition", "treated", "control"], n_cpus=1, quiet=True)
            stats.summary()
            cls.fits[n] = dds, stats

    def test_three_replicates_filter_test_without_count_replacement(self):
        dds, stats = self.fits[6]
        self.assertFalse(dds.var.loc["g0", "replaced"])
        self.assertTrue(dds.var.loc["g0", "_pvalue_cooks_outlier"])
        self.assertTrue(np.isnan(stats.results_df.loc["g0", "pvalue"]))
        self.assertTrue(np.isfinite(stats.results_df.loc["g0", "stat"]))

    def test_eight_replicates_enable_refitting_without_destroying_original_counts(self):
        dds, stats = self.fits[16]
        self.assertTrue(dds.var.loc["g0", "replaced"])
        self.assertTrue(dds.var.loc["g0", "refitted"])
        self.assertEqual(dds.X[0, 0], 1000000)
        self.assertTrue(np.isfinite(stats.results_df.loc["g0", "pvalue"]))
        self.assertLess(abs(stats.results_df.loc["g0", "log2FoldChange"]), 0.5)

    def test_all_zero_gene_retains_a_missing_test_row(self):
        _, stats = self.fits[6]
        row = stats.results_df.loc["g59"]
        self.assertEqual(row["baseMean"], 0)
        self.assertTrue(row[["log2FoldChange", "pvalue", "padj"]].isna().all())


if __name__ == "__main__":
    unittest.main()
