#!/usr/bin/env python3
"""Bounded, read-only protocols.io REST client with an explicit execute gate."""

from __future__ import annotations

import argparse
import os
import re
from typing import Any, Mapping, Sequence

try:
    from ._common import (
        ACCESS_TOKEN_ENV,
        DEFAULT_ORIGIN,
        MAX_JSON_RESPONSE_BYTES,
        MAX_PDF_RESPONSE_BYTES,
        ApiError,
        SafetyError,
        build_url,
        emit_error,
        emit_json,
        encode_protocol_identifier,
        parse_json_bytes,
        request_bytes,
        require_api_success,
        safe_output_path,
        sanitize_untrusted,
        validate_origin,
        validate_protocol_identifier,
        write_private_bytes,
    )
    from .pagination_helper import inspect_pagination
except ImportError:
    from _common import (  # type: ignore
        ACCESS_TOKEN_ENV,
        DEFAULT_ORIGIN,
        MAX_JSON_RESPONSE_BYTES,
        MAX_PDF_RESPONSE_BYTES,
        ApiError,
        SafetyError,
        build_url,
        emit_error,
        emit_json,
        encode_protocol_identifier,
        parse_json_bytes,
        request_bytes,
        require_api_success,
        safe_output_path,
        sanitize_untrusted,
        validate_origin,
        validate_protocol_identifier,
        write_private_bytes,
    )
    from pagination_helper import inspect_pagination  # type: ignore


