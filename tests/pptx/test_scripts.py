"""Tests for the pptx skill's package editors.

The shared `office/` tree is covered by the contract. What is specific here is
slide bookkeeping: `add_slide` has to pick a free slide number and a legal
slide id, and `clean` has to delete orphaned parts without deleting anything
the presentation still references.

`clean` is the dangerous one -- it removes files -- so the tests concentrate on
its refusal path. A package whose `sldIdLst` cannot be read must make the tool
stop rather than conclude that every slide is an orphan and delete the deck.
"""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pptx"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("defusedxml", reason="pptx scripts need defusedxml")

import add_slide  # noqa: E402
import clean  # noqa: E402
import thumbnail  # noqa: E402

OfficeTests = skill_contract.office.office_test_case(SKILL_ROOT)
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

RELATIONSHIPS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
SLIDE_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
)


class Deck:
    """A minimal unpacked .pptx directory with `count` registered slides."""

    def __init__(self, root: Path, count: int, *, orphans: int = 0) -> None:
        self.root = root
        self.slides = root / "ppt" / "slides"
        self.slides.mkdir(parents=True)
        (self.slides / "_rels").mkdir()
        (root / "ppt" / "_rels").mkdir(parents=True)

        total = count + orphans
        for number in range(1, total + 1):
            (self.slides / f"slide{number}.xml").write_text(
                f'<p:sld xmlns:p="{clean.PRESENTATION_NS}"/>', encoding="utf-8"
            )
            (self.slides / "_rels" / f"slide{number}.xml.rels").write_text(
                f'<Relationships xmlns="{RELATIONSHIPS_NS}"/>', encoding="utf-8"
            )

        # Only the first `count` slides are registered in the presentation.
        relationships = "".join(
            f'<Relationship Id="rId{n}" Type="{SLIDE_TYPE}" Target="slides/slide{n}.xml"/>'
            for n in range(1, total + 1)
        )
        (root / "ppt" / "_rels" / "presentation.xml.rels").write_text(
            f'<Relationships xmlns="{RELATIONSHIPS_NS}">{relationships}</Relationships>',
            encoding="utf-8",
        )
        slide_ids = "".join(
            f'<p:sldId id="{255 + n}" r:id="rId{n}"/>' for n in range(1, count + 1)
        )
        (root / "ppt" / "presentation.xml").write_text(
            '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<p:sldIdLst>{slide_ids}</p:sldIdLst></p:presentation>",
            encoding="utf-8",
        )
        overrides = "".join(
            f'<Override PartName="/ppt/slides/slide{n}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            for n in range(1, total + 1)
        )
        (root / "[Content_Types].xml").write_text(
            f'<Types xmlns="{clean.CONTENT_TYPES_NS}">{overrides}</Types>', encoding="utf-8"
        )

    def alternate_prefixes(self) -> None:
        for path in (self.root / "ppt/presentation.xml", self.root / "ppt/_rels/presentation.xml.rels", self.root / "[Content_Types].xml"):
            xml = path.read_text().replace("<p:", "<pres:").replace("</p:", "</pres:").replace("xmlns:p=", "xmlns:pres=")
            xml = xml.replace("r:id", "rel:id").replace("xmlns:r=", "xmlns:rel=")
            xml = xml.replace("<Relationships xmlns=", "<pkg:Relationships xmlns:pkg=")
            xml = xml.replace("</Relationships>", "</pkg:Relationships>").replace("<Relationship ", "<pkg:Relationship ")
            xml = xml.replace("<Types xmlns=", "<ct:Types xmlns:ct=").replace("</Types>", "</ct:Types>").replace("<Override ", "<ct:Override ")
            path.write_text(xml.replace('"', "'"), encoding="utf-8")


class DeckTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)


class SlideNumberingTests(DeckTestCase):
    def test_the_first_slide_in_an_empty_deck_is_one(self) -> None:
        slides = self.root / "slides"
        slides.mkdir()
        self.assertEqual(add_slide.get_next_slide_number(slides), 1)

    def test_the_next_number_follows_the_highest_existing_slide(self) -> None:
        slides = self.root / "slides"
        slides.mkdir()
        for number in (1, 2, 7):
            (slides / f"slide{number}.xml").write_text("<p:sld/>", encoding="utf-8")
        # 8, not 4: reusing a gap would collide with a relationship target.
        self.assertEqual(add_slide.get_next_slide_number(slides), 8)

    def test_files_that_are_not_slides_are_ignored(self) -> None:
        slides = self.root / "slides"
        slides.mkdir()
        (slides / "slide1.xml").write_text("<p:sld/>", encoding="utf-8")
        (slides / "slideLayout9.xml").write_text("<p:sldLayout/>", encoding="utf-8")
        (slides / "notes.xml").write_text("<x/>", encoding="utf-8")
        self.assertEqual(add_slide.get_next_slide_number(slides), 2)


