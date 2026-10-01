"""Tests for the PrimeKG query helpers.

PrimeKG itself is a ~4 million edge CSV nobody should download to run a test,
so these drive the same code against a small hand-built edge list with the
real column layout (`x_id, x_type, x_name, x_source, relation,
display_relation, y_*`). The queries treat the graph as undirected -- a node
can appear on either side of an edge -- and that symmetry is the easiest thing
to get wrong, so most of the assertions are about it.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "primekg"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("pandas", reason="primekg needs pandas")

import query_primekg  # noqa: E402

EDGES = """\
x_id,x_type,x_name,x_source,relation,display_relation,y_id,y_type,y_name,y_source
7157,gene/protein,TP53,NCBI,protein_protein,interacts with,672,gene/protein,BRCA1,NCBI
D001,disease,Breast Cancer,MONDO,disease_protein,associated with,672,gene/protein,BRCA1,NCBI
DBTEST1,drug,Olaparib,DrugBank,drug_protein,targets,672,gene/protein,BRCA1,NCBI
D001,disease,Breast Cancer,MONDO,disease_phenotype_positive,phenotype present,HP001,effect/phenotype,Breast Mass,HPO
D001,disease,Breast Cancer,MONDO,disease_disease,related to,D002,disease,Ovarian Cancer,MONDO
D002,disease,Ovarian Cancer,MONDO,disease_protein,associated with,7157,gene/protein,TP53,NCBI
"""


class PrimeKgTestCase(unittest.TestCase):
    """Point DATA_PATH at a small synthetic knowledge graph."""

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.data = Path(self._temporary.name) / "kg.csv"
        self.data.write_text(EDGES, encoding="utf-8")
        patcher = mock.patch.object(query_primekg, "DATA_PATH", str(self.data))
        patcher.start()
        self.addCleanup(patcher.stop)


class DataPathTests(unittest.TestCase):
    def test_the_default_path_is_relative_and_env_overridable(self) -> None:
        # A hardcoded absolute path would name one machine and work on no other.
        with mock.patch.dict("os.environ", {}, clear=True):
            import importlib
            self.assertFalse(Path(importlib.reload(query_primekg).DATA_PATH).is_absolute())

        with mock.patch.dict("os.environ", {"PRIMEKG_DATA": "/somewhere/kg.csv"}):
            import importlib

            reloaded = importlib.reload(query_primekg)
            self.assertEqual(reloaded.DATA_PATH, "/somewhere/kg.csv")
        importlib.reload(query_primekg)

    def test_a_missing_file_explains_where_to_get_the_data(self) -> None:
        with mock.patch.object(query_primekg, "DATA_PATH", "/no/such/kg.csv"):
            with self.assertRaises(FileNotFoundError) as raised:
                query_primekg._load_kg()
        message = str(raised.exception)
        self.assertIn("/no/such/kg.csv", message)
        self.assertIn("PRIMEKG_DATA", message)


class SearchTests(PrimeKgTestCase):
    def test_nodes_are_found_on_either_side_of_an_edge(self) -> None:
        # TP53 appears as x in one row and as y in another; one record either way.
        results = query_primekg.search_nodes("TP53")
        self.assertEqual(len(results), 1)
        # IDs are always read as strings, including numeric-only chunks/files.
        self.assertEqual(str(results[0]["id"]), "7157")
        self.assertEqual(results[0]["type"], "gene/protein")

    def test_search_is_case_insensitive_and_substring_based(self) -> None:
        for query in ("breast cancer", "BREAST", "east Can"):
            with self.subTest(query=query):
                names = {row["name"] for row in query_primekg.search_nodes(query)}
                self.assertIn("Breast Cancer", names)

    def test_a_type_filter_narrows_the_result(self) -> None:
        # "Breast" matches both the disease and the phenotype.
        unfiltered = {row["name"] for row in query_primekg.search_nodes("Breast")}
        self.assertEqual(unfiltered, {"Breast Cancer", "Breast Mass"})

        filtered = query_primekg.search_nodes("Breast", node_type="effect/phenotype")
        self.assertEqual([row["name"] for row in filtered], ["Breast Mass"])

    def test_no_match_returns_an_empty_list(self) -> None:
        self.assertEqual(query_primekg.search_nodes("no-such-gene"), [])

    def test_results_carry_the_source_database(self) -> None:
        self.assertEqual(query_primekg.search_nodes("Olaparib")[0]["source"], "DrugBank")


class NeighborTests(PrimeKgTestCase):
    def test_neighbors_are_collected_from_both_directions(self) -> None:
        # BRCA1 is only ever a y-node, so a one-sided query would return none.
        neighbors = query_primekg.get_neighbors(672)
        names = {row["neighbor_name"] for row in neighbors}
        self.assertEqual(names, {"TP53", "Breast Cancer", "Olaparib"})

    def test_a_node_id_is_matched_as_a_string_or_a_number(self) -> None:
        self.assertEqual(
            len(query_primekg.get_neighbors(672)),
            len(query_primekg.get_neighbors("672")),
        )

    def test_a_relation_filter_restricts_the_edge_type(self) -> None:
        targeted = query_primekg.get_neighbors(672, relation_type="drug_protein")
        self.assertEqual([row["neighbor_name"] for row in targeted], ["Olaparib"])

    def test_the_display_relation_is_carried_through(self) -> None:
        targeted = query_primekg.get_neighbors(672, relation_type="drug_protein")
        self.assertEqual(targeted[0]["display_relation"], "targets")

    def test_an_unknown_node_has_no_neighbors(self) -> None:
        self.assertEqual(query_primekg.get_neighbors("not-a-node"), [])


class PathTests(PrimeKgTestCase):
    def test_a_direct_edge_is_returned_as_a_one_hop_path(self) -> None:
        paths = query_primekg.find_paths("D001", "672")
        self.assertEqual(len(paths), 1)
        self.assertEqual(len(paths[0]), 1)
        self.assertEqual(paths[0][0]["relation"], "disease_protein")

    def test_direction_does_not_matter(self) -> None:
        self.assertEqual(
            len(query_primekg.find_paths("D001", "672")),
            len(query_primekg.find_paths("672", "D001")),
        )

    def test_unconnected_nodes_yield_no_path(self) -> None:
        self.assertEqual(query_primekg.find_paths("DBTEST1", "HP001"), [])

    def test_two_hop_search_connects_drug_protein_disease(self) -> None:
        paths = query_primekg.find_paths("DBTEST1", "D001", max_depth=2)
        self.assertEqual(len(paths), 1)
        self.assertEqual([edge["relation"] for edge in paths[0]],
                         ["drug_protein", "disease_protein"])
        self.assertEqual(paths[0][1]["traversal_from"]["id"], "672")
        self.assertEqual(paths[0][1]["traversal_to"]["id"], "D001")
        self.assertEqual(query_primekg.find_paths("DBTEST1", "D001", max_depth=1), [])


class DiseaseContextTests(PrimeKgTestCase):
    def test_the_context_is_bucketed_by_neighbour_type(self) -> None:
        context = query_primekg.get_disease_context("Breast Cancer")
        self.assertEqual(context["disease_info"]["name"], "Breast Cancer")
        self.assertEqual(
            [row["neighbor_name"] for row in context["associated_genes"]], ["BRCA1"]
        )
        self.assertEqual(
            [row["neighbor_name"] for row in context["phenotypes"]], ["Breast Mass"]
        )
        self.assertEqual(
            [row["neighbor_name"] for row in context["related_diseases"]],
            ["Ovarian Cancer"],
        )

    def test_a_disease_with_no_drug_edges_reports_an_empty_bucket(self) -> None:
        context = query_primekg.get_disease_context("Breast Cancer")
        self.assertEqual(context["associated_drugs"], [])

    def test_an_unknown_disease_reports_an_error_rather_than_raising(self) -> None:
        self.assertEqual(
            query_primekg.get_disease_context("no-such-disease"),
            {"error": "Disease not found"},
        )

    def test_a_gene_name_is_not_mistaken_for_a_disease(self) -> None:
        # search_nodes is type-filtered to 'disease', so a gene must not match.
        self.assertEqual(
            query_primekg.get_disease_context("TP53"), {"error": "Disease not found"}
        )


class IntegrityTests(PrimeKgTestCase):
    def append(self, row):
        with self.data.open("a") as handle:
            handle.write(row + "\n")

    def test_literal_search_handles_regex_characters(self):
        self.assertEqual(query_primekg.search_nodes("["), [])
        self.assertEqual(query_primekg.search_nodes(".*"), [])

    def test_reverse_rows_are_one_adjacency_with_both_original_rows(self):
        self.append("672,gene/protein,BRCA1,NCBI,drug_protein,targets,DBTEST1,drug,Olaparib,DrugBank")
        result = query_primekg.get_neighbors("672", "drug_protein")
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["edge_rows"]), 2)
        self.assertEqual({row["x_type"] for row in result[0]["edge_rows"]}, {"drug", "gene/protein"})
        paths = query_primekg.find_paths("DBTEST1", "D001")
        self.assertEqual(len(paths), 1)
        self.assertEqual(len(paths[0][0]["edge_rows"]), 2)

    def test_namespace_collision_is_rejected_and_can_be_disambiguated(self):
        self.append("672,disease,Another disease,MONDO,disease_protein,associated with,7157,gene/protein,TP53,NCBI")
        with self.assertRaisesRegex(ValueError, "Ambiguous node ID"):
            query_primekg.get_neighbors("672")
        result = query_primekg.get_neighbors("672", node_type="disease", node_source="MONDO")
        self.assertEqual([n["neighbor_name"] for n in result], ["TP53"])
        paths = query_primekg.find_paths("672", "7157", start_node_type="disease",
                                        start_node_source="MONDO", max_depth=1)
        self.assertEqual(len(paths), 1)

    def test_intermediate_id_collision_does_not_create_a_false_path(self):
        self.append("672,disease,Another disease,MONDO,disease_phenotype_positive,phenotype present,HP002,effect/phenotype,Other phenotype,HPO")
        self.assertEqual(query_primekg.find_paths("DBTEST1", "HP002"), [])

    def test_ambiguous_disease_name_is_not_silently_selected(self):
        result = query_primekg.get_disease_context("Cancer")
        self.assertEqual(result["error"], "Ambiguous disease name")
        self.assertEqual(len(result["candidates"]), 2)

    def test_exact_name_wins_over_a_longer_substring_match(self):
        self.append("D003,disease,Breast Cancer subtype,MONDO,disease_protein,associated with,7157,gene/protein,TP53,NCBI")
        self.assertEqual(query_primekg.get_disease_context("breast cancer")["disease_info"]["id"], "D001")

    def test_indications_and_contraindications_remain_distinct(self):
        for relation in ("indication", "contraindication", "off-label use"):
            self.append(f"DBTEST1,drug,Olaparib,DrugBank,{relation},{relation},D001,disease,Breast Cancer,MONDO")
        result = query_primekg.get_disease_context("Breast Cancer")
        self.assertEqual(len(result["associated_drugs"]), 3)
        self.assertEqual([len(v) for v in result["drug_relations"].values()], [1, 1, 1])

    def test_negative_phenotypes_keep_their_relation(self):
        self.append("D001,disease,Breast Cancer,MONDO,disease_phenotype_negative,phenotype absent,HP002,effect/phenotype,Other phenotype,HPO")
        result = query_primekg.get_disease_context("Breast Cancer")
        self.assertEqual({n["relation"] for n in result["phenotypes"]},
                         {"disease_phenotype_positive", "disease_phenotype_negative"})

    def test_string_ids_and_literal_na_are_preserved(self):
        self.data.write_text(EDGES.splitlines()[0] + "\n" +
                             "0001,gene/protein,NA,NCBI,protein_protein,ppi,2,gene/protein,Second,NCBI\n")
        result = query_primekg.search_nodes("NA")
        self.assertEqual(result[0]["id"], "0001")
        self.assertEqual(query_primekg.get_neighbors("0001")[0]["neighbor_id"], "2")
        self.assertEqual(query_primekg.get_neighbors("1"), [])

    def test_missing_schema_and_empty_values_are_rejected(self):
        self.data.write_text("id,name\n1,Example\n")
        with self.assertRaisesRegex(ValueError, "missing columns"):
            query_primekg.search_nodes("Example")
        self.data.write_text(EDGES.replace("7157,gene/protein", ",gene/protein", 1))
        with self.assertRaisesRegex(ValueError, "empty value"):
            query_primekg.search_nodes("TP53")

    def test_indexes_and_extra_provenance_are_preserved(self):
        self.data.write_text("x_index,y_index,evidence_id," + EDGES.splitlines()[0] + "\n" +
                             "11,22,synthetic-study," + EDGES.splitlines()[1] + "\n")
        node = query_primekg.search_nodes("TP53")[0]
        self.assertEqual(node["index"], "11")
        result = query_primekg.get_neighbors("7157")[0]
        self.assertEqual(result["neighbor_index"], "22")
        self.assertEqual(result["edge_rows"][0]["evidence_id"], "synthetic-study")

    def test_conflicting_indexes_fail_instead_of_merging_nodes(self):
        self.data.write_text("x_index,y_index," + EDGES.splitlines()[0] + "\n" +
                             "11,22," + EDGES.splitlines()[1] + "\n" +
                             "33,22," + EDGES.splitlines()[1] + "\n")
        with self.assertRaisesRegex(ValueError, "multiple release indexes"):
            query_primekg.get_neighbors("7157")

    def test_duplicate_release_index_does_not_merge_distinct_ids(self):
        self.data.write_text("x_index,y_index," + EDGES.splitlines()[0] + "\n" +
                             "11,11," + EDGES.splitlines()[1] + "\n")
        with self.assertRaisesRegex(ValueError, "multiple node identities"):
            query_primekg.get_neighbors("7157")

    def test_a_single_index_column_is_not_a_supported_schema(self):
        self.data.write_text("x_index," + EDGES.splitlines()[0] + "\n" +
                             "11," + EDGES.splitlines()[1] + "\n")
        with self.assertRaisesRegex(ValueError, "both x_index and y_index"):
            query_primekg.search_nodes("TP53")

    def test_depth_and_path_limit_are_explicit(self):
        for depth in (0, 3, -1, True):
            with self.assertRaises(ValueError):
                query_primekg.find_paths("D001", "672", max_depth=depth)
        self.append("D001,disease,Breast Cancer,MONDO,indication,indication,672,gene/protein,BRCA1,NCBI")
        with self.assertRaisesRegex(ValueError, "exceeds max_paths"):
            query_primekg.find_paths("D001", "672", max_paths=1)

    def test_self_paths_and_unknown_endpoints_are_empty(self):
        self.assertEqual(query_primekg.find_paths("672", "672"), [])
        self.assertEqual(query_primekg.find_paths("672", "unknown"), [])

    def test_search_limit_can_be_removed_and_invalid_limits_fail(self):
        self.assertEqual(len(query_primekg.search_nodes("Cancer", limit=1)), 1)
        self.assertEqual(len(query_primekg.search_nodes("Cancer", limit=None)), 2)
        for limit in (0, -1, True):
            with self.assertRaises(ValueError):
                query_primekg.search_nodes("Cancer", limit=limit)


if __name__ == "__main__":
    unittest.main()
