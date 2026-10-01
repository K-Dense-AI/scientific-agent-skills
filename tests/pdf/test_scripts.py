"""Tests for the pdf skill's form tooling.

The coordinate transforms are the part worth pinning. PDF puts the origin at
the bottom-left and images put it at the top-left, so filling a form from
image-space boxes means flipping the y axis and scaling both axes. Getting the
flip backwards places every field on the wrong half of the page, and nothing
raises -- the output just looks wrong. Both transforms are pure arithmetic, so
they are tested directly with hand-computed expectations.

The remaining tests build real PDFs with reportlab where a fixture is needed,
and skip when the reader libraries are absent.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pdf"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

# The preview converter exposes argparse; the remaining helpers use positional paths.
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def coords():
    pytest.importorskip("pypdf", reason="pdf scripts need pypdf")
    import fill_pdf_form_with_annotations

    return fill_pdf_form_with_annotations


class ImageToPdfTransformTests(unittest.TestCase):
    """Image space: origin top-left, y grows down. PDF: origin bottom-left."""

    def test_a_box_at_the_image_origin_lands_at_the_pdf_top(self) -> None:
        # Image (0,0)-(100,50) on a 1000x500 image over a 200x100 page:
        # x scales by 0.2, y flips -> top of the page.
        transformed = coords().transform_from_image_coords(
            (0, 0, 100, 50), 1000, 500, 200, 100
        )
        left, bottom, right, top = transformed
        self.assertAlmostEqual(left, 0.0)
        self.assertAlmostEqual(right, 20.0)
        self.assertAlmostEqual(top, 100.0)
        self.assertAlmostEqual(bottom, 90.0)

    def test_a_box_at_the_image_bottom_lands_at_the_pdf_origin(self) -> None:
        transformed = coords().transform_from_image_coords(
            (0, 450, 100, 500), 1000, 500, 200, 100
        )
        _, bottom, _, top = transformed
        self.assertAlmostEqual(bottom, 0.0)
        self.assertAlmostEqual(top, 10.0)

    def test_identity_scaling_only_flips_the_y_axis(self) -> None:
        transformed = coords().transform_from_image_coords(
            (10, 20, 30, 40), 100, 100, 100, 100
        )
        left, bottom, right, top = transformed
        self.assertAlmostEqual(left, 10.0)
        self.assertAlmostEqual(right, 30.0)
        self.assertAlmostEqual(bottom, 60.0)  # 100 - 40
        self.assertAlmostEqual(top, 80.0)  # 100 - 20

    def test_the_box_keeps_its_size_under_a_pure_flip(self) -> None:
        left, bottom, right, top = coords().transform_from_image_coords(
            (10, 20, 30, 50), 100, 100, 100, 100
        )
        self.assertAlmostEqual(right - left, 20.0)
        self.assertAlmostEqual(top - bottom, 30.0)

    def test_the_transform_is_invertible_within_rounding(self) -> None:
        original = (12.0, 34.0, 56.0, 78.0)
        once = coords().transform_from_image_coords(original, 200, 200, 200, 200)
        twice = coords().transform_from_image_coords(once, 200, 200, 200, 200)
        for expected, actual in zip(original, twice):
            self.assertAlmostEqual(expected, actual, places=6)


class PdfCoordinateTests(unittest.TestCase):
    def test_the_y_axis_is_flipped_about_the_page_height(self) -> None:
        left, bottom, right, top = coords().transform_from_pdf_coords(
            (10, 20, 30, 40), 100
        )
        self.assertAlmostEqual(left, 10.0)
        self.assertAlmostEqual(right, 30.0)
        self.assertAlmostEqual(bottom, 60.0)
        self.assertAlmostEqual(top, 80.0)

    def test_flipping_twice_returns_the_original(self) -> None:
        original = (5.0, 15.0, 25.0, 35.0)
        once = coords().transform_from_pdf_coords(original, 100)
        twice = coords().transform_from_pdf_coords(once, 100)
        for expected, actual in zip(original, twice):
            self.assertAlmostEqual(expected, actual, places=9)

    def test_a_box_spanning_the_full_page_is_unchanged_vertically(self) -> None:
        _, bottom, _, top = coords().transform_from_pdf_coords((0, 0, 10, 100), 100)
        self.assertAlmostEqual(bottom, 0.0)
        self.assertAlmostEqual(top, 100.0)


def field(description: str, label: list, entry: list, page: int = 1) -> dict:
    return {
        "description": description,
        "label_bounding_box": label,
        "entry_bounding_box": entry,
        "page_number": page,
    }


class BoundingBoxCheckTests(unittest.TestCase):
    """Overlapping boxes put text on top of text in the filled PDF."""

    def _messages(self, *fields) -> list[str]:
        import check_bounding_boxes

        return check_bounding_boxes.get_bounding_box_messages(
            io.StringIO(json.dumps({"form_fields": list(fields)}))
        )

    def _failures(self, *fields) -> list[str]:
        return [m for m in self._messages(*fields) if m.startswith("FAILURE")]

    def test_a_clean_layout_reports_only_the_field_count(self) -> None:
        messages = self._messages(
            field("Full name", [10, 10, 100, 30], [110, 10, 300, 30]),
            field("Email", [10, 40, 100, 60], [110, 40, 300, 60]),
        )
        self.assertEqual(
            messages, ["Read 2 fields", "SUCCESS: All bounding boxes are valid"]
        )

    def test_an_empty_form_reports_zero_fields(self) -> None:
        self.assertEqual(
            self._messages(), ["Read 0 fields", "SUCCESS: All bounding boxes are valid"]
        )

    def test_a_label_overlapping_its_own_entry_is_reported(self) -> None:
        failures = self._failures(
            field("Full name", [10, 10, 100, 30], [50, 10, 300, 30])
        )
        self.assertTrue(failures)
        self.assertIn("label and entry", failures[0])
        self.assertIn("Full name", failures[0])

    def test_two_fields_overlapping_each_other_are_reported(self) -> None:
        failures = self._failures(
            field("Full name", [10, 10, 100, 30], [110, 10, 300, 30]),
            field("Email", [90, 15, 200, 25], [310, 15, 400, 25]),
        )
        self.assertTrue(failures)
        joined = " ".join(failures)
        self.assertIn("Full name", joined)
        self.assertIn("Email", joined)

    def test_boxes_on_different_pages_never_collide(self) -> None:
        self.assertEqual(
            self._failures(
                field("A", [10, 10, 100, 30], [110, 10, 300, 30], page=1),
                field("B", [10, 10, 100, 30], [110, 10, 300, 30], page=2),
            ),
            [],
        )

    def test_boxes_that_merely_touch_do_not_count_as_intersecting(self) -> None:
        # Edge-sharing is how adjacent fields are normally laid out.
        self.assertEqual(
            self._failures(field("A", [10, 10, 100, 30], [100, 10, 200, 30])), []
        )

    def test_the_report_stops_after_twenty_messages(self) -> None:
        # A form where everything overlaps would otherwise produce thousands.
        overlapping = [
            field(f"Field {index}", [0, 0, 100, 100], [0, 0, 100, 100])
            for index in range(30)
        ]
        messages = self._messages(*overlapping)
        self.assertLessEqual(len(messages), 21)
        self.assertIn("Aborting further checks", messages[-1])


class FieldDescriptorTests(unittest.TestCase):
    """`make_field_dict` turns raw AcroForm entries into the filler's schema."""

    def _descriptor(self, raw: dict, field_id: str = "full_name") -> dict:
        pytest.importorskip("pypdf", reason="pdf scripts need pypdf")
        import extract_form_field_info

        return extract_form_field_info.make_field_dict(raw, field_id)

    def test_a_text_field_is_typed_as_text(self) -> None:
        descriptor = self._descriptor({"/FT": "/Tx"})
        self.assertEqual(descriptor["type"], "text")
        self.assertEqual(descriptor["field_id"], "full_name")

    def test_a_checkbox_learns_its_checked_and_unchecked_values(self) -> None:
        descriptor = self._descriptor(
            {"/FT": "/Btn", "/_States_": ["/Off", "/Yes"]}, "subscribe"
        )
        self.assertEqual(descriptor["type"], "checkbox")
        self.assertEqual(descriptor["checked_value"], "/Yes")
        self.assertEqual(descriptor["unchecked_value"], "/Off")

    def test_the_state_order_does_not_decide_which_value_means_checked(self) -> None:
        # "/Off" is the unchecked state wherever it appears in the list.
        descriptor = self._descriptor({"/FT": "/Btn", "/_States_": ["/Yes", "/Off"]})
        self.assertEqual(descriptor["checked_value"], "/Yes")
        self.assertEqual(descriptor["unchecked_value"], "/Off")

    def test_a_choice_field_carries_its_options(self) -> None:
        descriptor = self._descriptor(
            {"/FT": "/Ch", "/_States_": [("a", "Alpha"), ("b", "Beta")]}, "pick"
        )
        self.assertEqual(descriptor["type"], "choice")
        self.assertEqual(
            descriptor["choice_options"],
            [{"value": "a", "text": "Alpha"}, {"value": "b", "text": "Beta"}],
        )

    def test_an_unrecognised_field_type_is_labelled_rather_than_dropped(self) -> None:
        descriptor = self._descriptor({"/FT": "/Sig"})
        self.assertIn("unknown", descriptor["type"])
        self.assertIn("/Sig", descriptor["type"])