class SourceParsingTests(unittest.TestCase):
    def test_a_layout_filename_is_recognised(self) -> None:
        self.assertEqual(
            add_slide.parse_source("slideLayout2.xml"), ("layout", "slideLayout2.xml")
        )

    def test_anything_else_is_treated_as_a_slide_source(self) -> None:
        for source in ("deck.pptx", "slideLayout2", "layout.xml", ""):
            with self.subTest(source=source):
                self.assertEqual(add_slide.parse_source(source), ("slide", None))


class SlideIdTests(unittest.TestCase):
    def test_the_id_range_matches_the_ooxml_specification(self) -> None:
        # Outside 256..2147483647 PowerPoint refuses to open the file.
        self.assertEqual(add_slide.SLIDE_ID_MIN, 256)
        self.assertEqual(add_slide.SLIDE_ID_MAX, 2147483647)

    def test_the_minimal_slide_xml_is_well_formed(self) -> None:
        import defusedxml.ElementTree as ElementTree

        ElementTree.fromstring(add_slide.MINIMAL_SLIDE_XML)

    def test_shared_part_types_are_the_documented_set(self) -> None:
        self.assertEqual(
            set(add_slide.SHARED_PART_TYPES),
            {"chart", "diagramData", "oleObject", "package"},
        )


class OrphanDetectionTests(DeckTestCase):
    def test_alternate_prefixes_and_single_quotes_preserve_registered_slides(self) -> None:
        deck = Deck(self.root, count=2, orphans=1)
        deck.alternate_prefixes()
        clean.clean_unused_files(self.root)
        self.assertEqual(sorted(p.name for p in deck.slides.glob("*.xml")), ["slide1.xml", "slide2.xml"])
        self.assertNotIn("slide3.xml", (self.root / "[Content_Types].xml").read_text())

    def test_one_missing_slide_relationship_refuses_even_when_others_resolve(self) -> None:
        deck = Deck(self.root, count=2, orphans=1)
        path = self.root / "ppt/presentation.xml"
        path.write_text(path.read_text().replace('r:id="rId2"', 'r:id="missing"'))
        with self.assertRaises(clean.RefusedToClean):
            clean.clean_unused_files(self.root)
        self.assertEqual(len(list(deck.slides.glob("*.xml"))), 3)

    def test_missing_presentation_metadata_refuses_before_deletion(self) -> None:
        deck = Deck(self.root, count=2)
        (self.root / "ppt/presentation.xml").unlink()
        with self.assertRaises(clean.RefusedToClean):
            clean.clean_unused_files(self.root)
        self.assertEqual(len(list(deck.slides.glob("*.xml"))), 2)

    def test_malformed_content_types_refuses_before_deletion(self) -> None:
        from xml.parsers.expat import ExpatError
        deck = Deck(self.root, count=1, orphans=1)
        (self.root / "[Content_Types].xml").write_text("<Types>")
        with self.assertRaises(ExpatError):
            clean.clean_unused_files(self.root)
        self.assertEqual(len(list(deck.slides.glob("*.xml"))), 2)

    def test_registered_slides_are_reported_as_referenced(self) -> None:
        Deck(self.root, count=3)
        self.assertEqual(
            clean.get_slides_in_sldidlst(self.root),
            {"slide1.xml", "slide2.xml", "slide3.xml"},
        )

    def test_an_unregistered_slide_is_not_reported_as_referenced(self) -> None:
        Deck(self.root, count=2, orphans=1)
        referenced = clean.get_slides_in_sldidlst(self.root)
        self.assertEqual(referenced, {"slide1.xml", "slide2.xml"})

    def test_only_the_orphan_is_removed(self) -> None:
        deck = Deck(self.root, count=2, orphans=1)
        removed = clean.remove_orphaned_slides(self.root)

        # The slide and its relationship part are both reported.
        self.assertEqual(
            sorted(Path(name).name for name in removed),
            ["slide3.xml", "slide3.xml.rels"],
        )
        self.assertTrue((deck.slides / "slide1.xml").is_file())
        self.assertTrue((deck.slides / "slide2.xml").is_file())
        self.assertFalse((deck.slides / "slide3.xml").is_file())

    def test_a_deck_with_no_orphans_loses_nothing(self) -> None:
        deck = Deck(self.root, count=3)
        self.assertEqual(clean.remove_orphaned_slides(self.root), [])
        self.assertEqual(len(list(deck.slides.glob("slide*.xml"))), 3)

    def test_a_package_with_no_slides_directory_is_a_no_op(self) -> None:
        self.assertEqual(clean.remove_orphaned_slides(self.root), [])

    def test_an_unreadable_presentation_refuses_rather_than_deleting_everything(
        self,
    ) -> None:
        # If sldIdLst cannot be parsed, every slide looks orphaned. Deleting
        # them would destroy the deck, so the tool must refuse instead.
        deck = Deck(self.root, count=3)
        # sldIdLst still lists three slides, but every r:id now points at a
        # relationship that does not exist -- exactly what a parse failure
        # looks like from here.
        (self.root / "ppt" / "presentation.xml").write_text(
            '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            "<p:sldIdLst>"
            '<p:sldId id="256" r:id="rIdMissing1"/>'
            '<p:sldId id="257" r:id="rIdMissing2"/>'
            '<p:sldId id="258" r:id="rIdMissing3"/>'
            "</p:sldIdLst></p:presentation>",
            encoding="utf-8",
        )
        with self.assertRaises(clean.RefusedToClean):
            clean.remove_orphaned_slides(self.root)
        self.assertEqual(len(list(deck.slides.glob("slide*.xml"))), 3)

    def test_the_rels_file_goes_with_its_slide(self) -> None:
        deck = Deck(self.root, count=1, orphans=1)
        clean.remove_orphaned_slides(self.root)
        self.assertFalse((deck.slides / "_rels" / "slide2.xml.rels").is_file())
        self.assertTrue((deck.slides / "_rels" / "slide1.xml.rels").is_file())


