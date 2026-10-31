"""Tests for the liteparse batch directory parser.

Parsing is liteparse's job; the script owns file discovery, serialisation, and
error containment. All three are testable with a stub parser -- and the third
matters most: a batch run over a hundred documents must not abort because one
of them is corrupt.

Output paths preserve source suffixes and relative directories; existing files
are reported as failures instead of overwritten.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "liteparse"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("liteparse", reason="liteparse scripts import liteparse")

import batch_parse_dir  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def text_item(text: str = "hello"):
    return SimpleNamespace(
        text=text,
        x=1.0,
        y=2.0,
        width=3.0,
        height=4.0,
        font_name="Helvetica",
        font_size=12.0,
        confidence=0.99,
    )


def parse_result(text: str = "hello"):
    page = SimpleNamespace(
        page_num=1, width=612.0, height=792.0, text=text, text_items=[text_item(text)],
        markdown=text, page_label=None
    )
    return SimpleNamespace(text=text, pages=[page], total_pages=1, page_errors=[])


class StubParser:
    """Stands in for LiteParse; raises for any source named `broken*`."""

    def __init__(self) -> None:
        self.seen: list[Path] = []

    def parse(self, path: Path):
        self.seen.append(path)
        if path.stem.startswith("broken"):
            raise RuntimeError("unreadable document")
        return parse_result(f"contents of {path.name}")


class ExtensionTests(unittest.TestCase):
    def test_the_default_set_is_lowercase_and_dotted(self) -> None:
        self.assertTrue(batch_parse_dir.DEFAULT_EXTENSIONS)
        for extension in batch_parse_dir.DEFAULT_EXTENSIONS:
            with self.subTest(extension=extension):
                self.assertTrue(extension.startswith("."))
                self.assertEqual(extension, extension.lower())

    def test_the_documented_document_and_image_families_are_covered(self) -> None:
        defaults = batch_parse_dir.DEFAULT_EXTENSIONS
        for extension in (".pdf", ".docx", ".xlsx", ".pptx", ".csv", ".png", ".tiff"):
            with self.subTest(extension=extension):
                self.assertIn(extension, defaults)


class DiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)

    def touch(self, relative: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
        return path

    def _found(self, **kwargs) -> list[str]:
        kwargs.setdefault("recursive", False)
        kwargs.setdefault("extension", None)
        return [path.name for path in batch_parse_dir.iter_files(self.root, **kwargs)]

    def test_only_supported_extensions_are_yielded(self) -> None:
        self.touch("a.pdf")
        self.touch("b.docx")
        self.touch("c.exe")
        self.assertEqual(self._found(), ["a.pdf", "b.docx"])

    def test_matching_is_case_insensitive(self) -> None:
        self.touch("SCAN.PDF")
        self.assertEqual(self._found(), ["SCAN.PDF"])

    def test_an_explicit_extension_narrows_the_selection(self) -> None:
        self.touch("a.pdf")
        self.touch("b.docx")
        self.assertEqual(self._found(extension=".pdf"), ["a.pdf"])

    def test_an_explicit_extension_is_matched_case_insensitively(self) -> None:
        self.touch("a.PDF")
        self.assertEqual(self._found(extension=".PdF"), ["a.PDF"])

    def test_recursion_is_opt_in(self) -> None:
        self.touch("top.pdf")
        self.touch("nested/deep.pdf")
        self.assertEqual(self._found(), ["top.pdf"])
        self.assertEqual(sorted(self._found(recursive=True)), ["deep.pdf", "top.pdf"])

    def test_directories_are_skipped(self) -> None:
        (self.root / "folder.pdf").mkdir()
        self.assertEqual(self._found(), [])

    def test_the_order_is_deterministic(self) -> None:
        for name in ("c.pdf", "a.pdf", "b.pdf"):
            self.touch(name)
        self.assertEqual(self._found(), ["a.pdf", "b.pdf", "c.pdf"])


class SerialisationTests(unittest.TestCase):
    def test_a_result_becomes_a_json_serialisable_dictionary(self) -> None:
        payload = batch_parse_dir._result_to_dict(parse_result("body text"))
        json.dumps(payload)
        self.assertEqual(payload["text"], "body text")
        self.assertEqual(len(payload["pages"]), 1)

    def test_page_geometry_and_text_items_survive(self) -> None:
        page = batch_parse_dir._result_to_dict(parse_result())["pages"][0]
        self.assertEqual(page["page_num"], 1)
        self.assertEqual(page["width"], 612.0)
        self.assertEqual(len(page["text_items"]), 1)

    def test_a_text_item_keeps_its_position_font_and_confidence(self) -> None:
        item = batch_parse_dir._text_item_dict(text_item("word"))
        self.assertEqual(
            set(item),
            {"text", "x", "y", "width", "height", "font_name", "font_size", "confidence"},
        )
        self.assertEqual(item["text"], "word")
        self.assertEqual(item["font_name"], "Helvetica")
        self.assertEqual(item["confidence"], 0.99)


class ParseOneTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)
        self.output = self.root / "out"
        self.output.mkdir()
        self.parser = StubParser()

    def test_text_output_writes_the_plain_text(self) -> None:
        ok, source, message = batch_parse_dir.parse_one(
            self.parser, Path("paper.pdf"), self.output, "text"
        )
        self.assertTrue(ok)
        self.assertIn("paper.pdf.txt", message)
        self.assertEqual(
            (self.output / "paper.pdf.txt").read_text(encoding="utf-8"),
            "contents of paper.pdf",
        )

    def test_json_output_writes_the_structured_result(self) -> None:
        ok, _, message = batch_parse_dir.parse_one(
            self.parser, Path("paper.pdf"), self.output, "json"
        )
        self.assertTrue(ok)
        self.assertIn("paper.pdf.json", message)
        payload = json.loads((self.output / "paper.pdf.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["text"], "contents of paper.pdf")
        self.assertIn("pages", payload)

    def test_a_failing_document_is_reported_not_raised(self) -> None:
        # One corrupt file must not abort a hundred-document batch.
        ok, source, message = batch_parse_dir.parse_one(
            self.parser, Path("broken.pdf"), self.output, "text"
        )
        self.assertFalse(ok)
        self.assertEqual(source, "broken.pdf")
        self.assertIn("unreadable document", message)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_same_stem_different_formats_keep_both_outputs(self) -> None:
        for source in ("report.pdf", "report.docx"):
            ok, _, _ = batch_parse_dir.parse_one(self.parser, Path(source), self.output, "text")
            self.assertTrue(ok)
        self.assertEqual(sorted(p.name for p in self.output.iterdir()),
                         ["report.docx.txt", "report.pdf.txt"])

    def test_existing_output_is_preserved(self) -> None:
        target = self.output / "report.pdf.txt"
        target.write_text("earlier extraction", encoding="utf-8")
        ok, _, message = batch_parse_dir.parse_one(self.parser, Path("report.pdf"), self.output, "text")
        self.assertFalse(ok)
        self.assertIn("already exists", message)
        self.assertEqual(target.read_text(), "earlier extraction")
        self.assertFalse(self.parser.seen)

    def test_partial_pages_fail_without_writing_any_format(self) -> None:
        partial = parse_result()
        partial.page_errors = [SimpleNamespace(page_number=2, message="broken page")]
        parser = SimpleNamespace(parse=lambda _: partial)
        for fmt in ("text", "json", "markdown"):
            with self.subTest(fmt=fmt):
                ok, _, message = batch_parse_dir.parse_one(parser, Path("paper.pdf"), self.output, fmt)
                self.assertFalse(ok)
                self.assertIn("page 2: broken page", message)
        self.assertFalse(list(self.output.iterdir()))

    def test_page_cap_truncation_is_reported(self) -> None:
        partial = parse_result()
        partial.total_pages = 1001
        parser = SimpleNamespace(parse=lambda _: partial)
        ok, _, message = batch_parse_dir.parse_one(parser, Path("paper.pdf"), self.output, "json")
        self.assertFalse(ok)
        self.assertIn("returned 1 of 1001 source pages", message)
        self.assertFalse(list(self.output.iterdir()))

    def test_markdown_and_nested_output(self) -> None:
        out = self.output / "nested"
        ok, _, _ = batch_parse_dir.parse_one(self.parser, Path("paper.pdf"), out, "markdown")
        self.assertTrue(ok)
        self.assertEqual((out / "paper.pdf.md").read_text(), "contents of paper.pdf")

    def test_unknown_format_is_reported_without_parsing(self) -> None:
        ok, _, message = batch_parse_dir.parse_one(self.parser, Path("a.pdf"), self.output, "yaml")
        self.assertFalse(ok)
        self.assertIn("Unsupported output format", message)
        self.assertFalse(self.parser.seen)
        self.assertFalse(list(self.output.iterdir()))


if __name__ == "__main__":
    unittest.main()
