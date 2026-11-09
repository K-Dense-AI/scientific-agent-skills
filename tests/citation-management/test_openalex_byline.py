"""Work-specific author names survive OpenAlex normalization and BibTeX export."""

import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "citation-management"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import _common
import search_openalex


class OpenAlexBylineTests(unittest.TestCase):
    def setUp(self):
        self.searcher = search_openalex.OpenAlexSearcher()

    def test_work_byline_takes_precedence_over_entity_name(self):
        # An author entity can legitimately use a different name from one work.
        record = self.searcher._normalise({
            "authorships": [
                {"raw_author_name": "Liz Tuck",
                 "author": {"display_name": "Elizabeth J. Tuck"}},
                {"raw_author_name": "Ioana Agache",
                 "author": {"display_name": "Ioana Octavia Agache"}},
            ],
        })
        self.assertEqual(record["authors"], "Liz Tuck and Ioana Agache")

    def test_missing_or_blank_byline_falls_back_to_entity(self):
        for raw in ({}, {"raw_author_name": None}, {"raw_author_name": ""},
                    {"raw_author_name": " \t\n"}):
            with self.subTest(raw=raw):
                record = self.searcher._normalise({
                    "authorships": [{**raw, "author": {"display_name": "Jane Doe"}}],
                })
                self.assertEqual(record["authors"], "Jane Doe")

    def test_null_or_missing_entity_can_still_have_a_byline(self):
        for entity in ({}, {"author": None}, {"author": {}}):
            with self.subTest(entity=entity):
                record = self.searcher._normalise({
                    "authorships": [{**entity, "raw_author_name": "Jane Doe"}],
                })
                self.assertEqual(record["authors"], "Jane Doe")
                record = self.searcher._normalise({
                    "authorships": [{**entity, "raw_author_name": " \t"}],
                })
                self.assertEqual(record["authors"], "")

    def test_complete_author_string_and_order_survive_bibtex_export(self):
        record = self.searcher._normalise({
            "title": "An example", "publication_year": 2020, "type": "article",
            "authorships": [
                {"raw_author_name": "Carlos Talavera-López",
                 "author": {"display_name": "Carlos N. Talavera-López"}},
                {"raw_author_name": "Joshua M. Gorham",
                 "author": {"display_name": "Joshua Gorham"}},
                {"author": {"display_name": "Jane Doe"}},
            ],
        })
        expected = "Carlos Talavera-López and Joshua M. Gorham and Jane Doe"
        self.assertEqual(record["authors"], expected)
        entries = _common.parse_bibtex(self.searcher.metadata_to_bibtex(record))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["fields"]["author"], expected)


if __name__ == "__main__":
    unittest.main()
