"""Keep Crossref article locators separate from page ranges and issue numbers."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "citation-management"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

if REQUESTS_AVAILABLE:
    from extract_metadata import MetadataExtractor
    from _common import parse_bibtex


@unittest.skipUnless(REQUESTS_AVAILABLE, "requests is not installed")
class CrossrefArticleNumberTests(unittest.TestCase):
    def check_locator(self, extra: dict, article_number: str, pages: str) -> None:
        message = {
            "type": "journal-article", "title": ["Synthetic locator example"],
            "author": [{"given": "Jane", "family": "Doe"}],
            "container-title": ["Example Journal"],
            "published-online": {"date-parts": [[2026]]},
            "volume": "12", "issue": "3", **extra,
        }
        response = Mock(status_code=200)
        response.json.return_value = {"message": message}
        extractor = MetadataExtractor()
        with patch.object(extractor.session, "get", return_value=response) as get:
            record = extractor.extract_record("10.1234/synthetic-locator")
        get.assert_called_once_with(
            "https://api.crossref.org/works/10.1234%2Fsynthetic-locator", timeout=15,
        )
        self.assertEqual(record["article_number"], article_number)
        self.assertEqual(record["pages"], extra.get("page", ""))
        self.assertEqual(record["issue"], "3")
        fields = parse_bibtex(record["bibtex"])[0]["fields"]
        self.assertEqual(fields.get("eid", ""), article_number)
        self.assertEqual(fields.get("pages", ""), pages)
        self.assertEqual(fields["number"], "3")
        self.assertEqual(record["bibtex"].count("eid "), int(bool(article_number)))

    def test_article_number_without_pages(self) -> None:
        self.check_locator({"article-number": "6756"}, "6756", "")

    def test_pages_without_article_number(self) -> None:
        self.check_locator({"page": "41-50"}, "", "41--50")

    def test_pages_and_article_number_coexist(self) -> None:
        self.check_locator({"article-number": "137", "page": "14-28"}, "137", "14--28")

    def test_neither_locator_is_invented(self) -> None:
        self.check_locator({}, "", "")

    def test_leading_zero_is_preserved(self) -> None:
        self.check_locator({"article-number": "00123"}, "00123", "")

    def test_e_prefix_is_preserved(self) -> None:
        self.check_locator({"article-number": "e00053"}, "e00053", "")

    def test_null_article_number_is_absent(self) -> None:
        self.check_locator({"article-number": None}, "", "")

    def test_numeric_article_number_becomes_a_string(self) -> None:
        self.check_locator({"article-number": 0}, "0", "")


if __name__ == "__main__":
    unittest.main()
