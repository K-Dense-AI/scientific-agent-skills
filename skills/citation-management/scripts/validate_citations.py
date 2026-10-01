#!/usr/bin/env python3
"""
Citation Validation Tool
Validate BibTeX files for accuracy, completeness, and format compliance.
"""

import sys
import re
import requests
import argparse
import json
import time
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from urllib.parse import quote

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from _common import parse_bibtex_file as _parse_bibtex_file  # noqa: E402

# Typical reference-list lengths, as (minimum, typical maximum, display name).
#
# These are editorial rules of thumb drawn from what published papers at these
# venues tend to carry -- not sourced submission requirements, most of which do
# not cap references at all. They drive warnings only; a bibliography is never
# wrong merely for being short.
VENUE_STANDARDS = {
    'nature': (35, 50, 'Nature'),
    'science': (35, 50, 'Science'),
    'cell': (35, 50, 'Cell'),
    'multidisciplinary': (35, 50, 'High-impact Multidisciplinary Journal'),
    'neurips': (30, 45, 'NeurIPS'),
    'icml': (30, 45, 'ICML'),
    'iclr': (30, 45, 'ICLR'),
    'cvpr': (30, 45, 'CVPR'),
    'acl': (30, 45, 'ACL'),
    'ml_cs_conf': (30, 45, 'ML/CS Conference'),
    'review': (40, 65, 'Comprehensive Literature Review'),
    'market_research': (40, 65, 'Market Research Report'),
    'literature_review': (40, 65, 'Literature Review / Market Research'),
    'nejm': (30, 45, 'NEJM'),
    'lancet': (30, 45, 'The Lancet'),
    'jama': (30, 45, 'JAMA'),
    'medical': (30, 45, 'Medical Journal'),
}


