#!/usr/bin/env python3
"""Render reviewed Markdown with Pandoc/XeLaTeX and optional local CSL bibliography."""

import argparse
import os
import subprocess
from pathlib import Path


def check_dependencies():
    """Check both executables; TeX package availability still needs a real render."""
    available = True
    for name in ('pandoc', 'xelatex'):
        try:
            subprocess.run([name, '--version'], capture_output=True, check=True)
            print(f'[OK] {name} is installed')
        except (subprocess.CalledProcessError, OSError):
            print(f'[FAIL] {name} is NOT installed')
            available = False
    return available


def generate_pdf(markdown_file: str, output_pdf: str = None,
                 citation_style: str = None, template: str = None,
                 toc: bool = True, number_sections: bool = True,
                 bibliography: str = None) -> bool:
    """Render PDF. Style is a local CSL path/name; omitted uses Pandoc's default.

    A sibling .bib is detected automatically. Pandoc citation syntax [@key] is
    required for citeproc; manually typed reference text is not reformatted.
    """
    source = Path(markdown_file).resolve()
    destination = Path(output_pdf).resolve() if output_pdf else source.with_suffix('.pdf')
    if not source.is_file() or source == destination:
        print('[FAIL] Input must exist and output must differ from input')
        return False
    if not check_dependencies():
        return False
    cmd = ['pandoc', str(source), '-o', str(destination), '--pdf-engine=xelatex',
           '--resource-path', os.pathsep.join([str(source.parent), str(Path.cwd())]),
           '-V', 'geometry:margin=1in', '-V', 'fontsize=11pt',
           '-V', 'colorlinks=true', '-V', 'linkcolor=blue', '-V', 'urlcolor=blue',
           '-V', 'citecolor=blue', '--citeproc']
    if toc:
        cmd.extend(['--toc', '--toc-depth=3'])
    if number_sections:
        cmd.append('--number-sections')
    bib = Path(bibliography).resolve() if bibliography else source.with_suffix('.bib')
    if bibliography and not bib.is_file():
        print(f'[FAIL] Bibliography not found: {bib}')
        return False
    if bib.is_file():
        cmd.extend(['--bibliography', str(bib)])
    if citation_style:
        style = Path(citation_style if citation_style.endswith('.csl') else citation_style + '.csl')
        if not style.is_file():
            style = source.parent / style
        if not style.is_file():
            print('[FAIL] Supply an existing CSL file with --csl; style names are not downloaded automatically')
            return False
        cmd.extend(['--csl', str(style.resolve())])
    if template:
        if not Path(template).is_file():
            print(f'[FAIL] Template not found: {template}')
            return False
        cmd.extend(['--template', str(Path(template).resolve())])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if result.stderr:
            print(result.stderr.strip())  # Surface missing citation and rendering warnings.
        if not destination.is_file() or not destination.read_bytes().startswith(b'%PDF-'):
            print('[FAIL] Pandoc returned without a valid PDF output')
            return False
        print(f'[OK] PDF generated: {destination}')
        return True
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f'[FAIL] PDF generation: {getattr(exc, "stderr", None) or exc}')
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('markdown_file', nargs='?')
    parser.add_argument('output_pdf', nargs='?', help='Legacy positional output path')
    parser.add_argument('-o', '--output')
    parser.add_argument('--csl', '--citation-style', dest='citation_style',
                        help='Local CSL path, or local style name such as apa (requires apa.csl)')
    parser.add_argument('--bibliography', help='Local .bib, .json or other Pandoc bibliography file')
    parser.add_argument('--template')
    parser.add_argument('--no-toc', action='store_true')
    parser.add_argument('--no-numbers', action='store_true')
    parser.add_argument('--check-deps', action='store_true')
    args = parser.parse_args()
    if args.check_deps:
        raise SystemExit(0 if check_dependencies() else 1)
    if not args.markdown_file:
        parser.error('markdown_file is required unless --check-deps is used')
    if args.output and args.output_pdf:
        parser.error('choose either positional output or --output')
    raise SystemExit(0 if generate_pdf(args.markdown_file, args.output or args.output_pdf,
                                      citation_style=args.citation_style, template=args.template,
                                      toc=not args.no_toc, number_sections=not args.no_numbers,
                                      bibliography=args.bibliography) else 1)


if __name__ == '__main__':
    main()
