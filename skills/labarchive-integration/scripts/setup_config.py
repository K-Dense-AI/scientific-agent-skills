#!/usr/bin/env python3
"""Validate LabArchives regional endpoints and named environment variables.

This utility never reads .env files, writes configuration, authenticates, or
prints credential values.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit


REGIONS: dict[str, dict[str, str]] = {
    "us": {
        "label": "US and rest of world",
        "login_url": "https://mynotebook.labarchives.com",
        "eln_api_url": "https://api.labarchives.com/api",
    },
    "ca": {
        "label": "Canada",
        "login_url": "https://ca-mynotebook.labarchives.com",
        "eln_api_url": "https://caapi.labarchives.com/api",
    },
    "au": {
        "label": "Australia and New Zealand",
        "login_url": "https://au-mynotebook.labarchives.com",
        "eln_api_url": "https://auapi.labarchives.com/api",
    },
    "uk": {
        "label": "United Kingdom",
        "login_url": "https://uk-mynotebook.labarchives.com",
        "eln_api_url": "https://ukapi.labarchives.com/api",
    },
    "eu": {
        "label": "Europe outside the UK",
        "login_url": "https://eu-mynotebook.labarchives.com",
        "eln_api_url": "https://euapi.labarchives.com/api",
    },
}

INVENTORY_API_BASE_URL = "https://iapi.labarchives.com"

ENV_API_URL = "LABARCHIVES_ELN_API_URL"
ENV_ACCESS_KEY_ID = "LABARCHIVES_ACCESS_KEY_ID"
ENV_ACCESS_PASSWORD = "LABARCHIVES_ACCESS_PASSWORD"
ENV_USER_ID = "LABARCHIVES_USER_ID"
ENV_INVENTORY_LAB_ID = "LABARCHIVES_INVENTORY_LAB_ID"

_API_URL_TO_REGION = {
    values["eln_api_url"]: region for region, values in REGIONS.items()
}


class ConfigError(ValueError):
    """Raised when local LabArchives configuration is invalid."""


def normalize_eln_api_url(value: str) -> str:
    """Return an allowlisted ELN API URL or raise ConfigError."""

    candidate = value.strip()
    if not candidate:
        raise ConfigError("ELN API URL is empty")

    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError as exc:
        raise ConfigError(f"invalid ELN API URL: {exc}") from exc

    if parsed.scheme.lower() != "https":
        raise ConfigError("ELN API URL must use https")
    if parsed.username is not None or parsed.password is not None:
        raise ConfigError("credentials must not be embedded in the ELN API URL")
    if port is not None:
        raise ConfigError("ELN API URL must not specify a custom port")
    if parsed.query or parsed.fragment:
        raise ConfigError("ELN API URL must not contain a query or fragment")
    if parsed.path not in {"/api", "/api/"}:
        raise ConfigError("ELN API URL path must be exactly /api")

    host = (parsed.hostname or "").lower()
    normalized = f"https://{host}/api"
    if normalized not in _API_URL_TO_REGION:
        allowed = ", ".join(sorted(_API_URL_TO_REGION))
        raise ConfigError(f"ELN API URL is not allowlisted; expected one of: {allowed}")
    return normalized


def _present(env: Mapping[str, str], name: str) -> bool:
    return bool(env.get(name, "").strip())


def _dump(payload: Mapping[str, Any], *, compact: bool, stream: Any) -> None:
    if compact:
        json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
    else:
        json.dump(payload, stream, indent=2, sort_keys=True)
    stream.write("\n")


def _select_api_url(args: argparse.Namespace, env: Mapping[str, str]) -> str:
    if args.api_url and args.region:
        raise ConfigError("use either --api-url or --region, not both")
    if args.api_url:
        return normalize_eln_api_url(args.api_url)
    if args.region:
        return REGIONS[args.region]["eln_api_url"]

    from_env = env.get(ENV_API_URL, "")
    if not from_env.strip():
        raise ConfigError(f"set {ENV_API_URL}, or pass a non-secret --region/--api-url")
    return normalize_eln_api_url(from_env)


def command_regions(args: argparse.Namespace) -> int:
    payload = {
        "as_of": "2026-09-30",
        "inventory_documented_api_base_url": INVENTORY_API_BASE_URL,
        "regions": [
            {"code": code, **values} for code, values in sorted(REGIONS.items())
        ],
        "warning": (
            "Browser login URLs and ELN API URLs are different. "
            "Inventory has a separately documented API base; "
            "regional variants are not inferred."
        ),
    }
    _dump(payload, compact=args.compact, stream=sys.stdout)
    return 0


def command_check(
    args: argparse.Namespace, env: Mapping[str, str] | None = None
) -> int:
    selected_env = os.environ if env is None else env
    api_url = _select_api_url(args, selected_env)

    access_password_present = _present(selected_env, ENV_ACCESS_PASSWORD)
    prompted_in_memory = False
    if not access_password_present and args.prompt_missing_secret:
        prompted = getpass.getpass(
            f"{ENV_ACCESS_PASSWORD} (validated in memory; not saved): "
        )
        access_password_present = bool(prompted)
        prompted_in_memory = access_password_present
        prompted = ""

    status = {
        ENV_ACCESS_KEY_ID: _present(selected_env, ENV_ACCESS_KEY_ID),
        ENV_ACCESS_PASSWORD: access_password_present,
        ENV_USER_ID: _present(selected_env, ENV_USER_ID),
        ENV_INVENTORY_LAB_ID: _present(selected_env, ENV_INVENTORY_LAB_ID),
    }

    required = [ENV_ACCESS_KEY_ID, ENV_ACCESS_PASSWORD]
    if args.require_user_id:
        required.append(ENV_USER_ID)
    if args.require_inventory_lab_id:
        required.append(ENV_INVENTORY_LAB_ID)
    missing = [name for name in required if not status[name]]

    payload = {
        "valid": not missing,
        "region": _API_URL_TO_REGION[api_url],
        "eln_api_url": api_url,
        "credential_presence": status,
        "required_variables": required,
        "missing_variables": missing,
        "prompted_secret_kept_in_memory_only": prompted_in_memory,
        "dotenv_files_read": False,
        "remote_request_performed": False,
    }
    _dump(payload, compact=args.compact, stream=sys.stdout)
    return 0 if not missing else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate official LabArchives ELN regional URLs and the presence "
            "of named environment variables without printing secrets."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    regions_parser = subparsers.add_parser(
        "regions", help="print documented browser and ELN API regional URLs"
    )
    regions_parser.add_argument(
        "--compact", action="store_true", help="emit compact JSON"
    )
    regions_parser.set_defaults(handler=command_regions)

    check_parser = subparsers.add_parser(
        "check", help="validate endpoint selection and credential presence"
    )
    endpoint_group = check_parser.add_mutually_exclusive_group()
    endpoint_group.add_argument(
        "--region",
        choices=sorted(REGIONS),
        help=f"select a documented region instead of reading {ENV_API_URL}",
    )
    endpoint_group.add_argument(
        "--api-url",
        help="validate a non-secret ELN API URL against the official allowlist",
    )
    check_parser.add_argument(
        "--require-user-id",
        action="store_true",
        help=f"require {ENV_USER_ID} to be present",
    )
    check_parser.add_argument(
        "--require-inventory-lab-id",
        action="store_true",
        help=f"require {ENV_INVENTORY_LAB_ID} to be present",
    )
    check_parser.add_argument(
        "--prompt-missing-secret",
        action="store_true",
        help=(
            "use getpass for a missing Access Password; validate presence in "
            "memory only and do not save it"
        ),
    )
    check_parser.add_argument(
        "--compact", action="store_true", help="emit compact JSON"
    )
    check_parser.set_defaults(handler=command_check)
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
