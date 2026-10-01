"""Tests for the Hugging Science catalogue fetcher.

The whole script is a markdown parser wrapped in a network call, so the tests
feed `parse_markdown` fixture documents directly and never fetch anything. The
parser is a small state machine over headings and bullets, and its edge cases
-- a section suffix like `## Datasets (12)`, an H3 before any H2, a bullet key
it does not recognise -- are where a catalogue silently loses entries.
"""

from __future__ import annotations

import sys
import unittest
from unittest import mock

from pathlib import Path

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "hugging-science"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import fetch_catalog  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

CATALOGUE = """\
# Hugging Science

## Datasets (2)

### Protein Folding Benchmark
- **type**: dataset
- **tags**: biology, benchmark
- **huggingface**: https://huggingface.co/datasets/example/folding
- **author**: Example Lab
- **date**: 2026-01-15

A held-out set of folded structures.
Spanning two lines of prose.

### Climate Reanalysis Grid
- **type**: dataset
- **tags**: climate, earth-science
- **link**: https://huggingface.co/datasets/example/climate

## Models

### Genomics Encoder
- **type**: model
- **tags**: genomics
- **url**: https://huggingface.co/example/genomics-encoder

## Blog Posts

### Why Open Science Needs Open Weights
- **author**: A. Writer
- **date**: 2026-02-02

An argument.
"""


class ParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entries = fetch_catalog.parse_markdown(CATALOGUE)

    def test_every_entry_is_found(self) -> None:
        self.assertEqual(
            [entry.title for entry in self.entries],
            [
                "Protein Folding Benchmark",
                "Climate Reanalysis Grid",
                "Genomics Encoder",
                "Why Open Science Needs Open Weights",
            ],
        )

    def test_the_count_suffix_is_stripped_from_the_section_label(self) -> None:
        # "## Datasets (2)" must land in the same bucket as "## Datasets".
        self.assertEqual(self.entries[0].section, "datasets")
        self.assertEqual(self.entries[1].section, "datasets")
        self.assertEqual(self.entries[2].section, "models")
        self.assertEqual(self.entries[3].section, "blog posts")

    def test_metadata_bullets_populate_the_record(self) -> None:
        entry = self.entries[0]
        self.assertEqual(entry.type, "dataset")
        self.assertEqual(entry.tags, ["biology", "benchmark"])
        self.assertEqual(entry.url, "https://huggingface.co/datasets/example/folding")
        self.assertEqual(entry.author, "Example Lab")
        self.assertEqual(entry.date, "2026-01-15")

    def test_huggingface_link_and_url_keys_all_fill_the_url(self) -> None:
        self.assertTrue(self.entries[0].url)  # **huggingface**
        self.assertTrue(self.entries[1].url)  # **link**
        self.assertTrue(self.entries[2].url)  # **url**

    def test_prose_after_the_bullets_becomes_the_description(self) -> None:
        self.assertEqual(
            self.entries[0].description,
            "A held-out set of folded structures. Spanning two lines of prose.",
        )

    def test_an_entry_without_prose_has_an_empty_description(self) -> None:
        self.assertEqual(self.entries[1].description, "")

    def test_content_before_the_first_entry_is_ignored(self) -> None:
        entries = fetch_catalog.parse_markdown(
            "# Title\n\nSome preamble prose.\n\n### First\n- **type**: model\n"
        )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].title, "First")

    def test_an_entry_before_any_section_is_labelled_unknown(self) -> None:
        entries = fetch_catalog.parse_markdown("### Orphan\n- **type**: model\n")
        self.assertEqual(entries[0].section, "unknown")

    def test_unrecognised_bullet_keys_are_dropped_not_misfiled(self) -> None:
        entries = fetch_catalog.parse_markdown(
            "## Models\n\n### X\n- **license**: mit\n- **type**: model\n"
        )
        self.assertEqual(entries[0].type, "model")
        self.assertEqual(entries[0].tags, [])

    def test_empty_input_yields_no_entries(self) -> None:
        self.assertEqual(fetch_catalog.parse_markdown(""), [])
        self.assertEqual(fetch_catalog.parse_markdown("## Datasets\n"), [])

    def test_tags_are_split_and_blank_entries_discarded(self) -> None:
        entries = fetch_catalog.parse_markdown(
            "### X\n- **tags**: a, , b ,\n"
        )
        self.assertEqual(entries[0].tags, ["a", "b"])


class FilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entries = fetch_catalog.parse_markdown(CATALOGUE)

    def test_no_filter_matches_everything(self) -> None:
        self.assertTrue(all(e.matches_filter(None, None) for e in self.entries))

    def test_each_cli_filter_value_selects_its_section(self) -> None:
        expected = {"datasets": 2, "models": 1, "blogs": 1}
        for kind, count in expected.items():
            with self.subTest(kind=kind):
                matched = [e for e in self.entries if e.matches_filter(kind, None)]
                self.assertEqual(len(matched), count)

    def test_the_aliases_absorb_singular_section_headings_upstream(self) -> None:
        # The alias sets map one CLI value onto the section spellings the
        # source markdown may use, so `--filter datasets` still works when a
        # topic file writes `## Dataset`.
        singular = fetch_catalog.parse_markdown("## Dataset\n\n### X\n- **type**: dataset\n")
        self.assertTrue(singular[0].matches_filter("datasets", None))

        blog = fetch_catalog.parse_markdown("## Blog\n\n### Y\n")
        self.assertTrue(blog[0].matches_filter("blogs", None))

    def test_the_cli_only_offers_the_aliased_filter_values(self) -> None:
        # matches_filter falls back to an exact section match for anything that
        # is not an alias key, so the CLI must not offer values outside them.
        source = (SCRIPTS / "fetch_catalog.py").read_text(encoding="utf-8")
        self.assertIn('choices=["datasets", "models", "blogs"]', source)

    def test_kind_matching_is_case_insensitive(self) -> None:
        matched = [e for e in self.entries if e.matches_filter("MODELS", None)]
        self.assertEqual(len(matched), 1)

    def test_tag_matching_is_a_case_insensitive_substring(self) -> None:
        matched = [e.title for e in self.entries if e.matches_filter(None, "GENOM")]
        self.assertEqual(matched, ["Genomics Encoder"])

    def test_a_tag_also_matches_the_type_field(self) -> None:
        # `matches_filter` falls back to `type` so `--tag model` still works
        # on entries that carry no explicit tags.
        entry = fetch_catalog.Entry(title="X", section="models", type="model")
        self.assertTrue(entry.matches_filter(None, "model"))

    def test_kind_and_tag_must_both_match(self) -> None:
        matched = [e for e in self.entries if e.matches_filter("datasets", "genomics")]
        self.assertEqual(matched, [])

    def test_an_unknown_kind_matches_nothing_rather_than_everything(self) -> None:
        matched = [e for e in self.entries if e.matches_filter("posters", None)]
        self.assertEqual(matched, [])


class RenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entries = fetch_catalog.parse_markdown(CATALOGUE)

    def test_an_entry_renders_only_the_fields_it_has(self) -> None:
        rendered = fetch_catalog.render_entry(self.entries[1])
        self.assertIn("### Climate Reanalysis Grid", rendered)
        self.assertIn("- Type: dataset", rendered)
        self.assertIn("- URL: https://huggingface.co/datasets/example/climate", rendered)
        self.assertNotIn("- Author:", rendered)
        self.assertNotIn("- Date:", rendered)

    def test_grouped_rendering_counts_each_section(self) -> None:
        rendered = fetch_catalog.render_entries(self.entries)
        self.assertIn("## Datasets (2)", rendered)
        self.assertIn("## Models (1)", rendered)
        self.assertIn("## Blog Posts (1)", rendered)

    def test_ungrouped_rendering_omits_section_headers(self) -> None:
        rendered = fetch_catalog.render_entries(self.entries, group_by_section=False)
        self.assertNotIn("## Datasets", rendered)
        self.assertIn("### Genomics Encoder", rendered)

    def test_an_empty_result_says_so_rather_than_rendering_nothing(self) -> None:
        self.assertEqual(fetch_catalog.render_entries([]), "(no entries matched)")

    def test_a_rendered_catalogue_round_trips_through_the_parser(self) -> None:
        # render_entries emits the same H2/H3 shape the parser reads, so a
        # round trip must preserve every title and section.
        reparsed = fetch_catalog.parse_markdown(
            fetch_catalog.render_entries(self.entries)
        )
        self.assertEqual(
            [(e.title, e.section) for e in reparsed],
            [(e.title, e.section) for e in self.entries],
        )


