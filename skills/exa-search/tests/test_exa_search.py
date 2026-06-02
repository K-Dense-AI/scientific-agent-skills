"""Unit tests for the exa-search skill scripts.

These tests mock the Exa SDK so they never hit the live API. Run from the
skill root:

    python -m unittest discover -s tests -v

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
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

SKILL_ROOT = Path(__file__).resolve().parent.parent
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
    """The content-options builder is shared logic across all three scripts."""

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

    def test_calls_search_and_contents_when_contents_requested(self):
        _, client, _ = self._run_with_mock(["query", "--text"])
        client.search_and_contents.assert_called_once()
        client.search.assert_not_called()

    def test_calls_search_when_no_contents_flags(self):
        _, client, _ = self._run_with_mock(["query"])
        client.search.assert_called_once()
        client.search_and_contents.assert_not_called()

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


if __name__ == "__main__":
    unittest.main()
