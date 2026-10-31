"""Shared safety primitives for the protocols.io helper scripts.

The helpers use only the Python standard library. They never load ``.env``
files, never accept credentials as command-line arguments, and never follow
HTTP redirects.
"""

from __future__ import annotations

import json
import math
import os
import re
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, MutableMapping, Sequence


DEFAULT_ORIGIN = "https://www.protocols.io"
ACCESS_TOKEN_ENV = "PROTOCOLS_IO_ACCESS_TOKEN"
CREDENTIAL_ENV_NAMES = (ACCESS_TOKEN_ENV,)

MAX_LOCAL_JSON_BYTES = 2_000_000
MAX_JSON_RESPONSE_BYTES = 4_000_000
MAX_PDF_RESPONSE_BYTES = 25_000_000
MAX_ERROR_BYTES = 64_000
MAX_RETRIES = 2
MAX_RETRY_AFTER_SECONDS = 30.0
MIN_TIMEOUT_SECONDS = 1.0
MAX_TIMEOUT_SECONDS = 60.0
DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_REMOTE_STRING_CHARS = 4_000
MAX_REMOTE_COLLECTION_ITEMS = 500
MAX_REMOTE_DEPTH = 12

_CORE_HOSTS = frozenset({"protocols.io", "www.protocols.io"})
_TENANT_HOST_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.protocols\.io$")
_PROTOCOL_ID_RE = re.compile(
    r"^(?:10\.17504/protocols\.io\.[A-Za-z0-9][A-Za-z0-9._-]{0,240}|"
    r"[1-9][0-9]*|[A-Za-z0-9][A-Za-z0-9._-]{0,254})"
    r"(?:/(?:v[1-9][0-9]*|latest))?$"
)
_GUID_RE = re.compile(r"^[A-Fa-f0-9]{32}$")
_INTEGER_RE = re.compile(r"^(?:0|[1-9][0-9]*)$")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "credential",
    "password",
    "secret",
    "signature",
    "access_token",
    "refresh_token",
    "awsaccesskey",
    "policy",
)


class SafetyError(ValueError):
    """A local, user-correctable safety or validation failure."""


class ApiError(RuntimeError):
    """A bounded API failure that deliberately excludes credentials and bodies."""

    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        api_status: int | str | None = None,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.api_status = api_status


