#!/usr/bin/env python3
"""
DOI to BibTeX Converter
Convert DOIs to BibTeX through DOI content negotiation (Crossref/DataCite/mEDRA).
"""

import sys
import requests
import argparse
import time
import json
import re
from typing import Optional, List
from urllib.parse import quote, unquote

from _common import citation_key, parse_bibtex, render_entry

class DOIConverter:
    """Convert DOIs to BibTeX through their registration agency."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DOIConverter/1.0 (Citation Management Tool)'
        })
    
    def doi_to_bibtex(self, doi: str) -> Optional[str]:
        """
        Convert a single DOI to BibTeX format.
        
        Args:
            doi: Digital Object Identifier
            
        Returns:
            BibTeX string or None if conversion fails
        """
        # Clean DOI (remove URL prefix if present)
        doi = doi.strip()
        if re.match(r'^https?://(?:dx\.)?doi\.org/', doi, re.IGNORECASE):
            doi = unquote(re.sub(r'^https?://(?:dx\.)?doi\.org/', '', doi, flags=re.IGNORECASE))
        doi = re.sub(r'^doi:\s*', '', doi, flags=re.IGNORECASE)
        
        # Request BibTeX from CrossRef content negotiation
        url = f'https://doi.org/{quote(doi, safe="/")}'
        headers = {
            'Accept': 'application/x-bibtex',
            'User-Agent': 'DOIConverter/1.0 (Citation Management Tool)'
        }
        
        try:
            response = self.session.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                bibtex = response.text.strip()
                entries = parse_bibtex(bibtex)
                if len(entries) != 1:
                    print(f'Error: DOI service returned no single BibTeX entry for {doi}', file=sys.stderr)
                    return None
                entry = entries[0]
                fields = entry['fields']
                key = citation_key(fields.get('author', ''), fields.get('year', ''), fields.get('title', ''))
                entry_type = 'misc' if entry['type'] in ('data', 'dataset') else entry['type']
                return render_entry(entry_type, key, fields)
            elif response.status_code == 404:
                print(f'Error: DOI not found: {doi}', file=sys.stderr)
                return None
            else:
                print(f'Error: Failed to retrieve BibTeX for {doi} (status {response.status_code})', file=sys.stderr)
                return None
                
        except requests.exceptions.Timeout:
            print(f'Error: Request timeout for DOI: {doi}', file=sys.stderr)
            return None
        except requests.exceptions.RequestException as e:
            print(f'Error: Request failed for {doi}: {e}', file=sys.stderr)
            return None
    
    def convert_multiple(self, dois: List[str], delay: float = 0.5) -> List[str]:
        """
        Convert multiple DOIs to BibTeX.
        
        Args:
            dois: List of DOIs
            delay: Delay between requests (seconds) for rate limiting
            
        Returns:
            List of BibTeX entries (excludes failed conversions)
        """
        bibtex_entries = []
        
        for i, doi in enumerate(dois):
            print(f'Converting DOI {i+1}/{len(dois)}: {doi}', file=sys.stderr)
            bibtex = self.doi_to_bibtex(doi)
            
            if bibtex:
                bibtex_entries.append(bibtex)
            
            # Rate limiting
            if i < len(dois) - 1:  # Don't delay after last request
                time.sleep(delay)
        
        return bibtex_entries


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description='Convert DOIs to BibTeX using DOI content negotiation',
        epilog='Example: python doi_to_bibtex.py 10.1038/s41586-021-03819-2'
    )
    
    parser.add_argument(
        'dois',
        nargs='*',
        help='DOI(s) to convert (can provide multiple)'
    )
    
    parser.add_argument(
        '-i', '--input',
        help='Input file with DOIs (one per line)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file for BibTeX (default: stdout)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Delay between requests in seconds (default: 0.5)'
    )
    
    parser.add_argument(
        '--format',
        choices=['bibtex', 'json'],
        default='bibtex',
        help='Output format (default: bibtex)'
    )
    
    args = parser.parse_args()
    
    # Collect DOIs from command line and/or file
    dois = []
    
    if args.dois:
        dois.extend(args.dois)
    
    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                file_dois = [line.strip() for line in f if line.strip()]
                dois.extend(file_dois)
        except FileNotFoundError:
            print(f'Error: Input file not found: {args.input}', file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f'Error reading input file: {e}', file=sys.stderr)
            sys.exit(1)
    
    if not dois:
        parser.print_help()
        sys.exit(1)
    
    # Convert DOIs
    converter = DOIConverter()
    
    if len(dois) == 1:
        bibtex = converter.doi_to_bibtex(dois[0])
        if bibtex:
            bibtex_entries = [bibtex]
        else:
            sys.exit(1)
    else:
        bibtex_entries = converter.convert_multiple(dois, delay=args.delay)
    
    if not bibtex_entries:
        print('Error: No successful conversions', file=sys.stderr)
        sys.exit(1)
    
    # Format output
    if args.format == 'bibtex':
        output = '\n\n'.join(bibtex_entries) + '\n'
    else:  # json
        output = json.dumps({
            'count': len(bibtex_entries),
            'entries': bibtex_entries
        }, indent=2)
    
    # Write output
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f'Successfully wrote {len(bibtex_entries)} entries to {args.output}', file=sys.stderr)
        except Exception as e:
            print(f'Error writing output file: {e}', file=sys.stderr)
            sys.exit(1)
    else:
        print(output)
    
    # Summary
    if len(dois) > 1:
        success_rate = len(bibtex_entries) / len(dois) * 100
        print(f'\nConverted {len(bibtex_entries)}/{len(dois)} DOIs ({success_rate:.1f}%)', file=sys.stderr)
        if len(bibtex_entries) < len(dois):
            sys.exit(2)


if __name__ == '__main__':
    main()
