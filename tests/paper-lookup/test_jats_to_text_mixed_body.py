"""Regression tests for reading-order preservation in mixed JATS bodies.

Only synthetic XML is used; run with python -m unittest discover -s this_directory.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "paper-lookup"
SCRIPT = SKILL_ROOT / "scripts" / "jats_to_text.py"
SPEC = importlib.util.spec_from_file_location("jats_to_text_under_test", SCRIPT)
assert SPEC and SPEC.loader
reader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reader)


def article(body: str) -> str:
    return (
        '<article><front><article-meta><title-group><article-title>Example article</article-title>'
        '</title-group></article-meta></front>' + body + '</article>'
    )


class MixedBodyTests(unittest.TestCase):
    def sections(self, body: str):
        return reader.collect_sections(reader.parse(body))

    def cli(self, xml: str, *options: str):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "example.xml"
            path.write_text(xml, encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    code = reader.main([str(path), *options])
                except SystemExit as error:
                    code = error.code
            return code, out.getvalue(), err.getvalue()

    def test_paragraph_only_keeps_legacy_single_block(self):
        self.assertEqual(self.sections('<body><p>First <italic>inline</italic> text.</p><p>Second.</p></body>'),
                         [{"title": "", "sec_type": None, "text": "First inline text. Second."}])

    def test_section_only_keeps_titles_types_and_nested_text(self):
        body = '<body><sec sec-type="methods"><title>Methods</title><p>Outer.</p><sec><title>Detail</title><p>Nested.</p></sec></sec><sec><title>Results</title><p>Final.</p></sec></body>'
        self.assertEqual(self.sections(body), [
            {"title": "Methods", "sec_type": "methods", "text": "Methods Outer. Detail Nested."},
            {"title": "Results", "sec_type": None, "text": "Results Final."}])

    def test_prose_before_between_and_after_sections_stays_in_order(self):
        body = '<body><p>Lead one.</p><p>Lead two.</p><sec><title>First</title><p>Section one.</p></sec><p>Bridge one.</p><p>Bridge two.</p><sec><title>Second</title><p>Section two.</p></sec><p>Tail.</p></body>'
        self.assertEqual([s['text'] for s in self.sections(body)],
                         ['Lead one. Lead two.', 'First Section one.', 'Bridge one. Bridge two.', 'Second Section two.', 'Tail.'])

    def test_empty_prose_does_not_create_empty_blocks(self):
        self.assertEqual(self.sections('<body><p> </p><sec><title>Only</title><p>Kept.</p></sec><p/></body>'),
                         [{"title": "Only", "sec_type": None, "text": "Only Kept."}])

    def test_new_prose_keeps_inline_text_and_citation_tail(self):
        body = '<body><p>Alpha <italic>beta</italic><xref>9</xref> after.</p><sec><title>End</title><p>Done.</p></sec></body>'
        self.assertEqual(self.sections(body)[0]['text'], 'Alpha beta after.')

    def test_foreign_body_children_are_not_added_to_reading_order(self):
        body = '<body><p>Owned lead.</p><sub-article><body><p>FOREIGN ARTICLE</p></body></sub-article><response><body><p>FOREIGN RESPONSE</p></body></response><sec><title>Main</title><p>Owned section.</p></sec><p>Owned tail.</p></body>'
        texts = [s['text'] for s in self.sections(body)]
        self.assertEqual(texts, ['Owned lead.', 'Main Owned section.', 'Owned tail.'])
        self.assertNotIn('FOREIGN', ' '.join(texts))

    def test_foreign_content_nested_in_new_prose_is_skipped_with_tail(self):
        body = '<body><p>Owned before <sub-article><body><p>FOREIGN</p></body></sub-article> after.</p><sec><title>Main</title><p>Section.</p></sec></body>'
        self.assertEqual(self.sections(body)[0]['text'], 'Owned before after.')

    def test_nested_section_paragraph_is_not_emitted_twice(self):
        body = '<body><p>Lead.</p><sec><title>Outer</title><sec><title>Inner</title><p>Unique nested prose.</p></sec></sec></body>'
        sections = self.sections(body)
        self.assertEqual(len(sections), 2)
        self.assertEqual(' '.join(s['text'] for s in sections).count('Unique nested prose.'), 1)

    def test_unrelated_direct_table_is_not_promoted_to_prose(self):
        body = '<body><p>Lead.</p><table-wrap><p>TABLE ONLY</p></table-wrap><sec><title>Main</title><p>Body.</p></sec></body>'
        self.assertEqual([s['text'] for s in self.sections(body)], ['Lead.', 'Main Body.'])

    def test_cli_default_json_preserves_metadata_and_all_body_blocks(self):
        code, out, _ = self.cli(article('<body><p>Lead.</p><sec><title>Methods</title><p>Work.</p></sec></body>'))
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload['metadata']['title'], 'Example article')
        self.assertEqual(payload['section_count'], 2)
        self.assertEqual([s['text'] for s in payload['sections']], ['Lead.', 'Methods Work.'])

    def test_cli_text_only_preserves_reading_order(self):
        code, out, _ = self.cli(article('<body><p>Lead.</p><sec><title>Main</title><p>Middle.</p></sec><p>Tail.</p></body>'), '--text-only')
        self.assertEqual(code, 0)
        self.assertIn('Lead.', out)
        self.assertIn('Tail.', out)
        self.assertLess(out.index('Lead.'), out.index('Middle.'))
        self.assertLess(out.index('Middle.'), out.index('Tail.'))

    def test_cli_section_filter_still_selects_named_sections_only(self):
        code, out, _ = self.cli(article('<body><p>Lead.</p><sec sec-type="methods"><title>Approach</title><p>Work.</p></sec><p>Tail.</p></body>'), '--sections', 'methods')
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload['section_count'], 1)
        self.assertEqual(payload['sections'][0]['text'], 'Approach Work.')

    def test_cli_metadata_only_refusal_is_unchanged(self):
        code, out, err = self.cli(article(''))
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(out)['full_text_available'])
        self.assertIn('metadata only', err)
        code, out, _ = self.cli(article(''), '--allow-metadata-only')
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(out)['full_text_available'])

    def test_cli_malformed_xml_remains_an_error(self):
        code, out, err = self.cli('<article><body>')
        self.assertEqual(code, 1)
        self.assertEqual(out, '')
        self.assertIn('not parseable as XML', err)


if __name__ == '__main__':
    unittest.main()
