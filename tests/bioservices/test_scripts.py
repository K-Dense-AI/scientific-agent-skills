"""Tests for the BioServices cross-database workflow scripts.

BioServices *is* the network, so every service class is replaced here and the
tests assert on the request that would have been issued and on the parsing of a
canned response. Nothing in this file opens a connection.

The parsers are where these scripts can be quietly wrong, so the fixtures are
real records with published values: the KEGG flat file for ATP (C00002) carries
formula C10H16N5O13P3, exact mass 506.9957 and ChEBI 15422, and the parser must
pull exactly those out -- and must not mistake the indented DBLINKS lines that
follow the PATHWAY block for pathways.

The rest of the coverage is the batch machinery: chunking a large identifier
list into requests of the requested size, retrying a failed chunk one identifier
at a time, marking everything that never came back as failed, and writing a CSV
whose Unmapped and Failed rows distinguish absent mappings from service errors. Alias normalisation is tested
in both directions -- an alias must resolve and an already-official code must
survive untouched.
"""

from __future__ import annotations

import csv
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "bioservices"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("bioservices", reason="bioservices skill needs bioservices")

import batch_id_converter as converter  # noqa: E402
import compound_cross_reference as compound  # noqa: E402
import pathway_analysis as pathways  # noqa: E402
import protein_analysis_workflow as workflow  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

# KEGG's flat file for ATP, trimmed to the fields the parser reads. Field names
# start in column 1; continuation lines are indented 12 spaces.
ATP_ENTRY = """\
ENTRY       C00002                      Compound
NAME        ATP;
            Adenosine 5'-triphosphate
FORMULA     C10H16N5O13P3
EXACT_MASS  506.9957
MOL_WEIGHT  507.181
REACTION    R00002 R00076
PATHWAY     map00190  Oxidative phosphorylation
            map00230  Purine metabolism
            map00730  Thiamine metabolism
ENZYME      1.1.98.6        1.2.1.101
DBLINKS     CAS: 56-65-5
            PubChem: 3304
            ChEBI: 15422
            KNApSAcK: C00001491
            PDB-CCD: ATP
ATOM        31
///
"""


def quietly(function, *args, **kwargs):
    """Run one of these very chatty functions without its progress output."""
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


class DatabaseCodeTests(unittest.TestCase):
    """Aliases must resolve, and official codes must pass through untouched."""

    def test_lowercase_aliases_resolve_to_the_official_code(self) -> None:
        self.assertEqual(converter.normalize_database_code("uniprot"), "UniProtKB_AC-ID")
        self.assertEqual(converter.normalize_database_code("entrez"), "GeneID")
        self.assertEqual(converter.normalize_database_code("refseq"), "RefSeq_Protein")

    def test_aliases_are_matched_case_insensitively(self) -> None:
        self.assertEqual(converter.normalize_database_code("UniProt"), "UniProtKB_AC-ID")
        self.assertEqual(converter.normalize_database_code("ENSEMBL"), "Ensembl")

    def test_an_official_code_survives_normalisation(self) -> None:
        # Rewriting a valid code would break the mapping request.
        for code in ("UniProtKB_AC-ID", "Ensembl_Protein", "RefSeq_Protein", "GO"):
            with self.subTest(code=code):
                self.assertEqual(converter.normalize_database_code(code), code)

    def test_every_alias_maps_to_a_code_that_is_itself_stable(self) -> None:
        # Normalisation must be idempotent, or a second pass would corrupt it.
        for alias, code in converter.DATABASE_CODES.items():
            with self.subTest(alias=alias):
                self.assertEqual(converter.normalize_database_code(code), code)

    def test_an_unknown_code_is_passed_through_rather_than_rejected(self) -> None:
        # UniProt supports far more codes than the alias table lists.
        self.assertEqual(converter.normalize_database_code("Ensembl_Genomes"),
                         "Ensembl_Genomes")


class IdentifierFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)

    def read(self, text: str):
        path = self.root / "ids.txt"
        path.write_text(text, encoding="utf-8")
        return quietly(converter.read_ids_from_file, path)

    def test_identifiers_are_read_one_per_line_and_trimmed(self) -> None:
        self.assertEqual(self.read("P43403\n  P04637  \n"), ["P43403", "P04637"])

    def test_comments_and_blank_lines_are_ignored(self) -> None:
        self.assertEqual(
            self.read("# kinases\nP43403\n\n#P00000\nP04637\n"),
            ["P43403", "P04637"],
        )

    def test_an_empty_file_yields_no_identifiers(self) -> None:
        self.assertEqual(self.read("\n\n"), [])

    def test_a_missing_file_raises(self) -> None:
        with self.assertRaises(OSError):
            converter.read_ids_from_file(self.root / "absent.txt")


class RecordingUniProt:
    """Stands in for `bioservices.UniProt`, recording every mapping request."""

    def __init__(self, verbose: bool = True) -> None:
        self.requests: list[dict] = []
        RecordingUniProt.instances.append(self)

    instances: list["RecordingUniProt"] = []

    def mapping(self, fr: str, to: str, query: str):
        self.requests.append({"fr": fr, "to": to, "query": query})
        result = RecordingUniProt.responder(query)
        if isinstance(result, dict) and not ({"results", "failedIds"} & result.keys()):
            return {"results": [{"from": source, "to": target}
                    for source, targets in result.items() for target in targets],
                    "failedIds": [identifier for identifier in query.split(",") if identifier not in result]}
        return result


