#!/usr/bin/env python3
"""Check DOI registration and retrieve Crossref metadata for manual citation review.

Registration does not establish that a citation supports a claim. Crossref does
not cover all DOI registration agencies; unavailable metadata needs manual review.
"""

import argparse
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import quote, unquote

import requests


def normalize_doi(value: str) -> str:
    """Normalize a bare DOI or doi.org URL without stripping legal DOI punctuation."""
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I)
    return unquote(value).lower()


class CitationVerifier:
    def __init__(self, email: str = None):
        self.email = email
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'LiteratureReviewCitationVerifier/1.1'})

    def extract_dois(self, text: str) -> List[str]:
        """Extract unique candidates; prose punctuation remains inherently ambiguous."""
        found = []
        for candidate in re.findall(r'10\.\d{4,9}/[^\s<>"{}]+', text, flags=re.I):
            candidate = unquote(candidate).rstrip('.,;:')
            # Keep balanced parentheses inside older DOI suffixes, remove Markdown closers.
            while candidate and candidate[-1] in ')]':
                closing = candidate[-1]
                opening = '(' if closing == ')' else '['
                if candidate.count(closing) <= candidate.count(opening):
                    break
                candidate = candidate[:-1].rstrip('.,;:')
            candidate = normalize_doi(candidate)
            if candidate not in found:
                found.append(candidate)
        return found

    def _get(self, url: str, **kwargs):
        """Retry only transient read failures, with bounded backoff."""
        for attempt in range(3):
            response = self.session.get(url, timeout=20, **kwargs)
            if response.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                return response
            try:
                delay = float(response.headers.get('Retry-After', 2 ** attempt))
            except (TypeError, ValueError):
                delay = 2 ** attempt
            # Long server-directed delays need a later run, not an early retry.
            if delay > 60:
                return response
            time.sleep(max(0, delay))
        raise AssertionError('unreachable')

    def verify_doi(self, doi: str) -> Tuple[bool, Dict]:
        """Return registration status and metadata; false includes inconclusive requests."""
        doi = normalize_doi(doi)
        if not re.fullmatch(r'10\.\d{4,9}/\S+', doi):
            return False, {'doi': doi, 'status': 'invalid_syntax'}
        try:
            response = self._get(f"https://doi.org/api/handles/{quote(doi, safe='/')}")
            payload = response.json()
            code = payload.get('responseCode') if isinstance(payload, dict) else None
            returned = payload.get('handle', '') if isinstance(payload, dict) else ''
            if (code == 100 and response.status_code in (200, 404) and
                    isinstance(returned, str) and normalize_doi(returned) == doi):
                return False, {'doi': doi, 'status': 'missing', 'handle_response_code': code}
            if (response.status_code != 200 or code != 1 or
                    not isinstance(returned, str) or normalize_doi(returned) != doi):
                return False, {'doi': doi, 'status': 'inconclusive',
                               'http_status': response.status_code, 'handle_response_code': code}
            metadata = self._get_crossref_metadata(doi)
            metadata.update({'doi': doi, 'status': 'registered'})
            return True, metadata
        except (requests.RequestException, ValueError) as exc:
            return False, {'doi': doi, 'status': 'inconclusive', 'error': str(exc)}

    def _get_crossref_metadata(self, doi: str) -> Dict:
        """Fetch one Crossref work; no list pagination or key is needed."""
        try:
            response = self._get(f"https://api.crossref.org/works/{quote(doi, safe='/')}",
                                 params={'mailto': self.email} if self.email else {})
            if response.status_code != 200:
                return {'metadata_status': 'unavailable', 'crossref_http_status': response.status_code}
            message = response.json().get('message')
            if not isinstance(message, dict) or normalize_doi(message.get('DOI', '')) != doi:
                return {'metadata_status': 'unavailable', 'error': 'Crossref response DOI missing or mismatched'}
            def first(field):
                values = message.get(field) or []
                return values[0] if isinstance(values, list) and values else ''
            authors = message.get('author') or []
            return {
                'metadata_status': 'retrieved', 'title': first('title'),
                'authors': self._format_authors(authors), 'author': authors,
                'year': self._extract_year(message), 'journal': first('container-title'),
                'volume': message.get('volume', ''), 'issue': message.get('issue', ''),
                'pages': message.get('page', ''), 'doi': doi,
                'crossref_message': message,
            }
        except (requests.RequestException, ValueError, AttributeError) as exc:
            return {'metadata_status': 'unavailable', 'error': str(exc)}

    def _format_authors(self, authors: List[Dict]) -> str:
        """Preserve all authors for review; this is not a CSL citation formatter."""
        names = []
        for author in authors:
            if not isinstance(author, dict):
                continue
            family, given = author.get('family', ''), author.get('given', '')
            if family:
                names.append(f'{family}, {given}' if given else family)
            elif author.get('name'):
                names.append(author['name'])
        return '; '.join(names)

    def _extract_year(self, message: Dict) -> str:
        for field in ('published-print', 'published-online', 'published', 'issued'):
            dates = (message.get(field) or {}).get('date-parts') or []
            if dates and dates[0]:
                return str(dates[0][0])
        return ''

    def verify_url(self, url: str) -> Tuple[bool, int]:
        """Check accessibility only; a 403/HEAD failure is not proof of an invalid URL."""
        try:
            response = self.session.head(url, timeout=20, allow_redirects=True)
            return response.status_code < 400, response.status_code
        except requests.RequestException:
            return False, 0

    def verify_citations_in_file(self, filepath: str) -> Dict:
        dois = self.extract_dois(Path(filepath).read_text(encoding='utf-8'))
        report = {'total_dois': len(dois), 'verified': [], 'failed': [],
                  'metadata_unavailable': [], 'metadata': {}, 'errors': {}, 'missing': [], 'inconclusive': [],
                  'verification_scope': 'DOI registration and Crossref metadata, not claim support or retraction screening'}
        for doi in dois:
            print(f'Checking DOI: {doi}')
            registered, metadata = self.verify_doi(doi)
            if registered:
                report['verified'].append(doi)
                report['metadata'][doi] = metadata
                if metadata.get('metadata_status') != 'retrieved':
                    report['metadata_unavailable'].append(doi)
            else:
                report['failed'].append(doi)
                report['errors'][doi] = metadata
                bucket = 'missing' if metadata.get('status') == 'missing' else 'inconclusive'
                report[bucket].append(doi)
            time.sleep(0.5)  # Sequential, <=2 Crossref single-work requests/s.
        return report

    def format_citation_apa(self, metadata: Dict) -> str:
        """Return a metadata preview, not a standards-compliant APA reference."""
        return (f"{metadata.get('authors', '')} ({metadata.get('year') or 'n.d.'}). "
                f"{metadata.get('title', '')}. {metadata.get('journal', '')}. "
                f"https://doi.org/{metadata.get('doi', '')}")

    def format_citation_nature(self, metadata: Dict) -> str:
        """Return a metadata preview; use CSL for final Nature formatting."""
        return (f"{metadata.get('authors', '')} {metadata.get('title', '')}. "
                f"{metadata.get('journal', '')} {metadata.get('volume', '')}, "
                f"{metadata.get('pages', '')} ({metadata.get('year', '')}).")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('markdown_file', type=Path)
    parser.add_argument('--email', help='Your contact email for the Crossref polite pool')
    parser.add_argument('-o', '--output', type=Path, help='JSON report path')
    args = parser.parse_args()
    output = args.output or args.markdown_file.with_name(args.markdown_file.stem + '_citation_report.json')
    if output.resolve() == args.markdown_file.resolve():
        parser.error('report path must differ from the input file')
    try:
        verifier = CitationVerifier(email=args.email)
        report = verifier.verify_citations_in_file(str(args.markdown_file))
        output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    except (OSError, ValueError) as exc:
        parser.exit(1, f'[FAIL] {exc}\n')
    print(f"Registered: {len(report['verified'])}; unresolved: {len(report['failed'])}; "
          f"metadata unavailable: {len(report['metadata_unavailable'])}")
    print(f'[OK] Report: {output}')
    if not report['total_dois']:
        print('[WARN] No DOIs found; review references manually.')
    raise SystemExit(1 if report['failed'] else 0)


if __name__ == '__main__':
    main()