class CitationValidator:
    """Validate BibTeX entries for errors and inconsistencies."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CitationValidator/1.0 (Citation Management Tool)'
        })
        self.venue_standards = VENUE_STANDARDS

        # Required fields by entry type
        self.required_fields = {
            'article': ['author', 'title', 'journal', 'year'],
            'book': ['title', 'publisher', 'year'],  # author OR editor
            'inproceedings': ['author', 'title', 'booktitle', 'year'],
            'incollection': ['author', 'title', 'booktitle', 'publisher', 'year'],
            'phdthesis': ['author', 'title', 'school', 'year'],
            'mastersthesis': ['author', 'title', 'school', 'year'],
            'techreport': ['author', 'title', 'institution', 'year'],
            'misc': ['title', 'year']
        }
        
        # Recommended fields
        self.recommended_fields = {
            'article': ['volume', 'pages', 'doi'],
            'book': ['isbn'],
            'inproceedings': ['pages'],
        }
    
    def parse_bibtex_file(self, filepath: str) -> List[Dict]:
        """
        Parse BibTeX file and extract entries.
        
        Args:
            filepath: Path to BibTeX file
            
        Returns:
            List of entry dictionaries
        """
        return _parse_bibtex_file(filepath)
    
    def validate_entry(self, entry: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        Validate a single BibTeX entry.
        
        Args:
            entry: Entry dictionary
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        entry_type = entry['type']
        key = entry['key']
        fields = entry['fields']
        
        # Check required fields
        if entry_type in self.required_fields:
            for req_field in self.required_fields[entry_type]:
                if req_field not in fields or not fields[req_field]:
                    # Special case: book can have author OR editor
                    if entry_type == 'book' and req_field == 'author':
                        if 'editor' not in fields or not fields['editor']:
                            errors.append({
                                'type': 'missing_required_field',
                                'field': 'author or editor',
                                'severity': 'high',
                                'message': f'Entry {key}: Missing required field "author" or "editor"'
                            })
                    else:
                        errors.append({
                            'type': 'missing_required_field',
                            'field': req_field,
                            'severity': 'high',
                            'message': f'Entry {key}: Missing required field "{req_field}"'
                        })
        
        # Check recommended fields
        if entry_type in self.recommended_fields:
            for rec_field in self.recommended_fields[entry_type]:
                if rec_field not in fields or not fields[rec_field]:
                    warnings.append({
                        'type': 'missing_recommended_field',
                        'field': rec_field,
                        'severity': 'medium',
                        'message': f'Entry {key}: Missing recommended field "{rec_field}"'
                    })
        
        # Validate year
        if 'year' in fields:
            year = fields['year']
            if not re.match(r'^\d{4}$', year):
                errors.append({
                    'type': 'invalid_year',
                    'field': 'year',
                    'value': year,
                    'severity': 'high',
                    'message': f'Entry {key}: Invalid year format "{year}" (should be 4 digits)'
                })
            elif int(year) < 1600 or int(year) > 2030:
                warnings.append({
                    'type': 'suspicious_year',
                    'field': 'year',
                    'value': year,
                    'severity': 'medium',
                    'message': f'Entry {key}: Suspicious year "{year}" (outside reasonable range)'
                })
        
        # Validate DOI format
        if 'doi' in fields:
            doi = fields['doi']
            if not re.match(r'^10\.\d{4,}/[^\s]+$', doi):
                warnings.append({
                    'type': 'invalid_doi_format',
                    'field': 'doi',
                    'value': doi,
                    'severity': 'medium',
                    'message': f'Entry {key}: Invalid DOI format "{doi}"'
                })
        
        # Check for single hyphen in pages (should be --)
        if 'pages' in fields:
            pages = fields['pages']
            if re.search(r'\d-\d', pages) and '--' not in pages:
                warnings.append({
                    'type': 'page_range_format',
                    'field': 'pages',
                    'value': pages,
                    'severity': 'low',
                    'message': f'Entry {key}: Page range uses single hyphen, should use -- (en-dash)'
                })
        
        # Check author format
        if 'author' in fields:
            author = fields['author']
            if ';' in author or '&' in author:
                errors.append({
                    'type': 'invalid_author_format',
                    'field': 'author',
                    'severity': 'high',
                    'message': f'Entry {key}: Authors should be separated by " and ", not ";" or "&"'
                })
        
        return errors, warnings
    
    def verify_doi(self, doi: str) -> Tuple[Optional[bool], Optional[Dict]]:
        """
        Verify DOI resolves correctly and get metadata.
        
        Args:
            doi: Digital Object Identifier
            
        Returns:
            (True, metadata) when registered, (False, None) on resolver 404,
            or (None, None) when the lookup could not be completed.
        """
        # Ask the registration agency, not the publisher. A HEAD request to
        # doi.org follows the redirect to the publisher, and several publishers
        # answer HEAD with 403 or 405 behind a bot check -- which made a
        # perfectly good DOI look unresolvable.
        try:
            time.sleep(0.21)  # Stay below Crossref's public single-record limit.
            crossref_url = f'https://api.crossref.org/works/{quote(doi, safe="")}'
            metadata_response = self.session.get(crossref_url, timeout=10)

            if metadata_response.status_code == 200:
                data = metadata_response.json()
                message = data.get('message', {})
                if not isinstance(message, dict) or str(message.get('DOI', '')).lower() != doi.lower():
                    return None, None

                # Extract key metadata
                metadata = {
                    'title': (message.get('title') or [''])[0],
                    'year': self._extract_year_crossref(message),
                    'authors': self._format_authors_crossref(message.get('author', [])),
                }
                return True, metadata

            if metadata_response.status_code == 404:
                # Not a Crossref DOI. DataCite registers datasets and many
                # preprints, so check there before calling it broken.
                datacite_url = f'https://api.datacite.org/dois/{quote(doi, safe="")}'
                datacite_response = self.session.get(datacite_url, timeout=10)
                if datacite_response.status_code == 200:
                    record = datacite_response.json().get('data', {})
                    if str(record.get('id', '')).lower() == doi.lower():
                        return True, None
                    return None, None
                if datacite_response.status_code != 404:
                    return None, None
                # Other agencies mint DOIs too. Check the resolver itself,
                # without following publishers' bot-blocked landing pages.
                resolver = self.session.get(f'https://doi.org/{quote(doi, safe="/")}',
                                            allow_redirects=False, timeout=10)
                if resolver.status_code == 404:
                    return False, None
                if resolver.status_code in (301, 302, 303, 307, 308) and resolver.headers.get('Location'):
                    return True, None
                return None, None

            # Any other status is a transport problem on our side, not
            # evidence that the DOI is bad.
            return None, None

        except (requests.exceptions.RequestException, ValueError, TypeError, AttributeError):
            return None, None
    
    def detect_duplicates(self, entries: List[Dict]) -> List[Dict]:
        """
        Detect duplicate entries.
        
        Args:
            entries: List of entry dictionaries
            
        Returns:
            List of duplicate groups
        """
        duplicates = []
        
        # Check for duplicate DOIs
        doi_map = defaultdict(list)
        for entry in entries:
            doi = entry['fields'].get('doi', '').strip()
            if doi:
                doi_map[doi].append(entry['key'])
        
        for doi, keys in doi_map.items():
            if len(keys) > 1:
                duplicates.append({
                    'type': 'duplicate_doi',
                    'doi': doi,
                    'entries': keys,
                    'severity': 'high',
                    'message': f'Duplicate DOI {doi} found in entries: {", ".join(keys)}'
                })
        
        # Check for duplicate citation keys
        key_counts = defaultdict(int)
        for entry in entries:
            key_counts[entry['key']] += 1
        
        for key, count in key_counts.items():
            if count > 1:
                duplicates.append({
                    'type': 'duplicate_key',
                    'key': key,
                    'count': count,
                    'severity': 'high',
                    'message': f'Citation key "{key}" appears {count} times'
                })
        
        # Check for similar titles (possible duplicates)
        titles = {}
        for entry in entries:
            title = entry['fields'].get('title', '').lower()
            title = re.sub(r'[^\w\s]', '', title)  # Remove punctuation
            title = ' '.join(title.split())  # Normalize whitespace
            
            if title:
                if title in titles:
                    duplicates.append({
                        'type': 'similar_title',
                        'entries': [titles[title], entry['key']],
                        'severity': 'medium',
                        'message': f'Possible duplicate: "{titles[title]}" and "{entry["key"]}" have identical titles'
                    })
                else:
                    titles[title] = entry['key']
        
        return duplicates
    
    def parse_manuscript_citations(self, filepath: str) -> List[str]:
        """
        Parse a manuscript file (Markdown or LaTeX) and extract all cited keys.
        
        Args:
            filepath: Path to manuscript file
            
        Returns:
            List of cited citation keys
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f'Error reading manuscript file {filepath}: {e}', file=sys.stderr)
            return []
        
        cited_keys = set()
        
        # 1. LaTeX citations: \cite{key1, key2}, \citep{key}, \citet{key}, etc.
        latex_matches = re.findall(r'\\cite[a-z]*\*?\{([^}]+)\}', content)
        for match in latex_matches:
            keys = [k.strip() for k in match.split(',')]
            for key in keys:
                if key:
                    cited_keys.add(key)
                    
        # 2. Markdown / Pandoc citations: @key or [@key1; @key2]
        # Match @ followed by valid citation key chars (alphanumeric, -, _, :, .)
        # Avoid email addresses, twitter handles, etc. by requiring that @ is not preceded by alphanumeric/dot/dash/underscore
        md_matches = re.findall(r'(?<![a-zA-Z0-9_.-])@([a-zA-Z0-9_\-:]+)', content)
        for key in md_matches:
            # Exclude common false positives
            if key and not key.isdigit():
                cited_keys.add(key)
                
        return list(cited_keys)

    def validate_file(self, filepath: str, check_dois: bool = False, min_count: Optional[int] = None, venue: Optional[str] = None, manuscript_filepath: Optional[str] = None) -> Dict:
        """
        Validate entire BibTeX file.
        
        Args:
            filepath: Path to BibTeX file
            check_dois: Whether to verify DOIs (slow)
            min_count: Optional minimum citation count to enforce
            venue: Optional venue type to check against standards
            manuscript_filepath: Optional path to manuscript to cross-check citations
            
        Returns:
            Validation report dictionary
        """
        print(f'Parsing {filepath}...', file=sys.stderr)
        entries = self.parse_bibtex_file(filepath)
        
        if not entries:
            return {
                'filepath': filepath,
                'total_entries': 0,
                'valid_entries': 0,
                'errors': [{
                    'type': 'empty_bibtex_file',
                    'severity': 'high',
                    'message': f'BibTeX file {filepath} has no valid entries.'
                }],
                'warnings': [],
                'duplicates': [],
                'venue_standard_checked': venue,
                'min_count_checked': min_count,
                'manuscript_results': {'checked': False}
            }
        
        print(f'Found {len(entries)} entries', file=sys.stderr)
        
        all_errors = []
        all_warnings = []
        
        # Validate each entry
        for i, entry in enumerate(entries):
            print(f'Validating entry {i+1}/{len(entries)}: {entry["key"]}', file=sys.stderr)
            errors, warnings = self.validate_entry(entry)
            
            for error in errors:
                error['entry'] = entry['key']
                all_errors.append(error)
            
            for warning in warnings:
                warning['entry'] = entry['key']
                all_warnings.append(warning)
        
        # Check for duplicates
        print('Checking for duplicates...', file=sys.stderr)
        duplicates = self.detect_duplicates(entries)
        
        # Verify DOIs if requested
        doi_errors = []
        if check_dois:
            print('Verifying DOIs...', file=sys.stderr)
            for i, entry in enumerate(entries):
                doi = entry['fields'].get('doi', '')
                if doi:
                    print(f'Verifying DOI {i+1}: {doi}', file=sys.stderr)
                    is_valid, metadata = self.verify_doi(doi)
                    
                    if is_valid is None:
                        all_warnings.append({
                            'type': 'doi_unverified',
                            'entry': entry['key'],
                            'doi': doi,
                            'severity': 'medium',
                            'message': f'Entry {entry["key"]}: DOI lookup inconclusive; retry or verify manually: {doi}'
                        })
                    elif is_valid is False:
                        doi_errors.append({
                            'type': 'invalid_doi',
                            'entry': entry['key'],
                            'doi': doi,
                            'severity': 'high',
                            'message': f'Entry {entry["key"]}: DOI does not resolve: {doi}'
                        })
        
        all_errors.extend(doi_errors)
        
        # Count and Venue verification logic
        count_errors = []
        count_warnings = []

        target_min = None
        target_max = None
        venue_name = None

        if venue:
            v_lower = venue.lower().strip()
            if v_lower in self.venue_standards:
                target_min, target_max, venue_name = self.venue_standards[v_lower]
            else:
                print(f"Warning: Unknown venue '{venue}'. Supported venues are: {', '.join(self.venue_standards.keys())}", file=sys.stderr)
        
        if min_count is not None:
            target_min = min_count
            venue_name = f"Custom threshold (min: {min_count})"
            target_max = None
            
        # A reference list is never *wrong* for being short -- the right length
        # is whatever the argument needs -- so a shortfall is reported as a
        # warning. `--min-count` is the exception: an explicit floor the caller
        # asked to have enforced, so falling under it is an error.
        total_count = len(entries)
        if target_min is not None:
            if min_count is not None and total_count < min_count:
                count_errors.append({
                    'type': 'below_requested_minimum',
                    'severity': 'high',
                    'message': f'Total citation entries ({total_count}) is below the requested minimum of {min_count}.'
                })
            elif total_count < target_min:
                count_warnings.append({
                    'type': 'low_citation_count',
                    'severity': 'medium',
                    'message': f'Total citation entries ({total_count}) is below the {venue_name or "specified standard"} rule of thumb of {target_min}-{target_max or "+"}. This is a heuristic, not a submission requirement.'
                })

        # Manuscript checking logic
        manuscript_results = {
            'checked': False,
            'manuscript_filepath': None,
            'cited_keys': [],
            'missing_keys': [],
            'unused_keys': []
        }
        
        if manuscript_filepath:
            manuscript_results['checked'] = True
            manuscript_results['manuscript_filepath'] = manuscript_filepath
            
            # Parse cited keys
            cited_keys = self.parse_manuscript_citations(manuscript_filepath)
            manuscript_results['cited_keys'] = cited_keys
            
            bib_keys = {entry['key'] for entry in entries}
            
            # Missing references: cited in manuscript but not defined in BibTeX
            missing_keys = [key for key in cited_keys if key not in bib_keys]
            manuscript_results['missing_keys'] = missing_keys
            for key in missing_keys:
                all_errors.append({
                    'type': 'unresolved_citation',
                    'entry': key,
                    'severity': 'high',
                    'message': f'Unresolved citation: Key "@{key}" is cited in manuscript "{manuscript_filepath}" but not defined in the BibTeX file.'
                })
                
            # Unused references: defined in BibTeX but not cited in manuscript
            unused_keys = [key for key in bib_keys if key not in cited_keys]
            manuscript_results['unused_keys'] = unused_keys
            for key in unused_keys:
                all_warnings.append({
                    'type': 'unused_citation',
                    'entry': key,
                    'severity': 'medium',
                    'message': f'Unused citation: Reference "{key}" is defined in the BibTeX file but not cited in the manuscript.'
                })
                
            # Check the count of ACTUALLY used citations
            actual_count = len(cited_keys) - len(missing_keys)
            if target_min is not None:
                if min_count is not None and actual_count < min_count:
                    count_errors.append({
                        'type': 'manuscript_below_requested_minimum',
                        'severity': 'high',
                        'message': f'The manuscript cites {actual_count} references, below the requested minimum of {min_count}.'
                    })
                elif actual_count < target_min:
                    count_warnings.append({
                        'type': 'low_manuscript_citation_count',
                        'severity': 'medium',
                        'message': f'The manuscript cites {actual_count} references, below the {venue_name or "specified standard"} rule of thumb of {target_min}-{target_max or "+"}. This is a heuristic, not a submission requirement.'
                    })

        all_errors.extend(count_errors)
        all_warnings.extend(count_warnings)

        # Count entries carrying at least one high-severity error, rather than
        # subtracting the error count -- several errors can land on one entry,
        # which previously drove this figure negative.
        entries_with_errors = {
            error['entry'] for error in all_errors
            if error.get('severity') == 'high' and error.get('entry')
        }
        bib_keys_present = {entry['key'] for entry in entries}

        return {
            'filepath': filepath,
            'total_entries': len(entries),
            'valid_entries': len(entries) - len(entries_with_errors & bib_keys_present),
            'errors': all_errors,
            'warnings': all_warnings,
            'duplicates': duplicates,
            'venue_standard_checked': venue,
            'min_count_checked': min_count,
            'manuscript_results': manuscript_results
        }
    
    def _extract_year_crossref(self, message: Dict) -> str:
        """Extract year from CrossRef message."""
        date_parts = message.get('published-print', {}).get('date-parts', [[]])
        if not date_parts or not date_parts[0]:
            date_parts = message.get('published-online', {}).get('date-parts', [[]])
        
        if date_parts and date_parts[0]:
            return str(date_parts[0][0])
        return ''
    
    def _format_authors_crossref(self, authors: List[Dict]) -> str:
        """Format author list from CrossRef."""
        if not authors:
            return ''
        
        formatted = []
        for author in authors[:3]:  # First 3 authors
            given = author.get('given', '')
            family = author.get('family', '')
            if family:
                formatted.append(f'{family}, {given}' if given else family)
        
        if len(authors) > 3:
            formatted.append('et al.')
        
        return ', '.join(formatted)


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description='Validate BibTeX files for errors and inconsistencies',
        epilog='Example: python validate_citations.py references.bib'
    )
    
    parser.add_argument(
        'file',
        help='BibTeX file to validate'
    )
    
    parser.add_argument(
        '--check-dois',
        action='store_true',
        help='Verify DOIs resolve correctly (slow)'
    )
    
    parser.add_argument(
        '--report',
        help='Output file for the JSON validation report'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output'
    )
    
    parser.add_argument(
        '--min-count',
        type=int,
        help='Enforce a minimum number of citation entries'
    )
    
    parser.add_argument(
        '--venue',
        help='Enforce citation standards for a specific venue (e.g. nature, neurips, review)'
    )
    
    parser.add_argument(
        '--manuscript',
        help='Path to manuscript file (Markdown or LaTeX) to check for unresolved or unused citations'
    )
    
    args = parser.parse_args()
    
    # Validate file
    validator = CitationValidator()
    report = validator.validate_file(
        args.file, 
        check_dois=args.check_dois,
        min_count=args.min_count,
        venue=args.venue,
        manuscript_filepath=args.manuscript
    )
    
    # Print summary
    print('\n' + '='*60)
    print('CITATION VALIDATION REPORT')
    print('='*60)
    print(f'\nFile: {args.file}')
    if report.get('venue_standard_checked'):
        print(f'Venue Standard: {report["venue_standard_checked"]}')
    if report.get('min_count_checked') is not None:
        print(f'Required Min Count: {report["min_count_checked"]}')
    print(f'Total entries in BibTeX: {report["total_entries"]}')
    
    m_res = report.get('manuscript_results', {})
    if m_res.get('checked'):
        print(f'Manuscript checked: {m_res["manuscript_filepath"]}')
        print(f'  Actual unique citations in manuscript: {len(m_res["cited_keys"])}')
        print(f'  Missing/unresolved: {len(m_res["missing_keys"])}')
        print(f'  Unused in bib file: {len(m_res["unused_keys"])}')
        
    print(f'Valid entries: {report["valid_entries"]}')
    print(f'Errors: {len(report["errors"])}')
    print(f'Warnings: {len(report["warnings"])}')
    print(f'Duplicates: {len(report["duplicates"])}')
    
    # Print errors
    if report['errors']:
        print('\n' + '-'*60)
        print('ERRORS (must fix):')
        print('-'*60)
        for error in report['errors']:
            print(f'\n{error["message"]}')
            if args.verbose:
                print(f'  Type: {error["type"]}')
                print(f'  Severity: {error["severity"]}')
    
    # Print warnings
    if report['warnings'] and (args.verbose or report.get('venue_standard_checked') or report.get('min_count_checked') is not None or m_res.get('checked')):
        print('\n' + '-'*60)
        print('WARNINGS (should fix):')
        print('-'*60)
        for warning in report['warnings']:
            print(f'\n{warning["message"]}')
    
    # Print duplicates
    if report['duplicates']:
        print('\n' + '-'*60)
        print('DUPLICATES:')
        print('-'*60)
        for dup in report['duplicates']:
            print(f'\n{dup["message"]}')
    
    # Save report
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f'\nDetailed report saved to: {args.report}')
    
    # Exit with error code if there are high-severity errors
    has_high_errors = any(e.get('severity') == 'high' for e in report['errors'])
    if has_high_errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
