#!/usr/bin/env python3
"""
PubMed Search Tool
Search PubMed using E-utilities API and export results.
"""

import sys
import os
import re
import requests
import argparse
import json
import time
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    citation_key,
    format_pages,
    protect_title,
    render_entry,
)

class PubMedSearcher:
    """Search PubMed using NCBI E-utilities API."""
    
    def __init__(self, api_key: Optional[str] = None, email: Optional[str] = None):
        """
        Initialize searcher.
        
        Args:
            api_key: NCBI API key (optional but recommended)
            email: Email for Entrez (optional but recommended)
        """
        self.api_key = api_key or os.getenv('NCBI_API_KEY', '')
        self.email = email or os.getenv('NCBI_EMAIL', '')
        self.base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        self.session = requests.Session()
        
        # Rate limiting
        self.delay = 0.11 if self.api_key else 0.34  # 10/sec with key, 3/sec without
    
    def search(self, query: str, max_results: int = 100,
               date_start: Optional[str] = None, date_end: Optional[str] = None,
               publication_types: Optional[List[str]] = None) -> List[str]:
        """
        Search PubMed and return PMIDs.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            date_start: Start date (YYYY/MM/DD or YYYY)
            date_end: End date (YYYY/MM/DD or YYYY)
            publication_types: List of publication types to filter
            
        Returns:
            List of PMIDs
        """
        # Build query with filters
        if max_results < 1:
            raise ValueError('max_results must be positive')
        full_query = f'({query})'
        
        # Add date range
        if date_start or date_end:
            start = (date_start or '1900').replace('-', '/')
            end = (date_end or datetime.now().strftime('%Y')).replace('-', '/')
            full_query += f' AND {start}:{end}[Publication Date]'
        
        # Add publication types
        if publication_types:
            pub_type_query = ' OR '.join([f'"{pt}"[Publication Type]' for pt in publication_types])
            full_query += f' AND ({pub_type_query})'
        
        print(f'Searching PubMed: {full_query}', file=sys.stderr)

        # PubMed ESearch exposes only the first 10000 matches in total,
        # so say so rather than letting the caller believe they got everything.
        if max_results > 10000:
            print(
                f'Note: PubMed ESearch exposes only the first 10000 matches; '
                f'requesting 10000 rather than {max_results}. Narrow the query '
                f'or split it by date range for a larger set.',
                file=sys.stderr,
            )
            max_results = 10000

        # ESearch to get PMIDs
        esearch_url = self.base_url + 'esearch.fcgi'
        params = {
            'db': 'pubmed',
            'term': full_query,
            'retmax': max_results,
            'retmode': 'json',
            'tool': 'citation-management',
        }
        
        if self.email:
            params['email'] = self.email
        if self.api_key:
            params['api_key'] = self.api_key
        
        try:
            response = self.session.get(esearch_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('error') or data.get('esearchresult', {}).get('errorlist'):
                raise ValueError('ESearch returned a query error')
            pmids = data['esearchresult']['idlist']
            count = int(data['esearchresult']['count'])
            
            print(f'Found {count} results, retrieving {len(pmids)}', file=sys.stderr)
            
            return pmids
            
        except Exception as e:
            print(f'Error searching PubMed ({type(e).__name__}); request details omitted', file=sys.stderr)
            return []
    
    def fetch_metadata(self, pmids: List[str]) -> List[Dict]:
        """
        Fetch metadata for PMIDs.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of metadata dictionaries
        """
        if not pmids:
            return []
        
        metadata_list = []
        
        # Fetch in batches of 200
        batch_size = 200
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i+batch_size]
            print(f'Fetching metadata for PMIDs {i+1}-{min(i+batch_size, len(pmids))}...', file=sys.stderr)
            
            efetch_url = self.base_url + 'efetch.fcgi'
            params = {
                'db': 'pubmed',
                'id': ','.join(batch),
                'retmode': 'xml',
                'tool': 'citation-management',
            }
            
            if self.email:
                params['email'] = self.email
            if self.api_key:
                params['api_key'] = self.api_key
            
            try:
                time.sleep(self.delay)
                response = self.session.get(efetch_url, params=params, timeout=60)
                response.raise_for_status()
                
                # Parse XML
                root = ET.fromstring(response.content)
                if root.find('.//ERROR') is not None:
                    raise ValueError('EFetch returned an error')
                articles = root.findall('.//PubmedArticle')
                batch_metadata = []
                
                for article in articles:
                    metadata = self._extract_metadata_from_xml(article)
                    if metadata:
                        batch_metadata.append(metadata)
                if {record['pmid'] for record in batch_metadata} != set(batch):
                    print('Error: EFetch omitted requested records or returned unsupported book records', file=sys.stderr)
                    raise ValueError('Incomplete EFetch batch')
                metadata_list.extend(batch_metadata)
                
            except Exception as e:
                print(f'Error fetching metadata for batch ({type(e).__name__}); request details omitted', file=sys.stderr)
                # Never export a failed batch as a complete bibliography.
                return []
        
        return metadata_list
    
    @staticmethod
    def _element_text(element: Optional[ET.Element]) -> str:
        """Flatten an element's text, including any inline markup children.

        PubMed terminates titles with a full stop that is not part of the
        title; a trailing `?` or `!` is, so only the period is dropped.
        """
        if element is None:
            return ''
        text = ' '.join(''.join(element.itertext()).split())
        return text[:-1] if text.endswith('.') else text

    def _extract_metadata_from_xml(self, article: ET.Element) -> Optional[Dict]:
        """Extract metadata from PubmedArticle XML element."""
        try:
            medline_citation = article.find('.//MedlineCitation')
            article_elem = medline_citation.find('.//Article')
            journal = article_elem.find('.//Journal')
            
            # Get PMID
            pmid = medline_citation.findtext('.//PMID', '')
            
            # Get DOI
            doi = None
            article_ids = article.findall('.//ArticleId')
            for article_id in article_ids:
                if article_id.get('IdType') == 'doi':
                    doi = article_id.text
                    break
            
            # Get authors
            authors = []
            author_list = article_elem.find('.//AuthorList')
            if author_list is not None:
                for author in author_list.findall('.//Author'):
                    last_name = author.findtext('.//LastName', '')
                    fore_name = author.findtext('.//ForeName', '')
                    if last_name:
                        if fore_name:
                            authors.append(f'{last_name}, {fore_name}')
                        else:
                            authors.append(last_name)
            
            # Get year
            year = article_elem.findtext('.//Journal/JournalIssue/PubDate/Year', '')
            if not year:
                medline_date = article_elem.findtext('.//Journal/JournalIssue/PubDate/MedlineDate', '')
                if medline_date:
                    year_match = re.search(r'\d{4}', medline_date)
                    if year_match:
                        year = year_match.group()

            # Structured abstracts split into several labelled AbstractText
            # elements; taking only the first drops most of the abstract.
            sections = []
            for chunk in article_elem.findall('.//Abstract/AbstractText'):
                text = ''.join(chunk.itertext()).strip()
                if not text:
                    continue
                label = chunk.get('Label')
                sections.append(f'{label}: {text}' if label else text)
            abstract = ' '.join(sections)


            metadata = {
                'pmid': pmid,
                'doi': doi,
                # itertext, not findtext: titles carry inline markup such as
                # <i> and <sup>, and findtext returns only the leading run.
                'title': self._element_text(article_elem.find('.//ArticleTitle')),
                'authors': ' and '.join(authors),
                'journal': journal.findtext('.//Title', ''),
                'year': year,
                'volume': journal.findtext('.//JournalIssue/Volume', ''),
                'issue': journal.findtext('.//JournalIssue/Issue', ''),
                'pages': article_elem.findtext('.//Pagination/MedlinePgn', ''),
                'abstract': abstract
            }
            
            return metadata
            
        except Exception as e:
            print(f'Error extracting metadata: {e}', file=sys.stderr)
            return None
    
    def metadata_to_bibtex(self, metadata: Dict) -> str:
        """Convert metadata to BibTeX format.

        Uses the shared key scheme rather than appending the PMID, so an entry
        found here and the same paper found via Crossref or OpenAlex collide
        and can be deduplicated.
        """
        key = citation_key(
            metadata.get('authors', ''),
            metadata.get('year', ''),
            metadata.get('title', ''),
        )

        fields = {
            'author': metadata.get('authors', ''),
            'title': protect_title(metadata.get('title', '')),
            'journal': metadata.get('journal', ''),
            'year': metadata.get('year', ''),
            'volume': metadata.get('volume', ''),
            'number': metadata.get('issue', ''),
            'pages': format_pages(metadata.get('pages')),
            'doi': metadata.get('doi') or '',
        }

        if metadata.get('pmid'):
            fields['note'] = f'PMID: {metadata["pmid"]}'

        return render_entry('article', key, fields)


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description='Search PubMed using E-utilities API',
        epilog='Example: python search_pubmed.py "CRISPR gene editing" --limit 100'
    )
    
    parser.add_argument(
        'query',
        nargs='?',
        help='Search query (PubMed syntax)'
    )
    
    parser.add_argument(
        '--query',
        dest='query_arg',
        help='Search query (alternative to positional argument)'
    )
    
    parser.add_argument(
        '--query-file',
        help='File containing search query'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Maximum number of results (default: 100)'
    )
    
    parser.add_argument(
        '--date-start',
        help='Start date (YYYY/MM/DD or YYYY)'
    )
    
    parser.add_argument(
        '--date-end',
        help='End date (YYYY/MM/DD or YYYY)'
    )
    
    parser.add_argument(
        '--publication-types',
        help='Comma-separated publication types (e.g., "Review,Clinical Trial")'
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
    
    parser.add_argument(
        '--api-key',
        help='NCBI API key (or set NCBI_API_KEY env var)'
    )
    
    parser.add_argument(
        '--email',
        help='Email for Entrez (or set NCBI_EMAIL env var)'
    )
    
    args = parser.parse_args()
    
    # Get query
    query = args.query or args.query_arg
    
    if args.query_file:
        try:
            with open(args.query_file, 'r', encoding='utf-8') as f:
                query = f.read().strip()
        except Exception as e:
            print(f'Error reading query file: {e}', file=sys.stderr)
            sys.exit(1)
    
    if not query:
        parser.print_help()
        sys.exit(1)
    if args.limit < 1:
        parser.error('--limit must be positive')
    
    # Parse publication types
    pub_types = None
    if args.publication_types:
        pub_types = [pt.strip() for pt in args.publication_types.split(',')]
    
    # Search PubMed
    searcher = PubMedSearcher(api_key=args.api_key, email=args.email)
    pmids = searcher.search(
        query,
        max_results=args.limit,
        date_start=args.date_start,
        date_end=args.date_end,
        publication_types=pub_types
    )
    
    if not pmids:
        print('No results found', file=sys.stderr)
        sys.exit(1)
    
    # Fetch metadata
    metadata_list = searcher.fetch_metadata(pmids)
    if not metadata_list:
        print('Error: incomplete PubMed metadata retrieval; no output written', file=sys.stderr)
        sys.exit(2)
    
    # Format output
    if args.format == 'json':
        output = json.dumps({
            'query': query,
            'count': len(metadata_list),
            'results': metadata_list
        }, indent=2)
    else:  # bibtex
        bibtex_entries = [searcher.metadata_to_bibtex(m) for m in metadata_list]
        output = '\n\n'.join(bibtex_entries) + '\n'
    
    # Write output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f'Wrote {len(metadata_list)} results to {args.output}', file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
