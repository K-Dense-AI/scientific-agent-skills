"""Unit tests for the ontology-term-resolution skill scripts.

The offline tests stub every network call, so the suite runs without touching
EBI. A handful of live smoke tests are gated behind OLS_LIVE_TESTS=1; they
document the API behaviour the scripts were built against.

    uv run --with pytest python -m pytest tests/ontology-term-resolution -q
    OLS_LIVE_TESTS=1 uv run --with pytest python -m pytest tests/ontology-term-resolution -q
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
from unittest.mock import patch

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "ontology-term-resolution"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
LIVE = os.environ.get("OLS_LIVE_TESTS") == "1"


def _load_script(name: str):
    """Load a bundled script as a module regardless of cwd."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ols_client = _load_script("ols_client")
resolve_terms = _load_script("resolve_terms")
validate_terms = _load_script("validate_terms")
id_client = _load_script("id_client")
lookup_prefix = _load_script("lookup_prefix")
zooma_client = _load_script("zooma_client")
map_terms = _load_script("map_terms")


def doc(**overrides):
    """A search doc shaped like the ones OLS returns."""
    base = {
        "obo_id": "UBERON:0002107",
        "label": "liver",
        "synonym": ["iecur", "jecur"],
        "ontology_name": "uberon",
        "is_defining_ontology": True,
        "type": "class",
    }
    base.update(overrides)
    return base


class CurieHelperTests(unittest.TestCase):
    def test_is_curie_accepts_real_prefixes(self):
        for value in ("UBERON:0002107", "CL:0000182", "NCBITaxon:9606", "Orphanet:558",
                      "HsapDv:0000001", "APOLLO_SV:00000001"):
            self.assertTrue(ols_client.is_curie(value), value)

    def test_is_curie_rejects_non_curies(self):
        for value in ("liver", "not a curie", "", "http://purl.obolibrary.org/obo/UBERON_0002107",
                      "UBERON_0002107"):
            self.assertFalse(ols_client.is_curie(value), value)

    def test_ontology_id_is_the_lowercased_prefix(self):
        self.assertEqual(ols_client.curie_to_ontology_id("HP:0001250"), "hp")
        self.assertEqual(ols_client.curie_to_ontology_id("NCBITaxon:9606"), "ncbitaxon")
        self.assertEqual(ols_client.curie_to_ontology_id("HsapDv:0000001"), "hsapdv")

    def test_ontology_id_override_for_orphanet(self):
        """Orphanet CURIEs are served by the ontology OLS calls `ordo`."""
        self.assertEqual(ols_client.curie_to_ontology_id("Orphanet:558"), "ordo")

    def test_ontology_id_of_junk_is_none(self):
        self.assertIsNone(ols_client.curie_to_ontology_id("not a curie"))


class IriConversionTests(unittest.TestCase):
    def test_obo_purl_to_curie(self):
        self.assertEqual(
            ols_client.iri_to_curie("http://purl.obolibrary.org/obo/MONDO_0005135"),
            "MONDO:0005135",
        )

    def test_efo_namespace_to_curie(self):
        """EFO does not live under the OBO PURL namespace."""
        self.assertEqual(
            ols_client.iri_to_curie("http://www.ebi.ac.uk/efo/EFO_0000246"), "EFO:0000246"
        )

    def test_orphanet_namespace_to_curie(self):
        self.assertEqual(
            ols_client.iri_to_curie("http://www.orpha.net/ORDO/Orphanet_558"),
            "Orphanet:558",
        )

    def test_multi_underscore_prefix_splits_on_the_last_underscore(self):
        self.assertEqual(
            ols_client.iri_to_curie("http://purl.obolibrary.org/obo/APOLLO_SV_00000001"),
            "APOLLO_SV:00000001",
        )

    def test_unconvertible_iris_return_none(self):
        self.assertIsNone(ols_client.iri_to_curie(""))
        self.assertIsNone(ols_client.iri_to_curie("http://example.org/nounderscore"))

    def test_candidate_iris_use_the_right_template(self):
        self.assertEqual(
            ols_client.candidate_iris("UBERON:0002107"),
            ["http://purl.obolibrary.org/obo/UBERON_0002107"],
        )
        self.assertEqual(
            ols_client.candidate_iris("EFO:0000246"),
            ["http://www.ebi.ac.uk/efo/EFO_0000246"],
        )
        self.assertEqual(
            ols_client.candidate_iris("Orphanet:558"),
            ["http://www.orpha.net/ORDO/Orphanet_558"],
        )


