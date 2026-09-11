#!/usr/bin/env python3
"""Extract a structured reference list (and in-text citations) from a manuscript.

Supported inputs, auto-detected or forced with --format:

    markdown   numbered or bulleted reference sections in a .md / .txt file
    latex      \\bibitem entries, \\begin{thebibliography}, or inline \\cite keys
    bibtex     a .bib file (brace-depth parser, comment-safe)

Outputs a JSON list of reference candidates, each carrying whatever
identifiers could be recovered (DOI, arXiv ID, PMID, title, authors, year,
position). The downstream verifier only needs one identifier or a title to
work, so extraction is intentionally permissive: a partially parsed entry is
more useful than a dropped one.

Also extracts in-text citation sentences (--in-text) so claims can later be
checked against the source they cite.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import extract_arxiv_id, extract_pmid, normalize_doi  # noqa: E402

REFERENCE_HEADINGS = re.compile(
    r"^\s*(?:#+\s*)?(?:references|bibliography|works cited|literature cited)"
    r"\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_ENTRY_PREFIX = re.compile(r"^\s*(?:\[\d+\]|\(\d+\)|\d+[.)])\s*")
_TEX_BIBITEM = re.compile(r"\\bibitem(?:\[[^\]]*\])?\{?([^}\n]*)\}?\s*\n?")
_TEX_COMMENT = re.compile(r"(?m)^%.*$")

# A sentence that carries an in-text citation marker and something checkable
# (a number or a quoted phrase).
_NUMERIC_CLAIM = re.compile(r"\d+(?:\.\d+)?\s*%|\b\d+(?:\.\d+)?\b")
_QUOTED_CLAIM = re.compile(r"[\"“][^\"”]{8,}[\"”]")

_CITE_MARKERS = re.compile(
    r"(?P<bracket>\[\d+(?:\s*[,;–-]\s*\d+)*\])|(?P<paren>\(\d+(?:\s*[,;]\s*\d+)*\))"
    r"|(?P<author>[\w\-]+\s+et\s+al\.?,?\s+\(?\d{4}\)?)",
)


# --------------------------------------------------------------------------
# BibTeX
# --------------------------------------------------------------------------

def parse_bibtex(text: str) -> List[Dict]:
    """Parse BibTeX entries with a brace-depth scanner.

    Handles multi-line values, nested braces in titles, and comments between
    entries; single-line entries are recognised because depth, not newlines,
    closes them.
    """
    entries: List[Dict] = []
    index = 0
    length = len(text)
    while index < length:
        at = text.find("@", index)
        if at == -1:
            break
        header = re.match(r"@(\w+)\s*\{", text[at:])
        if not header:
            index = at + 1
            continue
        kind = header.group(1).lower()
        if kind in ("comment", "preamble", "string"):
            index = at + header.end()
            continue
        body_start = at + header.end()
        depth, cursor = 1, body_start
        while cursor < length and depth:
            if text[cursor] == "{":
                depth += 1
            elif text[cursor] == "}":
                depth -= 1
            cursor += 1
        if depth:  # unbalanced entry; take what is there
            cursor = length
        body = text[body_start:cursor - 1]
        key_match = re.match(r"\s*([^,\s]+)\s*,", body)
        entry: Dict = {
            "key": key_match.group(1) if key_match else "",
            "type": kind,
            "raw": body.strip(),
        }
        fields: Dict[str, str] = {}
        for field_match in re.finditer(
            r"(\w+)\s*=\s*(\{.*?\}|\".*?\")\s*(?:,|$)", body, re.DOTALL
        ):
            name = field_match.group(1).lower()
            value = field_match.group(2)
            if value.startswith("{") or value.startswith('"'):
                value = value[1:-1]
            fields[name] = re.sub(r"\s+", " ", value).strip()
        entry["fields"] = fields
        entries.append(_entry_from_fields(entry))
        index = cursor
    return entries


# --------------------------------------------------------------------------
# Field assembly
# --------------------------------------------------------------------------

def _entry_from_fields(entry: Dict) -> Dict:
    fields = entry.get("fields", {})
    title = fields.get("title", "")
    authors = fields.get("author", "")
    year_source = fields.get("year", "") or fields.get("date", "")
    blob = " ".join([title, authors, fields.get("journal", ""), fields.get("doi", ""),
                     fields.get("url", ""), fields.get("eprint", ""), entry.get("raw", "")])
    candidate = {
        "key": entry.get("key", ""),
        "type": entry.get("type", ""),
        "title": title,
        "authors": authors,
        "year": year_source,
        "doi": normalize_doi(fields.get("doi", "") or blob),
        # An eprint field carries the bare arXiv number without the arXiv
        # prefix the extractor looks for, so prepend it for that field only.
        "arxiv_id": extract_arxiv_id(
            "arxiv " + (fields.get("eprint", "") or "")
        ) or extract_arxiv_id(fields.get("url", "") or blob),
        "pmid": extract_pmid(fields.get("pmid", "") or fields.get("note", "") or blob),
    }
    return candidate


def _entry_from_text(raw: str, position: int) -> Dict:
    """Build a reference candidate from a free-text reference string."""
    text = re.sub(r"\s+", " ", raw).strip()
    doi = normalize_doi(text)
    arxiv_id = extract_arxiv_id(text)
    pmid = extract_pmid(text)

    title = _extract_title_from_text(text)
    authors = ""
    year = ""
    year_match = re.search(r"\(?((?:19|20)\d{2})\)?", text)
    if year_match:
        year = year_match.group(1)
        before_year = text[:year_match.start()].strip()
        # Author block conventionally sits before the year, before the title.
        authors = re.split(r"[.:]|\s{2,}", before_year)[0].strip(" .,")
    return {
        "key": str(position),
        "type": "text",
        "title": title or "",
        "authors": authors,
        "year": year,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "pmid": pmid,
        "raw": text,
    }


def _extract_title_from_text(text: str) -> str:
    """Best-effort title extraction from a free-text reference.

    The dominant convention in numbered reference lists is
    ``Authors (Year). Title. Venue.`` so the primary strategy takes the
    sentence following the year marker. Quoted titles, markdown italics, and
    (for yearless references) the first substantial sentence serve as
    fallbacks.
    """
    quoted = re.search(r"[\"“]([^\"”]{12,})[\"”]", text)
    italic = re.search(r"\*([^*]{12,})\*", text)

    # Primary: the sentence right after the year (covers "(2017)." and
    # "2017." and "(2017a)." variants).
    after_year = re.search(
        r"\(?((?:19|20)\d{2})[a-z]?\)?\s*\.\s*([A-Z\"“].+?)(?=\.\s+[A-Z\"“]|\.$|$)",
        text,
    )
    if after_year:
        candidate = after_year.group(2).strip(" .,")
        if len(candidate.split()) >= 3:
            return candidate

    # Fallbacks.
    if quoted:
        return quoted.group(1).strip(" .,")
    if italic:
        return italic.group(1).strip(" .,")
    sentences = [s for s in re.split(r"(?<=[.?!])\s+", text) if len(s.split()) >= 3]
    return sentences[0].strip(" .,") if sentences else ""


# --------------------------------------------------------------------------
# Document segmentation
# --------------------------------------------------------------------------

def _split_reference_block(block: str) -> List[str]:
    """Split a reference section into entries.

    Prefers explicit numbering; falls back to blank-line separation; falls
    back further to one-entry-per-line for hanging-indent styles.
    """
    lines = block.splitlines()
    entries: List[str] = []
    current: List[str] = []

    numbered = re.compile(r"^\s*(?:\[\d+\]|\(\d+\)|\d+[.)])\s+")
    if sum(1 for line in lines if numbered.match(line)) >= 2:
        for line in lines:
            if numbered.match(line):
                if current:
                    entries.append(" ".join(current))
                    current = []
            current.append(line)
        if current:
            entries.append(" ".join(current))
        return [e for e in entries if e.strip()]

    paragraphs = re.split(r"\n\s*\n", block)
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in paragraphs if p.strip()]
    if len(paragraphs) >= 2:
        return paragraphs
    return [re.sub(r"\s+", " ", line).strip() for line in lines if line.strip()]


def parse_markdown(text: str) -> List[Dict]:
    """Extract references from a markdown/plain-text manuscript."""
    heading = REFERENCE_HEADINGS.search(text)
    if heading:
        block = text[heading.end():]
        # Stop at the next top-level heading after the reference section.
        next_heading = re.search(r"^#{1,2}\s+(?!.*references)", block, re.IGNORECASE | re.MULTILINE)
        if next_heading:
            block = block[:next_heading.start()]
    else:
        # No heading: treat the whole document and let entry patterns decide.
        block = text
    raw_entries = _split_reference_block(block)
    entries = []
    for position, raw in enumerate(raw_entries, start=1):
        cleaned = _ENTRY_PREFIX.sub("", raw)
        if len(cleaned.split()) < 4:
            continue  # too short to be a reference (stray headers, URLs)
        entries.append(_entry_from_text(cleaned, position))
    return entries


def parse_latex(text: str) -> List[Dict]:
    """Extract references from a LaTeX document (\\bibitem entries).

    ``\\bibitem[label]{key}`` and bare ``\\bibitem{key}`` are both handled;
    each item's body runs to the next \\bibitem or the end of the document.
    """
    text = _TEX_COMMENT.sub("", text)
    matches = list(_TEX_BIBITEM.finditer(text))
    entries: List[Dict] = []
    for index, match in enumerate(matches):
        label = (match.group(1) or "").strip()
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        raw = re.sub(r"\s+", " ", text[body_start:body_end]).strip()
        # Render common LaTeX markup down to plain text: \emph{x} -> x.
        raw = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{([^{}]*)\})?", r"\3", raw)
        raw = re.sub(r"[{}~]", " ", raw)
        if len(raw.split()) < 4:
            continue
        entry = _entry_from_text(raw, len(entries) + 1)
        if label:
            entry["key"] = label
        entries.append(entry)
    return entries


# --------------------------------------------------------------------------
# In-text citation extraction
# ---------------------------------------------------------------------------

def extract_in_text_citations(text: str) -> List[Dict]:
    """Pull checkable sentences with citation markers out of a manuscript.

    Returns sentences that carry a numeric/bracketed marker or an
    author-year mention AND at least one verifiable element (a statistic or
    a quoted phrase). Verifier scripts join these to reference entries by
    marker or by key.
    """
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", re.sub(r"\s+", " ", text))
    found: List[Dict] = []
    for sentence in sentences:
        if not (_NUMERIC_CLAIM.search(sentence) or _QUOTED_CLAIM.search(sentence)):
            continue
        markers: List[str] = []
        for match in _CITE_MARKERS.finditer(sentence):
            marker = match.group("bracket") or match.group("paren") or match.group("author")
            if marker:
                markers.append(marker.strip())
        if not markers:
            continue
        quote = _QUOTED_CLAIM.search(sentence)
        found.append(
            {
                "sentence": sentence.strip(),
                "markers": markers,
                "quote": quote.group(0).strip("\"“”") if quote else None,
            }
        )
    return found


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def detect_format(path: Path, forced: Optional[str] = None) -> str:
    if forced:
        return forced
    suffix = path.suffix.lower()
    if suffix == ".bib":
        return "bibtex"
    if suffix in (".tex",):
        return "latex"
    if suffix in (".md", ".markdown", ".txt"):
        return "markdown"
    text = path.read_text(encoding="utf-8", errors="replace")
    if "\\bibitem" in text or "\\begin{thebibliography}" in text:
        return "latex"
    if "@" in text and re.search(r"@\w+\s*\{", text):
        return "bibtex"
    return "markdown"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract a structured reference list from a manuscript "
        "(markdown, LaTeX, or BibTeX) as JSON for verify_references.py."
    )
    parser.add_argument("manuscript", help="path to the manuscript (.md/.tex) or bibliography (.bib)")
    parser.add_argument(
        "--format",
        choices=["markdown", "latex", "bibtex"],
        default=None,
        help="force a parser instead of detecting from the filename",
    )
    parser.add_argument(
        "--in-text",
        action="store_true",
        help="also extract checkable in-text citation sentences (markdown/latex inputs)",
    )
    parser.add_argument("--output", help="write JSON here instead of stdout")
    args = parser.parse_args(argv)

    path = Path(args.manuscript)
    if not path.is_file():
        parser.error(f"not a file: {path}")
    fmt = detect_format(path, args.format)
    text = path.read_text(encoding="utf-8", errors="replace")

    if fmt == "bibtex":
        references = parse_bibtex(text)
    elif fmt == "latex":
        references = parse_latex(text)
    else:
        references = parse_markdown(text)

    payload: Dict = {"format": fmt, "source": str(path), "count": len(references),
                     "references": references}
    if args.in_text and fmt != "bibtex":
        payload["in_text_citations"] = extract_in_text_citations(text)

    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(f"parsed {len(references)} references ({fmt}) -> {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
