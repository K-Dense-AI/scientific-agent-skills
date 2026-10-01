"""Tests for the docx skill's OOXML editors.

The shared `office/` tree -- zip safety, relationship resolution, repacking --
is covered by the contract, since pptx and xlsx ship byte-identical copies.
What is specific to docx is the run merger and the comment writer; they edit
body XML and comment parts respectively, so the tests build a real unpacked package
in a temporary directory and assert on the XML that comes back out.

`merge_runs` is the one with a genuine correctness risk: Word splits a single
sentence across many `<w:r>` runs, and merging them must preserve the visible
text exactly, including whitespace held by `xml:space="preserve"`.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "docx"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("defusedxml", reason="docx scripts need defusedxml")

import merge_runs  # noqa: E402

OfficeTests = skill_contract.office.office_test_case(SKILL_ROOT)
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

WORDML = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def document(body: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:document xmlns:w="{WORDML}"><w:body>{body}</w:body></w:document>'
    )


def run(text: str, *, preserve: bool = False, properties: str = "") -> str:
    space = ' xml:space="preserve"' if preserve else ""
    return f"<w:r>{properties}<w:t{space}>{text}</w:t></w:r>"


class UnpackedPackage:
    """A minimal unpacked .docx directory."""

    def __init__(self, root: Path, body: str) -> None:
        self.root = root
        (root / "word").mkdir(parents=True, exist_ok=True)
        (root / "word" / "document.xml").write_text(document(body), encoding="utf-8")
        (root / "[Content_Types].xml").write_text("<Types/>", encoding="utf-8")

    @property
    def xml(self) -> str:
        return (self.root / "word" / "document.xml").read_text(encoding="utf-8")

    def visible_text(self) -> str:
        import re

        return "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", self.xml, re.DOTALL))


class MergeRunsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)

    def package(self, body: str) -> UnpackedPackage:
        return UnpackedPackage(self.root, body)


class TextPreservationTests(MergeRunsTestCase):
    def test_adjacent_identical_runs_merge_without_changing_the_text(self) -> None:
        # The trailing space needs xml:space="preserve" to be significant --
        # without it OOXML says the space is not part of the text, which is
        # what `office/helpers.rendered_text` implements.
        package = self.package(
            "<w:p>" + run("Hello ", preserve=True) + run("world") + run("!") + "</w:p>"
        )
        before = package.visible_text()
        merge_runs.merge_runs(str(self.root))
        self.assertEqual(package.visible_text(), before)
        self.assertEqual(package.visible_text(), "Hello world!")

    def test_unpreserved_trailing_whitespace_is_insignificant(self) -> None:
        # The counterpart: without xml:space="preserve" the space is dropped,
        # matching how Word itself reads the part.
        package = self.package("<w:p>" + run("Hello ") + run("world") + "</w:p>")
        merge_runs.merge_runs(str(self.root))
        self.assertEqual(package.visible_text(), "Helloworld")

    def test_merging_reduces_the_run_count(self) -> None:
        package = self.package(
            "<w:p>" + run("a") + run("b") + run("c") + "</w:p>"
        )
        merged, _ = merge_runs.merge_runs(str(self.root))
        self.assertGreater(merged, 0)
        self.assertEqual(package.xml.count("<w:r>"), 1)

    def test_runs_with_different_formatting_are_not_merged(self) -> None:
        bold = "<w:rPr><w:b/></w:rPr>"
        package = self.package(
            "<w:p>" + run("plain") + run("bold", properties=bold) + "</w:p>"
        )
        merge_runs.merge_runs(str(self.root))
        self.assertEqual(package.xml.count("<w:r>"), 2)
        self.assertEqual(package.visible_text(), "plainbold")

    def test_preserved_whitespace_survives_a_merge(self) -> None:
        # Losing xml:space="preserve" silently deletes the space between words.
        package = self.package(
            "<w:p>" + run("one ", preserve=True) + run("two", preserve=True) + "</w:p>"
        )
        merge_runs.merge_runs(str(self.root))
        self.assertEqual(package.visible_text(), "one two")

    def test_runs_in_different_paragraphs_are_not_merged_across(self) -> None:
        package = self.package(
            "<w:p>" + run("first") + "</w:p><w:p>" + run("second") + "</w:p>"
        )
        merge_runs.merge_runs(str(self.root))
        self.assertEqual(package.xml.count("<w:p>"), 2)
        self.assertEqual(package.visible_text(), "firstsecond")

    def test_a_document_with_nothing_to_merge_keeps_its_content(self) -> None:
        # The XML declaration is rewritten by minidom's serializer, so compare
        # the document element rather than the whole byte stream.
        package = self.package("<w:p>" + run("only one run") + "</w:p>")
        merged, _ = merge_runs.merge_runs(str(self.root))
        self.assertEqual(merged, 0)
        self.assertEqual(package.visible_text(), "only one run")
        self.assertEqual(package.xml.count("<w:r>"), 1)

    def test_an_empty_document_does_not_raise(self) -> None:
        self.package("")
        merged, _ = merge_runs.merge_runs(str(self.root))
        self.assertEqual(merged, 0)

    def test_the_result_is_still_well_formed_xml(self) -> None:
        import defusedxml.ElementTree as ElementTree

        package = self.package(
            "<w:p>" + "".join(run(str(index)) for index in range(20)) + "</w:p>"
        )
        merge_runs.merge_runs(str(self.root))
        ElementTree.fromstring(package.xml)
        self.assertEqual(package.visible_text(), "".join(str(i) for i in range(20)))

    def test_merging_is_idempotent(self) -> None:
        package = self.package("<w:p>" + run("a") + run("b") + "</w:p>")
        merge_runs.merge_runs(str(self.root))
        once = package.xml
        merged, _ = merge_runs.merge_runs(str(self.root))
        self.assertEqual(merged, 0)
        self.assertEqual(package.xml, once)


class HelperTests(unittest.TestCase):
    """`merge_runs` walks a minidom tree, so the helpers take minidom nodes."""

    def _runs(self, body: str) -> list:
        import defusedxml.minidom

        dom = defusedxml.minidom.parseString(document(body))
        root = dom.documentElement
        return merge_runs._find_runs(root, merge_runs._run_tag_names(root))

    def test_adjacency_requires_the_elements_to_be_siblings_in_order(self) -> None:
        runs = self._runs("<w:p>" + run("a") + run("b") + "</w:p>")
        self.assertEqual(len(runs), 2)
        self.assertTrue(merge_runs._is_adjacent(runs[0], runs[1]))
        self.assertFalse(merge_runs._is_adjacent(runs[1], runs[0]))

    def test_an_intervening_element_breaks_adjacency(self) -> None:
        runs = self._runs(
            "<w:p>" + run("a") + "<w:bookmarkStart/>" + run("b") + "</w:p>"
        )
        self.assertFalse(merge_runs._is_adjacent(runs[0], runs[1]))

    def test_element_matching_is_namespace_aware(self) -> None:
        runs = self._runs("<w:p>" + run("a") + "</w:p>")
        self.assertTrue(merge_runs._is_element(runs[0], "r"))
        self.assertFalse(merge_runs._is_element(runs[0], "p"))

    def test_run_tag_names_are_discovered_from_the_document(self) -> None:
        names = merge_runs._run_tag_names(
            __import__("defusedxml.minidom", fromlist=["parseString"])
            .parseString(document("<w:p>" + run("a") + "</w:p>"))
            .documentElement
        )
        self.assertTrue(names)


class TemplateTests(unittest.TestCase):
    def test_the_comment_templates_are_shipped_and_parse(self) -> None:
        import defusedxml.ElementTree as ElementTree

        templates = sorted((SCRIPTS / "templates").glob("*.xml"))
        self.assertTrue(templates, "no comment templates shipped")
        for template in templates:
            with self.subTest(template=template.name):
                ElementTree.fromstring(template.read_text(encoding="utf-8"))

    def test_the_documented_comment_parts_are_all_present(self) -> None:
        # The helper ships modern-comment extension templates; basic comments need fewer parts.
        shipped = {path.name for path in (SCRIPTS / "templates").glob("*.xml")}
        for required in (
            "comments.xml",
            "commentsExtended.xml",
            "commentsIds.xml",
            "people.xml",
        ):
            with self.subTest(part=required):
                self.assertIn(required, shipped)


if __name__ == "__main__":
    unittest.main()