class LabelMatchingTests(unittest.TestCase):
    def test_normalize_folds_case_and_whitespace_only(self):
        self.assertEqual(ols_client.normalize_label("  Liver\tCortex "), "liver cortex")
        self.assertEqual(
            ols_client.normalize_label("CD4-positive"), "cd4-positive",
            "hyphens carry meaning and must survive normalisation",
        )

    def test_synonyms_collected_from_every_field_spelling(self):
        self.assertEqual(ols_client.synonyms_of({"synonym": ["a"]}), ["a"])
        self.assertEqual(ols_client.synonyms_of({"synonyms": ["b"]}), ["b"])
        self.assertEqual(
            sorted(ols_client.synonyms_of({"exact_synonyms": ["c"], "related_synonyms": ["d"]})),
            ["c", "d"],
        )

    def test_match_type_distinguishes_label_synonym_and_partial(self):
        self.assertEqual(ols_client.match_type("liver", doc()), "exact_label")
        self.assertEqual(ols_client.match_type("LIVER", doc()), "exact_label")
        self.assertEqual(ols_client.match_type("iecur", doc()), "exact_synonym")
        self.assertEqual(
            ols_client.match_type("liver", doc(label="caudate lobe of liver", synonym=[])),
            "partial",
            "OLS ranks partial hits alongside exact ones; the client must tell them apart",
        )


class CandidateRankingTests(unittest.TestCase):
    def test_dedupe_keeps_the_defining_ontologys_copy(self):
        docs = [
            doc(ontology_name="cl", is_defining_ontology=False),
            doc(ontology_name="uberon", is_defining_ontology=True),
        ]
        deduped = ols_client.dedupe_candidates(docs)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["ontology_name"], "uberon")

    def test_dedupe_skips_docs_without_an_identifier(self):
        self.assertEqual(ols_client.dedupe_candidates([{"label": "x"}]), [])

    def test_exact_matches_outrank_partial_ones(self):
        docs = [
            doc(obo_id="UBERON:0001117", label="caudate lobe of liver", synonym=[]),
            doc(obo_id="UBERON:0002107", label="liver"),
        ]
        ranked = ols_client.rank_candidates("liver", docs)
        self.assertEqual([r["obo_id"] for r in ranked],
                         ["UBERON:0002107", "UBERON:0001117"])
        self.assertEqual(ranked[0]["match_type"], "exact_label")
        self.assertEqual(ranked[1]["match_type"], "partial")

    def test_label_match_outranks_synonym_match(self):
        docs = [
            doc(obo_id="UBERON:0000001", label="other", synonym=["liver"]),
            doc(obo_id="UBERON:0002107", label="liver", synonym=[]),
        ]
        ranked = ols_client.rank_candidates("liver", docs)
        self.assertEqual(ranked[0]["obo_id"], "UBERON:0002107")
        self.assertEqual(ranked[1]["match_type"], "exact_synonym")