@dataclass(frozen=True)
class HttpResult:
    """A bounded HTTP response."""

    status: int
    headers: Mapping[str, str]
    body: bytes
    url: str
    attempts: int


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject every redirect so credentials cannot cross origins."""

    def redirect_request(  # type: ignore[override]
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Mapping[str, str],
        newurl: str,
    ) -> None:
        del req, fp, code, msg, headers, newurl
        return None


def _reject_constant(value: str) -> None:
    raise SafetyError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SafetyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_bytes(raw: bytes, *, source: str = "response") -> Any:
    """Parse strict UTF-8 JSON with duplicate-key and NaN rejection."""

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SafetyError(f"{source} is not UTF-8 JSON") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise SafetyError(
            f"invalid JSON in {source} at line {exc.lineno}, column {exc.colno}"
        ) from exc


def _path_inside_cwd(raw_path: str, *, must_exist: bool) -> Path:
    base = Path.cwd().resolve()
    candidate = Path(raw_path)
    unresolved = candidate if candidate.is_absolute() else base / candidate
    try:
        relative = unresolved.relative_to(base)
    except ValueError as exc:
        raise SafetyError(
            "path must stay inside the current working directory"
        ) from exc
    if ".." in relative.parts:
        raise SafetyError("parent-directory traversal is forbidden")

    cursor = base
    parts = relative.parts[:-1] if not must_exist else relative.parts
    for part in parts:
        cursor /= part
        if cursor.is_symlink():
            raise SafetyError(f"symlink paths are forbidden: {raw_path}")

    resolved = unresolved.resolve(strict=False)
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise SafetyError("resolved path escapes the working directory") from exc
    return resolved


def safe_input_path(
    raw_path: str,
    *,
    suffixes: Sequence[str],
    max_bytes: int,
) -> Path:
    """Return a bounded, regular, non-symlink input path under the CWD."""

    path = _path_inside_cwd(raw_path, must_exist=True)
    if path.is_symlink() or not path.exists() or not path.is_file():
        raise SafetyError(f"input is not a regular non-symlink file: {raw_path}")
    if suffixes and path.suffix.lower() not in {suffix.lower() for suffix in suffixes}:
        raise SafetyError("input suffix must be one of: " + ", ".join(sorted(suffixes)))
    size = path.stat().st_size
    if size > max_bytes:
        raise SafetyError(f"input exceeds the local safety cap of {max_bytes} bytes")
    return path


def load_local_json(
    raw_path: str,
    *,
    max_bytes: int = MAX_LOCAL_JSON_BYTES,
) -> Any:
    path = safe_input_path(raw_path, suffixes=(".json",), max_bytes=max_bytes)
    return parse_json_bytes(path.read_bytes(), source=str(path))


def safe_output_path(raw_path: str, *, suffix: str) -> Path:
    """Validate a new output path below the CWD without creating it."""

    path = _path_inside_cwd(raw_path, must_exist=False)
    if path.suffix.lower() != suffix.lower():
        raise SafetyError(f"output must have a {suffix} suffix")
    parent = path.parent
    if not parent.exists() or not parent.is_dir() or parent.is_symlink():
        raise SafetyError("output parent must be an existing non-symlink directory")
    if path.exists() or path.is_symlink():
        raise SafetyError("refusing to overwrite an existing output path")
    return path


def write_private_bytes(path: Path, data: bytes) -> None:
    """Create a private output file atomically with collision protection."""

    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        stat.S_IRUSR | stat.S_IWUSR,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def clean_text(value: str, *, max_chars: int = MAX_REMOTE_STRING_CHARS) -> str:
    """Remove control characters and bound untrusted text."""

    cleaned = _CONTROL_RE.sub("\ufffd", value)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars] + f"\u2026[truncated {len(cleaned) - max_chars} chars]"


def _sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def sanitize_untrusted(
    value: Any,
    *,
    depth: int = 0,
    max_string_chars: int = MAX_REMOTE_STRING_CHARS,
    max_items: int = MAX_REMOTE_COLLECTION_ITEMS,
) -> Any:
    """Redact secrets and bound arbitrary remote or user-provided structures."""

    if depth > MAX_REMOTE_DEPTH:
        return {"truncated": "maximum nesting depth reached"}
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else "[NON_FINITE_REDACTED]"
    if isinstance(value, str):
        return clean_text(value, max_chars=max_string_chars)
    if isinstance(value, Mapping):
        result: MutableMapping[str, Any] = {}
        entries = list(value.items())
        for key, item in entries[:max_items]:
            text_key = clean_text(str(key), max_chars=256)
            if _sensitive_key(text_key):
                result[text_key] = "[REDACTED]"
            else:
                result[text_key] = sanitize_untrusted(
                    item,
                    depth=depth + 1,
                    max_string_chars=max_string_chars,
                    max_items=max_items,
                )
        if len(entries) > max_items:
            result["_truncated_items"] = len(entries) - max_items
        return dict(result)
    if isinstance(value, (list, tuple)):
        result = [
            sanitize_untrusted(
                item,
                depth=depth + 1,
                max_string_chars=max_string_chars,
                max_items=max_items,
            )
            for item in value[:max_items]
        ]
        if len(value) > max_items:
            result.append({"_truncated_items": len(value) - max_items})
        return result
    return clean_text(repr(value), max_chars=max_string_chars)


def emit_json(payload: Any, *, stream: Any = None) -> None:
    if stream is None:
        import sys

        stream = sys.stdout
    print(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False),
        file=stream,
    )


def emit_error(error: Exception) -> int:
    import sys

    payload: dict[str, Any] = {
        "ok": False,
        "error": type(error).__name__,
        "message": clean_text(str(error), max_chars=500),
    }
    if isinstance(error, ApiError):
        payload["http_status"] = error.http_status
        payload["api_status"] = error.api_status
    emit_json(payload, stream=sys.stderr)
    return 2


def validate_timeout(value: float) -> float:
    if (
        not math.isfinite(value)
        or not MIN_TIMEOUT_SECONDS <= value <= MAX_TIMEOUT_SECONDS
    ):
        raise SafetyError(
            f"timeout must be between {MIN_TIMEOUT_SECONDS:g} and "
            f"{MAX_TIMEOUT_SECONDS:g} seconds"
        )
    return value


def validate_retries(value: int) -> int:
    if isinstance(value, bool) or not 0 <= value <= MAX_RETRIES:
        raise SafetyError(f"retries must be between 0 and {MAX_RETRIES}")
    return value


def is_official_host(host: str, *, allow_tenant: bool = False) -> bool:
    normalized = host.rstrip(".").lower()
    if normalized in _CORE_HOSTS:
        return True
    return allow_tenant and _TENANT_HOST_RE.fullmatch(normalized) is not None


def validate_origin(raw_origin: str, *, allow_tenant: bool = False) -> str:
    parsed = urllib.parse.urlsplit(raw_origin)
    try:
        port = parsed.port
    except ValueError as exc:
        raise SafetyError("origin contains an invalid port") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise SafetyError(
            "origin must be an HTTPS protocols.io origin without credentials, "
            "path, query, fragment, or non-default port"
        )
    if not is_official_host(parsed.hostname, allow_tenant=allow_tenant):
        raise SafetyError("origin host is not on the official protocols.io allowlist")
    return f"https://{parsed.hostname.lower()}"


def validate_remote_url(
    raw_url: str,
    *,
    allow_tenant: bool = False,
    allowed_paths: Sequence[str] = ("/api/", "/view/"),
) -> str:
    parsed = urllib.parse.urlsplit(raw_url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise SafetyError("URL contains an invalid port") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.fragment
    ):
        raise SafetyError("remote URL must be credential-free HTTPS on port 443")
    if not is_official_host(parsed.hostname, allow_tenant=allow_tenant):
        raise SafetyError("remote host is not on the official protocols.io allowlist")
    if not any(parsed.path.startswith(prefix) for prefix in allowed_paths):
        raise SafetyError("remote URL path is outside the allowlisted API/export paths")
    return urllib.parse.urlunsplit(
        ("https", parsed.hostname.lower(), parsed.path, parsed.query, "")
    )


def build_url(
    origin: str,
    path: str,
    params: Mapping[str, Any] | None = None,
) -> str:
    normalized_origin = validate_origin(origin, allow_tenant=True)
    if not path.startswith("/") or "\\" in path or "\x00" in path:
        raise SafetyError("request path must be an absolute URL path")
    query = urllib.parse.urlencode(params or {}, doseq=True)
    return urllib.parse.urlunsplit(
        ("https", urllib.parse.urlsplit(normalized_origin).netloc, path, query, "")
    )


def validate_protocol_identifier(value: str) -> str:
    if _PROTOCOL_ID_RE.fullmatch(value) is None:
        raise SafetyError(
            "protocol identifier must be an integer, URI, or DOI with an optional "
            "/vN or /latest suffix"
        )
    return value


def encode_protocol_identifier(value: str) -> str:
    validated = validate_protocol_identifier(value)
    return "/".join(
        urllib.parse.quote(part, safe="._-") for part in validated.split("/")
    )


def validate_guid(value: str) -> str:
    if _GUID_RE.fullmatch(value) is None:
        raise SafetyError("GUID must contain exactly 32 hexadecimal characters")
    return value.upper()


def validate_nonnegative_integer(value: str, *, name: str, maximum: int) -> int:
    if _INTEGER_RE.fullmatch(value) is None:
        raise SafetyError(f"{name} must be an unsigned base-10 integer")
    parsed = int(value)
    if parsed > maximum:
        raise SafetyError(f"{name} must not exceed {maximum}")
    return parsed


def credential_status(
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return presence-only credential status without exposing values."""

    environment = os.environ if environ is None else environ
    present = {name: bool(environment.get(name)) for name in CREDENTIAL_ENV_NAMES}
    return {
        "named_variables_only": True,
        "dotenv_loaded": False,
        "variables": {
            name: {"present": is_present} for name, is_present in present.items()
        },
        "rest_bearer_ready": present[ACCESS_TOKEN_ENV],
        "oauth_credentials_consumed": False,
    }


