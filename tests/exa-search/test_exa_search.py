"""Unit tests for the exa-search skill scripts.

These tests mock the SDK or its HTTP transport and never hit the live API.
Run from the repository root:

    python tests/run_all.py --isolated exa-search

Tests cover: CLI argument plumbing, the content-options builder (text /
highlights), CSV splitting for domain lists, the content fallback
cascade, and the x-exa-integration header wiring.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest

import pytest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import skill_contract

# Guarded so a bare project-environment run skips cleanly instead of failing;
# the real run is `tests/run_all.py --isolated exa-search`.
pytest.importorskip("exa_py", reason="exa-search needs exa-py")

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "exa-search"
SCRIPTS_DIR = SKILL_ROOT / "scripts"


def _load_script(name: str):
    """Load one of the scripts as a module regardless of cwd."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _fake_result(**overrides):
    defaults = {
        "title": "Attention Is All You Need",
        "url": "https://arxiv.org/abs/1706.03762",
        "id": "abc123",
        "author": "Vaswani et al.",
        "published_date": "2017-06-12",
        "score": 0.91,
        "text": "Full paper text here",
        "highlights": ["The Transformer relies entirely on self-attention"],
        "highlight_scores": [0.87],
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class BuildContentsTests(unittest.TestCase):
    """Check explicit content selection in both scripts."""

    def setUp(self):
        self.search_mod = _load_script("exa_search")
        self.extract_mod = _load_script("exa_extract")

    def test_search_no_flags_returns_none(self):
        self.assertIsNone(self.search_mod._build_contents(False, False))

    def test_search_text_only(self):
        self.assertEqual(self.search_mod._build_contents(True, False), {"text": True})

    def test_search_highlights_only(self):
        self.assertEqual(
            self.search_mod._build_contents(False, True),
            {"highlights": True},
        )

    def test_search_text_and_highlights_combine(self):
        self.assertEqual(
            self.search_mod._build_contents(True, True),
            {"text": True, "highlights": True},
        )

    def test_extract_defaults_to_text_when_nothing_specified(self):
        self.assertEqual(self.extract_mod._build_contents(False, False), {"text": True})

    def test_extract_highlights_suppresses_sdk_default_text(self):
        self.assertEqual(self.extract_mod._build_contents(False, True),
                         {"highlights": True, "text": False})


class SplitCsvTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load_script("exa_search")

    def test_none_returns_none(self):
        self.assertIsNone(self.mod._split_csv(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(self.mod._split_csv(""))

    def test_splits_and_trims(self):
        self.assertEqual(
            self.mod._split_csv("arxiv.org, nature.com ,pubmed.gov"),
            ["arxiv.org", "nature.com", "pubmed.gov"],
        )

    def test_ignores_empty_segments(self):
        self.assertEqual(self.mod._split_csv("a,, b,"), ["a", "b"])


class ResultTypingTests(unittest.TestCase):
    """Verify the Any → typed-dataclass conversion handles missing fields."""

    def setUp(self):
        self.mod = _load_script("exa_search")

    def test_full_result(self):
        item = _fake_result()
        typed = self.mod._result_to_typed(item)
        self.assertEqual(typed.url, "https://arxiv.org/abs/1706.03762")
        self.assertEqual(typed.highlights, ["The Transformer relies entirely on self-attention"])
        self.assertEqual(typed.highlight_scores, [0.87])

    def test_missing_optional_fields_default_cleanly(self):
        item = SimpleNamespace(url="https://example.com")
        typed = self.mod._result_to_typed(item)
        self.assertEqual(typed.url, "https://example.com")
        self.assertIsNone(typed.title)
        self.assertIsNone(typed.text)
        self.assertEqual(typed.highlights, [])
        self.assertEqual(typed.highlight_scores, [])

    def test_highlights_only_response(self):
        """Content fallback: when only highlights are present, text must stay None."""
        item = _fake_result(text=None, highlights=["snippet A", "snippet B"])
        typed = self.mod._result_to_typed(item)
        self.assertIsNone(typed.text)
        self.assertEqual(typed.highlights, ["snippet A", "snippet B"])

    def test_text_only_response(self):
        item = _fake_result(highlights=[], highlight_scores=[])
        typed = self.mod._result_to_typed(item)
        self.assertEqual(typed.text, "Full paper text here")
        self.assertEqual(typed.highlights, [])


class IntegrationHeaderAndFlowTests(unittest.TestCase):
    """End-to-end: run() sets the integration header and calls the right SDK method."""

    def setUp(self):
        self.mod = _load_script("exa_search")

    def _run_with_mock(self, argv):
        fake_client = MagicMock()
        fake_client.headers = {}
        fake_client.search_and_contents.return_value = SimpleNamespace(
            results=[_fake_result()],
            autoprompt_string=None,
        )
        fake_client.search.return_value = SimpleNamespace(
            results=[_fake_result()],
            autoprompt_string=None,
        )
        # Mock at the source module so the import inside the script gets the fake.
        # NOTE: the script does `from exa_py import Exa` at module top, so the name
        # to patch is the already-imported binding on the script module itself.
        with patch.object(self.mod, "Exa", return_value=fake_client) as ctor, \
             patch.dict(os.environ, {"EXA_API_KEY": "test-key"}, clear=False):
            args = self.mod.build_parser().parse_args(argv)
            payload = self.mod.run(args)
        return payload, fake_client, ctor

    def test_integration_header_is_set(self):
        _, client, _ = self._run_with_mock(["what is attention", "--highlights"])
        self.assertEqual(
            client.headers.get("x-exa-integration"),
            "k-dense-ai--scientific-agent-skills",
        )

    def test_uses_current_search_contents_parameter(self):
        _, client, _ = self._run_with_mock(["query", "--text"])
        client.search.assert_called_once_with(query="query", num_results=10,
                                              type="auto", contents={"text": True})
        client.search_and_contents.assert_not_called()

    def test_calls_search_when_no_contents_flags(self):
        _, client, _ = self._run_with_mock(["query"])
        client.search.assert_called_once()
        self.assertIs(client.search.call_args.kwargs["contents"], False)
        client.search_and_contents.assert_not_called()

    def test_legacy_scholarly_category_maps_to_publication(self):
        _, client, _ = self._run_with_mock(["query", "--category", "research paper"])
        self.assertEqual(client.search.call_args.kwargs["category"], "publication")

    def test_invalid_filters_fail_before_constructing_client(self):
        for argv in (["q", "--num-results", "0"], ["q", "--num-results", "101"],
                     ["q", "--category", "people", "--exclude-domains", "example.com"],
                     ["q", "--category", "company", "--start-published-date", "2026-01-01T00:00:00Z"]):
            with self.subTest(argv=argv), patch.object(self.mod, "Exa") as ctor:
                with self.assertRaises(ValueError):
                    self.mod.run(self.mod.build_parser().parse_args(argv))
                ctor.assert_not_called()

    def test_domain_filters_are_split_and_passed(self):
        _, client, _ = self._run_with_mock(
            ["q", "--include-domains", "arxiv.org, nature.com", "--exclude-domains", "spam.com"]
        )
        kwargs = client.search.call_args.kwargs
        self.assertEqual(kwargs["include_domains"], ["arxiv.org", "nature.com"])
        self.assertEqual(kwargs["exclude_domains"], ["spam.com"])

    def test_missing_api_key_exits_with_code_2(self):
        # Remove EXA_API_KEY for this call only.
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as ctx:
                self.mod.run(self.mod.build_parser().parse_args(["q"]))
            self.assertEqual(ctx.exception.code, 2)

    def test_output_file_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "results.json"
            fake_client = MagicMock()
            fake_client.headers = {}
            fake_client.search.return_value = SimpleNamespace(
                results=[_fake_result()],
                autoprompt_string=None,
            )
            with patch.object(self.mod, "Exa", return_value=fake_client), \
                 patch.dict(os.environ, {"EXA_API_KEY": "k"}, clear=False):
                rc = self.mod.main(["q", "-o", str(out)])
            self.assertEqual(rc, 0)
            self.assertTrue(out.exists())
            payload = json.loads(out.read_text())
            self.assertEqual(payload["num_results"], 1)
            self.assertEqual(payload["results"][0]["title"], "Attention Is All You Need")


class RealSdkTransportTests(unittest.TestCase):
    """Exercise SDK serialization, defaults, headers and result parsing offline."""

    def _run(self, script, argv, response_data):
        module = _load_script(script)
        response = MagicMock(status_code=200)
        response.json.return_value = response_data
        with patch("exa_py.api.requests.post", return_value=response) as post, \
             patch.dict(os.environ, {"EXA_API_KEY": "offline-test-key"}):
            payload = module.run(module.build_parser().parse_args(argv))
        return payload, post.call_args

    def test_search_serializes_current_filters_and_contents(self):
        payload, call = self._run("exa_search", [
            "CRISPR", "--category", "publication", "--type", "deep-reasoning",
            "--highlights", "--include-domains", "arxiv.org,nature.com",
            "--start-published-date", "2026-01-01T00:00:00Z", "--user-location", "US",
        ], {"results": [{"url": "https://arxiv.org/abs/example", "id": "doc",
                        "publishedDate": "2026-01-02", "highlights": ["Finding"]}]})
        self.assertEqual(call.args[0], "https://api.exa.ai/search")
        body = json.loads(call.kwargs["data"])
        self.assertEqual(body["contents"], {"highlights": True})
        self.assertEqual(body["category"], "publication")
        self.assertEqual(body["type"], "deep-reasoning")
        self.assertEqual(body["includeDomains"], ["arxiv.org", "nature.com"])
        self.assertEqual(body["startPublishedDate"], "2026-01-01T00:00:00Z")
        self.assertEqual(body["userLocation"], "US")
        self.assertEqual(call.kwargs["headers"]["x-api-key"], "offline-test-key")
        self.assertEqual(call.kwargs["headers"]["x-exa-integration"],
                         "k-dense-ai--scientific-agent-skills")
        self.assertEqual(payload["results"][0]["published_date"], "2026-01-02")
        self.assertIsNone(payload["results"][0]["score"])
        self.assertEqual(payload["results"][0]["highlight_scores"], [])

    def test_search_without_content_flags_does_not_request_text(self):
        _, call = self._run("exa_search", ["CRISPR"], {"results": []})
        self.assertNotIn("contents", json.loads(call.kwargs["data"]))

    def test_extraction_preserves_partial_statuses_and_freshness(self):
        payload, call = self._run("exa_extract", [
            "https://example.com/a", "https://example.com/b", "--highlights", "--max-age-hours", "0",
        ], {"results": [{"url": "https://example.com/a", "id": "https://example.com/a",
                         "highlights": ["Extract"]}],
            "statuses": [{"id": "https://example.com/a", "status": "success", "source": "crawled"},
                         {"id": "https://example.com/b", "status": "error",
                          "error": {"tag": "CRAWL_TIMEOUT", "httpStatusCode": None}}]})
        self.assertEqual(call.args[0], "https://api.exa.ai/contents")
        body = json.loads(call.kwargs["data"])
        self.assertEqual(body, {"urls": ["https://example.com/a", "https://example.com/b"],
                                "highlights": True, "text": False, "maxAgeHours": 0})
        self.assertEqual(payload["num_results"], 1)
        self.assertEqual(payload["statuses"][0]["source"], "crawled")
        self.assertEqual(payload["statuses"][1],
                         {"id": "https://example.com/b", "status": "error", "source": None})

    def test_extract_rejects_oversized_batch_and_invalid_age_without_http(self):
        module = _load_script("exa_extract")
        for argv in (["https://example.com"] * 101,
                     ["https://example.com", "--max-age-hours", "721"],
                     ["https://example.com", "--max-age-hours", "-2"]):
            with self.subTest(argv=argv), patch.object(module, "Exa") as ctor:
                with self.assertRaises(ValueError):
                    module.run(module.build_parser().parse_args(argv))
                ctor.assert_not_called()

    def test_extract_accepts_100_urls_and_cache_only(self):
        urls = [f"https://example.com/{i}" for i in range(100)]
        _, call = self._run("exa_extract", urls + ["--max-age-hours", "-1"], {"results": []})
        body = json.loads(call.kwargs["data"])
        self.assertEqual(body["urls"], urls)
        self.assertEqual(body["maxAgeHours"], -1)
        self.assertIs(body["text"], True)


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

if __name__ == "__main__":
    unittest.main()
