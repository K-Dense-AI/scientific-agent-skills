#!/usr/bin/env python3
"""
Fetch and parse content from the Hugging Science catalog (huggingscience.co).

The catalog ships LLM-friendly markdown at three endpoints:
  - https://huggingscience.co/llms.txt        (compact index)
  - https://huggingscience.co/llms-full.txt   (every entry, every domain)
  - https://huggingscience.co/topics/<slug>.md (one domain at a time)

Each entry in a topic file looks like:

    ### org/name-or-title
    - **Type**: <category>
    - **Tags**: <comma-separated>
    - **HuggingFace**: <url>     (or **Link**: <url> for blog posts)
    - **Author**: <username>     (blog posts only)
    - **Date**: <YYYY-MM-DD>     (blog posts only)

    <one-line description>

Usage examples:
    fetch_catalog.py topics                          # list all topic slugs
    fetch_catalog.py topic biology                   # fetch and pretty-print a topic
    fetch_catalog.py topic materials-science --filter models
    fetch_catalog.py topic chemistry --tag "drug discovery"
    fetch_catalog.py all                             # dump llms-full.txt
    fetch_catalog.py search "protein language"      # substring search across llms-full.txt
    fetch_catalog.py json topic biology              # structured JSON output

Stdlib only — no external deps required.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict, field
from typing import Iterable

BASE = "https://huggingscience.co"

KNOWN_TOPICS = [
    "astronomy",
    "benchmark",
    "biology",
    "biotechnology",
    "chemistry",
    "climate",
    "conservation",
    "earth-science",
    "ecology",
    "energy",
    "engineering",
    "genomics",
    "materials-science",
    "mathematics",
    "medicine",
    "physics",
    "scientific-reasoning",
]


@dataclass
class Entry:
    title: str
    section: str  # "datasets" | "models" | "blog posts" | "unknown"
    type: str = ""
    tags: list[str] = field(default_factory=list)
    url: str = ""
    author: str = ""
    date: str = ""
    description: str = ""

    def matches_filter(self, kind: str | None, tag: str | None) -> bool:
        if kind:
            section_aliases = {
                "datasets": {"datasets", "dataset"},
                "models": {"models", "model"},
                "blogs": {"blog posts", "blog", "blogs"},
            }
            wanted = section_aliases.get(kind.lower(), {kind.lower()})
            if self.section.lower() not in wanted:
                return False
        if tag:
            t = tag.lower()
            if not any(t in tg.lower() for tg in self.tags) and t not in self.type.lower():
                return False
        return True


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "hugging-science-skill/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} fetching {url}: {e.reason}")
    except urllib.error.URLError as e:
        sys.exit(f"Network error fetching {url}: {e.reason}")


def parse_markdown(md: str) -> list[Entry]:
    """Parse a topic file or llms-full.txt into a list of Entry records.

    Strategy: track the most recent H2 (## Section) as the section label;
    each H3 (### Title) starts a new entry, with bulleted metadata and a
    free-text description until the next H3 or H2."""
    entries: list[Entry] = []
    current_section = "unknown"
    current: Entry | None = None
    desc_lines: list[str] = []

    def finalize(e: Entry | None, desc: list[str]) -> None:
        if e is None:
            return
        e.description = " ".join(line.strip() for line in desc if line.strip()).strip()
        entries.append(e)

    for raw in md.splitlines():
        line = raw.rstrip()
        # Section header (H2)
        m2 = re.match(r"^##\s+(.+?)\s*$", line)
        if m2 and not line.startswith("###"):
            finalize(current, desc_lines)
            current, desc_lines = None, []
            section = m2.group(1).strip().lower()
            section = section.split(" (")[0]  # strip "(N)" suffix if present
            current_section = section
            continue
        # Entry header (H3)
        m3 = re.match(r"^###\s+(.+?)\s*$", line)
        if m3:
            finalize(current, desc_lines)
            current = Entry(title=m3.group(1).strip(), section=current_section)
            desc_lines = []
            continue
        if current is None:
            continue
        # Metadata bullet
        mb = re.match(r"^\s*[-*]\s+\*\*(\w+)\*\*\s*:\s*(.+?)\s*$", line)
        if mb:
            key, value = mb.group(1).lower(), mb.group(2).strip()
            if key == "type":
                current.type = value
            elif key == "tags":
                current.tags = [t.strip() for t in value.split(",") if t.strip()]
            elif key in ("huggingface", "link", "url"):
                current.url = value
            elif key == "author":
                current.author = value
            elif key == "date":
                current.date = value
            continue
        # Otherwise treat as description
        desc_lines.append(line)

    finalize(current, desc_lines)
    return entries


def render_entry(e: Entry) -> str:
    lines = [f"### {e.title}"]
    if e.type:
        lines.append(f"- Type: {e.type}")
    if e.tags:
        lines.append(f"- Tags: {', '.join(e.tags)}")
    if e.url:
        lines.append(f"- URL: {e.url}")
    if e.author:
        lines.append(f"- Author: {e.author}")
    if e.date:
        lines.append(f"- Date: {e.date}")
    if e.description:
        lines.append("")
        lines.append(e.description)
    return "\n".join(lines)


def render_entries(entries: Iterable[Entry], group_by_section: bool = True) -> str:
    entries = list(entries)
    if not entries:
        return "(no entries matched)"
    if not group_by_section:
        return "\n\n".join(render_entry(e) for e in entries)
    by_section: dict[str, list[Entry]] = {}
    for e in entries:
        by_section.setdefault(e.section, []).append(e)
    out = []
    for section, items in by_section.items():
        out.append(f"## {section.title()} ({len(items)})")
        out.append("")
        for e in items:
            out.append(render_entry(e))
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def cmd_topics(_: argparse.Namespace) -> None:
    print("Known Hugging Science topic slugs (use as `topic <slug>`):\n")
    for t in KNOWN_TOPICS:
        print(f"  {t}")
    print(
        "\nSlugs are best-effort; if a topic 404s, fetch llms.txt directly to see the "
        "live list:\n  python fetch_catalog.py raw llms"
    )


def cmd_topic(args: argparse.Namespace) -> None:
    slug = args.slug.strip().lower().replace("_", "-").replace(" ", "-")
    md = fetch(f"{BASE}/topics/{slug}.md")
    entries = parse_markdown(md)
    entries = [e for e in entries if e.matches_filter(args.filter, args.tag)]
    if args.format == "json":
        print(json.dumps([asdict(e) for e in entries], indent=2))
    else:
        print(f"# Hugging Science: {slug} ({len(entries)} entries)\n")
        print(render_entries(entries))


def cmd_all(args: argparse.Namespace) -> None:
    md = fetch(f"{BASE}/llms-full.txt")
    if args.raw:
        print(md)
        return
    entries = parse_markdown(md)
    entries = [e for e in entries if e.matches_filter(args.filter, args.tag)]
    if args.format == "json":
        print(json.dumps([asdict(e) for e in entries], indent=2))
    else:
        print(f"# Hugging Science: full catalog ({len(entries)} entries)\n")
        print(render_entries(entries))


def cmd_search(args: argparse.Namespace) -> None:
    md = fetch(f"{BASE}/llms-full.txt")
    entries = parse_markdown(md)
    needle = args.query.lower()
    matched = [
        e
        for e in entries
        if needle in e.title.lower()
        or needle in e.description.lower()
        or needle in e.type.lower()
        or any(needle in t.lower() for t in e.tags)
    ]
    matched = [e for e in matched if e.matches_filter(args.filter, args.tag)]
    if args.format == "json":
        print(json.dumps([asdict(e) for e in matched], indent=2))
    else:
        print(f"# Search '{args.query}' — {len(matched)} match(es)\n")
        print(render_entries(matched))


def cmd_raw(args: argparse.Namespace) -> None:
    name = args.name.lower()
    if name in ("llms", "index"):
        print(fetch(f"{BASE}/llms.txt"))
    elif name in ("full", "llms-full"):
        print(fetch(f"{BASE}/llms-full.txt"))
    else:
        sys.exit(f"unknown raw target: {name} (try 'llms' or 'full')")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("topics", help="list known topic slugs")
    sp.set_defaults(func=cmd_topics)

    sp = sub.add_parser("topic", help="fetch a single topic file")
    sp.add_argument("slug", help="topic slug, e.g. biology, materials-science")
    sp.add_argument("--filter", choices=["datasets", "models", "blogs"], help="restrict to one section")
    sp.add_argument("--tag", help="restrict to entries with a tag substring (case-insensitive)")
    sp.add_argument("--format", choices=["markdown", "json"], default="markdown")
    sp.set_defaults(func=cmd_topic)

    sp = sub.add_parser("all", help="fetch the full llms-full.txt")
    sp.add_argument("--raw", action="store_true", help="print the raw file untouched")
    sp.add_argument("--filter", choices=["datasets", "models", "blogs"], help="restrict to one section")
    sp.add_argument("--tag", help="restrict to entries with a tag substring")
    sp.add_argument("--format", choices=["markdown", "json"], default="markdown")
    sp.set_defaults(func=cmd_all)

    sp = sub.add_parser("search", help="substring search across the full catalog")
    sp.add_argument("query")
    sp.add_argument("--filter", choices=["datasets", "models", "blogs"], help="restrict to one section")
    sp.add_argument("--tag", help="restrict to entries with a tag substring")
    sp.add_argument("--format", choices=["markdown", "json"], default="markdown")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("raw", help="dump a raw catalog file")
    sp.add_argument("name", help="'llms' for llms.txt, 'full' for llms-full.txt")
    sp.set_defaults(func=cmd_raw)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
