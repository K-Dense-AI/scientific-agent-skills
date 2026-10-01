"""Offline tests for the paper-lookup scripts.

No network. Every fixture is a trimmed copy of a real response captured on
2026-07-27, because the behavior under test *is* the shape of these payloads --
a synthetic JATS document with a tidy `<body>` would not exercise the case this
skill exists to catch.

One exception, flagged rather than hidden: `arxiv_error.xml` is reconstructed
from a verified live response rather than saved from one. Its `totalResults`, its
`<title>Error</title>`, and its `start must be an integer` summary were all
observed from the real API, but arXiv penalizes repeated malformed requests
harder than valid ones (see references/arxiv.md) and stayed throttled for the
rest of the session, so the capture could not be repeated to save the bytes.

The three exit codes are the point of the suite:

    jats_to_text.py  -> 2 when a document has no <body>
    arxiv_atom.py    -> 3 on arXiv's HTTP-200 error feed
    paginate.py      -> 4 when a walk ends short of the reported total

Each is a failure the upstream API reports as success.
"""

from __future__ import annotations

import json
import io
import subprocess
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "paper-lookup"
SCRIPTS = SKILL_ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import skill_contract  # noqa: E402

import _common  # noqa: E402
import arxiv_atom  # noqa: E402
import jats_to_text  # noqa: E402
import openalex_abstract  # noqa: E402
import paginate  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def run_script(name: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=SCRIPTS,
    )


def fixture(name: str) -> str:
    return str(FIXTURES / name)


class CommonTests(unittest.TestCase):
    def test_collapse_ws_flattens_arxiv_hard_wrapping(self) -> None:
        wrapped = "The dominant sequence\n  transduction models\tare based on"
        self.assertEqual(
            _common.collapse_ws(wrapped), "The dominant sequence transduction models are based on"
        )

    def test_collapse_ws_handles_none(self) -> None:
        self.assertEqual(_common.collapse_ws(None), "")

    def test_strip_control_keeps_tab_and_newline(self) -> None:
        self.assertEqual(_common.strip_control("a\x00b\tc\nd\x07"), "ab\tc\nd")

    def test_read_input_rejects_oversized_file(self) -> None:
        with self.assertRaises(_common.InputError):
            _common.read_input(fixture("openalex_work.json"), max_bytes=10)

    def test_read_input_rejects_missing_file(self) -> None:
        with self.assertRaises(_common.InputError):
            _common.read_input(str(FIXTURES / "does-not-exist.json"))

    def test_load_json_attributes_the_parse_failure_to_the_source(self) -> None:
        with self.assertRaises(_common.InputError) as caught:
            _common.load_json(fixture("jats_no_body.xml"))
        self.assertIn("jats_no_body.xml", str(caught.exception))


class ReconciliationTests(unittest.TestCase):
    """The three outcomes must stay distinguishable.

    Collapsing "the caller set a bound" into "records are missing" is what makes
    a bounded search look broken; collapsing it the other way is what makes a
    broken search look bounded.
    """

    def test_complete_walk(self) -> None:
        record = _common.Reconciliation(expected=360, retrieved=360, pages=12)
        self.assertTrue(record.complete)
        self.assertTrue(record.ok)
        self.assertNotIn("shortfall", record.as_dict())

    def test_bound_is_explained_not_a_failure(self) -> None:
        record = _common.Reconciliation(
            expected=697030, retrieved=100, pages=2, stopped_at_limit=True
        )
        self.assertFalse(record.complete)
        self.assertTrue(record.ok)
        summary = record.as_dict()
        self.assertEqual(summary["shortfall"], 696930)
        self.assertIn("max-records", summary["shortfall_reason"])

    def test_unexplained_shortfall_is_not_ok(self) -> None:
        record = _common.Reconciliation(expected=360, retrieved=120, pages=4)
        self.assertFalse(record.ok)
        self.assertIn("UNEXPLAINED", record.as_dict()["shortfall_reason"])

    def test_absent_total_is_a_documented_state(self) -> None:
        record = _common.Reconciliation(expected=None, retrieved=5, pages=1)
        self.assertTrue(record.ok)
        self.assertIn("expected_total_note", record.as_dict())


