#!/usr/bin/env python3
"""Validate named OMERO endpoint/auth variables without contacting OMERO."""

from __future__ import annotations

import argparse
import json
import socket
import sys
from typing import Any

from omero_common import (
    ConfigError,
    config_summary,
    load_connection_config,
    scrubbed_error,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate only named OMERO_* variables locally. By default this "
            "does not resolve DNS and never contacts an OMERO server."
        )
    )
    parser.add_argument(
        "--require-auth",
        action="store_true",
        help=(
            "Require OMERO_SESSION_KEY or both OMERO_USER and "
            "OMERO_PASSWORD."
        ),
    )
    parser.add_argument(
        "--resolve-host",
        action="store_true",
        help=(
            "Resolve OMERO_HOST through DNS without opening an OMERO "
            "connection."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a concise text summary.",
    )
    return parser


def resolve_host(host: str, port: int, *, limit: int = 10) -> list[str]:
    """Resolve a bounded set of unique numeric addresses."""

    addresses: list[str] = []
    seen: set[str] = set()
    for result in socket.getaddrinfo(
        host,
        port,
        type=socket.SOCK_STREAM,
    ):
        address = result[4][0]
        if address not in seen:
            seen.add(address)
            addresses.append(address)
        if len(addresses) >= limit:
            break
    return addresses


def format_text(payload: dict[str, Any]) -> str:
    endpoint = payload["endpoint"]
    lines = [
        "OMERO configuration is valid.",
        f"Endpoint: {endpoint['host']}:{endpoint['port']}",
        f"Secure transport requested: {endpoint['secure_transport']}",
        f"Authentication mode: {payload['authentication_mode']}",
        "Credential values included: false",
    ]
    if "resolved_addresses" in payload:
        lines.append(
            "Resolved addresses: "
            + ", ".join(payload["resolved_addresses"])
        )
    for warning in payload.get("warnings", []):
        lines.append(f"Warning: {warning}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_connection_config(require_auth=args.require_auth)
        payload = config_summary(config)
        payload["status"] = "valid"
        payload["server_contacted"] = False
        payload["warnings"] = []
        if not config.secure:
            payload["warnings"].append(
                "OMERO_SECURE is false; post-login traffic may be unencrypted"
            )
        if config.authentication_mode == "missing":
            payload["warnings"].append(
                "No complete authentication credential is configured"
            )
        if args.resolve_host:
            payload["resolved_addresses"] = resolve_host(
                config.host,
                config.port,
            )
            payload["dns_resolution_performed"] = True
        else:
            payload["dns_resolution_performed"] = False

        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(format_text(payload))
        return 0
    except (ConfigError, socket.gaierror, OSError) as error:
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "invalid",
                        "server_contacted": False,
                        "error": scrubbed_error(error),
                        "credential_values_included": False,
                    },
                    indent=2,
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
        else:
            print(scrubbed_error(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