class ResolveStrategyTests(unittest.TestCase):
    def test_ladder_stops_at_the_first_strategy_that_hits(self):
        calls = []

        def fake_search(text, **kwargs):
            calls.append(kwargs.get("query_fields"))
            return [doc()]

        with patch.object(resolve_terms, "search", fake_search):
            result = resolve_terms.resolve_one(
                "liver", ontology="uberon", subtree_iri=None, rows=5, exact_only=False
            )
        self.assertEqual(result["strategy"], "exact")
        self.assertEqual(calls, ["label,synonym"], "later strategies must not run")

    def test_ladder_escalates_when_exact_finds_nothing(self):
        seen = []

        def fake_search(text, **kwargs):
            seen.append(kwargs)
            return [doc(label="heart left ventricle", synonym=[])] if len(seen) == 3 else []

        with patch.object(resolve_terms, "search", fake_search):
            result = resolve_terms.resolve_one(
                "left ventrical", ontology=None, subtree_iri=None, rows=5, exact_only=False
            )
        self.assertEqual(result["strategy"], "fulltext")
        self.assertEqual(result["candidates"][0]["match_type"], "partial")

    def test_exact_only_never_escalates(self):
        calls = []

        def fake_search(text, **kwargs):
            calls.append(kwargs)
            return []

        with patch.object(resolve_terms, "search", fake_search):
            result = resolve_terms.resolve_one(
                "zzzquux", ontology=None, subtree_iri=None, rows=5, exact_only=True
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["candidates"], [])

    def test_unresolved_query_becomes_a_visible_row(self):
        rows = resolve_terms.to_rows([{"query": "zzz", "strategy": "exact", "candidates": []}])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["match_type"], "unresolved")
        self.assertEqual(rows[0]["curie"], "", "an unresolved term must never carry an ID")


class ValidateTermTests(unittest.TestCase):
    def check(self, term, curie="UBERON:0002107", label=None, branch=None, ontologies=None,
              ancestors=()):
        with patch.object(validate_terms, "term_detail", return_value=term), \
             patch.object(validate_terms, "ancestor_curies", return_value=set(ancestors)):
            return validate_terms.check_term(
                curie, label, branch=branch, expect_ontologies=ontologies
            )

    def live_term(self, **overrides):
        base = {
            "label": "liver",
            "ontology_name": "uberon",
            "is_defining_ontology": True,
            "is_obsolete": False,
            "type": "class",
            "synonyms": ["iecur"],
            "_home_ontology": "uberon",
            "_resolved_via": "obo_id",
        }
        base.update(overrides)
        return base

    def test_valid_term_passes(self):
        result = self.check(self.live_term(), label="liver")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["actual_label"], "liver")

    def test_malformed_curie_is_rejected_without_a_lookup(self):
        with patch.object(validate_terms, "term_detail") as lookup:
            result = validate_terms.check_term(
                "liver", None, branch=None, expect_ontologies=None
            )
        lookup.assert_not_called()
        self.assertEqual(result["status"], "malformed_curie")

    def test_missing_term_is_not_found(self):
        self.assertEqual(self.check(None)["status"], "not_found")

    def test_obsolete_term_reports_its_replacement_as_a_curie(self):
        term = self.live_term(
            label="obsolete_parasitic infection",
            ontology_name="efo",
            is_obsolete=True,
            term_replaced_by="http://purl.obolibrary.org/obo/MONDO_0005135",
            _home_ontology="efo",
        )
        result = self.check(term, curie="EFO:0001067")
        self.assertEqual(result["status"], "obsolete")
        self.assertEqual(result["replacement"], "MONDO:0005135")

    def test_obsolete_without_replacement_says_so(self):
        result = self.check(self.live_term(is_obsolete=True))
        self.assertEqual(result["status"], "obsolete")
        self.assertEqual(result["replacement"], "")
        self.assertIn("no stated replacement", result["detail"])

    def test_label_mismatch_reports_both_labels(self):
        result = self.check(self.live_term(), label="kidney")
        self.assertEqual(result["status"], "label_mismatch")
        self.assertIn("kidney", result["detail"])
        self.assertIn("liver", result["detail"])

    def test_label_comparison_is_case_insensitive(self):
        self.assertEqual(self.check(self.live_term(), label="LIVER")["status"], "ok")

    def test_synonym_label_warns_and_names_the_primary_label(self):
        result = self.check(self.live_term(), label="iecur")
        self.assertEqual(result["status"], "matched_synonym")
        self.assertIn("primary label is 'liver'", result["detail"])

    def test_wrong_ontology_is_caught(self):
        term = self.live_term(label="hepatocyte", ontology_name="cl", _home_ontology="cl")
        result = self.check(term, curie="CL:0000182", ontologies={"uberon"})
        self.assertEqual(result["status"], "wrong_ontology")

    def test_branch_membership_passes_and_fails(self):
        term = self.live_term()
        ok = self.check(term, branch="UBERON:0000465", ancestors={"UBERON:0000465"})
        self.assertEqual(ok["status"], "ok")
        bad = self.check(term, branch="CL:0000000", ancestors={"UBERON:0000465"})
        self.assertEqual(bad["status"], "wrong_branch")

    def test_a_term_is_in_its_own_branch(self):
        result = self.check(self.live_term(), branch="UBERON:0002107", ancestors=set())
        self.assertEqual(result["status"], "ok")

    def test_imported_only_term_warns(self):
        term = self.live_term(ontology_name="efo", is_defining_ontology=False,
                              _home_ontology="mondo", _resolved_via="iri")
        result = self.check(term, curie="MONDO:0000001")
        self.assertEqual(result["status"], "imported_only")
        self.assertIn("mondo does not define", result["detail"])

    def test_non_class_terms_warn(self):
        result = self.check(self.live_term(type="property"))
        self.assertEqual(result["status"], "not_a_class")

    def test_failure_beats_warning(self):
        """A wrong branch outranks a synonym-label warning."""
        result = self.check(self.live_term(), label="iecur", branch="CL:0000000",
                            ancestors={"UBERON:0000465"})
        self.assertEqual(result["status"], "wrong_branch")