class BatchConversionTests(unittest.TestCase):
    def setUp(self) -> None:
        RecordingUniProt.instances = []
        RecordingUniProt.responder = lambda query: {
            identifier: [f"hsa:{identifier}"] for identifier in query.split(",")
        }
        patcher = patch.object(converter, "UniProt", RecordingUniProt)
        patcher.start()
        self.addCleanup(patcher.stop)
        # Rate limiting is real behaviour, but the suite must not sleep for it.
        sleeper = patch.object(converter.time, "sleep")
        self.sleep = sleeper.start()
        self.addCleanup(sleeper.stop)

    @property
    def requests(self) -> list[dict]:
        self.assertEqual(len(RecordingUniProt.instances), 1)
        return RecordingUniProt.instances[0].requests

    def convert(self, ids, **kwargs):
        return quietly(
            converter.batch_convert, ids, "UniProtKB_AC-ID", "KEGG", **kwargs
        )

    def test_a_short_list_is_one_comma_separated_request(self) -> None:
        mapping, failed = self.convert(["P43403", "P04637"])
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[0]["query"], "P43403,P04637")
        self.assertEqual(self.requests[0]["fr"], "UniProtKB_AC-ID")
        self.assertEqual(self.requests[0]["to"], "KEGG")
        self.assertEqual(mapping["P43403"], ["hsa:P43403"])
        self.assertEqual(failed, [])

    def test_a_long_list_is_split_into_chunks_of_the_requested_size(self) -> None:
        # 250 identifiers at 100 per request is 3 requests: 100, 100, 50.
        identifiers = [f"P{index:05d}" for index in range(250)]
        mapping, failed = self.convert(identifiers, chunk_size=100, delay=0)
        self.assertEqual(len(self.requests), 3)
        self.assertEqual(
            [len(request["query"].split(",")) for request in self.requests],
            [100, 100, 50],
        )
        # Every identifier appears exactly once across the chunks.
        sent = [
            identifier
            for request in self.requests
            for identifier in request["query"].split(",")
        ]
        self.assertEqual(sent, identifiers)
        self.assertEqual(len(mapping), 250)
        self.assertEqual(failed, [])

    def test_a_chunk_size_larger_than_the_list_still_sends_one_request(self) -> None:
        self.convert(["P43403"], chunk_size=500)
        self.assertEqual(len(self.requests), 1)

    def test_identifiers_that_never_map_are_reported_as_failed(self) -> None:
        RecordingUniProt.responder = lambda query: {"P43403": ["hsa:7535"]}
        mapping, failed = self.convert(["P43403", "P99999"], delay=0)
        self.assertEqual(mapping["P43403"], ["hsa:7535"])
        # Absent from the response, so present in the result with no target --
        # a silently dropped identifier would inflate the mapping rate.
        self.assertEqual(mapping["P99999"], [])
        self.assertEqual(len(mapping), 2)

    def test_an_empty_response_marks_the_whole_chunk_failed(self) -> None:
        RecordingUniProt.responder = lambda query: {}
        mapping, failed = self.convert(["P43403", "P04637"], delay=0)
        self.assertEqual(sorted(failed), ["P04637", "P43403"])
        self.assertTrue(all(value == [] for value in mapping.values()))

    def test_a_failed_chunk_is_retried_one_identifier_at_a_time(self) -> None:
        # UniProt rejects a whole batch when one identifier in it is malformed,
        # so the per-identifier retry is what rescues the rest.
        def responder(query: str):
            if "," in query:
                raise RuntimeError("400 Bad Request")
            if query == "BROKEN":
                return {}
            return {query: [f"hsa:{query}"]}

        RecordingUniProt.responder = staticmethod(responder)
        mapping, failed = self.convert(["P43403", "BROKEN", "P04637"], delay=0)
        queries = [request["query"] for request in self.requests]
        self.assertEqual(queries[0], "P43403,BROKEN,P04637")  # the failed batch
        self.assertEqual(queries[1:], ["P43403", "BROKEN", "P04637"])
        self.assertEqual(mapping["P43403"], ["hsa:P43403"])
        self.assertEqual(failed, ["BROKEN"])

    def test_a_retry_that_also_fails_records_the_identifier_once(self) -> None:
        def responder(query: str):
            raise RuntimeError("service unavailable")

        RecordingUniProt.responder = staticmethod(responder)
        mapping, failed = self.convert(["P43403"], delay=0)
        self.assertEqual(failed, ["P43403"])
        self.assertIsNone(mapping["P43403"])

    def test_the_delay_is_only_taken_between_chunks(self) -> None:
        self.convert([f"P{index}" for index in range(3)], chunk_size=1, delay=0.5)
        # Three chunks, two gaps.
        self.assertEqual(
            [call.args[0] for call in self.sleep.call_args_list], [0.5, 0.5]
        )

    def test_no_delay_is_taken_when_it_is_switched_off(self) -> None:
        self.convert([f"P{index}" for index in range(3)], chunk_size=1, delay=0)
        self.sleep.assert_not_called()


class MappingCsvTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)
        self.path = self.root / "mapping.csv"
        quietly(
            converter.save_mapping_csv,
            {"P43403": ["hsa:7535", "mmu:22637"], "P99999": None, "P04637": ["hsa:7157"]},
            self.path,
            "UniProtKB_AC-ID",
            "KEGG",
        )
        with self.path.open(newline="", encoding="utf-8") as handle:
            self.rows = list(csv.reader(handle))

    def test_the_header_is_the_documented_five_columns(self) -> None:
        self.assertEqual(
            self.rows[0],
            ["Source_ID", "Source_DB", "Target_IDs", "Target_DB", "Mapping_Status"],
        )

    def test_rows_are_sorted_by_source_identifier(self) -> None:
        self.assertEqual(
            [row[0] for row in self.rows[1:]], ["P04637", "P43403", "P99999"]
        )

    def test_multiple_targets_are_joined_with_semicolons(self) -> None:
        # A comma would collide with the CSV delimiter.
        row = next(row for row in self.rows if row[0] == "P43403")
        self.assertEqual(row[2], "hsa:7535;mmu:22637")
        self.assertEqual(row[4], "Success")

    def test_an_unmapped_identifier_is_written_as_an_empty_failed_row(self) -> None:
        row = next(row for row in self.rows if row[0] == "P99999")
        self.assertEqual(row[2], "")
        self.assertEqual(row[4], "Failed")

    def test_the_source_and_target_databases_are_recorded_on_every_row(self) -> None:
        for row in self.rows[1:]:
            self.assertEqual((row[1], row[3]), ("UniProtKB_AC-ID", "KEGG"))

    def test_failed_identifiers_are_saved_only_when_there_are_some(self) -> None:
        target = self.root / "failed.txt"
        quietly(converter.save_failed_ids, [], target)
        self.assertFalse(target.exists())
        quietly(converter.save_failed_ids, ["P99999", "P88888"], target)
        self.assertEqual(
            target.read_text(encoding="utf-8").split(), ["P99999", "P88888"]
        )


class FakeKegg:
    """Records KEGG requests and replays canned flat-file responses."""

    def __init__(self, find_result: str = "", entries: dict | None = None) -> None:
        self.services = SimpleNamespace(http_get=self.http_get)
        self.find_result = find_result
        self.entries = entries or {}
        self.requests: list[tuple[str, tuple]] = []

    def http_get(self, endpoint, frmt="txt"):
        self.requests.append(("http_get", (endpoint, frmt)))
        return self.find_result

    def find(self, database: str, query: str):
        self.requests.append(("find", (database, query)))
        return self.find_result

    def get(self, identifier: str):
        self.requests.append(("get", (identifier,)))
        return self.entries.get(identifier, "")


class KeggCompoundSearchTests(unittest.TestCase):
    def search(self, find_result: str):
        fake = FakeKegg(find_result=find_result)
        with patch.object(compound, "KEGG", lambda *a, **k: fake):
            _, identifier = quietly(compound.search_kegg_compound, "ATP")
        return fake, identifier

    def test_the_compound_database_is_searched_by_name(self) -> None:
        fake, _ = self.search("cpd:C00002\tATP; Adenosine 5'-triphosphate\n")
        self.assertEqual(fake.requests[0], ("http_get", ("find/compound/ATP", "txt")))

    def test_the_cpd_prefix_is_stripped_from_the_first_hit(self) -> None:
        # Downstream calls rebuild "cpd:<id>", so keeping the prefix here would
        # produce "cpd:cpd:C00002".
        _, identifier = self.search("cpd:C00002\tATP\n")
        self.assertEqual(identifier, "C00002")

    def test_no_results_returns_no_identifier(self) -> None:
        for empty in ("", "\n", "   "):
            with self.subTest(response=repr(empty)):
                _, identifier = self.search(empty)
                self.assertIsNone(identifier)

    def test_a_service_error_returns_no_identifier_rather_than_raising(self) -> None:
        class Broken:
            services = SimpleNamespace()
            def find(self, *args):
                raise RuntimeError("KEGG is down")

        with patch.object(compound, "KEGG", lambda *a, **k: Broken()):
            _, identifier = quietly(compound.search_kegg_compound, "ATP")
        self.assertIsNone(identifier)


class KeggEntryParsingTests(unittest.TestCase):
    """Parsed against the published values in the ATP entry above."""

    def setUp(self) -> None:
        self.kegg = FakeKegg(entries={"cpd:C00002": ATP_ENTRY})
        self.info = quietly(compound.get_kegg_info, self.kegg, "C00002")

    def test_the_entry_is_requested_with_the_cpd_prefix(self) -> None:
        self.assertEqual(self.kegg.requests, [("get", ("cpd:C00002",))])

    def test_the_published_formula_and_masses_are_extracted(self) -> None:
        self.assertEqual(self.info["formula"], "C10H16N5O13P3")
        self.assertEqual(self.info["exact_mass"], "506.9957")
        self.assertEqual(self.info["mol_weight"], "507.181")

    def test_the_name_loses_its_trailing_semicolon(self) -> None:
        # KEGG separates synonyms with ";"; keeping it would corrupt the label.
        self.assertEqual(self.info["name"], "ATP")

    def test_the_chebi_identifier_is_pulled_out_of_dblinks(self) -> None:
        # ATP is CHEBI:15422.
        self.assertEqual(self.info["chebi_id"], "15422")

    def test_multiple_chebi_forms_are_preserved_without_selecting_one(self) -> None:
        # KEGG C00022 links charged pyruvate and neutral pyruvic acid.
        entry = ATP_ENTRY.replace("ChEBI: 15422", "ChEBI: 15361 32816 15361")
        info = quietly(compound.get_kegg_info,
                       FakeKegg(entries={"cpd:C00022": entry}), "C00022")
        self.assertEqual(info["chebi_ids"], ["15361", "32816"])
        self.assertIsNone(info["chebi_id"])
        with patch.object(compound, "UniChem") as api:
            self.assertIsNone(quietly(compound.get_chembl_id, "C00022", info["chebi_id"]))
        api.assert_not_called()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.txt"
            quietly(compound.save_results, "pyruvate", info, None, output)
            report = output.read_text()
        self.assertIn("ChEBI candidates (unresolved): 15361, 32816", report)
        self.assertNotIn("ChEMBL:", report)

    def test_only_the_pathway_block_becomes_pathways(self) -> None:
        # Three PATHWAY lines. The indented DBLINKS lines that follow must not
        # be collected, or the pathway count is inflated by database links.
        self.assertEqual(len(self.info["pathways"]), 3)
        self.assertEqual(self.info["pathways"][0], "map00190  Oxidative phosphorylation")
        self.assertTrue(
            all("PubChem" not in pathway for pathway in self.info["pathways"])
        )
        self.assertTrue(
            all("KNApSAcK" not in pathway for pathway in self.info["pathways"])
        )

    def test_an_entry_without_a_pathway_block_has_no_pathways(self) -> None:
        entry = "ENTRY       C99999\nNAME        Nothing\nFORMULA     CH4\n///\n"
        info = quietly(
            compound.get_kegg_info, FakeKegg(entries={"cpd:C99999": entry}), "C99999"
        )
        self.assertEqual(info["pathways"], [])
        self.assertIsNone(info["chebi_id"])
        self.assertEqual(info["formula"], "CH4")

    def test_an_empty_response_is_reported_as_no_information(self) -> None:
        self.assertIsNone(quietly(compound.get_kegg_info, FakeKegg(), "C00002"))


