#!/usr/bin/env python3
"""Safe PufferLib training-plan template.

This script never imports PufferLib, starts training, loads checkpoints, uses a
GPU, or contacts an external logger. It emits a validated argv preview for a
human to review in an appropriately sandboxed, pinned environment.
"""

from __future__ import annotations

import argparse
import copy
from typing import Any

try:
    from ._common import LOGGER_CREDENTIAL_ENV, UserInputError, bounded_int, emit_json, validate_slug
    from .validate_plan import PROFILES, default_plan, validate_plan
except ImportError:  # Direct script execution.
    from _common import LOGGER_CREDENTIAL_ENV, UserInputError, bounded_int, emit_json, validate_slug
    from validate_plan import PROFILES, default_plan, validate_plan


def _command_preview(plan: dict[str, Any]) -> list[str]:
    """Build argv without shell interpolation or execution."""
    environment = plan["environment"]["name"]
    if environment == "synthetic":
        return []

    training = plan["training"]
    vector = plan["vectorization"]
    command = [
        "puffer",
        "train",
        environment,
        "--train.total-timesteps",
        str(training["total_timesteps"]),
        "--train.seed",
        str(training["seed"]),
        "--train.minibatch-size",
        str(training["minibatch_size"]),
    ]
    if plan["profile"] == "pypi-3.0.0":
        backend_name = {
            "serial": "Serial",
            "multiprocessing": "Multiprocessing",
            "native": "PufferEnv",
        }[vector["backend"]]
        command.extend(
            [
                "--train.device",
                training["device"],
                "--train.bptt-horizon",
                str(training["horizon"]),
                "--vec.seed",
                str(training["seed"]),
                "--vec.backend",
                backend_name,
                "--vec.num-envs",
                str(vector["num_envs"]),
                "--vec.num-workers",
                str(vector["num_workers"]),
                "--vec.batch-size",
                str(vector["batch_size"]),
            ]
        )
    else:
        command.extend(
            [
                "--seed",
                str(training["seed"]),
                "--train.horizon",
                str(training["horizon"]),
                "--vec.total-agents",
                str(vector["total_agents"]),
                "--vec.num-buffers",
                str(vector["num_buffers"]),
                "--vec.num-threads",
                str(vector["num_threads"]),
            ]
        )
        if vector["backend"] == "torch":
            command.append("--slowly")

    logger = plan["logging"]["backend"]
    if logger != "none":
        command.append(f"--{logger}")
    return command


