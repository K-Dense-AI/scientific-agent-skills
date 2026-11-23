"""Parse data, never execute JavaScript or instructions from remote responses."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from transport import BASE, RMBaseError


class HTMLData(HTMLParser):
    """Table stack keeps nested tables separate from their containing cells."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.stack, self.text, self.links = [], [], [], []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self.skip += 1
        if self.skip:
            return
        if tag == "table":
            table = {"attrs": attrs, "rows": [], "row": None, "cell": None}
            self.tables.append(table)
            self.stack.append(table)
        elif self.stack and tag == "tr":
            self.stack[-1]["row"] = []
        elif self.stack and tag in ("td", "th"):
            self.stack[-1]["cell"] = {"tag": tag, "text": [], "links": []}
        if tag in ("a", "img"):
            target = attrs.get("href") if tag == "a" else attrs.get("src")
            if target:
                url = urljoin(BASE, target)
                p = urlsplit(url)
                if p.scheme in ("http", "https") and p.hostname and not p.username and not p.password:
                    self.links.append(url)
                    if self.stack and self.stack[-1]["cell"] is not None:
                        self.stack[-1]["cell"]["links"].append(url)
        if tag == "br":
            self.handle_data(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or not self.stack:
            return
        table = self.stack[-1]
        if tag in ("td", "th") and table["cell"] is not None:
            cell = table["cell"]
            cell["text"] = " ".join("".join(cell["text"]).split())
            if table["row"] is not None:
                table["row"].append(cell)
            table["cell"] = None
        elif tag == "tr" and table["row"] is not None:
            table["rows"].append(table["row"])
            table["row"] = None
        elif tag == "table":
            self.stack.pop()

    def handle_data(self, text):
        if not self.skip:
            self.text.append(text)
            if self.stack and self.stack[-1]["cell"] is not None:
                self.stack[-1]["cell"]["text"].append(text)


def html_document(raw):
    try:
        text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
    except UnicodeDecodeError as exc:
        raise RMBaseError("schema_changed", "RMBase returned non-UTF-8 content.", 4) from exc
    parser = HTMLData()
    parser.feed(text)
    return parser


def normalize(value):
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if isinstance(value, str) and re.search(r"<[A-Za-z/!]", value):
        doc = html_document(value)
        return {"text": " ".join("".join(doc.text).split()), "links": sorted(set(doc.links))}
    return value


def json_rows(raw, required=(), *, clean_html=True):
    try:
        rows = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise RMBaseError("schema_changed", "Expected a JSON array from RMBase; received a different response.", 4) from exc
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise RMBaseError("schema_changed", "Expected an array of RMBase records.", 4)
    if any(not set(required).issubset(row) for row in rows):
        raise RMBaseError("schema_changed", "Required RMBase fields are missing.", 4)
    return normalize(rows) if clean_html else rows


def table_records(table):
    rows = [row for row in table["rows"] if row]
    if not rows or not all(c["tag"] == "th" for c in rows[0]):
        return None
    headers = [c["text"] for c in rows[0]]
    if len(set(headers)) != len(headers):
        raise RMBaseError("schema_changed", "Duplicate HTML table headers.", 4)
    result = []
    for row in rows[1:]:
        if len(row) != len(headers):
            raise RMBaseError("schema_changed", "HTML table column count changed.", 4)
        record = {name: cell["text"] for name, cell in zip(headers, row)}
        links = sorted({link for cell in row for link in cell["links"]})
        if links:
            record["source_links"] = links
        result.append(record)
    return result


def gene_sites(raw):
    doc = html_document(raw)
    for table in doc.tables:
        if table["attrs"].get("id") == "resultTable":
            rows = table_records(table)
            if rows is None or (rows and not {"Mod ID", "Mod Site Loc", "Mod Type"}.issubset(rows[0])):
                break
            return rows
    raise RMBaseError("schema_changed", "Gene detail table is missing or changed.", 4)


def modification_detail(raw, expected_id):
    doc = html_document(raw)
    for table in doc.tables:
        fields = {}
        for row in table["rows"]:
            for i in range(len(row) - 1):
                if row[i]["tag"] == "th" and row[i + 1]["tag"] == "td":
                    fields[row[i]["text"]] = row[i + 1]["text"]
        if "mod ID" not in fields:
            continue
        if fields["mod ID"] == "":
            return []
        if fields["mod ID"] != expected_id or "mod Site" not in fields:
            raise RMBaseError("schema_changed", "Modification identity does not match the requested record.", 4)
        # Observed missing-ID page echoes the query and renders this exact empty
        # location, plus an empty modification type/sequence. Its support count
        # misleadingly says 1; do not treat that placeholder as a real record.
        if fields["mod Site"] == ":-:" and fields.get("mod Type") == "" and fields.get("Sequence") == "":
            return []
        if not fields.get("mod Type") or not fields.get("Sequence"):
            raise RMBaseError("schema_changed", "Modification fields are incomplete.", 4)
        related = []
        for child in doc.tables:
            records = table_records(child)
            if records is not None:
                related.append({"columns": [c["text"] for c in child["rows"][0]], "records": records})
        pmids = sorted(set(re.findall(r"\b\d{6,9}\b", fields.get("PubMed ID", ""))))
        return [{"modID": expected_id, "fields": fields, "related_tables": related, "pmids": pmids}]
    raise RMBaseError("schema_changed", "Modification detail table is missing; this is not evidence of absence.", 4)


def validate_bed(data):
    if not data or len(data) >= 2_000_000:
        raise RMBaseError("invalid_bed", "BED6 must be nonempty and smaller than 2 MB.")
    try:
        lines = data.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError as exc:
        raise RMBaseError("invalid_bed", "BED6 must be UTF-8 text.") from exc
    names, count = set(), 0
    for number, line in enumerate(lines, 1):
        if not line.strip() or line.startswith(("#", "track ", "browser ")):
            continue
        cols = line.split("\t")
        valid = len(cols) == 6
        if valid:
            chrom, start, end, name, score, strand = cols
            valid = (bool(re.fullmatch(r"[A-Za-z0-9_.-]+", chrom))
                     and start.isascii() and start.isdigit() and end.isascii() and end.isdigit()
                     and int(start) < int(end) and bool(re.fullmatch(r"[A-Za-z0-9_.:-]+", name))
                     and name not in names and score.isascii() and score.isdigit()
                     and 0 <= int(score) <= 1000 and strand in {"+", "-", "."})
        if not valid:
            raise RMBaseError("invalid_bed", f"Invalid BED6 row {number}; check columns, coordinates, score, strand and unique names.")
        names.add(name)
        count += 1
    if not count:
        raise RMBaseError("invalid_bed", "BED6 contains no intervals.")
    return count
