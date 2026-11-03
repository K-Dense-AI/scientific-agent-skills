"""Tests for the verify-citations skill.

Live provider access is not used in CI. The suite covers parsing, matching,
and reports offline, with mocked provider responses for the HTTP error and
candidate-selection paths.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "verify-citations"
SCRIPTS = SKILL_ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import _common  # noqa: E402
import check_retractions  # noqa: E402
import generate_report  # noqa: E402
import parse_references  # noqa: E402
import verify_references  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


class IdentifierNormalisationTests(unittest.TestCase):
    def test_doi_url_prefixes_are_stripped(self) -> None:
        for raw in (
            "https://doi.org/10.1038/s41586-021-03819-2",
            "http://dx.doi.org/10.1038/s41586-021-03819-2",
            "doi: 10.1038/s41586-021-03819-2",
            "DOI:10.1038/S41586-021-03819-2",
        ):
            with self.subTest(raw=raw):
                self.assertEqual(
                    _common.normalize_doi(raw), "10.1038/s41586-021-03819-2"
                )

    def test_bare_doi_is_found_inside_text(self) -> None:
        text = "Nature 596, 583-589 (2021). 10.1038/s41586-021-03819-2"
        self.assertEqual(
            _common.normalize_doi(text), "10.1038/s41586-021-03819-2"
        )

    def test_trailing_sentence_punctuation_is_not_part_of_the_doi(self) -> None:
        self.assertEqual(
            _common.normalize_doi("Nature. 10.1038/s41586-021-03819-2."),
            "10.1038/s41586-021-03819-2",
        )

    def test_a_missing_doi_returns_none_not_an_empty_string(self) -> None:
        self.assertIsNone(_common.normalize_doi("no identifier here"))
        self.assertIsNone(_common.normalize_doi(None))

    def test_parenthesized_doi_suffix_is_preserved(self) -> None:
        self.assertEqual(
            _common.normalize_doi("10.1016/S0140-6736(97)11096-0"),
            "10.1016/s0140-6736(97)11096-0",
        )
        self.assertEqual(
            _common.normalize_doi("(10.1016/S0140-6736(97)11096-0)."),
            "10.1016/s0140-6736(97)11096-0",
        )

    def test_arxiv_ids_new_and_old(self) -> None:
        self.assertEqual(_common.extract_arxiv_id("arXiv:1706.03762"), "1706.03762")
        self.assertEqual(
            _common.extract_arxiv_id("arXiv:2401.12345v2"), "2401.12345"
        )
        self.assertEqual(
            _common.extract_arxiv_id("arXiv:cs/0112017"), "cs/0112017"
        )
        self.assertIsNone(_common.extract_arxiv_id("not an arxiv id"))

    def test_pmid_extraction(self) -> None:
        self.assertEqual(_common.extract_pmid("PMID: 35688944"), "35688944")
        self.assertIsNone(_common.extract_pmid("no pmid"))

    def test_parenthesized_doi_is_collected_by_retraction_sweep(self) -> None:
        text = "A citation (10.1016/S0140-6736(97)11096-0)."
        path = FIXTURES.parent / "parenthesized-doi.txt"
        path.write_text(text, encoding="utf-8")
        self.addCleanup(path.unlink)
        self.assertEqual(
            check_retractions.collect_dois([str(path)], []),
            ["10.1016/s0140-6736(97)11096-0"],
        )


class TitleMatchingTests(unittest.TestCase):
    def test_identical_and_case_punct_variants_score_one(self) -> None:
        base = "Attention Is All You Need"
        self.assertEqual(_common.title_similarity(base, base), 1.0)
        self.assertEqual(
            _common.title_similarity(base, "attention  is all you  need!"), 1.0
        )

    def test_retracted_status_prefix_is_ignored_for_title_matching(self) -> None:
        title = "Ileal-lymphoid nodular hyperplasia in children"
        self.assertEqual(
            _common.title_similarity(title, f"RETRACTED: {title}"), 1.0
        )

    def test_latex_and_math_are_folded_before_comparison(self) -> None:
        self.assertEqual(
            _common.title_similarity(
                "The \\emph{Invariant} Measure of $L^2$ Flows",
                "The Invariant Measure of Flows",
            ),
            1.0,
        )

    def test_subtitles_do_not_split_a_match(self) -> None:
        score = _common.title_similarity(
            "Highly accurate protein structure prediction with AlphaFold",
            "Highly accurate protein structure prediction",
        )
        self.assertGreaterEqual(score, _common.MATCH_THRESHOLD
                                if hasattr(_common, "MATCH_THRESHOLD") else 0.85)

    def test_unrelated_titles_score_low(self) -> None:
        score = _common.title_similarity(
            "Attention Is All You Need", "Quantum leverage in protein folding"
        )
        self.assertLess(score, 0.5)

    def test_empty_titles_never_match(self) -> None:
        self.assertEqual(_common.title_similarity("", "anything"), 0.0)
        self.assertEqual(_common.title_similarity(None, None), 0.0)

    def test_short_containment_does_not_clear_match_threshold(self) -> None:
        score = _common.title_similarity(
            "Deep learning for protein structure prediction",
            "Deep learning for protein structure prediction with AlphaFold and templates in modern biology research",
        )
        self.assertLess(score, 0.85)


class MetadataComparisonTests(unittest.TestCase):
    def test_agreeing_records_produce_no_reasons(self) -> None:
        reasons = _common.compare_metadata(
            {"title": "Attention Is All You Need", "year": "2017",
             "authors": "Vaswani, Ashish"},
            {"title": "Attention is all you need", "year": 2017,
             "author": [{"family": "Vaswani", "given": "Ashish"}]},
        )
        self.assertEqual(reasons, [])

    def test_wrong_year_is_reported(self) -> None:
        reasons = _common.compare_metadata(
            {"title": "Attention Is All You Need", "year": "2017"},
            {"title": "Attention is all you need", "year": 2014,
             "author": [{"family": "Vaswani"}]},
        )
        self.assertTrue(any("year" in reason for reason in reasons))

    def test_wrong_first_author_is_reported(self) -> None:
        reasons = _common.compare_metadata(
            {"title": "Attention Is All You Need", "year": "2017",
             "authors": "Zhang, L."},
            {"title": "Attention is all you need", "year": 2017,
             "author": [{"family": "Vaswani"}]},
        )
        self.assertTrue(any("author" in reason for reason in reasons))

    def test_year_tolerance_accepts_off_by_one(self) -> None:
        reasons = _common.compare_metadata(
            {"title": "A Paper", "year": "2020", "authors": "Roe, J."},
            {"title": "A paper", "year": 2021, "author": [{"family": "Roe"}]},
        )
        self.assertEqual(reasons, [])

    def test_initials_first_and_vancouver_authors_are_parsed(self) -> None:
        resolved = {
            "title": "A Paper", "year": 2021,
            "author": [{"family": "Jumper"}],
        }
        for stated in ("J. Jumper, R. Evans", "Jumper J, Evans R"):
            with self.subTest(stated=stated):
                self.assertEqual(
                    _common.compare_metadata(
                        {"title": "A Paper", "year": 2021, "authors": stated},
                        resolved,
                    ),
                    [],
                )

    def test_lone_initial_is_not_treated_as_an_author_mismatch(self) -> None:
        self.assertEqual(
            _common.compare_metadata(
                {"title": "A Paper", "year": 2021, "authors": "J."},
                {"title": "A Paper", "year": 2021,
                 "author": [{"family": "Jumper"}]},
            ),
            [],
        )


class BibTeXParsingTests(unittest.TestCase):
    def test_fixture_entries_parse_with_identifiers(self) -> None:
        text = (FIXTURES / "sample.bib").read_text(encoding="utf-8")
        entries = parse_references.parse_bibtex(text)
        keys = [entry["key"] for entry in entries]
        self.assertEqual(keys, ["jumper2021", "vaswani2017", "singleline"])
        jumper = entries[0]
        self.assertEqual(jumper["doi"], "10.1038/s41586-021-03819-2")
        self.assertEqual(jumper["year"], "2021")
        self.assertIn("AlphaFold", jumper["title"])
        vaswani = entries[1]
        self.assertEqual(vaswani["arxiv_id"], "1706.03762")

    def test_comments_and_preamble_are_skipped(self) -> None:
        text = "@preamble{\"stuff\"}\n@comment{note}\n@article{a, title = {T}}"
        entries = parse_references.parse_bibtex(text)
        self.assertEqual([entry["key"] for entry in entries], ["a"])

    def test_single_line_entry_is_captured(self) -> None:
        text = "@misc{s, title = {T}, year = {2020}, doi = {10.1000/xyz123}}"
        entries = parse_references.parse_bibtex(text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["doi"], "10.1000/xyz123")

    def test_nested_braces_and_unquoted_values_are_parsed(self) -> None:
        text = "@article{x, title = {Foo {Bar}, baz}, year = 2021, doi = {10.1000/x}}"
        entry = parse_references.parse_bibtex(text)[0]
        self.assertEqual(entry["title"], "Foo {Bar}, baz")
        self.assertEqual(entry["year"], "2021")


class MarkdownParsingTests(unittest.TestCase):
    def test_fixture_references_are_extracted_in_order(self) -> None:
        text = (FIXTURES / "sample_manuscript.md").read_text(encoding="utf-8")
        entries = parse_references.parse_markdown(text)
        self.assertEqual(len(entries), 4)
        self.assertEqual([entry["key"] for entry in entries], ["1", "2", "3", "4"])

    def test_identifiers_survive_extraction(self) -> None:
        text = (FIXTURES / "sample_manuscript.md").read_text(encoding="utf-8")
        entries = parse_references.parse_markdown(text)
        held = entries[0]
        self.assertEqual(held["doi"], "10.1080/24733938.2025.1234567")
        self.assertEqual(held["year"], "2025")
        vaswani = entries[2]
        self.assertEqual(vaswani["arxiv_id"], "1706.03762")

    def test_titles_are_extracted_from_numbered_references(self) -> None:
        text = (FIXTURES / "sample_manuscript.md").read_text(encoding="utf-8")
        entries = parse_references.parse_markdown(text)
        self.assertIn("Attention Is All You Need", entries[2]["title"])
        self.assertIn("VARS", entries[0]["title"])

    def test_text_before_the_references_heading_is_not_parsed(self) -> None:
        text = (FIXTURES / "sample_manuscript.md").read_text(encoding="utf-8")
        entries = parse_references.parse_markdown(text)
        self.assertFalse(
            any("Vision-Language" in (entry["title"] or "") for entry in entries)
        )


class LaTeXParsingTests(unittest.TestCase):
    def test_bibitem_entries_with_labels_parse(self) -> None:
        text = (
            "\\begin{thebibliography}{9}\n"
            "% a comment\n"
            "\\bibitem{vaswani2017} Vaswani, A. (2017). Attention Is All You Need. NeurIPS.\n"
            "\\bibitem[Jumper2021]{jumper21} Jumper, J. (2021). Protein structure. Nature.\n"
            "\\end{thebibliography}\n"
        )
        entries = parse_references.parse_latex(text)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["key"], "vaswani2017")
        self.assertEqual(entries[1]["key"], "jumper21")
        self.assertIn("Attention Is All You Need", entries[0]["title"])

    def test_latex_markup_is_rendered_down(self) -> None:
        text = "\\bibitem{e} Einstein, A. (1905). On the \\emph{Electrodynamics} of Moving Bodies. Ann. Phys.\n"
        entries = parse_references.parse_latex(text)
        self.assertEqual(entries[0]["title"], "On the Electrodynamics of Moving Bodies")


class InTextCitationTests(unittest.TestCase):
    def test_checkable_sentences_with_markers_are_extracted(self) -> None:
        text = (
            "The MVFoul winner reached 44.76 combined balanced accuracy [2]. "
            "Our method uses a vision-language model. Referees agree weakly "
            "\"severity is a distribution\" (Held et al., 2025)."
        )
        found = parse_references.extract_in_text_citations(text)
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]["markers"], ["[2]"])
        self.assertIn("44.76", found[0]["sentence"])
        self.assertEqual(found[1]["quote"], "severity is a distribution")

    def test_plain_sentences_without_markers_are_ignored(self) -> None:
        text = "The model has 94.5 percent accuracy. Nothing here is cited."
        self.assertEqual(parse_references.extract_in_text_citations(text), [])


class VerdictLogicTests(unittest.TestCase):
    def test_entry_without_identifier_or_title_is_skipped(self) -> None:
        result = verify_references.resolve_reference({"key": "9", "type": "text"})
        self.assertEqual(result["verdict"], _common.SKIPPED)

    def test_dead_doi_is_retained_when_title_fallback_resolves(self) -> None:
        original_fetch = verify_references._fetch_by_doi
        original_search = verify_references._search_crossref
        original_pause = verify_references.REQUEST_PAUSE
        try:
            verify_references._fetch_by_doi = lambda doi: None
            verify_references._search_crossref = lambda title: [{
                "title": title,
                "year": 2021,
                "author": [{"family": "Roe"}],
                "type": "journal-article",
            }]
            verify_references.REQUEST_PAUSE = 0
            result = verify_references.resolve_reference({
                "key": "1", "doi": "10.1080/24733938.2025.1234567",
                "title": "A Real Scientific Paper", "year": "2021", "authors": "Roe, J.",
            })
        finally:
            verify_references._fetch_by_doi = original_fetch
            verify_references._search_crossref = original_search
            verify_references.REQUEST_PAUSE = original_pause
        self.assertEqual(result["verdict"], _common.METADATA_MISMATCH)
        self.assertTrue(any("DOI not found" in reason for reason in result["mismatch_reasons"]))

    def test_search_candidates_drop_components_and_keep_retraction_metadata(self) -> None:
        original_fetch = verify_references.fetch_json
        try:
            verify_references.fetch_json = lambda *args, **kwargs: {
                "message": {
                    "items": [
                        {"title": ["A Supplement"], "type": "component"},
                        {"title": ["Metadata Free"], "type": "journal-article"},
                        {
                            "title": ["A Retracted Paper"],
                            "type": "journal-article",
                            "author": [{"family": "Roe"}],
                            "issued": {"date-parts": [[2021]]},
                            "updated-by": [{"type": "retraction", "DOI": "10.5555/notice"}],
                        },
                    ]
                }
            }
            records = verify_references._search_crossref("A Retracted Paper")
        finally:
            verify_references.fetch_json = original_fetch
        assert len(records) == 1
        assert records[0]["_retraction"] == "updated-by: retraction (10.5555/notice)"

    def test_search_retraction_is_preserved(self) -> None:
        original_search = verify_references._search_crossref
        original_pause = verify_references.REQUEST_PAUSE
        try:
            verify_references._search_crossref = lambda title: [{
                "title": title,
                "year": 2021,
                "author": [{"family": "Roe"}],
                "type": "journal-article",
                "_retraction": "updated-by: retraction (10.5555/notice)",
            }]
            verify_references.REQUEST_PAUSE = 0
            result = verify_references.resolve_reference({
                "key": "1", "title": "A Real Scientific Paper", "year": "2021", "authors": "Roe, J.",
            })
        finally:
            verify_references._search_crossref = original_search
            verify_references.REQUEST_PAUSE = original_pause
        self.assertEqual(result["verdict"], _common.RETRACTED)
        self.assertIn("retraction", result["retraction_detail"])

    def test_title_search_uses_author_and_year_to_select_retracted_original(self) -> None:
        title = (
            "Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and "
            "pervasive developmental disorder in children"
        )
        notice_doi = "10.1016/s0140-6736(10)60175-4"
        original_doi = "10.1016/s0140-6736(97)11096-0"
        letter_doi = "10.1016/s0140-6736(05)77837-5"
        items = [
            {
                "title": [f"Retraction—{title}"], "type": "journal-article",
                "DOI": notice_doi,
                "author": [{"family": "The Editors of The Lancet"}],
                "issued": {"date-parts": [[2010, 2]]},
                "update-to": [{"type": "retraction", "DOI": original_doi}],
            },
            {
                "title": [title], "type": "journal-article", "DOI": letter_doi,
                "author": [{"family": "Sabra"}],
                "issued": {"date-parts": [[1998, 7]]},
            },
            {
                "title": [f"RETRACTED: {title}"], "type": "journal-article",
                "DOI": original_doi,
                "author": [{"family": "Wakefield"}],
                "issued": {"date-parts": [[1998, 2]]},
                "updated-by": [{"type": "retraction", "DOI": notice_doi}],
            },
        ]
        original_pause = verify_references.REQUEST_PAUSE
        try:
            verify_references.REQUEST_PAUSE = 0
            for ordered_items in (items, list(reversed(items))):
                with self.subTest(order=[item["DOI"] for item in ordered_items]):
                    with patch.object(
                        verify_references, "fetch_json",
                        return_value={"message": {"items": ordered_items}},
                    ):
                        result = verify_references.resolve_reference({
                            "key": "wakefield", "title": title, "year": "1998",
                            "authors": "Wakefield, A. J.",
                        })
                    self.assertEqual(result["verdict"], _common.RETRACTED)
                    self.assertEqual(result["resolved"]["doi"], original_doi)
        finally:
            verify_references.REQUEST_PAUSE = original_pause

    def test_title_search_returns_unresolved_when_shared_title_is_ambiguous(self) -> None:
        title = (
            "Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and "
            "pervasive developmental disorder in children"
        )
        items = [
            {
                "title": [title], "type": "journal-article",
                "DOI": "10.1016/s0140-6736(05)77837-5",
                "author": [{"family": "Sabra"}],
                "issued": {"date-parts": [[1998, 7]]},
            },
            {
                "title": [f"RETRACTED: {title}"], "type": "journal-article",
                "DOI": "10.1016/s0140-6736(97)11096-0",
                "author": [{"family": "Wakefield"}],
                "issued": {"date-parts": [[1998, 2]]},
                "updated-by": [{"type": "retraction", "DOI": "10.5555/notice"}],
            },
        ]
        original_pause = verify_references.REQUEST_PAUSE
        try:
            verify_references.REQUEST_PAUSE = 0
            with patch.object(
                verify_references, "fetch_json",
                return_value={"message": {"items": items}},
            ):
                result = verify_references.resolve_reference({"key": "ambiguous", "title": title})
        finally:
            verify_references.REQUEST_PAUSE = original_pause
        self.assertEqual(result["verdict"], _common.UNRESOLVED)
        self.assertIn("ambiguous Crossref title match", result["detail"])
        self.assertIn("10.1016/s0140-6736(05)77837-5", result["detail"])
        self.assertIn("10.1016/s0140-6736(97)11096-0", result["detail"])

    def test_timeout_is_unresolved_and_later_references_are_kept(self) -> None:
        successful_response = Mock(status_code=200)
        successful_response.json.return_value = {
            "message": {
                "title": ["A Successful Paper"],
                "issued": {"date-parts": [[2021]]},
                "author": [{"family": "Roe"}],
                "DOI": "10.5555/success",
            }
        }
        original_pause = verify_references.REQUEST_PAUSE
        try:
            verify_references.REQUEST_PAUSE = 0
            with patch.object(
                _common.requests, "get",
                side_effect=[_common.requests.exceptions.Timeout("timed out"), successful_response],
            ) as get:
                results = verify_references.verify_all([
                    {"key": "timeout", "doi": "10.5555/timeout"},
                    {"key": "success", "doi": "10.5555/success",
                     "title": "A Successful Paper", "year": "2021", "authors": "Roe, J."},
                ])
        finally:
            verify_references.REQUEST_PAUSE = original_pause
        self.assertEqual(get.call_count, 2)
        self.assertEqual([item["verdict"] for item in results], [
            _common.UNRESOLVED, _common.VERIFIED,
        ])
        report = generate_report.render_report(results)
        self.assertIn("timeout", report)
        self.assertIn("A Successful Paper", report)

    def test_connection_failure_is_normalized(self) -> None:
        with patch.object(
            _common.requests, "get",
            side_effect=_common.requests.exceptions.ConnectionError("offline"),
        ):
            with self.assertRaisesRegex(RuntimeError, "request failed"):
                _common.fetch_json("https://api.crossref.org/works")

    def test_invalid_json_is_normalized(self) -> None:
        response = Mock(status_code=200)
        response.json.side_effect = ValueError("invalid JSON")
        with patch.object(_common.requests, "get", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "invalid JSON response"):
                _common.fetch_json("https://api.crossref.org/works")

    def test_malformed_arxiv_xml_is_normalized(self) -> None:
        with patch.object(
            verify_references, "fetch_response",
            return_value=SimpleNamespace(text="<feed><entry>"),
        ):
            with self.assertRaisesRegex(RuntimeError, "invalid XML response"):
                verify_references._fetch_arxiv("2401.12345")

    def test_taxonomy_constants_are_shared(self) -> None:
        # The report renderer and the verifier must agree on verdict strings.
        for verdict in (
            _common.VERIFIED,
            _common.METADATA_MISMATCH,
            _common.RETRACTED,
            _common.NOT_FOUND,
            _common.UNRESOLVED,
            _common.SKIPPED,
        ):
            self.assertIn(verdict, _common.VERDICT_ORDER)
            self.assertIn(verdict, generate_report._VERDICT_GLYPH)


class ReportRenderingTests(unittest.TestCase):
    RESULTS = [
        {"key": "1", "title": "A Real Paper", "year": "2021",
         "verdict": "verified",
         "resolved": {"title": "A Real Paper", "year": 2021, "container": "Nature"}},
        {"key": "2", "title": "Quantum leverage in protein folding",
         "verdict": "not-found", "doi": "10.5555/fake",
         "detail": "no record found in any queried provider",
         "resolved": {}},
        {"key": "3", "title": "A Retracted Study", "verdict": "retracted",
         "resolved": {"title": "A Retracted Study", "year": 2019},
         "retraction_detail": "update-to: retraction (10.5555/retract)"},
        {"key": "4", "title": "A Misdated Paper", "verdict": "metadata-mismatch",
         "resolved": {"title": "A Misdated Paper", "year": 2013},
         "mismatch_reasons": ["year mismatch: stated 2020 vs resolved 2013"]},
    ]

    def test_report_contains_coverage_and_flagged_groups(self) -> None:
        report = generate_report.render_report(self.RESULTS)
        self.assertIn("# Citation audit", report)
        self.assertIn("**coverage:** 25%", report)
        self.assertIn("## retracted (1)", report)
        self.assertIn("## not-found (1)", report)
        self.assertIn("## metadata-mismatch (1)", report)
        self.assertIn("10.5555/retract", report)
        self.assertIn("year mismatch: stated 2020 vs resolved 2013", report)

    def test_flagged_sections_come_before_the_full_table(self) -> None:
        report = generate_report.render_report(self.RESULTS)
        self.assertLess(report.index("## retracted"), report.index("## All references"))

    def test_clean_reports_say_so(self) -> None:
        report = generate_report.render_report(
            [{"key": "1", "title": "Fine", "verdict": "verified",
              "resolved": {"title": "Fine", "year": 2020}}]
        )
        self.assertNotIn("## retracted", report)
        self.assertIn("## All references", report)

    def test_empty_input_renders_a_usable_report(self) -> None:
        report = generate_report.render_report([])
        self.assertIn("No references", report)

    def test_summarize_counts_by_verdict(self) -> None:
        counts = generate_report.summarize(self.RESULTS)
        self.assertEqual(counts, {"verified": 1, "not-found": 1,
                                  "retracted": 1, "metadata-mismatch": 1})


class RetractionSweepTests(unittest.TestCase):
    def test_unknown_doi_is_not_found_when_both_providers_return_404(self) -> None:
        original_crossref = check_retractions._crossref_retraction
        original_openalex = check_retractions._openalex_retraction
        try:
            check_retractions._crossref_retraction = (
                lambda doi: (_ for _ in ()).throw(
                    RuntimeError("HTTP 404 from Crossref")
                )
            )
            check_retractions._openalex_retraction = (
                lambda doi: (_ for _ in ()).throw(
                    RuntimeError("HTTP 404 from OpenAlex")
                )
            )
            result = check_retractions.check_doi("10.5555/unknown")
        finally:
            check_retractions._crossref_retraction = original_crossref
            check_retractions._openalex_retraction = original_openalex
        self.assertEqual(result["verdict"], check_retractions.NOT_FOUND)

    def test_dois_are_collected_from_json_and_text(self) -> None:
        payload = FIXTURES.parent / "retraction_input.json"
        payload.write_text(json.dumps({"references": [
            {"doi": "10.1038/s41586-021-03819-2"},
            {"raw": "also 10.1000/abc123 here"},
        ]}), encoding="utf-8")
        self.addCleanup(payload.unlink)
        bib = FIXTURES / "sample.bib"
        dois = check_retractions.collect_dois(
            [str(payload), str(bib)], ["10.1000/dup"]
        )
        self.assertIn("10.1038/s41586-021-03819-2", dois)
        self.assertIn("10.1000/abc123", dois)
        self.assertIn("10.1038/s41586-021-03819-2", dois)
        self.assertIn("10.1000/xyz123", dois)  # from the .bib
        self.assertIn("10.1000/dup", dois)
        self.assertEqual(len(dois), len(set(dois)), "duplicates must be dropped")

    def test_a_doi_with_no_doi_shaped_text_yields_nothing(self) -> None:
        plain = FIXTURES.parent / "plain.txt"
        plain.write_text("no identifiers at all", encoding="utf-8")
        self.addCleanup(plain.unlink)
        self.assertEqual(check_retractions.collect_dois([str(plain)], []), [])


if __name__ == "__main__":
    unittest.main()
