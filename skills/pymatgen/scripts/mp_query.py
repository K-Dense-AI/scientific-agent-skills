#!/usr/bin/env python3
"""Plan or explicitly execute one bounded Materials Project summary query."""

from __future__ import annotations

import argparse
import math
import os
import re
from datetime import datetime, timezone
from typing import Any

from _common import (
    CliError,
    DEFAULT_MAX_OUTPUT_BYTES,
    MP_API_VERSION,
    PYMATGEN_CORE_VERSION,
    PYMATGEN_VERSION,
    checked_output_file,
    emit_json,
    json_text,
    package_versions,
    positive_int,
    safe_error_message,
    write_json_new,
)


FIELD_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,79}$")
MATERIAL_ID_PATTERN = re.compile(r"^(?:mp|mvc)-(?:[0-9]{1,30}|[a-z]{1,30})$")
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9.+\-()]+$")
MAX_RESULTS = 100
MAX_FIELDS = 20
MAX_MATERIAL_IDS = 100


def csv_tokens(value: str | None, label: str) -> list[str] | None:
    """Parse a bounded, unique comma-separated token list."""
    if value is None:
        return None
    tokens = [token.strip() for token in value.split(",") if token.strip()]
    if not tokens:
        raise CliError(f"{label} must contain at least one token")
    if len(tokens) > 100:
        raise CliError(f"{label} may contain at most 100 tokens")
    if any(not TOKEN_PATTERN.fullmatch(token) for token in tokens):
        raise CliError(f"{label} contains unsupported characters")
    return list(dict.fromkeys(tokens))


def parse_fields(value: str) -> list[str]:
    """Parse explicit response fields."""
    fields = [field.strip() for field in value.split(",") if field.strip()]
    fields = list(dict.fromkeys(fields))
    if not fields:
        raise CliError("--fields must contain at least one field")
    if len(fields) > MAX_FIELDS:
        raise CliError(f"--fields may contain at most {MAX_FIELDS} fields")
    invalid = [field for field in fields if not FIELD_PATTERN.fullmatch(field)]
    if invalid:
        raise CliError(f"invalid field names: {invalid}")
    return fields


def checked_range(
    values: list[float] | None,
    label: str,
    *,
    non_negative: bool = False,
) -> tuple[float, float] | None:
    """Validate an inclusive two-number range."""
    if values is None:
        return None
    low, high = values
    if not all(math.isfinite(value) for value in (low, high)):
        raise CliError(f"{label} bounds must be finite")
    if low > high:
        raise CliError(f"{label} minimum must not exceed maximum")
    if non_negative and low < 0:
        raise CliError(f"{label} must be non-negative")
    return float(low), float(high)


def query_contract(args: argparse.Namespace) -> dict[str, Any]:
    """Validate arguments and return the exact public search kwargs."""
    if len(args.material_id) > MAX_MATERIAL_IDS:
        raise CliError(
            f"--material-id may be repeated at most {MAX_MATERIAL_IDS} times"
        )
    invalid_ids = [
        item
        for item in args.material_id
        if not MATERIAL_ID_PATTERN.fullmatch(item)
    ]
    if invalid_ids:
        raise CliError(f"invalid Materials Project IDs: {invalid_ids}")
    for label, value in (("--formula", args.formula), ("--chemsys", args.chemsys)):
        if value is not None and (
            len(value) > 200 or not TOKEN_PATTERN.fullmatch(value)
        ):
            raise CliError(f"{label} contains unsupported characters")
    elements = csv_tokens(args.elements, "--elements")
    exclude_elements = csv_tokens(args.exclude_elements, "--exclude-elements")
    energy_range = checked_range(
        args.energy_above_hull,
        "--energy-above-hull",
        non_negative=True,
    )
    band_gap = checked_range(args.band_gap, "--band-gap", non_negative=True)
    stable = None
    if args.is_stable != "any":
        stable = args.is_stable == "true"
    fields = parse_fields(args.fields)
    effective_fields = list(dict.fromkeys(["material_id", *fields]))
    filters: dict[str, Any] = {
        "material_ids": args.material_id or None,
        "formula": args.formula,
        "chemsys": args.chemsys,
        "elements": elements,
        "exclude_elements": exclude_elements,
        "energy_above_hull": energy_range,
        "band_gap": band_gap,
        "is_stable": stable,
    }
    if not any(value is not None for value in filters.values()):
        raise CliError("at least one query filter is required")
    search_kwargs = {
        key: value for key, value in filters.items() if value is not None
    }
    search_kwargs.update(
        {
            "fields": effective_fields,
            "all_fields": False,
            "num_chunks": 1,
            "chunk_size": args.limit,
        }
    )
    return {
        "filters": filters,
        "requested_fields": fields,
        "effective_fields": effective_fields,
        "search_kwargs": search_kwargs,
    }


