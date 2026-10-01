#!/usr/bin/env python3
"""Shared, bounded helpers for local standards-readiness evidence checks.

These helpers validate structure and evidence metadata only. They never determine
regulatory applicability, conformity, compliance, certification, accreditation, or
audit outcome.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from _catalog import DEFAULT_STANDARD, STANDARD_KEYS, STANDARDS, StandardProfile

MAX_INPUT_BYTES = 2_000_000
MAX_ITEMS = 5_000
MAX_DEPTH = 30
MAX_TEXT_CHARS = 20_000
RESEARCH_BASIS = "2026-10-01"
EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_INPUT_ERROR = 2

ALLOWED_STATUSES = {
    "draft",
    "in-review",
    "approved",
    "implemented",
    "verified",
    "closed",
    "not-applicable",
}
APPROVAL_STATUSES = {"pending", "approved", "rejected"}
EVIDENCE_TYPES = {
    "document",
    "record",
    "report",
    "log",
    "training",
    "validation",
    "approval",
    "other",
}
PLACEHOLDER_RE = re.compile(
    r"^(?:tbd|todo|unknown|replace[-_ ]?me|n/?a\s+without\s+rationale|"
    r"<[^>]+>|\[[^\]]+\])$",
    re.IGNORECASE,
)

DISCLAIMER = (
    "Structural evidence check only. A zero-finding result does not establish "
    "legal applicability, regulatory compliance, conformity to any standard, "
    "certification, accreditation, MDSAP acceptability, EU conformity, or "
    "inspection readiness."
)


class InputError(ValueError):
    """Raised for unsafe, unreadable, or invalid input."""


@dataclass(frozen=True)
class Finding:
    """One deterministic structural or evidence finding."""

    code: str
    path: str
    message: str
    severity: str = "gap"

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "severity": self.severity,
        }


def _reject_constant(value: str) -> None:
    raise InputError(f"non-finite JSON number is not permitted: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON key is not permitted: {key}")
        result[key] = value
    return result


def _check_depth_and_size(value: Any) -> None:
    stack: list[tuple[Any, int]] = [(value, 1)]
    items = 0
    while stack:
        current, depth = stack.pop()
        if depth > MAX_DEPTH:
            raise InputError(f"JSON nesting exceeds {MAX_DEPTH} levels")
        if isinstance(current, dict):
            items += len(current)
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            items += len(current)
            stack.extend((item, depth + 1) for item in current)
        elif isinstance(current, str) and len(current) > MAX_TEXT_CHARS:
            raise InputError(
                f"JSON string exceeds {MAX_TEXT_CHARS} characters"
            )
        elif isinstance(current, float) and not math.isfinite(current):
            # parse_constant rejects NaN/Infinity tokens, but a JSON number such
            # as 1e999 also overflows to infinity with the standard parser.
            raise InputError("non-finite JSON number is not permitted")
        if items > MAX_ITEMS:
            raise InputError(f"JSON contains more than {MAX_ITEMS} items")


def _safe_input_file(path_text: str, suffixes: set[str]) -> Path:
    path = Path(path_text)
    if path.is_symlink():
        raise InputError(f"symbolic-link input is refused: {path}")
    try:
        stat = path.stat()
    except OSError as exc:
        raise InputError(f"cannot stat input {path}: {exc}") from exc
    if not path.is_file():
        raise InputError(f"input is not a regular file: {path}")
    if path.suffix.lower() not in suffixes:
        expected = ", ".join(sorted(suffixes))
        raise InputError(f"input suffix must be one of: {expected}")
    if stat.st_size > MAX_INPUT_BYTES:
        raise InputError(
            f"input exceeds {MAX_INPUT_BYTES} bytes: {stat.st_size}"
        )
    return path


def load_json(path_text: str) -> Any:
    """Load bounded UTF-8 JSON, rejecting links, duplicates, and non-finite values."""

    path = _safe_input_file(path_text, {".json"})
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise InputError(f"cannot read UTF-8 JSON {path}: {exc}") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except InputError:
        raise
    except (ValueError, RecursionError) as exc:
        raise InputError(f"invalid JSON in {path}: {exc}") from exc
    _check_depth_and_size(value)
    return value


def load_markdown(path_text: str) -> str:
    """Load bounded local Markdown without interpreting embedded content."""

    path = _safe_input_file(path_text, {".md", ".markdown"})
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise InputError(f"cannot read UTF-8 Markdown {path}: {exc}") from exc
    if "\x00" in text:
        raise InputError(f"NUL byte is not permitted in Markdown: {path}")
    return text


def require_root_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError("JSON root must be an object")
    return value


def is_placeholder(value: Any) -> bool:
    return (
        not isinstance(value, str)
        or not value.strip()
        or bool(PLACEHOLDER_RE.fullmatch(value.strip()))
    )


def valid_iso_date(value: Any) -> bool:
    if (
        not isinstance(value, str)
        or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None
    ):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


class Review:
    """Accumulates fail-closed findings while preserving deterministic order."""

    def __init__(self) -> None:
        self.findings: list[Finding] = []

    def add(
        self,
        code: str,
        path: str,
        message: str,
        severity: str = "gap",
    ) -> None:
        self.findings.append(Finding(code, path, message, severity))

    def object(self, value: Any, path: str) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            self.add("TYPE_OBJECT", path, "must be an object")
            return None
        return value

    def list(
        self,
        value: Any,
        path: str,
        *,
        min_items: int = 1,
        max_items: int = MAX_ITEMS,
    ) -> list[Any] | None:
        if not isinstance(value, list):
            self.add("TYPE_LIST", path, "must be an array")
            return None
        if len(value) < min_items:
            self.add("LIST_EMPTY", path, f"must contain at least {min_items} item(s)")
        if len(value) > max_items:
            self.add("LIST_BOUNDED", path, f"must contain at most {max_items} items")
            return value[:max_items]
        return value

    def text(
        self,
        obj: dict[str, Any],
        key: str,
        path: str,
        *,
        max_chars: int = 500,
    ) -> str | None:
        value = obj.get(key)
        field_path = f"{path}.{key}"
        if is_placeholder(value):
            self.add("TEXT_REQUIRED", field_path, "requires non-placeholder text")
            return None
        assert isinstance(value, str)
        if len(value) > max_chars:
            self.add(
                "TEXT_BOUNDED",
                field_path,
                f"must not exceed {max_chars} characters",
            )
        return value.strip()

    def choice(
        self,
        obj: dict[str, Any],
        key: str,
        allowed: set[str],
        path: str,
    ) -> str | None:
        value = obj.get(key)
        field_path = f"{path}.{key}"
        if not isinstance(value, str) or value not in allowed:
            self.add(
                "CHOICE_INVALID",
                field_path,
                f"must be one of: {', '.join(sorted(allowed))}",
            )
            return None
        return value

    def date(
        self,
        obj: dict[str, Any],
        key: str,
        path: str,
        *,
        required: bool = True,
    ) -> str | None:
        value = obj.get(key)
        field_path = f"{path}.{key}"
        if value in (None, "") and not required:
            return None
        if not valid_iso_date(value):
            self.add("DATE_INVALID", field_path, "must be an ISO date (YYYY-MM-DD)")
            return None
        return str(value)

    def unique_ids(
        self,
        rows: Iterable[Any],
        path: str,
        *,
        key: str = "id",
    ) -> None:
        seen: set[str] = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            value = row.get(key)
            if not isinstance(value, str) or not value.strip():
                continue
            if value in seen:
                self.add(
                    "ID_DUPLICATE",
                    f"{path}[{index}].{key}",
                    f"duplicate identifier: {value}",
                )
            seen.add(value)

    def evidence(
        self,
        obj: dict[str, Any],
        path: str,
        *,
        min_items: int = 1,
    ) -> list[dict[str, Any]]:
        raw = self.list(obj.get("evidence"), f"{path}.evidence", min_items=min_items)
        if raw is None:
            return []
        evidence: list[dict[str, Any]] = []
        for index, item in enumerate(raw):
            item_path = f"{path}.evidence[{index}]"
            record = self.object(item, item_path)
            if record is None:
                continue
            self.text(record, "id", item_path, max_chars=120)
            self.choice(record, "type", EVIDENCE_TYPES, item_path)
            self.text(record, "location", item_path, max_chars=1_000)
            self.text(record, "revision_or_date", item_path, max_chars=120)
            evidence.append(record)
        self.unique_ids(evidence, f"{path}.evidence")
        return evidence

    def approval(
        self,
        obj: dict[str, Any],
        path: str,
        *,
        require_approved: bool,
    ) -> dict[str, Any] | None:
        approval_path = f"{path}.approval"
        approval = self.object(obj.get("approval"), approval_path)
        if approval is None:
            return None
        status = self.choice(
            approval,
            "status",
            APPROVAL_STATUSES,
            approval_path,
        )
        if require_approved and status != "approved":
            self.add(
                "APPROVAL_PENDING",
                f"{approval_path}.status",
                "human approval must be recorded as approved",
            )
        if status == "approved":
            self.text(approval, "by", approval_path, max_chars=200)
            self.date(approval, "date", approval_path)
        return approval

    def source_refs(
        self,
        obj: dict[str, Any],
        path: str,
        *,
        min_items: int = 1,
    ) -> list[dict[str, Any]]:
        raw = self.list(
            obj.get("source_refs"),
            f"{path}.source_refs",
            min_items=min_items,
        )
        if raw is None:
            return []
        sources: list[dict[str, Any]] = []
        for index, item in enumerate(raw):
            item_path = f"{path}.source_refs[{index}]"
            source = self.object(item, item_path)
            if source is None:
                continue
            self.text(source, "id", item_path, max_chars=120)
            self.text(source, "title", item_path, max_chars=300)
            self.text(source, "version_or_date", item_path, max_chars=120)
            url = self.text(source, "url", item_path, max_chars=1_000)
            if url is not None and not url.startswith("https://"):
                self.add(
                    "SOURCE_URL",
                    f"{item_path}.url",
                    "must use an https official-source URL",
                )
            self.date(source, "accessed", item_path)
            sources.append(source)
        self.unique_ids(sources, f"{path}.source_refs")
        return sources

    def controlled_item(
        self,
        obj: dict[str, Any],
        path: str,
        *,
        require_approved: bool = True,
        require_sources: bool = True,
    ) -> None:
        self.text(obj, "owner", path, max_chars=200)
        self.choice(obj, "status", ALLOWED_STATUSES, path)
        self.evidence(obj, path)
        self.approval(obj, path, require_approved=require_approved)
        if require_sources:
            self.source_refs(obj, path)


def standard_parser(
    description: str,
    input_help: str,
    *,
    with_standard: bool = False,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=description,
        epilog=DISCLAIMER,
    )
    parser.add_argument("input", help=input_help)
    if with_standard:
        parser.add_argument(
            "--standard",
            choices=STANDARD_KEYS,
            default=DEFAULT_STANDARD,
            help=(
                "Declared standard profile supplying the process-domain and scope "
                "vocabulary. Selecting a profile does not decide that the standard "
                "applies. An unlisted value is refused."
            ),
        )
    parser.add_argument(
        "--output",
        help="Write the JSON report locally instead of stdout",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow replacing an existing regular output file",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit compact JSON",
    )
    return parser


def profile_for(args: argparse.Namespace) -> StandardProfile:
    """Return the declared standard profile, defaulting to the device QMS set.

    argparse refuses an unlisted --standard value with exit code 2, so this never
    silently falls back to the default for an unknown standard.
    """

    return STANDARDS[getattr(args, "standard", DEFAULT_STANDARD)]


def build_report(
    tool: str,
    findings: Iterable[Finding],
    *,
    metrics: dict[str, Any] | None = None,
    basis: str = RESEARCH_BASIS,
    standard: str | None = None,
) -> dict[str, Any]:
    ordered = sorted(
        findings,
        key=lambda item: (item.path, item.code, item.message, item.severity),
    )
    report = {
        "basis_date": basis,
        "disclaimer": DISCLAIMER,
        "findings": [item.as_dict() for item in ordered],
        "metrics": metrics or {},
        "result": "gaps-found" if ordered else "complete-for-human-review",
        "tool": tool,
    }
    if standard is not None:
        report["standard"] = standard
    return report


def emit_report(
    report: dict[str, Any],
    output: str | None,
    *,
    force: bool,
    compact: bool,
) -> None:
    text = json.dumps(
        report,
        ensure_ascii=False,
        indent=None if compact else 2,
        sort_keys=True,
        allow_nan=False,
    )
    if not compact:
        text += "\n"
    if output is None:
        sys.stdout.write(text)
        return
    path = Path(output)
    if path.is_symlink():
        raise InputError(f"symbolic-link output is refused: {path}")
    if path.exists():
        if not path.is_file():
            raise InputError(f"output is not a regular file: {path}")
        if not force:
            raise InputError(
                f"output exists; pass --force to replace it: {path}"
            )
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot write output {path}: {exc}") from exc


def finish(
    tool: str,
    review: Review,
    args: argparse.Namespace,
    *,
    metrics: dict[str, Any] | None = None,
    standard: str | None = None,
) -> int:
    report = build_report(
        tool,
        review.findings,
        metrics=metrics,
        standard=standard,
    )
    emit_report(
        report,
        args.output,
        force=args.force,
        compact=args.compact,
    )
    return EXIT_FINDINGS if review.findings else EXIT_OK


def guarded_main(main_function: Any) -> None:
    try:
        code = int(main_function())
    except InputError as exc:
        print(f"INPUT_ERROR: {exc}", file=sys.stderr)
        code = EXIT_INPUT_ERROR
    raise SystemExit(code)
