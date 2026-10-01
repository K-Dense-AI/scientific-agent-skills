#!/usr/bin/env python3
"""Create a deterministic token/cost preflight without calling any model."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from decimal import Decimal, ROUND_HALF_UP

if __package__:
    from ._common import (
        HYPOGENIC_COMMIT,
        HYPOGENIC_VERSION,
        HYPOGENIC_WHEEL_SHA256,
        MAX_CONFIG_BYTES,
        CliError,
        checked_input_file,
        emit_error,
        emit_json,
        load_structured_document,
        named_env_presence,
        sha256_file,
        validate_run_config,
    )
else:
    from _common import (  # type: ignore
        HYPOGENIC_COMMIT,
        HYPOGENIC_VERSION,
        HYPOGENIC_WHEEL_SHA256,
        MAX_CONFIG_BYTES,
        CliError,
        checked_input_file,
        emit_error,
        emit_json,
        load_structured_document,
        named_env_presence,
        sha256_file,
        validate_run_config,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a plan-only HypoGeniC token/cost upper bound. No package, "
            "model, provider SDK, dataset, .env, or network service is loaded."
        )
    )
    parser.add_argument("--config", required=True, help="Local reviewed run policy")
    parser.add_argument("--root", default=".", help="Existing local I/O boundary")
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Check only the configured named credential variable; never print its value",
    )
    parser.add_argument(
        "--check-inputs",
        action="store_true",
        help="Require the configured task config and dataset manifest to exist",
    )
    return parser


def _money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def make_plan(
    config: dict,
    *,
    config_sha256: str,
    check_env: bool,
    inputs_checked: bool,
) -> dict:
    limits = config["limits"]
    pricing = config["pricing"]
    max_requests = limits["max_requests"]
    input_tokens = max_requests * limits["max_input_tokens_per_request"]
    output_tokens = max_requests * limits["max_output_tokens_per_request"]
    total_tokens = input_tokens + output_tokens
    token_cap_ok = total_tokens <= limits["max_total_tokens"]

    rates_available = pricing["input_usd_per_million_tokens"] is not None
    estimated_cost: float | None = None
    cost_cap_ok = False
    if rates_available:
        million = Decimal(1_000_000)
        input_cost = (
            Decimal(input_tokens)
            * Decimal(str(pricing["input_usd_per_million_tokens"]))
            / million
        )
        output_cost = (
            Decimal(output_tokens)
            * Decimal(str(pricing["output_usd_per_million_tokens"]))
            / million
        )
        exact_cost = input_cost + output_cost
        estimated_cost = _money(exact_cost)
        cost_cap_ok = exact_cost <= Decimal(
            str(limits["max_cost_usd"])
        )

    environment = (
        named_env_presence(config)
        if check_env
        else {
            "checked": False,
            "name": config["provider"]["credential_env"],
            "value_included": False,
        }
    )
    environment_ready = (
        not check_env
        or environment.get("required") is False
        or environment.get("present") is True
    )
    ready = (
        rates_available
        and token_cap_ok
        and cost_cap_ok
        and environment_ready
        and config["execution"]["mode"] == "plan_only"
    )
    blockers: list[str] = []
    if not rates_available:
        blockers.append("current provider token prices are not supplied")
    if not token_cap_ok:
        blockers.append("worst-case tokens exceed max_total_tokens")
    if rates_available and not cost_cap_ok:
        blockers.append("worst-case API cost exceeds max_cost_usd")
    if not environment_ready:
        blockers.append("the named provider credential is absent")

    return {
        "ok": ready,
        "plan_kind": "hypogenic_preflight_only",
        "schema_version": config["schema_version"],
        "config_sha256": config_sha256,
        "software": {
            "package": "hypogenic",
            "version": HYPOGENIC_VERSION,
            "source_commit": HYPOGENIC_COMMIT,
            "wheel_sha256": HYPOGENIC_WHEEL_SHA256,
            "package_imported": False,
        },
        "provider": {
            "type": config["provider"]["type"],
            "model": config["provider"]["model"],
            "data_destination": config["provider"]["data_destination"],
            "credential_environment": environment,
            "local_model_path_configured": (
                config["provider"]["local_model_path"] is not None
            ),
        },
        "data": {
            "task_config": config["data"]["task_config"],
            "dataset_manifest": config["data"]["dataset_manifest"],
            "output_directory": config["data"]["output_directory"],
            "test_split_policy": "locked_until_final",
            "test_split_sent_during_generation": False,
            "inputs_checked": inputs_checked,
        },
        "limits": limits,
        "cost_upper_bound": {
            "method": (
                "max_requests * per-request input/output token caps * "
                "user-reviewed per-million-token rates"
            ),
            "maximum_input_tokens": input_tokens,
            "maximum_output_tokens": output_tokens,
            "maximum_total_tokens": total_tokens,
            "within_total_token_cap": token_cap_ok,
            "pricing_available": rates_available,
            "pricing_reviewed_on": pricing["reviewed_on"],
            "pricing_source": pricing["source"],
            "estimated_maximum_cost_usd": estimated_cost,
            "configured_cost_cap_usd": limits["max_cost_usd"],
            "within_cost_cap": cost_cap_ok if rates_available else None,
            "not_a_provider_quote": True,
        },
        "execution": {
            "ready_for_separate_execution_review": ready,
            "blockers": blockers,
            "external_calls_authorized": False,
            "requires_separate_confirmation": True,
            "network_access": False,
            "model_called": False,
            "commands_executed": False,
        },
        "logging": {
            "level": config["logging"]["level"],
            "prompt_content_redacted": True,
            "response_content_redacted": True,
            "credential_values_included": False,
        },
        "caveats": [
            "This is a conservative arithmetic bound, not tokenizer output or a provider quote.",
            "The pinned upstream CLI does not enforce this dollar budget.",
            "This plan does not verify model compatibility or the SDK endpoint actually used.",
            "Verify current model limits, prices, account limits, and retention before execution.",
            "Candidate hypotheses and benchmark metrics are not scientific validation.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config_path = checked_input_file(
            args.config,
            root=args.root,
            suffixes={".json", ".yaml", ".yml"},
            max_bytes=MAX_CONFIG_BYTES,
        )
        config = validate_run_config(
            load_structured_document(
                args.config,
                root=args.root,
                max_bytes=MAX_CONFIG_BYTES,
            )
        )
        if args.check_inputs:
            checked_input_file(
                config["data"]["task_config"],
                root=args.root,
                suffixes={".json", ".yaml", ".yml"},
                max_bytes=MAX_CONFIG_BYTES,
            )
            checked_input_file(
                config["data"]["dataset_manifest"],
                root=args.root,
                suffixes={".json"},
                max_bytes=MAX_CONFIG_BYTES,
            )
        plan = make_plan(
            config,
            config_sha256=sha256_file(config_path, max_bytes=MAX_CONFIG_BYTES),
            check_env=args.check_env,
            inputs_checked=bool(args.check_inputs),
        )
        emit_json(plan)
        return 0 if plan["ok"] else 3
    except (CliError, OSError) as error:
        return emit_error(error)


if __name__ == "__main__":
    raise SystemExit(main())
