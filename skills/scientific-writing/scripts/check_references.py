"""Check local reference identifiers and duplicates without resolving them."""

from __future__ import annotations

import argparse
import re
import unicodedata
from typing import Any

from _common import (
    InputError,
    Issue,
    emit_report,
    is_nonempty_string,
    issue,
    read_json,
    require_list,
    require_object,
    run,
)
from validate_manifest import validate_source_manifest

TOOL = "check_references"
EVIDENCE_ID_RE = re.compile(r"^E[0-9]{3,8}$")
DOI_RE = re.compile(r"^10\.[0-9]{4,9}/\S+$", re.IGNORECASE)
PMID_RE = re.compile(r"^[1-9][0-9]{0,8}$")
PMCID_RE = re.compile(r"^PMC[1-9][0-9]{0,8}$", re.IGNORECASE)
URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)


def normalize_doi(value: str) -> str:
    normalized = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    return normalized.rstrip(".,;")


def normalize_title(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value).casefold()
    tokens: list[str] = []
    token: list[str] = []
    for char in decomposed:
        if char.isalnum() or (token and unicodedata.category(char).startswith("M")):
            token.append(char)
        elif token:
            tokens.append("".join(token))
            token = []
    if token:
        tokens.append("".join(token))
    return " ".join(tokens)


def normalize_isbn(value: str) -> str:
    return re.sub(r"[^0-9Xx]", "", value)


def valid_isbn(value: str) -> bool:
    normalized = normalize_isbn(value)
    if len(normalized) == 10:
        if not re.fullmatch(r"[0-9]{9}[0-9Xx]", normalized):
            return False
        total = sum(
            (10 - index) * (10 if char.lower() == "x" else int(char))
            for index, char in enumerate(normalized)
        )
        return total % 11 == 0
    if len(normalized) == 13 and normalized.isdigit():
        total = sum(
            int(char) * (1 if index % 2 == 0 else 3)
            for index, char in enumerate(normalized)
        )
        return total % 10 == 0
    return False


def _record_duplicate(
    seen: dict[str, str],
    normalized: str,
    evidence_id: str,
    code: str,
    issues: list[Issue],
) -> None:
    if not normalized:
        return
    prior = seen.get(normalized)
    if prior is not None and prior != evidence_id:
        issues.append(
            issue(
                "error",
                code,
                location=prior,
                item_id=evidence_id,
            )
        )
    else:
        seen[normalized] = evidence_id


def check_sources(data: dict[str, Any]) -> tuple[list[Issue], int]:
    issues = validate_source_manifest(data, require_verified=False)
    sources = require_list(data.get("sources"), "sources")
    evidence_ids: set[str] = set()
    seen_dois: dict[str, str] = {}
    seen_pmids: dict[str, str] = {}
    seen_pmcids: dict[str, str] = {}
    seen_isbns: dict[str, str] = {}
    seen_titles: dict[str, str] = {}

    for index, raw_source in enumerate(sources):
        source = require_object(raw_source, f"sources[{index}]")
        evidence_id = source.get("evidence_id")
        if not isinstance(evidence_id, str) or not EVIDENCE_ID_RE.fullmatch(
            evidence_id
        ):
            issues.append(
                issue("error", "INVALID_EVIDENCE_ID", location=f"sources[{index}]")
            )
            continue
        if evidence_id in evidence_ids:
            issues.append(issue("error", "DUPLICATE_EVIDENCE_ID", item_id=evidence_id))
            continue
        evidence_ids.add(evidence_id)

        title = source.get("title")
        if is_nonempty_string(title):
            _record_duplicate(
                seen_titles,
                normalize_title(str(title)),
                evidence_id,
                "POSSIBLE_DUPLICATE_TITLE",
                issues,
            )

        identifiers = require_object(
            source.get("identifiers"), f"sources[{index}].identifiers"
        )
        doi = identifiers.get("doi")
        if is_nonempty_string(doi):
            normalized_doi = normalize_doi(str(doi))
            if not DOI_RE.fullmatch(normalized_doi):
                issues.append(issue("error", "MALFORMED_DOI", item_id=evidence_id))
            else:
                _record_duplicate(
                    seen_dois,
                    normalized_doi,
                    evidence_id,
                    "DUPLICATE_DOI",
                    issues,
                )

        pmid = identifiers.get("pmid")
        if is_nonempty_string(pmid):
            normalized_pmid = str(pmid).strip()
            if not PMID_RE.fullmatch(normalized_pmid):
                issues.append(issue("error", "MALFORMED_PMID", item_id=evidence_id))
            else:
                _record_duplicate(
                    seen_pmids,
                    normalized_pmid,
                    evidence_id,
                    "DUPLICATE_PMID",
                    issues,
                )

        pmcid = identifiers.get("pmcid")
        if is_nonempty_string(pmcid):
            normalized_pmcid = str(pmcid).strip().upper()
            if not PMCID_RE.fullmatch(normalized_pmcid):
                issues.append(issue("error", "MALFORMED_PMCID", item_id=evidence_id))
            else:
                _record_duplicate(
                    seen_pmcids,
                    normalized_pmcid,
                    evidence_id,
                    "DUPLICATE_PMCID",
                    issues,
                )

        isbn = identifiers.get("isbn")
        if is_nonempty_string(isbn):
            normalized_isbn = normalize_isbn(str(isbn))
            if not valid_isbn(normalized_isbn):
                issues.append(issue("error", "MALFORMED_ISBN", item_id=evidence_id))
            else:
                _record_duplicate(
                    seen_isbns,
                    normalized_isbn.upper(),
                    evidence_id,
                    "DUPLICATE_ISBN",
                    issues,
                )

        url = identifiers.get("url")
        if is_nonempty_string(url) and not URL_RE.fullmatch(str(url).strip()):
            issues.append(issue("error", "MALFORMED_URL", item_id=evidence_id))

        if not any(is_nonempty_string(value) for value in identifiers.values()):
            issues.append(
                issue("warning", "NO_IDENTIFIER_TO_CHECK", item_id=evidence_id)
            )
    return issues, len(sources)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate DOI, PMID, PMCID, ISBN, and URL syntax and flag duplicates "
            "in a local source manifest. No identifier is resolved over a network."
        )
    )
    parser.add_argument("sources", help="UTF-8 JSON source manifest")
    return parser


def cli() -> int:
    args = build_parser().parse_args()
    data = require_object(read_json(args.sources), "source_manifest")
    if data.get("schema_version") != "1.0":
        raise InputError("unsupported source-manifest version")
    issues, count = check_sources(data)
    return emit_report(
        TOOL, issues, summary={"sources_checked": count, "network_used": False}
    )


if __name__ == "__main__":
    run(TOOL, cli)
