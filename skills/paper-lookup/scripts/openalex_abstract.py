#!/usr/bin/env python3
"""Reconstruct OpenAlex abstracts from `abstract_inverted_index`.

OpenAlex never returns an abstract as a string. It returns
`{"word": [positions], ...}`, and the caller has to invert it. The naive
inversion loses words: building `{position: word}` and joining silently drops
every duplicate position, and real payloads do contain them.

Reads a single work object, a list of works, or a `/works` list response
(`{"meta": ..., "results": [...]}`). Emits each work's id, doi, title, and
reconstructed abstract, plus a per-work note when the abstract could not be
rebuilt.

    curl -s "https://api.openalex.org/works/doi:10.7717/peerj.4375" | python3 openalex_abstract.py -
    python3 openalex_abstract.py results.json --text-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import InputError, collapse_ws, emit, fail, load_json  # noqa: E402


def reconstruct(inverted_index: dict[str, list[int]]) -> tuple[str, list[str]]:
    """Rebuild abstract text from an inverted index.

    Returns the text and any anomalies worth reporting. Words are bucketed by
    position rather than assigned, so a position claimed by two words keeps both
    (joined in index order) instead of one overwriting the other.
    """
    anomalies: list[str] = []
    buckets: dict[int, list[str]] = {}

    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            anomalies.append(f"positions for {word!r} were {type(positions).__name__}, not a list")
            continue
        for position in positions:
            if not isinstance(position, int) or isinstance(position, bool):
                anomalies.append(f"non-integer position {position!r} for {word!r}")
                continue
            if position < 0:
                anomalies.append(f"negative position {position} for {word!r}")
                continue
            buckets.setdefault(position, []).append(word)

    if not buckets:
        return "", anomalies

    collisions = sum(1 for words in buckets.values() if len(words) > 1)
    if collisions:
        anomalies.append(
            f"{collisions} position(s) claimed by more than one token; kept all, joined in index order"
        )

    ordered = sorted(buckets)
    missing = ordered[-1] - ordered[0] + 1 - len(ordered)
    if missing:
        anomalies.append(f"{missing} position(s) absent from the index; the abstract has gaps")
    if ordered[0] != 0:
        anomalies.append(f"index starts at position {ordered[0]}, not 0; leading words may be missing")

    text = " ".join(" ".join(buckets[position]) for position in ordered)
    return collapse_ws(text), anomalies


def works_from(payload: Any) -> list[dict[str, Any]]:
    """Accept a single work, a bare list, or a `/works` list response."""
    if isinstance(payload, dict):
        if "error" in payload or ("message" in payload and "id" not in payload and "results" not in payload):
            raise InputError("OpenAlex returned an error object, not a work")
        if isinstance(payload.get("results"), list):
            return [w for w in payload["results"] if isinstance(w, dict)]
        if not payload.get("id"):
            raise InputError("OpenAlex object lacks a work id/results array")
        return [payload]
    if isinstance(payload, list):
        return [w for w in payload if isinstance(w, dict)]
    raise InputError(f"expected a work object or list, got {type(payload).__name__}")


def summarize(work: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": work.get("id"),
        "doi": work.get("doi"),
        "title": collapse_ws(work.get("title") or work.get("display_name")),
        "publication_year": work.get("publication_year"),
    }

    index = work.get("abstract_inverted_index")
    if isinstance(index, dict) and index:
        text, anomalies = reconstruct(index)
        record["abstract"] = text
        record["abstract_word_count"] = len(text.split()) if text else 0
        if anomalies:
            record["abstract_warnings"] = anomalies
    else:
        record["abstract"] = None
        # Distinguish the two reasons an abstract is missing: the field was not
        # requested, or OpenAlex has none. Reporting them the same way would let
        # a `select=` mistake read as a coverage gap.
        record["abstract_warnings"] = [
            "no abstract_inverted_index on this work: either OpenAlex has no abstract for it, "
            "or the field was excluded by `select=` -- re-request without `select` to tell which"
        ]
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reconstruct readable abstracts from OpenAlex abstract_inverted_index payloads."
        ),
        epilog='curl -s "https://api.openalex.org/works/doi:10.7717/peerj.4375" | %(prog)s -',
    )
    parser.add_argument("source", help="path to an OpenAlex JSON payload, or - for stdin")
    parser.add_argument("-o", "--output", help="write JSON here instead of stdout")
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="print just the abstract text, one blank-line-separated block per work",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        payload = load_json(args.source)
        works = works_from(payload)
    except InputError as error:
        fail(str(error))

    if not works:
        fail("payload contained no work objects")

    records = [summarize(work) for work in works]

    if args.text_only:
        blocks = [record["abstract"] for record in records if record["abstract"]]
        if not blocks:
            fail("no abstracts could be reconstructed from this payload")
        text = "\n\n".join(blocks) + "\n"
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0

    emit(
        {
            "count": len(records),
            "with_abstract": sum(1 for r in records if r["abstract"]),
            "works": records,
        },
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
