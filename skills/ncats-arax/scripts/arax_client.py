#!/usr/bin/env python3
"""Bounded, provenance-preserving client for the NCATS Translator ARAX API."""

from __future__ import annotations

import argparse
import email.utils
import hashlib
import ipaddress
import json
import os
import re
import socket
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


CLIENT_NAME = "ncats-arax"
CLIENT_VERSION = "1.0"
USER_AGENT = "scientific-agent-skills-ncats-arax/1.0"
SUBMITTER = "scientific-agent-skills-ncats-arax"
PRODUCTION_BASE_URL = "https://arax.transltr.io/api/arax/v1.4"
TESTED_ARAX_VERSION = "1.5.4"
TESTED_TRAPI_VERSION = "1.5.0"
SUPPORTED_TRAPI_SERIES = {"1.5", "1.6"}

GET_TIMEOUT_SECONDS = 30
LOOKUP_TIMEOUT_SECONDS = 120
FEDERATED_TIMEOUT_SECONDS = 180
KP_TIMEOUT_SECONDS = 30
LOOKUP_RESULT_LIMIT = 20
FEDERATED_RESULT_LIMIT = 50
MAX_RESULT_LIMIT = 50
MAX_PROVIDERS = 5
MIN_FEDERATED_PROVIDERS = 2
MAX_PREDICATES = 5
MAX_QUALIFIERS = 6
MAX_IDENTIFIER_LENGTH = 200
MAX_RESPONSE_BYTES = 25 * 1024 * 1024
MAX_WARNING_MESSAGE = 500
MAX_DISPLAY_TEXT = 500
PUBLICATION_PREVIEW = 10

RETRYABLE_GET_STATUS = {429, 502, 503, 504}
CURIE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*:[^\s]+$")
BIOLINK_RE = re.compile(r"^biolink:[A-Za-z][A-Za-z0-9._-]*$")
PROVIDER_RE = re.compile(r"^infores:[A-Za-z0-9._-]+$")
TRAPI_VERSION_RE = re.compile(r"\bTRAPI\s+(\d+\.\d+(?:\.\d+)?)\b", re.IGNORECASE)
EXPAND_RE = re.compile(
    r"^expand\(edge_key=(e[01]),kp=(.+),kp_timeout=30,"
    r"return_minimal_metadata=false\)$"
)
FILTER_RE = re.compile(
    r"^filter_results\(action=limit_number_of_results,max_results=(\d+),"
    r"prune_kg=true\)$"
)

WARNING_CODES = {
    "PUBLIC_QUERY",
    "NORMALIZATION_REQUIRES_CONFIRMATION",
    "NORMALIZATION_CATEGORY_MISMATCH",
    "NO_RESULTS",
    "NO_PUBLICATIONS_RETURNED",
    "NO_PRIMARY_SOURCE_RETURNED",
    "UNSCORED_RESPONSE_ORDER",
    "RESULT_LIMIT_REACHED",
    "INTERNAL_PRUNING_DETECTED",
    "KP_TIMEOUT",
    "KP_ERROR",
    "MALFORMED_KP_RESPONSE",
    "MISSING_AUXILIARY_GRAPH",
    "REVERSED_EDGE_BINDING",
    "UNTESTED_SERVICE_VERSION",
    "NONPRODUCTION_ENDPOINT",
}


class AraxClientError(Exception):
    """Base error carrying the documented CLI exit classification."""

    def __init__(
        self,
        message: str,
        *,
        exit_code: int,
        kind: str,
        http_status: int | None = None,
        response_body: bytes | None = None,
        attempts: int = 0,
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.kind = kind
        self.http_status = http_status
        self.response_body = response_body
        self.attempts = attempts


class UsageError(AraxClientError):
    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=2, kind="invalid_input")


class PreflightError(AraxClientError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, exit_code=3, kind="preflight", **kwargs)


class NormalizationError(AraxClientError):
    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=4, kind="normalization_no_result")


class TransportError(AraxClientError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, exit_code=5, kind="transport_or_http", **kwargs)


class ResponseError(AraxClientError):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, exit_code=6, kind="invalid_response", **kwargs)


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: bytes
    headers: dict[str, str]
    elapsed_ms: int
    attempts: int


@dataclass(frozen=True)
class ServiceInfo:
    base_url: str
    openapi_url: str
    arax_version: str | None
    trapi_version: str | None
    warnings: tuple[dict[str, Any], ...]

    def as_dict(self, *, biolink_version: str | None = None) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "openapi_url": self.openapi_url,
            "arax_version": self.arax_version,
            "trapi_version": self.trapi_version,
            "biolink_version": biolink_version,
        }


@dataclass(frozen=True)
class QueryContract:
    kind: str
    mode: str
    provider_ids: tuple[str, ...]
    expand_order: str | None
    qnode_ids: dict[str, list[str]]
    result_limit: int
    query_edges: dict[str, tuple[str, str]]


