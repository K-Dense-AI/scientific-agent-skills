"""Offline contracts for the dedicated image endpoint and retained PNG output."""
from __future__ import annotations

import base64
import importlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "scientific-schematics"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJ1sAAAAASUVORK5CYII="
)


@unittest.skipUnless(importlib.util.find_spec("requests"), "requests is not installed")
class ImageApiTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module("generate_schematic_ai")
        self.generator = self.module.ScientificSchematicGenerator(api_key="test-credential")

    def response(self, body, status=200):
        return mock.Mock(status_code=status, json=mock.Mock(return_value=body))

    def test_generation_uses_dedicated_endpoint_and_supported_fields(self):
        body = {"data": [{"b64_json": base64.b64encode(PNG).decode(), "media_type": "image/png"}]}
        with mock.patch.object(self.module.requests, "post", return_value=self.response(body)) as post:
            self.assertEqual(self.generator.generate_image("specified arrows"), PNG)
        args, kwargs = post.call_args
        self.assertEqual(args, ("https://openrouter.ai/api/v1/images",))
        self.assertEqual(kwargs["json"], {
            "model": "google/gemini-3.1-flash-image", "prompt": "specified arrows", "n": 1,
        })
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-credential")
        self.assertEqual(kwargs["timeout"], 120)
        self.assertEqual(post.call_count, 1)

    def test_review_stays_on_chat_endpoint_with_image_input(self):
        body = {"choices": [{"message": {"content": "SCORE: 9\nVERDICT: ACCEPTABLE"}}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "figure.png"
            path.write_bytes(PNG)
            with mock.patch.object(self.module.requests, "post", return_value=self.response(body)) as post:
                review = self.generator.review_image(str(path), "arrows", 1)
        args, kwargs = post.call_args
        self.assertEqual(args, ("https://openrouter.ai/api/v1/chat/completions",))
        payload = kwargs["json"]
        self.assertEqual(payload["model"], "google/gemini-3.7-flash")
        self.assertNotIn("modalities", payload)
        self.assertEqual(payload["messages"][0]["content"][1]["image_url"]["url"],
                         "data:image/png;base64," + base64.b64encode(PNG).decode())
        self.assertEqual(review.score, 9)

    def test_omitted_media_type_is_accepted_only_with_png_signature(self):
        body = {"data": [{"b64_json": base64.b64encode(PNG).decode()}]}
        self.assertEqual(self.generator._extract_image_from_response(body), PNG)

    def test_malformed_missing_or_mislabeled_images_are_rejected(self):
        for body in (
            {}, {"data": []}, {"data": [None]}, {"data": [{}]},
            {"data": [{"b64_json": "!!!!"}]},
            {"data": [{"b64_json": base64.b64encode(b"<html>error").decode()}]},
            {"data": [{"b64_json": base64.b64encode(PNG).decode(), "media_type": "image/jpeg"}]},
        ):
            with self.subTest(body=body), self.assertRaises(RuntimeError):
                self.generator._extract_image_from_response(body)

    def test_api_error_is_not_retried_or_leaked_as_an_image(self):
        body = {"error": {"message": "rejected test-credential"}}
        with mock.patch.object(self.module.requests, "post", return_value=self.response(body, 429)) as post:
            self.assertIsNone(self.generator.generate_image("arrows"))
        self.assertEqual(post.call_count, 1)
        self.assertIn("HTTP 429", self.generator._last_error)
        self.assertNotIn("test-credential", self.generator._last_error)

    def test_non_json_and_non_object_responses_report_actionable_errors(self):
        for response in (mock.Mock(status_code=502, json=mock.Mock(side_effect=ValueError)),
                         self.response([])):
            with mock.patch.object(self.module.requests, "post", return_value=response):
                self.assertIsNone(self.generator.generate_image("arrows"))
                self.assertTrue(self.generator._last_error)

    def test_second_generation_failure_preserves_first_image_and_score(self):
        review = self.module.ReviewResult("SCORE: 6", 6.0, True, True)
        self.generator._last_error = "provider failed"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "diagram.png"
            with mock.patch.object(self.generator, "generate_image", side_effect=[PNG, None]) as generate, \
                 mock.patch.object(self.generator, "review_image", return_value=review):
                result = self.generator.generate_iterative("arrows", str(output))
            self.assertEqual(output.read_bytes(), PNG)
            self.assertTrue(result["success"])
            self.assertFalse(result["quality_met"])
            self.assertTrue(result["final_reviewed"])
            self.assertEqual(result["final_score"], 6)
            self.assertEqual(result["termination_reason"], "generation_failed")
            self.assertEqual(generate.call_count, 2)
            saved = json.loads((Path(tmp) / "diagram_review_log.json").read_text())
            self.assertEqual(saved["final_image"], str(Path(tmp) / "diagram_v1.png"))
            self.assertFalse(saved["iterations"][1]["success"])

    def test_first_generation_failure_stops_without_retry_or_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "diagram.png"
            with mock.patch.object(self.generator, "generate_image", return_value=None) as generate:
                result = self.generator.generate_iterative("arrows", str(output))
            self.assertFalse(output.exists())
            self.assertFalse(result["success"])
            self.assertEqual(result["termination_reason"], "generation_failed")
            self.assertEqual(generate.call_count, 1)

    def test_unscored_review_saves_png_without_quality_claim(self):
        review = self.module.ReviewResult("unavailable", None, False, False, "timeout")
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(self.generator, "generate_image", return_value=PNG) as generate, \
                 mock.patch.object(self.generator, "review_image", return_value=review):
                result = self.generator.generate_iterative("arrows", str(Path(tmp) / "diagram.png"))
            self.assertTrue(result["success"])
            self.assertFalse(result["quality_met"])
            self.assertFalse(result["final_reviewed"])
            self.assertIsNone(result["final_score"])
            self.assertEqual(generate.call_count, 1)

    def test_public_python_api_rejects_invalid_budget_format_and_document_type(self):
        with mock.patch.object(self.module.requests, "post") as post:
            for kwargs in ({"iterations": 0}, {"iterations": 3}, {"iterations": True},
                           {"iterations": 1.5}, {"doc_type": "imaginary"}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    self.generator.generate_iterative("arrows", "diagram.png", **kwargs)
            for path in ("diagram.pdf", "diagram.jpg", "diagram"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    self.generator.generate_iterative("arrows", path)
            post.assert_not_called()