class CatalogueSourceTests(unittest.TestCase):
    def test_topic_slugs_are_lowercase_hyphenated_and_sorted(self) -> None:
        topics = fetch_catalog.KNOWN_TOPICS
        self.assertTrue(topics)
        self.assertEqual(topics, sorted(topics))
        for topic in topics:
            with self.subTest(topic=topic):
                self.assertRegex(topic, r"^[a-z]+(-[a-z]+)*$")

    def test_the_base_url_is_https(self) -> None:
        self.assertTrue(fetch_catalog.BASE.startswith("https://"))

    def test_requests_identify_the_skill_and_carry_a_timeout(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"ok"
        with mock.patch("urllib.request.urlopen", return_value=response) as opened:
            self.assertEqual(fetch_catalog.fetch(f"{fetch_catalog.BASE}/llms.txt"), "ok")

        request = opened.call_args.args[0]
        self.assertIn("hugging-science-skill", request.get_header("User-agent"))
        self.assertEqual(opened.call_args.kwargs["timeout"], 30)

    def test_network_failures_exit_with_a_message_rather_than_a_traceback(self) -> None:
        import urllib.error

        failures = [
            urllib.error.HTTPError("u", 404, "Not Found", {}, None),
            urllib.error.URLError("no route to host"),
        ]
        for error in failures:
            with self.subTest(error=type(error).__name__):
                with mock.patch("urllib.request.urlopen", side_effect=error):
                    with self.assertRaises(SystemExit) as raised:
                        fetch_catalog.fetch("https://example.invalid/x")
                self.assertNotIn("Traceback", str(raised.exception))



class CurrentCatalogTests(unittest.TestCase):
    def test_cross_topic_duplicates_do_not_inflate_resource_count(self):
        md = CATALOGUE + "\n## Topic: Biology\n" + CATALOGUE
        entries = fetch_catalog.unique_entries(fetch_catalog.parse_markdown(md))
        # The blog has no URL: do not silently merge unknown identities.
        self.assertEqual(len(entries), 5)
        self.assertEqual(sum(e.url.endswith('/folding') for e in entries), 1)

    def test_model_and_dataset_at_the_same_url_are_not_merged(self):
        entries = [fetch_catalog.Entry('same', section, url='https://example.org/x')
                   for section in ('models', 'datasets')]
        self.assertEqual(len(fetch_catalog.unique_entries(entries)), 2)

    def test_search_filters_before_deduplication(self):
        import argparse
        import contextlib
        import io
        md = CATALOGUE + CATALOGUE.replace('biology, benchmark', 'biology, new-tag')
        args = argparse.Namespace(query='folding', filter='datasets', tag='new-tag', format='json')
        with mock.patch.object(fetch_catalog, 'fetch', return_value=md):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                fetch_catalog.cmd_search(args)
        import json
        result = json.loads(output.getvalue())
        self.assertEqual(len(result), 1)
        self.assertIn('new-tag', result[0]['tags'])

    def test_all_raw_preserves_provenance_banner(self):
        import argparse
        import contextlib
        import io
        with mock.patch.object(fetch_catalog, 'fetch', return_value=CATALOGUE):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                fetch_catalog.cmd_all(argparse.Namespace(raw=True))
        self.assertIn('untrusted third-party data', output.getvalue())
        self.assertTrue(output.getvalue().endswith(CATALOGUE + '\n'))

    def test_socket_timeout_is_a_clean_failure(self):
        with mock.patch('urllib.request.urlopen', side_effect=TimeoutError):
            with self.assertRaisesRegex(SystemExit, 'Timeout fetching'):
                fetch_catalog.fetch('https://example.invalid')


if __name__ == "__main__":
    unittest.main()
