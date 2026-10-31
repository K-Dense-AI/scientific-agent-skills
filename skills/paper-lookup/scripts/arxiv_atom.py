#!/usr/bin/env python3
"""Parse arXiv Atom XML into JSON records, catching arXiv's HTTP-200 failures.

arXiv has no JSON output, and its Atom feed has four traps that make hand-rolled
parsing quietly wrong (all documented in references/arxiv.md):

- The feed carries its own `<link>` before the first entry, so "the first link"
  is the query URL, not a paper.
- A malformed parameter returns HTTP 200, `totalResults` **1**, and a single
  entry titled `Error` -- which reads as a successful one-hit search.
- `<id>` is now `https://` and carries a version suffix (`1706.03762v7`).
- `<title>` and `<summary>` arrive hard-wrapped mid-sentence.

This script handles all four, exits **3** on the Error entry, and exits **5** when arXiv is
throttling -- which it signals with the bare plain-text body `Rate exceeded.`, not a feed.

    curl -s "https://export.arxiv.org/api/query?id_list=1706.03762" | python3 arxiv_atom.py -
    python3 arxiv_atom.py feed.xml --ids-only
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import InputError, collapse_ws, emit, fail, read_input  # noqa: E402

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}


def split_version(arxiv_id: str) -> tuple[str, str | None]:
    """`1706.03762v7` -> `("1706.03762", "7")`.

    The bare ID is what Semantic Scholar's `ARXIV:` prefix, a DOI, and a
    user-supplied ID all use, so comparing the versioned form against any of them
    fails. Both are returned rather than choosing one.
    """
    base, separator, version = arxiv_id.rpartition("v")
    if separator and version.isdigit() and base:
        return base, version
    return arxiv_id, None


def id_from_url(url: str) -> str:
    """The arXiv ID from an `<id>` URL, scheme-agnostically.

    Preserve the entire path after `/abs/`: old identifiers such as
    `hep-th/9901001` contain a slash.
    """
    from urllib.parse import urlsplit

    path = urlsplit(url).path.rstrip("/")
    return path.split("/abs/", 1)[1] if "/abs/" in path else path.rsplit("/", 1)[-1]


def link_for(entry: ET.Element, *, rel: str, mime: str | None = None) -> str | None:
    for link in entry.findall("atom:link", NS):
        if link.get("rel") != rel:
            continue
        if mime and link.get("type") != mime:
            continue
        return link.get("href")
    return None


def parse_entry(entry: ET.Element) -> dict[str, Any]:
    raw_id = collapse_ws(entry.findtext("atom:id", namespaces=NS))
    versioned = id_from_url(raw_id) if raw_id else ""
    arxiv_id, version = split_version(versioned)

    categories = [
        term
        for term in (category.get("term") for category in entry.findall("atom:category", NS))
        if term
    ]
    primary = entry.find("arxiv:primary_category", NS)

    return {
        "arxiv_id": arxiv_id,
        "arxiv_id_versioned": versioned or None,
        "version": version,
        "title": collapse_ws(entry.findtext("atom:title", namespaces=NS)),
        "abstract": collapse_ws(entry.findtext("atom:summary", namespaces=NS)),
        "authors": [
            collapse_ws(name)
            for name in (
                author.findtext("atom:name", namespaces=NS)
                for author in entry.findall("atom:author", NS)
            )
            if collapse_ws(name)
        ],
        "published": collapse_ws(entry.findtext("atom:published", namespaces=NS)) or None,
        "updated": collapse_ws(entry.findtext("atom:updated", namespaces=NS)) or None,
        "primary_category": primary.get("term") if primary is not None else None,
        "categories": categories,
        "doi": collapse_ws(entry.findtext("arxiv:doi", namespaces=NS)) or None,
        "journal_ref": collapse_ws(entry.findtext("arxiv:journal_ref", namespaces=NS)) or None,
        "comment": collapse_ws(entry.findtext("arxiv:comment", namespaces=NS)) or None,
        # Selected by rel/type, never by position: the feed's own <link> precedes
        # the entries and would otherwise be picked up as a paper URL.
        "abstract_url": link_for(entry, rel="alternate", mime="text/html"),
        "pdf_url": link_for(entry, rel="related", mime="application/pdf"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Parse an arXiv Atom feed into JSON records. Exits 3 when the feed is an "
            "arXiv error response, which arrives as HTTP 200 with totalResults 1 and a "
            "single entry titled 'Error'."
        ),
        epilog='curl -s "https://export.arxiv.org/api/query?id_list=1706.03762" | %(prog)s -',
    )
    parser.add_argument("source", help="path to an arXiv Atom XML file, or - for stdin")
    parser.add_argument("-o", "--output", help="write JSON here instead of stdout")
    parser.add_argument(
        "--ids-only",
        action="store_true",
        help="print one bare arXiv ID per line (version suffix stripped)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        xml_text = read_input(args.source)
    except InputError as error:
        fail(str(error))

    # Throttling is not XML. arXiv answers a rate-limited caller with the bare
    # plain-text body "Rate exceeded." -- 14 bytes, no feed, no status to key on --
    # so an XML parse error here is usually a pacing problem, not a bad response.
    if xml_text.strip().startswith("Rate exceeded"):
        fail(
            "arXiv is throttling: it returned the plain-text body 'Rate exceeded.' instead of a "
            "feed. Its limit is one request per three seconds; wait and retry, and serialize "
            "arXiv calls rather than running them alongside other work.",
            code=5,
        )

    try:
        feed = ET.fromstring(xml_text)
    except ET.ParseError as error:
        fail(
            f"not parseable as XML: {error}. The first 100 bytes were: "
            f"{xml_text[:100]!r} -- arXiv returns plain text rather than a feed for "
            "throttling and some gateway errors."
        )

    if feed.tag != f"{{{NS['atom']}}}feed":
        fail("not an arXiv Atom feed; check for an HTML/XML error response")
    entries = feed.findall("atom:entry", NS)

    # The error check must precede any other interpretation: the error feed is a
    # structurally valid one-hit search result.
    for entry in entries:
        if collapse_ws(entry.findtext("atom:title", namespaces=NS)) == "Error":
            reason = collapse_ws(entry.findtext("atom:summary", namespaces=NS))
            fail(f"arXiv returned an error feed: {reason or 'no reason given'}", code=3)

    total = collapse_ws(feed.findtext("opensearch:totalResults", namespaces=NS))
    # The feed <title> echoes the query as arXiv actually ran it. An unrecognized
    # field prefix is silently rewritten to `all:`, so this is the only way to see
    # that the executed query is not the one that was sent.
    echoed_query = collapse_ws(feed.findtext("atom:title", namespaces=NS))

    records = [parse_entry(entry) for entry in entries]

    if args.ids_only:
        text = "".join(f"{record['arxiv_id']}\n" for record in records if record["arxiv_id"])
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0

    payload: dict[str, Any] = {
        "total_results": int(total) if total.isdigit() else None,
        "returned": len(records),
        "query_as_executed": echoed_query or None,
        "entries": records,
    }
    if not records:
        payload["note"] = (
            "zero entries with HTTP 200 is arXiv's genuine no-match response, including for "
            "an unknown ID in id_list; report it as 'not found in arXiv', not as a failure"
        )
    emit(payload, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