class InputParsingTests(unittest.TestCase):
    def parse(self, text, terms=()):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "in.tsv"
            path.write_text(text, encoding="utf-8")
            args = validate_terms.build_parser().parse_args(
                [*terms, "--input", str(path)]
            )
            return validate_terms.read_pairs(args)

    def test_tsv_with_headers(self):
        pairs = self.parse("id\tlabel\nUBERON:0002107\tliver\nCL:0000182\thepatocyte\n")
        self.assertEqual(pairs, [("UBERON:0002107", "liver"), ("CL:0000182", "hepatocyte")])

    def test_alternate_header_names(self):
        pairs = self.parse("ontology_term_id\tterm_label\nUBERON:0002107\tliver\n")
        self.assertEqual(pairs, [("UBERON:0002107", "liver")])

    def test_csv_is_detected(self):
        pairs = self.parse("id,label\nUBERON:0002107,liver\n")
        self.assertEqual(pairs, [("UBERON:0002107", "liver")])

    def test_headerless_two_columns(self):
        pairs = self.parse("UBERON:0002107\tliver\n")
        self.assertEqual(pairs, [("UBERON:0002107", "liver")])

    def test_single_column_has_no_labels(self):
        pairs = self.parse("UBERON:0002107\nCL:0000182\n")
        self.assertEqual(pairs, [("UBERON:0002107", None), ("CL:0000182", None)])

    def test_id_only_header_without_label_column(self):
        pairs = self.parse("curie\nUBERON:0002107\n")
        self.assertEqual(pairs, [("UBERON:0002107", None)])

    def test_comment_and_blank_lines_are_skipped(self):
        pairs = self.parse("id\tlabel\n# a note\n\nUBERON:0002107\tliver\n")
        self.assertEqual(pairs, [("UBERON:0002107", "liver")])

    def test_positional_terms_merge_with_file_terms(self):
        pairs = self.parse("id\nCL:0000182\n", terms=["UBERON:0002107"])
        self.assertEqual(pairs, [("UBERON:0002107", None), ("CL:0000182", None)])

    def test_resolve_deduplicates_queries_preserving_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "q.txt"
            path.write_text("liver\n# comment\nheart\nliver\n", encoding="utf-8")
            args = resolve_terms.build_parser().parse_args(["--input", str(path)])
            self.assertEqual(resolve_terms.read_inputs(args), ["liver", "heart"])


