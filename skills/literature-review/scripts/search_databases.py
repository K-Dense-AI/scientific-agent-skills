#!/usr/bin/env python3
"""
Literature Database Search Script
Processes normalized search records locally; does not query databases.
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import unquote
from typing import Dict, List
from datetime import datetime

def format_search_results(results: List[Dict], output_format: str = 'json') -> str:
    """
    Format search results for output.

    Args:
        results: List of search results
        output_format: Format (json, markdown, or bibtex)

    Returns:
        Formatted string
    """
    if output_format == 'json':
        return json.dumps(results, indent=2)

    elif output_format == 'markdown':
        md = f"# Literature Search Results\n\n"
        md += f"**Export Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        md += f"**Total Results**: {len(results)}\n\n"

        for i, result in enumerate(results, 1):
            md += f"## {i}. {result.get('title', 'Untitled')}\n\n"
            md += f"**Authors**: {result.get('authors', 'Unknown')}\n\n"
            md += f"**Year**: {result.get('year', 'N/A')}\n\n"
            md += f"**Source**: {result.get('source', 'Unknown')}\n\n"

            if result.get('abstract'):
                md += f"**Abstract**: {result['abstract']}\n\n"

            if result.get('doi'):
                md += f"**DOI**: [{result['doi']}](https://doi.org/{result['doi']})\n\n"

            if result.get('url'):
                md += f"**URL**: {result['url']}\n\n"

            if result.get('citations') is not None:
                md += f"**Citations**: {result['citations']}\n\n"

            md += "---\n\n"

        return md

    elif output_format == 'bibtex':
        bibtex = ""
        used_keys = set()
        for i, result in enumerate(results, 1):
            entry_type = result.get('type', 'article')
            base_key = re.sub(r'[^a-zA-Z0-9_-]', '',
                              f"{result.get('first_author') or 'unknown'}{result.get('year') or '0000'}")
            cite_key, suffix = base_key, 2
            while cite_key in used_keys:
                cite_key = f'{base_key}_{suffix}'
                suffix += 1
            used_keys.add(cite_key)

            bibtex += f"@{entry_type}{{{cite_key},\n"
            bibtex += f"  title = {{{result.get('title', '')}}},\n"
            bibtex += f"  author = {{{result.get('authors', '')}}},\n"
            bibtex += f"  year = {{{result.get('year', '')}}},\n"

            if result.get('journal'):
                bibtex += f"  journal = {{{result['journal']}}},\n"

            if result.get('volume'):
                bibtex += f"  volume = {{{result['volume']}}},\n"

            if result.get('pages'):
                bibtex += f"  pages = {{{result['pages']}}},\n"

            if result.get('doi'):
                bibtex += f"  doi = {{{result['doi']}}},\n"

            bibtex += "}\n\n"

        return bibtex

    else:
        raise ValueError(f"Unknown format: {output_format}")

def deduplicate_results(results: List[Dict]) -> List[Dict]:
    """
    Keep the first occurrence of a DOI; use title only among DOI-less records.

    Exact title matches still require review. Preserve raw exports to recover
    metadata from duplicate records; this helper does not identify studies.

    Args:
        results: List of search results

    Returns:
        Deduplicated list
    """
    seen_dois = set()
    seen_titles = set()
    unique_results = []

    for result in results:
        doi = unquote(re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '',
                            str(result.get('doi') or '').strip(), flags=re.I)).lower()
        title = str(result.get('title') or '').lower().strip()

        # Check DOI first (more reliable)
        if doi and doi in seen_dois:
            continue

        # Check title as fallback
        if not doi and title in seen_titles:
            continue

        # Add to results
        if doi:
            seen_dois.add(doi)
        if title and not doi:
            seen_titles.add(title)

        unique_results.append(result)

    return unique_results

def rank_results(results: List[Dict], criteria: str = 'citations') -> List[Dict]:
    """
    Rank results by specified criteria.

    Args:
        results: List of search results
        criteria: Ranking criteria (citations, year, relevance)

    Returns:
        Ranked list
    """
    field = {'citations': 'citations', 'year': 'year', 'relevance': 'relevance_score'}.get(criteria)
    if field is None:
        return results
    def score(record):
        try:
            value = float(record.get(field))
            return value if math.isfinite(value) else float('-inf')
        except (ValueError, TypeError):
            return float('-inf')
    return sorted(results, key=score, reverse=True)

def filter_by_year(results: List[Dict], start_year: int = None, end_year: int = None) -> List[Dict]:
    """
    Filter results by publication year range.

    Args:
        results: List of search results
        start_year: Minimum year (inclusive)
        end_year: Maximum year (inclusive)

    Returns:
        Filtered list
    """
    filtered = []

    for result in results:
        try:
            year = int(result.get('year'))
            if start_year and year < start_year:
                continue
            if end_year and year > end_year:
                continue
            filtered.append(result)
        except (ValueError, TypeError):
            # Include if year parsing fails
            filtered.append(result)

    return filtered

def generate_search_summary(results: List[Dict]) -> Dict:
    """
    Generate summary statistics for search results.

    Args:
        results: List of search results

    Returns:
        Summary dictionary
    """
    summary = {
        'total_results': len(results),
        'sources': {},
        'year_distribution': {},
        'avg_citations': 0,
        'total_citations': 0
    }

    citations = []

    for result in results:
        # Count by source
        source = result.get('source', 'Unknown')
        summary['sources'][source] = summary['sources'].get(source, 0) + 1

        # Count by year
        year = result.get('year', 'Unknown')
        summary['year_distribution'][year] = summary['year_distribution'].get(year, 0) + 1

        # Collect citations
        if result.get('citations') is not None:
            try:
                value = int(result['citations'])
                if value >= 0:
                    citations.append(value)
            except (ValueError, TypeError):
                pass

    if citations:
        summary['avg_citations'] = sum(citations) / len(citations)
        summary['total_citations'] = sum(citations)

    return summary

def main():
    """Process a JSON array; refuse raw provider envelopes and unknown options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results_file', type=Path)
    parser.add_argument('--format', choices=['json', 'markdown', 'bibtex'], default='markdown')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--rank', choices=['citations', 'year', 'relevance'])
    parser.add_argument('--year-start', type=int)
    parser.add_argument('--year-end', type=int)
    parser.add_argument('--deduplicate', action='store_true')
    parser.add_argument('--summary', action='store_true')
    args = parser.parse_args()
    if args.year_start and args.year_end and args.year_start > args.year_end:
        parser.error('--year-start must not exceed --year-end')
    try:
        results = json.loads(args.results_file.read_text(encoding='utf-8'))
        if not isinstance(results, list) or any(not isinstance(r, dict) for r in results):
            raise ValueError('input must be a normalized JSON array of record objects, not a provider response')
        if args.deduplicate:
            results = deduplicate_results(results)
        if args.year_start is not None or args.year_end is not None:
            results = filter_by_year(results, args.year_start, args.year_end)
        if args.rank:
            results = rank_results(results, args.rank)
        if args.summary:
            print(json.dumps(generate_search_summary(results), indent=2), file=sys.stderr)
        output = format_search_results(results, args.format)
        if args.output:
            args.output.write_text(output, encoding='utf-8')
            print(f'[OK] Results saved to: {args.output}', file=sys.stderr)
        else:
            print(output)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f'[FAIL] {exc}\n')


if __name__ == '__main__':
    main()
