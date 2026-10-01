"""Regressions for DOI uncertainty, corpus preservation, and PDF CLI contracts."""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'literature-review'
SCRIPTS = SKILL_ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))

import generate_pdf
import search_databases
import verify_citations

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def response(status=200, payload=None, headers=None):
    result = Mock(status_code=status, headers=headers or {})
    result.json.return_value = payload
    return result


def verifier_with(*responses):
    verifier = verify_citations.CitationVerifier()
    verifier.session.get = Mock(side_effect=responses)
    return verifier


def test_doi_extraction_preserves_balanced_parentheses_deduplicates_and_strips_prose():
    text = 'https://doi.org/10.1000/A(B). [duplicate](https://doi.org/10.1000/a(b)) and 10.1000/test;'
    assert verify_citations.CitationVerifier().extract_dois(text) == ['10.1000/a(b)', '10.1000/test']


@pytest.mark.parametrize('status,payload,expected', [
    (200, {'responseCode': 100, 'handle': '10.1000/x'}, 'missing'),
    (404, {'responseCode': 100, 'handle': '10.1000/x'}, 'missing'),
    (200, {'responseCode': 2, 'handle': '10.1000/x'}, 'inconclusive'),
    (200, {'responseCode': 1, 'handle': '10.1000/other'}, 'inconclusive'),
    (200, [], 'inconclusive'),
    (403, {}, 'inconclusive'),
])
def test_handle_status_and_identity_are_required(status, payload, expected):
    verifier = verifier_with(response(status, payload))
    registered, details = verifier.verify_doi('10.1000/x')
    assert not registered
    assert details['status'] == expected
    assert verifier.session.get.call_count == 1


def test_crossref_missing_does_not_invalidate_registered_doi():
    verifier = verifier_with(response(payload={'responseCode': 1, 'handle': '10.1000/x'}), response(404))
    registered, details = verifier.verify_doi('https://doi.org/10.1000/X')
    assert registered
    assert details['metadata_status'] == 'unavailable'
    assert details['crossref_http_status'] == 404


def test_timeout_is_inconclusive():
    verifier = verifier_with(requests.Timeout('network timeout'))
    registered, details = verifier.verify_doi('10.1000/x')
    assert not registered and details['status'] == 'inconclusive'


def test_crossref_preserves_all_authors_empty_fields_and_issued_year():
    authors = [{'given': 'Alex', 'family': f'Family{i}'} for i in range(6)] + [{'name': 'Study Group'}]
    message = {'DOI': '10.1000/x', 'title': [], 'container-title': [],
               'author': authors, 'issued': {'date-parts': [[2026]]}}
    verifier = verifier_with(response(payload={'responseCode': 1, 'handle': '10.1000/X'}),
                             response(payload={'message': message}))
    registered, details = verifier.verify_doi('10.1000/x')
    assert registered
    assert details['author'] == authors
    assert 'Family5' in details['authors'] and 'Study Group' in details['authors']
    assert details['title'] == '' and details['year'] == '2026'
    assert details['crossref_message'] == message


def test_crossref_wrong_identifier_is_not_accepted():
    verifier = verifier_with(response(payload={'message': {'DOI': '10.1000/other'}}))
    assert verifier._get_crossref_metadata('10.1000/x')['metadata_status'] == 'unavailable'


def test_get_retries_429_with_retry_after_and_encodes_reserved_suffix(monkeypatch):
    sleep = Mock()
    monkeypatch.setattr(verify_citations.time, 'sleep', sleep)
    verifier = verifier_with(response(429, {}, {'Retry-After': '2'}),
                             response(payload={'responseCode': 1, 'handle': '10.1000/a?b#c'}),
                             response(404))
    assert verifier.verify_doi('10.1000/a?b#c')[0]
    assert sleep.call_args.args == (2,)
    assert verifier.session.get.call_args_list[0].args[0].endswith('10.1000/a%3Fb%23c')


def test_report_keeps_missing_and_inconclusive_separate(tmp_path, monkeypatch):
    paper = tmp_path / 'paper.md'
    paper.write_text('10.1000/a 10.1000/b 10.1000/c')
    verifier = verify_citations.CitationVerifier()
    verifier.verify_doi = Mock(side_effect=[(False, {'status': 'missing'}),
                                           (False, {'status': 'inconclusive'}),
                                           (True, {'status': 'registered', 'metadata_status': 'unavailable'})])
    monkeypatch.setattr(verify_citations.time, 'sleep', lambda _: None)
    report = verifier.verify_citations_in_file(str(paper))
    assert report['missing'] == ['10.1000/a']
    assert report['inconclusive'] == ['10.1000/b']
    assert report['metadata_unavailable'] == ['10.1000/c']


