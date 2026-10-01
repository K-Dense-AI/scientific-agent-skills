"""Offline endpoint, provenance, and draft-retention regressions."""
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

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "infographics"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJ1sAAAAASUVORK5CYII="
)


@unittest.skipUnless(importlib.util.find_spec("requests"), "requests is not installed")
class ApiTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module("generate_infographic_ai")
        self.generator = self.module.InfographicGenerator(api_key="test-credential")

    @staticmethod
    def response(body, status=200):
        return mock.Mock(status_code=status, json=mock.Mock(return_value=body))

    def test_image_endpoint_contract_and_reference_images(self):
        body = {"data": [{"b64_json": base64.b64encode(PNG).decode(), "media_type": "image/png"}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "reference.png"
            path.write_bytes(PNG)
            with mock.patch.object(self.module.requests, "post", return_value=self.response(body)) as post:
                self.assertEqual(self.generator.generate_image("values", [str(path)]), PNG)
        args, kwargs = post.call_args
        self.assertEqual(args, ("https://openrouter.ai/api/v1/images",))
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-credential")
        self.assertEqual(kwargs["timeout"], 120)
        self.assertEqual(kwargs["json"], {
            "model": "google/gemini-3.1-flash-image", "prompt": "values", "n": 1,
            "input_references": [{"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(PNG).decode(),
            }}],
        })
        self.assertEqual(post.call_count, 1)

    def test_png_response_contract_checks_mime_base64_and_signature(self):
        valid = {"data": [{"b64_json": base64.b64encode(PNG).decode()}]}
        self.assertEqual(self.generator._extract_image_from_response(valid), PNG)
        for body in ({}, {"data": []}, {"data": [None]}, {"data": [{}]},
                     {"data": [{"b64_json": "!"}]},
                     {"data": [{"b64_json": base64.b64encode(b"<html>").decode()}]},
                     {"data": [{"b64_json": base64.b64encode(PNG).decode(), "media_type": "image/jpeg"}]}):
            with self.subTest(body=body), self.assertRaises(RuntimeError):
                self.generator._extract_image_from_response(body)

    def test_error_is_redacted_and_never_retried(self):
        body = {"error": {"message": "rejected test-credential"}}
        with mock.patch.object(self.module.requests, "post", return_value=self.response(body, 429)) as post:
            self.assertIsNone(self.generator.generate_image("values"))
        self.assertEqual(post.call_count, 1)
        self.assertIn("HTTP 429", self.generator._last_error)
        self.assertNotIn("test-credential", self.generator._last_error)

    def test_non_json_and_non_object_responses_are_rejected(self):
        for response in (mock.Mock(status_code=502, json=mock.Mock(side_effect=ValueError)),
                         self.response([])):
            with mock.patch.object(self.module.requests, "post", return_value=response):
                self.assertIsNone(self.generator.generate_image("values"))
                self.assertTrue(self.generator._last_error)

    def test_review_uses_vision_chat_and_marketing_threshold(self):
        body = {"choices": [{"message": {"content": "SCORE: 8.2\nVERDICT: ACCEPTABLE"}}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "figure.png"
            path.write_bytes(PNG)
            with mock.patch.object(self.module.requests, "post", return_value=self.response(body)) as post:
                review = self.generator.review_image(str(path), "values", "statistical", 1, "marketing")
        args, kwargs = post.call_args
        self.assertEqual(args, ("https://openrouter.ai/api/v1/chat/completions",))
        self.assertEqual(kwargs["json"]["model"], "google/gemini-3.7-flash")
        self.assertNotIn("modalities", kwargs["json"])
        parts = kwargs["json"]["messages"][0]["content"]
        self.assertIn("8.5/10", parts[0]["text"])
        self.assertTrue(parts[1]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertTrue(review.needs_improvement)

    def test_research_and_web_search_preserve_normalized_source_records(self):
        citation = {"url": "https://example.org/study", "title": "Example study", "start_index": 0, "end_index": 4}
        annotations = [{"type": "url_citation", "url_citation": citation}]
        body = {"choices": [{"message": {"content": "A=12", "annotations": annotations}}],
                "search_results": [{"title": "Provider result"}], "citations": [citation["url"]]}
        for method, context in ((self.generator.research_topic, "high"), (self.generator.web_search, "medium")):
            with mock.patch.object(self.module.requests, "post", return_value=self.response(body)) as post:
                result = method("a topic")
            self.assertTrue(result["success"])
            self.assertEqual(result["sources"], [citation])
            self.assertEqual(result["annotations"], annotations)
            self.assertEqual(result["search_results"], body["search_results"])
            self.assertEqual(result["citations"], body["citations"])
            args, kwargs = post.call_args
            self.assertEqual(args, ("https://openrouter.ai/api/v1/chat/completions",))
            self.assertEqual(kwargs["json"]["web_search_options"], {"search_context_size": context})
            self.assertNotIn("search_mode", kwargs["json"])
            self.assertNotIn("search_context_size", kwargs["json"])

    def test_empty_research_is_not_reported_as_success(self):
        for content in (None, "", [], {"unexpected": "text"}):
            body = {"choices": [{"message": {"content": content}}]}
            with mock.patch.object(self.module.requests, "post", return_value=self.response(body)):
                self.assertFalse(self.generator.research_topic("topic")["success"])

    def test_refinement_retains_research_and_failed_final_call_retains_draft(self):
        research = {"success": True, "content": "A=12", "sources": [{"url": "https://example.org/study"}]}
        review = self.module.ReviewResult("SCORE: 6", 6.0, True, True)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "chart.png"
            with mock.patch.object(self.generator, "research_topic", return_value=research), \
                 mock.patch.object(self.generator, "generate_image", side_effect=[PNG, None]) as generate, \
                 mock.patch.object(self.generator, "review_image", return_value=review) as reviewer:
                result = self.generator.generate_iterative("topic", str(output), research=True)
            self.assertEqual(output.read_bytes(), PNG)
            self.assertEqual(generate.call_count, 2)
            for call in generate.call_args_list:
                self.assertIn("A=12", call.args[0])
                self.assertIn("https://example.org/study", call.args[0])
            self.assertIn("A=12", reviewer.call_args.args[1])
            self.assertTrue(result["success"])
            self.assertFalse(result["quality_met"])
            self.assertEqual(result["final_score"], 6)
            self.assertEqual(result["termination_reason"], "generation_failed")
            saved = json.loads((Path(tmp) / "chart_review_log.json").read_text())
            self.assertEqual(saved["research_data"], research)
            self.assertFalse(saved["iterations"][1]["success"])

    def test_first_generation_failure_stops_without_a_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "chart.png"
            with mock.patch.object(self.generator, "generate_image", return_value=None) as generate:
                result = self.generator.generate_iterative("topic", str(output))
            self.assertFalse(result["success"])
            self.assertFalse(output.exists())
            self.assertEqual(result["termination_reason"], "generation_failed")
            self.assertEqual(generate.call_count, 1)

    def test_unavailable_review_saves_draft_without_quality_claim(self):
        review = self.module.ReviewResult("failed", None, False, False, "timeout")
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(self.generator, "generate_image", return_value=PNG), \
                 mock.patch.object(self.generator, "review_image", return_value=review):
                result = self.generator.generate_iterative("topic", str(Path(tmp) / "chart.png"))
        self.assertTrue(result["success"])
        self.assertFalse(result["quality_met"])
        self.assertFalse(result["final_reviewed"])
        self.assertIsNone(result["final_score"])
        self.assertEqual(result["termination_reason"], "review_unavailable")

    def test_quality_status_tracks_both_score_and_requested_improvements(self):
        for score, needs_improvement, expected, reason in (
            (9.0, False, True, "quality_met"),
            (6.0, True, False, "max_iterations"),
            (9.0, True, False, "max_iterations"),
        ):
            review = self.module.ReviewResult("critique", score, needs_improvement, True)
            with self.subTest(score=score, needs_improvement=needs_improvement), \
                 tempfile.TemporaryDirectory() as tmp, \
                 mock.patch.object(self.generator, "generate_image", return_value=PNG), \
                 mock.patch.object(self.generator, "review_image", return_value=review):
                result = self.generator.generate_iterative("topic", str(Path(tmp) / "chart.png"), iterations=1)
                self.assertEqual(result["quality_met"], expected)
                self.assertEqual(result["termination_reason"], reason)

    def test_internal_reasoning_is_not_a_passing_review_answer(self):
        body = {"choices": [{"message": {"content": None, "reasoning": "SCORE: 9\nVERDICT: ACCEPTABLE"}}]}
        with mock.patch.object(self.generator, "_image_to_base64", return_value="data:image/png;base64,AAAA"), \
             mock.patch.object(self.module.requests, "post", return_value=self.response(body)):
            review = self.generator.review_image("image.png", "values", None, 1)
        self.assertIsNone(review.score)
        self.assertIsNotNone(review.error)

    def test_invalid_options_fail_before_network_calls(self):
        with mock.patch.object(self.module.requests, "post") as post:
            for kwargs in ({"iterations": 0}, {"iterations": -1}, {"iterations": True},
                           {"iterations": 1.5}, {"doc_type": "imaginary"},
                           {"palette": "rainbow"}, {"context_images": ["a.png"] * 15}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    self.generator.generate_iterative("values", "chart.png", **kwargs)
            for output in ("chart", "chart.jpg", "chart.pdf"):
                with self.subTest(output=output), self.assertRaises(ValueError):
                    self.generator.generate_iterative("values", output)
            post.assert_not_called()

    def test_wrapper_forwards_context_references_without_putting_key_in_args(self):
        wrapper = importlib.import_module("generate_infographic")
        argv = ["generate_infographic.py", "topic", "-o", "chart.png", "--context-image", "brand.png"]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(wrapper, "resolve_api_key", return_value="test-credential"), \
             mock.patch.object(wrapper.subprocess, "run", return_value=mock.Mock(returncode=0)) as run, \
             self.assertRaises(SystemExit) as caught:
            wrapper.main()
        self.assertEqual(caught.exception.code, 0)
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[-2:], ["--context-image", "brand.png"])
        self.assertNotIn("test-credential", cmd)
        self.assertEqual(run.call_args.kwargs["env"]["OPENROUTER_API_KEY"], "test-credential")