def plan_payload(
    args: argparse.Namespace,
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Disclose network, credential, cache, field, limit, and output behavior."""
    return {
        "ok": True,
        "action": "materials_project_summary_query",
        "execute_requested": bool(args.execute),
        "network_will_be_accessed": bool(args.execute),
        "endpoint": "https://api.materialsproject.org/materials/summary/",
        "client": "mp_api.client.MPRester",
        "network_operations_when_executed": [
            "mp-api compatibility/heartbeat metadata checks during MPRester initialization",
            "one bounded materials.summary.search call",
        ],
        "user_agent_with_platform_details": False,
        "authentication": {
            "environment_variable": "MP_API_KEY",
            "read_only_when_execute_is_set": True,
            "accepted_on_command_line": False,
            "value_logged_or_serialized": False,
        },
        "query": {
            "filters": contract["filters"],
            "requested_fields": contract["requested_fields"],
            "effective_fields": contract["effective_fields"],
            "limit": args.limit,
            "num_chunks": 1,
        },
        "result_cache": {
            "enabled": False,
            "read": False,
            "written": False,
            "note": (
                "This CLI has no implicit result cache. The explicit JSON output "
                "is the reusable artifact. It does not request mp-api full-dataset "
                "downloads, so the configured full-dataset cache is not used."
            ),
        },
        "output": {
            "path_as_provided": args.output,
            "required_for_execution": True,
            "maximum_bytes": args.max_output_bytes,
            "existing_files_overwritten": False,
        },
        "rate_and_error_handling": {
            "custom_retries": False,
            "client_behavior": (
                "mp-api 0.46.5 retries 429, 502, and 504 according to its "
                "configured retry policy and respects Retry-After"
            ),
            "numeric_service_quota_assumed": False,
            "errors_are_redacted_and_bounded": True,
        },
        "data_use": {
            "license": "CC BY 4.0 for Materials Project data; contributed data may differ",
            "citation_required": True,
            "computed_data_is_experimental_truth": False,
            "database_version_recorded_automatically": True,
        },
    }


def document_to_json(document: Any) -> dict[str, Any]:
    """Convert an mp-api document through its public Pydantic interface."""
    if isinstance(document, dict):
        result = document
    elif hasattr(document, "model_dump"):
        result = document.model_dump(mode="json")
    else:
        raise CliError(
            f"unsupported mp-api result type: {type(document).__name__}"
        )
    if not isinstance(result, dict):
        raise CliError("mp-api document did not serialize to an object")
    json_text(result, pretty=False)
    return result


def execute_query(
    args: argparse.Namespace,
    contract: dict[str, Any],
    output_path: Any,
) -> dict[str, Any]:
    """Execute exactly one bounded summary search."""
    api_key = os.getenv("MP_API_KEY")
    if not api_key:
        raise CliError(
            "MP_API_KEY is not set; obtain it from the Materials Project dashboard "
            "and inject only that named secret through your shell or secret manager"
        )
    installed = package_versions(("pymatgen", "pymatgen-core", "mp-api"))
    expected = {
        "pymatgen": PYMATGEN_VERSION,
        "pymatgen-core": PYMATGEN_CORE_VERSION,
        "mp-api": MP_API_VERSION,
    }
    if installed != expected:
        raise CliError(
            f"network execution requires the verified package snapshot; "
            f"expected={expected}, installed={installed}"
        )
    from mp_api.client import MPRester
    from mp_api.client.core.exceptions import MPRestError

    try:
        with MPRester(
            api_key=api_key,
            endpoint="https://api.materialsproject.org/",
            include_user_agent=False,
            mute_progress_bars=True,
            notify_db_version=False,
        ) as rester:
            database_version = rester.db_version
            available = set(rester.materials.summary.available_fields)
            invalid_fields = [
                field
                for field in contract["effective_fields"]
                if field not in available
            ]
            if invalid_fields:
                raise CliError(
                    f"fields unavailable in this endpoint/client: {invalid_fields}"
                )
            documents = rester.materials.summary.search(
                **contract["search_kwargs"]
            )
    except CliError:
        raise
    except MPRestError as exc:
        raise CliError(safe_error_message(exc, secret=api_key)) from exc
    except Exception as exc:
        raise CliError(safe_error_message(exc, secret=api_key)) from exc
    serialized = [document_to_json(document) for document in documents[: args.limit]]
    result = {
        "schema_version": "1.0",
        "provenance": {
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "endpoint": "https://api.materialsproject.org/materials/summary/",
            "pymatgen_version": PYMATGEN_VERSION,
            "pymatgen_core_version": PYMATGEN_CORE_VERSION,
            "mp_api_version": MP_API_VERSION,
            "database_version": database_version,
            "data_license": "CC BY 4.0; contributed data is owned by contributors",
            "citation": "https://materialsproject.org/about/cite",
        },
        "query": {
            "filters": contract["filters"],
            "fields": contract["effective_fields"],
            "limit": args.limit,
            "num_chunks": 1,
        },
        "returned": len(serialized),
        "returned_equals_requested_limit": len(serialized) == args.limit,
        "more_results_may_exist": len(serialized) == args.limit,
        "documents": serialized,
        "interpretation_limits": [
            "Materials Project values are computed and method-dependent.",
            "Aggregated values can change between database releases.",
            "Missing fields do not imply a measured zero.",
            "Band gaps and other properties carry documented systematic errors.",
        ],
    }
    write_json_new(output_path, result, max_bytes=args.max_output_bytes)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan a bounded Materials Project summary query. No network or "
            "credential access occurs unless --execute is supplied."
        )
    )
    parser.add_argument("--material-id", action="append", default=[])
    parser.add_argument("--formula")
    parser.add_argument("--chemsys")
    parser.add_argument("--elements", help="Comma-separated required elements")
    parser.add_argument(
        "--exclude-elements", help="Comma-separated excluded elements"
    )
    parser.add_argument(
        "--energy-above-hull",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
    )
    parser.add_argument("--band-gap", nargs=2, type=float, metavar=("MIN", "MAX"))
    parser.add_argument(
        "--is-stable",
        choices=("any", "true", "false"),
        default="any",
    )
    parser.add_argument(
        "--fields",
        required=True,
        help="Comma-separated response fields; material_id is always added",
    )
    parser.add_argument("--limit", type=positive_int, default=25)
    parser.add_argument("--output", help="New JSON result path (required with --execute)")
    parser.add_argument("--plan-output", help="New JSON path for the dry-run plan")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Explicitly permit the disclosed bounded network query",
    )
    parser.add_argument(
        "--max-output-bytes",
        type=positive_int,
        default=DEFAULT_MAX_OUTPUT_BYTES,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.limit > MAX_RESULTS:
            raise CliError(f"--limit may not exceed {MAX_RESULTS}")
        if args.max_output_bytes > 50 * 1024 * 1024:
            raise CliError("--max-output-bytes may not exceed 50 MiB")
        contract = query_contract(args)
        plan = plan_payload(args, contract)
        if args.execute:
            if not args.output:
                raise CliError("--execute requires an explicit new --output path")
            output_path = checked_output_file(args.output)
            result = execute_query(args, contract, output_path)
            emit_json(
                {
                    "ok": True,
                    "executed": True,
                    "network_accessed": True,
                    "output": output_path.name,
                    "output_bytes": output_path.stat().st_size,
                    "returned": result["returned"],
                    "overwrote_existing": False,
                    "api_key_logged": False,
                }
            )
        elif args.plan_output:
            plan_path = checked_output_file(args.plan_output)
            write_json_new(plan_path, plan, max_bytes=args.max_output_bytes)
            emit_json(
                {
                    "ok": True,
                    "executed": False,
                    "network_accessed": False,
                    "plan_output": plan_path.name,
                    "overwrote_existing": False,
                }
            )
        else:
            emit_json(plan)
        return 0
    except (CliError, ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
        emit_json(
            {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}"[:1000],
                "completed": False,
                "execute_requested": bool(args.execute),
                "network_may_have_been_accessed": bool(args.execute),
                "api_key_logged": False,
            }
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