def test_non_markdown_input_is_never_overwritten(tmp_path):
    path = tmp_path / 'references.txt'
    path.write_text('No identifiers in this draft.')
    run = subprocess.run([sys.executable, str(SCRIPTS / 'verify_citations.py'), str(path)],
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert path.read_text() == 'No identifiers in this draft.'
    assert json.loads((tmp_path / 'references_citation_report.json').read_text())['total_dois'] == 0
    refused = subprocess.run([sys.executable, str(SCRIPTS / 'verify_citations.py'), str(path),
                              '--output', str(path)], capture_output=True, text=True)
    assert refused.returncode != 0
    assert path.read_text() == 'No identifiers in this draft.'


def test_missing_year_null_doi_and_url_doi_are_preserved_correctly():
    results = [{'title': None, 'doi': None}, {'title': 'A', 'doi': 'https://doi.org/10.1000/X'},
               {'title': 'B', 'doi': 'doi:10.1000/x'}, {'title': 'No year'}]
    filtered = search_databases.filter_by_year(search_databases.deduplicate_results(results), 2020, 2026)
    assert len(filtered) == 3


def test_title_dedup_does_not_merge_identified_and_unidentified_records():
    records = [{'title': 'A', 'doi': '10.1000/x'}, {'title': 'A'}]
    assert len(search_databases.deduplicate_results(records)) == 2
    assert len(search_databases.deduplicate_results(records[::-1])) == 2


def test_numeric_ranking_handles_null_strings_nan_and_zero():
    records = [{'citations': '2'}, {'citations': None}, {'citations': '10'},
               {'citations': 0}, {'citations': 'NaN'}]
    assert [r['citations'] for r in search_databases.rank_results(records)][:3] == ['10', '2', 0]
    assert search_databases.generate_search_summary([{'citations': 0}, {'citations': 10}])['avg_citations'] == 5


def test_bibtex_citation_keys_are_unique():
    data = [{'first_author': 'Lee', 'year': 2026}, {'first_author': 'Lee', 'year': 2026}]
    text = search_databases.format_search_results(data, 'bibtex')
    assert '@article{Lee2026,' in text and '@article{Lee2026_2,' in text


def test_json_stdout_remains_machine_readable_and_raw_envelopes_fail(tmp_path):
    path = tmp_path / 'records.json'
    path.write_text('[{"title":"A"},{"title":"A"}]')
    run = subprocess.run([sys.executable, str(SCRIPTS / 'search_databases.py'), str(path),
                          '--deduplicate', '--summary', '--format', 'json'], capture_output=True, text=True)
    assert run.returncode == 0
    assert json.loads(run.stdout) == [{'title': 'A'}]
    path.write_text('{"results": []}')
    run = subprocess.run([sys.executable, str(SCRIPTS / 'search_databases.py'), str(path)],
                          capture_output=True, text=True)
    assert run.returncode != 0
    assert 'normalized JSON array' in run.stderr


def test_pdf_cli_output_flag_and_local_csl_are_honored(tmp_path, monkeypatch):
    source = tmp_path / 'review.md'
    source.write_text('See [@article].')
    source.with_suffix('.bib').write_text('@article{article,title={Title},year={2026}}')
    style = tmp_path / 'apa.csl'
    style.write_text('<style/>')
    output = tmp_path / 'requested.pdf'
    monkeypatch.setattr(generate_pdf, 'check_dependencies', lambda: True)
    def render(cmd, **kwargs):
        assert cmd[cmd.index('-o') + 1] == str(output)
        assert cmd[cmd.index('--csl') + 1] == str(style)
        assert '--citeproc' in cmd and '--bibliography' in cmd
        assert '--number-sections' not in cmd and '--toc' not in cmd
        output.write_bytes(b'%PDF-1.7 test')
        return Mock(stderr='')
    monkeypatch.setattr(generate_pdf.subprocess, 'run', render)
    monkeypatch.setattr(sys, 'argv', ['generate_pdf.py', str(source), '--output', str(output),
                                     '--csl', 'apa', '--no-toc', '--no-numbers'])
    with pytest.raises(SystemExit) as exc:
        generate_pdf.main()
    assert exc.value.code == 0


def test_missing_csl_or_template_does_not_silently_ignore_request(tmp_path, monkeypatch):
    source = tmp_path / 'review.md'
    source.write_text('Text')
    monkeypatch.setattr(generate_pdf, 'check_dependencies', lambda: True)
    run = Mock()
    monkeypatch.setattr(generate_pdf.subprocess, 'run', run)
    assert not generate_pdf.generate_pdf(str(source), citation_style=str(tmp_path / 'absent.csl'))
    assert not generate_pdf.generate_pdf(str(source), template=str(tmp_path / 'absent.tex'))
    run.assert_not_called()


def test_dependency_check_exits_failure_when_tools_are_missing(monkeypatch):
    monkeypatch.setattr(generate_pdf, 'check_dependencies', lambda: False)
    monkeypatch.setattr(sys, 'argv', ['generate_pdf.py', '--check-deps'])
    with pytest.raises(SystemExit) as exc:
        generate_pdf.main()
    assert exc.value.code == 1