class ExitCodeTests(unittest.TestCase):
    def run_validate(self, argv, results):
        with patch.object(validate_terms, "check_term", side_effect=results), \
             redirect_stdout(io.StringIO()) as out:
            code = validate_terms.main(argv)
        return code, out.getvalue()

    def result(self, status):
        return {"id": "X:1", "status": status, "actual_label": "", "ontology": "",
                "replacement": "", "detail": ""}

    def test_clean_run_exits_zero(self):
        code, _ = self.run_validate(["UBERON:0002107"], [self.result("ok")])
        self.assertEqual(code, 0)

    def test_failure_exits_one(self):
        code, _ = self.run_validate(["UBERON:9999999"], [self.result("not_found")])
        self.assertEqual(code, 1)

    def test_warning_alone_exits_zero(self):
        code, _ = self.run_validate(["UBERON:0002107"], [self.result("matched_synonym")])
        self.assertEqual(code, 0)

    def test_strict_makes_warnings_fail(self):
        code, _ = self.run_validate(
            ["UBERON:0002107", "--strict"], [self.result("matched_synonym")]
        )
        self.assertEqual(code, 1)

    def test_no_input_exits_two(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(validate_terms.main([]), 2)

    def test_bad_branch_curie_exits_two(self):
        with redirect_stdout(io.StringIO()):
            code = validate_terms.main(["UBERON:0002107", "--branch", "liver"])
        self.assertEqual(code, 2)

    def test_tsv_output_has_the_documented_columns(self):
        _, output = self.run_validate(["UBERON:0002107"], [self.result("ok")])
        self.assertEqual(output.splitlines()[0].split("\t"), list(validate_terms.TSV_COLUMNS))

    def test_json_output_is_a_list_of_records(self):
        _, output = self.run_validate(
            ["UBERON:0002107", "--format", "json"], [self.result("ok")]
        )
        self.assertEqual(json.loads(output)[0]["status"], "ok")


HP_RESOURCE = {
    "prefix": "hp",
    "preferred_prefix": "HP",
    "name": "Human Phenotype Ontology",
    "pattern": r"^\d{7}$",
    "example": "0011140",
    "uri_format": "http://purl.obolibrary.org/obo/HP_$1",
    "synonyms": ["hpo"],
    "mappings": {"ols": "hp", "ontobee": "HP", "miriam": "hp"},
}


class PrefixHelperTests(unittest.TestCase):
    def test_split_query_handles_prefix_and_curie(self):
        self.assertEqual(id_client.split_query("HP"), ("HP", None))
        self.assertEqual(id_client.split_query("HP:0001250"), ("HP", "0001250"))
        self.assertEqual(id_client.split_query("  HPO:0001250 "), ("HPO", "0001250"))

    def test_local_pattern_is_the_local_id_only(self):
        self.assertTrue(id_client.local_matches_pattern("0001250", r"^\d{7}$"))
        self.assertFalse(
            id_client.local_matches_pattern("HP:0001250", r"^\d{7}$"),
            "the Bioregistry pattern applies to the local id, not the CURIE",
        )
        self.assertIsNone(id_client.local_matches_pattern("0001250", None))

    def test_uri_format_and_ontobee_url(self):
        iri = id_client.apply_uri_format(HP_RESOURCE["uri_format"], "0001250")
        self.assertEqual(iri, "http://purl.obolibrary.org/obo/HP_0001250")
        page = id_client.ontobee_url("HP", iri)
        self.assertTrue(page.startswith("https://ontobee.org/ontology/HP?iri="))
        self.assertIn("HP_0001250", page)

    def test_identifiers_resolver_url_keeps_the_colon(self):
        url = id_client.identifiers_resolver_url("HP:0001250")
        self.assertEqual(url, "https://resolver.api.identifiers.org/HP:0001250")
        self.assertNotIn("%3A", url)

    def test_preferred_prefix_is_ok_in_either_case(self):
        for query in ("HP", "hp"):
            result = id_client.classify_prefix_query(query, HP_RESOURCE, local=None)
            self.assertEqual(result["status"], "ok", query)
            self.assertEqual(result["preferred_prefix"], "HP")

    def test_synonym_prefix_is_flagged(self):
        result = id_client.classify_prefix_query("HPO", HP_RESOURCE, local=None)
        self.assertEqual(result["status"], "synonym_prefix")
        self.assertIn("preferred prefix HP", result["detail"])

    def test_synonym_curie_still_builds_the_preferred_form(self):
        result = id_client.classify_prefix_query("HPO:0001250", HP_RESOURCE, local="0001250")
        self.assertEqual(result["status"], "synonym_prefix")
        self.assertEqual(result["canonical_curie"], "HP:0001250")
        self.assertEqual(result["default_iri"], "http://purl.obolibrary.org/obo/HP_0001250")

    def test_invalid_local_id_is_caught_without_a_network_call(self):
        result = id_client.classify_prefix_query("HP:notanid", HP_RESOURCE, local="notanid")
        self.assertEqual(result["status"], "invalid_local")
        self.assertEqual(result["canonical_curie"], "")

    def test_unknown_prefix(self):
        result = id_client.classify_prefix_query("NOTAREAL", None, local=None)
        self.assertEqual(result["status"], "unknown_prefix")

    def test_reference_detail_overrides_for_invalid_local(self):
        result = id_client.classify_prefix_query(
            "HP:abc",
            HP_RESOURCE,
            local="abc",
            reference_detail="invalid identifier: hp:abc for pattern ^\\d{7}$",
        )
        self.assertEqual(result["status"], "invalid_local")
        self.assertIn("invalid identifier", result["detail"])


class LookupPrefixCliTests(unittest.TestCase):
    def test_malformed_input_does_not_hit_the_network(self):
        with patch.object(lookup_prefix, "get_resource") as fetch:
            result = lookup_prefix.lookup_one("not a curie!!!")
        fetch.assert_not_called()
        self.assertEqual(result["status"], "malformed")

    def test_lookup_uses_bioregistry_then_identifiers(self):
        with patch.object(lookup_prefix, "get_resource", return_value=HP_RESOURCE), \
             patch.object(lookup_prefix, "get_reference", return_value={"providers": {}}), \
             patch.object(
                 lookup_prefix,
                 "resolve_identifiers",
                 return_value={"errorMessage": None, "payload": {"resolvedResources": []}},
             ):
            result = lookup_prefix.lookup_one("HP:0001250")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["canonical_curie"], "HP:0001250")

    def test_unknown_prefix_from_404(self):
        with patch.object(
            lookup_prefix,
            "get_resource",
            side_effect=id_client.NotFoundError("Prefix not found: xyz", "url"),
        ):
            result = lookup_prefix.lookup_one("xyz")
        self.assertEqual(result["status"], "unknown_prefix")

    def test_no_input_exits_two(self):
        # pytest captures stdin, so isatty() is False unless we force a TTY.
        with patch.object(sys.stdin, "isatty", return_value=True), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(lookup_prefix.main([]), 2)


