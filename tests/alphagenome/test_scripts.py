"""Tests for the alphagenome skill scripts.

Nothing here touches the network. The parsing, coordinate, Phred, export, and
portal-link tests run in the bare project environment; the tests that build
AnnData objects or drive the CLIs against a fake Atlas client need the
``alphagenome`` package and skip cleanly without it. Run them for real with:

    python tests/run_all.py --isolated alphagenome
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "alphagenome"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


common = _load_script("_common")
atlas_link = _load_script("atlas_link")
atlas_query = _load_script("atlas_query")
score_variants = _load_script("score_variants")

try:  # the SDK-dependent half
    import anndata
    import numpy as np
    import pandas as pd
    from alphagenome.data import genome

    HAVE_SDK = True
except ImportError:  # pragma: no cover - bare project environment
    HAVE_SDK = False


def run_main(module, argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = module.main(argv)
    return code, out.getvalue(), err.getvalue()


def rows_from_tsv(text):
    lines = [line for line in text.splitlines() if line]
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"))) for line in lines[1:]]


# ---------------------------------------------------------------------------
# shared contract
# ---------------------------------------------------------------------------

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


# ---------------------------------------------------------------------------
# _common: parsing and arithmetic (standard library only)
# ---------------------------------------------------------------------------


class ChromosomeTests(unittest.TestCase):
    def test_chr_prefix_is_added_once(self):
        self.assertEqual(common.normalize_chromosome("22"), "chr22")
        self.assertEqual(common.normalize_chromosome("chr22"), "chr22")
        self.assertEqual(common.normalize_chromosome("CHRX"), "chrX")

    def test_mitochondrion_spellings_collapse(self):
        for spelling in ("MT", "M", "chrM", "chrMT"):
            self.assertEqual(common.normalize_chromosome(spelling), "chrM")

    def test_empty_is_rejected(self):
        with self.assertRaises(ValueError):
            common.normalize_chromosome("  ")


class VariantParsingTests(unittest.TestCase):
    def test_default_gnomad_gtex_and_open_targets_spellings_agree(self):
        expected = common.VariantSpec("chr22", 36201698, "A", "C")
        for text in (
            "chr22:36201698:A>C",
            "22:36201698:A>C",
            "22-36201698-A-C",
            "chr22_36201698_A_C_b38",
            "22_36201698_A_C",
            "22:36201698:A:C",
        ):
            with self.subTest(text=text):
                self.assertEqual(common.parse_variant_string(text), expected)

    def test_bases_are_uppercased_and_indels_kept(self):
        spec = common.parse_variant_string("chr1:100:at>a")
        self.assertEqual((spec.ref, spec.alt), ("AT", "A"))
        self.assertFalse(spec.is_snv)
        self.assertTrue(common.parse_variant_string("chr1:100:A>T").is_snv)

    def test_rsid_and_garbage_are_rejected_with_guidance(self):
        for text in ("rs12345", "chr1:100", "chr1:100:A", "chr1:100:A>Z", "chr1:x:A>T"):
            with self.subTest(text=text), self.assertRaises(ValueError) as caught:
                common.parse_variant_string(text)
            self.assertIn("1-based", str(caught.exception))

    def test_string_form_round_trips(self):
        spec = common.parse_variant_string("22-36201698-A-C")
        self.assertEqual(str(spec), "chr22:36201698:A>C")
        self.assertEqual(spec.to_row()["position"], 36201698)


class IntervalParsingTests(unittest.TestCase):
    def test_one_based_closed_becomes_zero_based_half_open(self):
        self.assertEqual(common.parse_interval_string("chr11:5225727-5226575"), ("chr11", 5225726, 5226575))
        self.assertEqual(common.interval_width(5225726, 5226575), 849)

    def test_thousands_separators_and_missing_prefix(self):
        self.assertEqual(common.parse_interval_string("11:5,225,727-5,226,575"), ("chr11", 5225726, 5226575))

    def test_single_base_window_has_width_one(self):
        chrom, start, end = common.parse_interval_string("chr1:100-100")
        self.assertEqual(end - start, 1)

    def test_invalid_intervals_are_rejected(self):
        for text in ("chr1:0-10", "chr1:20-10", "chr1:10", "chr1-10-20"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                common.parse_interval_string(text)


class VariantFileTests(unittest.TestCase):
    def test_tsv_with_vcf_style_columns(self):
        variants, warnings = common.read_variant_table(FIXTURES / "variants.tsv")
        self.assertEqual([str(v) for v in variants], ["chr22:36201698:A>C", "chr9:128225994:G>A"])
        self.assertEqual(variants[0].name, "rs_a")
        self.assertEqual(len(warnings), 1)
        self.assertIn("line 4", warnings[0])

    def test_csv_with_variant_column_reports_unparseable_rows(self):
        variants, warnings = common.read_variant_table(FIXTURES / "variants.csv")
        self.assertEqual([str(v) for v in variants], ["chr22:36201698:A>C", "chr22:36201698:A>G"])
        self.assertEqual(len(warnings), 1)
        self.assertIn("rs12345", warnings[0])

    def test_vcf_splits_multiallelic_and_skips_symbolic(self):
        variants, warnings = common.read_variant_table(FIXTURES / "variants.vcf")
        self.assertEqual(
            [str(v) for v in variants],
            ["chr22:36201698:A>C", "chr22:36201698:A>G", "chr22:36201700:AT>A", "chrM:100:G>A"],
        )
        self.assertEqual(variants[0].name, "rs1")
        self.assertEqual(variants[2].name, "")
        self.assertTrue(any("<DEL>" in message for message in warnings))

    def test_missing_columns_are_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "odd.tsv"
            path.write_text("gene\tscore\nHBB\t1\n", encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                common.read_variant_table(path)
            self.assertIn("CHROM/POS/REF/ALT", str(caught.exception))

    def test_missing_file_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            common.read_variant_table(FIXTURES / "nope.tsv")

    def test_collect_variants_merges_flags_and_file(self):
        variants, warnings = common.collect_variants(["chr1:100:A>T"], str(FIXTURES / "variants.tsv"))
        self.assertEqual(len(variants), 3)
        self.assertEqual(str(variants[0]), "chr1:100:A>T")
        self.assertEqual(len(warnings), 1)


class ScoreArithmeticTests(unittest.TestCase):
    def test_phred_scale_matches_the_report(self):
        for cdf, phred in ((0.9, 10.0), (0.99, 20.0), (0.999, 30.0)):
            tail, value = common.cdf_to_tail_and_phred(cdf)
            self.assertAlmostEqual(tail, 1 - cdf, places=9)
            self.assertAlmostEqual(value, phred, places=6)

    def test_saturated_quantile_is_floored_not_infinite(self):
        tail, phred = common.cdf_to_tail_and_phred(1.0)
        self.assertEqual(tail, 1e-7)
        self.assertAlmostEqual(phred, 70.0)

    def test_nan_propagates(self):
        tail, phred = common.cdf_to_tail_and_phred(float("nan"))
        self.assertTrue(tail != tail and phred != phred)

    def test_top_percent(self):
        self.assertAlmostEqual(common.phred_to_top_percent(20.0), 1.0)
        self.assertAlmostEqual(common.phred_to_top_percent(30.0), 0.1)

    def test_feature_display_names_cover_all_eighteen(self):
        self.assertEqual(len(common.AVI_FEATURES), 18)
        self.assertEqual(common.feature_display_name("MERGED_SPLICING"), "Splicing")
        self.assertEqual(common.feature_display_name("UNKNOWN_KEY"), "UNKNOWN_KEY")
        splicing_scorers = common.AVI_FEATURES["MERGED_SPLICING"][2]
        self.assertEqual(set(splicing_scorers), {"SPLICE_SITES", "SPLICE_SITE_USAGE", "SPLICE_JUNCTIONS"})


class ExportTests(unittest.TestCase):
    ROWS = [{"variant": "chr1:1:A>T", "score": 1.23456789, "note": None}, {"variant": "chr1:2:A>T", "score": float("nan")}]

    def test_tsv_to_stdout_orders_columns_by_first_appearance(self):
        out = io.StringIO()
        with redirect_stdout(out):
            common.write_rows(self.ROWS, None, "tsv")
        rows = rows_from_tsv(out.getvalue())
        self.assertEqual(list(rows[0]), ["variant", "score", "note"])
        self.assertEqual(rows[0]["score"], "1.23457")
        self.assertEqual(rows[1]["score"], "")

    def test_json_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            common.write_rows(self.ROWS, str(path), "json")
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data[0]["variant"], "chr1:1:A>T")
            self.assertIsNone(data[0]["note"])

    def test_format_follows_extension_then_flag(self):
        self.assertEqual(common.format_from_output("x.csv", None), "csv")
        self.assertEqual(common.format_from_output("x.parquet", None), "parquet")
        self.assertEqual(common.format_from_output("x.txt", None), "tsv")
        self.assertEqual(common.format_from_output("x.csv", "json"), "json")
        self.assertEqual(common.format_from_output(None, None), "tsv")

    def test_unknown_format_and_parquet_without_path_are_rejected(self):
        with self.assertRaises(ValueError):
            common.write_rows(self.ROWS, None, "xlsx")
        with self.assertRaises(ValueError):
            common.write_rows(self.ROWS, None, "parquet")


class ApiKeyTests(unittest.TestCase):
    def test_primary_then_fallback_spelling(self):
        with mock.patch.dict(os.environ, {"ALPHAGENOME_API_KEY": "primary", "ALPHA_GENOME_API_KEY": "fallback"}):
            self.assertEqual(common.load_api_key(), "primary")
        with mock.patch.dict(os.environ, {"ALPHA_GENOME_API_KEY": "fallback"}, clear=True):
            self.assertEqual(common.load_api_key(), "fallback")

    def test_explicit_variable_name(self):
        with mock.patch.dict(os.environ, {"MY_KEY": "abc"}, clear=True):
            self.assertEqual(common.load_api_key("MY_KEY"), "abc")

    def test_missing_key_exits_with_signup_url(self):
        with mock.patch.dict(os.environ, {}, clear=True), self.assertRaises(SystemExit) as caught:
            common.load_api_key()
        self.assertIn("deepmind.google.com/science/alphagenome", str(caught.exception))

    def test_portal_url_encodes_the_allele_separator(self):
        url = common.portal_variant_url("chr22:36201698:A>C")
        self.assertTrue(url.startswith(common.ATLAS_BASE_URL))
        self.assertIn("q=chr22:36201698:A%3EC", url)
        self.assertIn("m=variant", url)


# ---------------------------------------------------------------------------
# atlas_link.py (standard library only)
# ---------------------------------------------------------------------------


class AtlasLinkTests(unittest.TestCase):
    def test_variant_link_normalises_and_encodes(self):
        url = atlas_link.build_url("variant", "22-36201698-A-C")
        self.assertIn("q=chr22:36201698:A%3EC", url)
        self.assertIn("m=variant", url)
        self.assertIn("lItems=avi,section:RNA_SEQ,section:DNASE,section:CHIP_TF", url)

    def test_locus_link_keeps_one_based_closed_coordinates(self):
        url = atlas_link.build_url("locus", "11:5,225,727-5,226,575", modalities=("RNA_SEQ",))
        self.assertIn("q=chr11:5225727-5226575", url)
        self.assertIn("m=locus", url)
        self.assertIn("f=SCORER_MODALITY:RNA-seq", url)

    def test_gene_uses_entity_mode_and_motifs_take_zoom(self):
        self.assertIn("q=HBB&m=entity", atlas_link.build_url("gene", "HBB"))
        url = atlas_link.build_url("motifs", "chr11:5225727-5226575", zoom="chr11:5225800-5226000", include_avi=False)
        self.assertIn("m=motifs", url)
        self.assertIn("i=chr11:5225800-5226000", url)
        self.assertNotIn("avi", url.split("lItems=")[1].split("&")[0])

    def test_tf_filter_pulls_in_rna_seq_and_dnase(self):
        filter_string = atlas_link.build_filter(biosample="K562", modalities=("CHIP_TF",), tfs=("GATA1",))
        self.assertEqual(
            filter_string,
            "BIOSAMPLE_NAME:K562,SCORER_MODALITY:ChIP-TF,SCORER_MODALITY:RNA-seq,SCORER_MODALITY:DNase,ASSAY_TRANSCRIPTOR_FACTOR:GATA1",
        )
        self.assertIsNone(atlas_link.build_filter())

    def test_modalities_are_validated(self):
        self.assertEqual(atlas_link.parse_modalities("rna_seq, dnase"), ["RNA_SEQ", "DNASE"])
        with self.assertRaises(ValueError):
            atlas_link.parse_modalities("RNA_SEQ,WHATEVER")
        with self.assertRaises(ValueError):
            atlas_link.build_url("nonsense", "HBB")

    def test_cli_prints_url_or_markdown_and_rejects_rsids(self):
        code, out, _ = run_main(atlas_link, ["variant", "chr9:128225994:G>A", "--biosample", "K562", "--tf", "GATA1"])
        self.assertEqual(code, 0)
        self.assertIn("BIOSAMPLE_NAME:K562", out)
        code, out, _ = run_main(atlas_link, ["gene", "HBB", "--markdown"])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("[HBB on AlphaGenome Atlas](https://"))
        code, _, err = run_main(atlas_link, ["variant", "rs12345"])
        self.assertEqual(code, 1)
        self.assertIn("rsIDs are not supported", err)


# ---------------------------------------------------------------------------
# score_variants.py helpers
# ---------------------------------------------------------------------------


class SequenceLengthTests(unittest.TestCase):
    def test_names_and_integers(self):
        self.assertEqual(score_variants.parse_sequence_length("1MB"), 2**20)
        self.assertEqual(score_variants.parse_sequence_length("16kb"), 2**14)
        self.assertEqual(score_variants.parse_sequence_length("524288"), 2**19)
        with self.assertRaises(ValueError):
            score_variants.parse_sequence_length("2KB")

    @unittest.skipUnless(HAVE_SDK, "alphagenome not installed")
    def test_lengths_match_the_sdk_constants(self):
        from alphagenome.models import dna_client

        self.assertEqual(
            set(score_variants.SEQUENCE_LENGTHS.values()), set(dna_client.SUPPORTED_SEQUENCE_LENGTHS.values())
        )


@unittest.skipUnless(HAVE_SDK, "alphagenome not installed")
class ScorerSelectionTests(unittest.TestCase):
    def test_default_excludes_active_scorers(self):
        chosen = score_variants.select_scorers(None, "human")
        self.assertEqual(len(chosen), 12)
        self.assertTrue(all("ACTIVE" not in type(s).__name__.upper() or "GeneMaskActive" not in type(s).__name__ for s in chosen))
        self.assertEqual(len(score_variants.select_scorers(None, "human", include_active=True)), 19)

    def test_mouse_drops_polyadenylation(self):
        err = io.StringIO()
        with redirect_stderr(err):
            chosen = score_variants.select_scorers(None, "mouse")
        self.assertEqual(len(chosen), 11)
        self.assertIn("POLYADENYLATION", err.getvalue())

    def test_named_selection_and_unknown_names(self):
        chosen = score_variants.select_scorers(["RNA_SEQ", "SPLICE_SITE_USAGE", "RNA_SEQ"], "human")
        self.assertEqual([type(s).__name__ for s in chosen], ["GeneMaskLFCScorer", "GeneMaskSplicingScorer"])
        with self.assertRaises(ValueError) as caught:
            score_variants.select_scorers(["NOT_A_SCORER"], "human")
        self.assertIn("NOT_A_SCORER", str(caught.exception))

    def test_list_scorers_needs_no_network(self):
        code, out, _ = run_main(score_variants, ["--list-scorers"])
        self.assertEqual(code, 0)
        rows = rows_from_tsv(out)
        self.assertEqual(len(rows), 19)
        self.assertIn("RNA_SEQ", {row["name"] for row in rows})


# ---------------------------------------------------------------------------
# atlas_query.py against a fake Atlas client
# ---------------------------------------------------------------------------

if HAVE_SDK:
    FEATURE_KEYS = list(common.AVI_FEATURES)

    def _variant(text):
        return genome.Variant.from_str(text)

    def _avi_adata(variants, raws, cdfs):
        return anndata.AnnData(
            X=np.asarray(raws, dtype=np.float32).reshape(-1, 1),
            obs=pd.DataFrame({"variant": variants}, index=[str(i) for i in range(len(variants))]),
            var=pd.DataFrame({"name": ["AVI_SCORE"]}, index=["0"]),
            layers={"quantiles": np.asarray(cdfs, dtype=np.float32).reshape(-1, 1)},
        )

    def _fi_adata(variants, top_index):
        matrix = np.full((len(variants), 18), 0.01, dtype=np.float32)
        matrix[:, top_index] = 0.9
        return anndata.AnnData(
            X=matrix,
            obs=pd.DataFrame({"variant": variants}, index=[str(i) for i in range(len(variants))]),
            var=pd.DataFrame({"name": FEATURE_KEYS}, index=[str(i) for i in range(18)]),
        )

    TRACKS = pd.DataFrame(
        {
            "name": ["UBERON:0001114 polyA plus RNA-seq", "UBERON:0001157 polyA plus RNA-seq", "CL:0000084 total RNA-seq"],
            "strand": [".", ".", "."],
            "ontology_curie": ["UBERON:0001114", "UBERON:0001157", "CL:0000084"],
            "biosample_name": ["right lobe of liver", "transverse colon", "T cell"],
            "biosample_type": ["tissue", "tissue", "primary_cell"],
        },
        index=["0", "1", "2"],
    )

    def _rna_adata(variant):
        return anndata.AnnData(
            X=np.array([[0.05, -1.4, 0.2], [0.0, 0.3, -0.6]], dtype=np.float32),
            obs=pd.DataFrame(
                {"gene_id": ["ENSG0001", "ENSG0002"], "gene_name": ["HBB", "HBD"], "strand": ["-", "-"], "variant": [variant, variant]},
                index=["0", "1"],
            ),
            var=TRACKS.copy(),
            layers={"quantiles": np.array([[0.55, 0.002, 0.7], [0.5, 0.8, 0.03]], dtype=np.float32)},
        )

    class FakeAtlasClient:
        """Serves canned AnnData shaped like the live Atlas responses."""

        def __init__(self):
            self.calls = []

        def query_variant(self, variant, requested_scorers, **filters):
            self.calls.append(("variant", str(variant), tuple(requested_scorers), filters))
            if variant.position == 999:
                raise ValueError("variant not found in Atlas")
            out = {}
            if common.AVI_SCORER in requested_scorers:
                out[common.AVI_SCORER] = _avi_adata([variant], [2.5], [0.995])
            if common.AVI_FEATURES_SCORER in requested_scorers:
                out[common.AVI_FEATURES_SCORER] = _fi_adata([variant], FEATURE_KEYS.index("MAX_ABS_RNA_SEQ"))
            if "RNA_SEQ" in requested_scorers:
                out["RNA_SEQ"] = _rna_adata(variant)
            return out

        def query_interval(self, interval, requested_scorers, progress_bar=True, **filters):
            self.calls.append(("interval", str(interval), tuple(requested_scorers), filters))
            variants, raws, cdfs = [], [], []
            for offset in range(interval.width):
                for alt in "CGT":
                    variants.append(genome.Variant(interval.chromosome, interval.start + offset + 1, "A", alt))
                    raws.append(float(offset))
                    cdfs.append(0.5 + 0.49 * offset / max(1, interval.width - 1))
            out = {}
            if common.AVI_SCORER in requested_scorers:
                out[common.AVI_SCORER] = _avi_adata(variants, raws, cdfs)
            if common.AVI_FEATURES_SCORER in requested_scorers:
                out[common.AVI_FEATURES_SCORER] = _fi_adata(variants, FEATURE_KEYS.index("MERGED_SPLICING"))
            if "RNA_SEQ" in requested_scorers:
                out["RNA_SEQ"] = _rna_adata(variants[0])
            return out

        def scorer_metadata(self):
            return {
                "RNA_SEQ": SimpleNamespace(name="RNA_SEQ", is_signed=True, track_metadata=TRACKS.copy()),
                "AVI_SCORE": SimpleNamespace(name="AVI_SCORE", is_signed=False, track_metadata=pd.DataFrame()),
            }


@unittest.skipUnless(HAVE_SDK, "alphagenome not installed")
class AtlasConversionTests(unittest.TestCase):
    def test_summarize_avi_computes_phred_and_top_feature(self):
        variant = _variant("chr22:36201698:A>C")
        rows = atlas_query.summarize_avi(_avi_adata([variant], [2.5], [0.99]), _fi_adata([variant], FEATURE_KEYS.index("ALPHAMISSENSE")))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["variant"], "chr22:36201698:A>C")
        self.assertAlmostEqual(row["avi_raw"], 2.5, places=5)
        self.assertAlmostEqual(row["avi_phred"], 20.0, places=3)
        self.assertAlmostEqual(row["avi_top_percent"], 1.0, places=3)
        self.assertEqual(row["top_feature_key"], "ALPHAMISSENSE")
        self.assertEqual(row["top_feature"], "AlphaMissense")
        self.assertEqual(len([key for key in row if key.startswith("fi_")]), 18)
        self.assertIn("A%3EC", row["atlas_url"])

    def test_summarize_avi_without_attributions_or_quantiles(self):
        variant = _variant("chr1:5:A>T")
        adata = _avi_adata([variant], [0.1], [0.5])
        del adata.layers["quantiles"]
        rows = atlas_query.summarize_avi(adata, None)
        self.assertEqual(rows[0]["top_feature_key"], "")
        self.assertTrue(rows[0]["avi_phred"] != rows[0]["avi_phred"])  # NaN
        self.assertEqual(atlas_query.summarize_avi(None, None), [])

    def test_tidy_atlas_scores_is_one_row_per_gene_track(self):
        rows = atlas_query.tidy_atlas_scores({"RNA_SEQ": _rna_adata(_variant("chr11:5227002:T>A"))})
        self.assertEqual(len(rows), 6)
        strongest = min(rows, key=lambda row: row["raw_score"])
        self.assertEqual(strongest["gene_name"], "HBB")
        self.assertEqual(strongest["biosample_name"], "transverse colon")
        self.assertEqual(strongest["ontology_curie"], "UBERON:0001157")
        self.assertAlmostEqual(strongest["quantile_score"], 0.002, places=5)
        self.assertEqual(strongest["gene_strand"], "-")
        self.assertEqual(rows[0]["track_index"], 0)

    def test_max_abs_track_and_metadata_rows(self):
        hit = atlas_query.max_abs_track(_rna_adata(_variant("chr11:5227002:T>A")))
        self.assertAlmostEqual(hit["raw_score"], -1.4, places=5)
        self.assertEqual(hit["gene_name"], "HBB")
        metadata = FakeAtlasClient().scorer_metadata()
        scorers = atlas_query.scorer_rows(metadata)
        self.assertEqual([row["scorer"] for row in scorers], ["AVI_SCORE", "RNA_SEQ"])
        self.assertEqual(scorers[1]["n_tracks"], 3)
        self.assertEqual(scorers[1]["n_biosamples"], 3)
        tracks = atlas_query.track_rows(metadata, "RNA_SEQ", "colon")
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0]["ontology_curie"], "UBERON:0001157")
        self.assertEqual(len(atlas_query.track_rows(metadata, None, None)), 3)


@unittest.skipUnless(HAVE_SDK, "alphagenome not installed")
class AtlasQueryCliTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeAtlasClient()
        patcher = mock.patch.object(atlas_query, "make_client", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_avi_for_variants_writes_one_row_each_and_keeps_failures(self):
        out_path = Path(self.tmp.name) / "avi.tsv"
        code, _, err = run_main(
            atlas_query,
            ["avi", "--variant", "chr22:36201698:A>C", "chr1:999:A>T", "--workers", "1", "-o", str(out_path)],
        )
        self.assertEqual(code, 0)
        rows = rows_from_tsv(out_path.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 2)
        good = next(row for row in rows if row["variant"] == "chr22:36201698:A>C")
        self.assertAlmostEqual(float(good["avi_phred"]), 23.0103, places=3)
        self.assertEqual(good["top_feature_key"], "MAX_ABS_RNA_SEQ")
        self.assertEqual(good["error"], "")
        bad = next(row for row in rows if row["variant"] == "chr1:999:A>T")
        self.assertIn("not found", bad["error"])
        self.assertEqual(bad["avi_phred"], "")
        self.assertEqual(self.client.calls[0][2], common.AVI_SCORERS)

    def test_avi_from_vcf_warns_about_indels_and_filters_by_phred(self):
        out_path = Path(self.tmp.name) / "avi.json"
        code, _, err = run_main(
            atlas_query,
            ["avi", "--input", str(FIXTURES / "variants.vcf"), "--min-phred", "20", "--workers", "1", "-o", str(out_path)],
        )
        self.assertEqual(code, 0)
        self.assertIn("indel", err)
        rows = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["avi_phred"] >= 20 for row in rows))

    def test_avi_with_tracks_adds_the_strongest_track(self):
        code, out, _ = run_main(atlas_query, ["avi", "--variant", "chr22:36201698:A>C", "--with-tracks", "--format", "json"])
        self.assertEqual(code, 0)
        row = json.loads(out)[0]
        self.assertEqual(row["top_track_scorer"], "RNA_SEQ")
        self.assertEqual(row["top_track_biosample"], "transverse colon")
        self.assertEqual(row["top_track_gene"], "HBB")
        self.assertEqual(self.client.calls[1][2], ("RNA_SEQ",))

    def test_avi_interval_scans_three_variants_per_base_and_sorts(self):
        out_path = Path(self.tmp.name) / "window.tsv"
        code, _, _ = run_main(atlas_query, ["avi", "--interval", "chr11:5225727-5225736", "--top-k", "5", "-o", str(out_path)])
        self.assertEqual(code, 0)
        rows = rows_from_tsv(out_path.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 5)
        phreds = [float(row["avi_phred"]) for row in rows]
        self.assertEqual(phreds, sorted(phreds, reverse=True))
        self.assertEqual(self.client.calls[0][1], "chr11:5225726-5225736:.")

    def test_avi_interval_refuses_wide_windows_and_large_stdout(self):
        with self.assertRaises(SystemExit) as caught:
            run_main(atlas_query, ["avi", "--interval", "chr11:1-5000"])
        self.assertIn("--max-window", str(caught.exception))
        with self.assertRaises(SystemExit) as caught:
            run_main(atlas_query, ["avi", "--interval", "chr11:1-40"])
        self.assertIn("-o FILE", str(caught.exception))
        code, out, _ = run_main(atlas_query, ["avi", "--interval", "chr11:1-40", "--force-stdout"])
        self.assertEqual(code, 0)
        self.assertEqual(len(rows_from_tsv(out)), 120)

    def test_avi_without_inputs_exits(self):
        with self.assertRaises(SystemExit):
            run_main(atlas_query, ["avi"])

    def test_scores_forwards_filters_and_flattens(self):
        out_path = Path(self.tmp.name) / "scores.csv"
        code, _, _ = run_main(
            atlas_query,
            [
                "scores", "--variant", "chr11:5227002:T>A", "--scorers", "RNA_SEQ",
                "--ontology", "UBERON:0001157", "--gene", "HBB", "--workers", "1", "-o", str(out_path),
            ],
        )
        self.assertEqual(code, 0)
        filters = self.client.calls[0][3]
        self.assertEqual(filters["ontology_terms"], ["UBERON:0001157"])
        self.assertEqual(filters["gene_names"], ["HBB"])
        text = out_path.read_text(encoding="utf-8")
        self.assertEqual(len(text.strip().splitlines()), 7)  # header + 2 genes x 3 tracks
        self.assertIn("quantile_score", text.splitlines()[0])

    def test_scores_min_abs_quantile_keeps_tails(self):
        code, out, _ = run_main(
            atlas_query,
            ["scores", "--variant", "chr11:5227002:T>A", "--scorers", "RNA_SEQ", "--min-abs-quantile", "0.9", "--workers", "1"],
        )
        self.assertEqual(code, 0)
        rows = rows_from_tsv(out)
        self.assertEqual({row["quantile_score"] for row in rows}, {"0.002", "0.03"})

    def test_scorers_and_tracks_subcommands(self):
        code, out, _ = run_main(atlas_query, ["scorers"])
        self.assertEqual(code, 0)
        self.assertEqual([row["scorer"] for row in rows_from_tsv(out)], ["AVI_SCORE", "RNA_SEQ"])
        code, out, _ = run_main(atlas_query, ["tracks", "--query", "t cell", "--format", "json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)[0]["ontology_curie"], "CL:0000084")


if __name__ == "__main__":
    unittest.main()
