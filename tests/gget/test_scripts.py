"""Tests for the gget workflow scripts.

Every gget module in these scripts is a network call, so all three suites patch
the gget function with `autospec=True` and assert on the call that *would* have
gone out. `autospec` is load-bearing rather than decoration: it binds each
recorded call against the installed gget signature, so a script that passes an
argument gget no longer accepts fails here instead of failing in the field --
which is how `f.write(gget.muscle(...))` (muscle returns None) and
`f.write(gget.seq(...))` (seq returns a list) were caught.

The rest is the logic the scripts own: FASTA and gene-list parsing, the
per-database enrichment sweep, the deliberate five-gene cap on expression
lookups, and the resilience contract -- one service failing must not abort the
run, but an empty gene search must stop it before any further request is made.
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "gget"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

pd = pytest.importorskip("pandas", reason="gget scripts need pandas")
gget = pytest.importorskip("gget", reason="gget skill needs gget")

import batch_sequence_analysis as batch  # noqa: E402
import enrichment_pipeline as pipeline  # noqa: E402
import gene_analysis  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


#: Every gget module these scripts reach for. All of them are network calls.
GGET_MODULES = (
    "blast", "muscle", "enrichr", "archs4", "search", "info", "seq",
    "opentargets", "alphafold",
)


class WorkingDirectoryTestCase(unittest.TestCase):
    """The scripts write output relative to the working directory."""

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)
        previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, previous)

        # Every gget module is replaced up front, with `autospec` so each
        # recorded call is bound against the installed gget signature. The
        # default side effect is a blanket guard: a module a test forgot to
        # arrange raises instead of quietly querying Ensembl, NCBI, Enrichr or
        # ARCHS4 for real.
        self._modules = {}
        for name in GGET_MODULES:
            patcher = patch.object(gget, name, autospec=True)
            mock = patcher.start()
            self.addCleanup(patcher.stop)
            mock.side_effect = AssertionError(
                f"gget.{name} was called without being stubbed"
            )
            self._modules[name] = mock

    def stub(self, name: str, **kwargs):
        """Arrange the already-installed mock for one gget module."""
        mock = self._modules[name]
        # Clears the blanket guard installed in setUp. Call history needs no
        # reset: every test gets its own patchers.
        mock.side_effect = kwargs.pop("side_effect", None)
        if "return_value" in kwargs:
            mock.return_value = kwargs.pop("return_value")
        self.assertEqual(kwargs, {}, "unsupported stub arguments")
        return mock

    def quietly(self, function, *args, **kwargs):
        """Run a chatty workflow function, swallowing its progress output."""
        with redirect_stdout(io.StringIO()):
            return function(*args, **kwargs)


def blast_frame(description: str = "hypothetical protein") -> pd.DataFrame:
    """A BLAST result shaped like gget.blast returns."""
    return pd.DataFrame(
        [{"Description": description, "Max Score": 300, "Query Coverage": "98%"}]
    )


class FastaReadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)

    def read(self, text: str):
        path = self.root / "sequences.fasta"
        path.write_text(text, encoding="utf-8")
        return batch.read_fasta(path)

    def test_wrapped_sequence_lines_are_joined(self) -> None:
        # FASTA wraps at 60-80 columns; keeping the newlines would corrupt
        # every downstream BLAST query.
        records = self.read(">seq1\nMKVL\nAAPG\n")
        self.assertEqual(records, [{"id": "seq1", "seq": "MKVLAAPG"}])

    def test_the_final_record_is_not_dropped(self) -> None:
        # The loop flushes on the next '>', so the last record needs the
        # explicit flush after the file ends.
        records = self.read(">a\nMK\n>b\nVL\n>c\nAA\n")
        self.assertEqual([r["id"] for r in records], ["a", "b", "c"])
        self.assertEqual(records[-1]["seq"], "AA")

    def test_the_identifier_excludes_the_angle_bracket(self) -> None:
        records = self.read(">sp|P12345| my protein\nMK\n")
        self.assertEqual(records[0]["id"], "sp|P12345| my protein")

    def test_an_empty_file_yields_no_records(self) -> None:
        self.assertEqual(self.read(""), [])

    def test_a_header_with_no_sequence_is_still_a_record(self) -> None:
        # Dropping it would silently renumber every later sequence.
        records = self.read(">empty\n>next\nMK\n")
        self.assertEqual(records[0], {"id": "empty", "seq": ""})
        self.assertEqual(len(records), 2)

    def test_a_missing_trailing_newline_is_tolerated(self) -> None:
        self.assertEqual(self.read(">a\nMK")[0]["seq"], "MK")


class BatchSequenceAnalysisTests(WorkingDirectoryTestCase):
    def fasta(self, records: int = 2) -> Path:
        path = self.root / "input.fasta"
        path.write_text(
            "".join(f">seq{i}\nMKVL{i}\n" for i in range(records)), encoding="utf-8"
        )
        return path

    def test_each_sequence_is_blasted_once_with_the_documented_parameters(self) -> None:
        blast = self.stub("blast", return_value=blast_frame())
        self.stub("muscle")
        self.quietly(
            batch.analyze_sequences,
            self.fasta(2),
            blast_db="swissprot",
            output_dir=str(self.root / "out"),
        )
        self.assertEqual(blast.call_count, 2)
        sequences = [call.args[0] for call in blast.call_args_list]
        self.assertEqual(sequences, ["MKVL0", "MKVL1"])
        for call in blast.call_args_list:
            # save=False keeps gget from writing files of its own next to the
            # script; limit=10 is what the reported "top hit" assumes.
            self.assertEqual(call.kwargs["database"], "swissprot")
            self.assertEqual(call.kwargs["limit"], 10)
            self.assertIs(call.kwargs["save"], False)

    def test_one_csv_is_written_per_sequence_named_after_it(self) -> None:
        self.stub("blast", return_value=blast_frame("kinase domain"))
        self.stub("muscle")
        output = self.root / "out"
        self.quietly(batch.analyze_sequences, self.fasta(2), output_dir=str(output))
        written = sorted(path.name for path in output.glob("*_blast.csv"))
        self.assertEqual(written, ["seq0_blast.csv", "seq1_blast.csv"])
        table = pd.read_csv(output / "seq0_blast.csv")
        self.assertEqual(table.loc[0, "Description"], "kinase domain")

    def test_a_failed_blast_does_not_abort_the_remaining_sequences(self) -> None:
        # A batch run that dies on sequence 1 of 50 is useless.
        blast = self.stub(
            "blast",
            side_effect=[RuntimeError("NCBI timed out"), blast_frame()],
        )
        self.stub("muscle")
        output = self.root / "out"
        self.quietly(batch.analyze_sequences, self.fasta(2), output_dir=str(output))
        self.assertEqual(blast.call_count, 2)
        self.assertFalse((output / "seq0_blast.csv").exists())
        self.assertTrue((output / "seq1_blast.csv").exists())

    def test_headers_cannot_escape_output_or_overwrite_duplicate_records(self):
        self.stub("blast", return_value=blast_frame())
        self.stub("muscle")
        fasta = self.root / "unsafe.fasta"
        fasta.write_text(">../escaped\nMKK\n>../escaped\nMKK\n>/tmp/absolute\nMKK\n")
        out = self.root / "out"
        self.quietly(batch.analyze_sequences, fasta, output_dir=str(out))
        self.assertEqual(len(list(out.glob("*_blast.csv"))), 3)
        self.assertFalse((self.root / "escaped_blast.csv").exists())

    def test_default_database_is_selected_by_gget(self):
        blast = self.stub("blast", return_value=blast_frame())
        self.quietly(batch.analyze_sequences, self.fasta(1), align=False,
                     output_dir=str(self.root / "out"))
        self.assertEqual(blast.call_args.kwargs["database"], "default")

    def test_alignment_asks_gget_to_write_the_file(self) -> None:
        # gget.muscle returns None, so the alignment must be requested via
        # `out=`; writing the return value would raise TypeError.
        self.stub("blast", return_value=blast_frame())
        muscle = self.stub("muscle")
        output = self.root / "out"
        self.quietly(batch.analyze_sequences, self.fasta(2), output_dir=str(output))
        muscle.assert_called_once()
        self.assertEqual(
            muscle.call_args.kwargs["out"], str(output / "alignment.afa")
        )

    def test_a_single_sequence_is_not_aligned(self) -> None:
        # An alignment of one sequence is meaningless and wastes a request.
        self.stub("blast", return_value=blast_frame())
        muscle = self.stub("muscle")
        self.quietly(
            batch.analyze_sequences, self.fasta(1), output_dir=str(self.root / "out")
        )
        muscle.assert_not_called()

    def test_alignment_can_be_switched_off(self) -> None:
        self.stub("blast", return_value=blast_frame())
        muscle = self.stub("muscle")
        self.quietly(
            batch.analyze_sequences,
            self.fasta(3),
            align=False,
            output_dir=str(self.root / "out"),
        )
        muscle.assert_not_called()

    def test_structure_prediction_stays_a_no_op_even_when_requested(self) -> None:
        # The AlphaFold call is commented out on purpose (it needs `gget setup
        # alphafold` and hours of compute); the flag must not silently start it.
        self.stub("blast", return_value=blast_frame())
        self.stub("muscle")
        alphafold = self.stub("alphafold")
        self.quietly(
            batch.analyze_sequences,
            self.fasta(2),
            predict_structure=True,
            output_dir=str(self.root / "out"),
        )
        alphafold.assert_not_called()

    def test_an_empty_fasta_file_runs_no_queries(self) -> None:
        (self.root / "empty.fasta").write_text("", encoding="utf-8")
        blast = self.stub("blast")
        muscle = self.stub("muscle")
        self.quietly(
            batch.analyze_sequences,
            self.root / "empty.fasta",
            output_dir=str(self.root / "out"),
        )
        blast.assert_not_called()
        muscle.assert_not_called()


class GeneListReadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)

    def write(self, name: str, text: str) -> Path:
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_a_plain_list_drops_blank_lines_and_whitespace(self) -> None:
        path = self.write("genes.txt", "TP53\n\n  BRCA1  \n\n")
        self.assertEqual(pipeline.read_gene_list(path), ["TP53", "BRCA1"])

    def test_a_csv_takes_the_first_column_and_skips_the_header(self) -> None:
        # The header row must not become a gene symbol.
        path = self.write("genes.csv", "gene,logFC\nTP53,2.1\nBRCA1,-1.4\n")
        self.assertEqual(pipeline.read_gene_list(path), ["TP53", "BRCA1"])

    def test_a_csv_read_as_text_would_keep_the_commas(self) -> None:
        # Guards the suffix check: the same content named .txt is not a CSV.
        path = self.write("genes.txt", "gene,logFC\nTP53,2.1\n")
        self.assertEqual(pipeline.read_gene_list(path), ["gene,logFC", "TP53,2.1"])

    def test_an_empty_list_file_yields_no_genes(self) -> None:
        self.assertEqual(pipeline.read_gene_list(self.write("none.txt", "\n\n")), [])


def enrichr_frame(term: str = "p53 signaling pathway") -> pd.DataFrame:
    """An enrichment table shaped like gget.enrichr returns."""
    return pd.DataFrame(
        [
            {"path_name": term, "adj_p_val": 1e-8},
            {"path_name": "apoptosis", "adj_p_val": 0.002},
        ]
    )


def archs4_frame() -> pd.DataFrame:
    """A tissue-expression table; 'lung' is the clear maximum."""
    return pd.DataFrame(
        [
            {"id": "liver", "median": 3.5},
            {"id": "lung", "median": 9.25},
            {"id": "kidney", "median": 1.0},
        ]
    )


class EnrichmentPipelineTests(WorkingDirectoryTestCase):
    #: The five Enrichr categories the script sweeps, in order.
    DATABASES = ["pathway", "ontology", "transcription", "diseases_drugs", "celltypes"]
    LIBRARIES = ["KEGG_2021_Human", "GO_Biological_Process_2021", "ChEA_2016", "GWAS_Catalog_2019", "PanglaoDB_Augmented_2021"]

    def test_pipeline_consumes_installed_enrichr_adapter_response(self):
        # Exercise the installed adapter's normalization, not a hand-written
        # DataFrame mock that could silently invent nonexistent field names.
        import importlib
        import json
        from types import SimpleNamespace

        adapter = importlib.import_module("gget.gget_enrichr")
        added = SimpleNamespace(ok=True, json=lambda: {"userListId": 123})

        def enrichment_response(url, params, **kwargs):
            row = [1, "DNA repair", 0.001, 2.0, 12.0, ["TP53"], 0.02, 0, 0]
            return SimpleNamespace(ok=True, text=json.dumps({params["backgroundType"]: [row]}))

        self.stub("archs4", return_value=archs4_frame())
        with patch.object(gget, "enrichr", adapter.enrichr), \
             patch.object(adapter.requests, "post", return_value=added), \
             patch.object(adapter.requests, "get", side_effect=enrichment_response):
            self.assertTrue(self.quietly(pipeline.enrichment_pipeline, ["TP53"],
                                        output_prefix="actual", plot=False))
        result = pd.read_csv(self.root / "actual_summary.csv")
        self.assertEqual(result.iloc[0]["Top Term"], "DNA repair")
        self.assertEqual(result.iloc[0]["Top Adjusted P-value"], 0.02)

    def test_failed_sweep_is_not_reported_as_success(self):
        self.stub("enrichr", side_effect=RuntimeError("service unavailable"))
        self.stub("archs4", return_value=archs4_frame())
        self.assertFalse(self.quietly(pipeline.enrichment_pipeline, ["TP53"], plot=False))

    def test_nonhuman_libraries_require_explicit_names_and_skip_archs4(self):
        enrichr = self.stub("enrichr", return_value=enrichr_frame())
        with self.assertRaisesRegex(ValueError, "species-specific"):
            self.quietly(pipeline.enrichment_pipeline, ["gene"], species="fly")
        self.quietly(pipeline.enrichment_pipeline, ["gene"], species="fly",
                     databases=["Example_Fly_Library"], plot=False)
        self.assertEqual(enrichr.call_args.kwargs["database"], "Example_Fly_Library")
        self._modules["archs4"].assert_not_called()

    def test_mouse_expression_keeps_mouse_species(self):
        self.stub("enrichr", return_value=enrichr_frame())
        archs4 = self.stub("archs4", return_value=archs4_frame())
        self.quietly(pipeline.enrichment_pipeline, ["Trp53"], species="mouse")
        self.assertEqual(archs4.call_args.kwargs["species"], "mouse")

    def test_summary_preserves_library_name_and_adjusted_p_value(self):
        self.stub("enrichr", return_value=enrichr_frame())
        self.stub("archs4", return_value=archs4_frame())
        self.quietly(pipeline.enrichment_pipeline, ["TP53"], output_prefix="run")
        result = pd.read_csv(self.root / "run_summary.csv")
        self.assertEqual(result.iloc[0]["Database"], "KEGG_2021_Human")
        self.assertEqual(result.iloc[0]["Top Adjusted P-value"], 1e-8)

    def test_every_documented_database_is_queried_once_in_order(self) -> None:
        enrichr = self.stub("enrichr", return_value=enrichr_frame())
        self.stub("archs4", return_value=archs4_frame())
        self.quietly(pipeline.enrichment_pipeline, ["TP53"], output_prefix="run")
        self.assertEqual(
            [call.kwargs["database"] for call in enrichr.call_args_list],
            self.LIBRARIES,
        )

    def test_species_background_and_plotting_are_forwarded(self) -> None:
        enrichr = self.stub("enrichr", return_value=enrichr_frame())
        self.stub("archs4", return_value=archs4_frame())
        self.quietly(
            pipeline.enrichment_pipeline,
            ["TP53", "BRCA1"],
            species="mouse",
            background=["ACTB"],
            output_prefix="run",
            plot=False,
        )
        for call in enrichr.call_args_list:
            self.assertEqual(call.args[0], ["TP53", "BRCA1"])
            self.assertEqual(call.kwargs["species"], "mouse")
            self.assertEqual(call.kwargs["background_list"], ["ACTB"])
            self.assertIs(call.kwargs["plot"], False)

    def test_one_csv_per_database_plus_a_summary_is_written(self) -> None:
        self.stub("enrichr", return_value=enrichr_frame())
        self.stub("archs4", return_value=archs4_frame())
        self.quietly(pipeline.enrichment_pipeline, ["TP53"], output_prefix="run")
        for database in self.DATABASES:
            with self.subTest(database=database):
                self.assertTrue((self.root / f"run_{database}.csv").is_file())
        summary = pd.read_csv(self.root / "run_summary.csv")
        self.assertEqual(len(summary), len(self.DATABASES))
        self.assertEqual(summary.loc[0, "Top Term"], "p53 signaling pathway")
        self.assertEqual(summary.loc[0, "Total Terms"], 2)

    def test_a_database_with_no_hits_is_left_out_of_the_summary(self) -> None:
        # Reporting an empty category as a result would overstate the analysis.
        self.stub(
            "enrichr",
            side_effect=[enrichr_frame(), pd.DataFrame(), None,
                         enrichr_frame(), enrichr_frame()],
        )
        self.stub("archs4", return_value=archs4_frame())
        self.quietly(pipeline.enrichment_pipeline, ["TP53"], output_prefix="run")
        summary = pd.read_csv(self.root / "run_summary.csv")
        self.assertEqual(len(summary), 3)
        self.assertFalse((self.root / "run_ontology.csv").exists())

    def test_a_failing_database_does_not_stop_the_sweep(self) -> None:
        enrichr = self.stub(
            "enrichr",
            side_effect=[
                RuntimeError("Enrichr is down"),
                enrichr_frame(),
                enrichr_frame(),
                enrichr_frame(),
                enrichr_frame(),
            ],
        )
        self.stub("archs4", return_value=archs4_frame())
        self.quietly(pipeline.enrichment_pipeline, ["TP53"], output_prefix="run")
        self.assertEqual(enrichr.call_count, 5)
        summary = pd.read_csv(self.root / "run_summary.csv")
        self.assertEqual(len(summary), 4)

    def test_expression_lookups_are_capped_at_five_genes(self) -> None:
        # One ARCHS4 request per gene would make a 2,000-gene list unusable.
        self.stub("enrichr", return_value=enrichr_frame())
        archs4 = self.stub("archs4", return_value=archs4_frame())
        genes = [f"GENE{i}" for i in range(9)]
        self.quietly(pipeline.enrichment_pipeline, genes, output_prefix="run")
        self.assertEqual(archs4.call_count, 5)
        self.assertEqual(
            [call.args[0] for call in archs4.call_args_list], genes[:5]
        )
        for call in archs4.call_args_list:
            self.assertEqual(call.kwargs["which"], "tissue")

    def test_the_top_tissue_is_the_one_with_the_highest_median(self) -> None:
        self.stub("enrichr", return_value=enrichr_frame())
        self.stub("archs4", return_value=archs4_frame())
        self.quietly(pipeline.enrichment_pipeline, ["TP53"], output_prefix="run")
        expression = pd.read_csv(self.root / "run_expression.csv")
        self.assertEqual(expression.loc[0, "Gene"], "TP53")
        self.assertEqual(expression.loc[0, "Top Tissue"], "lung")
        self.assertEqual(expression.loc[0, "Median Expression"], 9.25)

    def test_an_expression_failure_leaves_the_enrichment_results_intact(self) -> None:
        self.stub("enrichr", return_value=enrichr_frame())
        self.stub("archs4", side_effect=RuntimeError("ARCHS4 is down"))
        self.assertTrue(
            self.quietly(pipeline.enrichment_pipeline, ["TP53"], output_prefix="run")
        )
        self.assertTrue((self.root / "run_summary.csv").is_file())
        self.assertFalse((self.root / "run_expression.csv").exists())


def search_frame(ensembl_id: str = "ENSG00000141510") -> pd.DataFrame:
    """A gget.search result for TP53."""
    return pd.DataFrame(
        [
            {
                "ensembl_id": ensembl_id,
                "ensembl_description": "tumor protein p53",
                "gene_name": "TP53",
            }
        ]
    )


def info_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [{"uniprot_id": "P04637", "pdb_id": ["1TUP"], "primary_gene_name": "TP53", "ensembl_gene_name": "TP53"}],
        index=["ENSG00000141510"]
    )


def correlation_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [{"gene_symbol": "MDM2", "pearson_correlation": 0.81}]
    )


def diseases_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [{"disease.name": "Li-Fraumeni syndrome", "score": 0.9}]
    )


class GeneAnalysisTests(WorkingDirectoryTestCase):
    def stub_everything(self) -> dict:
        return {
            "search": self.stub("search", return_value=search_frame()),
            "info": self.stub("info", return_value=info_frame()),
            "seq": self.stub("seq", return_value=[">ENSG00000141510", "ATGGAG"]),
            "archs4": self.stub(
                "archs4", side_effect=[archs4_frame(), correlation_frame()]
            ),
            "opentargets": self.stub(
                "opentargets", side_effect=[diseases_frame(), pd.DataFrame()]
            ),
        }

    def test_exact_symbol_is_selected_after_unrelated_substring_hits(self):
        self.stub_everything()
        wrong = search_frame("ENSG00000000001")
        wrong["gene_name"] = "TP53BP1"
        self.stub("search", return_value=pd.concat([wrong, search_frame()], ignore_index=True))
        self.quietly(gene_analysis.analyze_gene, "TP53")
        self.assertEqual(self._modules["info"].call_args.args[0], ["ENSG00000141510"])

    def test_ambiguous_exact_symbol_is_rejected(self):
        self.stub("search", return_value=pd.concat([search_frame(), search_frame("OTHER")]))
        self.assertFalse(self.quietly(gene_analysis.analyze_gene, "TP53"))
        self._modules["info"].assert_not_called()

    def test_current_service_fields_are_displayed_without_warning(self):
        self.stub_everything()
        output = io.StringIO()
        with redirect_stdout(output):
            gene_analysis.analyze_gene("TP53")
        self.assertIn("MDM2: r = 0.810", output.getvalue())
        self.assertIn("Li-Fraumeni syndrome: score = 0.900", output.getvalue())
        self.assertNotIn("Warning:", output.getvalue())
        info = pd.read_csv(self.root / "tp53_info.csv")
        self.assertEqual(info.loc[0, "query_ensembl_id"], "ENSG00000141510")

    def test_mouse_queries_do_not_use_human_association_or_correlation_services(self):
        self.stub_everything()
        found = search_frame("ENSMUSG00000059552")
        found["gene_name"] = "Trp53"
        self.stub("search", return_value=found)
        archs4 = self.stub("archs4", return_value=archs4_frame())
        self.quietly(gene_analysis.analyze_gene, "Trp53", species="mus_musculus")
        archs4.assert_called_once_with("Trp53", which="tissue", species="mouse")
        self._modules["opentargets"].assert_not_called()

    def test_the_search_is_scoped_to_species_without_truncating_exact_match_candidates(self) -> None:
        stubs = self.stub_everything()
        self.assertTrue(
            self.quietly(gene_analysis.analyze_gene, "TP53", "homo_sapiens")
        )
        stubs["search"].assert_called_once()
        call = stubs["search"].call_args
        self.assertEqual(call.args[0], ["TP53"])
        self.assertEqual(call.kwargs["species"], "homo_sapiens")
        self.assertNotIn("limit", call.kwargs)

    def test_a_gene_that_does_not_exist_stops_before_any_other_request(self) -> None:
        # Without the early return the Ensembl ID lookup would index an empty
        # frame and raise instead of reporting "not found".
        search = self.stub("search", return_value=pd.DataFrame())
        info = self.stub("info")
        self.assertFalse(
            self.quietly(gene_analysis.analyze_gene, "NOT_A_GENE", "homo_sapiens")
        )
        search.assert_called_once()
        info.assert_not_called()

    def test_the_ensembl_identifier_from_the_search_drives_every_lookup(self) -> None:
        stubs = self.stub_everything()
        self.quietly(gene_analysis.analyze_gene, "TP53")
        self.assertEqual(stubs["info"].call_args.args[0], ["ENSG00000141510"])
        self.assertIs(stubs["info"].call_args.kwargs["pdb"], True)
        for call in stubs["opentargets"].call_args_list:
            self.assertEqual(call.args[0], "ENSG00000141510")

    def test_both_sequence_forms_are_requested(self) -> None:
        stubs = self.stub_everything()
        self.quietly(gene_analysis.analyze_gene, "TP53")
        self.assertEqual(stubs["seq"].call_count, 2)
        translated = [
            call.kwargs.get("translate", False) for call in stubs["seq"].call_args_list
        ]
        self.assertEqual(translated, [False, True])

    def test_the_fasta_files_hold_the_lines_gget_returned(self) -> None:
        # gget.seq returns a list of FASTA lines; writing the list itself
        # raises TypeError, so the join is what makes the file valid.
        self.stub_everything()
        self.quietly(gene_analysis.analyze_gene, "TP53")
        text = (self.root / "tp53_nucleotide.fasta").read_text(encoding="utf-8")
        self.assertEqual(text, ">ENSG00000141510\nATGGAG\n")

    def test_missing_sequences_do_not_create_empty_fasta_outputs(self):
        self.stub_everything()
        self.stub("seq", return_value=None)
        self.assertFalse(self.quietly(gene_analysis.analyze_gene, "TP53"))
        self.assertFalse((self.root / "tp53_nucleotide.fasta").exists())
        self._modules["archs4"].assert_not_called()

    def test_an_already_joined_string_is_written_unchanged(self) -> None:
        # Older gget releases returned one string; both shapes must work.
        self.assertEqual(
            gene_analysis.fasta_text(">x\nATG\n"), ">x\nATG\n"
        )
        self.assertEqual(gene_analysis.fasta_text(">x\nATG"), ">x\nATG\n")
        self.assertEqual(gene_analysis.fasta_text(None), "")

    def test_the_output_prefix_defaults_to_the_lowercased_gene(self) -> None:
        self.stub_everything()
        self.quietly(gene_analysis.analyze_gene, "TP53")
        self.assertTrue((self.root / "tp53_info.csv").is_file())

    def test_an_explicit_prefix_is_used_verbatim(self) -> None:
        self.stub_everything()
        self.quietly(gene_analysis.analyze_gene, "TP53", output_prefix="run1")
        self.assertTrue((self.root / "run1_info.csv").is_file())

    def test_expression_and_correlation_are_separate_archs4_queries(self) -> None:
        stubs = self.stub_everything()
        self.quietly(gene_analysis.analyze_gene, "TP53")
        self.assertEqual(
            [call.kwargs["which"] for call in stubs["archs4"].call_args_list],
            ["tissue", "correlation"],
        )

    def test_both_opentargets_resources_are_requested_with_a_limit(self) -> None:
        stubs = self.stub_everything()
        self.quietly(gene_analysis.analyze_gene, "TP53")
        self.assertEqual(
            [call.kwargs["resource"] for call in stubs["opentargets"].call_args_list],
            ["diseases", "drugs"],
        )
        for call in stubs["opentargets"].call_args_list:
            self.assertEqual(call.kwargs["limit"], 10)

    def test_an_empty_drug_table_is_not_written(self) -> None:
        self.stub_everything()  # drugs is an empty frame
        self.quietly(gene_analysis.analyze_gene, "TP53")
        self.assertTrue((self.root / "tp53_diseases.csv").is_file())
        self.assertFalse((self.root / "tp53_drugs.csv").exists())

    def test_optional_lookups_may_fail_without_failing_the_run(self) -> None:
        # Steps 4-7 are wrapped in warnings on purpose: the sequences and
        # annotations already retrieved are worth keeping.
        self.stub("search", return_value=search_frame())
        self.stub("info", return_value=info_frame())
        self.stub("seq", return_value=[">x", "ATG"])
        self.stub("archs4", side_effect=RuntimeError("ARCHS4 is down"))
        self.stub("opentargets", side_effect=RuntimeError("Open Targets is down"))
        self.assertTrue(self.quietly(gene_analysis.analyze_gene, "TP53"))
        self.assertTrue((self.root / "tp53_nucleotide.fasta").is_file())
        self.assertFalse((self.root / "tp53_tissue_expression.csv").exists())


if __name__ == "__main__":
    unittest.main()