class RejectRepeatedValueAction(argparse.Action):
    """Reject repeated scalar flags instead of silently accepting the last value."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        if getattr(namespace, self.dest, None) is not None:
            parser.error(f"{option_string} may be supplied only once")
        setattr(namespace, self.dest, values)


def _sanitize_text(value: Any, limit: int = MAX_DISPLAY_TEXT) -> str:
    text = str(value)
    text = "".join(" " if ord(char) < 32 or ord(char) == 127 else char for char in text)
    text = " ".join(text.split())
    if len(text) > limit:
        return text[: max(0, limit - 1)] + "…"
    return text


def make_warning(
    code: str,
    message: str,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if code not in WARNING_CODES:
        raise ValueError(f"unknown warning code: {code}")
    safe_context: dict[str, Any] = {}
    for key, value in (context or {}).items():
        if value is None or isinstance(value, (bool, int, float)):
            safe_context[str(key)] = value
        else:
            safe_context[str(key)] = _sanitize_text(value, 200)
    return {
        "code": code,
        "message": _sanitize_text(message, MAX_WARNING_MESSAGE),
        "context": safe_context,
    }


def _append_warning(
    warnings: list[dict[str, Any]],
    code: str,
    message: str,
    context: Mapping[str, Any] | None = None,
) -> None:
    warning = make_warning(code, message, context)
    identity = (warning["code"], json.dumps(warning["context"], sort_keys=True), warning["message"])
    existing = {
        (item.get("code"), json.dumps(item.get("context", {}), sort_keys=True), item.get("message"))
        for item in warnings
    }
    if identity not in existing:
        warnings.append(warning)


def _has_control(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)


def validate_curie(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_IDENTIFIER_LENGTH:
        raise UsageError("CURIE must be a nonempty string of at most 200 characters")
    if _has_control(value) or not CURIE_RE.fullmatch(value):
        raise UsageError(f"invalid CURIE: {_sanitize_text(value, 80)}")
    return value


def _looks_like_curie(value: str) -> bool:
    try:
        validate_curie(value)
    except UsageError:
        return False
    return True


def validate_biolink_term(value: str, label: str = "Biolink term") -> str:
    if not isinstance(value, str) or len(value) > MAX_IDENTIFIER_LENGTH:
        raise UsageError(f"{label} must be at most 200 characters")
    if _has_control(value) or not BIOLINK_RE.fullmatch(value):
        raise UsageError(f"invalid {label.lower()}: {_sanitize_text(value, 80)}")
    return value


def validate_provider_id(value: str) -> str:
    if not isinstance(value, str) or len(value) > MAX_IDENTIFIER_LENGTH:
        raise UsageError("provider identifier must be at most 200 characters")
    if _has_control(value) or not PROVIDER_RE.fullmatch(value):
        raise UsageError(f"invalid provider identifier: {_sanitize_text(value, 80)}")
    if value.lower() == "infores:all":
        raise UsageError("all-provider federation is not supported")
    return value


def _unique(values: Sequence[str], label: str) -> list[str]:
    if len(set(values)) != len(values):
        raise UsageError(f"duplicate {label} values are not allowed")
    return list(values)


def validate_predicates(values: Sequence[str]) -> list[str]:
    if not 1 <= len(values) <= MAX_PREDICATES:
        raise UsageError("each query edge requires one to five predicates")
    return _unique([validate_biolink_term(value, "Biolink predicate") for value in values], "predicate")


def parse_qualifiers(values: Sequence[str]) -> list[tuple[str, str]]:
    if len(values) > MAX_QUALIFIERS:
        raise UsageError("each query edge accepts at most six qualifiers")
    parsed: list[tuple[str, str]] = []
    seen_types: set[str] = set()
    for raw in values:
        if "=" not in raw:
            raise UsageError("qualifiers must use TYPE=VALUE")
        qualifier_type, qualifier_value = raw.split("=", 1)
        validate_biolink_term(qualifier_type, "Biolink qualifier type")
        if (
            not qualifier_value
            or len(qualifier_value) > MAX_IDENTIFIER_LENGTH
            or _has_control(qualifier_value)
        ):
            raise UsageError("qualifier values must be nonempty, control-free, and at most 200 characters")
        if qualifier_type in seen_types:
            raise UsageError("a qualifier type may appear only once per edge")
        seen_types.add(qualifier_type)
        parsed.append((qualifier_type, qualifier_value))
    return parsed


def validate_result_limit(value: int) -> int:
    if not 1 <= value <= MAX_RESULT_LIMIT:
        raise UsageError("result limit must be between 1 and 50")
    return value


def validate_base_url(value: str, allow_nonproduction: bool) -> tuple[str, list[dict[str, Any]]]:
    raw = value.rstrip("/")
    parts = urllib.parse.urlsplit(raw)
    try:
        parts.port
    except ValueError as exc:
        raise UsageError("base URL contains an invalid port") from exc
    if parts.scheme.lower() != "https" or not parts.hostname:
        raise UsageError("base URL must be an absolute HTTPS URL")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise UsageError("base URL may not contain credentials, a query string, or a fragment")
    hostname = parts.hostname.lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise UsageError("localhost endpoints are not allowed")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise UsageError("private, loopback, link-local, and reserved endpoint addresses are not allowed")
    normalized = urllib.parse.urlunsplit(("https", parts.netloc, parts.path.rstrip("/"), "", ""))
    warnings: list[dict[str, Any]] = []
    if normalized != PRODUCTION_BASE_URL:
        if not allow_nonproduction:
            raise PreflightError(
                "nonproduction endpoint requires --allow-nonproduction-endpoint"
            )
        _append_warning(
            warnings,
            "NONPRODUCTION_ENDPOINT",
            "An explicitly selected nonproduction ARAX endpoint is in use.",
            {"base_url": normalized},
        )
    return normalized, warnings


def resolve_mode(
    mode: str,
    provider_values: Sequence[str],
    result_limit: int | None,
) -> tuple[list[str], int]:
    if mode == "lookup":
        if provider_values:
            raise UsageError("--kp is allowed only with --mode federated")
        providers = ["infores:rtx-kg2"]
        limit = LOOKUP_RESULT_LIMIT if result_limit is None else result_limit
    elif mode == "federated":
        providers = _unique([validate_provider_id(value) for value in provider_values], "provider")
        if not MIN_FEDERATED_PROVIDERS <= len(providers) <= MAX_PROVIDERS:
            raise UsageError("federated mode requires two to five explicit providers")
        limit = FEDERATED_RESULT_LIMIT if result_limit is None else result_limit
    else:
        raise UsageError(f"unsupported mode: {mode}")
    return providers, validate_result_limit(limit)


def build_query_edge(
    subject: str,
    object_: str,
    predicates: Sequence[str],
    qualifiers: Sequence[tuple[str, str]],
) -> dict[str, Any]:
    edge: dict[str, Any] = {
        "subject": subject,
        "object": object_,
        "predicates": list(predicates),
    }
    if qualifiers:
        edge["qualifier_constraints"] = [
            {
                "qualifier_set": [
                    {"qualifier_type_id": qualifier_type, "qualifier_value": qualifier_value}
                    for qualifier_type, qualifier_value in qualifiers
                ]
            }
        ]
    return edge


def _provider_parameter(mode: str, provider_ids: Sequence[str]) -> str:
    if mode == "lookup":
        return "infores:rtx-kg2"
    return "[" + ",".join(provider_ids) + "]"


def build_operations(
    edge_keys: Sequence[str],
    mode: str,
    provider_ids: Sequence[str],
    result_limit: int,
) -> dict[str, list[str]]:
    kp_value = _provider_parameter(mode, provider_ids)
    actions = [
        f"expand(edge_key={edge_key},kp={kp_value},kp_timeout={KP_TIMEOUT_SECONDS},"
        "return_minimal_metadata=false)"
        for edge_key in edge_keys
    ]
    actions.extend(
        [
            "scoreless_resultify(ignore_edge_direction=true)",
            f"filter_results(action=limit_number_of_results,max_results={result_limit},prune_kg=true)",
            "return(response=true,store=false)",
        ]
    )
    return {"actions": actions}


def build_one_hop_query(
    *,
    subject_id: str | None,
    subject_category: str,
    predicates: Sequence[str],
    object_id: str | None,
    object_category: str,
    qualifiers: Sequence[tuple[str, str]],
    mode: str,
    provider_ids: Sequence[str],
    result_limit: int,
) -> dict[str, Any]:
    if subject_id is None and object_id is None:
        raise UsageError("one-hop queries require at least one pinned endpoint")
    nodes: dict[str, dict[str, Any]] = {
        "n0": {"categories": [validate_biolink_term(subject_category, "Biolink category")]},
        "n1": {"categories": [validate_biolink_term(object_category, "Biolink category")]},
    }
    if subject_id is not None:
        nodes["n0"]["ids"] = [validate_curie(subject_id)]
    if object_id is not None:
        nodes["n1"]["ids"] = [validate_curie(object_id)]
    body = {
        "message": {
            "query_graph": {
                "nodes": nodes,
                "edges": {
                    "e0": build_query_edge("n0", "n1", validate_predicates(predicates), qualifiers)
                },
            }
        },
        "operations": build_operations(["e0"], mode, provider_ids, result_limit),
        "stream_progress": False,
        "submitter": SUBMITTER,
    }
    return body


def build_two_hop_query(
    *,
    subject_id: str,
    subject_category: str,
    predicates_1: Sequence[str],
    intermediate_category: str,
    predicates_2: Sequence[str],
    object_id: str,
    object_category: str,
    qualifiers_1: Sequence[tuple[str, str]],
    qualifiers_2: Sequence[tuple[str, str]],
    mode: str,
    provider_ids: Sequence[str],
    expand_order: str,
    result_limit: int,
) -> dict[str, Any]:
    if expand_order not in {"right-first", "left-first"}:
        raise UsageError("expand order must be right-first or left-first")
    nodes = {
        "n0": {
            "ids": [validate_curie(subject_id)],
            "categories": [validate_biolink_term(subject_category, "Biolink category")],
        },
        "n1": {
            "categories": [validate_biolink_term(intermediate_category, "Biolink category")]
        },
        "n2": {
            "ids": [validate_curie(object_id)],
            "categories": [validate_biolink_term(object_category, "Biolink category")],
        },
    }
    edge_order = ["e1", "e0"] if expand_order == "right-first" else ["e0", "e1"]
    return {
        "message": {
            "query_graph": {
                "nodes": nodes,
                "edges": {
                    "e0": build_query_edge(
                        "n0", "n1", validate_predicates(predicates_1), qualifiers_1
                    ),
                    "e1": build_query_edge(
                        "n1", "n2", validate_predicates(predicates_2), qualifiers_2
                    ),
                },
            }
        },
        "operations": build_operations(edge_order, mode, provider_ids, result_limit),
        "stream_progress": False,
        "submitter": SUBMITTER,
    }


def serialize_request(body: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise UsageError("request contains a value that cannot be represented as strict JSON") from exc


def _origin(url: str) -> tuple[str, str | None, int | None]:
    parts = urllib.parse.urlsplit(url)
    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError("URL contains an invalid port") from exc
    if port is None and parts.scheme.lower() == "https":
        port = 443
    return parts.scheme.lower(), parts.hostname.lower() if parts.hostname else None, port


class SameOriginHttpsRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        try:
            original_origin = _origin(req.full_url)
            redirect_origin = _origin(newurl)
        except ValueError:
            original_origin = _origin(req.full_url)
            redirect_origin = ("", None, None)
        if original_origin != redirect_origin or redirect_origin[0] != "https":
            raise urllib.error.HTTPError(
                newurl,
                code,
                "cross-origin or protocol-downgrade redirect rejected",
                headers,
                fp,
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open_url(request: urllib.request.Request, timeout: int) -> Any:
    opener = urllib.request.build_opener(SameOriginHttpsRedirectHandler())
    return opener.open(request, timeout=timeout)


def read_bounded_response(response: Any, byte_limit: int = MAX_RESPONSE_BYTES) -> bytes:
    body = response.read(byte_limit + 1)
    if len(body) > byte_limit:
        raise ResponseError("response exceeded the 25 MiB byte limit")
    return body


def _response_status(response: Any) -> int:
    status = getattr(response, "status", None)
    return int(status if status is not None else response.getcode())


def _headers_dict(headers: Any) -> dict[str, str]:
    if headers is None:
        return {}
    try:
        return {str(key): str(value) for key, value in headers.items()}
    except AttributeError:
        return {}


def _retry_delay(headers: Mapping[str, str], now: Callable[[], datetime] | None = None) -> float:
    raw = next((value for key, value in headers.items() if key.lower() == "retry-after"), None)
    if raw is None:
        return 1.0
    try:
        return min(10.0, max(0.0, float(raw)))
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(raw)
            current = (now or (lambda: datetime.now(timezone.utc)))()
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return min(10.0, max(0.0, (parsed - current).total_seconds()))
        except (TypeError, ValueError, OverflowError):
            return 1.0


def _is_timeout_error(error: BaseException) -> bool:
    if isinstance(error, (TimeoutError, socket.timeout)):
        return True
    return isinstance(error, urllib.error.URLError) and isinstance(
        getattr(error, "reason", None), (TimeoutError, socket.timeout)
    )


def request_get_with_retry(
    url: str,
    *,
    timeout: int = GET_TIMEOUT_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> HttpResult:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "User-Agent": USER_AGENT,
        },
    )
    started = time.monotonic()
    for attempt in (1, 2):
        try:
            with _open_url(request, timeout) as response:
                try:
                    body = read_bounded_response(response)
                except ResponseError as exc:
                    exc.attempts = attempt
                    exc.http_status = _response_status(response)
                    raise
                return HttpResult(
                    status=_response_status(response),
                    body=body,
                    headers=_headers_dict(getattr(response, "headers", None)),
                    elapsed_ms=round((time.monotonic() - started) * 1000),
                    attempts=attempt,
                )
        except urllib.error.HTTPError as exc:
            headers = _headers_dict(exc.headers)
            if exc.code in RETRYABLE_GET_STATUS and attempt == 1:
                try:
                    exc.close()
                finally:
                    sleep(_retry_delay(headers))
                continue
            try:
                body = read_bounded_response(exc)
            except ResponseError as oversized:
                oversized.http_status = exc.code
                oversized.attempts = attempt
                raise oversized from exc
            raise TransportError(
                f"GET failed with HTTP {exc.code}",
                http_status=exc.code,
                response_body=body,
                attempts=attempt,
            ) from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            if _is_timeout_error(exc) and attempt == 1:
                sleep(1.0)
                continue
            raise TransportError(f"GET transport failure: {_sanitize_text(exc)}", attempts=attempt) from exc
    raise AssertionError("unreachable")


def post_query(url: str, request_bytes: bytes, *, timeout: int) -> HttpResult:
    request = urllib.request.Request(
        url,
        data=request_bytes,
        method="POST",
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    started = time.monotonic()
    try:
        with _open_url(request, timeout) as response:
            try:
                body = read_bounded_response(response)
            except ResponseError as exc:
                exc.attempts = 1
                exc.http_status = _response_status(response)
                raise
            return HttpResult(
                status=_response_status(response),
                body=body,
                headers=_headers_dict(getattr(response, "headers", None)),
                elapsed_ms=round((time.monotonic() - started) * 1000),
                attempts=1,
            )
    except urllib.error.HTTPError as exc:
        try:
            body = read_bounded_response(exc)
        except ResponseError as oversized:
            oversized.http_status = exc.code
            oversized.attempts = 1
            raise oversized from exc
        raise TransportError(
            f"POST failed with HTTP {exc.code}",
            http_status=exc.code,
            response_body=body,
            attempts=1,
        ) from exc
    except ResponseError:
        raise
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        raise TransportError(f"POST transport failure: {_sanitize_text(exc)}", attempts=1) from exc


def _decode_json(body: bytes, label: str) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")

    try:
        return json.loads(body.decode("utf-8"), parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ResponseError(f"{label} was not valid strict UTF-8 JSON") from exc


def _version_series(version: str | None) -> str | None:
    if not version:
        return None
    parts = version.split(".")
    if len(parts) < 2 or not all(part.isdigit() for part in parts[:2]):
        return None
    return ".".join(parts[:2])


def _check_trapi_version(
    trapi_version: str | None,
    allow_untested: bool,
    warnings: list[dict[str, Any]],
) -> None:
    series = _version_series(trapi_version)
    if series not in SUPPORTED_TRAPI_SERIES and not allow_untested:
        raise PreflightError(
            "service reports an unknown or missing TRAPI series; use --allow-untested-version to continue"
        )
    if trapi_version != TESTED_TRAPI_VERSION:
        _append_warning(
            warnings,
            "UNTESTED_SERVICE_VERSION",
            "The service TRAPI version differs from the tested production version.",
            {"reported": trapi_version, "tested": TESTED_TRAPI_VERSION},
        )


def parse_openapi_service_info(
    payload: Any,
    *,
    base_url: str,
    openapi_url: str,
    allow_untested_version: bool,
    initial_warnings: Sequence[dict[str, Any]] = (),
) -> ServiceInfo:
    if not isinstance(payload, dict):
        raise PreflightError("OpenAPI document is not an object")
    info = payload.get("info")
    paths = payload.get("paths")
    if not isinstance(info, dict) or not isinstance(paths, dict):
        raise PreflightError("OpenAPI document is missing info or paths")
    title = info.get("title")
    if not isinstance(title, str) or "arax" not in title.lower():
        raise PreflightError("OpenAPI title does not identify ARAX")
    if "/query" not in paths:
        raise PreflightError("OpenAPI document does not expose /query")
    version_match = TRAPI_VERSION_RE.search(title)
    trapi_version = version_match.group(1) if version_match else None
    arax_version = str(info["version"]) if info.get("version") is not None else None
    warnings = list(initial_warnings)
    _check_trapi_version(trapi_version, allow_untested_version, warnings)
    if arax_version != TESTED_ARAX_VERSION:
        _append_warning(
            warnings,
            "UNTESTED_SERVICE_VERSION",
            "The ARAX version differs from the tested production version.",
            {"reported": arax_version, "tested": TESTED_ARAX_VERSION},
        )
    return ServiceInfo(
        base_url=base_url,
        openapi_url=openapi_url,
        arax_version=arax_version,
        trapi_version=trapi_version,
        warnings=tuple(warnings),
    )


def fetch_openapi(
    base_url: str,
    *,
    allow_untested_version: bool,
    initial_warnings: Sequence[dict[str, Any]] = (),
) -> tuple[ServiceInfo, HttpResult]:
    openapi_url = base_url + "/openapi.json"
    try:
        result = request_get_with_retry(openapi_url)
    except TransportError as exc:
        raise PreflightError(
            str(exc),
            http_status=exc.http_status,
            response_body=exc.response_body,
            attempts=exc.attempts,
        ) from exc
    try:
        payload = _decode_json(result.body, "OpenAPI response")
        service = parse_openapi_service_info(
            payload,
            base_url=base_url,
            openapi_url=openapi_url,
            allow_untested_version=allow_untested_version,
            initial_warnings=initial_warnings,
        )
    except (PreflightError, ResponseError) as exc:
        if isinstance(exc, ResponseError):
            wrapped = PreflightError(str(exc))
        else:
            wrapped = exc
        wrapped.http_status = result.status
        wrapped.response_body = result.body
        wrapped.attempts = result.attempts
        raise wrapped
    return service, result


def normalize_entity_request(base_url: str, term: str) -> HttpResult:
    query = urllib.parse.urlencode({"q": term})
    return request_get_with_retry(base_url + "/entity?" + query)


def parse_normalization_response(
    payload: Any,
    *,
    term: str,
    expected_category: str | None,
    max_synonyms: int,
    service: ServiceInfo,
) -> tuple[dict[str, Any], bool]:
    warnings = [make_warning("PUBLIC_QUERY", "The normalization request was sent to a public service.")]
    requires_confirmation = not _looks_like_curie(term)
    if requires_confirmation:
        _append_warning(
            warnings,
            "NORMALIZATION_REQUIRES_CONFIRMATION",
            "Review the normalized identifier and category before constructing a graph query.",
        )
    record: Any = payload.get(term) if isinstance(payload, dict) else None
    if record is None and isinstance(payload, dict) and len(payload) == 1:
        record = next(iter(payload.values()))
    usable = isinstance(record, dict) and isinstance(record.get("id"), dict)
    identifier_record = record.get("id", {}) if usable else {}
    identifier = identifier_record.get("identifier") if isinstance(identifier_record, dict) else None
    if not isinstance(identifier, str) or not _looks_like_curie(identifier):
        usable = False
        identifier = None
    category = identifier_record.get("category") if isinstance(identifier_record, dict) else None
    if expected_category is not None and category != expected_category and usable:
        _append_warning(
            warnings,
            "NORMALIZATION_CATEGORY_MISMATCH",
            "The canonical category differs from the expected category.",
            {"expected": expected_category, "returned": category},
        )
    nodes = record.get("nodes", []) if isinstance(record, dict) else []
    preview: list[dict[str, Any]] = []
    if isinstance(nodes, list):
        for node in nodes[:max_synonyms]:
            if not isinstance(node, dict):
                continue
            preview.append(
                {
                    "identifier": node.get("identifier", node.get("id")),
                    "name": node.get("name"),
                    "category": node.get("category"),
                }
            )
    if not usable:
        _append_warning(
            warnings,
            "NO_RESULTS",
            "Normalization returned no usable canonical CURIE.",
        )
    summary = {
        "schema_version": "1.0",
        "kind": "normalization",
        "query": {
            "input": term,
            "expected_category": expected_category,
            "requires_user_confirmation": requires_confirmation,
        },
        "service": service.as_dict(),
        "canonical": {
            "identifier": identifier,
            "name": identifier_record.get("name") if isinstance(identifier_record, dict) else None,
            "category": category,
        },
        "category_counts": record.get("categories", {}) if isinstance(record, dict) else {},
        "total_synonyms": record.get("total_synonyms", 0) if isinstance(record, dict) else 0,
        "synonym_preview": preview,
        "warnings": warnings,
    }
    return summary, usable


def _require_exact_keys(value: Mapping[str, Any], allowed: set[str], label: str) -> None:
    extras = set(value) - allowed
    missing = allowed - set(value)
    if extras or missing:
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(sorted(missing)))
        if extras:
            details.append("unsupported " + ", ".join(sorted(extras)))
        raise UsageError(f"{label} has " + "; ".join(details))


def _validate_edge_contract(edge: Any) -> tuple[str, str]:
    if not isinstance(edge, dict):
        raise UsageError("saved request contains an invalid query edge")
    allowed = {"subject", "object", "predicates"}
    if "qualifier_constraints" in edge:
        allowed.add("qualifier_constraints")
    _require_exact_keys(edge, allowed, "saved query edge")
    subject = edge.get("subject")
    object_ = edge.get("object")
    if not isinstance(subject, str) or not isinstance(object_, str):
        raise UsageError("saved query edge lacks subject or object")
    predicates = edge.get("predicates")
    if not isinstance(predicates, list):
        raise UsageError("saved query edge lacks predicates")
    validate_predicates(predicates)
    constraints = edge.get("qualifier_constraints")
    if constraints is not None:
        if not isinstance(constraints, list) or len(constraints) != 1:
            raise UsageError("saved query edge must have one AND qualifier set")
        if not isinstance(constraints[0], dict):
            raise UsageError("saved query edge has invalid qualifiers")
        _require_exact_keys(constraints[0], {"qualifier_set"}, "qualifier constraint")
        qualifier_set = constraints[0].get("qualifier_set")
        if not isinstance(qualifier_set, list):
            raise UsageError("saved query edge has invalid qualifiers")
        raw = []
        for qualifier in qualifier_set:
            if not isinstance(qualifier, dict):
                raise UsageError("saved query edge has invalid qualifiers")
            _require_exact_keys(
                qualifier,
                {"qualifier_type_id", "qualifier_value"},
                "saved qualifier",
            )
            raw.append(f"{qualifier.get('qualifier_type_id')}={qualifier.get('qualifier_value')}")
        parse_qualifiers(raw)
    return subject, object_


def _parse_kp_parameter(value: str) -> tuple[str, tuple[str, ...]]:
    if value == "infores:rtx-kg2":
        return "lookup", (value,)
    if not value.startswith("[") or not value.endswith("]"):
        raise UsageError("saved request does not use lookup or selected-provider federation")
    providers = tuple(validate_provider_id(item) for item in value[1:-1].split(",") if item)
    if not MIN_FEDERATED_PROVIDERS <= len(providers) <= MAX_PROVIDERS:
        raise UsageError("saved federated request must name two to five providers")
    _unique(list(providers), "provider")
    return "federated", providers


def validate_saved_request_contract(payload: Any) -> QueryContract:
    if not isinstance(payload, dict) or "workflow" in payload:
        raise UsageError("saved request is not a supported fixed-operation request")
    _require_exact_keys(
        payload,
        {"message", "operations", "stream_progress", "submitter"},
        "saved request",
    )
    if payload["stream_progress"] is not False or payload["submitter"] != SUBMITTER:
        raise UsageError("saved request changes fixed submission controls")
    message = payload.get("message")
    if not isinstance(message, dict):
        raise UsageError("saved request lacks a query graph")
    _require_exact_keys(message, {"query_graph"}, "saved message")
    graph = message.get("query_graph") if isinstance(message, dict) else None
    if not isinstance(graph, dict):
        raise UsageError("saved request lacks a query graph")
    _require_exact_keys(graph, {"nodes", "edges"}, "saved query graph")
    nodes = graph.get("nodes") if isinstance(graph, dict) else None
    edges = graph.get("edges") if isinstance(graph, dict) else None
    if not isinstance(nodes, dict) or not isinstance(edges, dict):
        raise UsageError("saved request lacks a query graph")
    if set(nodes) == {"n0", "n1"} and set(edges) == {"e0"}:
        kind = "one-hop"
    elif set(nodes) == {"n0", "n1", "n2"} and set(edges) == {"e0", "e1"}:
        kind = "two-hop"
    else:
        raise UsageError("saved request must be exactly one hop or endpoint-pinned two hop")
    qnode_ids: dict[str, list[str]] = {}
    for key, node in nodes.items():
        if not isinstance(node, dict):
            raise UsageError("saved request contains an invalid qnode")
        allowed_node_keys = {"categories"}
        if "ids" in node:
            allowed_node_keys.add("ids")
        _require_exact_keys(node, allowed_node_keys, "saved qnode")
        categories = node.get("categories")
        if not isinstance(categories, list) or len(categories) != 1:
            raise UsageError("every saved qnode must have exactly one category")
        validate_biolink_term(categories[0], "Biolink category")
        ids = node.get("ids", [])
        if not isinstance(ids, list) or len(ids) > 1:
            raise UsageError("saved qnodes may have at most one CURIE")
        qnode_ids[key] = [validate_curie(value) for value in ids]
    if kind == "one-hop" and not (qnode_ids["n0"] or qnode_ids["n1"]):
        raise UsageError("saved one-hop request has no pinned endpoint")
    if kind == "two-hop" and not (
        len(qnode_ids["n0"]) == 1 and not qnode_ids["n1"] and len(qnode_ids["n2"]) == 1
    ):
        raise UsageError("saved two-hop request is not endpoint pinned")
    query_edges = {key: _validate_edge_contract(edge) for key, edge in edges.items()}
    expected_edges = {"e0": ("n0", "n1")}
    if kind == "two-hop":
        expected_edges["e1"] = ("n1", "n2")
    if query_edges != expected_edges:
        raise UsageError("saved query edge topology is unsupported")
    operations = payload.get("operations")
    if not isinstance(operations, dict):
        raise UsageError("saved request lacks operations")
    _require_exact_keys(operations, {"actions"}, "saved operations")
    actions = operations.get("actions") if isinstance(operations, dict) else None
    expected_count = 4 if kind == "one-hop" else 5
    if not isinstance(actions, list) or len(actions) != expected_count:
        raise UsageError("saved request does not contain the fixed action sequence")
    if actions[-3] != "scoreless_resultify(ignore_edge_direction=true)":
        raise UsageError("saved request does not use scoreless resultification")
    filter_match = FILTER_RE.fullmatch(actions[-2]) if isinstance(actions[-2], str) else None
    if filter_match is None or actions[-1] != "return(response=true,store=false)":
        raise UsageError("saved request does not use the fixed filter and return actions")
    result_limit = validate_result_limit(int(filter_match.group(1)))
    expand_actions = actions[:-3]
    expand_keys: list[str] = []
    mode: str | None = None
    provider_ids: tuple[str, ...] | None = None
    for action in expand_actions:
        match = EXPAND_RE.fullmatch(action) if isinstance(action, str) else None
        if match is None:
            raise UsageError("saved request contains an unsupported expansion action")
        current_mode, current_providers = _parse_kp_parameter(match.group(2))
        if mode is not None and (current_mode, current_providers) != (mode, provider_ids):
            raise UsageError("saved request changes providers between edges")
        mode, provider_ids = current_mode, current_providers
        expand_keys.append(match.group(1))
    if kind == "one-hop":
        if expand_keys != ["e0"]:
            raise UsageError("saved one-hop request has invalid expansion order")
        expand_order = None
    elif expand_keys == ["e1", "e0"]:
        expand_order = "right-first"
    elif expand_keys == ["e0", "e1"]:
        expand_order = "left-first"
    else:
        raise UsageError("saved two-hop request has invalid expansion order")
    return QueryContract(
        kind=kind,
        mode=mode or "lookup",
        provider_ids=provider_ids or ("infores:rtx-kg2",),
        expand_order=expand_order,
        qnode_ids=qnode_ids,
        result_limit=result_limit,
        query_edges=query_edges,
    )


def _normalize_node_bindings(value: Any) -> tuple[dict[str, list[dict[str, Any]]], dict[str, set[str]]]:
    if not isinstance(value, dict):
        raise ResponseError("result node_bindings is not an object")
    normalized: dict[str, list[dict[str, Any]]] = {}
    identifiers: dict[str, set[str]] = {}
    for qnode_key, bindings in value.items():
        if not isinstance(bindings, list):
            raise ResponseError("node binding list is malformed")
        normalized[qnode_key] = []
        identifiers[qnode_key] = set()
        for binding in bindings:
            if not isinstance(binding, dict) or not isinstance(binding.get("id"), str):
                raise ResponseError("node binding is missing an identifier")
            identifiers[qnode_key].add(binding["id"])
            normalized[qnode_key].append(
                {
                    "id": binding["id"],
                    "query_id": binding.get("query_id"),
                    "attributes": binding.get("attributes", []),
                }
            )
    return normalized, identifiers


def _resource_ids_for_role(sources: Sequence[dict[str, Any]], role: str) -> list[str]:
    found: list[str] = []
    for source in sources:
        resource_role = source.get("resource_role")
        if isinstance(resource_role, str) and resource_role.removeprefix("biolink:") == role:
            resource_id = source.get("resource_id")
            if isinstance(resource_id, str) and resource_id not in found:
                found.append(resource_id)
    return found


def extract_publications(edge: Mapping[str, Any]) -> list[str]:
    publications: list[str] = []
    attributes = edge.get("attributes", [])
    if not isinstance(attributes, list):
        return publications
    for attribute in attributes:
        if not isinstance(attribute, dict) or attribute.get("attribute_type_id") != "biolink:publications":
            continue
        value = attribute.get("value")
        candidates: Iterable[Any] = value if isinstance(value, list) else [value]
        for candidate in candidates:
            if isinstance(candidate, str) and candidate not in publications:
                publications.append(candidate)
    return publications


def _classify_logs(
    payload: Mapping[str, Any],
    contract: QueryContract,
    warnings: list[dict[str, Any]],
) -> bool:
    partial = False
    logs = payload.get("logs", [])
    if not isinstance(logs, list):
        return partial
    for log in logs:
        if not isinstance(log, dict):
            continue
        message = _sanitize_text(log.get("message", ""), MAX_WARNING_MESSAGE)
        code = _sanitize_text(log.get("code", ""), 100)
        level = _sanitize_text(log.get("level", ""), 30).lower()
        combined = f"{code} {message}".lower()
        provider = next((item for item in contract.provider_ids if item.lower() in combined), None)
        context = {"provider_id": provider} if provider else {}
        failure_level = level in {"warning", "error", "critical", "fatal"}
        timeout_failure = failure_level and (
            "timed out" in combined
            or "timeout error" in combined
            or "timeout failure" in combined
            or "timeout" in code.lower()
        )
        malformed_failure = failure_level and any(
            token in combined for token in ("malformed", "deserial", "invalid trapi")
        )
        if timeout_failure:
            _append_warning(warnings, "KP_TIMEOUT", message or "A provider timed out.", context)
            partial = partial or contract.mode == "federated"
        elif malformed_failure:
            _append_warning(
                warnings,
                "MALFORMED_KP_RESPONSE",
                message or "A provider returned a malformed response.",
                context,
            )
            partial = partial or contract.mode == "federated"
        elif contract.mode == "federated" and level in {"warning", "error", "critical"} and (
            "kp" in combined or provider is not None
        ):
            _append_warning(warnings, "KP_ERROR", message or "A provider reported an error.", context)
            partial = True
        result_pruning = (
            "result_limit" in code.lower()
            or "result_prun" in code.lower()
            or "pruned result" in combined
            or ("removed" in combined and "result" in combined)
        )
        if result_pruning:
            _append_warning(
                warnings,
                "INTERNAL_PRUNING_DETECTED",
                message or "ARAX reported internal pruning or result removal.",
            )
    return partial


def parse_trapi_response(
    payload: Any,
    contract: QueryContract,
    *,
    service: ServiceInfo | None = None,
    initial_warnings: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ResponseError("TRAPI response is not an object")
    message = payload.get("message")
    if not isinstance(message, dict):
        raise ResponseError("TRAPI response is missing message")
    knowledge_graph = message.get("knowledge_graph")
    if not isinstance(knowledge_graph, dict):
        raise ResponseError("TRAPI response is missing knowledge_graph")
    kg_nodes = knowledge_graph.get("nodes")
    kg_edges = knowledge_graph.get("edges")
    results = message.get("results")
    if not isinstance(kg_nodes, dict) or not isinstance(kg_edges, dict) or not isinstance(results, list):
        raise ResponseError("TRAPI response has malformed nodes, edges, or results")
    auxiliary_graphs = message.get("auxiliary_graphs", {})
    if not isinstance(auxiliary_graphs, dict):
        auxiliary_graphs = {}
    warnings = [dict(item) for item in initial_warnings]
    _append_warning(
        warnings,
        "UNSCORED_RESPONSE_ORDER",
        "Result positions are preserved from the unscored ARAX response.",
    )
    partial = _classify_logs(payload, contract, warnings)
    summarized_results: list[dict[str, Any]] = []
    analyses_count = 0
    bound_edges_count = 0
    for position, result in enumerate(results[: contract.result_limit], start=1):
        if not isinstance(result, dict):
            raise ResponseError("TRAPI result is not an object")
        node_bindings, binding_ids = _normalize_node_bindings(result.get("node_bindings"))
        if set(node_bindings) != set(contract.qnode_ids):
            raise ResponseError("result node_bindings do not match the supported query graph")
        analyses = result.get("analyses")
        if not isinstance(analyses, list):
            raise ResponseError("TRAPI result analyses is not a list")
        normalized_analyses: list[dict[str, Any]] = []
        for analysis in analyses:
            if not isinstance(analysis, dict):
                raise ResponseError("TRAPI analysis is not an object")
            edge_bindings = analysis.get("edge_bindings")
            if not isinstance(edge_bindings, dict):
                raise ResponseError("TRAPI analysis edge_bindings is not an object")
            if set(edge_bindings) != set(contract.query_edges):
                raise ResponseError("TRAPI analysis edge_bindings do not match the supported query graph")
            support_graph_ids = analysis.get("support_graphs", [])
            if not isinstance(support_graph_ids, list):
                support_graph_ids = []
            missing_support = [item for item in support_graph_ids if item not in auxiliary_graphs]
            if support_graph_ids and missing_support:
                support_status = "missing"
                for graph_id in missing_support:
                    _append_warning(
                        warnings,
                        "MISSING_AUXILIARY_GRAPH",
                        "A referenced auxiliary graph was not returned.",
                        {"support_graph_id": graph_id},
                    )
            elif support_graph_ids:
                support_status = "available"
            else:
                support_status = "not_returned"
            normalized_edges: dict[str, list[dict[str, Any]]] = {}
            for qedge_key in contract.query_edges:
                bindings = edge_bindings.get(qedge_key, [])
                if not isinstance(bindings, list):
                    raise ResponseError("query-edge binding list is malformed")
                normalized_edges[qedge_key] = []
                qsubject, qobject = contract.query_edges[qedge_key]
                expected_subjects = binding_ids.get(qsubject, set())
                expected_objects = binding_ids.get(qobject, set())
                for binding in bindings:
                    if not isinstance(binding, dict) or not isinstance(binding.get("id"), str):
                        raise ResponseError("query-edge binding is missing an edge identifier")
                    edge_id = binding["id"]
                    edge = kg_edges.get(edge_id)
                    if not isinstance(edge, dict):
                        raise ResponseError(f"bound knowledge-graph edge is missing: {edge_id}")
                    subject = edge.get("subject")
                    object_ = edge.get("object")
                    predicate = edge.get("predicate")
                    if not all(isinstance(item, str) for item in (subject, object_, predicate)):
                        raise ResponseError(f"bound edge is malformed: {edge_id}")
                    matches_direction = subject in expected_subjects and object_ in expected_objects
                    matches_reverse = subject in expected_objects and object_ in expected_subjects
                    if not matches_direction and not matches_reverse:
                        raise ResponseError(
                            f"bound edge endpoints do not match result node bindings: {edge_id}"
                        )
                    if matches_reverse:
                        _append_warning(
                            warnings,
                            "REVERSED_EDGE_BINDING",
                            "A bound edge does not match the query's physical direction; it was preserved.",
                            {"edge_id": edge_id, "query_edge": qedge_key},
                        )
                    sources_value = edge.get("sources", [])
                    sources = [dict(item) for item in sources_value if isinstance(item, dict)] if isinstance(sources_value, list) else []
                    primary = _resource_ids_for_role(sources, "primary_knowledge_source")
                    aggregators = _resource_ids_for_role(sources, "aggregator_knowledge_source")
                    supporting = _resource_ids_for_role(sources, "supporting_data_source")
                    if not primary:
                        _append_warning(
                            warnings,
                            "NO_PRIMARY_SOURCE_RETURNED",
                            "No primary knowledge source was returned for a bound edge.",
                            {"edge_id": edge_id},
                        )
                    publications = extract_publications(edge)
                    if not publications:
                        _append_warning(
                            warnings,
                            "NO_PUBLICATIONS_RETURNED",
                            "No recognized publication metadata was returned for a bound edge.",
                            {"edge_id": edge_id},
                        )
                    qualifiers_value = edge.get("qualifiers", [])
                    qualifiers = []
                    if isinstance(qualifiers_value, list):
                        qualifiers = [
                            {
                                "qualifier_type_id": item.get("qualifier_type_id"),
                                "qualifier_value": item.get("qualifier_value"),
                            }
                            for item in qualifiers_value
                            if isinstance(item, dict)
                        ]
                    subject_node = kg_nodes.get(subject, {})
                    object_node = kg_nodes.get(object_, {})
                    normalized_edges[qedge_key].append(
                        {
                            "edge_id": edge_id,
                            "subject": subject,
                            "subject_name": subject_node.get("name") if isinstance(subject_node, dict) else None,
                            "predicate": predicate,
                            "object": object_,
                            "object_name": object_node.get("name") if isinstance(object_node, dict) else None,
                            "matches_query_direction": matches_direction,
                            "qualifiers": qualifiers,
                            "sources": sources,
                            "primary_knowledge_sources": primary,
                            "aggregator_knowledge_sources": aggregators,
                            "supporting_data_sources": supporting,
                            "publication_ids": publications,
                            "publication_availability": "available" if publications else "not_returned",
                            "support_graph_ids": list(support_graph_ids),
                            "support_graph_status": support_status,
                        }
                    )
                    bound_edges_count += 1
            normalized_analyses.append(
                {
                    "resource_id": analysis.get("resource_id"),
                    "score": analysis.get("score"),
                    "support_graphs": list(support_graph_ids),
                    "edge_bindings": normalized_edges,
                }
            )
            analyses_count += 1
        summarized_results.append(
            {
                "position": position,
                "description": _sanitize_text(result.get("description"), MAX_DISPLAY_TEXT)
                if result.get("description") is not None
                else None,
                "node_bindings": node_bindings,
                "analyses": normalized_analyses,
            }
        )
    raw_count = len(results)
    total_results_count = payload.get("total_results_count")
    if not isinstance(total_results_count, int) or isinstance(total_results_count, bool):
        total_results_count = None
    pruning = any(item.get("code") == "INTERNAL_PRUNING_DETECTED" for item in warnings)
    if raw_count > contract.result_limit or pruning or (
        total_results_count is not None and total_results_count > raw_count
    ):
        truncation_status = "confirmed"
    elif raw_count == contract.result_limit:
        truncation_status = "possible"
    else:
        truncation_status = "no"
    if raw_count >= contract.result_limit:
        _append_warning(
            warnings,
            "RESULT_LIMIT_REACHED",
            "The response reached or exceeded the requested result limit.",
            {"result_limit": contract.result_limit},
        )
    if raw_count == 0:
        _append_warning(
            warnings,
            "NO_RESULTS",
            "ARAX returned no results under these constraints.",
        )
    if service is None:
        service_data = {
            "base_url": None,
            "openapi_url": None,
            "arax_version": payload.get("tool_version"),
            "trapi_version": payload.get("schema_version"),
            "biolink_version": payload.get("biolink_version"),
        }
    else:
        service_data = service.as_dict(biolink_version=payload.get("biolink_version"))
    return {
        "schema_version": "1.0",
        "query": {
            "kind": contract.kind,
            "mode": contract.mode,
            "provider_ids": list(contract.provider_ids),
            "expand_order": contract.expand_order,
            "qnode_ids": contract.qnode_ids,
            "result_limit": contract.result_limit,
        },
        "service": service_data,
        "counts": {
            "results_returned": raw_count,
            "results_summarized": len(summarized_results),
            "analyses_summarized": analyses_count,
            "bound_edges_summarized": bound_edges_count,
            "knowledge_graph_nodes": len(kg_nodes),
            "knowledge_graph_edges": len(kg_edges),
            "server_total_results_count": total_results_count,
        },
        "truncation_status": truncation_status,
        "completeness": "partial" if partial else "complete",
        "results": summarized_results,
        "warnings": warnings,
    }


def render_text_summary(
    summary: Mapping[str, Any],
    *,
    summary_path: str = "summary.json",
    response_path: str = "response.json",
) -> str:
    def rendered(value: Any, limit: int = 200) -> str:
        return _sanitize_text(value, limit)

    def rendered_list(values: Any, *, limit: int = 200) -> str:
        if not isinstance(values, list) or not values:
            return "not returned"
        return ", ".join(rendered(value, limit) for value in values)

    lines: list[str] = []
    query = summary.get("query", {})
    counts = summary.get("counts", {})
    lines.append(
        f"ARAX returned {counts.get('results_returned', 0)} result(s); "
        f"showing {counts.get('results_summarized', 0)} in unscored response order."
    )
    lines.append(
        f"Query: {rendered(query.get('kind'))} / {rendered(query.get('mode'))}; "
        f"limit {rendered(query.get('result_limit'))}; "
        f"truncation {rendered(summary.get('truncation_status'))}; "
        f"completeness {rendered(summary.get('completeness'))}."
    )
    warnings = summary.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        lines.append("Warnings:")
        for warning in warnings:
            if isinstance(warning, dict):
                lines.append(
                    f"  - {rendered(warning.get('code'), 100)}: "
                    f"{rendered(warning.get('message', ''), MAX_WARNING_MESSAGE)}"
                )
    results = summary.get("results", [])
    if not results:
        lines.append("Not returned under these constraints.")
    for result in results if isinstance(results, list) else []:
        if not isinstance(result, dict):
            continue
        lines.append(
            f"Unscored position {rendered(result.get('position'))}: "
            f"{rendered(result.get('description') or 'candidate path', MAX_DISPLAY_TEXT)}"
        )
        node_bindings = result.get("node_bindings", {})
        if isinstance(node_bindings, dict):
            for qnode, bindings in node_bindings.items():
                ids = [item.get("id") for item in bindings if isinstance(item, dict)] if isinstance(bindings, list) else []
                lines.append(f"  {rendered(qnode, 100)}: {rendered_list(ids)}")
        analyses = result.get("analyses", [])
        for analysis_index, analysis in enumerate(analyses if isinstance(analyses, list) else [], start=1):
            if not isinstance(analysis, dict):
                continue
            lines.append(
                f"  Analysis {analysis_index}: resource {rendered(analysis.get('resource_id'))}; "
                f"score {rendered(analysis.get('score'))}"
            )
            edge_bindings = analysis.get("edge_bindings", {})
            if not isinstance(edge_bindings, dict):
                continue
            for qedge, edges in edge_bindings.items():
                for edge in edges if isinstance(edges, list) else []:
                    if not isinstance(edge, dict):
                        continue
                    subject = edge.get("subject")
                    subject_name = edge.get("subject_name")
                    object_ = edge.get("object")
                    object_name = edge.get("object_name")
                    lines.append(
                        f"    {rendered(qedge, 100)}/{rendered(edge.get('edge_id'))}: "
                        f"{rendered(subject)} ({rendered(subject_name)}) "
                        f"--{rendered(edge.get('predicate'))}--> "
                        f"{rendered(object_)} ({rendered(object_name)})"
                    )
                    if not edge.get("matches_query_direction"):
                        lines.append("      Direction warning: physical edge orientation differs from the query.")
                    qualifiers = edge.get("qualifiers", [])
                    if qualifiers:
                        rendered_qualifiers = ", ".join(
                            f"{_sanitize_text(item.get('qualifier_type_id'), 200)}="
                            f"{_sanitize_text(item.get('qualifier_value'), 200)}"
                            for item in qualifiers
                            if isinstance(item, dict)
                        )
                        lines.append(f"      Qualifiers: {rendered_qualifiers}")
                    for label, field in (
                        ("Primary sources", "primary_knowledge_sources"),
                        ("Aggregator sources", "aggregator_knowledge_sources"),
                        ("Supporting sources", "supporting_data_sources"),
                    ):
                        values = edge.get(field, [])
                        lines.append(f"      {label}: {rendered_list(values)}")
                    publications = edge.get("publication_ids", [])
                    preview = publications[:PUBLICATION_PREVIEW] if isinstance(publications, list) else []
                    lines.append(
                        f"      Publications: {len(publications) if isinstance(publications, list) else 0}; "
                        f"preview {rendered_list(preview)}"
                    )
    lines.append(f"Complete bounded publication and source lists: {rendered(summary_path, 500)}")
    lines.append(f"Exact TRAPI payload: {rendered(response_path, 500)}")
    lines.append("Candidate paths require subsequent scientific verification.")
    return "\n".join(lines)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def prepare_output_directory(value: str | Path) -> Path:
    path = Path(value)
    try:
        if path.exists():
            if not path.is_dir():
                raise UsageError("output path exists and is not a directory")
            if any(path.iterdir()):
                raise UsageError("output directory must be new or empty")
        else:
            path.mkdir(parents=True)
    except UsageError:
        raise
    except OSError as exc:
        raise ResponseError(f"could not prepare output directory: {_sanitize_text(exc)}") from exc
    return path


def atomic_write_bytes(path: Path, value: bytes) -> None:
    try:
        if path.exists():
            raise ResponseError(f"refusing to overwrite existing artifact: {path.name}")
    except ResponseError:
        raise
    except OSError as exc:
        raise ResponseError(f"could not inspect artifact path {path.name}: {_sanitize_text(exc)}") from exc
    descriptor: int | None = None
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".ncats-arax-", dir=str(path.parent)
        )
        temporary = Path(temporary_name)
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        handle = os.fdopen(descriptor, "wb")
        descriptor = None
        with handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise ResponseError(f"refusing to overwrite concurrently created artifact: {path.name}")
        os.replace(temporary, path)
    except ResponseError:
        raise
    except OSError as exc:
        raise ResponseError(f"could not write artifact {path.name}: {_sanitize_text(exc)}") from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        except OSError:
            pass


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> bytes:
    try:
        encoded = (
            json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ResponseError("artifact data cannot be represented as strict JSON") from exc
    atomic_write_bytes(path, encoded)
    return encoded


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_manifest(
    command: str,
    *,
    base_url: str,
    privacy_acknowledged: bool,
    http_timeout: int,
    result_limit: int | None = None,
) -> dict[str, Any]:
    return {
        "manifest_version": "1.0",
        "run_id": str(uuid.uuid4()),
        "command": command,
        "started_at": _utc_now(),
        "finished_at": None,
        "execution_status": "client_error",
        "result_status": "not_available",
        "privacy_acknowledged": privacy_acknowledged,
        "client": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
        "service": {
            "base_url": base_url,
            "openapi_url": base_url + "/openapi.json",
            "arax_version": None,
            "trapi_version": None,
            "biolink_version": None,
        },
        "request": {
            "method": "GET",
            "url": base_url + "/openapi.json",
            "file": None,
            "bytes": None,
            "sha256": None,
        },
        "response": {
            "http_status": None,
            "file": None,
            "bytes": None,
            "sha256": None,
            "elapsed_ms": None,
        },
        "limits": {
            "result_limit": result_limit,
            "response_byte_limit": MAX_RESPONSE_BYTES,
            "kp_timeout_seconds": KP_TIMEOUT_SECONDS if command in {"one-hop", "two-hop"} else None,
            "http_timeout_seconds": http_timeout,
        },
        "attempts": {"openapi_get": 0, "entity_get": 0, "query_post": 0},
        "artifacts": {"request": None, "response": None, "summary": None},
        "error": None,
        "warnings": [],
    }


def _apply_service_to_manifest(manifest: dict[str, Any], service: ServiceInfo) -> None:
    manifest["service"].update(service.as_dict())
    manifest["warnings"] = [dict(item) for item in service.warnings]


def _record_response(manifest: dict[str, Any], result: HttpResult, filename: str = "response.json") -> None:
    manifest["response"].update(
        {
            "http_status": result.status,
            "file": filename,
            "bytes": len(result.body),
            "sha256": sha256_bytes(result.body),
            "elapsed_ms": result.elapsed_ms,
        }
    )
    manifest["artifacts"]["response"] = filename


def _write_manifest(output_dir: Path, manifest: dict[str, Any]) -> None:
    manifest["finished_at"] = _utc_now()
    atomic_write_json(output_dir / "manifest.json", manifest)


def _retain_failure(
    output_dir: Path | None,
    manifest: dict[str, Any] | None,
    error: AraxClientError,
    stage: str,
) -> None:
    if output_dir is None or manifest is None:
        return
    try:
        manifest["execution_status"] = "http_error" if error.exit_code == 5 else "client_error"
        manifest["result_status"] = "not_available"
        manifest["error"] = {"kind": error.kind, "message": _sanitize_text(error)}
        if error.http_status is not None:
            manifest["response"]["http_status"] = error.http_status
        attempt_key = {
            "openapi": "openapi_get",
            "entity": "entity_get",
            "query": "query_post",
        }.get(stage)
        if error.attempts and attempt_key is not None:
            manifest["attempts"][attempt_key] = error.attempts
        if error.response_body is not None and not (output_dir / "response.json").exists():
            atomic_write_bytes(output_dir / "response.json", error.response_body)
            failed = HttpResult(
                status=error.http_status or 0,
                body=error.response_body,
                headers={},
                elapsed_ms=0,
                attempts=error.attempts,
            )
            _record_response(manifest, failed)
        if not (output_dir / "manifest.json").exists():
            _write_manifest(output_dir, manifest)
    except Exception as manifest_error:
        print(
            f"warning: could not retain failure artifacts: {_sanitize_text(manifest_error)}",
            file=sys.stderr,
        )


def _json_from_http(result: HttpResult, label: str) -> Any:
    return _decode_json(result.body, label)


def _preflight_summary(service: ServiceInfo) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "kind": "preflight",
        "service": service.as_dict(),
        "checks": {
            "title_identifies_arax": True,
            "query_path_present": True,
            "version_supported": _version_series(service.trapi_version) in SUPPORTED_TRAPI_SERIES,
        },
        "warnings": [dict(item) for item in service.warnings],
    }


def handle_preflight(args: argparse.Namespace) -> int:
    base_url, endpoint_warnings = validate_base_url(args.base_url, args.allow_nonproduction_endpoint)
    output_dir = prepare_output_directory(args.output_dir) if args.output_dir else None
    manifest = new_manifest(
        "preflight", base_url=base_url, privacy_acknowledged=False, http_timeout=GET_TIMEOUT_SECONDS
    ) if output_dir else None
    stage = "openapi"
    try:
        service, result = fetch_openapi(
            base_url,
            allow_untested_version=args.allow_untested_version,
            initial_warnings=endpoint_warnings,
        )
        summary = _preflight_summary(service)
        if output_dir is not None and manifest is not None:
            _apply_service_to_manifest(manifest, service)
            manifest["attempts"]["openapi_get"] = result.attempts
            atomic_write_bytes(output_dir / "response.json", result.body)
            _record_response(manifest, result)
            atomic_write_json(output_dir / "summary.json", summary)
            manifest["artifacts"]["summary"] = "summary.json"
            manifest["execution_status"] = "success"
            manifest["result_status"] = "not_available"
            _write_manifest(output_dir, manifest)
        print(
            f"ARAX {service.arax_version or 'unknown'}; TRAPI {service.trapi_version or 'unknown'}; "
            f"/query available at {service.base_url}"
        )
        for warning in service.warnings:
            print(f"warning {warning['code']}: {warning['message']}", file=sys.stderr)
        return 0
    except AraxClientError as exc:
        _retain_failure(output_dir, manifest, exc, stage)
        raise


def handle_normalize(args: argparse.Namespace) -> int:
    if not 0 <= args.max_synonyms <= 50:
        raise UsageError("--max-synonyms must be between 0 and 50")
    expected_category = (
        validate_biolink_term(args.expected_category, "Biolink category")
        if args.expected_category
        else None
    )
    if not args.term or len(args.term) > MAX_IDENTIFIER_LENGTH or _has_control(args.term):
        raise UsageError("normalization term must be control-free and at most 200 characters")
    base_url, endpoint_warnings = validate_base_url(args.base_url, args.allow_nonproduction_endpoint)
    output_dir = prepare_output_directory(args.output_dir)
    manifest = new_manifest(
        "normalize", base_url=base_url, privacy_acknowledged=True, http_timeout=GET_TIMEOUT_SECONDS
    )
    stage = "openapi"
    try:
        service, preflight_result = fetch_openapi(
            base_url,
            allow_untested_version=args.allow_untested_version,
            initial_warnings=endpoint_warnings,
        )
        _apply_service_to_manifest(manifest, service)
        manifest["attempts"]["openapi_get"] = preflight_result.attempts
        stage = "entity"
        manifest["request"].update(
            {
                "method": "GET",
                "url": base_url + "/entity?" + urllib.parse.urlencode({"q": args.term}),
            }
        )
        entity_result = normalize_entity_request(base_url, args.term)
        manifest["attempts"]["entity_get"] = entity_result.attempts
        atomic_write_bytes(output_dir / "response.json", entity_result.body)
        _record_response(manifest, entity_result)
        payload = _json_from_http(entity_result, "entity response")
        summary, usable = parse_normalization_response(
            payload,
            term=args.term,
            expected_category=expected_category,
            max_synonyms=args.max_synonyms,
            service=service,
        )
        atomic_write_json(output_dir / "summary.json", summary)
        manifest["artifacts"]["summary"] = "summary.json"
        manifest["warnings"] = summary["warnings"]
        manifest["execution_status"] = "success"
        manifest["result_status"] = "results" if usable else "no_results"
        _write_manifest(output_dir, manifest)
        if not usable:
            raise NormalizationError("normalization returned no usable canonical CURIE")
        canonical = summary["canonical"]
        print(
            f"Canonical: {canonical['identifier']} ({canonical.get('name') or 'name not returned'}; "
            f"{canonical.get('category') or 'category not returned'})"
        )
        if summary["query"]["requires_user_confirmation"]:
            print("Review and confirm this normalization before constructing a graph query.")
        return 0
    except NormalizationError:
        raise
    except AraxClientError as exc:
        _retain_failure(output_dir, manifest, exc, stage)
        raise


def _build_from_args(args: argparse.Namespace) -> tuple[dict[str, Any], QueryContract, int]:
    providers, limit = resolve_mode(args.mode, args.kp or [], args.result_limit)
    if args.command == "one-hop":
        body = build_one_hop_query(
            subject_id=args.subject_id,
            subject_category=args.subject_category,
            predicates=args.predicate,
            object_id=args.object_id,
            object_category=args.object_category,
            qualifiers=parse_qualifiers(args.qualifier or []),
            mode=args.mode,
            provider_ids=providers,
            result_limit=limit,
        )
        timeout = LOOKUP_TIMEOUT_SECONDS if args.mode == "lookup" else FEDERATED_TIMEOUT_SECONDS
    else:
        body = build_two_hop_query(
            subject_id=args.subject_id,
            subject_category=args.subject_category,
            predicates_1=args.predicate_1,
            intermediate_category=args.intermediate_category,
            predicates_2=args.predicate_2,
            object_id=args.object_id,
            object_category=args.object_category,
            qualifiers_1=parse_qualifiers(args.qualifier_1 or []),
            qualifiers_2=parse_qualifiers(args.qualifier_2 or []),
            mode=args.mode,
            provider_ids=providers,
            expand_order=args.expand_order,
            result_limit=limit,
        )
        timeout = LOOKUP_TIMEOUT_SECONDS if args.mode == "lookup" else FEDERATED_TIMEOUT_SECONDS
    return body, validate_saved_request_contract(body), timeout


def _validate_query_response_version(
    payload: Mapping[str, Any],
    allow_untested_version: bool,
    warnings: list[dict[str, Any]],
) -> None:
    try:
        _check_trapi_version(
            payload.get("schema_version") if isinstance(payload.get("schema_version"), str) else None,
            allow_untested_version,
            warnings,
        )
    except PreflightError:
        raise


def handle_graph_query(args: argparse.Namespace) -> int:
    body, contract, timeout = _build_from_args(args)
    request_bytes = serialize_request(body)
    base_url, endpoint_warnings = validate_base_url(args.base_url, args.allow_nonproduction_endpoint)
    output_dir = prepare_output_directory(args.output_dir)
    manifest = new_manifest(
        args.command,
        base_url=base_url,
        privacy_acknowledged=True,
        http_timeout=timeout,
        result_limit=contract.result_limit,
    )
    stage = "openapi"
    try:
        service, preflight_result = fetch_openapi(
            base_url,
            allow_untested_version=args.allow_untested_version,
            initial_warnings=endpoint_warnings,
        )
        _apply_service_to_manifest(manifest, service)
        manifest["attempts"]["openapi_get"] = preflight_result.attempts
        stage = "query"
        atomic_write_bytes(output_dir / "request.json", request_bytes)
        manifest["request"].update(
            {
                "method": "POST",
                "url": base_url + "/query",
                "file": "request.json",
                "bytes": len(request_bytes),
                "sha256": sha256_bytes(request_bytes),
            }
        )
        manifest["artifacts"]["request"] = "request.json"
        result = post_query(base_url + "/query", request_bytes, timeout=timeout)
        manifest["attempts"]["query_post"] = result.attempts
        atomic_write_bytes(output_dir / "response.json", result.body)
        _record_response(manifest, result)
        payload = _json_from_http(result, "TRAPI response")
        if not isinstance(payload, dict):
            raise ResponseError("TRAPI response is not an object")
        warnings = [dict(item) for item in service.warnings]
        _append_warning(warnings, "PUBLIC_QUERY", "The graph query was sent to a public service.")
        _validate_query_response_version(payload, args.allow_untested_version, warnings)
        summary = parse_trapi_response(payload, contract, service=service, initial_warnings=warnings)
        atomic_write_json(output_dir / "summary.json", summary)
        manifest["artifacts"]["summary"] = "summary.json"
        manifest["service"]["biolink_version"] = payload.get("biolink_version")
        manifest["warnings"] = summary["warnings"]
        manifest["execution_status"] = "success"
        if summary["completeness"] == "partial":
            manifest["result_status"] = "partial"
            exit_code = 7
        elif summary["counts"]["results_returned"] == 0:
            manifest["result_status"] = "no_results"
            exit_code = 0
        else:
            manifest["result_status"] = "results"
            exit_code = 0
        _write_manifest(output_dir, manifest)
        print(
            render_text_summary(
                summary,
                summary_path=str(output_dir / "summary.json"),
                response_path=str(output_dir / "response.json"),
            )
        )
        return exit_code
    except AraxClientError as exc:
        _retain_failure(output_dir, manifest, exc, stage)
        raise


def handle_summarize(args: argparse.Namespace) -> int:
    request_path = Path(args.request)
    response_path = Path(args.response)
    try:
        request_bytes = request_path.read_bytes()
        response_bytes = response_path.read_bytes()
    except OSError as exc:
        raise UsageError(f"could not read saved artifact: {_sanitize_text(exc)}") from exc
    if len(response_bytes) > MAX_RESPONSE_BYTES:
        raise ResponseError("saved response exceeded the 25 MiB byte limit")
    request_payload = _decode_json(request_bytes, "saved request")
    response_payload = _decode_json(response_bytes, "saved response")
    contract = validate_saved_request_contract(request_payload)
    warnings: list[dict[str, Any]] = []
    if isinstance(response_payload, dict):
        _validate_query_response_version(response_payload, False, warnings)
    summary = parse_trapi_response(
        response_payload,
        contract,
        service=None,
        initial_warnings=warnings,
    )
    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(
            render_text_summary(
                summary,
                summary_path="standard output with --format json",
                response_path=str(response_path),
            )
        )
    return 7 if summary["completeness"] == "partial" else 0


def _add_network_policy_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=PRODUCTION_BASE_URL)
    parser.add_argument("--allow-nonproduction-endpoint", action="store_true")
    parser.add_argument("--allow-untested-version", action="store_true")


def _add_query_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mode", choices=("lookup", "federated"), default="lookup")
    parser.add_argument("--kp", action="append", default=[])
    parser.add_argument("--result-limit", type=int)
    parser.add_argument("--acknowledge-public-query", action="store_true", required=True)
    parser.add_argument("--output-dir", required=True)
    _add_network_policy_options(parser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bounded NCATS Translator ARAX lookup and provenance inspection"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight", help="verify the ARAX OpenAPI and versions")
    preflight.add_argument("--output-dir")
    _add_network_policy_options(preflight)

    normalize = subparsers.add_parser("normalize", help="normalize one term or CURIE for review")
    normalize.add_argument("term")
    normalize.add_argument("--expected-category")
    normalize.add_argument("--max-synonyms", type=int, default=10)
    normalize.add_argument("--acknowledge-public-query", action="store_true", required=True)
    normalize.add_argument("--output-dir", required=True)
    _add_network_policy_options(normalize)

    one_hop = subparsers.add_parser("one-hop", help="run a typed one-hop lookup")
    one_hop.add_argument("--subject-id", action=RejectRepeatedValueAction)
    one_hop.add_argument("--subject-category", required=True)
    one_hop.add_argument("--predicate", action="append", required=True)
    one_hop.add_argument("--object-id", action=RejectRepeatedValueAction)
    one_hop.add_argument("--object-category", required=True)
    one_hop.add_argument("--qualifier", action="append", default=[])
    _add_query_common(one_hop)

    two_hop = subparsers.add_parser("two-hop", help="run an endpoint-pinned two-hop lookup")
    two_hop.add_argument("--subject-id", required=True, action=RejectRepeatedValueAction)
    two_hop.add_argument("--subject-category", required=True)
    two_hop.add_argument("--predicate-1", action="append", required=True)
    two_hop.add_argument("--intermediate-category", required=True)
    two_hop.add_argument("--predicate-2", action="append", required=True)
    two_hop.add_argument("--object-id", required=True, action=RejectRepeatedValueAction)
    two_hop.add_argument("--object-category", required=True)
    two_hop.add_argument("--qualifier-1", action="append", default=[])
    two_hop.add_argument("--qualifier-2", action="append", default=[])
    two_hop.add_argument(
        "--expand-order", choices=("right-first", "left-first"), default="right-first"
    )
    _add_query_common(two_hop)

    summarize = subparsers.add_parser("summarize", help="inspect a saved supported ARAX response")
    summarize.add_argument("--request", required=True)
    summarize.add_argument("--response", required=True)
    summarize.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            return handle_preflight(args)
        if args.command == "normalize":
            return handle_normalize(args)
        if args.command in {"one-hop", "two-hop"}:
            return handle_graph_query(args)
        if args.command == "summarize":
            return handle_summarize(args)
        raise UsageError(f"unsupported command: {args.command}")
    except AraxClientError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
