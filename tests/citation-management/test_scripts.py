"""Tests for the citation-management BibTeX tooling.

Four of this skill's scripts reach the network (Crossref, PubMed, OpenAlex,
Scholar); the parsing, rendering, and validation layers underneath them are
pure text processing. The pure half is where citation errors are actually
introduced -- a page range silently rewritten, a title truncated at a nested
brace, a DOI left with its URL prefix so lookups fail, two distinct papers
merged because they share a key -- so that is what the suite drives, end to end
through real `.bib` files.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "citation-management"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _common  # noqa: E402
import format_bibtex  # noqa: E402
import validate_citations  # noqa: E402

try:  # the network-facing scripts need requests; the pure layers do not
    import extract_metadata  # noqa: E402
    import search_openalex  # noqa: E402
    import search_pubmed  # noqa: E402

    REQUESTS_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without requests
    REQUESTS_AVAILABLE = False

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

BIBLIOGRAPHY = """\
@article{jumper2021,
  author = {Jumper, John and Evans, Richard},
  title = {Highly accurate protein structure prediction},
  journal = {Nature},
  year = {2021},
  volume = {596},
  pages = {583-589},
  doi = {https://doi.org/10.1038/s41586-021-03819-2}
}

@inproceedings{vaswani2017,
  author = {Vaswani, Ashish; Shazeer, Noam},
  title = {Attention Is All You Need},
  booktitle = {NeurIPS},
  year = {2017},
  pages = {pp. 5998--6008}
}
"""


class BibTeXTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)
        self.formatter = format_bibtex.BibTeXFormatter()

    def bib(self, text: str = BIBLIOGRAPHY) -> str:
        path = self.root / "refs.bib"
        path.write_text(text, encoding="utf-8")
        return str(path)


class ParsingTests(BibTeXTestCase):
    def test_entries_are_parsed_with_type_key_and_fields(self) -> None:
        entries = self.formatter.parse_bibtex_file(self.bib())
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["key"], "jumper2021")
        self.assertEqual(entries[0]["type"], "article")
        self.assertEqual(entries[0]["fields"]["journal"], "Nature")
        self.assertEqual(entries[1]["type"], "inproceedings")

    def test_an_empty_file_parses_to_no_entries(self) -> None:
        self.assertEqual(self.formatter.parse_bibtex_file(self.bib("")), [])

    def test_comments_outside_entries_are_ignored(self) -> None:
        entries = self.formatter.parse_bibtex_file(
            self.bib(
                "% a leading comment\n"
                "@article{a,\n  title = {T},\n  year = {2020}\n}\n"
                "% a trailing comment\n"
            )
        )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["key"], "a")

    def test_an_entry_closed_on_the_same_line_is_recognised(self) -> None:
        # Single-line entries are legal BibTeX. The brace-depth parser reads
        # them; the regex it replaced anchored on `\n}` and skipped them.
        entries = self.formatter.parse_bibtex_file(
            self.bib("@article{a, title = {T}, year = {2020}}\n")
        )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["fields"]["title"], "T")

    def test_a_nested_brace_in_a_title_survives_parsing(self) -> None:
        # Capitalisation protection puts braces inside a field value. A
        # `\{([^}]*)\}` field pattern truncates at the inner brace and silently
        # corrupts the bibliography, which is what this guards.
        entries = self.formatter.parse_bibtex_file(
            self.bib(
                "@article{a,\n"
                "  title = {Prediction with {AlphaFold} and {DNA} data},\n"
                "  year = {2021}\n}\n"
            )
        )
        self.assertEqual(
            entries[0]["fields"]["title"],
            "Prediction with {AlphaFold} and {DNA} data",
        )

    def test_a_comma_inside_a_field_does_not_split_the_field(self) -> None:
        entries = self.formatter.parse_bibtex_file(
            self.bib('@article{a,\n  title = {One, two, three},\n  year = {2021}\n}\n')
        )
        self.assertEqual(entries[0]["fields"]["title"], "One, two, three")
        self.assertEqual(entries[0]["fields"]["year"], "2021")

    def test_string_and_comment_blocks_are_not_treated_as_entries(self) -> None:
        entries = self.formatter.parse_bibtex_file(
            self.bib(
                '@string{nat = "Nature"}\n'
                "@comment{not an entry}\n"
                "@article{a,\n  title = {T},\n  year = {2021}\n}\n"
            )
        )
        self.assertEqual([e["key"] for e in entries], ["a"])

    def test_quoted_field_values_are_read_as_well_as_braced_ones(self) -> None:
        entries = self.formatter.parse_bibtex_file(
            self.bib('@article{a,\n  title = "Quoted Title",\n  year = {2020}\n}\n')
        )
        self.assertEqual(entries[0]["fields"]["title"], "Quoted Title")

    def test_an_unreadable_file_returns_no_entries_rather_than_raising(self) -> None:
        self.assertEqual(
            self.formatter.parse_bibtex_file(str(self.root / "absent.bib")), []
        )


class FixTests(BibTeXTestCase):
    def _fixed_fields(self, **fields) -> dict:
        entry = {"key": "k", "type": "article", "fields": fields}
        return self.formatter.fix_common_issues(entry)["fields"]

    def test_a_single_hyphen_page_range_becomes_an_en_dash_range(self) -> None:
        # BibTeX renders `583-589` as a hyphen, not an en dash.
        self.assertEqual(self._fixed_fields(pages="583-589")["pages"], "583--589")

    def test_an_already_correct_range_is_left_alone(self) -> None:
        self.assertEqual(self._fixed_fields(pages="583--589")["pages"], "583--589")

    def test_a_pp_prefix_is_stripped(self) -> None:
        for raw in ("pp. 5998--6008", "PP.5998--6008"):
            with self.subTest(raw=raw):
                self.assertEqual(self._fixed_fields(pages=raw)["pages"], "5998--6008")

    def test_a_doi_loses_its_url_prefix(self) -> None:
        # A DOI stored as a URL fails every downstream Crossref lookup.
        for raw in (
            "https://doi.org/10.1038/x",
            "http://doi.org/10.1038/x",
            "doi:10.1038/x",
        ):
            with self.subTest(raw=raw):
                self.assertEqual(self._fixed_fields(doi=raw)["doi"], "10.1038/x")

    def test_a_bare_doi_is_untouched(self) -> None:
        self.assertEqual(self._fixed_fields(doi="10.1038/x")["doi"], "10.1038/x")

    def test_author_separators_are_normalised_to_and(self) -> None:
        self.assertEqual(
            self._fixed_fields(author="Vaswani, A.; Shazeer, N.")["author"],
            "Vaswani, A. and Shazeer, N.",
        )
        self.assertEqual(
            self._fixed_fields(author="Smith, J. & Jones, K.")["author"],
            "Smith, J. and Jones, K.",
        )

    def test_a_doubled_and_is_collapsed(self) -> None:
        self.assertEqual(
            self._fixed_fields(author="A and and B")["author"], "A and B"
        )

    def test_fixing_does_not_mutate_the_original_entry(self) -> None:
        entry = {"key": "k", "type": "article", "fields": {"pages": "1-2"}}
        self.formatter.fix_common_issues(entry)
        self.assertEqual(entry["fields"]["pages"], "1-2")

    def test_absent_fields_are_not_invented(self) -> None:
        self.assertEqual(self._fixed_fields(title="T"), {"title": "T"})


class DeduplicationTests(BibTeXTestCase):
    def _entries(self, *specs) -> list:
        return [
            {"key": key, "type": "article", "fields": fields} for key, fields in specs
        ]

    def test_entries_sharing_a_doi_collapse_to_one(self) -> None:
        entries = self._entries(
            ("a2021", {"doi": "10.1/x"}), ("b2021", {"doi": "10.1/x"})
        )
        self.assertEqual(len(self.formatter.deduplicate_entries(entries)), 1)

    def test_entries_sharing_a_citation_key_collapse_to_one(self) -> None:
        entries = self._entries(("same", {"doi": "10.1/a"}), ("same", {"doi": "10.1/b"}))
        self.assertEqual(len(self.formatter.deduplicate_entries(entries)), 1)

    def test_distinct_entries_all_survive(self) -> None:
        entries = self._entries(
            ("a", {"doi": "10.1/a"}), ("b", {"doi": "10.1/b"}), ("c", {})
        )
        self.assertEqual(len(self.formatter.deduplicate_entries(entries)), 3)

    def test_the_first_occurrence_is_kept(self) -> None:
        entries = self._entries(
            ("first", {"doi": "10.1/x", "title": "T1"}),
            ("second", {"doi": "10.1/x", "title": "T2"}),
        )
        kept = self.formatter.deduplicate_entries(entries)
        self.assertEqual(kept[0]["key"], "first")

    def test_entries_without_a_doi_are_deduplicated_by_key_alone(self) -> None:
        entries = self._entries(("a", {}), ("a", {}), ("b", {}))
        self.assertEqual(len(self.formatter.deduplicate_entries(entries)), 2)


class SortTests(BibTeXTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.entries = [
            {"key": "zeta", "type": "article", "fields": {"year": "2019", "author": "Young, A.", "title": "Beta"}},
            {"key": "alpha", "type": "article", "fields": {"year": "2021", "author": "Adams, B.", "title": "Alpha"}},
        ]

    def test_the_default_sort_is_by_citation_key(self) -> None:
        self.assertEqual(
            [e["key"] for e in self.formatter.sort_entries(self.entries)],
            ["alpha", "zeta"],
        )

    def test_sorting_by_year_author_and_title(self) -> None:
        expected = {
            "year": ["zeta", "alpha"],
            "author": ["alpha", "zeta"],
            "title": ["alpha", "zeta"],
        }
        for field, order in expected.items():
            with self.subTest(sort_by=field):
                self.assertEqual(
                    [e["key"] for e in self.formatter.sort_entries(self.entries, field)],
                    order,
                )

    def test_descending_reverses_the_order(self) -> None:
        self.assertEqual(
            [e["key"] for e in self.formatter.sort_entries(self.entries, "key", True)],
            ["zeta", "alpha"],
        )

    def test_entries_missing_the_sort_field_go_last(self) -> None:
        entries = self.entries + [{"key": "omega", "type": "article", "fields": {}}]
        ordered = self.formatter.sort_entries(entries, "year")
        self.assertEqual(ordered[-1]["key"], "omega")

    def test_an_unknown_sort_field_falls_back_to_the_key(self) -> None:
        self.assertEqual(
            [e["key"] for e in self.formatter.sort_entries(self.entries, "nonsense")],
            ["alpha", "zeta"],
        )


class RenderTests(BibTeXTestCase):
    def test_a_formatted_entry_reparses_to_the_same_fields(self) -> None:
        original = self.formatter.parse_bibtex_file(self.bib())[0]
        rendered = self.formatter.format_entry(original)

        path = self.root / "round-trip.bib"
        path.write_text(rendered, encoding="utf-8")
        reparsed = self.formatter.parse_bibtex_file(str(path))[0]

        self.assertEqual(reparsed["key"], original["key"])
        self.assertEqual(reparsed["type"], original["type"])
        self.assertEqual(reparsed["fields"], original["fields"])

    def test_fields_are_emitted_in_the_documented_order(self) -> None:
        entry = {
            "key": "k",
            "type": "article",
            "fields": {"year": "2021", "title": "T", "author": "A"},
        }
        rendered = self.formatter.format_entry(entry)
        self.assertLess(rendered.index("author"), rendered.index("title"))
        self.assertLess(rendered.index("title"), rendered.index("year"))

    def test_braces_are_balanced(self) -> None:
        rendered = self.formatter.format_entry(
            self.formatter.parse_bibtex_file(self.bib())[0]
        )
        self.assertEqual(rendered.count("{"), rendered.count("}"))

    def test_a_protected_title_round_trips_without_losing_a_brace(self) -> None:
        # The regression that motivated the parser rewrite: this pipeline
        # previously emitted `{... with {AlphaFold}` -- one brace short, so the
        # file no longer compiled and every later entry was swallowed.
        source = (
            "@article{a,\n"
            "  title = {Prediction with {AlphaFold}},\n"
            "  author = {Jumper, John},\n"
            "  journal = {Nature},\n"
            "  year = {2021}\n}\n"
        )
        rendered = self.formatter.format_entry(
            self.formatter.parse_bibtex_file(self.bib(source))[0]
        )
        self.assertEqual(rendered.count("{"), rendered.count("}"))
        self.assertIn("{Prediction with {AlphaFold}}", rendered)

    def test_formatting_is_idempotent(self) -> None:
        first = self.formatter.format_file(self.bib(), output=None)
        path = self.root / "once.bib"
        path.write_text(first, encoding="utf-8")
        second = self.formatter.format_file(str(path), output=None)
        self.assertEqual(first, second)


class EndToEndTests(BibTeXTestCase):
    def test_formatting_a_file_applies_every_fix(self) -> None:
        output = self.root / "clean.bib"
        self.formatter.format_file(self.bib(), output=str(output))
        text = output.read_text(encoding="utf-8")

        self.assertIn("583--589", text)
        self.assertIn("10.1038/s41586-021-03819-2", text)
        self.assertNotIn("https://doi.org/", text)
        self.assertNotIn("pp. ", text)
        self.assertIn("Vaswani, Ashish and Shazeer, Noam", text)

    def test_the_result_still_parses(self) -> None:
        output = self.root / "clean.bib"
        self.formatter.format_file(self.bib(), output=str(output))
        self.assertEqual(len(self.formatter.parse_bibtex_file(str(output))), 2)


class ValidationTests(BibTeXTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.validator = validate_citations.CitationValidator()

    def test_a_complete_article_raises_no_errors(self) -> None:
        entry = {
            "key": "jumper2021",
            "type": "article",
            "fields": {
                "author": "Jumper, John",
                "title": "A title",
                "journal": "Nature",
                "year": "2021",
            },
        }
        errors, _ = self.validator.validate_entry(entry)
        self.assertEqual(errors, [])

    def test_a_missing_required_field_is_reported(self) -> None:
        entry = {
            "key": "incomplete",
            "type": "article",
            "fields": {"title": "A title", "year": "2021"},
        }
        errors, _ = self.validator.validate_entry(entry)
        self.assertTrue(errors)
        self.assertIn("author", " ".join(str(error) for error in errors).lower())

    def test_duplicate_detection_finds_repeated_entries(self) -> None:
        entries = self.formatter.parse_bibtex_file(self.bib(BIBLIOGRAPHY + BIBLIOGRAPHY))
        self.assertTrue(self.validator.detect_duplicates(entries))

    def test_distinct_entries_are_not_reported_as_duplicates(self) -> None:
        entries = self.formatter.parse_bibtex_file(self.bib())
        self.assertEqual(self.validator.detect_duplicates(entries), [])

    def test_manuscript_citation_keys_are_extracted(self) -> None:
        manuscript = self.root / "paper.tex"
        manuscript.write_text(
            "As shown \\cite{jumper2021} and \\citep{vaswani2017,smith2020}.\n",
            encoding="utf-8",
        )
        keys = self.validator.parse_manuscript_citations(str(manuscript))
        self.assertIn("jumper2021", keys)
        self.assertIn("vaswani2017", keys)
        self.assertIn("smith2020", keys)

    def test_a_manuscript_with_no_citations_yields_none(self) -> None:
        manuscript = self.root / "paper.tex"
        manuscript.write_text("No citations here.\n", encoding="utf-8")
        self.assertEqual(self.validator.parse_manuscript_citations(str(manuscript)), [])

    def test_the_valid_entry_count_never_goes_negative(self) -> None:
        # Several errors can land on one entry. Subtracting the error *count*
        # from the entry count reported `Valid entries: -2` for a one-entry
        # file, so the figure counts distinct failing entries instead.
        path = self.bib("@article{a,\n  title = {T}\n}\n")
        report = self.validator.validate_file(path)
        self.assertEqual(report["total_entries"], 1)
        self.assertEqual(report["valid_entries"], 0)
        self.assertGreater(len(report["errors"]), 1)

    def test_a_venue_shortfall_is_a_warning_not_an_error(self) -> None:
        # Reference-list length is editorial judgement, so falling under a
        # venue rule of thumb must not fail the run.
        report = self.validator.validate_file(self.bib(), venue="nature")
        self.assertTrue(
            any(w["type"] == "low_citation_count" for w in report["warnings"])
        )
        self.assertFalse(
            any(e.get("type", "").startswith("critically_low") for e in report["errors"])
        )

    def test_an_explicit_min_count_is_enforced_as_an_error(self) -> None:
        report = self.validator.validate_file(self.bib(), min_count=10)
        self.assertTrue(
            any(e["type"] == "below_requested_minimum" for e in report["errors"])
        )

    def test_venue_standards_are_available_without_running_a_validation(self) -> None:
        self.assertIn("nature", validate_citations.CitationValidator().venue_standards)


class PageTests(unittest.TestCase):
    def test_a_single_hyphen_range_becomes_an_en_dash_range(self) -> None:
        self.assertEqual(_common.format_pages("583-589"), "583--589")

    def test_an_already_correct_range_is_not_doubled(self) -> None:
        # A blanket `replace('-', '--')` turned this into `583----589`.
        self.assertEqual(_common.format_pages("583--589"), "583--589")

    def test_an_abbreviated_end_page_is_expanded(self) -> None:
        # PubMed's MedlinePgn abbreviates the end page; `1123--30` is not a
        # page range any reader or reference manager can resolve.
        self.assertEqual(_common.format_pages("1123-30"), "1123--1130")
        self.assertEqual(_common.format_pages("95-7"), "95--97")

    def test_an_article_number_is_left_alone(self) -> None:
        for raw in ("e0123456", "e70246", "12", "1,3,5"):
            with self.subTest(raw=raw):
                self.assertEqual(_common.format_pages(raw), raw)

    def test_a_pp_prefix_is_stripped(self) -> None:
        self.assertEqual(_common.format_pages("pp. 5998--6008"), "5998--6008")

    def test_an_en_dash_is_normalised(self) -> None:
        self.assertEqual(_common.format_pages("583–589"), "583--589")

    def test_an_empty_value_yields_an_empty_string(self) -> None:
        self.assertEqual(_common.format_pages(None), "")


class CitationKeyTests(unittest.TestCase):
    def test_a_comma_separated_name_uses_the_surname(self) -> None:
        self.assertEqual(
            _common.citation_key("Jumper, John", "2021", "Highly accurate prediction"),
            "Jumper2021highly",
        )

    def test_a_pubmed_style_name_uses_the_leading_surname(self) -> None:
        # `Smith JA` is surname-first; taking the last token yields `JA`.
        self.assertEqual(_common.citation_key("Smith JA", "2021", "A study"), "Smith2021study")

    def test_a_western_style_name_uses_the_trailing_surname(self) -> None:
        self.assertEqual(_common.citation_key("John Smith", "2021", "A study"), "Smith2021study")

    def test_accents_and_punctuation_are_removed(self) -> None:
        # A key reaches LaTeX and sometimes a file path, and its source is a
        # publisher-controlled record.
        self.assertEqual(_common.citation_key("Müller, Hans", "2021", "A study"), "Muller2021study")
        self.assertEqual(_common.citation_key("O'Brien, Pat", "2021", "A study"), "OBrien2021study")

    def test_a_key_is_always_safe_to_use(self) -> None:
        for authors in ("", "$(rm -rf /)", "van der Berg, Jan", "李, 明"):
            with self.subTest(authors=authors):
                key = _common.citation_key(authors, "2021", "A study")
                self.assertRegex(key, r"^[A-Za-z0-9]+$")

    def test_a_missing_year_becomes_a_placeholder(self) -> None:
        self.assertTrue(_common.citation_key("Smith, J", "", "A study").startswith("SmithXXXX"))

    def test_the_same_paper_from_two_sources_gets_the_same_key(self) -> None:
        # This is what makes cross-source deduplication possible at all.
        crossref = _common.citation_key("Jumper, John", "2021", "Highly accurate prediction")
        pubmed = _common.citation_key("Jumper J", "2021", "Highly accurate prediction")
        self.assertEqual(crossref, pubmed)


class TitleProtectionTests(unittest.TestCase):
    def test_an_acronym_is_braced(self) -> None:
        self.assertEqual(
            _common.protect_title("Prediction with AlphaFold"),
            "Prediction with {AlphaFold}",
        )

    def test_protection_is_idempotent(self) -> None:
        once = _common.protect_title("Editing DNA with CRISPR")
        self.assertEqual(_common.protect_title(once), once)

    def test_an_acronym_inside_a_longer_word_is_untouched(self) -> None:
        self.assertEqual(_common.protect_title("Studies of mRNA"), "Studies of {mRNA}")
        self.assertNotIn("{RNA}", _common.protect_title("Studies of mRNA"))


class RekeyTests(BibTeXTestCase):
    def test_entries_are_rekeyed_to_the_shared_scheme(self) -> None:
        entries = self.formatter.parse_bibtex_file(self.bib())
        rekeyed = self.formatter.rekey_entries(entries)
        self.assertEqual(rekeyed[0]["key"], "Jumper2021highly")

    def test_a_key_collision_gets_a_suffix(self) -> None:
        entries = [
            {"key": "x", "type": "article", "fields": {"author": "Smith, J", "year": "2021", "title": "A study"}},
            {"key": "y", "type": "article", "fields": {"author": "Smith, J", "year": "2021", "title": "A study"}},
        ]
        keys = [e["key"] for e in self.formatter.rekey_entries(entries)]
        self.assertEqual(len(set(keys)), 2)
        self.assertEqual(keys[0], "Smith2021study")


@unittest.skipUnless(REQUESTS_AVAILABLE, "requests is not installed")
class EntryRenderingTests(unittest.TestCase):
    """The BibTeX each extractor emits, without touching the network."""

    def setUp(self) -> None:
        self.extractor = extract_metadata.MetadataExtractor()

    def _fields(self, bibtex: str) -> dict:
        return _common.parse_bibtex(bibtex)[0]["fields"]

    def test_a_book_keeps_its_publisher(self) -> None:
        # `publisher` was extracted from Crossref and then dropped by the
        # writer, so every @book failed its own required-field check.
        bibtex = self.extractor.metadata_to_bibtex({
            "entry_type": "book", "authors": "Smith, John", "title": "A Book",
            "year": "2021", "publisher": "Springer",
        })
        self.assertEqual(self._fields(bibtex)["publisher"], "Springer")

    def test_a_report_maps_its_publisher_to_institution(self) -> None:
        bibtex = self.extractor.metadata_to_bibtex({
            "entry_type": "techreport", "authors": "Smith, John", "title": "A Report",
            "year": "2021", "publisher": "NIST",
        })
        self.assertEqual(self._fields(bibtex)["institution"], "NIST")

    def test_a_chapter_uses_booktitle_rather_than_journal(self) -> None:
        fields = self._fields(self.extractor.metadata_to_bibtex({
            "entry_type": "incollection", "authors": "Smith, John", "title": "A Chapter",
            "year": "2021", "journal": "A Collection", "publisher": "Springer",
        }))
        self.assertEqual(fields["booktitle"], "A Collection")
        self.assertNotIn("journal", fields)

    def test_an_unpublished_preprint_is_misc_not_a_journalless_article(self) -> None:
        # arXiv mints DOIs for unpublished preprints, so a DOI alone must not
        # promote an entry to @article -- that yields an article with no
        # journal, which fails validation every time.
        fields = self._fields(self.extractor.metadata_to_bibtex({
            "type": "arxiv", "entry_type": "misc", "arxiv_id": "2103.00020",
            "authors": "Radford, Alec", "title": "A Preprint", "year": "2021",
        }))
        self.assertEqual(fields["note"], "Preprint")
        self.assertIn("arXiv", fields["howpublished"])

    def test_a_published_preprint_gains_its_journal(self) -> None:
        journal = self.extractor._journal_from_arxiv_ref("Nature 596, 583-589 (2021)")
        self.assertEqual(journal, "Nature")

    def test_only_one_note_field_is_emitted(self) -> None:
        # Two `note` lines in one entry is a BibTeX error.
        bibtex = self.extractor.metadata_to_bibtex({
            "type": "arxiv", "entry_type": "misc", "arxiv_id": "2103.1",
            "pmid": "123", "authors": "Smith, John", "title": "T", "year": "2021",
        })
        self.assertEqual(bibtex.count("note "), 1)

    def test_a_pubmed_entry_key_is_shared_scheme_and_pages_expand(self) -> None:
        bibtex = search_pubmed.PubMedSearcher().metadata_to_bibtex({
            "authors": "Müller, Hans", "year": "2021", "pmid": "1",
            "title": "Deep learning methods", "journal": "Nature", "pages": "1123-30",
        })
        self.assertIn("@article{Muller2021deep,", bibtex)
        self.assertEqual(self._fields(bibtex)["pages"], "1123--1130")


@unittest.skipUnless(REQUESTS_AVAILABLE, "requests is not installed")
class CredentialDiagnosticTests(unittest.TestCase):
    def test_ncbi_request_failures_do_not_print_query_string_credentials(self):
        import io
        from contextlib import redirect_stderr
        from unittest.mock import patch

        fake_key = "dummy-test-key"
        fake_email = "test@example.invalid"
        with patch.dict("os.environ", {"NCBI_API_KEY": fake_key, "NCBI_EMAIL": fake_email}):
            pubmed = search_pubmed.PubMedSearcher()
            extractor = extract_metadata.MetadataExtractor()
        cases = [
            (pubmed, pubmed.search, ("example",)),
            (pubmed, pubmed.fetch_metadata, (["1"],)),
            (extractor, extractor.extract_from_pmid, ("1",)),
        ]
        for owner, method, arguments in cases:
            with self.subTest(method=method.__name__):
                diagnostic = io.StringIO()
                error = search_pubmed.requests.exceptions.HTTPError(
                    "503 for url: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
                    f"efetch.fcgi?api_key={fake_key}&email={fake_email}")
                with patch.object(owner.session, "get", side_effect=error), redirect_stderr(diagnostic):
                    method(*arguments)
                self.assertIn("HTTPError", diagnostic.getvalue())
                self.assertNotIn(fake_key, diagnostic.getvalue())
                self.assertNotIn(fake_email, diagnostic.getvalue())
                self.assertNotIn("https://", diagnostic.getvalue())


@unittest.skipUnless(REQUESTS_AVAILABLE, "requests is not installed")
class OpenAlexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.searcher = search_openalex.OpenAlexSearcher()

    def test_key_stays_in_header_and_page_size_uses_supported_maximum(self):
        from unittest.mock import patch, Mock
        with patch.dict("os.environ", {"OPENALEX_API_KEY": "unit-test-key"}):
            searcher = search_openalex.OpenAlexSearcher()
        response = Mock()
        response.json.return_value = {"meta": {"count": 0}, "results": []}
        with patch.object(searcher.session, "get", return_value=response) as get:
            searcher.search("example", max_results=250)
        self.assertEqual(searcher.session.headers["Authorization"], "Bearer unit-test-key")
        self.assertEqual(get.call_args.kwargs["params"]["per-page"], "100")
        self.assertNotIn("api_key", get.call_args.kwargs["params"])
        self.assertEqual(get.call_args.args[0], "https://api.openalex.org/works")

    def test_failed_second_page_does_not_masquerade_as_complete_search(self):
        from unittest.mock import patch, Mock
        response = Mock()
        response.json.return_value = {"meta": {"count": 2, "next_cursor": "page2"},
                                      "results": [{"id": "https://openalex.org/W1"}]}
        with patch.object(self.searcher.session, "get", side_effect=[
            response, search_openalex.requests.exceptions.Timeout("offline")
        ]), patch.object(search_openalex.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "after 1 records"):
                self.searcher.search("example", max_results=2)

    def test_repeated_cursor_cannot_fill_limit_with_duplicate_pages(self):
        from unittest.mock import patch, Mock
        response = Mock()
        response.json.return_value = {"meta": {"count": 3, "next_cursor": "page2"},
                                      "results": [{"id": "https://openalex.org/W1"}]}
        with patch.object(self.searcher.session, "get", return_value=response) as get, \
                patch.object(search_openalex.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "repeated cursor"):
                self.searcher.search("example", max_results=3)
        self.assertEqual(get.call_count, 2)

    def test_duplicate_work_with_a_fresh_cursor_is_rejected(self):
        from unittest.mock import patch, Mock
        first, second = Mock(), Mock()
        first.json.return_value = {"meta": {"count": 3, "next_cursor": "page2"},
                                   "results": [{"id": "https://openalex.org/W1"}]}
        second.json.return_value = {"meta": {"count": 3, "next_cursor": "page3"},
                                    "results": [{"id": "https://openalex.org/W1"}]}
        with patch.object(self.searcher.session, "get", side_effect=[first, second]), \
                patch.object(search_openalex.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "duplicate work ID"):
                self.searcher.search("example", max_results=2)

    def test_successful_cursor_pages_preserve_each_unique_work(self):
        from unittest.mock import patch, Mock
        first, second = Mock(), Mock()
        first.json.return_value = {"meta": {"count": 2, "next_cursor": "page2"},
                                   "results": [{"id": "https://openalex.org/W1"}]}
        second.json.return_value = {"meta": {"count": 2, "next_cursor": "page3"},
                                    "results": [{"id": "https://openalex.org/W2"}]}
        cursors = []
        responses = iter([first, second])
        def get_page(url, *, params, timeout):
            cursors.append(params["cursor"])
            return next(responses)
        with patch.object(self.searcher.session, "get", side_effect=get_page), \
                patch.object(search_openalex.time, "sleep"):
            result = self.searcher.search("example", max_results=2)
        self.assertEqual(cursors, ["*", "page2"])
        self.assertEqual([record["openalex_id"] for record in result],
                         ["https://openalex.org/W1", "https://openalex.org/W2"])

    def test_nonpositive_limit_fails_before_network_request(self):
        from unittest.mock import patch
        with patch.object(self.searcher.session, "get") as get:
            with self.assertRaises(ValueError):
                self.searcher.search("example", max_results=0)
        get.assert_not_called()

    def test_an_abstract_is_rebuilt_from_its_inverted_index(self) -> None:
        self.assertEqual(
            self.searcher._abstract({"Deep": [0], "learning": [1], "works": [2]}),
            "Deep learning works",
        )

    def test_an_absent_abstract_yields_an_empty_string(self) -> None:
        self.assertEqual(self.searcher._abstract(None), "")

    def test_a_work_is_flattened_to_the_shared_metadata_shape(self) -> None:
        record = self.searcher._normalise({
            "id": "https://openalex.org/W1",
            "doi": "https://doi.org/10.1/x",
            "title": "A Paper",
            "publication_year": 2021,
            "type": "article",
            "authorships": [{"author": {"display_name": "Jane Doe"}}],
            "primary_location": {"source": {"display_name": "Nature"}},
            "biblio": {"volume": "596", "issue": "7873", "first_page": "583", "last_page": "589"},
            "cited_by_count": 10,
        })
        self.assertEqual(record["doi"], "10.1/x")  # the URL prefix is stripped
        self.assertEqual(record["authors"], "Jane Doe")
        self.assertEqual(record["journal"], "Nature")
        self.assertEqual(record["pages"], "583-589")

    def test_a_single_page_work_does_not_become_a_range(self) -> None:
        record = self.searcher._normalise({"biblio": {"first_page": "7", "last_page": "7"}})
        self.assertEqual(record["pages"], "7")

    def test_a_preprint_renders_as_misc(self) -> None:
        bibtex = self.searcher.metadata_to_bibtex({
            "type": "preprint", "authors": "Jane Doe", "title": "A Preprint",
            "year": "2021", "doi": "10.1/x",
        })
        self.assertTrue(bibtex.startswith("@misc{"))


if __name__ == "__main__":
    unittest.main()
