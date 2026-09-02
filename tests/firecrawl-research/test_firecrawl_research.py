"""Unit tests for the firecrawl-research skill scripts.

These tests mock the Firecrawl SDK so they never hit the live API. Run the
suite from the repository root:

    uv run --with pytest python -m pytest tests/firecrawl-research -q

Tests cover: CSV filter splitting, the keyless/authenticated client fallback,
response normalisation across the two shapes the SDK returns (plain dicts from
the research endpoints, a pydantic model from `search`), the empty-passages
warning, and subcommand argument plumbing.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import skill_contract

# Guarded so a bare project-environment run skips cleanly instead of failing;
# the real run is `tests/run_all.py --isolated firecrawl-research`.
pytest.importorskip("firecrawl", reason="firecrawl-research needs firecrawl-py")

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "firecrawl-research"
SCRIPTS_DIR = SKILL_ROOT / "scripts"


def _load_script(name: str):
    """Load the script as a module regardless of cwd."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _paper_hit(**overrides):
    defaults = {
        "paperId": "3935048904807925401",
        "primaryId": "arxiv:1706.03762",
        "ids": {"doi": ["10.48550/arXiv.1706.03762"]},
        "title": "Attention Is All You Need",
        "abstract": "The dominant sequence transduction models ...",
        "score": 0.97,
    }
    defaults.update(overrides)
    return defaults


class SplitCsvTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load_script("firecrawl_research")

    def test_none_returns_none(self):
        self.assertIsNone(self.mod._split_csv(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(self.mod._split_csv(""))

    def test_splits_and_trims(self):
        self.assertEqual(self.mod._split_csv("cs.LG, q-bio.GN ,stat.ML"), ["cs.LG", "q-bio.GN", "stat.ML"])

    def test_ignores_empty_segments(self):
        self.assertEqual(self.mod._split_csv("a,, b,"), ["a", "b"])


class ClientAuthTests(unittest.TestCase):
    """The key is optional, but running keyless must be announced.

    These build the *real* client rather than a mock: the top-level `Firecrawl`
    wrapper raises ValueError("No API key provided") when constructed without a
    key, and a mocked constructor cannot show that. Construction is offline, so
    no request is made.
    """

    def setUp(self):
        self.mod = _load_script("firecrawl_research")

    def test_key_is_passed_when_set(self):
        with patch.dict(os.environ, {"FIRECRAWL_API_KEY": "fc-test"}, clear=False):
            client = self.mod._client()
        self.assertEqual(client.http_client.api_key, "fc-test")

    def test_keyless_construction_succeeds_and_warns(self):
        stderr = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stderr(stderr):
            client = self.mod._client()
        self.assertIsNone(client.http_client.api_key)
        self.assertIn("FIRECRAWL_API_KEY is not set", stderr.getvalue())

    def test_keyless_client_exposes_the_research_methods(self):
        with patch.dict(os.environ, {}, clear=True), redirect_stderr(io.StringIO()):
            client = self.mod._client()
        for name in ("search_papers", "inspect_paper", "read_paper", "related_papers", "search_github"):
            with self.subTest(method=name):
                self.assertTrue(callable(getattr(client, name, None)))

    def test_sdk_internal_retries_are_disabled(self):
        """This module owns retries; the SDK's own loop must not multiply them."""
        with patch.dict(os.environ, {"FIRECRAWL_API_KEY": "fc-test"}, clear=False):
            client = self.mod._client()
        self.assertEqual(client.http_client.max_retries, 1)


class NormalisationTests(unittest.TestCase):
    """The research endpoints return dicts; `search` returns a pydantic model."""

    def setUp(self):
        self.mod = _load_script("firecrawl_research")

    def test_plain_dict_passes_through(self):
        payload = {"success": True, "results": []}
        self.assertIs(self.mod._as_plain(payload), payload)

    def test_pydantic_like_object_is_dumped(self):
        model = SimpleNamespace(model_dump=lambda: {"web": [{"url": "https://example.org"}]})
        self.assertEqual(self.mod._as_plain(model), {"web": [{"url": "https://example.org"}]})


class SearchPapersTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load_script("firecrawl_research")

    def _run(self, argv):
        client = MagicMock()
        client.search_papers.return_value = {"success": True, "results": [_paper_hit()]}
        args = self.mod.build_parser().parse_args(argv)
        payload = args.func(args, client)
        return payload, client

    def test_filters_are_split_into_lists(self):
        _, client = self._run(
            [
                "search-papers", "molecular property prediction",
                "--categories", "cs.LG, q-bio.QM",
                "--authors", "Vaswani",
                "--from-date", "2023-01-01",
                "--to-date", "2025-12-31",
            ]
        )
        kwargs = client.search_papers.call_args.kwargs
        self.assertEqual(kwargs["categories"], ["cs.LG", "q-bio.QM"])
        self.assertEqual(kwargs["authors"], ["Vaswani"])
        # The SDK spells these from_date/to_date, not the REST from/to.
        self.assertEqual(kwargs["from_date"], "2023-01-01")
        self.assertEqual(kwargs["to_date"], "2025-12-31")

    def test_absent_filters_are_none_not_empty_lists(self):
        _, client = self._run(["search-papers", "query"])
        kwargs = client.search_papers.call_args.kwargs
        self.assertIsNone(kwargs["categories"])
        self.assertIsNone(kwargs["authors"])

    def test_limit_maps_to_k(self):
        _, client = self._run(["search-papers", "query", "--limit", "25"])
        self.assertEqual(client.search_papers.call_args.kwargs["k"], 25)


class ReadPaperTests(unittest.TestCase):
    """Empty passages is a quiet failure and must be surfaced."""

    def setUp(self):
        self.mod = _load_script("firecrawl_research")

    def _run(self, passages):
        client = MagicMock()
        client.read_paper.return_value = {
            "success": True,
            "paperId": "1",
            "query": "q",
            "passages": passages,
            "paper": {"title": "T"},
        }
        args = self.mod.build_parser().parse_args(
            ["read-paper", "pmid:34515826", "--question", "does it report X"]
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            payload = args.func(args, client)
        return payload, client, stderr.getvalue()

    def test_empty_passages_warns(self):
        payload, _, stderr = self._run([])
        self.assertEqual(payload["passages"], [])
        self.assertIn("No full-text passages indexed", stderr)
        self.assertIn("pmid:34515826", stderr)

    def test_populated_passages_do_not_warn(self):
        _, _, stderr = self._run([{"text": "...", "score": 0.03}])
        self.assertEqual(stderr, "")

    def test_question_and_limit_are_passed_positionally(self):
        _, client, _ = self._run([{"text": "x"}])
        call = client.read_paper.call_args
        self.assertEqual(call.args, ("pmid:34515826", "does it report X"))
        self.assertEqual(call.kwargs["k"], 4)


class RelatedPapersTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load_script("firecrawl_research")

    def test_mode_defaults_to_similar(self):
        client = MagicMock()
        client.related_papers.return_value = {"success": True, "results": []}
        args = self.mod.build_parser().parse_args(
            ["related-papers", "arxiv:1706.03762", "--intent", "efficient transformers"]
        )
        args.func(args, client)
        self.assertEqual(client.related_papers.call_args.kwargs["mode"], "similar")

    def test_invalid_mode_is_rejected(self):
        with self.assertRaises(SystemExit):
            self.mod.build_parser().parse_args(
                ["related-papers", "id", "--intent", "i", "--mode", "cited-by"]
            )


def _api_error(status, retry_after=None):
    """An exception shaped like the SDK's FirecrawlError subclasses.

    Those classes are not exported from the package root, so the script keys off
    the duck-typed `status_code` / `response` attributes instead of importing an
    internal module. The fake mirrors that shape.
    """
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    error = RuntimeError(f"rate limited ({status})")
    error.status_code = status
    error.response = SimpleNamespace(headers=headers)
    return error


class RetryTests(unittest.TestCase):
    """The SDK retries transport errors and 502 only; 408/429/5xx land here."""

    def setUp(self):
        self.mod = _load_script("firecrawl_research")

    def test_429_is_retried_then_succeeds(self):
        operation = MagicMock(side_effect=[_api_error(429), {"success": True}])
        with patch.object(self.mod.time, "sleep") as sleep:
            result = self.mod._call_with_retries(operation, "q")
        self.assertEqual(result, {"success": True})
        self.assertEqual(operation.call_count, 2)
        sleep.assert_called_once()

    def test_retry_after_seconds_header_is_honoured(self):
        operation = MagicMock(side_effect=[_api_error(429, "7"), {"ok": True}])
        with patch.object(self.mod.time, "sleep") as sleep:
            self.mod._call_with_retries(operation, "q")
        self.assertAlmostEqual(sleep.call_args.args[0], 7.0)

    def test_retry_after_is_capped(self):
        operation = MagicMock(side_effect=[_api_error(429, "99999"), {"ok": True}])
        with patch.object(self.mod.time, "sleep") as sleep:
            self.mod._call_with_retries(operation, "q")
        self.assertEqual(sleep.call_args.args[0], self.mod.MAX_BACKOFF_SECONDS)

    def test_unparseable_retry_after_falls_back_to_backoff(self):
        operation = MagicMock(side_effect=[_api_error(503, "not-a-date"), {"ok": True}])
        with patch.object(self.mod.time, "sleep") as sleep:
            self.mod._call_with_retries(operation, "q")
        self.assertEqual(sleep.call_args.args[0], self.mod.BACKOFF_BASE_SECONDS)

    def test_backoff_grows_exponentially(self):
        operation = MagicMock(side_effect=[_api_error(500), _api_error(500), {"ok": True}])
        with patch.object(self.mod.time, "sleep") as sleep:
            self.mod._call_with_retries(operation, "q")
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1.0, 2.0])

    def test_retry_budget_is_bounded(self):
        operation = MagicMock(side_effect=_api_error(429))
        with patch.object(self.mod.time, "sleep"):
            with self.assertRaises(RuntimeError):
                self.mod._call_with_retries(operation, "q")
        self.assertEqual(operation.call_count, self.mod.MAX_ATTEMPTS)

    def test_non_retryable_status_raises_immediately(self):
        operation = MagicMock(side_effect=_api_error(401))
        with patch.object(self.mod.time, "sleep") as sleep:
            with self.assertRaises(RuntimeError):
                self.mod._call_with_retries(operation, "q")
        self.assertEqual(operation.call_count, 1)
        sleep.assert_not_called()

    def test_transport_errors_are_retried(self):
        """The SDK's own loop is off, so this layer has to cover them."""
        boom = self.mod.requests.ConnectionError("connection reset")
        operation = MagicMock(side_effect=[boom, {"ok": True}])
        with patch.object(self.mod.time, "sleep"):
            self.mod._call_with_retries(operation, "q")
        self.assertEqual(operation.call_count, 2)

    def test_persistent_502_costs_exactly_max_attempts_requests(self):
        """Drives the real SDK request path, not a stand-in for it.

        The SDK retries 502 internally three times by default; layered under
        this loop that would be MAX_ATTEMPTS x 3 requests with stacked sleeps.
        `_client` disables the inner loop, so the real budget is MAX_ATTEMPTS.
        """
        response = MagicMock(status_code=502, headers={}, text="bad gateway")
        response.json.return_value = {"error": "Bad Gateway"}
        with patch.dict(os.environ, {"FIRECRAWL_API_KEY": "fc-test"}, clear=False):
            client = self.mod._client()
        # `self.mod.time` is the stdlib time module, so this one patch also
        # covers any sleep the SDK would have done internally.
        with patch.object(self.mod.requests, "get", return_value=response) as http_get, \
             patch.object(self.mod.time, "sleep") as sleep:
            with self.assertRaises(Exception):
                self.mod._call_with_retries(client.search_papers, "q", k=2)
        self.assertEqual(http_get.call_count, self.mod.MAX_ATTEMPTS)
        self.assertEqual(sleep.call_count, self.mod.MAX_ATTEMPTS - 1)

    def test_search_papers_goes_through_the_retry_wrapper(self):
        client = MagicMock()
        client.search_papers.side_effect = [_api_error(429), {"success": True, "results": []}]
        args = self.mod.build_parser().parse_args(["search-papers", "q"])
        with patch.object(self.mod.time, "sleep"):
            payload = args.func(args, client)
        self.assertEqual(payload, {"success": True, "results": []})
        self.assertEqual(client.search_papers.call_count, 2)


class MainTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load_script("firecrawl_research")

    def test_subcommand_is_required(self):
        with self.assertRaises(SystemExit):
            self.mod.build_parser().parse_args([])

    def test_output_file_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "papers.json"
            client = MagicMock()
            client.search_papers.return_value = {"success": True, "results": [_paper_hit()]}
            with patch.object(self.mod, "_client", return_value=client):
                rc = self.mod.main(["search-papers", "attention", "-o", str(out)])
            self.assertEqual(rc, 0)
            payload = json.loads(out.read_text())
            self.assertEqual(payload["results"][0]["primaryId"], "arxiv:1706.03762")

    def test_output_before_subcommand_is_rejected_not_silently_dropped(self):
        """Declaring -o on both parsers would reset it to None; it must error."""
        with self.assertRaises(SystemExit):
            self.mod.build_parser().parse_args(["-o", "out.json", "search-papers", "q"])

    def test_output_is_available_on_every_subcommand(self):
        parser = self.mod.build_parser()
        for argv in (
            ["search-papers", "q"],
            ["inspect-paper", "arxiv:1"],
            ["read-paper", "arxiv:1", "--question", "q"],
            ["related-papers", "arxiv:1", "--intent", "i"],
            ["search-github", "q"],
        ):
            with self.subTest(command=argv[0]):
                args = parser.parse_args([*argv, "-o", "out.json"])
                self.assertEqual(args.output, "out.json")

    def test_api_failure_exits_1_without_a_traceback(self):
        client = MagicMock()
        client.search_papers.side_effect = _api_error(401)
        stderr = io.StringIO()
        with patch.object(self.mod, "_client", return_value=client), redirect_stderr(stderr):
            rc = self.mod.main(["search-papers", "q"])
        self.assertEqual(rc, 1)
        self.assertIn("Firecrawl request failed (HTTP 401)", stderr.getvalue())


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

if __name__ == "__main__":
    unittest.main()