class ValueValidationTests(unittest.TestCase):
    def _error(self, field_info, value):
        pytest.importorskip("pypdf", reason="pdf scripts need pypdf")
        import fill_fillable_fields

        return fill_fillable_fields.validation_error_for_field_value(field_info, value)

    CHECKBOX = {
        "field_id": "subscribe",
        "type": "checkbox",
        "checked_value": "/Yes",
        "unchecked_value": "/Off",
    }

    def test_a_checkbox_accepts_only_its_two_declared_states(self) -> None:
        self.assertIsNone(self._error(self.CHECKBOX, "/Yes"))
        self.assertIsNone(self._error(self.CHECKBOX, "/Off"))

        error = self._error(self.CHECKBOX, "/Maybe")
        self.assertIsNotNone(error)
        self.assertIn("subscribe", error)
        self.assertIn("/Yes", error)

    def test_a_choice_field_accepts_only_its_option_values(self) -> None:
        choice = {
            "field_id": "country",
            "type": "choice",
            "choice_options": [{"value": "uk", "text": "United Kingdom"}],
        }
        self.assertIsNone(self._error(choice, "uk"))
        # The display text is not a valid value -- only the option value is.
        self.assertIsNotNone(self._error(choice, "United Kingdom"))

    def test_a_radio_group_accepts_only_its_option_values(self) -> None:
        radio = {
            "field_id": "size",
            "type": "radio_group",
            "radio_options": [{"value": "/S"}, {"value": "/M"}],
        }
        self.assertIsNone(self._error(radio, "/M"))
        self.assertIsNotNone(self._error(radio, "/XL"))

    def test_a_text_field_accepts_any_string(self) -> None:
        text_field = {"field_id": "full_name", "type": "text"}
        for value in ("Ada Lovelace", "", "12345"):
            with self.subTest(value=value):
                self.assertIsNone(self._error(text_field, value))


if __name__ == "__main__":
    unittest.main()
