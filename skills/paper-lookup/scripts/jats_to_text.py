#!/usr/bin/env python3
"""Turn PMC / Europe PMC JATS XML into sectioned text, refusing metadata-only XML.

The failure this exists to stop: NCBI eFetch returns **HTTP 200** and a
well-formed `<pmc-articleset>` for articles whose publisher forbids XML
redistribution -- containing `<front>` metadata, no `<body>`, and the reason in
an XML *comment* that every standard parser discards. An agent that fetches,
parses, and reports "full text retrieved" has retrieved the title and author
list. See the hazard section of references/pmc.md.

So this script exits **2** when there is no `<body>`, and surfaces the discarded
comment as the explanation. Metadata is still emitted, clearly labelled as
metadata, so the caller can fall back to Europe PMC (a clean 404), Unpaywall, or
the abstract without a second fetch.

Handles both wrappers: eFetch's `<pmc-articleset><article>` and Europe PMC's bare
`<article>`.

    curl -s ".../efetch.fcgi?db=pmc&id=7029759&retmode=xml" | python3 jats_to_text.py -
    python3 jats_to_text.py article.xml --sections METHODS,RESULTS --text-only
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import InputError, collapse_ws, emit, fail, read_input  # noqa: E402

#: Tags whose text is not part of the reading order. `xref` and `label` are
#: excluded so citation markers and "Figure 1" labels do not land mid-sentence.
SKIP_TAGS = frozenset({"xref", "label", "table-wrap", "graphic", "media", "inline-formula"})

#: Block-level tags that must not run into their neighbours.
#:
#: NCBI serializes JATS with no whitespace between elements, so
#: `<title>Introduction</title><p>A mysterious illness...` concatenates to
#: "IntroductionA mysterious illness" unless a separator is inserted at these
#: boundaries. Inline tags (`italic`, `sup`, `xref`) are deliberately absent --
#: separating those would break words apart instead.
BLOCK_TAGS = frozenset(
    {
        "abstract",
        "body",
        "caption",
        "def-item",
        "disp-quote",
        "list-item",
        "p",
        "sec",
        "statement",
        "td",
        "th",
        "title",
        "tr",
    }
)

#: Publisher restriction notices arrive only as XML comments.
RESTRICTION_HINT = re.compile(r"does not allow|not allow downloading|restricted", re.IGNORECASE)


def parse(xml_text: str) -> ET.Element:
    try:
        return ET.fromstring(xml_text)
    except ET.ParseError as error:
        raise InputError(f"not parseable as XML: {error}") from error


def find_article(root: ET.Element) -> ET.Element:
    """The `<article>` element, whichever wrapper it arrived in."""
    if root.tag == "article":
        return root
    article = root.find(".//article")
    if article is None:
        raise InputError(
            f"no <article> element (root was <{root.tag}>); "
            "this is not a JATS document -- check whether the response was an error page"
        )
    return article


def comments_in(xml_text: str) -> list[str]:
    """XML comments, which ElementTree drops.

    Read from the raw text on purpose: the publisher-restriction notice that
    explains a missing `<body>` exists *only* as a comment, so parsing it away is
    what makes the failure silent.
    """
    return [collapse_ws(match) for match in re.findall(r"<!--(.*?)-->", xml_text, re.DOTALL)]


def element_text(element: ET.Element) -> str:
    """Flattened text of an element, skipping non-reading-order tags."""
    parts: list[str] = []

    def walk(node: ET.Element) -> None:
        if node.tag in SKIP_TAGS:
            # Keep the tail: text following an <xref> continues the sentence.
            if node.tail:
                parts.append(node.tail)
            return
        block = node.tag in BLOCK_TAGS
        if block:
            parts.append(" ")
        if node.text:
            parts.append(node.text)
        for child in node:
            walk(child)
        if block:
            parts.append(" ")
        if node.tail:
            parts.append(node.tail)

    walk(element)
    return collapse_ws("".join(parts))


def section_title(section: ET.Element) -> str:
    title = section.find("title")
    return element_text(title) if title is not None else ""


def collect_sections(body: ET.Element) -> list[dict[str, Any]]:
    """Top-level `<sec>` blocks, each with its nested subsection text inlined."""
    sections: list[dict[str, Any]] = []

    top_level = body.findall("sec")
    if not top_level:
        # Some articles put paragraphs straight under <body> with no sections.
        text = element_text(body)
        return [{"title": "", "sec_type": None, "text": text}] if text else []

    for section in top_level:
        sections.append(
            {
                "title": section_title(section),
                "sec_type": section.get("sec-type"),
                "text": element_text(section),
            }
        )
    return sections


#: JATS `pub-id-type` values, mapped to the field names this script emits.
#: PMC tags its own accession as `pmcid` (the bare `pmc` form appears in older
#: documents), alongside `pmcid-ver`/`pmcaid`/`pmcaiid` variants that are not the
#: canonical PMCID and must not be mistaken for it.
ID_TYPES = {"pmid": "pmid", "pmcid": "pmcid", "pmc": "pmcid", "doi": "doi"}


def extract_metadata(article: ET.Element) -> dict[str, Any]:
    front = article.find("front")
    metadata: dict[str, Any] = {
        "title": None,
        "journal": None,
        "pmid": None,
        "pmcid": None,
        "doi": None,
        "authors": [],
        "abstract": None,
    }
    if front is None:
        return metadata

    title = front.find(".//title-group/article-title")
    if title is not None:
        metadata["title"] = element_text(title)

    journal = front.find(".//journal-title")
    if journal is not None:
        metadata["journal"] = element_text(journal)

    # First occurrence per type wins. F1000Research and similar journals nest peer
    # review reports as sub-articles with their own DOIs; last-wins would report a
    # review's DOI as the article's.
    for article_id in front.findall(".//article-id"):
        field_name = ID_TYPES.get(article_id.get("pub-id-type") or "")
        if field_name and metadata[field_name] is None:
            metadata[field_name] = collapse_ws(article_id.text)

    for contributor in front.findall(".//contrib"):
        surname = contributor.find(".//surname")
        given = contributor.find(".//given-names")
        name = " ".join(
            part
            for part in (
                element_text(given) if given is not None else "",
                element_text(surname) if surname is not None else "",
            )
            if part
        )
        if name:
            metadata["authors"].append(name)

    abstract = front.find(".//abstract")
    if abstract is not None:
        metadata["abstract"] = element_text(abstract)

    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert PMC/Europe PMC JATS XML to sectioned text. Exits 2 when the document "
            "carries no <body>, which is how eFetch signals a non-open-access article "
            "while still returning HTTP 200."
        ),
        epilog="python3 %(prog)s article.xml --sections METHODS,RESULTS",
    )
    parser.add_argument("source", help="path to a JATS XML file, or - for stdin")
    parser.add_argument("-o", "--output", help="write here instead of stdout")
    parser.add_argument(
        "--sections",
        help=(
            "comma-separated section filter, matched case-insensitively against the "
            "section title and sec-type (e.g. METHODS,RESULTS)"
        ),
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="emit plain text rather than JSON",
    )
    parser.add_argument(
        "--allow-metadata-only",
        action="store_true",
        help=(
            "exit 0 instead of 2 when there is no <body>. Only for callers that have "
            "explicitly decided metadata is enough -- the default refusal is the point."
        ),
    )
    return parser


def matches(section: dict[str, Any], wanted: list[str]) -> bool:
    haystack = f"{section['title']} {section['sec_type'] or ''}".lower()
    return any(want in haystack for want in wanted)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        xml_text = read_input(args.source)
        root = parse(xml_text)
        article = find_article(root)
    except InputError as error:
        fail(str(error))

    metadata = extract_metadata(article)
    body = article.find("body")

    if body is None:
        comments = comments_in(xml_text)
        restriction = next((c for c in comments if RESTRICTION_HINT.search(c)), None)
        payload = {
            "full_text_available": False,
            "reason": restriction
            or "document has no <body> element and gave no stated reason",
            "metadata": metadata,
            "guidance": (
                "This is metadata only, not full text. Do not present it as the article. "
                "Try Europe PMC /{PMCID}/fullTextXML (returns 404 rather than a bodyless 200), "
                "consult PMC Article Datasets for supported bulk access, or fall back to "
                "Unpaywall/CORE for an open-access copy."
            ),
        }
        if comments:
            payload["xml_comments"] = comments
        emit(payload, args.output)
        if args.allow_metadata_only:
            return 0
        fail(
            "no <body> element: this document is metadata only, not full text"
            + (f" -- {restriction}" if restriction else ""),
            code=2,
        )

    sections = collect_sections(body)
    if args.sections:
        wanted = [part.strip().lower() for part in args.sections.split(",") if part.strip()]
        selected = [section for section in sections if matches(section, wanted)]
        if not selected:
            available = ", ".join(s["title"] or s["sec_type"] or "(untitled)" for s in sections)
            fail(f"no section matched {args.sections!r}; available: {available}")
        sections = selected

    if args.text_only:
        blocks = []
        if metadata["title"]:
            blocks.append(metadata["title"])
        for section in sections:
            heading = section["title"]
            blocks.append(f"{heading}\n{section['text']}" if heading else section["text"])
        text = "\n\n".join(blocks) + "\n"
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0

    emit(
        {
            "full_text_available": True,
            "metadata": metadata,
            "section_count": len(sections),
            "word_count": sum(len(section["text"].split()) for section in sections),
            "sections": sections,
        },
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