def make_plan(args: argparse.Namespace) -> dict[str, Any]:
    plan = default_plan(args.profile)
    environment = validate_slug(args.environment, name="environment")
    plan["environment"]["name"] = environment
    plan["environment"]["adapter"] = args.adapter
    plan["environment"]["provenance_verified"] = (
        environment == "synthetic" or args.provenance_verified
    )

    plan["training"].update(
        {
            "device": args.device,
            "horizon": bounded_int(
                args.horizon, name="horizon", minimum=1, maximum=65_536
            ),
            "minibatch_size": bounded_int(
                args.minibatch_size,
                name="minibatch_size",
                minimum=1,
                maximum=16_777_216,
            ),
            "seed": bounded_int(
                args.seed, name="seed", minimum=0, maximum=2**32 - 1
            ),
            "total_timesteps": bounded_int(
                args.total_timesteps,
                name="total_timesteps",
                minimum=1,
                maximum=1_000_000_000,
            ),
        }
    )
    plan["evaluation"].update(
        {
            "deterministic": args.deterministic_eval,
            "episodes": bounded_int(
                args.eval_episodes,
                name="eval_episodes",
                minimum=1,
                maximum=10_000,
            ),
            "seed": bounded_int(
                args.eval_seed, name="eval_seed", minimum=0, maximum=2**32 - 1
            ),
            "separate": True,
        }
    )
    plan["logging"].update(
        {
            "backend": args.logger,
            "disclosure_ack": args.acknowledge_external_disclosure,
            "external_opt_in": args.enable_external_logging,
            "upload_checkpoints": args.upload_checkpoints,
        }
    )
    if args.profile == "pypi-3.0.0":
        backend = args.backend or "serial"
        plan["vectorization"].update(
            {
                "backend": backend,
                "batch_size": bounded_int(
                    args.batch_size,
                    name="batch_size",
                    minimum=1,
                    maximum=65_536,
                ),
                "num_envs": bounded_int(
                    args.num_envs, name="num_envs", minimum=1, maximum=65_536
                ),
                "num_workers": bounded_int(
                    args.num_workers,
                    name="num_workers",
                    minimum=1,
                    maximum=256,
                ),
                "start_method": args.start_method,
                "zero_copy": args.zero_copy,
            }
        )
    else:
        backend = args.backend or "torch"
        plan["vectorization"].update(
            {
                "backend": backend,
                "num_buffers": bounded_int(
                    args.num_buffers, name="num_buffers", minimum=1, maximum=256
                ),
                "num_threads": bounded_int(
                    args.num_threads, name="num_threads", minimum=1, maximum=256
                ),
                "start_method": "spawn",
                "total_agents": bounded_int(
                    args.total_agents,
                    name="total_agents",
                    minimum=1,
                    maximum=65_536,
                ),
            }
        )
        plan["checkpoint"]["format"] = (
            "state_dict" if backend == "torch" else "native-bin"
        )
    return plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a bounded, local PufferLib dry-run plan. This command never "
            "executes the generated argv."
        )
    )
    parser.add_argument("--profile", choices=PROFILES, default="pypi-3.0.0")
    parser.add_argument("--environment", default="synthetic")
    parser.add_argument(
        "--adapter",
        choices=["synthetic", "gymnasium", "pettingzoo", "native-ocean"],
        default="synthetic",
    )
    parser.add_argument(
        "--provenance-verified",
        action="store_true",
        help="Explicitly attest review for a non-synthetic environment",
    )
    parser.add_argument(
        "--backend",
        choices=["serial", "multiprocessing", "native", "torch"],
        default=None,
    )
    parser.add_argument("--num-envs", type=int, default=4)
    parser.add_argument("--num-workers", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--zero-copy", action="store_true")
    parser.add_argument(
        "--start-method", choices=["spawn", "forkserver"], default="spawn"
    )
    parser.add_argument("--total-agents", type=int, default=64)
    parser.add_argument("--num-buffers", type=int, default=2)
    parser.add_argument("--num-threads", type=int, default=1)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--total-timesteps", type=int, default=10_000)
    parser.add_argument("--horizon", type=int, default=16)
    parser.add_argument("--minibatch-size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eval-seed", type=int, default=1_000_042)
    parser.add_argument("--eval-episodes", type=int, default=10)
    parser.add_argument(
        "--stochastic-eval",
        dest="deterministic_eval",
        action="store_false",
        default=True,
    )
    parser.add_argument("--logger", choices=["none", "wandb", "neptune"], default="none")
    parser.add_argument("--enable-external-logging", action="store_true")
    parser.add_argument("--acknowledge-external-disclosure", action="store_true")
    parser.add_argument("--upload-checkpoints", action="store_true")
    parser.add_argument("--compact", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        plan = make_plan(args)
        errors = validate_plan(plan)
        logger = plan["logging"]["backend"]
        report = {
            "command_preview": _command_preview(plan) if not errors else [],
            "credential": {
                "environment_variable": LOGGER_CREDENTIAL_ENV.get(logger),
                "value_read_or_logged": False,
            },
            "dry_run": True,
            "errors": errors,
            "external_logging_disclosure": (
                "External services may receive configuration, metrics, source metadata, "
                "hardware telemetry, and explicitly enabled artifacts; review vendor "
                "privacy, retention, access, and pricing before use."
                if logger != "none"
                else None
            ),
            "network_used": False,
            "preview_limitations": [
                "Historical 3.0/4.0 CLI preview only; not a 5.0 command.",
                "Set environment-specific rollout batch size and verify agent counts.",
                "Start method and zero-copy are plan requirements, not applied by this preview.",
                "For 4.0, the compiled backend selects CPU/CUDA; the plan does not rebuild it.",
            ],
            "plan": copy.deepcopy(plan),
            "status": "valid" if not errors else "invalid",
        }
    except (UserInputError, KeyError, ValueError) as exc:
        report = {
            "command_preview": [],
            "dry_run": True,
            "errors": [str(exc)],
            "network_used": False,
            "plan": None,
            "status": "invalid",
        }
    emit_json(report, pretty=not args.compact)
    return 0 if report["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