class UniChemMappingTests(unittest.TestCase):
    def test_missing_cross_reference_does_not_request_an_unsupported_source(self):
        with patch.object(compound, "UniChem") as api:
            self.assertIsNone(quietly(compound.get_chembl_id, "C00999"))
        api.assert_not_called()

    def test_current_api_deduplicates_matches_and_preserves_ambiguity(self):
        for values, expected in [([], None), (["CHEMBL25", "CHEMBL25"], "CHEMBL25"),
                                 (["CHEMBL25", "CHEMBL99"], None)]:
            with self.subTest(values=values), patch.object(compound, "UniChem") as api:
                api.return_value.get_compounds.return_value = {"compounds": [
                    {"sources": [{"shortName": "chembl", "compoundId": value}]}
                    for value in values
                ]}
                self.assertEqual(quietly(compound.get_chembl_id, "C00999", "15365"), expected)
                api.return_value.get_compounds.assert_called_once_with("CHEBI:15365", "chebi")

    def test_prefixed_identifier_and_service_failure(self):
        with patch.object(compound, "UniChem") as api:
            api.return_value.get_compounds.side_effect = RuntimeError("offline")
            self.assertIsNone(quietly(compound.get_chembl_id, "C00999", "CHEBI:15365"))
            api.return_value.get_compounds.assert_called_once_with("CHEBI:15365", "chebi")


class ChebiAndChemblTests(unittest.TestCase):
    def test_a_bare_chebi_number_is_prefixed_before_the_request(self) -> None:
        # The ChEBI service requires the "CHEBI:" namespace.
        requested: list[str] = []

        class FakeChebi:
            def getCompleteEntity(self, identifier):
                requested.append(identifier)
                return type(
                    "Entity",
                    (),
                    {
                        "chebiId": "CHEBI:15422",
                        "chebiAsciiName": "ATP",
                        "formula": "C10H16N5O13P3",
                        "mass": "507.18100",
                    },
                )()

        with patch.object(compound, "ChEBI", lambda *a, **k: FakeChebi()):
            info = quietly(compound.get_chebi_info, "15422")
        self.assertEqual(requested, ["CHEBI:15422"])
        self.assertEqual(info["chebi_id"], "CHEBI:15422")
        self.assertEqual(info["name"], "ATP")
        self.assertEqual(info["formula"], "C10H16N5O13P3")

    def test_an_already_prefixed_identifier_is_not_prefixed_twice(self) -> None:
        requested: list[str] = []

        class FakeChebi:
            def getCompleteEntity(self, identifier):
                requested.append(identifier)
                return None

        with patch.object(compound, "ChEBI", lambda *a, **k: FakeChebi()):
            quietly(compound.get_chebi_info, "CHEBI:15422")
        self.assertEqual(requested, ["CHEBI:15422"])

    def test_no_chebi_identifier_means_no_request_at_all(self) -> None:
        with patch.object(compound, "ChEBI") as chebi:
            self.assertIsNone(quietly(compound.get_chebi_info, None))
        chebi.assert_not_called()

    def test_the_chembl_lookup_uses_the_current_method_name(self) -> None:
        # `get_compound_by_chemblId` was removed after bioservices 1.6; the
        # current release exposes `get_molecule`, and the installed class must
        # actually have whatever the script calls.
        from bioservices import ChEMBL

        self.assertTrue(hasattr(ChEMBL, "get_molecule"))

        requested: list[str] = []

        class FakeChembl:
            def get_molecule(self, identifier):
                requested.append(identifier)
                return {
                    "pref_name": "ASPIRIN",
                    "molecule_properties": {"full_mwt": "180.16", "alogp": "1.31"},
                    "molecule_structures": {"canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O"},
                }

        with patch.object(compound, "ChEMBL", lambda *a, **k: FakeChembl()):
            result = quietly(compound.get_chembl_info, "CHEMBL25")
        self.assertEqual(requested, ["CHEMBL25"])
        self.assertEqual(result["pref_name"], "ASPIRIN")

    def test_no_chembl_identifier_means_no_request(self) -> None:
        with patch.object(compound, "ChEMBL") as chembl:
            self.assertIsNone(quietly(compound.get_chembl_info, None))
        chembl.assert_not_called()

    def test_a_chembl_error_is_swallowed_into_a_none_result(self) -> None:
        class Broken:
            def get_molecule(self, identifier):
                raise RuntimeError("ChEMBL is down")

        with patch.object(compound, "ChEMBL", lambda *a, **k: Broken()):
            self.assertIsNone(quietly(compound.get_chembl_info, "CHEMBL25"))