class RedactionTests(unittest.TestCase):
    """Credentials must never reach the provenance output.

    OpenAlex and Crossref authenticate by query string, so the URL that was
    actually fetched carries the secret -- and provenance is printed.
    """

    def test_api_key_value_is_replaced_but_the_parameter_survives(self) -> None:
        redacted = _common.redact_url("https://api.openalex.org/works?cursor=*&api_key=SECRET")
        self.assertNotIn("SECRET", redacted)
        self.assertIn("api_key=REDACTED", redacted)
        self.assertIn("cursor=", redacted)

    def test_contact_details_are_redacted_too(self) -> None:
        for param in ("mailto", "email", "tool"):
            with self.subTest(param=param):
                redacted = _common.redact_url(f"https://api.crossref.org/works?{param}=me@x.com")
                self.assertNotIn("me@x.com", redacted)

    def test_redaction_is_case_insensitive_on_the_parameter_name(self) -> None:
        self.assertNotIn("SECRET", _common.redact_url("https://x.test/?API_KEY=SECRET"))

    def test_urls_without_a_query_are_untouched(self) -> None:
        url = "https://api.biorxiv.org/details/biorxiv/2024-01-01/2024-01-03/0/json"
        self.assertEqual(_common.redact_url(url), url)

    def test_dry_run_output_carries_no_key(self) -> None:
        import os

        environment = {**os.environ, "OPENALEX_API_KEY": "SECRET_TEST_KEY"}
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "paginate.py"),
                "--api",
                "openalex",
                "--query",
                "search=crispr",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=SCRIPTS,
            env=environment,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("SECRET_TEST_KEY", result.stdout)
        self.assertIn("api_key=REDACTED", result.stdout)


