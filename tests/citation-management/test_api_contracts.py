"""Network contract regressions using fixtures, never public API calls."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'citation-management'
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
import _common
import doi_to_bibtex
import extract_metadata
import search_google_scholar
import search_openalex
import search_pubmed
import validate_citations


def response(status=200, payload=None, content=b'', headers=None, text=''):
    return Mock(status_code=status, json=Mock(return_value=payload), content=content,
                headers=headers or {}, text=text)


class IdentifierTests(unittest.TestCase):
    def test_identifier_parsing_preserves_versions_and_complete_doi(self):
        extractor = extract_metadata.MetadataExtractor()
        for raw, expected in [
            ('1', ('pmid', '1')),
            ('doi:10.1234/a', ('doi', '10.1234/a')),
            ('hep-th/9901001v2', ('arxiv', 'hep-th/9901001v2')),
            ('https://arxiv.org/abs/1706.03762v7', ('arxiv', '1706.03762v7')),
            ('https://arxiv.org/pdf/hep-th/9901001v2.pdf', ('arxiv', 'hep-th/9901001v2')),
            ('https://doi.org/10.1234/a%23b', ('doi', '10.1234/a#b')),
            ('https://example.org/doi/10.1234/a/b?tracking=1', ('doi', '10.1234/a/b')),
            ('https://pmc.ncbi.nlm.nih.gov/articles/PMC7611378/', ('pmcid', 'PMC7611378')),
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(extractor.identify_type(raw), expected)

    def test_search_json_input_extracts_identifiers_without_silent_drops(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input.json'
            path.write_text(json.dumps({'results': [{'doi': '10.1234/x', 'pmid': '1'},
                                                  {'pmid': 2}, {'url': 'https://example.org/paper'}]}))
            self.assertEqual(extract_metadata.read_identifiers(str(path)),
                             ['10.1234/x', '2', 'https://example.org/paper'])
            path.write_text(json.dumps({'results': [{'title': 'No identifier'}]}))
            with self.assertRaisesRegex(ValueError, 'record 1'):
                extract_metadata.read_identifiers(str(path))

    def test_repeated_flags_and_partial_batch_status(self):
        metadata = {'entry_type': 'article', 'authors': 'Doe, Jane', 'title': 'T', 'year': '2026'}
        output = io.StringIO()
        args = ['extract_metadata.py', '--doi', '10.1234/a', '--doi', '10.1234/b', '--format', 'json']
        with patch.object(sys, 'argv', args), patch.object(extract_metadata.MetadataExtractor,
                'extract_from_doi', side_effect=[metadata, None]) as fetch, \
                patch.object(extract_metadata.time, 'sleep'), redirect_stdout(output), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exit_result:
                extract_metadata.main()
        self.assertEqual(exit_result.exception.code, 2)
        self.assertEqual([call.args[0] for call in fetch.call_args_list], ['10.1234/a', '10.1234/b'])
        self.assertEqual(json.loads(output.getvalue())['count'], 1)


class MetadataEndpointTests(unittest.TestCase):
    def test_current_pmc_converter_numeric_pmid(self):
        extractor = extract_metadata.MetadataExtractor(email='test@example.invalid')
        reply = response(payload={'records': [{'pmid': 27102758, 'pmcid': 'PMC7611378'}]})
        with patch.object(extractor.session, 'get', return_value=reply) as get, \
                patch.object(extractor, 'extract_from_pmid', return_value={'pmid': '27102758'}) as fetch:
            self.assertEqual(extractor.extract_from_pmcid('PMC7611378'), {'pmid': '27102758'})
        self.assertEqual(get.call_args.args[0], 'https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/')
        self.assertEqual(get.call_args.kwargs['params']['format'], 'json')
        self.assertEqual(get.call_args.kwargs['params']['tool'], 'citation-management')
        self.assertNotIn('api_key', get.call_args.kwargs['params'])
        fetch.assert_called_once_with('27102758')

    def test_pmc_doi_fallback_and_redacted_error(self):
        extractor = extract_metadata.MetadataExtractor(email='private@example.invalid')
        with patch.object(extractor.session, 'get', return_value=response(payload={'records': [{'doi': '10.1234/x'}]})), \
                patch.object(extractor, 'extract_from_doi', return_value={'doi': '10.1234/x'}) as fetch:
            self.assertEqual(extractor.extract_from_pmcid('PMC1'), {'doi': '10.1234/x'})
        fetch.assert_called_once_with('10.1234/x')
        diagnostic = io.StringIO()
        with patch.object(extractor.session, 'get', side_effect=extract_metadata.requests.Timeout('email=private@example.invalid')), redirect_stderr(diagnostic):
            self.assertIsNone(extractor.extract_from_pmcid('PMC1'))
        self.assertNotIn('private@example.invalid', diagnostic.getvalue())

    def test_arxiv_error_feed_is_not_a_citation_and_requests_are_paced(self):
        extractor = extract_metadata.MetadataExtractor()
        xml = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/api/errors#incorrect_id</id><title>Error</title></entry></feed>'
        with patch.object(extractor.session, 'get', return_value=response(content=xml)) as get, \
                patch.object(extract_metadata.time, 'monotonic', side_effect=[10, 11, 13]), \
                patch.object(extract_metadata.time, 'sleep') as sleep:
            self.assertIsNone(extractor.extract_from_arxiv('1234.12345'))
            self.assertIsNone(extractor.extract_from_arxiv('1234.12345'))
        sleep.assert_called_once_with(2.0)
        self.assertEqual(get.call_args.args[0], 'https://export.arxiv.org/api/query')

    def test_doi_negotiation_quotes_suffix_and_normalises_key(self):
        converter = doi_to_bibtex.DOIConverter()
        bib = '@article{providerkey, author={Doe, Jane}, title={A study}, year={2026}}'
        with patch.object(converter.session, 'get', return_value=response(text=bib)) as get:
            entry = converter.doi_to_bibtex('10.1234/a#b?c')
        self.assertEqual(get.call_args.args[0], 'https://doi.org/10.1234/a%23b%3Fc')
        self.assertEqual(get.call_args.kwargs['headers']['Accept'], 'application/x-bibtex')
        self.assertEqual(_common.parse_bibtex(entry)[0]['key'], 'Doe2026study')

    def test_doi_negotiation_rejects_html(self):
        converter = doi_to_bibtex.DOIConverter()
        with patch.object(converter.session, 'get', return_value=response(text='<html>Captcha</html>')):
            self.assertIsNone(converter.doi_to_bibtex('10.1234/x'))

    def test_crossref_issued_year_is_retained(self):
        self.assertEqual(extract_metadata.MetadataExtractor()._extract_year_crossref(
            {'issued': {'date-parts': [[2026]]}}), '2026')

    def test_dataset_is_not_labelled_preprint(self):
        rendered = search_openalex.OpenAlexSearcher().metadata_to_bibtex(
            {'type': 'dataset', 'authors': 'Doe, Jane', 'title': 'Measurements', 'year': '2026'})
        self.assertNotIn('Preprint', rendered)


class DOIValidationTests(unittest.TestCase):
    def setUp(self):
        self.validator = validate_citations.CitationValidator()
        patcher = patch.object(validate_citations.time, 'sleep')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_transport_or_bad_response_is_inconclusive(self):
        for replies in ([response(429)], [response(503)],
                        [response(payload={})], [response(404), response(429)],
                        [response(404), response(200, {'data': {'id': 'different'}})]):
            with self.subTest(replies=replies), patch.object(self.validator.session, 'get', side_effect=replies):
                self.assertEqual(self.validator.verify_doi('10.1234/x'), (None, None))
        with patch.object(self.validator.session, 'get', side_effect=validate_citations.requests.Timeout()):
            self.assertEqual(self.validator.verify_doi('10.1234/x'), (None, None))

    def test_datacite_record_proves_registration(self):
        with patch.object(self.validator.session, 'get', side_effect=[response(404), response(payload={'data': {'id': '10.1234/x'}})]):
            self.assertEqual(self.validator.verify_doi('10.1234/x'), (True, None))

    def test_other_registration_agency_uses_resolver_without_following_publisher(self):
        with patch.object(self.validator.session, 'get', side_effect=[response(404), response(404),
                response(302, headers={'Location': 'https://publisher.example/article'})]) as get:
            self.assertEqual(self.validator.verify_doi('10.1234/x'), (True, None))
        self.assertFalse(get.call_args.kwargs['allow_redirects'])

    def test_resolver_404_is_invalid(self):
        with patch.object(self.validator.session, 'get', side_effect=[response(404), response(404), response(404)]):
            self.assertEqual(self.validator.verify_doi('10.1234/x'), (False, None))

    def test_inconclusive_result_is_visible_in_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'refs.bib'
            path.write_text('@article{x,author={A},title={T},year={2026},journal={J},doi={10.1234/x}}')
            with patch.object(self.validator, 'verify_doi', return_value=(None, None)):
                report = self.validator.validate_file(str(path), check_dois=True)
        self.assertIn('doi_unverified', [warning['type'] for warning in report['warnings']])
        self.assertNotIn('invalid_doi', [error['type'] for error in report['errors']])


class SearchContractTests(unittest.TestCase):
    def test_pubmed_filters_group_query_and_identify_tool(self):
        searcher = search_pubmed.PubMedSearcher()
        with patch.object(searcher.session, 'get', return_value=response(payload={'esearchresult': {'idlist': ['1'], 'count': '1'}})) as get:
            self.assertEqual(searcher.search('A OR B', date_start='2020-01-01', date_end='2024-12-31'), ['1'])
        self.assertEqual(get.call_args.kwargs['params']['term'], '(A OR B) AND 2020/01/01:2024/12/31[Publication Date]')
        self.assertEqual(get.call_args.kwargs['params']['tool'], 'citation-management')

    def test_pubmed_failed_second_batch_does_not_export_partial_records(self):
        searcher = search_pubmed.PubMedSearcher()
        xml = b'<PubmedArticleSet>' + b'<PubmedArticle/>' * 200 + b'</PubmedArticleSet>'
        records = [{'pmid': str(i)} for i in range(1, 201)]
        with patch.object(searcher.session, 'get', side_effect=[response(content=xml), search_pubmed.requests.Timeout()]), \
                patch.object(searcher, '_extract_metadata_from_xml', side_effect=records), \
                patch.object(search_pubmed.time, 'sleep'):
            self.assertEqual(searcher.fetch_metadata([str(i) for i in range(1, 202)]), [])

    def test_pubmed_missing_record_does_not_masquerade_as_complete(self):
        searcher = search_pubmed.PubMedSearcher()
        with patch.object(searcher.session, 'get', return_value=response(content=b'<PubmedArticleSet/>')), patch.object(search_pubmed.time, 'sleep'):
            self.assertEqual(searcher.fetch_metadata(['1']), [])

    def test_scholar_years_go_to_upstream_and_limit_does_not_consume_extra_record(self):
        upstream = Mock()
        upstream.search_pubs.return_value = iter([
            {'bib': {'title': 'T', 'author': ['Doe, Jane', 'Smith, John'], 'pub_year': '2024'}},
            {'bib': {'title': 'Extra'}}])
        with patch.object(search_google_scholar, 'SCHOLARLY_AVAILABLE', True), \
                patch.object(search_google_scholar, 'scholarly', upstream, create=True), \
                patch.object(search_google_scholar.time, 'sleep'):
            searcher = search_google_scholar.GoogleScholarSearcher()
            records = searcher.search('topic', max_results=1, year_start=2020, year_end=2024)
            bib = searcher.metadata_to_bibtex(records[0])
        upstream.search_pubs.assert_called_once_with('topic', year_low=2020, year_high=2024)
        self.assertEqual(next(upstream.search_pubs.return_value)['bib']['title'], 'Extra')
        self.assertEqual(_common.parse_bibtex(bib)[0]['fields']['author'], 'Doe, Jane and Smith, John')