class CompoundReportTests(unittest.TestCase):
    def test_the_report_records_every_identifier_that_was_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.txt"
            quietly(
                compound.save_results,
                "ATP",
                {
                    "kegg_id": "C00002",
                    "name": "ATP",
                    "formula": "C10H16N5O13P3",
                    "exact_mass": "506.9957",
                    "mol_weight": "507.181",
                    "chebi_id": "15422",
                    "pathways": ["map00190", "map00230"],
                },
                "CHEMBL14249",
                path,
            )
            text = path.read_text(encoding="utf-8")
        self.assertIn("ATP", text)
        self.assertIn("C10H16N5O13P3", text)
        self.assertIn("KEGG: C00002", text)
        self.assertIn("ChEBI: 15422", text)
        self.assertIn("CHEMBL14249", text)
        self.assertIn("Pathways: 2 found", text)

    def test_a_report_without_kegg_information_still_writes(self) -> None:
        # The compound may resolve in ChEMBL but not in KEGG.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.txt"
            quietly(compound.save_results, "Mystery", None, "CHEMBL1", path)
            text = path.read_text(encoding="utf-8")
        self.assertIn("Mystery", text)
        self.assertIn("CHEMBL1", text)
        self.assertNotIn("KEGG Compound\n", text)


class FakeKgmlKegg:
    """A KEGG stand-in for the KGML pathway walk."""

    def __init__(self, parsed: dict | None = None, entry: str = "") -> None:
        self.parsed = parsed
        self.entry = entry
        self.parsed_ids: list[str] = []

    def parse_kgml_pathway(self, pathway_id: str):
        self.parsed_ids.append(pathway_id)
        if self.parsed is None:
            raise RuntimeError("no KGML for this pathway")
        return self.parsed

    def get(self, pathway_id: str):
        return self.entry


KGML = {
    "entries": [{"id": "1", "gene_names": "TP53"}, {"id": "2", "gene_names": "MDM2"}],
    "relations": [
        {"entry1": "1", "entry2": "2", "name": "activation", "link": "PPrel"},
        {"entry1": "2", "entry2": "1", "name": "inhibition", "link": "PPrel"},
        {"entry1": "1", "entry2": "2", "name": "binding/association", "link": "PPrel"},
        {"entry1": "1", "entry2": "2", "name": "activation", "link": "PPrel"},
        {"entry1": "2", "entry2": "2", "name": "methylation", "link": "PPrel"},
    ],
}


class PathwayAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)

    def analyse(self, kegg, pathway_id: str = "hsa04115"):
        return quietly(pathways.analyze_pathway, kegg, pathway_id)

    def test_entries_and_relations_are_counted_and_typed(self) -> None:
        kegg = FakeKgmlKegg(parsed=KGML, entry="NAME        p53 signaling pathway\n")
        result = self.analyse(kegg)
        self.assertEqual(result["num_entries"], 2)
        self.assertEqual(result["num_relations"], 5)
        # Hand-counted from KGML above.
        self.assertEqual(
            result["relation_types"],
            {"activation": 2, "inhibition": 1, "binding/association": 1,
             "methylation": 1},
        )
        self.assertEqual(result["pathway_name"], "p53 signaling pathway")

    def test_a_pathway_without_kgml_is_skipped_not_fatal(self) -> None:
        # Many KEGG pathways have no KGML; one of them must not end the run.
        self.assertIsNone(self.analyse(FakeKgmlKegg(parsed=None)))

    def test_a_missing_name_falls_back_to_unknown(self) -> None:
        result = self.analyse(FakeKgmlKegg(parsed=KGML, entry="ENTRY  hsa04115\n"))
        self.assertEqual(result["pathway_name"], "Unknown")

    def test_an_empty_pathway_reports_zero_rather_than_failing(self) -> None:
        result = self.analyse(FakeKgmlKegg(parsed={}, entry=""))
        self.assertEqual((result["num_entries"], result["num_relations"]), (0, 0))
        self.assertEqual(result["relation_types"], {})

    def test_failed_pathways_are_dropped_from_the_batch(self) -> None:
        class Flaky(FakeKgmlKegg):
            def parse_kgml_pathway(self, pathway_id):
                if pathway_id == "bad":
                    raise RuntimeError("no KGML")
                return KGML

        results = quietly(
            pathways.analyze_all_pathways, Flaky(entry=""), ["good", "bad", "good2"]
        )
        self.assertEqual([r["pathway_id"] for r in results], ["good", "good2"])

    def test_the_limit_truncates_the_pathway_list(self) -> None:
        kegg = FakeKgmlKegg(parsed=KGML, entry="")
        results = quietly(
            pathways.analyze_all_pathways, kegg, ["a", "b", "c", "d"], 2
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(kegg.parsed_ids, ["a", "b"])

    def test_the_summary_buckets_the_four_named_interaction_types(self) -> None:
        result = self.analyse(FakeKgmlKegg(parsed=KGML, entry="NAME  p53\n"))
        path = self.root / "summary.csv"
        quietly(pathways.save_pathway_summary, [result], path)
        with path.open(newline="", encoding="utf-8") as handle:
            header, row = list(csv.reader(handle))
        self.assertEqual(
            header,
            ["Pathway_ID", "Pathway_Name", "Num_Entries", "Num_Relation_Records",
             "Activation", "Inhibition", "Phosphorylation", "Binding", "Other"],
        )
        columns = dict(zip(header, row))
        self.assertEqual(columns["Activation"], "2")
        self.assertEqual(columns["Inhibition"], "1")
        self.assertEqual(columns["Phosphorylation"], "0")
        self.assertEqual(columns["Binding"], "1")
        # methylation is not one of the four named buckets.
        self.assertEqual(columns["Other"], "1")
        # Every relation is accounted for exactly once.
        self.assertEqual(
            sum(int(columns[name]) for name in
                ("Activation", "Inhibition", "Phosphorylation", "Binding", "Other")),
            int(columns["Num_Relation_Records"]),
        )

    def test_interactions_are_written_as_three_column_sif(self) -> None:
        result = self.analyse(FakeKgmlKegg(parsed=KGML, entry=""))
        path = self.root / "network.sif"
        quietly(pathways.save_interactions_sif, [result], path)
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 5)
        # SIF is source<TAB>interaction<TAB>target; Cytoscape reads nothing else.
        self.assertEqual(lines[0].split("\t"), ["hsa04115#1", "activation", "hsa04115#2"])
        for line in lines:
            self.assertEqual(len(line.split("\t")), 3)

    def test_per_pathway_files_are_named_without_a_colon(self) -> None:
        # "path:hsa04115" would be an illegal filename on some systems.
        result = self.analyse(FakeKgmlKegg(parsed=KGML, entry=""), "path:hsa04115")
        quietly(pathways.save_detailed_pathway_info, [result], str(self.root))
        written = [p.name for p in (self.root / "pathways").iterdir()]
        self.assertEqual(written, ["path_hsa04115_interactions.csv"])

    def test_listing_uses_scoped_endpoint_without_global_organism_catalogue(self):
        with patch.object(pathways, "KEGG") as kegg:
            kegg.services.http_get.return_value = "hsa00010\tGlycolysis\nhsa04115\tp53\n"
            ids = quietly(pathways.get_all_pathways, kegg, "hsa")
            kegg.services.http_get.assert_called_once_with("list/pathway/hsa", frmt="txt")
            self.assertEqual(ids, ["hsa00010", "hsa04115"])


