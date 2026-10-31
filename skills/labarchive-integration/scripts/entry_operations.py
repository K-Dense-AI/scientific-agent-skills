#!/usr/bin/env python3
"""Offline LabArchives request-signing helpers and redacted request plans.

The CLI performs no network requests and never prints credentials or reusable
signatures. Import the functions into institution-reviewed HTTP code when
needed, and pass returned authentication material directly to the client.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import json
import os
import re
import sys
import time
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote

from setup_config import (
    ENV_ACCESS_KEY_ID,
    ENV_ACCESS_PASSWORD,
    ENV_API_URL,
    ENV_INVENTORY_LAB_ID,
    ENV_USER_ID,
    INVENTORY_API_BASE_URL,
    ConfigError,
    normalize_eln_api_url,
)


_ELN_COMPONENT = re.compile(r"^[a-z][a-z0-9_]*$")
_INVENTORY_PATH = re.compile(r"^/public/v1/[A-Za-z0-9._~!$&'()*+,;=:@/-]+$")
_OFFICIAL_VECTOR = {
    "access_key_id": "0234wedkfjrtfd34er",
    "api_method_input": "entry_attachment",
    "expires_ms": 264433207000,
    "access_password": "1234567890",
    "signature": (
        "mT7pS+KgqlNseR0bo4YLQOVIsgOugMWzlQGllInXS25Q7VpA6lRmL0nUq/"
        "UUdrlF+WV7POYE1vcwvN/pnac7bw=="
    ),
}


def _require_text(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ConfigError(f"{label} must not be empty")
    return normalized


def _require_secret(value: str, label: str) -> str:
    if not value:
        raise ConfigError(f"{label} must not be empty")
    return value


def _expires_ms(value: int | None = None) -> int:
    selected = time.time_ns() // 1_000_000 if value is None else value
    if selected < 0:
        raise ConfigError("expires must be a non-negative epoch-millisecond value")
    return selected


def create_signature(
    access_key_id: str,
    api_method_input: str,
    expires_ms: int,
    access_password: str,
) -> str:
    """Create the documented Base64(HMAC-SHA-512) LabArchives signature.

    No separators are inserted. The result is not URI-encoded.
    """

    key_id = _require_text(access_key_id, "Access Key ID")
    method_input = _require_text(api_method_input, "API method input")
    secret = _require_secret(access_password, "Access Password")
    expires = _expires_ms(expires_ms)
    message = f"{key_id}{method_input}{expires}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha512).digest()
    return base64.b64encode(digest).decode("ascii")


def encode_eln_signature(signature: str) -> str:
    """URI-encode a Base64 signature for an ELN sig query parameter."""

    return quote(_require_text(signature, "signature"), safe="")


def build_eln_auth_params(
    access_key_id: str,
    access_password: str,
    api_method: str,
    expires_ms: int | None = None,
) -> dict[str, str]:
    """Return ELN query authentication parameters.

    Keep the returned mapping out of logs. A normal query encoder will
    URI-encode the Base64 signature.
    """

    method = validate_eln_component(api_method, "ELN API method")
    expires = _expires_ms(expires_ms)
    signature = create_signature(access_key_id, method, expires, access_password)
    return {
        "akid": _require_text(access_key_id, "Access Key ID"),
        "expires": str(expires),
        "sig": signature,
    }


def build_inventory_headers(
    access_key_id: str,
    access_password: str,
    user_id: str,
    lab_id: str | None,
    relative_path: str,
    expires_ms: int | None = None,
) -> dict[str, str]:
    """Return documented Inventory v1 authentication headers.

    The relative path includes resolved route parameters and excludes any query
    string. The users/me bootstrap route does not require a Lab ID; pass None
    or an empty string there to omit that header. Other routes require a Lab ID.
    Keep the returned mapping out of logs.
    """

    path = validate_inventory_path(relative_path)
    expires = _expires_ms(expires_ms)
    signature = create_signature(access_key_id, path, expires, access_password)
    headers = {
        "X-LabArchives-UId": _require_text(user_id, "Inventory user ID"),
        "X-LabArchives-AKId": _require_text(access_key_id, "Access Key ID"),
        "X-LabArchives-Signature": signature,
        "X-LabArchives-Expires": str(expires),
    }
    if path != "/public/v1/users/me" or (lab_id and lab_id.strip()):
        headers["X-LabArchives-LabId"] = _require_text(lab_id or "", "Inventory Lab ID")
    return headers


def validate_eln_component(value: str, label: str) -> str:
    """Validate a class or method copied from the official ELN API tree."""

    normalized = value.strip()
    if not _ELN_COMPONENT.fullmatch(normalized):
        raise ConfigError(
            f"{label} must match {_ELN_COMPONENT.pattern!r}; "
            "copy it from the current official method page"
        )
    return normalized


def validate_inventory_path(value: str) -> str:
    """Validate an exact, resolved Inventory v1 relative route."""

    path = value.strip()
    if "?" in path or "#" in path:
        raise ConfigError(
            "Inventory signature path must exclude query strings and fragments"
        )
    if "\\" in path or "%" in path or any(character.isspace() for character in path):
        raise ConfigError(
            "Inventory signature path must be an unencoded relative route"
        )
    if "{" in path or "}" in path:
        raise ConfigError("resolve all Inventory route placeholders before signing")
    if not _INVENTORY_PATH.fullmatch(path):
        raise ConfigError(
            "Inventory path must be an exact route beginning with /public/v1/"
        )
    segments = path.split("/")
    if any(segment in {".", ".."} for segment in segments) or "//" in path:
        raise ConfigError("Inventory path contains an unsafe or ambiguous segment")
    return path


def _secret_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _dump(payload: Mapping[str, Any], *, compact: bool, stream: Any) -> None:
    if compact:
        json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
    else:
        json.dump(payload, stream, indent=2, sort_keys=True)
    stream.write("\n")


def _load_credentials(
    args: argparse.Namespace, env: Mapping[str, str]
) -> tuple[str, str]:
    access_key_id = env.get(ENV_ACCESS_KEY_ID, "").strip()
    if not access_key_id:
        raise ConfigError(
            f"required environment variable is missing: {ENV_ACCESS_KEY_ID}"
        )

    access_password = env.get(ENV_ACCESS_PASSWORD, "")
    if not access_password and args.prompt_missing_secret:
        access_password = getpass.getpass(f"{ENV_ACCESS_PASSWORD}: ")
    if not access_password:
        raise ConfigError(
            f"required environment variable is missing: {ENV_ACCESS_PASSWORD}"
        )
    return access_key_id, access_password


def command_self_test(args: argparse.Namespace) -> int:
    actual = create_signature(
        _OFFICIAL_VECTOR["access_key_id"],
        _OFFICIAL_VECTOR["api_method_input"],
        int(_OFFICIAL_VECTOR["expires_ms"]),
        _OFFICIAL_VECTOR["access_password"],
    )
    passed = hmac.compare_digest(actual, str(_OFFICIAL_VECTOR["signature"]))
    payload = {
        "passed": passed,
        "source": "official LabArchives Call Authentication example",
        "signature_fingerprint": _secret_fingerprint(actual),
        "credentials_used": "public dummy test vector only",
        "remote_request_performed": False,
    }
    _dump(payload, compact=args.compact, stream=sys.stdout)
    return 0 if passed else 1


def command_eln_plan(
    args: argparse.Namespace, env: Mapping[str, str] | None = None
) -> int:
    selected_env = os.environ if env is None else env
    access_key_id, access_password = _load_credentials(args, selected_env)
    api_class = validate_eln_component(args.api_class, "ELN API class")
    api_method = validate_eln_component(args.api_method, "ELN API method")
    api_url = normalize_eln_api_url(args.api_url or selected_env.get(ENV_API_URL, ""))
    auth = build_eln_auth_params(
        access_key_id,
        access_password,
        api_method,
        expires_ms=args.expires_ms,
    )
    payload = {
        "dry_run": True,
        "remote_request_performed": False,
        "api_surface": "legacy ELN",
        "endpoint_without_query": f"{api_url}/{api_class}/{api_method}",
        "signature_input": api_method,
        "expires_ms": int(auth["expires"]),
        "authentication_parameter_names": sorted(auth),
        "access_key_id_fingerprint": _secret_fingerprint(access_key_id),
        "signature_fingerprint": _secret_fingerprint(auth["sig"]),
        "reusable_authentication_material_printed": False,
        "warning": (
            "Verify the exact official method page, HTTP verb, and parameters "
            "before implementing a request."
        ),
    }
    _dump(payload, compact=args.compact, stream=sys.stdout)
    return 0


def command_inventory_plan(
    args: argparse.Namespace, env: Mapping[str, str] | None = None
) -> int:
    selected_env = os.environ if env is None else env
    access_key_id, access_password = _load_credentials(args, selected_env)
    user_id = selected_env.get(ENV_USER_ID, "")
    lab_id = selected_env.get(ENV_INVENTORY_LAB_ID, "")
    headers = build_inventory_headers(
        access_key_id,
        access_password,
        user_id,
        lab_id,
        args.path,
        expires_ms=args.expires_ms,
    )
    payload = {
        "dry_run": True,
        "remote_request_performed": False,
        "api_surface": "Inventory API v1",
        "relative_path": validate_inventory_path(args.path),
        "absolute_base_url": INVENTORY_API_BASE_URL,
        "expires_ms": int(headers["X-LabArchives-Expires"]),
        "authentication_header_names": sorted(headers),
        "access_key_id_fingerprint": _secret_fingerprint(access_key_id),
        "signature_fingerprint": _secret_fingerprint(
            headers["X-LabArchives-Signature"]
        ),
        "reusable_authentication_material_printed": False,
        "warning": (
            "The Inventory overview documents this base URL. Confirm the account "
            "deployment before a live request; do not infer regional variants."
        ),
    }
    _dump(payload, compact=args.compact, stream=sys.stdout)
    return 0


def _add_plan_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--expires-ms",
        type=int,
        help=(
            "explicit current epoch milliseconds for deterministic validation; "
            "defaults to the local current time"
        ),
    )
    parser.add_argument(
        "--prompt-missing-secret",
        action="store_true",
        help="use getpass for a missing Access Password without saving it",
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate redacted, offline LabArchives signing plans. "
            "No HTTP requests are implemented."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    self_test = subparsers.add_parser(
        "self-test", help="check HMAC implementation against the official vector"
    )
    self_test.add_argument("--compact", action="store_true", help="emit compact JSON")
    self_test.set_defaults(handler=command_self_test)

    eln = subparsers.add_parser(
        "eln-plan", help="create a redacted legacy ELN request-signing plan"
    )
    eln.add_argument(
        "--api-url",
        help=f"allowlisted ELN API URL; otherwise read {ENV_API_URL}",
    )
    eln.add_argument("--api-class", required=True, help="official ELN API class")
    eln.add_argument("--api-method", required=True, help="official ELN API method")
    _add_plan_options(eln)
    eln.set_defaults(handler=command_eln_plan)

    inventory = subparsers.add_parser(
        "inventory-plan",
        help="create a redacted Inventory v1 request-signing plan",
    )
    inventory.add_argument(
        "--path",
        required=True,
        help="exact /public/v1/... route with path values resolved and no query",
    )
    _add_plan_options(inventory)
    inventory.set_defaults(handler=command_inventory_plan)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except ConfigError as exc:
        _dump(
            {
                "valid": False,
                "error": str(exc),
                "remote_request_performed": False,
            },
            compact=getattr(args, "compact", False),
            stream=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        print('{"valid":false,"error":"cancelled"}', file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
