#!/usr/bin/env python3
"""
Google Scholar Search Tool
Search Google Scholar and export results.

Note: This script requires the 'scholarly' library.
Install with: uv pip install scholarly
"""

import sys
import argparse
import json
import time
import random
from typing import List, Dict, Optional
from itertools import islice

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    citation_key,
    protect_title,
    render_entry,
)

try:
    from scholarly import scholarly, ProxyGenerator
    SCHOLARLY_AVAILABLE = True
except ImportError:
    SCHOLARLY_AVAILABLE = False
    print('Warning: scholarly library not installed. Install with: uv pip install scholarly', file=sys.stderr)

class GoogleScholarSearcher:
    """Search Google Scholar using scholarly library."""
    
    def __init__(self, use_proxy: bool = False):
        """
        Initialize searcher.
        
        Args:
            use_proxy: Use an optional scholarly proxy provider (does not authorize bypassing blocks)
        """
        if not SCHOLARLY_AVAILABLE:
            raise ImportError('scholarly library required. Install with: uv pip install scholarly')
        
        # Setup proxy if requested
        if use_proxy:
            try:
                pg = ProxyGenerator()
                pg.FreeProxies()
                scholarly.use_proxy(pg)
                print('Using free proxy', file=sys.stderr)
            except Exception as e:
                print(f'Warning: Could not setup proxy: {e}', file=sys.stderr)
    
    def search(self, query: str, max_results: int = 50,
               year_start: Optional[int] = None, year_end: Optional[int] = None,
               sort_by: str = 'relevance') -> List[Dict]:
        """
        Search Google Scholar.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            year_start: Start year filter
            year_end: End year filter
            sort_by: Sort order ('relevance' or 'citations')
            
        Returns:
            List of result dictionaries
        """
        if not SCHOLARLY_AVAILABLE:
            print('Error: scholarly library not installed', file=sys.stderr)
            return []
        
        print(f'Searching Google Scholar: {query}', file=sys.stderr)
        print(f'Max results: {max_results}', file=sys.stderr)
        
        results = []
        
        try:
            # Perform search
            search_query = scholarly.search_pubs(query, year_low=year_start, year_high=year_end)
            
            for i, result in enumerate(islice(search_query, max_results)):
                
                print(f'Retrieved {i+1}/{max_results}', file=sys.stderr)
                
                # Extract metadata
                metadata = {
                    'title': result.get('bib', {}).get('title', ''),
                    'authors': ' and '.join(result.get('bib', {}).get('author', [])),
                    'year': result.get('bib', {}).get('pub_year', ''),
                    'venue': result.get('bib', {}).get('venue', ''),
                    'abstract': result.get('bib', {}).get('abstract', ''),
                    'citations': result.get('num_citations', 0),
                    'url': result.get('pub_url', ''),
                    'eprint_url': result.get('eprint_url', ''),
                }
                
                # Filter by year
                if year_start or year_end:
                    try:
                        pub_year = int(metadata['year']) if metadata['year'] else 0
                        if year_start and pub_year < year_start:
                            continue
                        if year_end and pub_year > year_end:
                            continue
                    except ValueError:
                        pass
                
                results.append(metadata)
                
                # Rate limiting to avoid blocking
                time.sleep(random.uniform(2, 5))
            
        except Exception as e:
            print(f'Error during search: {e}', file=sys.stderr)
            return []  # A blocked or failed iterator is not a complete search.
        
        # Sort if requested
        if sort_by == 'citations' and results:
            results.sort(key=lambda x: x.get('citations', 0), reverse=True)
        
        return results
    
    def metadata_to_bibtex(self, metadata: Dict) -> str:
        """Convert metadata to BibTeX format.

        Scholar records carry no DOI and an unstructured venue string, so an
        entry built from one is a starting point: run it through the metadata
        enrichment pass before citing it.
        """
        authors = metadata.get('authors', '')

        key = citation_key(authors, metadata.get('year', ''), metadata.get('title', ''))

        # Determine entry type (guess based on venue)
        venue = metadata.get('venue', '').lower()
        if 'proceedings' in venue or 'conference' in venue or 'symposium' in venue:
            entry_type = 'inproceedings'
            venue_field = 'booktitle'
        else:
            entry_type = 'article'
            venue_field = 'journal'

        fields = {
            'author': authors,
            'title': protect_title(metadata.get('title', '')),
            venue_field: metadata.get('venue', ''),
            'year': metadata.get('year', ''),
            'url': metadata.get('url', ''),
        }

        # The citation count deliberately does not go in the `.bib`: it changes
        # every week, and baking it into a bibliography makes the file wrong
        # the moment it is written. It stays in the JSON output instead.

        return render_entry(entry_type, key, fields)


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description='Search Google Scholar (requires scholarly library)',
        epilog='Example: python search_google_scholar.py "machine learning" --limit 50'
    )
    
    parser.add_argument(
        'query',
        help='Search query'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Maximum number of results (default: 50)'
    )
    
    parser.add_argument(
        '--year-start',
        type=int,
        help='Start year for filtering'
    )
    
    parser.add_argument(
        '--year-end',
        type=int,
        help='End year for filtering'
    )
    
    parser.add_argument(
        '--sort-by',
        choices=['relevance', 'citations'],
        default='relevance',
        help='Order within retrieved results; citations is a local sort (default: relevance)'
    )
    
    parser.add_argument(
        '--use-proxy',
        action='store_true',
        help='Use scholarly free-proxy support; respect upstream access restrictions'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file (default: stdout)'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'bibtex'],
        default='json',
        help='Output format (default: json)'
    )
    
    args = parser.parse_args()
    if args.limit < 1:
        parser.error('--limit must be positive')
    
    if not SCHOLARLY_AVAILABLE:
        print('\nError: scholarly library not installed', file=sys.stderr)
        print('Install with: uv pip install scholarly', file=sys.stderr)
        print('\nAlternatively, use PubMed search for biomedical literature:', file=sys.stderr)
        print('  python search_pubmed.py "your query"', file=sys.stderr)
        sys.exit(1)
    
    # Search
    searcher = GoogleScholarSearcher(use_proxy=args.use_proxy)
    results = searcher.search(
        args.query,
        max_results=args.limit,
        year_start=args.year_start,
        year_end=args.year_end,
        sort_by=args.sort_by
    )
    
    if not results:
        print('No results found', file=sys.stderr)
        sys.exit(1)
    
    # Format output
    if args.format == 'json':
        output = json.dumps({
            'query': args.query,
            'count': len(results),
            'results': results
        }, indent=2)
    else:  # bibtex
        bibtex_entries = [searcher.metadata_to_bibtex(r) for r in results]
        output = '\n\n'.join(bibtex_entries) + '\n'
    
    # Write output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f'Wrote {len(results)} results to {args.output}', file=sys.stderr)
    else:
        print(output)
    
    print(f'\nRetrieved {len(results)} results', file=sys.stderr)


if __name__ == '__main__':
    main()
