#!/usr/bin/env python3
"""Produce a bounded, read-only OMERO object inventory."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from typing import Any

from omero_common import (
    ConfigError,
    DependencyError,
    OutputPathError,
    bounded_int,
    config_summary,
    emit_json,
    gateway_session,
    json_safe,
    load_connection_config,
    scrubbed_error,
)


OBJECT_TYPES = (
    "Project",
    "Dataset",
    "Image",
    "Screen",
    "Plate",
    "Well",
    "Fileset",
    "OriginalFile",
)


def positive_argument(value: str) -> int:
    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or execute a bounded read-only OMERO object inventory. "
            "Without --execute, no server connection is made."
        )
    )
    parser.add_argument(
        "--object-type",
        choices=OBJECT_TYPES,
        default="Image",
        help="Allowlisted OMERO object type (default: Image).",
    )
    parser.add_argument(
        "--limit",
        type=positive_argument,
        default=100,
        help="Overall object cap, 1..1000 (default: 100).",
    )
    parser.add_argument(
        "--page-size",
        type=positive_argument,
        default=50,
        help="Server page size, 1..200 and no greater than limit.",
    )
    parser.add_argument(
        "--group-id",
        type=positive_argument,
        help="Optional explicit group ID; cross-group -1 is not supported.",
    )
    parser.add_argument(
        "--include-names",
        action="store_true",
        help="Include object names; names are redacted by default.",
    )
    parser.add_argument(
        "--output",
        help="Optional .json output in an existing directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing regular output file, never a symlink.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Connect and perform the read-only inventory.",
    )
    parser.add_argument(
        "--allow-insecure-transport",
        action="store_true",
        help=(
            "Permit OMERO_SECURE=false after explicit policy review. "
            "Encrypted transport remains the default."
        ),
    )
    return parser


def call_or_none(obj: Any, method: str) -> Any:
    function = getattr(obj, method, None)
    if not callable(function):
        return None
    return function()


def object_record(
    obj: Any,
    *,
    requested_type: str,
    include_names: bool,
) -> dict[str, Any]:
    """Serialize only a small allowlisted metadata subset."""

    record: dict[str, Any] = {
        "type": getattr(obj, "OMERO_CLASS", requested_type),
        "id": call_or_none(obj, "getId"),
    }
    if include_names:
        record["name"] = json_safe(
            call_or_none(obj, "getName"),
            max_string_length=512,
        )
    else:
        record["name_redacted"] = True

    details = call_or_none(obj, "getDetails")
    owner = call_or_none(details, "getOwner") if details is not None else None
    group = call_or_none(details, "getGroup") if details is not None else None
    record["owner_id"] = call_or_none(owner, "getId")
    record["group_id"] = call_or_none(group, "getId")

    if requested_type == "Image":
        record["dimensions"] = {
            "x": call_or_none(obj, "getSizeX"),
            "y": call_or_none(obj, "getSizeY"),
            "z": call_or_none(obj, "getSizeZ"),
            "c": call_or_none(obj, "getSizeC"),
            "t": call_or_none(obj, "getSizeT"),
        }
        record["pixels_type"] = call_or_none(obj, "getPixelsType")
    elif requested_type == "OriginalFile":
        record["size_bytes"] = call_or_none(obj, "getSize")
        record["mimetype"] = json_safe(
            call_or_none(obj, "getMimetype"),
            max_string_length=128,
        )
    return record


def collect_inventory(
    connection: Any,
    *,
    object_type: str,
    limit: int,
    page_size: int,
    include_names: bool,
) -> dict[str, Any]:
    """Collect records with explicit server and client limits."""

    records: list[dict[str, Any]] = []
    offset = 0
    exhausted = False

    while len(records) < limit:
        requested = min(page_size, limit - len(records))
        page = list(
            connection.getObjects(
                object_type,
                opts={
                    "limit": requested,
                    "offset": offset,
                    "order_by": "obj.id",
                },
            )
        )
        if not page:
            exhausted = True
            break

        records.extend(
            object_record(
                obj,
                requested_type=object_type,
                include_names=include_names,
            )
            for obj in page[:requested]
        )
        if len(page) < requested:
            exhausted = True
            break
        offset += len(page)

    return {
        "records": records,
        "returned": len(records),
        "limit_reached": len(records) == limit,
        "server_result_exhausted": exhausted,
    }


def dry_run_payload(
    args: argparse.Namespace,
    config: Any,
) -> dict[str, Any]:
    return {
        "mode": "dry-run",
        "server_contacted": False,
        "configuration": config_summary(config),
        "scope": {
            "object_type": args.object_type,
            "group_id": args.group_id,
            "limit": args.limit,
            "page_size": args.page_size,
            "include_names": args.include_names,
            "cross_group": False,
        },
        "next_step": "Review scope, then add --execute for a read-only query.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        bounded_int(args.limit, name="limit", minimum=1, maximum=1000)
        bounded_int(
            args.page_size,
            name="page-size",
            minimum=1,
            maximum=200,
        )
        if args.page_size > args.limit:
            raise ValueError("page-size must not exceed limit")

        config = load_connection_config(require_auth=args.execute)
        if not args.execute:
            emit_json(
                dry_run_payload(args, config),
                output=args.output,
                overwrite=args.overwrite,
            )
            return 0

        with gateway_session(
            config,
            allow_insecure_transport=args.allow_insecure_transport,
        ) as connection:
            if args.group_id is not None:
                connection.SERVICE_OPTS.setOmeroGroup(str(args.group_id))
            result = collect_inventory(
                connection,
                object_type=args.object_type,
                limit=args.limit,
                page_size=args.page_size,
                include_names=args.include_names,
            )

        payload = {
            "mode": "executed-read-only",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "configuration": config_summary(config),
            "scope": {
                "object_type": args.object_type,
                "group_id": args.group_id,
                "limit": args.limit,
                "page_size": args.page_size,
                "include_names": args.include_names,
                "cross_group": False,
            },
            **result,
        }
        emit_json(
            payload,
            output=args.output,
            overwrite=args.overwrite,
        )
        return 0
    except (
        ConfigError,
        DependencyError,
        OutputPathError,
        FileExistsError,
        ValueError,
        RuntimeError,
    ) as error:
        print(scrubbed_error(error), file=sys.stderr)
        return 2
    except Exception as error:
        print(scrubbed_error(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