class JatsTests(unittest.TestCase):
    def test_full_text_article_yields_sections(self) -> None:
        result = run_script("jats_to_text.py", fixture("jats_with_body.xml"))
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["full_text_available"])
        self.assertEqual(payload["metadata"]["pmcid"], "PMC7029759")
        self.assertEqual(payload["metadata"]["pmid"], "32117569")
        self.assertGreater(payload["section_count"], 0)
        self.assertGreater(payload["word_count"], 0)

    def test_first_article_id_wins_over_nested_sub_article_doi(self) -> None:
        """F1000Research-style peer-review sub-articles carry their own DOIs."""
        result = run_script("jats_to_text.py", fixture("jats_with_body.xml"))
        payload = json.loads(result.stdout)
        self.assertEqual(payload["metadata"]["doi"], "10.12688/f1000research.22211.2")

    def test_missing_body_exits_2_and_surfaces_the_xml_comment(self) -> None:
        """The whole reason this script exists: eFetch returns 200 for this."""
        result = run_script("jats_to_text.py", fixture("jats_no_body.xml"))
        self.assertEqual(result.returncode, 2, result.stdout)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["full_text_available"])
        self.assertIn("does not allow downloading", payload["reason"])
        # The reason exists only as an XML comment, which ElementTree discards.
        self.assertTrue(payload["xml_comments"])
        self.assertIn("Europe PMC", payload["guidance"])

    def test_metadata_still_emitted_when_body_is_missing(self) -> None:
        result = run_script("jats_to_text.py", fixture("jats_no_body.xml"))
        payload = json.loads(result.stdout)
        self.assertEqual(payload["metadata"]["journal"], "British Medical Journal (Clinical research ed.)")

    def test_allow_metadata_only_opts_out_of_the_refusal(self) -> None:
        result = run_script("jats_to_text.py", fixture("jats_no_body.xml"), "--allow-metadata-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["full_text_available"])

    def test_europepmc_bare_article_wrapper_is_accepted(self) -> None:
        """eFetch wraps in <pmc-articleset>; Europe PMC returns a bare <article>."""
        result = run_script("jats_to_text.py", fixture("jats_europepmc.xml"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["full_text_available"])

    def test_section_filter_matches_case_insensitively(self) -> None:
        result = run_script("jats_to_text.py", fixture("jats_with_body.xml"), "--sections", "methods")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["section_count"], 1)

    def test_unmatched_section_filter_lists_what_is_available(self) -> None:
        result = run_script("jats_to_text.py", fixture("jats_with_body.xml"), "--sections", "nope")
        self.assertEqual(result.returncode, 1)
        self.assertIn("available:", result.stderr)

    def test_non_jats_xml_is_rejected_with_a_useful_message(self) -> None:
        result = run_script("jats_to_text.py", fixture("not_jats.xml"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("no <article> element", result.stderr)

    def test_xref_text_is_dropped_but_the_sentence_survives(self) -> None:
        """Citation markers must not land mid-sentence, and the tail must stay."""
        body = jats_to_text.parse(
            "<body><sec><title>Results</title>"
            "<p>Growth increased<xref ref-type=\"bibr\">12</xref> after treatment.</p>"
            "</sec></body>"
        )
        section = jats_to_text.collect_sections(body)[0]
        self.assertEqual(section["text"], "Results Growth increased after treatment.")


class ArxivTests(unittest.TestCase):
    def test_entry_is_parsed_with_version_split(self) -> None:
        result = run_script("arxiv_atom.py", fixture("arxiv_feed.xml"))
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        entry = payload["entries"][0]
        self.assertEqual(entry["arxiv_id"], "1706.03762")
        self.assertEqual(entry["arxiv_id_versioned"], "1706.03762v7")
        self.assertEqual(entry["version"], "7")

    def test_pdf_link_is_selected_by_rel_not_position(self) -> None:
        """The feed's own <link> precedes the entries and must not be picked up."""
        result = run_script("arxiv_atom.py", fixture("arxiv_feed.xml"))
        entry = json.loads(result.stdout)["entries"][0]
        self.assertEqual(entry["pdf_url"], "https://arxiv.org/pdf/1706.03762v7")
        self.assertEqual(entry["abstract_url"], "https://arxiv.org/abs/1706.03762v7")
        self.assertNotIn("api/query", entry["pdf_url"])

    def test_hard_wrapped_title_and_abstract_are_collapsed(self) -> None:
        result = run_script("arxiv_atom.py", fixture("arxiv_feed.xml"))
        entry = json.loads(result.stdout)["entries"][0]
        self.assertEqual(entry["title"], "Attention Is All You Need")
        self.assertNotIn("\n", entry["abstract"])

    def test_absent_arxiv_doi_is_none_not_invented(self) -> None:
        result = run_script("arxiv_atom.py", fixture("arxiv_feed.xml"))
        entry = json.loads(result.stdout)["entries"][0]
        self.assertIsNone(entry["doi"])

    def test_error_feed_exits_3(self) -> None:
        """arXiv sends this with HTTP 200 and totalResults 1."""
        result = run_script("arxiv_atom.py", fixture("arxiv_error.xml"))
        self.assertEqual(result.returncode, 3, result.stdout)
        self.assertIn("start must be an integer", result.stderr)

    def test_rate_limited_plain_text_body_exits_5(self) -> None:
        """arXiv answers a throttled caller with 14 bytes of plain text, not XML."""
        result = run_script("arxiv_atom.py", fixture("arxiv_rate_limited.txt"))
        self.assertEqual(result.returncode, 5, result.stdout)
        self.assertIn("throttling", result.stderr)
        self.assertIn("three seconds", result.stderr)

    def test_non_xml_body_reports_what_it_actually_got(self) -> None:
        result = run_script("arxiv_atom.py", fixture("openalex_work.json"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("first 100 bytes", result.stderr)

    def test_empty_feed_is_reported_as_a_genuine_no_match(self) -> None:
        result = run_script("arxiv_atom.py", fixture("arxiv_empty.xml"))
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["total_results"], 0)
        self.assertEqual(payload["returned"], 0)
        self.assertIn("not found in arXiv", payload["note"])

    def test_query_as_executed_is_reported(self) -> None:
        """An unknown field prefix is silently rewritten to `all:` upstream."""
        result = run_script("arxiv_atom.py", fixture("arxiv_rewritten_query.xml"))
        payload = json.loads(result.stdout)
        self.assertIn("all:badfield:xyz", payload["query_as_executed"])

    def test_ids_only_strips_versions(self) -> None:
        result = run_script("arxiv_atom.py", fixture("arxiv_feed.xml"), "--ids-only")
        self.assertEqual(result.stdout.strip(), "1706.03762")

    def test_split_version_leaves_unversioned_ids_alone(self) -> None:
        self.assertEqual(arxiv_atom.split_version("2103.15348"), ("2103.15348", None))
        self.assertEqual(arxiv_atom.split_version("2103.15348v12"), ("2103.15348", "12"))
        # Old-style IDs contain letters and a slash but no version.
        self.assertEqual(arxiv_atom.split_version("hep-th/9901001"), ("hep-th/9901001", None))

    def test_id_from_url_is_scheme_agnostic(self) -> None:
        self.assertEqual(arxiv_atom.id_from_url("http://arxiv.org/abs/1706.03762v7"), "1706.03762v7")
        self.assertEqual(arxiv_atom.id_from_url("https://arxiv.org/abs/1706.03762v7"), "1706.03762v7")


class OpenAlexAbstractTests(unittest.TestCase):
    def test_abstract_is_reconstructed_in_position_order(self) -> None:
        text, anomalies = openalex_abstract.reconstruct(
            {"Despite": [0], "growing": [1], "interest": [2], "in": [3], "OA": [4]}
        )
        self.assertEqual(text, "Despite growing interest in OA")
        self.assertEqual(anomalies, [])

    def test_duplicate_positions_keep_both_tokens(self) -> None:
        """The naive {position: word} inversion silently drops one of these."""
        text, anomalies = openalex_abstract.reconstruct({"alpha": [0], "beta": [0], "gamma": [1]})
        self.assertIn("alpha", text)
        self.assertIn("beta", text)
        self.assertIn("gamma", text)
        self.assertTrue(any("more than one token" in note for note in anomalies))

    def test_gaps_in_the_index_are_reported(self) -> None:
        _, anomalies = openalex_abstract.reconstruct({"first": [0], "last": [5]})
        self.assertTrue(any("absent from the index" in note for note in anomalies))

    def test_non_integer_positions_are_reported_not_crashed_on(self) -> None:
        text, anomalies = openalex_abstract.reconstruct({"word": ["x"], "real": [0]})
        self.assertEqual(text, "real")
        self.assertTrue(any("non-integer position" in note for note in anomalies))

    def test_empty_index_yields_empty_text(self) -> None:
        self.assertEqual(openalex_abstract.reconstruct({}), ("", []))

    def test_single_work_payload(self) -> None:
        result = run_script("openalex_abstract.py", fixture("openalex_work.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["with_abstract"], 1)
        self.assertIn("Open Access", payload["works"][0]["abstract"])

    def test_list_response_payload(self) -> None:
        result = run_script("openalex_abstract.py", fixture("openalex_list.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["count"], 2)

    def test_missing_index_distinguishes_no_abstract_from_select_exclusion(self) -> None:
        result = run_script("openalex_abstract.py", fixture("openalex_no_abstract.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        work = json.loads(result.stdout)["works"][0]
        self.assertIsNone(work["abstract"])
        self.assertIn("`select=`", work["abstract_warnings"][0])

    def test_text_only_fails_loudly_when_nothing_reconstructs(self) -> None:
        result = run_script("openalex_abstract.py", fixture("openalex_no_abstract.json"), "--text-only")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no abstracts", result.stderr)

    def test_works_from_rejects_a_bare_scalar(self) -> None:
        with self.assertRaises(_common.InputError):
            openalex_abstract.works_from("not a work")


class PaginateAdapterTests(unittest.TestCase):
    """Adapter unit tests. The network walk is covered by manual verification;
    what matters here is the arithmetic that made the walk wrong before."""

    def test_biorxiv_steps_by_the_reported_count_not_100(self) -> None:
        payload = {
            "messages": [{"status": "ok", "cursor": 0, "count": 30, "total": "360"}],
            "collection": [{"doi": f"10.1101/x{i}"} for i in range(30)],
        }
        page = paginate._rxiv_parse(payload, 0)
        self.assertEqual(page.total, 360)
        self.assertEqual(page.next_state, 30, "stepping by 100 would skip records 30-99")
        self.assertEqual(len(page.records), 30)

    def test_biorxiv_pubs_steps_by_100(self) -> None:
        payload = {
            "messages": [{"status": "ok", "cursor": 0, "count": 100, "total": "124"}],
            "collection": [{"preprint_doi": f"10.1101/x{i}"} for i in range(100)],
        }
        self.assertEqual(paginate._rxiv_parse(payload, 0).next_state, 100)

    def test_biorxiv_stops_when_the_next_offset_reaches_total(self) -> None:
        payload = {
            "messages": [{"status": "ok", "cursor": 330, "count": 30, "total": "360"}],
            "collection": [{"doi": f"10.1101/x{i}"} for i in range(30)],
        }
        self.assertIsNone(paginate._rxiv_parse(payload, 330).next_state)

    def test_biorxiv_reports_the_count_mismatch_it_falls_back_from(self) -> None:
        payload = {
            "messages": [{"status": "ok", "cursor": 0, "count": 30, "total": "360"}],
            "collection": [{"doi": "10.1101/x"}],
        }
        page = paginate._rxiv_parse(payload, 0)
        self.assertEqual(page.next_state, 1)
        self.assertTrue(any("but returned" in note for note in page.notes or []))

    def test_biorxiv_no_articles_found_is_surfaced(self) -> None:
        """HTTP 200 with an empty collection, indistinguishable without status."""
        page = paginate._rxiv_parse(
            {"messages": [{"status": "no articles found"}], "collection": []}, 0
        )
        self.assertEqual(page.records, [])
        self.assertIsNone(page.next_state)
        self.assertTrue(any("no articles found" in note for note in page.notes or []))

    def test_biorxiv_endpoint_without_counts_reports_no_total(self) -> None:
        """DOI and N-most-recent lookups omit count/total entirely."""
        page = paginate._rxiv_parse(
            {"messages": [{"status": "ok", "category": "all"}], "collection": [{"doi": "10.1101/x"}]},
            0,
        )
        self.assertIsNone(page.total)
        self.assertIsNone(page.next_state)

    def test_biorxiv_url_selects_details_or_pubs(self) -> None:
        build = paginate._rxiv_url("biorxiv")
        self.assertIn("/details/biorxiv/2024-01-01/2024-01-03/0/json", build("2024-01-01/2024-01-03", 0, 100))
        self.assertEqual("https://api.biorxiv.org/pubs/biorxiv/2024-01-01/2024-01-03/30", build("pubs:2024-01-01/2024-01-03", 30, 100))

    def test_medrxiv_never_uses_the_api_medrxiv_host(self) -> None:
        url = paginate._rxiv_url("medrxiv")("2024-01-01/2024-01-03", 0, 100)
        self.assertIn("api.biorxiv.org", url)
        self.assertNotIn("api.medrxiv.org", url)

    def test_europepmc_stops_on_an_echoed_cursor(self) -> None:
        """There is no null terminator: exhaustion echoes your own cursor back."""
        page = paginate._europepmc_parse(
            {"hitCount": 19, "nextCursorMark": "ABC", "resultList": {"result": []}}, "ABC"
        )
        self.assertIsNone(page.next_state)
        self.assertEqual(page.total, 19)

    def test_europepmc_continues_on_a_new_cursor(self) -> None:
        page = paginate._europepmc_parse(
            {"hitCount": 19, "nextCursorMark": "DEF", "resultList": {"result": [{"id": "1"}]}}, "ABC"
        )
        self.assertEqual(page.next_state, "DEF")

    def test_europepmc_errcode_in_a_200_body_raises(self) -> None:
        with self.assertRaises(RuntimeError) as caught:
            paginate._europepmc_parse(
                {"errCode": 404, "errMsg": "Invalid page size provided"}, "*"
            )
        self.assertIn("Invalid page size", str(caught.exception))

    def test_europepmc_reports_the_query_as_parsed(self) -> None:
        page = paginate._europepmc_parse(
            {
                "hitCount": 1,
                "nextCursorMark": "B",
                "request": {"queryString": 'SRC:"PPR"'},
                "resultList": {"result": [{"id": "PPR1"}]},
            },
            "*",
        )
        self.assertTrue(any("as parsed" in note for note in page.notes or []))

    def test_openalex_stops_on_an_empty_page(self) -> None:
        page = paginate._openalex_parse({"meta": {"count": 5, "next_cursor": "X"}, "results": []}, "*")
        self.assertIsNone(page.next_state)

    def test_openalex_surfaces_the_reported_cost(self) -> None:
        page = paginate._openalex_parse(
            {"meta": {"count": 5, "next_cursor": "X", "cost_usd": 0.001}, "results": [{"id": "W1"}]},
            "*",
        )
        self.assertTrue(any("cost_usd" in note for note in page.notes or []))

    def test_crossref_stops_on_an_empty_page(self) -> None:
        page = paginate._crossref_parse(
            {"message": {"total-results": 7, "next-cursor": "X", "items": []}}, "*"
        )
        self.assertIsNone(page.next_state)
        self.assertEqual(page.total, 7)

    def test_every_api_declares_a_delay_and_a_query_format(self) -> None:
        for name, api in paginate.APIS.items():
            with self.subTest(api=name):
                self.assertGreater(api.delay, 0, "an API with no delay would be parallelized by accident")
                self.assertTrue(api.note)

    def test_dry_run_makes_no_request(self) -> None:
        result = run_script(
            "paginate.py", "--api", "biorxiv", "--query", "2024-01-01/2024-01-03", "--dry-run"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["first_url"].startswith("https://api.biorxiv.org/details/"))

    def test_list_apis_needs_no_other_argument(self) -> None:
        result = run_script("paginate.py", "--list-apis")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(json.loads(result.stdout)), sorted(paginate.APIS))

    def test_missing_required_arguments_exit_2(self) -> None:
        result = run_script("paginate.py", "--api", "biorxiv")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--list-apis", result.stderr)

    def test_nonpositive_bounds_are_rejected(self) -> None:
        for flag in ("--max-records", "--max-calls", "--page-size"):
            with self.subTest(flag=flag):
                result = run_script(
                    "paginate.py", "--api", "biorxiv", "--query", "5", flag, "0", "--dry-run"
                )
                self.assertEqual(result.returncode, 1)


class CurrentContractRegressionTests(unittest.TestCase):
    """Synthetic boundary cases supplement the dated response fixtures."""

    def test_legacy_arxiv_id_keeps_archive_and_version(self) -> None:
        self.assertEqual(
            arxiv_atom.id_from_url("https://arxiv.org/abs/hep-th/9901001v2"),
            "hep-th/9901001v2",
        )

    def test_xml_error_page_is_not_an_empty_atom_feed(self) -> None:
        with patch.object(arxiv_atom, "read_input", return_value="<html><body>Blocked</body></html>"), patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as caught:
                arxiv_atom.main(["-"])
        self.assertEqual(caught.exception.code, 1)

    def test_sparse_abstract_does_not_allocate_the_missing_positions(self) -> None:
        text, notes = openalex_abstract.reconstruct({"start": [0], "end": [10**12], "bad": [-1]})
        self.assertEqual(text, "start end")
        self.assertTrue(any("999999999999 position" in note for note in notes))
        self.assertTrue(any("negative position" in note for note in notes))

    def test_api_errors_cannot_be_reported_as_empty_searches_or_works(self) -> None:
        for parser in (paginate._rxiv_parse, paginate._europepmc_parse, paginate._openalex_parse, paginate._crossref_parse):
            with self.subTest(parser=parser.__name__), self.assertRaises(RuntimeError):
                parser({"error": "request rejected"}, 0)
        with self.assertRaises(_common.InputError):
            openalex_abstract.works_from({"error": "rate limit exceeded"})

    def test_rxiv_doi_and_recent_count_use_non_paginated_routes(self) -> None:
        build = paginate._rxiv_url("biorxiv")
        self.assertEqual(build("10.1101/2024.01.16.575895", 0, 100), "https://api.biorxiv.org/details/biorxiv/10.1101/2024.01.16.575895/na/json")
        self.assertEqual(build("5", 0, 100), "https://api.biorxiv.org/details/biorxiv/5")

    def test_url_builders_override_conflicting_pagination_and_preserve_encoding(self) -> None:
        from urllib.parse import parse_qs, urlsplit

        url = paginate._openalex_url("search=alpha%26beta&per_page=999&page=5&cursor=old", "new+cursor=", 999)
        params = parse_qs(urlsplit(url).query)
        self.assertEqual(params["search"], ["alpha&beta"])
        self.assertEqual(params["per_page"], ["100"])
        self.assertEqual(params["cursor"], ["new+cursor="])
        self.assertNotIn("page", params)
        url = paginate._crossref_url("query=alpha&rows=999&offset=20&cursor=old", "new+cursor=", 2)
        params = parse_qs(urlsplit(url).query)
        self.assertEqual(params["rows"], ["2"])
        self.assertEqual(params["cursor"], ["new+cursor="])
        self.assertNotIn("offset", params)

    def test_crossref_sample_is_not_a_paginated_query(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "sample"):
            paginate._crossref_url("sample=5", "*", 100)

    def test_crossref_short_final_page_stops_even_if_cursor_is_present(self) -> None:
        page = paginate._crossref_parse({"message": {"total-results": 1, "items-per-page": 100, "items": [{"DOI": "10.1/example"}], "next-cursor": "same"}}, "same")
        self.assertIsNone(page.next_state)

    def test_europepmc_single_hit_can_omit_the_next_cursor(self) -> None:
        page = paginate._europepmc_parse({"hitCount": 1, "resultList": {"result": [{"id": "32117569", "source": "MED"}]}}, "*")
        self.assertEqual(len(page.records), 1)
        self.assertIsNone(page.next_state)

    def test_final_page_overshoot_is_an_explained_bound(self) -> None:
        payload = {"messages": [{"status": "ok", "total": "3", "count": 3}], "collection": [{"doi": str(i)} for i in range(3)]}
        with patch.object(paginate, "fetch", return_value=payload):
            records, summary, _ = paginate.walk(paginate.APIS["biorxiv"], "2024-01-01/2024-01-01", page_size=100, max_records=2, max_calls=1, verbose=False)
        self.assertEqual(len(records), 2)
        self.assertTrue(summary.stopped_at_limit)
        self.assertTrue(summary.ok)
        self.assertFalse(summary.complete)

    def test_network_error_does_not_echo_key_or_error_body(self) -> None:
        import urllib.error

        url = "https://api.openalex.org/works?api_key=SECRET"
        error = urllib.error.HTTPError(url, 403, "SECRET", {}, io.BytesIO(b"SECRET"))
        with patch.object(paginate.urllib.request, "urlopen", side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                paginate.fetch(url)
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertIn("HTTP 403", str(caught.exception))

    def test_query_credential_is_redacted_in_completed_output(self) -> None:
        with patch.object(paginate, "walk", return_value=([], _common.Reconciliation(expected=0), [])), patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(paginate.main(["--api", "openalex", "--query", "search=crispr&api_key=SECRET"]), 0)
        self.assertNotIn("SECRET", output.getvalue())
        self.assertIn("REDACTED", json.loads(output.getvalue())["query"])


class StructureTests(unittest.TestCase):
    """Repo rules that apply to this skill specifically."""

    def test_frontmatter_conforms(self) -> None:
        self.assertEqual(skill_contract.structure.frontmatter_problems(SKILL_ROOT), [])

    def test_skill_md_is_within_the_line_budget(self) -> None:
        self.assertEqual(skill_contract.structure.length_problems(SKILL_ROOT), [])

    def test_no_stray_tests_under_the_skill(self) -> None:
        self.assertEqual(skill_contract.structure.stray_test_problems(SKILL_ROOT), [])

    def test_no_bytecode_shipped(self) -> None:
        """Running the scripts by hand during development leaves __pycache__ behind."""
        self.assertEqual(skill_contract.structure.bytecode_problems(SKILL_ROOT), [])

    def test_referenced_paths_exist(self) -> None:
        self.assertEqual(skill_contract.structure.link_problems(SKILL_ROOT), [])

    def test_scripts_compile(self) -> None:
        self.assertEqual(skill_contract.structure.compile_problems(SKILL_ROOT), [])

    def test_no_dynamic_execution(self) -> None:
        self.assertEqual(skill_contract.structure.dynamic_execution_problems(SKILL_ROOT), [])

    def test_no_leftover_tool_call_markup(self) -> None:
        """A previous release shipped a stray </content></invoke> at EOF."""
        for path in sorted(SKILL_ROOT.rglob("*.md")):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                for marker in ("</content>", "</invoke>", "</function_calls>"):
                    self.assertNotIn(marker, text)

    def test_every_reference_file_is_linked_from_skill_md(self) -> None:
        skill_md = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for reference in sorted((SKILL_ROOT / "references").glob("*.md")):
            with self.subTest(reference=reference.name):
                self.assertIn(f"references/{reference.name}", skill_md)

    def test_every_script_is_documented_in_skill_md(self) -> None:
        skill_md = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for script in sorted(SCRIPTS.glob("*.py")):
            if script.name == "_common.py":
                continue
            with self.subTest(script=script.name):
                self.assertIn(f"scripts/{script.name}", skill_md)

    def test_paginate_covers_every_api_it_advertises(self) -> None:
        skill_md = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in paginate.APIS:
            with self.subTest(api=name):
                self.assertIn(name, skill_md.lower())


if __name__ == "__main__":
    unittest.main()
