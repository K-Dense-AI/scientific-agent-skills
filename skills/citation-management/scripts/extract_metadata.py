#!/usr/bin/env python3
"""
Metadata Extraction Tool
Extract citation metadata from DOI, PMID, arXiv ID, or URL using various APIs.
"""

import sys
import os
import requests
import argparse
import time
import re
import json
import defusedxml.ElementTree as ET
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlparse, quote

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    citation_key,
    format_pages,
    protect_title,
    render_entry,
)

class MetadataExtractor:
    """Extract metadata from various sources and generate BibTeX."""
    
    def __init__(self, email: Optional[str] = None):
        """
        Initialize extractor.
        
        Args:
            email: Email for Entrez API (recommended for PubMed)
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MetadataExtractor/1.0 (Citation Management Tool)'
        })
        self.email = email or os.getenv('NCBI_EMAIL', '')
    
    def identify_type(self, identifier: str) -> Tuple[str, str]:
        """
        Identify the type of identifier.
        
        Args:
            identifier: DOI, PMID, arXiv ID, or URL
            
        Returns:
            Tuple of (type, cleaned_identifier)
        """
        identifier = identifier.strip()
        
        # Check if URL
        if identifier.startswith('http://') or identifier.startswith('https://'):
            return self._parse_url(identifier)
        
        # Check for DOI
        if identifier.startswith('10.'):
            return ('doi', identifier)
        
        # Check for arXiv ID
        if re.match(r'^\d{4}\.\d{4,5}(v\d+)?$', identifier):
            return ('arxiv', identifier)
        if identifier.startswith('arXiv:'):
            return ('arxiv', identifier.replace('arXiv:', ''))
        
        # Check for PMID (8-digit number typically)
        if identifier.isdigit() and len(identifier) >= 7:
            return ('pmid', identifier)
        
        # Check for PMCID
        if identifier.upper().startswith('PMC') and identifier[3:].isdigit():
            return ('pmcid', identifier.upper())
        
        return ('unknown', identifier)
    
    def _parse_url(self, url: str) -> Tuple[str, str]:
        """Parse URL to extract identifier type and value."""
        parsed = urlparse(url)
        
        # DOI URLs
        if 'doi.org' in parsed.netloc:
            doi = parsed.path.lstrip('/')
            return ('doi', doi)
        
        # PubMed URLs
        if 'pubmed.ncbi.nlm.nih.gov' in parsed.netloc or 'ncbi.nlm.nih.gov/pubmed' in url:
            pmid = re.search(r'/(\d+)', parsed.path)
            if pmid:
                return ('pmid', pmid.group(1))
        
        # arXiv URLs
        if 'arxiv.org' in parsed.netloc:
            arxiv_id = re.search(r'/abs/(\d{4}\.\d{4,5})', parsed.path)
            if arxiv_id:
                return ('arxiv', arxiv_id.group(1))
        
        # Nature, Science, Cell, etc. - try to extract DOI from URL
        doi_match = re.search(r'10\.\d{4,}/[^\s/]+', url)
        if doi_match:
            return ('doi', doi_match.group())
        
        return ('url', url)
    
    def extract_from_doi(self, doi: str) -> Optional[Dict]:
        """
        Extract metadata from DOI using CrossRef API.
        
        Args:
            doi: Digital Object Identifier
            
        Returns:
            Metadata dictionary or None
        """
        # A DOI is publisher-controlled text and may legitimately contain
        # `#`, `?`, `<` or `>`, so it cannot be interpolated into a URL raw.
        url = f'https://api.crossref.org/works/{quote(doi, safe="")}'

        try:
            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                message = data.get('message', {})

                container = message.get('container-title') or ['']
                isbns = message.get('ISBN') or []
                issns = message.get('ISSN') or []

                metadata = {
                    'type': 'doi',
                    'entry_type': self._crossref_type_to_bibtex(message.get('type')),
                    'doi': doi,
                    'title': (message.get('title') or [''])[0],
                    'authors': self._format_authors_crossref(message.get('author', [])),
                    'editors': self._format_authors_crossref(message.get('editor', [])),
                    'year': self._extract_year_crossref(message),
                    'journal': container[0] if container else '',
                    'volume': str(message.get('volume', '')) if message.get('volume') else '',
                    'issue': str(message.get('issue', '')) if message.get('issue') else '',
                    'pages': message.get('page', ''),
                    'publisher': message.get('publisher', ''),
                    'isbn': isbns[0] if isbns else '',
                    'issn': issns[0] if issns else '',
                    'url': f'https://doi.org/{doi}'
                }

                return metadata
            else:
                print(f'Error: CrossRef API returned status {response.status_code} for DOI: {doi}', file=sys.stderr)
                return None
                
        except Exception as e:
            print(f'Error extracting metadata from DOI {doi}: {e}', file=sys.stderr)
            return None
    
    def extract_from_pmid(self, pmid: str) -> Optional[Dict]:
        """
        Extract metadata from PMID using PubMed E-utilities.
        
        Args:
            pmid: PubMed ID
            
        Returns:
            Metadata dictionary or None
        """
        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
        params = {
            'db': 'pubmed',
            'id': pmid,
            'retmode': 'xml',
            'rettype': 'abstract'
        }
        
        if self.email:
            params['email'] = self.email
        
        api_key = os.getenv('NCBI_API_KEY')
        if api_key:
            params['api_key'] = api_key
        
        try:
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                article = root.find('.//PubmedArticle')
                
                if article is None:
                    print(f'Error: No article found for PMID: {pmid}', file=sys.stderr)
                    return None
                
                # Extract metadata from XML
                medline_citation = article.find('.//MedlineCitation')
                article_elem = medline_citation.find('.//Article')
                journal = article_elem.find('.//Journal')
                
                # Get DOI if available
                doi = None
                article_ids = article.findall('.//ArticleId')
                for article_id in article_ids:
                    if article_id.get('IdType') == 'doi':
                        doi = article_id.text
                        break
                
                metadata = {
                    'type': 'pmid',
                    'entry_type': 'article',
                    'pmid': pmid,
                    'title': self._pubmed_title(article_elem.find('.//ArticleTitle')),
                    'authors': self._format_authors_pubmed(article_elem.findall('.//Author')),
                    'year': self._extract_year_pubmed(article_elem),
                    'journal': journal.findtext('.//Title', ''),
                    'volume': journal.findtext('.//JournalIssue/Volume', ''),
                    'issue': journal.findtext('.//JournalIssue/Issue', ''),
                    'pages': article_elem.findtext('.//Pagination/MedlinePgn', ''),
                    'doi': doi
                }
                
                return metadata
            else:
                print(f'Error: PubMed API returned status {response.status_code} for PMID: {pmid}', file=sys.stderr)
                return None
                
        except Exception as e:
            print(f'Error extracting metadata from PMID {pmid}: {e}', file=sys.stderr)
            return None
    
    @staticmethod
    def _pubmed_title(element) -> str:
        """Read a PubMed ArticleTitle as a citation title.

        `itertext`, not `findtext`, because titles carry inline markup such as
        <i> and <sup> and findtext returns only the leading run. PubMed also
        terminates titles with a full stop that is not part of the title; a
        trailing `?` or `!` is, so only the period is dropped.
        """
        if element is None:
            return ''
        text = ' '.join(''.join(element.itertext()).split())
        return text[:-1] if text.endswith('.') else text

    def extract_from_arxiv(self, arxiv_id: str) -> Optional[Dict]:
        """
        Extract metadata from arXiv ID using arXiv API.
        
        Args:
            arxiv_id: arXiv identifier
            
        Returns:
            Metadata dictionary or None
        """
        url = 'http://export.arxiv.org/api/query'
        params = {
            'id_list': arxiv_id,
            'max_results': 1
        }
        
        try:
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                # Parse Atom XML
                root = ET.fromstring(response.content)
                ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
                
                entry = root.find('atom:entry', ns)
                if entry is None:
                    print(f'Error: No entry found for arXiv ID: {arxiv_id}', file=sys.stderr)
                    return None
                
                # Extract DOI if published
                doi_elem = entry.find('arxiv:doi', ns)
                doi = doi_elem.text if doi_elem is not None else None
                
                # Extract journal reference if published
                journal_ref_elem = entry.find('arxiv:journal_ref', ns)
                journal_ref = journal_ref_elem.text if journal_ref_elem is not None else None
                
                # Get publication date
                published = entry.findtext('atom:published', '', ns)
                year = published[:4] if published else ''
                
                # Get authors
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.findtext('atom:name', '', ns)
                    if name:
                        authors.append(name)
                
                # Only call it an @article when there is a journal to name.
                # A DOI alone is not enough -- arXiv mints DataCite DOIs for
                # unpublished preprints -- and an @article without a `journal`
                # fails the required-field check in validate_citations.py.
                journal = self._journal_from_arxiv_ref(journal_ref)

                metadata = {
                    'type': 'arxiv',
                    'entry_type': 'article' if journal else 'misc',
                    'arxiv_id': arxiv_id,
                    'title': entry.findtext('atom:title', '', ns).strip().replace('\n', ' '),
                    'authors': ' and '.join(authors),
                    'year': year,
                    'doi': doi,
                    'journal': journal,
                    'journal_ref': journal_ref,
                    'abstract': entry.findtext('atom:summary', '', ns).strip().replace('\n', ' '),
                    'url': f'https://arxiv.org/abs/{arxiv_id}'
                }

                return metadata
            else:
                print(f'Error: arXiv API returned status {response.status_code} for ID: {arxiv_id}', file=sys.stderr)
                return None
                
        except Exception as e:
            print(f'Error extracting metadata from arXiv {arxiv_id}: {e}', file=sys.stderr)
            return None
    
    def metadata_to_bibtex(self, metadata: Dict, citation_key: Optional[str] = None) -> str:
        """
        Convert metadata dictionary to BibTeX format.
        
        Args:
            metadata: Metadata dictionary
            citation_key: Optional custom citation key
            
        Returns:
            BibTeX string
        """
        if not citation_key:
            citation_key = self._generate_citation_key(metadata)

        entry_type = metadata.get('entry_type', 'misc')

        fields = {
            'author': metadata.get('authors', ''),
            'editor': metadata.get('editors', ''),
            'title': protect_title(metadata.get('title', '')),
            'year': metadata.get('year', ''),
            'volume': metadata.get('volume', ''),
            'number': metadata.get('issue', ''),
            'pages': format_pages(metadata.get('pages')),
            'doi': metadata.get('doi') or '',
            'isbn': metadata.get('isbn', ''),
            'issn': metadata.get('issn', ''),
        }

        # The venue field's name depends on the entry type, and a book or
        # report needs its publisher/institution or it fails validation.
        if entry_type in ('inproceedings', 'incollection'):
            fields['booktitle'] = metadata.get('journal', '')
        elif entry_type != 'misc':
            fields['journal'] = metadata.get('journal', '')

        if entry_type in ('book', 'incollection', 'inproceedings'):
            fields['publisher'] = metadata.get('publisher', '')
        elif entry_type == 'techreport':
            fields['institution'] = metadata.get('publisher', '')

        if entry_type == 'misc' and metadata.get('type') == 'arxiv':
            arxiv_id = metadata.get('arxiv_id', '')
            fields['howpublished'] = f'arXiv:{arxiv_id}' if arxiv_id else 'arXiv'

        # A DOI is the stable locator; only fall back to a URL without one.
        if not fields['doi'] and metadata.get('url'):
            fields['url'] = metadata['url']

        # BibTeX takes one `note` per entry, so build it from all the parts
        # that would otherwise each claim the field.
        notes = []
        if metadata.get('pmid'):
            notes.append(f'PMID: {metadata["pmid"]}')
        if metadata.get('type') == 'arxiv' and entry_type == 'misc':
            notes.append('Preprint')
        if notes:
            fields['note'] = '. '.join(notes)

        return render_entry(entry_type, citation_key, fields)

    @staticmethod
    def _journal_from_arxiv_ref(journal_ref: Optional[str]) -> str:
        """Pull a journal name out of arXiv's free-text `journal_ref`.

        The field has no schema -- `Nature 596, 583-589 (2021)` is typical --
        so take the leading run of non-numeric text and leave the rest for the
        enrichment pass rather than guessing at volume and pages.
        """
        if not journal_ref:
            return ''
        head = re.split(r'[,;]|\s\d', journal_ref.strip(), maxsplit=1)[0]
        return head.strip(' .')
    
    def _crossref_type_to_bibtex(self, crossref_type: str) -> str:
        """Map CrossRef type to BibTeX entry type."""
        type_map = {
            'journal-article': 'article',
            'book': 'book',
            'book-chapter': 'incollection',
            'proceedings-article': 'inproceedings',
            'posted-content': 'misc',
            'dataset': 'misc',
            'report': 'techreport'
        }
        return type_map.get(crossref_type, 'misc')
    
    def _format_authors_crossref(self, authors: List[Dict]) -> str:
        """Format author list from CrossRef data."""
        if not authors:
            return ''
        
        formatted = []
        for author in authors:
            given = author.get('given', '')
            family = author.get('family', '')
            if family:
                if given:
                    formatted.append(f'{family}, {given}')
                else:
                    formatted.append(family)
        
        return ' and '.join(formatted)
    
    def _format_authors_pubmed(self, authors: List) -> str:
        """Format author list from PubMed XML."""
        formatted = []
        for author in authors:
            last_name = author.findtext('.//LastName', '')
            fore_name = author.findtext('.//ForeName', '')
            if last_name:
                if fore_name:
                    formatted.append(f'{last_name}, {fore_name}')
                else:
                    formatted.append(last_name)
        
        return ' and '.join(formatted)
    
    def _extract_year_crossref(self, message: Dict) -> str:
        """Extract year from CrossRef message."""
        # Try published-print first, then published-online
        date_parts = message.get('published-print', {}).get('date-parts', [[]])
        if not date_parts or not date_parts[0]:
            date_parts = message.get('published-online', {}).get('date-parts', [[]])
        
        if date_parts and date_parts[0]:
            return str(date_parts[0][0])
        return ''
    
    def _extract_year_pubmed(self, article: ET.Element) -> str:
        """Extract year from PubMed XML."""
        year = article.findtext('.//Journal/JournalIssue/PubDate/Year', '')
        if not year:
            medline_date = article.findtext('.//Journal/JournalIssue/PubDate/MedlineDate', '')
            if medline_date:
                year_match = re.search(r'\d{4}', medline_date)
                if year_match:
                    year = year_match.group()
        return year
    
    def _generate_citation_key(self, metadata: Dict) -> str:
        """Generate a citation key from metadata.

        Shared with every other producer in this skill so that entries from
        different sources collide when -- and only when -- they are the same
        paper. Values arrive verbatim from a publisher-controlled record, and
        the key reaches both LaTeX and, in some workflows, a file path, so the
        shared helper restricts it to ASCII letters and digits.
        """
        return citation_key(
            metadata.get('authors', ''),
            metadata.get('year', ''),
            metadata.get('title', ''),
        )

    def _protect_title(self, title: str) -> str:
        """Protect capitalization in title for BibTeX."""
        return protect_title(title)

    def extract_from_pmcid(self, pmcid: str) -> Optional[Dict]:
        """Resolve a PMCID to a PMID via the NCBI ID converter, then extract."""
        url = 'https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/'
        params = {'ids': pmcid, 'format': 'json', 'tool': 'citation-management'}
        if self.email:
            params['email'] = self.email

        try:
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code != 200:
                print(f'Error: ID converter returned status {response.status_code} for {pmcid}', file=sys.stderr)
                return None

            records = response.json().get('records', [])
            if not records or 'pmid' not in records[0]:
                if records and records[0].get('doi'):
                    return self.extract_from_doi(records[0]['doi'])
                print(f'Error: Could not resolve {pmcid} to a PMID or DOI', file=sys.stderr)
                return None

            return self.extract_from_pmid(records[0]['pmid'])

        except (requests.exceptions.RequestException, ValueError) as e:
            print(f'Error resolving PMCID {pmcid}: {e}', file=sys.stderr)
            return None

    def extract_from_url(self, url: str) -> Optional[Dict]:
        """Extract via a DOI advertised in the page's citation metadata.

        Publishers embed `citation_doi` / `DC.Identifier` meta tags on article
        pages. Reading the DOI and handing off to Crossref is far more reliable
        than scraping the page itself, and it fails honestly when absent.
        """
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                print(f'Error: URL returned status {response.status_code}: {url}', file=sys.stderr)
                return None

            head = response.text[:200000]
            patterns = [
                r'<meta[^>]+name=["\'](?:citation_doi|DC\.Identifier|dc\.identifier)["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\'](?:citation_doi|DC\.Identifier|dc\.identifier)["\']',
            ]
            for pattern in patterns:
                match = re.search(pattern, head, re.IGNORECASE)
                if match:
                    doi = match.group(1).strip()
                    doi = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:)', '', doi, flags=re.IGNORECASE)
                    if doi.startswith('10.'):
                        print(f'Found DOI in page metadata: {doi}', file=sys.stderr)
                        return self.extract_from_doi(doi)

            print(f'Error: No DOI found in page metadata for {url}', file=sys.stderr)
            return None

        except requests.exceptions.RequestException as e:
            print(f'Error fetching {url}: {e}', file=sys.stderr)
            return None


    def extract(self, identifier: str) -> Optional[str]:
        """
        Extract metadata and return BibTeX.
        
        Args:
            identifier: DOI, PMID, arXiv ID, or URL
            
        Returns:
            BibTeX string or None
        """
        id_type, clean_id = self.identify_type(identifier)
        
        print(f'Identified as {id_type}: {clean_id}', file=sys.stderr)
        
        metadata = None
        
        if id_type == 'doi':
            metadata = self.extract_from_doi(clean_id)
        elif id_type == 'pmid':
            metadata = self.extract_from_pmid(clean_id)
        elif id_type == 'arxiv':
            metadata = self.extract_from_arxiv(clean_id)
        elif id_type == 'pmcid':
            metadata = self.extract_from_pmcid(clean_id)
        elif id_type == 'url':
            metadata = self.extract_from_url(clean_id)
        else:
            print(f'Error: Unknown identifier type: {identifier}', file=sys.stderr)
            return None
        
        if metadata:
            return self.metadata_to_bibtex(metadata)
        else:
            return None

    def extract_record(self, identifier: str) -> Optional[Dict]:
        """Extract metadata and return it with its rendered BibTeX attached."""
        id_type, clean_id = self.identify_type(identifier)

        print(f'Identified as {id_type}: {clean_id}', file=sys.stderr)

        handlers = {
            'doi': self.extract_from_doi,
            'pmid': self.extract_from_pmid,
            'arxiv': self.extract_from_arxiv,
            'pmcid': self.extract_from_pmcid,
            'url': self.extract_from_url,
        }

        handler = handlers.get(id_type)
        if handler is None:
            print(f'Error: Unknown identifier type: {identifier}', file=sys.stderr)
            return None

        metadata = handler(clean_id)
        if not metadata:
            return None

        record = dict(metadata)
        record['citation_key'] = self._generate_citation_key(metadata)
        record['bibtex'] = self.metadata_to_bibtex(metadata, record['citation_key'])
        return record


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description='Extract citation metadata from DOI, PMID, arXiv ID, or URL',
        epilog='Example: python extract_metadata.py --doi 10.1038/s41586-021-03819-2'
    )
    
    parser.add_argument('--doi', help='Digital Object Identifier')
    parser.add_argument('--pmid', help='PubMed ID')
    parser.add_argument('--arxiv', help='arXiv ID')
    parser.add_argument('--url', help='URL to article')
    parser.add_argument('-i', '--input', help='Input file with identifiers (one per line)')
    parser.add_argument('-o', '--output', help='Output file for BibTeX (default: stdout)')
    parser.add_argument('--format', choices=['bibtex', 'json'], default='bibtex', help='Output format')
    parser.add_argument('--email', help='Email for NCBI E-utilities (recommended)')
    
    args = parser.parse_args()
    
    # Collect identifiers
    identifiers = []
    if args.doi:
        identifiers.append(args.doi)
    if args.pmid:
        identifiers.append(args.pmid)
    if args.arxiv:
        identifiers.append(args.arxiv)
    if args.url:
        identifiers.append(args.url)
    
    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                file_ids = [line.strip() for line in f if line.strip()]
                identifiers.extend(file_ids)
        except Exception as e:
            print(f'Error reading input file: {e}', file=sys.stderr)
            sys.exit(1)
    
    if not identifiers:
        parser.print_help()
        sys.exit(1)
    
    # Extract metadata
    extractor = MetadataExtractor(email=args.email)
    records = []

    for i, identifier in enumerate(identifiers):
        print(f'\nProcessing {i+1}/{len(identifiers)}...', file=sys.stderr)
        record = extractor.extract_record(identifier)
        if record:
            records.append(record)

        # Rate limiting
        if i < len(identifiers) - 1:
            time.sleep(0.5)

    if not records:
        print('Error: No successful extractions', file=sys.stderr)
        sys.exit(1)

    bibtex_entries = [record['bibtex'] for record in records]

    # Format output
    if args.format == 'bibtex':
        output = '\n\n'.join(bibtex_entries) + '\n'
    else:  # json
        output = json.dumps({
            'count': len(records),
            'entries': records
        }, indent=2)
    
    # Write output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"\nSuccessfully wrote {len(records)} entries to {args.output}", file=sys.stderr)
    else:
        print(output)
    
    print(f'\nExtracted {len(bibtex_entries)}/{len(identifiers)} entries', file=sys.stderr)


if __name__ == '__main__':
    main()