class ZoomaHelperTests(unittest.TestCase):
    def test_filter_requires_an_ontology(self):
        with self.assertRaises(zooma_client.ZoomaError):
            zooma_client.ontology_filter([])
        self.assertEqual(
            zooma_client.ontology_filter(["UBERON", "CL"]),
            "required:[none],ontologies:[uberon,cl]",
        )

    def test_flatten_hit_converts_obo_iris_and_flags_weak_confidence(self):
        hit = {
            "confidence": "MEDIUM",
            "semanticTags": ["http://purl.obolibrary.org/obo/CL_2000001"],
            "annotatedProperty": {"propertyType": "unspecified", "propertyValue": "PBMC"},
            "provenance": {
                "evidence": "OLS_TEXT_TAGGER",
                "source": {"name": "cl"},
            },
        }
        rows = zooma_client.flatten_hit(hit)
        self.assertEqual(rows[0]["curie"], "CL:2000001")
        self.assertFalse(rows[0]["safe"])
        self.assertEqual(rows[0]["confidence"], "MEDIUM")

    def test_high_confidence_is_safe(self):
        hit = {
            "confidence": "HIGH",
            "semanticTags": ["http://purl.obolibrary.org/obo/UBERON_0002107"],
            "annotatedProperty": {},
            "provenance": {},
        }
        self.assertTrue(zooma_client.flatten_hit(hit)[0]["safe"])