class TrashRemovalTests(DeckTestCase):
    def test_a_trash_directory_is_removed(self) -> None:
        # The directory PowerPoint leaves behind is literally named "[trash]".
        trash = self.root / "[trash]"
        trash.mkdir()
        (trash / "leftover.xml").write_text("<x/>", encoding="utf-8")
        removed = clean.remove_trash_directory(self.root)
        self.assertEqual([Path(name).name for name in removed], ["leftover.xml"])
        self.assertFalse(trash.exists())

    def test_a_package_without_one_is_untouched(self) -> None:
        self.assertEqual(clean.remove_trash_directory(self.root), [])


class PackageEditingTests(DeckTestCase):
    def test_duplicate_with_alternate_prefixes_registers_and_removes_notes(self) -> None:
        deck = Deck(self.root, count=2)
        deck.alternate_prefixes()
        rels = deck.slides / "_rels/slide1.xml.rels"
        rels.write_text(
            f'<pkg:Relationships xmlns:pkg="{RELATIONSHIPS_NS}">'
            f'<pkg:Relationship Id="rId1" Type="{clean.OFFICE_REL_NS}/notesSlide" Target="../notesSlides/notesSlide1.xml"/>'
            f'<pkg:Relationship Id="rId2" Type="{clean.OFFICE_REL_NS}/chart" Target="../charts/chart1.xml"/>'
            '</pkg:Relationships>'
        )
        created = add_slide.add_slide(self.root, "slide1.xml", after="slide1.xml")
        self.assertEqual(created, "slide3.xml")
        dom = add_slide._read_xml(self.root / "ppt/presentation.xml", clean.PRESENTATION_NS, "presentation")
        self.assertEqual([n.getAttribute("id") for n in add_slide._slide_ids(dom)], ["256", "258", "257"])
        copied_rels = (deck.slides / "_rels/slide3.xml.rels").read_text()
        self.assertNotIn("notesSlide", copied_rels)
        self.assertIn("../charts/chart1.xml", copied_rels)
        self.assertEqual(clean.get_slides_in_sldidlst(self.root), {"slide1.xml", "slide2.xml", "slide3.xml"})

    def test_bad_content_types_leaves_no_new_slide(self) -> None:
        from xml.parsers.expat import ExpatError
        deck = Deck(self.root, count=1)
        (self.root / "[Content_Types].xml").write_text("<Types>")
        with self.assertRaises(ExpatError):
            add_slide.add_slide(self.root, "slide1.xml")
        self.assertEqual([p.name for p in deck.slides.glob("*.xml")], ["slide1.xml"])

    def test_thumbnail_order_and_hidden_status_follow_namespaced_ids(self) -> None:
        deck = Deck(self.root, count=2)
        deck.alternate_prefixes()
        slide = deck.slides / "slide2.xml"
        slide.write_text(slide.read_text().replace("/>", ' show="0"/>'))
        package = self.root / "test.pptx"
        with zipfile.ZipFile(package, "w") as zf:
            for file in self.root.rglob("*.xml"):
                zf.write(file, file.relative_to(self.root))
            for file in self.root.rglob("*.rels"):
                zf.write(file, file.relative_to(self.root))
        self.assertEqual(thumbnail.get_slide_info(package), [
            {"name": "slide1.xml", "hidden": False}, {"name": "slide2.xml", "hidden": True},
        ])

    def test_thumbnail_refuses_mismatched_render_count(self) -> None:
        with self.assertRaisesRegex(ValueError, "mislabeled"):
            thumbnail.build_slide_list([{"name": "slide1.xml", "hidden": False}], [], self.root)

    def test_thumbnail_rejects_nonpositive_columns(self) -> None:
        with self.assertRaises(ValueError):
            thumbnail.create_grids([], 0, 300, self.root / "grid.jpg")


class ThumbnailConstantTests(unittest.TestCase):
    def test_the_grid_constants_are_sane(self) -> None:
        import thumbnail

        self.assertGreater(thumbnail.THUMBNAIL_WIDTH, 0)
        self.assertGreater(thumbnail.CONVERSION_DPI, 0)
        self.assertLessEqual(thumbnail.DEFAULT_COLS, thumbnail.MAX_COLS)
        self.assertTrue(0 < thumbnail.JPEG_QUALITY <= 100)


if __name__ == "__main__":
    unittest.main()
