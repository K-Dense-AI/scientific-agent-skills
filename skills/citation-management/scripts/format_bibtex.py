#!/usr/bin/env python3
"""
BibTeX Formatter and Cleaner
Format, clean, sort, and deduplicate BibTeX files.

Writing is opt-in: pass --output to write elsewhere, or --in-place to
overwrite the input. Neither flag prints the result to stdout and leaves the
input untouched.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict
from typing import Dict, List, Optional

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    FIELD_ORDER,
    citation_key,
    format_pages,
    parse_bibtex_file,
    render_entry,
)


class BibTeXFormatter:
    """Format and clean BibTeX entries."""

    def __init__(self):
        # Standard field order for readability
        self.field_order = list(FIELD_ORDER)

    def parse_bibtex_file(self, filepath: str) -> List[Dict]:
        """
        Parse BibTeX file and extract entries.

        Args:
            filepath: Path to BibTeX file

        Returns:
            List of entry dictionaries
        """
        return parse_bibtex_file(filepath)

    def format_entry(self, entry: Dict) -> str:
        """
        Format a single BibTeX entry.

        Args:
            entry: Entry dictionary

        Returns:
            Formatted BibTeX string
        """
        return render_entry(entry['type'], entry['key'], entry['fields'])

    def fix_common_issues(self, entry: Dict) -> Dict:
        """
        Fix common formatting issues in entry.

        Args:
            entry: Entry dictionary

        Returns:
            Fixed entry dictionary
        """
        fixed = dict(entry)
        fields = OrderedDict(entry['fields'])

        # Normalise page ranges: strip `pp.`, use an en-dash range, and expand
        # abbreviated end pages. Idempotent, unlike a blanket hyphen replace.
        if 'pages' in fields:
            fields['pages'] = format_pages(fields['pages'])

        # Fix DOI (remove URL prefix if present)
        if 'doi' in fields:
            doi = fields['doi']
            doi = doi.replace('https://doi.org/', '')
            doi = doi.replace('http://doi.org/', '')
            doi = doi.replace('https://dx.doi.org/', '')
            doi = doi.replace('http://dx.doi.org/', '')
            doi = doi.replace('doi:', '')
            fields['doi'] = doi.strip()

        # Fix author separators (semicolon or ampersand to 'and')
        if 'author' in fields:
            author = fields['author']
            author = author.replace(';', ' and')
            author = author.replace(' & ', ' and ')
            # Clean up multiple 'and's
            author = re.sub(r'\s+and\s+and\s+', ' and ', author)
            author = re.sub(r'\s+', ' ', author).strip()
            fields['author'] = author

        fixed['fields'] = fields
        return fixed

    def deduplicate_entries(self, entries: List[Dict]) -> List[Dict]:
        """
        Remove duplicate entries based on DOI or citation key.

        Args:
            entries: List of entry dictionaries

        Returns:
            List of unique entries
        """
        seen_dois = set()
        seen_keys = set()
        unique_entries = []

        for entry in entries:
            doi = entry['fields'].get('doi', '').strip().lower()
            key = entry['key']

            # Check DOI first (more reliable)
            if doi:
                if doi in seen_dois:
                    print(f'Duplicate DOI found: {doi} (skipping {key})', file=sys.stderr)
                    continue

            # Check citation key
            if key in seen_keys:
                print(f'Duplicate citation key found: {key} (skipping)', file=sys.stderr)
                continue
            if doi:
                seen_dois.add(doi)
            seen_keys.add(key)

            unique_entries.append(entry)

        return unique_entries

    def rekey_entries(self, entries: List[Dict]) -> List[Dict]:
        """Rewrite citation keys to this skill's shared scheme.

        Entries pulled from different sources arrive with different key
        conventions, which hides duplicates. Collisions between genuinely
        distinct papers get a letter suffix.
        """
        rekeyed = []
        used = {}

        for entry in entries:
            fields = entry['fields']
            base = citation_key(
                fields.get('author', ''),
                fields.get('year', ''),
                fields.get('title', ''),
            )
            if base in used:
                used[base] += 1
                # 'a' is the original, so the second occurrence becomes 'b'.
                new_key = f'{base}{chr(ord("a") + used[base])}'
            else:
                used[base] = 0
                new_key = base

            updated = dict(entry)
            updated['key'] = new_key
            rekeyed.append(updated)

        return rekeyed

    def sort_entries(self, entries: List[Dict], sort_by: str = 'key', descending: bool = False) -> List[Dict]:
        """
        Sort entries by specified field.

        Args:
            entries: List of entry dictionaries
            sort_by: Field to sort by ('key', 'year', 'author', 'title')
            descending: Sort in descending order

        Returns:
            Sorted list of entries
        """
        def get_sort_key(entry: Dict) -> str:
            if sort_by == 'year':
                # Zero-pad so string comparison orders numerically, and push
                # undated entries to the end.
                year = entry['fields'].get('year', '')
                digits = re.sub(r'[^0-9]', '', year)
                return digits.zfill(4) if digits else '9999'
            if sort_by == 'author':
                author = entry['fields'].get('author', '')
                if not author:
                    return 'zzz'
                first = author.split(' and ')[0]
                if ',' in first:
                    return first.split(',')[0].strip().lower()
                words = first.split()
                return words[-1].lower() if words else 'zzz'
            if sort_by == 'title':
                return entry['fields'].get('title', '').lower()
            return entry['key'].lower()

        return sorted(entries, key=get_sort_key, reverse=descending)

    def format_file(self, filepath: str, output: Optional[str] = None,
                    deduplicate: bool = False, sort_by: Optional[str] = None,
                    descending: bool = False, fix_issues: bool = True,
                    rekey: bool = False) -> Optional[str]:
        """
        Format entire BibTeX file.

        Args:
            filepath: Input BibTeX file
            output: Output file, or None to return the formatted text
            deduplicate: Remove duplicates
            sort_by: Field to sort by
            descending: Sort in descending order
            fix_issues: Fix common formatting issues
            rekey: Rewrite citation keys to the shared scheme

        Returns:
            The formatted BibTeX text, or None when nothing was parsed.
        """
        print(f'Parsing {filepath}...', file=sys.stderr)
        entries = self.parse_bibtex_file(filepath)

        if not entries:
            print('No entries found', file=sys.stderr)
            return None

        print(f'Found {len(entries)} entries', file=sys.stderr)

        # Fix common issues
        if fix_issues:
            print('Fixing common issues...', file=sys.stderr)
            entries = [self.fix_common_issues(e) for e in entries]

        # Rekey before deduplicating, so cross-source duplicates collapse.
        if rekey:
            print('Rewriting citation keys...', file=sys.stderr)
            entries = self.rekey_entries(entries)

        # Deduplicate
        if deduplicate:
            print('Removing duplicates...', file=sys.stderr)
            original_count = len(entries)
            entries = self.deduplicate_entries(entries)
            removed = original_count - len(entries)
            if removed > 0:
                print(f'Removed {removed} duplicate(s)', file=sys.stderr)

        # Sort
        if sort_by:
            print(f'Sorting by {sort_by}...', file=sys.stderr)
            entries = self.sort_entries(entries, sort_by, descending)

        # Format entries
        print('Formatting entries...', file=sys.stderr)
        formatted_entries = [self.format_entry(e) for e in entries]
        output_content = '\n\n'.join(formatted_entries) + '\n'

        if output is None:
            return output_content

        try:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(output_content)
            print(f'Successfully wrote {len(entries)} entries to {output}', file=sys.stderr)
        except OSError as e:
            print(f'Error writing file: {e}', file=sys.stderr)
            sys.exit(1)

        return output_content


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description='Format, clean, sort, and deduplicate BibTeX files',
        epilog='Example: python format_bibtex.py references.bib -o clean.bib --deduplicate --sort year'
    )

    parser.add_argument(
        'file',
        help='BibTeX file to format'
    )

    parser.add_argument(
        '-o', '--output',
        help='Write the result to this file'
    )

    parser.add_argument(
        '--in-place',
        action='store_true',
        help='Overwrite the input file (mutually exclusive with --output)'
    )

    parser.add_argument(
        '--deduplicate', '--remove-duplicates',
        dest='deduplicate',
        action='store_true',
        help='Remove duplicate entries'
    )

    parser.add_argument(
        '--rekey',
        action='store_true',
        help="Rewrite citation keys to this skill's shared scheme before deduplicating"
    )

    parser.add_argument(
        '--sort',
        choices=['key', 'year', 'author', 'title'],
        help='Sort entries by field'
    )

    parser.add_argument(
        '--descending',
        action='store_true',
        help='Sort in descending order'
    )

    parser.add_argument(
        '--no-fix',
        action='store_true',
        help='Do not fix common issues'
    )

    args = parser.parse_args()

    if args.output and args.in_place:
        parser.error('--output and --in-place are mutually exclusive')

    destination = args.file if args.in_place else args.output

    # Format file
    formatter = BibTeXFormatter()
    result = formatter.format_file(
        args.file,
        output=destination,
        deduplicate=args.deduplicate,
        sort_by=args.sort,
        descending=args.descending,
        fix_issues=not args.no_fix,
        rekey=args.rekey,
    )

    if result is None:
        sys.exit(1)

    # Without a destination the input is left alone and the result goes to
    # stdout, so a mistaken invocation cannot destroy a bibliography.
    if destination is None:
        print(result, end='')


if __name__ == '__main__':
    main()