class NcbiEmailTests(unittest.TestCase):
    """BLAST submissions need a contact address; a bad one gets rejected."""

    def test_a_valid_address_on_the_command_line_wins(self) -> None:
        with patch.dict("os.environ", {"NCBI_EMAIL": "env@lab.org"}):
            self.assertEqual(
                workflow.resolve_ncbi_email("cli@lab.org"), "cli@lab.org"
            )

    def test_the_environment_is_the_fallback(self) -> None:
        with patch.dict("os.environ", {"NCBI_EMAIL": "env@lab.org"}):
            self.assertEqual(workflow.resolve_ncbi_email(None), "env@lab.org")

    def test_surrounding_whitespace_is_stripped(self) -> None:
        self.assertEqual(workflow.resolve_ncbi_email("  a@b.org  "), "a@b.org")

    def test_no_address_anywhere_yields_none(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(workflow.resolve_ncbi_email(None))
            self.assertIsNone(workflow.resolve_ncbi_email(""))

    def test_malformed_addresses_are_refused(self) -> None:
        for candidate in ("not-an-email", "a@b", "a b@c.org", "@b.org", "a@.org"):
            with self.subTest(candidate=candidate):
                with patch.dict("os.environ", {}, clear=True):
                    self.assertIsNone(workflow.resolve_ncbi_email(candidate))


class ProteinSearchTests(unittest.TestCase):
    TABLE = (
        "Entry\tGene names\tOrganism\tLength\tProtein names\n"
        "P43403\tZAP70 SRK\tHomo sapiens\t619\tTyrosine-protein kinase ZAP-70\n"
        "P04637\tTP53\tHomo sapiens\t393\tCellular tumor antigen p53\n"
    )

    class FakeUniProt:
        def __init__(self, verbose: bool = True, retrieve=None, search="") -> None:
            self.retrieve_result = retrieve
            self.search_result = search
            self.calls: list[tuple[str, tuple, dict]] = []

        def retrieve(self, *args, **kwargs):
            self.calls.append(("retrieve", args, kwargs))
            if self.retrieve_result is None:
                raise RuntimeError("not an accession")
            return self.retrieve_result

        def search(self, *args, **kwargs):
            self.calls.append(("search", args, kwargs))
            return self.search_result

    def run_search(self, query: str, **kwargs):
        fake = self.FakeUniProt(**kwargs)
        with patch.object(workflow, "UniProt", lambda **k: fake):
            _, identifier = quietly(workflow.search_protein, query)
        return fake, identifier

    def test_an_accession_shaped_query_is_retrieved_directly(self) -> None:
        # P43403 is six characters starting with P, so it is fetched rather
        # than searched -- one request instead of a full-text query.
        fake, identifier = self.run_search("P43403", retrieve={"primaryAccession": "P43403"})
        self.assertEqual(identifier, "P43403")
        self.assertEqual([call[0] for call in fake.calls], ["retrieve"])

    def test_a_name_query_falls_through_to_search(self) -> None:
        fake, identifier = self.run_search("ZAP70_HUMAN", search=self.TABLE)
        self.assertEqual([call[0] for call in fake.calls], ["search"])
        self.assertEqual(identifier, "P43403")  # the first data row

    def test_a_failed_direct_retrieval_falls_back_to_search(self) -> None:
        fake, identifier = self.run_search("P43403", retrieve=None, search=self.TABLE)
        self.assertEqual([call[0] for call in fake.calls], ["retrieve", "search"])
        self.assertEqual(identifier, "P43403")

    def test_a_header_only_response_finds_nothing(self) -> None:
        # One line means the table had no data rows; indexing lines[1] would
        # raise instead of reporting "not found".
        _, identifier = self.run_search("NOSUCHPROTEIN", search="Entry\tGene names\n")
        self.assertIsNone(identifier)

    def test_an_empty_response_finds_nothing(self) -> None:
        _, identifier = self.run_search("NOSUCHPROTEIN", search="")
        self.assertIsNone(identifier)


class SequenceRetrievalTests(unittest.TestCase):
    class FakeUniProt:
        def __init__(self, fasta) -> None:
            self.fasta = fasta
            self.formats: list[str] = []

        def retrieve(self, identifier, frmt=None):
            self.formats.append(frmt)
            return self.fasta

    def test_the_fasta_header_is_dropped_and_the_lines_joined(self) -> None:
        fake = self.FakeUniProt(">sp|P43403|ZAP70_HUMAN\nMPDPAAHL\nPFFYGSIS\n")
        sequence = quietly(workflow.retrieve_sequence, fake, "P43403")
        # 16 residues across two wrapped lines; a header left in would corrupt
        # the BLAST submission that follows.
        self.assertEqual(sequence, "MPDPAAHLPFFYGSIS")
        self.assertEqual(fake.formats, ["fasta"])

    def test_an_empty_response_yields_no_sequence(self) -> None:
        self.assertIsNone(
            quietly(workflow.retrieve_sequence, self.FakeUniProt(""), "P43403")
        )

    def test_a_service_error_yields_no_sequence(self) -> None:
        class Broken:
            def retrieve(self, *args, **kwargs):
                raise RuntimeError("UniProt is down")

        self.assertIsNone(quietly(workflow.retrieve_sequence, Broken(), "P43403"))


class BlastGuardTests(unittest.TestCase):
    def test_blast_is_not_submitted_without_a_contact_address(self) -> None:
        # EBI rejects anonymous submissions; sending one wastes a job slot.
        with patch.object(workflow, "NCBIblast") as blast:
            self.assertIsNone(quietly(workflow.run_blast, "MPDPAAHL", None))
        blast.assert_not_called()

    def test_blast_is_not_submitted_when_explicitly_skipped(self) -> None:
        with patch.object(workflow, "NCBIblast") as blast:
            self.assertIsNone(
                quietly(workflow.run_blast, "MPDPAAHL", "a@b.org", skip=True)
            )
        blast.assert_not_called()

    def test_a_finished_job_returns_its_result(self) -> None:
        class FakeBlast:
            def __init__(self, verbose: bool = True) -> None:
                self.submitted: dict = {}
                self.services = SimpleNamespace()

            def run(self, **kwargs):
                self.submitted = kwargs
                return "ncbiblast-1"

            def get_status(self, jobid):
                return "FINISHED"

            def get_result(self, jobid, kind):
                return "BLAST report\nhit 1\n"

        fake = FakeBlast()
        with patch.object(workflow, "NCBIblast", lambda **k: fake):
            result = quietly(workflow.run_blast, "MPDPAAHL", "a@b.org")
        self.assertIn("BLAST report", result)
        self.assertEqual(fake.submitted["program"], "blastp")
        self.assertEqual(fake.submitted["stype"], "protein")
        self.assertEqual(fake.submitted["database"], "uniprotkb")
        self.assertEqual(fake.submitted["email"], "a@b.org")

    def test_a_failed_job_returns_nothing_rather_than_polling_forever(self) -> None:
        class FailingBlast:
            services = SimpleNamespace()
            def __init__(self, verbose: bool = True) -> None:
                pass

            def run(self, **kwargs):
                return "ncbiblast-2"

            def get_status(self, jobid):
                return "ERROR"

        with patch.object(workflow, "NCBIblast", lambda **k: FailingBlast()):
            with patch.object(workflow.time, "sleep"):
                self.assertIsNone(quietly(workflow.run_blast, "MPDPAAHL", "a@b.org"))


class InteractionTests(unittest.TestCase):
    def test_associations_preserve_stable_identifiers_and_scores(self):
        rows = [{"stringId_A": "9606.A", "stringId_B": "9606.B", "score": 0.95}]
        with patch.object(workflow, "STRING") as client:
            client.return_value.get_interaction_partners.return_value = rows
            self.assertEqual(quietly(workflow.find_interactions, "P43403", 9606), rows)
            kwargs = client.return_value.get_interaction_partners.call_args.kwargs
            self.assertEqual(kwargs["species"], 9606)
            self.assertEqual(kwargs["required_score"], 700)

    def test_unknown_taxon_does_not_default_to_human(self):
        with patch.object(workflow, "STRING") as client:
            self.assertEqual(quietly(workflow.find_interactions, "P43403"), [])
        client.assert_not_called()


class GoAnnotationTests(unittest.TestCase):
    def test_json_pages_are_combined_deduplicated_and_not_assertions_excluded(self):
        kinase = {"goId": "GO:0004713", "goName": "kinase", "goAspect": "molecular_function"}
        process = {"goId": "GO:0002250", "goName": "immune", "goAspect": "biological_process"}
        negative = {"goId": "GO:0005886", "goName": "membrane", "goAspect": "cellular_component", "qualifier": "NOT|located_in"}
        with patch.object(workflow, "QuickGO") as client:
            client.return_value.Annotation.side_effect = [
                {"results": [kinase, negative], "pageInfo": {"current": 1, "total": 2}},
                {"results": [kinase, process], "pageInfo": {"current": 2, "total": 2}},
            ]
            result = quietly(workflow.get_go_annotations, "P43403")
            calls = client.return_value.Annotation.call_args_list
            self.assertEqual([c.kwargs["page"] for c in calls], [1, 2])
            self.assertEqual(calls[0].kwargs["geneProductId"], "UniProtKB:P43403")
        self.assertEqual(result, {"F": [("GO:0004713", "kinase")], "P": [("GO:0002250", "immune")], "C": []})

    def test_service_failure_does_not_report_no_annotations(self):
        with patch.object(workflow, "QuickGO") as client:
            client.return_value.Annotation.return_value = 503
            with self.assertRaisesRegex(ValueError, "incomplete"):
                quietly(workflow.get_go_annotations, "P43403")

    def test_zero_hits_is_an_empty_aspect_mapping(self):
        with patch.object(workflow, "QuickGO") as client:
            client.return_value.Annotation.return_value = {"results": [], "pageInfo": {"total": 0}}
            self.assertEqual(quietly(workflow.get_go_annotations, "P43403"), {"P": [], "F": [], "C": []})

    def test_invalid_or_excessive_page_total_fails_before_followup_requests(self):
        for total in [None, "2", True, -1, float("inf"), float("nan"), 1001]:
            with self.subTest(total=total), patch.object(workflow, "QuickGO") as client:
                client.return_value.Annotation.return_value = {"results": [], "pageInfo": {"total": total}}
                with self.assertRaisesRegex(ValueError, "page total"):
                    quietly(workflow.get_go_annotations, "P43403")
                self.assertEqual(client.return_value.Annotation.call_count, 1)

    def test_repeated_page_and_changing_catalogue_fail(self):
        for second in [{"current": 1, "total": 2}, {"current": 2, "total": 3}]:
            with self.subTest(second=second), patch.object(workflow, "QuickGO") as client:
                client.return_value.Annotation.side_effect = [
                    {"results": [], "pageInfo": {"current": 1, "total": 2}},
                    {"results": [], "pageInfo": second},
                ]
                with self.assertRaisesRegex(ValueError, "wrong page|total changed"):
                    quietly(workflow.get_go_annotations, "P43403")
                self.assertEqual(client.return_value.Annotation.call_count, 2)

    def test_invalid_page_cap_fails_before_network_access(self):
        for cap in [0, -1, True, 1.5]:
            with self.subTest(cap=cap), patch.object(workflow, "QuickGO") as client:
                with self.assertRaisesRegex(ValueError, "max_pages"):
                    quietly(workflow.get_go_annotations, "P43403", max_pages=cap)
                client.assert_not_called()


class CurrentMappingContractTests(unittest.TestCase):
    def test_nested_uniprot_targets_and_multiple_targets(self):
        payload = {"results": [{"from": "hsa:7535", "to": {"primaryAccession": "P43403"}},
                               {"from": "hsa:7535", "to": {"primaryAccession": "Q12345"}}],
                   "failedIds": ["bad"]}
        self.assertEqual(converter.mapping_to_lists(payload), {"hsa:7535": ["P43403", "Q12345"], "bad": []})

    def test_timeout_and_unknown_record_shape_are_not_empty_success(self):
        for payload in [None, 503, {}, {"results": [{"from": "P43403", "to": {"unknown": "X"}}]}]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                converter.mapping_to_lists(payload)

    def test_target_alias_uses_the_target_code(self):
        self.assertEqual(converter.normalize_database_code("uniprot", target=True), "UniProtKB")

    def test_missing_ids_are_in_failed_list(self):
        with patch.object(converter, "UniProt") as client:
            client.return_value.mapping.return_value = {"results": [{"from": "P43403", "to": "hsa:7535"}]}
            mapping, failed = quietly(converter.batch_convert, ["P43403", "MISSING"], "UniProtKB_AC-ID", "KEGG", delay=0)
        self.assertEqual(failed, ["MISSING"])
        self.assertIsNone(mapping["MISSING"])

    def test_all_kegg_mappings_contribute_pathways(self):
        with patch.object(workflow, "UniProt") as client, patch.object(workflow, "KEGG") as kegg:
            client.mapping.return_value = {"results": [{"from": "P43403", "to": "hsa:1"}, {"from": "P43403", "to": "hsa:2"}]}
            kegg.get_pathway_by_gene.side_effect = [{"hsa00001": "first"}, {"hsa00002": "second"}]
            found = quietly(workflow.discover_pathways, client, kegg, "P43403")
        self.assertEqual(found, [("hsa00001", "first"), ("hsa00002", "second")])


class ScientificExportTests(unittest.TestCase):
    def test_sif_does_not_merge_local_ids_across_pathways(self):
        relation = {"entry1": "1", "entry2": "2", "name": None}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "network.sif"
            quietly(pathways.save_interactions_sif,
                    [{"pathway_id": "A", "relations": [relation]}, {"pathway_id": "B", "relations": [relation]}], target)
            self.assertEqual(target.read_text().splitlines(), ["A#1\tinteraction\tA#2", "B#1\tinteraction\tB#2"])

    def test_exact_compound_name_beats_substring_hits(self):
        fake = FakeKegg("C15823\tProgeldanamycin\nC11222\tGeldanamycin\n")
        with patch.object(compound, "KEGG", lambda: fake):
            self.assertEqual(quietly(compound.search_kegg_compound, "Geldanamycin")[1], "C11222")

    def test_unmapped_csv_is_distinct_from_request_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "mapping.csv"
            quietly(converter.save_mapping_csv, {"missing": [], "error": None}, target, "KEGG", "UniProtKB")
            with target.open() as handle:
                rows = {row["Source_ID"]: row for row in csv.DictReader(handle)}
            self.assertEqual(rows["missing"]["Mapping_Status"], "Unmapped")
            self.assertEqual(rows["error"]["Mapping_Status"], "Failed")

    def test_ambiguous_compound_name_does_not_choose_first(self):
        with patch.object(compound, "KEGG", lambda: FakeKegg("cpd:C00002\tATP\ncpd:C00008\tADP\n")):
            self.assertIsNone(quietly(compound.search_kegg_compound, "adenosine")[1])

    def test_chembl_null_properties_do_not_discard_valid_record(self):
        with patch.object(compound, "ChEMBL") as client:
            payload = {"pref_name": "X", "molecule_properties": None, "molecule_structures": None}
            client.return_value.get_molecule.return_value = payload
            self.assertEqual(quietly(compound.get_chembl_info, "CHEMBL1"), payload)


if __name__ == "__main__":
    unittest.main()