class MapTermsTests(unittest.TestCase):
    def test_safe_only_drops_weak_hits(self):
        hits = [
            {
                "confidence": "HIGH",
                "semanticTags": ["http://purl.obolibrary.org/obo/CL_2000001"],
                "annotatedProperty": {},
                "provenance": {},
            },
            {
                "confidence": "MEDIUM",
                "semanticTags": ["http://purl.obolibrary.org/obo/CL_0000784"],
                "annotatedProperty": {},
                "provenance": {},
            },
        ]
        with patch.object(map_terms, "annotate", return_value=hits):
            result = map_terms.map_one(
                "PBMC", ontologies=["cl"], property_type=None, top=5, safe_only=True
            )
        self.assertEqual([c["curie"] for c in result["candidates"]], ["CL:2000001"])

    def test_unresolved_row_has_no_curie(self):
        rows = map_terms.to_rows([{"query": "zzz", "candidates": []}])
        self.assertEqual(rows[0]["match_type"], "unresolved")
        self.assertEqual(rows[0]["curie"], "")

    def test_missing_ontology_exits_two(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(map_terms.main(["PBMC", "--ontology", ""]), 2)

    def test_no_input_exits_two(self):
        with patch.object(sys.stdin, "isatty", return_value=True), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(map_terms.main(["--ontology", "cl"]), 2)


@unittest.skipUnless(LIVE, "set OLS_LIVE_TESTS=1 to run tests that call EBI OLS")
class LiveApiTests(unittest.TestCase):
    """Pin the live-service behaviour the offline logic assumes."""

    def test_exact_true_alone_is_not_exact_label_matching(self):
        loose = ols_client.search("liver", ontology="uberon", query_fields=None, rows=5)
        tight = ols_client.search("liver", ontology="uberon", query_fields="label", rows=5)
        self.assertGreater(len(loose), len(tight))
        self.assertEqual([d["label"] for d in tight], ["liver"])

    def test_obsolete_term_carries_its_replacement(self):
        term = ols_client.term_detail("EFO:0001067")
        self.assertTrue(term["is_obsolete"])
        self.assertEqual(
            ols_client.iri_to_curie(term["term_replaced_by"]), "MONDO:0005135"
        )

    def test_search_cannot_report_obsolescence(self):
        docs = ols_client.search(
            "obsolete_parasitic infection", ontology="efo", include_obsolete=True, rows=1
        )
        self.assertTrue(docs)
        self.assertNotIn("is_obsolete", docs[0])
        self.assertNotIn("term_replaced_by", docs[0])

    def test_iri_fallback_resolves_a_term_missing_from_the_obo_id_index(self):
        term = ols_client.term_detail("MONDO:0000001")
        self.assertIsNotNone(term, "MONDO:0000001 is live but unindexed by obo_id")
        self.assertEqual(term["_resolved_via"], "iri")

    def test_orphanet_override_resolves(self):
        term = ols_client.term_detail("Orphanet:558")
        self.assertEqual(term["label"], "Marfan syndrome")

    def test_unknown_id_resolves_to_nothing(self):
        self.assertIsNone(ols_client.term_detail("UBERON:9999999"))


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

if __name__ == "__main__":
    unittest.main()
