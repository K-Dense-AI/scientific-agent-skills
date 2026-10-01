"""Regression tests for the Parallel-first research lookup skill."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "skills" / "research-lookup" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from manuscript_packet import (  # noqa: E402
    build_manuscript_packet,
    deduplicate_sources,
    save_packet,
)
from research_lookup import (  # noqa: E402
    DEFAULT_TARGET_REFERENCES,
    ResearchLookup,
    build_parser,
)

import skill_contract


def source(
    index: int,
    *,
    title: str | None = None,
    text: str | None = None,
    extracted: bool = False,
) -> dict:
    return {
        "title": title or f"Randomized controlled trial of intervention {index}",
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{1000000 + index}/",
        "publish_date": f"202{index % 6}-01-01",
        "excerpts": [
            text
            or (
                f"Authors: Author {index}. Journal: Evidence Journal. PMID: "
                f"{1000000 + index}. Randomized controlled trial. n={100 + index}. "
                "The study showed a 20% improvement (p<0.05). "
                "A limitation was the short follow-up."
            )
        ],
        "extracted": extracted,
    }


class RoutingTests(unittest.TestCase):
    @patch("research_lookup.shutil.which", return_value="/usr/local/bin/parallel-cli")
    def test_default_backend_is_search_and_parallel_alias_is_research(self, _which):
        default = ResearchLookup()
        legacy = ResearchLookup(force_backend="parallel")

        self.assertEqual(default._select_backend("general research"), "search")
        self.assertEqual(legacy._select_backend("deep research"), "research")

    @patch("research_lookup.shutil.which", return_value="/usr/local/bin/parallel-cli")
    @patch.dict("research_lookup.os.environ", {"PARALLEL_API_KEY": "test-key"})
    def test_chat_is_available_but_never_selected_by_default(self, _which):
        default = ResearchLookup()
        explicit = ResearchLookup(force_backend="chat", chat_model="core")

        self.assertEqual(default._select_backend("synthesize evidence"), "search")
        self.assertEqual(explicit._select_backend("synthesize evidence"), "chat")

    @patch("research_lookup.shutil.which", return_value="/usr/local/bin/parallel-cli")
    @patch.dict("research_lookup.os.environ", {"PARALLEL_API_KEY": "test-key"})
    def test_explicit_chat_preserves_content_basis_and_citations(self, _which):
        lookup = ResearchLookup(force_backend="chat", chat_model="core")

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    "Evidence synthesis with DOI: 10.1234/example."
                                )
                            }
                        }
                    ],
                    "basis": [
                        {
                            "citations": [
                                {
                                    "title": "Basis source",
                                    "url": "https://example.org/source",
                                }
                            ]
                        }
                    ],
                    "usage": {"total_tokens": 100},
                }

        with patch("requests.post", return_value=FakeResponse()) as post:
            result = lookup.lookup("synthesize the evidence")

        self.assertTrue(result["success"])
        self.assertEqual(result["backend"], "chat")
        self.assertEqual(result["model"], "parallel-chat/core")
        self.assertEqual(result["sources"][0]["title"], "Basis source")
        self.assertTrue(
            any(
                citation["url"] == "https://doi.org/10.1234/example"
                for citation in result["citations"]
            )
        )
        request = post.call_args
        self.assertEqual(
            request.args[0], "https://api.parallel.ai/v1beta/chat/completions"
        )
        self.assertEqual(request.kwargs["headers"]["x-api-key"], "test-key")
        self.assertEqual(request.kwargs["json"]["model"], "core")
        self.assertFalse(request.kwargs["json"]["stream"])

    @patch("research_lookup.shutil.which", return_value="/usr/local/bin/parallel-cli")
    def test_parser_and_class_default_to_sixty_references(self, _which):
        args = build_parser().parse_args(
            ["topic", "--academic", "--force-backend", "chat"]
        )
        lookup = ResearchLookup(academic=True)

        self.assertEqual(DEFAULT_TARGET_REFERENCES, 60)
        self.assertEqual(args.target_references, 60)
        self.assertEqual(args.force_backend, "chat")
        self.assertEqual(args.chat_model, "core")
        self.assertEqual(lookup.target_references, 60)
        self.assertEqual(lookup.extract_limit, 60)

    @patch("research_lookup.shutil.which", return_value="/usr/local/bin/parallel-cli")
    def test_nonacademic_lookup_uses_one_search_without_extract(self, _which):
        lookup = ResearchLookup(academic=False, max_results=2)
        calls: list[list[str]] = []

        def fake_cli(args, *, timeout=None):
            del timeout
            calls.append(args)
            return {
                "search_id": "search_general",
                "session_id": "session_general",
                "status": "ok",
                "results": [source(1), source(2)],
                "usage": [{"name": "sku_search", "count": 1}],
            }

        lookup._run_parallel_cli = fake_cli  # type: ignore[method-assign]
        result = lookup.lookup("latest official technical guidance")

        self.assertTrue(result["success"])
        self.assertEqual(result["backend"], "search")
        self.assertFalse(result["academic"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "search")
        self.assertEqual(result["usage"], [{"name": "sku_search", "count": 1}])

    @patch("research_lookup.shutil.which", return_value="/usr/local/bin/parallel-cli")
    def test_academic_lookup_runs_facets_and_batched_extract(self, _which):
        lookup = ResearchLookup(
            academic=True,
            target_references=3,
            max_results=2,
            extract_limit=3,
            extract_batch_size=2,
        )
        search_count = 0
        extract_count = 0

        def fake_cli(args, *, timeout=None):
            nonlocal search_count, extract_count
            del timeout
            if args[0] == "search":
                search_count += 1
                start = search_count * 10
                return {
                    "search_id": f"search_{search_count}",
                    "session_id": "session_academic",
                    "status": "ok",
                    "results": [source(start), source(start + 1)],
                    "usage": [{"name": "sku_search", "count": 1}],
                }
            self.assertEqual(args[0], "extract")
            extract_count += 1
            urls = [
                value
                for value in args[1 : args.index("--objective")]
                if value.startswith("https://")
            ]
            return {
                "extract_id": f"extract_{extract_count}",
                "session_id": "session_academic",
                "status": "ok",
                "results": [
                    {
                        **source(int(url.rstrip("/").split("/")[-1]) - 1000000),
                        "url": url,
                    }
                    for url in urls
                ],
                "errors": [],
                "usage": [{"name": "sku_extract_excerpts", "count": len(urls)}],
            }

        lookup._run_parallel_cli = fake_cli  # type: ignore[method-assign]
        result = lookup.lookup("find papers for a manuscript on intervention")

        self.assertTrue(result["success"])
        self.assertTrue(result["academic"])
        self.assertEqual(search_count, 5)
        self.assertEqual(extract_count, 2)
        self.assertEqual(result["packet"]["target_references"], 3)
        self.assertGreaterEqual(len(result["packet"]["references"]), 3)
        self.assertGreaterEqual(
            result["packet"]["coverage"]["verified_references"],
            3,
        )
        self.assertEqual(
            result["packet"]["coverage"]["verification_mix"]["extracted"],
            3,
        )
        self.assertIn("search_ledger", result)
        self.assertTrue(
            any(entry["capability"] == "extract" for entry in result["search_ledger"])
        )

    @patch("research_lookup.shutil.which", return_value="/usr/local/bin/parallel-cli")
    @patch.dict("research_lookup.os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_perplexity_failure_fallback_is_opt_in(self, _which):
        lookup = ResearchLookup(allow_perplexity_fallback=True)
        lookup._parallel_search = lambda query: (_ for _ in ()).throw(  # type: ignore[method-assign]
            RuntimeError("search unavailable")
        )
        lookup._perplexity_lookup = lambda query: {  # type: ignore[method-assign]
            "success": True,
            "query": query,
            "response": "fallback",
            "citations": [],
            "sources": [],
            "timestamp": "now",
            "backend": "perplexity",
            "model": "perplexity/sonar-pro-search",
        }

        result = lookup.lookup("topic")

        self.assertTrue(result["success"])
        self.assertEqual(result["fallback_from"], "search")
        self.assertIn("search unavailable", result["fallback_reason"])

    @patch("research_lookup.shutil.which", return_value=None)
    @patch.dict("research_lookup.os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=True)
    def test_key_alone_never_switches_to_perplexity_when_cli_is_missing(self, _which):
        lookup = ResearchLookup()
        lookup._run_parallel_cli = Mock(side_effect=RuntimeError("CLI missing"))
        lookup._perplexity_lookup = Mock()

        result = lookup.lookup("topic")

        self.assertFalse(result["success"])
        self.assertEqual(result["backend"], "search")
        lookup._perplexity_lookup.assert_not_called()

    @patch("research_lookup.shutil.which", return_value=None)
    @patch.dict("research_lookup.os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=True)
    def test_opt_in_fallback_still_handles_missing_cli(self, _which):
        lookup = ResearchLookup(allow_perplexity_fallback=True)
        lookup._run_parallel_cli = Mock(side_effect=RuntimeError("CLI missing"))
        lookup._perplexity_lookup = Mock(return_value={"success": True, "backend": "perplexity"})

        result = lookup.lookup("topic")

        self.assertTrue(result["success"])
        self.assertEqual(result["fallback_from"], "search")
        lookup._perplexity_lookup.assert_called_once_with("topic")

    @patch("research_lookup.shutil.which", return_value="parallel-cli")
    def test_mixed_extract_results_preserve_errors_session_and_evidence(self, _which):
        lookup = ResearchLookup(extract_limit=3)
        candidates = [source(index) for index in range(3)]
        lookup._run_parallel_cli = Mock(return_value={
            "extract_id": "extract_mixed",
            "session_id": "session_shared",
            "results": [
                {"url": candidates[0]["url"], "excerpts": ["Retrieved evidence showed a different effect."]},
                {"url": candidates[2]["url"], "excerpts": []},
            ],
            "errors": [{"url": candidates[1]["url"], "error_type": "FETCH_ERROR", "http_status_code": 403}],
            "warnings": [{"type": "warning", "message": "Partial retrieval"}],
        })
        ledger = []

        records, _ = lookup._extract_sources(candidates, ledger, "session_shared")
        packet = build_manuscript_packet(query="topic", sources=records, search_ledger=ledger, target_references=3)

        self.assertEqual(packet["coverage"]["verified_references"], 1)
        self.assertEqual(packet["coverage"]["shortfall"], 2)
        self.assertEqual(ledger[0]["status"], "partial")
        self.assertEqual(len(ledger[0]["unresolved_urls"]), 2)
        self.assertEqual(ledger[0]["errors"][0]["http_status_code"], 403)
        self.assertTrue(ledger[0]["warnings"])
        args = lookup._run_parallel_cli.call_args.args[0]
        self.assertEqual(args[args.index("--session-id") + 1], "session_shared")
        extracted = next(ref for ref in packet["references"] if ref["verification_status"] == "extracted")
        self.assertEqual(extracted["supporting_excerpts"], ["Retrieved evidence showed a different effect."])
        self.assertNotIn("20% improvement", " ".join(extracted["key_findings"]))

    @patch("research_lookup.shutil.which", return_value="parallel-cli")
    def test_research_reads_saved_markdown_and_preserves_basis(self, _which):
        lookup = ResearchLookup(force_backend="research", previous_interaction_id="trun_previous")

        def fake_cli(args, *, timeout=None):
            del timeout
            output_base = Path(args[args.index("-o") + 1])
            output_base.with_suffix(".md").write_text("A short research report.", encoding="utf-8")
            self.assertEqual(args[args.index("--previous-interaction-id") + 1], "trun_previous")
            return {
                "run_id": "trun_new", "interaction_id": "trun_new", "status": "completed",
                "output": {"type": "text", "content_file": "report.md", "basis": [
                    {"citations": [{"url": "https://example.org/study", "title": "Study"}]}
                ]},
            }

        lookup._run_parallel_cli = fake_cli
        result = lookup.lookup("topic")

        self.assertTrue(result["success"])
        self.assertEqual(result["response"], "A short research report.")
        self.assertEqual(result["run_id"], "trun_new")
        self.assertEqual(result["sources"][0]["title"], "Study")

    @patch("research_lookup.shutil.which", return_value="parallel-cli")
    def test_research_rejects_noncompleted_empty_and_oversized_requests(self, _which):
        lookup = ResearchLookup(force_backend="research")
        for payload in (
            {"status": "failed", "run_id": "trun_bad", "output": {}},
            {"status": "completed", "output": {"basis": [{"reasoning": "Not a report. " * 20}]}},
        ):
            with self.subTest(payload=payload):
                lookup._run_parallel_cli = Mock(return_value=payload)
                self.assertFalse(lookup.lookup("topic")["success"])
        lookup._run_parallel_cli = Mock()
        result = lookup.lookup("x" * 15000)
        self.assertIn("15,000", result["error"])
        lookup._run_parallel_cli.assert_not_called()
        self.assertEqual(ResearchLookup._find_report_text({"output": {"content": "Short."}}), "Short.")

    @patch("research_lookup.shutil.which", return_value="parallel-cli")
    @patch.dict("research_lookup.os.environ", {"OPENROUTER_API_KEY": "test-key"}, clear=True)
    def test_openrouter_request_and_standard_annotations(self, _which):
        lookup = ResearchLookup(force_backend="perplexity")
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": "A cited finding.", "annotations": [
                {"type": "url_citation", "url_citation": {
                    "url": "https://example.org/study", "title": "Study", "content": "Source excerpt",
                    "start_index": 0, "end_index": 15,
                }}
            ]}}],
            "citations": ["https://example.org/study"],
            "usage": {"total_tokens": 30},
        }
        with patch("requests.post", return_value=response) as post:
            result = lookup.lookup("topic")

        self.assertTrue(result["success"])
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["sources"][0]["snippet"], "Source excerpt")
        self.assertEqual(result["raw_response"], response.json.return_value)
        self.assertEqual(post.call_args.args[0], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer test-key")
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["model"], "perplexity/sonar-pro-search")
        self.assertEqual(body["web_search_options"], {"search_context_size": "high"})
        self.assertNotIn("search_mode", body)
        self.assertNotIn("search_context_size", body)

    @patch("research_lookup.shutil.which", return_value="parallel-cli")
    def test_cli_response_errors_and_nonobjects_fail(self, _which):
        lookup = ResearchLookup()
        for payload in ([], {"type": "error", "error": {"message": "unavailable"}}):
            with self.subTest(payload=payload), patch("research_lookup.subprocess.run", return_value=
                    subprocess.CompletedProcess([], 0, stdout=json.dumps(payload), stderr="")):
                with self.assertRaises(RuntimeError):
                    lookup._run_parallel_cli(["search", "topic", "--json"])

    @patch("research_lookup.shutil.which", return_value="parallel-cli")
    def test_current_modes_and_extract_batch_limit(self, _which):
        self.assertEqual(build_parser().parse_args(["topic", "--search-mode", "fast"]).search_mode, "fast")
        self.assertEqual(ResearchLookup(search_mode="fast").search_mode, "fast")
        for size in (0, 21):
            with self.subTest(size=size), self.assertRaises(ValueError):
                ResearchLookup(extract_batch_size=size)


class PacketTests(unittest.TestCase):
    def test_deduplication_merges_doi_url_and_title_records(self):
        first = {
            "title": "A Definitive Study",
            "url": "https://doi.org/10.1234/example?utm_source=test",
            "excerpts": ["DOI: 10.1234/example"],
            "facets": ["reviews"],
        }
        duplicate = {
            "title": "A definitive study",
            "url": "https://doi.org/10.1234/example",
            "excerpts": ["Additional evidence."],
            "facets": ["seminal"],
            "extracted": True,
        }

        merged = deduplicate_sources([first, duplicate])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["doi"], "10.1234/example")
        self.assertEqual(merged[0]["facets"], ["reviews", "seminal"])
        self.assertTrue(merged[0]["extracted"])
        self.assertEqual(len(merged[0]["excerpts"]), 2)

    def test_packet_has_manuscript_artifacts_and_never_pads_shortfall(self):
        sources = [
            source(1, extracted=True),
            source(
                2,
                text=(
                    "Authors: Researcher Two. Journal: Evidence Journal. "
                    "PMID: 1000002. Systematic review. The evidence was inconsistent "
                    "and showed no significant effect. Limitation: high heterogeneity."
                ),
                extracted=True,
            ),
        ]

        packet = build_manuscript_packet(
            query="manuscript evidence",
            sources=sources,
            search_ledger=[{"capability": "search", "status": "ok"}],
            target_references=60,
            manuscript_context={"study_type": "cohort"},
        )

        self.assertEqual(len(packet["references"]), 2)
        self.assertEqual(packet["coverage"]["requested_references"], 60)
        self.assertEqual(packet["coverage"]["verified_references"], 2)
        self.assertEqual(packet["coverage"]["shortfall"], 58)
        self.assertTrue(packet["claim_source_map"])
        self.assertIn("introduction", packet["section_briefs"])
        self.assertIn("methods-rationale", packet["section_briefs"])
        self.assertIn("discussion", packet["section_briefs"])
        self.assertTrue(packet["synthesis"]["conflicting_evidence"])
        self.assertTrue(any("not padded" in item for item in packet["warnings"]))

    def test_retracted_reference_is_marked_for_exclusion(self):
        packet = build_manuscript_packet(
            query="topic",
            sources=[
                source(
                    1,
                    text=(
                        "Retraction notice. This randomized controlled trial was "
                        "retracted because the findings were unreliable."
                    ),
                    extracted=True,
                )
            ],
            search_ledger=[],
            target_references=1,
        )

        reference = packet["references"][0]
        self.assertTrue(reference["retracted"])
        self.assertEqual(reference["evidence_quality"], "exclude")
        self.assertEqual(packet["coverage"]["verified_references"], 0)
        self.assertEqual(packet["claim_source_map"], [])
        self.assertEqual(packet["synthesis"]["consensus_evidence"], [])
        self.assertTrue(all(not brief["reference_ids"] for brief in packet["section_briefs"].values()))

    def test_identifiers_and_empty_extracts_do_not_count_as_verification(self):
        packet = build_manuscript_packet(
            query="topic", sources=[
                source(1),
                {"url": "https://doi.org/10.1234/example", "title": "A DOI is only a candidate identifier"},
                {"url": "https://example.org/empty", "title": "Empty extraction", "extracted": True, "excerpts": []},
            ], search_ledger=[], target_references=3,
        )
        self.assertEqual(packet["coverage"]["verified_references"], 0)
        self.assertEqual(packet["coverage"]["shortfall"], 3)
        self.assertEqual(packet["coverage"]["verification_mix"], {"search-only": 3})
        self.assertTrue(all(claim["status"] == "unverified-source" for claim in packet["claim_source_map"]))

    def test_save_packet_writes_all_expected_artifacts(self):
        packet = build_manuscript_packet(
            query="topic",
            sources=[source(1, extracted=True)],
            search_ledger=[{"capability": "search", "status": "ok"}],
            target_references=1,
        )

        with tempfile.TemporaryDirectory() as directory:
            artifacts = save_packet(packet, directory)

            self.assertEqual(
                set(artifacts),
                {
                    "packet_json",
                    "packet_markdown",
                    "references_json",
                    "references_bib",
                    "evidence_matrix",
                    "claim_source_map",
                    "synthesis",
                    "section_briefs",
                    "coverage",
                    "search_ledger",
                },
            )
            self.assertTrue(all(Path(path).exists() for path in artifacts.values()))
            self.assertIn(
                "Manuscript Research Packet",
                Path(artifacts["packet_markdown"]).read_text(encoding="utf-8"),
            )

    def test_existing_citation_extraction_remains_available(self):
        citations = ResearchLookup._extract_citations_from_text(
            "See DOI: 10.1234/Example and https://pubmed.ncbi.nlm.nih.gov/12345678/."
        )
        urls = {citation["url"] for citation in citations}

        self.assertIn("https://doi.org/10.1234/example", urls)
        self.assertIn("https://pubmed.ncbi.nlm.nih.gov/12345678", urls)


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SCRIPT_DIR.parent)

if __name__ == "__main__":
    unittest.main()