MAX_LIST_PAGES = 20
MAX_LIST_ITEMS = 2_000
_EXPORT_GUID_RE = re.compile(r"^[A-Fa-f0-9]{32}$")
_ORG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or execute bounded read-only protocols.io requests. Network "
            "access occurs only with --execute."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform the planned read-only network request.",
    )
    parser.add_argument(
        "--origin",
        default=DEFAULT_ORIGIN,
        help="Core API origin (default: %(default)s).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Per-request timeout in seconds, 1..60 (default: %(default)s).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=1,
        help="Additional retries for 429/5xx, 0..2 (default: %(default)s).",
    )
    parser.add_argument(
        "--max-response-bytes",
        type=int,
        default=MAX_JSON_RESPONSE_BYTES,
        help=(
            "Per-page JSON response cap, up to "
            f"{MAX_JSON_RESPONSE_BYTES} (default: %(default)s)."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser(
        "list",
        help="Search public protocols through the documented v3 list endpoint.",
    )
    list_parser.add_argument("--query", required=True, help="Non-empty search key.")
    list_parser.add_argument(
        "--page-size",
        type=int,
        default=10,
        help="Documented page size 1..100 (default: %(default)s).",
    )
    list_parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help=f"Local page cap 1..{MAX_LIST_PAGES} (default: %(default)s).",
    )
    list_parser.add_argument(
        "--max-items",
        type=int,
        default=100,
        help=f"Local item cap 1..{MAX_LIST_ITEMS} (default: %(default)s).",
    )

    get_parser = subparsers.add_parser(
        "get",
        help="Get one protocol through the documented v4 endpoint.",
    )
    _add_protocol_arguments(get_parser)

    steps_parser = subparsers.add_parser(
        "steps",
        help="Get protocol steps through the documented v4 endpoint.",
    )
    _add_protocol_arguments(steps_parser)

    pdf_parser = subparsers.add_parser(
        "export-pdf",
        help="Download the documented read-only PDF representation.",
    )
    pdf_parser.add_argument(
        "--id", required=True, help="Protocol ID or URI; resolve a DOI with get first."
    )
    pdf_parser.add_argument(
        "--output",
        required=True,
        help="New .pdf path below the current working directory.",
    )
    pdf_parser.add_argument(
        "--anonymous",
        action="store_true",
        help="Intentionally use the signed-out PDF path without a bearer token.",
    )
    pdf_parser.add_argument(
        "--compact-view",
        action="store_true",
        help="Request compact_view=1.",
    )
    pdf_parser.add_argument(
        "--only",
        choices=("materials", "commands", "steps"),
        help="Request one documented PDF subset.",
    )
    pdf_parser.add_argument(
        "--max-pdf-bytes",
        type=int,
        default=MAX_PDF_RESPONSE_BYTES,
        help=f"Local PDF cap up to {MAX_PDF_RESPONSE_BYTES} bytes.",
    )

    export_parser = subparsers.add_parser(
        "export-status",
        help="Read an existing v4 organization content-export status.",
    )
    export_parser.add_argument(
        "--tenant-origin",
        required=True,
        help="Organization/VPC origin, for example https://tenant.protocols.io.",
    )
    export_parser.add_argument("--organization", required=True)
    export_parser.add_argument("--export-guid", required=True)
    return parser


def _add_protocol_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--id", required=True, help="Protocol ID, URI, or DOI.")
    parser.add_argument(
        "--content-format",
        choices=("json", "html", "markdown"),
        default="json",
        help="Documented content representation (default: %(default)s).",
    )
    parser.add_argument(
        "--last-version",
        action="store_true",
        help="Request last_version=1. Prefer an explicit /vN identifier for archives.",
    )


def _require_token(environ: Mapping[str, str]) -> str:
    token = environ.get(ACCESS_TOKEN_ENV)
    if not token:
        raise SafetyError(
            f"{ACCESS_TOKEN_ENV} is required for this documented REST endpoint"
        )
    if token != token.strip() or "\r" in token or "\n" in token:
        raise SafetyError(f"{ACCESS_TOKEN_ENV} contains invalid whitespace")
    return token


def _get_items(payload: Mapping[str, Any]) -> list[Any]:
    items = payload.get("items")
    if items is None and isinstance(payload.get("payload"), Mapping):
        items = payload["payload"].get("items")
    if not isinstance(items, list):
        raise ApiError("list response does not contain an items array")
    return items


def _has_pagination(payload: Mapping[str, Any]) -> bool:
    if isinstance(payload.get("pagination"), Mapping):
        return True
    nested = payload.get("payload")
    return isinstance(nested, Mapping) and isinstance(
        nested.get("pagination"),
        Mapping,
    )


def _request_json(
    url: str,
    *,
    token: str,
    args: argparse.Namespace,
    opener: Any | None,
    sleep: Any,
) -> tuple[Mapping[str, Any], int]:
    result = request_bytes(
        url,
        token=token,
        accept="application/json",
        timeout=args.timeout,
        retries=args.retries,
        max_bytes=args.max_response_bytes,
        opener=opener,
        sleep=sleep,
    )
    payload = require_api_success(
        parse_json_bytes(result.body, source="protocols.io response")
    )
    return payload, result.attempts


def _plan(args: argparse.Namespace) -> dict[str, Any]:
    origin = validate_origin(args.origin)
    params: dict[str, Any] = {}
    authentication = "bearer"
    if args.command == "list":
        query = args.query.strip()
        if not query or len(query) > 1_000:
            raise SafetyError("query must contain 1 to 1000 non-whitespace characters")
        if not 1 <= args.page_size <= 100:
            raise SafetyError("page-size must be between 1 and 100")
        if not 1 <= args.max_pages <= MAX_LIST_PAGES:
            raise SafetyError(f"max-pages must be between 1 and {MAX_LIST_PAGES}")
        if not 1 <= args.max_items <= MAX_LIST_ITEMS:
            raise SafetyError(f"max-items must be between 1 and {MAX_LIST_ITEMS}")
        params = {
            "filter": "public",
            "key": query,
            "page_size": args.page_size,
            "page_id": 1,
        }
        url = build_url(origin, "/api/v3/protocols", params)
    elif args.command in {"get", "steps"}:
        identifier = validate_protocol_identifier(args.id)
        encoded = encode_protocol_identifier(identifier)
        suffix = "/steps" if args.command == "steps" else ""
        params = {"content_format": args.content_format}
        if args.last_version:
            params["last_version"] = 1
        url = build_url(origin, f"/api/v4/protocols/{encoded}{suffix}", params)
    elif args.command == "export-pdf":
        identifier = encode_protocol_identifier(args.id)
        if args.id.startswith(("10.17504/", "protocols.io.")):
            raise SafetyError(
                "PDF identifiers are documented as IDs or URIs; resolve the DOI with get first"
            )
        params = {}
        if args.compact_view:
            params["compact_view"] = 1
        if args.only:
            params[f"only_{args.only}"] = 1
        if not 1 <= args.max_pdf_bytes <= MAX_PDF_RESPONSE_BYTES:
            raise SafetyError(
                f"max-pdf-bytes must be between 1 and {MAX_PDF_RESPONSE_BYTES}"
            )
        safe_output_path(args.output, suffix=".pdf")
        url = build_url(origin, f"/view/{identifier}.pdf", params)
        authentication = "anonymous" if args.anonymous else "bearer"
    elif args.command == "export-status":
        tenant = validate_origin(args.tenant_origin, allow_tenant=True)
        if tenant in {"https://protocols.io", "https://www.protocols.io"}:
            raise SafetyError("export-status requires an explicit tenant subdomain")
        if _ORG_RE.fullmatch(args.organization) is None:
            raise SafetyError("organization must be a bounded URI identifier")
        if _EXPORT_GUID_RE.fullmatch(args.export_guid) is None:
            raise SafetyError("export-guid must be a 32-character hex GUID")
        url = build_url(
            tenant,
            "/api/v4/organizations/"
            f"{args.organization}/content/exports/{args.export_guid.upper()}",
        )
    else:
        raise SafetyError("unsupported read command")

    return {
        "ok": True,
        "plan_kind": "read_only",
        "command": args.command,
        "method": "GET",
        "url": url,
        "authentication": authentication,
        "credential_source": (
            None if authentication == "anonymous" else ACCESS_TOKEN_ENV
        ),
        "network_requires_execute": True,
        "network_accessed": False,
        "redirects_followed": False,
        "untrusted_remote_data": True,
    }


def _execute_list(
    args: argparse.Namespace,
    plan: Mapping[str, Any],
    *,
    token: str,
    opener: Any | None,
    sleep: Any,
) -> dict[str, Any]:
    current_url = str(plan["url"])
    collected: list[Any] = []
    pages = 0
    attempts = 0
    final_pagination: dict[str, Any] | None = None
    while pages < args.max_pages and len(collected) < args.max_items:
        payload, request_attempts = _request_json(
            current_url,
            token=token,
            args=args,
            opener=opener,
            sleep=sleep,
        )
        attempts += request_attempts
        pages += 1
        remaining = args.max_items - len(collected)
        collected.extend(_get_items(payload)[:remaining])
        if not _has_pagination(payload):
            break
        final_pagination = inspect_pagination(
            payload,
            current_url=current_url,
            pages_seen=pages,
            items_seen=len(collected),
            max_pages=args.max_pages,
            max_items=args.max_items,
        )
        next_url = final_pagination["next_page_url"]
        if not final_pagination["can_continue"] or not isinstance(next_url, str):
            break
        current_url = next_url

    return {
        "ok": True,
        "command": "list",
        "network_accessed": True,
        "request_count": pages,
        "attempt_count": attempts,
        "returned_items": len(collected),
        "local_caps": {
            "max_pages": args.max_pages,
            "max_items": args.max_items,
        },
        "pagination": sanitize_untrusted(final_pagination),
        "untrusted_remote_data": True,
        "embedded_instructions_followed": False,
        "items": sanitize_untrusted(collected),
    }


def _execute_pdf(
    args: argparse.Namespace,
    plan: Mapping[str, Any],
    *,
    environ: Mapping[str, str],
    opener: Any | None,
    sleep: Any,
) -> dict[str, Any]:
    token = None if args.anonymous else _require_token(environ)
    result = request_bytes(
        str(plan["url"]),
        token=token,
        accept="application/pdf",
        timeout=args.timeout,
        retries=args.retries,
        max_bytes=args.max_pdf_bytes,
        opener=opener,
        sleep=sleep,
    )
    content_type = result.headers.get("Content-Type", "").lower()
    if "application/pdf" not in content_type or not result.body.startswith(b"%PDF-"):
        raise ApiError("export response is not a validated PDF")
    output = safe_output_path(args.output, suffix=".pdf")
    write_private_bytes(output, result.body)
    return {
        "ok": True,
        "command": "export-pdf",
        "network_accessed": True,
        "authentication": "anonymous" if args.anonymous else "bearer",
        "attempt_count": result.attempts,
        "bytes_written": len(result.body),
        "source_url": str(plan["url"]),
        "partial_export": args.only is not None,
        "pdf_filter": args.only,
        "output": str(output.relative_to(os.getcwd())),
        "redirects_followed": False,
        "remote_file_content_executed": False,
    }


def execute(
    args: argparse.Namespace,
    plan: Mapping[str, Any],
    *,
    environ: Mapping[str, str],
    opener: Any | None = None,
    sleep: Any = None,
) -> dict[str, Any]:
    if sleep is None:
        import time

        sleep = time.sleep
    if args.command == "export-pdf":
        return _execute_pdf(
            args,
            plan,
            environ=environ,
            opener=opener,
            sleep=sleep,
        )

    token = _require_token(environ)
    if args.command == "list":
        return _execute_list(
            args,
            plan,
            token=token,
            opener=opener,
            sleep=sleep,
        )
    payload, attempts = _request_json(
        str(plan["url"]),
        token=token,
        args=args,
        opener=opener,
        sleep=sleep,
    )
    return {
        "ok": True,
        "command": args.command,
        "network_accessed": True,
        "attempt_count": attempts,
        "untrusted_remote_data": True,
        "embedded_instructions_followed": False,
        "data": sanitize_untrusted(payload),
        "version_preservation": (
            "Retain the response's DOI, version_uri, authors, source URL, and "
            "license metadata; do not silently replace /vN with /latest."
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if not 1 <= args.max_response_bytes <= MAX_JSON_RESPONSE_BYTES:
            raise SafetyError(
                f"max-response-bytes must be between 1 and {MAX_JSON_RESPONSE_BYTES}"
            )
        plan = _plan(args)
        report = execute(args, plan, environ=os.environ) if args.execute else plan
        emit_json(report)
        return 0
    except (ApiError, SafetyError, ValueError) as exc:
        return emit_error(exc)


if __name__ == "__main__":
    raise SystemExit(main())