def _bounded_read(response: Any, max_bytes: int) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            declared = int(content_length)
        except (TypeError, ValueError):
            declared = -1
        if declared > max_bytes:
            raise SafetyError(
                f"response Content-Length exceeds the {max_bytes}-byte safety cap"
            )

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(min(65_536, max_bytes - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise SafetyError(f"response exceeds the {max_bytes}-byte safety cap")
        chunks.append(chunk)
    return b"".join(chunks)


def _retry_delay(headers: Mapping[str, str], attempt: int) -> float:
    raw = headers.get("Retry-After")
    if raw is not None:
        try:
            seconds = float(raw)
        except (TypeError, ValueError):
            seconds = 0.0
        if math.isfinite(seconds) and seconds > 0:
            return min(seconds, MAX_RETRY_AFTER_SECONDS)
    return min(float(2**attempt), MAX_RETRY_AFTER_SECONDS)


def _api_error_from_body(status: int, body: bytes) -> ApiError:
    api_status: int | str | None = None
    if body:
        try:
            payload = parse_json_bytes(body, source="error response")
        except SafetyError:
            payload = None
        if isinstance(payload, Mapping):
            api_status = payload.get("status_code")
    message = f"protocols.io returned HTTP {status}"
    if api_status is not None:
        message += f" with API status {api_status}"
    return ApiError(message, http_status=status, api_status=api_status)


def request_bytes(
    url: str,
    *,
    token: str | None,
    accept: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    retries: int = 1,
    max_bytes: int = MAX_JSON_RESPONSE_BYTES,
    opener: Any | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> HttpResult:
    """Perform one bounded GET request to an allowlisted URL.

    Only idempotent GET requests are supported. Redirects are rejected. Retries
    are bounded and limited to 429/500/502/503/504 responses.
    """

    safe_url = validate_remote_url(url, allow_tenant=True)
    timeout = validate_timeout(timeout)
    retries = validate_retries(retries)
    if max_bytes < 1 or max_bytes > MAX_PDF_RESPONSE_BYTES:
        raise SafetyError(f"max_bytes must be between 1 and {MAX_PDF_RESPONSE_BYTES}")
    if token is not None and (
        not token
        or any(character.isspace() or ord(character) < 32 for character in token)
        or "\x7f" in token
    ):
        raise SafetyError("access token is empty or contains forbidden characters")

    request_headers = {
        "Accept": accept,
        "User-Agent": "scientific-agent-skills/protocolsio-integration-1.4",
    }
    if token is not None:
        request_headers["Authorization"] = f"Bearer {token}"

    transport = opener or urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        NoRedirectHandler(),
    )
    retryable = {429, 500, 502, 503, 504}
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            safe_url,
            headers=request_headers,
            method="GET",
        )
        try:
            with transport.open(request, timeout=timeout) as response:
                raw_status = getattr(response, "status", None)
                if raw_status is None:
                    raw_status = response.getcode()
                status = int(raw_status)
                body = _bounded_read(response, max_bytes)
                headers = {
                    str(key): str(value) for key, value in response.headers.items()
                }
                final_url = validate_remote_url(
                    str(getattr(response, "url", safe_url)),
                    allow_tenant=True,
                )
                if status >= 400:
                    raise _api_error_from_body(status, body[:MAX_ERROR_BYTES])
                return HttpResult(
                    status=status,
                    headers=headers,
                    body=body,
                    url=final_url,
                    attempts=attempt + 1,
                )
        except urllib.error.HTTPError as exc:
            headers = {str(key): str(value) for key, value in exc.headers.items()}
            if exc.code in retryable and attempt < retries:
                sleep(_retry_delay(headers, attempt))
                continue
            try:
                body = _bounded_read(exc, MAX_ERROR_BYTES)
            except SafetyError:
                body = b""
            raise _api_error_from_body(exc.code, body) from None
        except urllib.error.URLError as exc:
            if attempt < retries:
                sleep(min(float(2**attempt), MAX_RETRY_AFTER_SECONDS))
                continue
            reason = clean_text(str(exc.reason), max_chars=200)
            raise ApiError(f"network request failed: {reason}") from None

    raise ApiError("bounded request attempts were exhausted")


def require_api_success(payload: Any) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise ApiError("protocols.io returned a non-object JSON response")
    status = payload.get("status_code", 0)
    if status not in (0, "0", None):
        raise ApiError(
            f"protocols.io returned API status {status}",
            api_status=status,
        )
    return payload
