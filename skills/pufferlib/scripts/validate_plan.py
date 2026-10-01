#!/usr/bin/env python3
"""Strict, dependency-free validator for PufferLib training plans."""

from __future__ import annotations

import argparse
import copy
import re
from typing import Any

try:
    from ._common import (
        LOGGER_CREDENTIAL_ENV,
        MAX_ENVS,
        MAX_EVAL_EPISODES,
        MAX_STEPS,
        MAX_WORKERS,
        SOURCE_4_COMMIT,
        STABLE_SDIST_SHA256,
        UserInputError,
        emit_json,
        load_json_object,
        require_keys,
        secret_key_paths,
        validate_slug,
    )
except ImportError:  # Direct script execution.
    from _common import (
        LOGGER_CREDENTIAL_ENV,
        MAX_ENVS,
        MAX_EVAL_EPISODES,
        MAX_STEPS,
        MAX_WORKERS,
        SOURCE_4_COMMIT,
        STABLE_SDIST_SHA256,
        UserInputError,
        emit_json,
        load_json_object,
        require_keys,
        secret_key_paths,
        validate_slug,
    )

PROFILES = ("pypi-3.0.0", "source-4.0")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def default_plan(profile: str = "pypi-3.0.0") -> dict[str, Any]:
    """Return a bounded local plan that never starts training."""
    if profile not in PROFILES:
        raise UserInputError(f"profile must be one of {PROFILES}")
    common: dict[str, Any] = {
        "schema_version": 1,
        "profile": profile,
        "environment": {
            "adapter": "synthetic",
            "name": "synthetic",
            "provenance_verified": True,
        },
        "training": {
            "device": "cpu",
            "horizon": 16,
            "minibatch_size": 256,
            "seed": 42,
            "total_timesteps": 10_000,
        },
        "evaluation": {
            "deterministic": True,
            "episodes": 10,
            "seed": 1_000_042,
            "separate": True,
        },
        "logging": {
            "backend": "none",
            "disclosure_ack": False,
            "external_opt_in": False,
            "upload_checkpoints": False,
        },
        "checkpoint": {
            "format": "state_dict",
            "trusted_only": True,
        },
    }
    if profile == "pypi-3.0.0":
        common["package"] = {
            "name": "pufferlib",
            "sha256": STABLE_SDIST_SHA256,
            "version": "3.0.0",
        }
        common["vectorization"] = {
            "backend": "serial",
            "batch_size": 4,
            "num_envs": 4,
            "num_workers": 1,
            "start_method": "spawn",
            "zero_copy": False,
        }
    else:
        common["package"] = {
            "commit": SOURCE_4_COMMIT,
            "name": "pufferlib",
            "version": "4.0.0-source",
        }
        common["vectorization"] = {
            "backend": "torch",
            "num_buffers": 2,
            "num_threads": 1,
            "start_method": "spawn",
            "total_agents": 64,
        }
    return common


def _mapping(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return {}
    return value


def _integer(
    value: Any,
    *,
    path: str,
    minimum: int,
    maximum: int,
    errors: list[str],
) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{path} must be an integer")
        return None
    if not minimum <= value <= maximum:
        errors.append(f"{path} must be between {minimum} and {maximum}")
        return None
    return value


def _boolean(value: Any, *, path: str, errors: list[str]) -> bool | None:
    if type(value) is not bool:
        errors.append(f"{path} must be boolean")
        return None
    return value


def _validate_package(
    package: dict[str, Any], profile: str, errors: list[str]
) -> None:
    if profile == "pypi-3.0.0":
        errors.extend(
            require_keys(
                package,
                allowed={"name", "version", "sha256"},
                required={"name", "version", "sha256"},
                path="$.package",
            )
        )
        if package.get("version") != "3.0.0":
            errors.append("$.package.version must equal 3.0.0")
        if package.get("sha256") != STABLE_SDIST_SHA256:
            errors.append("$.package.sha256 must match the published 3.0.0 sdist")
    elif profile == "source-4.0":
        errors.extend(
            require_keys(
                package,
                allowed={"name", "version", "commit"},
                required={"name", "version", "commit"},
                path="$.package",
            )
        )
        commit = package.get("commit")
        if not isinstance(commit, str) or not _COMMIT.fullmatch(commit):
            errors.append("$.package.commit must be a pinned 40-character commit")
        if package.get("version") != "4.0.0-source":
            errors.append("$.package.version must equal 4.0.0-source")
    if package.get("name") != "pufferlib":
        errors.append("$.package.name must equal pufferlib")


def _validate_environment(environment: dict[str, Any], errors: list[str]) -> None:
    errors.extend(
        require_keys(
            environment,
            allowed={"adapter", "name", "provenance_verified"},
            required={"adapter", "name", "provenance_verified"},
            path="$.environment",
        )
    )
    try:
        validate_slug(environment.get("name"), name="environment.name")
    except UserInputError as exc:
        errors.append(str(exc))
    if environment.get("adapter") not in {
        "synthetic",
        "gymnasium",
        "pettingzoo",
        "native-ocean",
    }:
        errors.append("$.environment.adapter is not allowlisted")
    if environment.get("name") == "synthetic" and environment.get("adapter") != "synthetic":
        errors.append("the synthetic environment must use the synthetic adapter")
    if environment.get("name") != "synthetic" and environment.get("adapter") == "synthetic":
        errors.append("a non-synthetic environment cannot use the synthetic adapter")
    if environment.get("provenance_verified") is not True:
        errors.append("$.environment.provenance_verified must be true")


def _validate_training(training: dict[str, Any], errors: list[str]) -> None:
    errors.extend(
        require_keys(
            training,
            allowed={"device", "horizon", "minibatch_size", "seed", "total_timesteps"},
            required={"device", "horizon", "minibatch_size", "seed", "total_timesteps"},
            path="$.training",
        )
    )
    if training.get("device") not in {"cpu", "cuda"}:
        errors.append("$.training.device must be cpu or cuda")
    _integer(
        training.get("seed"),
        path="$.training.seed",
        minimum=0,
        maximum=2**32 - 1,
        errors=errors,
    )
    _integer(
        training.get("total_timesteps"),
        path="$.training.total_timesteps",
        minimum=1,
        maximum=MAX_STEPS,
        errors=errors,
    )
    horizon = _integer(
        training.get("horizon"),
        path="$.training.horizon",
        minimum=1,
        maximum=65_536,
        errors=errors,
    )
    minibatch = _integer(
        training.get("minibatch_size"),
        path="$.training.minibatch_size",
        minimum=1,
        maximum=16_777_216,
        errors=errors,
    )
    if horizon and minibatch and minibatch % horizon:
        errors.append("$.training.minibatch_size must be divisible by horizon")


def _validate_vectorization(
    vectorization: dict[str, Any],
    profile: str,
    training: dict[str, Any],
    errors: list[str],
) -> None:
    if profile == "pypi-3.0.0":
        allowed = {
            "backend",
            "batch_size",
            "num_envs",
            "num_workers",
            "start_method",
            "zero_copy",
        }
        errors.extend(
            require_keys(
                vectorization,
                allowed=allowed,
                required=allowed,
                path="$.vectorization",
            )
        )
        backend = vectorization.get("backend")
        if backend not in {
            "serial",
            "multiprocessing",
            "native",
        }:
            errors.append("$.vectorization.backend is invalid for PufferLib 3.0.0")
        num_envs = _integer(
            vectorization.get("num_envs"),
            path="$.vectorization.num_envs",
            minimum=1,
            maximum=MAX_ENVS,
            errors=errors,
        )
        workers = _integer(
            vectorization.get("num_workers"),
            path="$.vectorization.num_workers",
            minimum=1,
            maximum=MAX_WORKERS,
            errors=errors,
        )
        batch = _integer(
            vectorization.get("batch_size"),
            path="$.vectorization.batch_size",
            minimum=1,
            maximum=MAX_ENVS,
            errors=errors,
        )
        zero_copy = _boolean(
            vectorization.get("zero_copy"),
            path="$.vectorization.zero_copy",
            errors=errors,
        )
        if vectorization.get("start_method") not in {"spawn", "forkserver"}:
            errors.append("$.vectorization.start_method must be spawn or forkserver")
        if num_envs and workers and num_envs % workers:
            errors.append("$.vectorization.num_envs must be divisible by num_workers")
        if num_envs and batch and batch > num_envs:
            errors.append("$.vectorization.batch_size cannot exceed num_envs")
        if num_envs and batch and zero_copy and num_envs % batch:
            errors.append(
                "$.vectorization.num_envs must be divisible by batch_size "
                "when zero_copy is true"
            )
        if num_envs and workers and batch:
            envs_per_worker = num_envs // workers if num_envs % workers == 0 else 0
            if envs_per_worker and batch % envs_per_worker:
                errors.append(
                    "$.vectorization.batch_size must be divisible by envs_per_worker"
                )
        if backend == "native" and num_envs != 1:
            errors.append(
                "$.vectorization.num_envs must equal 1 for the stable native backend"
            )
    else:
        allowed = {
            "backend",
            "num_buffers",
            "num_threads",
            "start_method",
            "total_agents",
        }
        errors.extend(
            require_keys(
                vectorization,
                allowed=allowed,
                required=allowed,
                path="$.vectorization",
            )
        )
        if vectorization.get("backend") not in {"native", "torch"}:
            errors.append("$.vectorization.backend must be native or torch")
        agents = _integer(
            vectorization.get("total_agents"),
            path="$.vectorization.total_agents",
            minimum=1,
            maximum=MAX_ENVS,
            errors=errors,
        )
        buffers = _integer(
            vectorization.get("num_buffers"),
            path="$.vectorization.num_buffers",
            minimum=1,
            maximum=256,
            errors=errors,
        )
        _integer(
            vectorization.get("num_threads"),
            path="$.vectorization.num_threads",
            minimum=1,
            maximum=MAX_WORKERS,
            errors=errors,
        )
        if vectorization.get("start_method") != "spawn":
            errors.append("$.vectorization.start_method must be spawn for 4.0")
        if agents and buffers and agents % buffers:
            errors.append("$.vectorization.total_agents must be divisible by num_buffers")
        horizon = training.get("horizon")
        minibatch = training.get("minibatch_size")
        if (
            isinstance(agents, int)
            and isinstance(horizon, int)
            and isinstance(minibatch, int)
            and minibatch > agents * horizon
        ):
            errors.append(
                "$.training.minibatch_size cannot exceed total_agents * horizon"
            )


def _validate_evaluation(
    evaluation: dict[str, Any], training: dict[str, Any], errors: list[str]
) -> None:
    allowed = {"deterministic", "episodes", "seed", "separate"}
    errors.extend(
        require_keys(
            evaluation,
            allowed=allowed,
            required=allowed,
            path="$.evaluation",
        )
    )
    _boolean(evaluation.get("deterministic"), path="$.evaluation.deterministic", errors=errors)
    _boolean(evaluation.get("separate"), path="$.evaluation.separate", errors=errors)
    _integer(
        evaluation.get("episodes"),
        path="$.evaluation.episodes",
        minimum=1,
        maximum=MAX_EVAL_EPISODES,
        errors=errors,
    )
    _integer(
        evaluation.get("seed"),
        path="$.evaluation.seed",
        minimum=0,
        maximum=2**32 - 1,
        errors=errors,
    )
    if evaluation.get("separate") is not True:
        errors.append("$.evaluation.separate must be true")
    if evaluation.get("seed") == training.get("seed"):
        errors.append("training and evaluation seeds must differ")


def _validate_logging(
    logging: dict[str, Any], profile: str, errors: list[str]
) -> None:
    allowed = {
        "backend",
        "disclosure_ack",
        "external_opt_in",
        "upload_checkpoints",
    }
    errors.extend(
        require_keys(logging, allowed=allowed, required=allowed, path="$.logging")
    )
    backend = logging.get("backend")
    if backend not in LOGGER_CREDENTIAL_ENV:
        errors.append("$.logging.backend must be none, wandb, or neptune")
        return
    if backend == "neptune":
        errors.append("Neptune hosted service shut down on 2026-03-05; use local logging")
    opt_in = _boolean(
        logging.get("external_opt_in"),
        path="$.logging.external_opt_in",
        errors=errors,
    )
    disclosure = _boolean(
        logging.get("disclosure_ack"),
        path="$.logging.disclosure_ack",
        errors=errors,
    )
    upload = _boolean(
        logging.get("upload_checkpoints"),
        path="$.logging.upload_checkpoints",
        errors=errors,
    )
    if backend == "none" and any(value is True for value in (opt_in, disclosure, upload)):
        errors.append("external logging flags must be false when backend is none")
    if backend != "none" and (opt_in is not True or disclosure is not True):
        errors.append(
            "external logging requires external_opt_in=true and disclosure_ack=true"
        )
    if backend == "wandb" and upload is not True:
        errors.append(
            "reviewed upstream W&B training uploads model artifacts at close; "
            "upload_checkpoints=true is required (no supported CLI upload opt-out)"
        )


def _validate_checkpoint(checkpoint: dict[str, Any], errors: list[str]) -> None:
    allowed = {"format", "trusted_only"}
    errors.extend(
        require_keys(
            checkpoint,
            allowed=allowed,
            required=allowed,
            path="$.checkpoint",
        )
    )
    if checkpoint.get("format") not in {"state_dict", "native-bin", "opaque"}:
        errors.append("$.checkpoint.format is invalid")
    if checkpoint.get("trusted_only") is not True:
        errors.append("$.checkpoint.trusted_only must be true")


def validate_plan(plan: Any) -> list[str]:
    """Return all deterministic schema and safety errors."""
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["$ must be an object"]
    secret_paths = secret_key_paths(plan)
    if secret_paths:
        errors.append(
            "credential-bearing keys are forbidden in plans: " + ", ".join(secret_paths)
        )
    top_allowed = {
        "checkpoint",
        "environment",
        "evaluation",
        "logging",
        "package",
        "profile",
        "schema_version",
        "training",
        "vectorization",
    }
    errors.extend(
        require_keys(
            plan,
            allowed=top_allowed,
            required=top_allowed,
            path="$",
        )
    )
    if plan.get("schema_version") != 1:
        errors.append("$.schema_version must equal 1")
    profile = plan.get("profile")
    if profile not in PROFILES:
        errors.append(f"$.profile must be one of {PROFILES}")
        return errors

    package = _mapping(plan.get("package"), "$.package", errors)
    environment = _mapping(plan.get("environment"), "$.environment", errors)
    training = _mapping(plan.get("training"), "$.training", errors)
    vectorization = _mapping(plan.get("vectorization"), "$.vectorization", errors)
    evaluation = _mapping(plan.get("evaluation"), "$.evaluation", errors)
    logging = _mapping(plan.get("logging"), "$.logging", errors)
    checkpoint = _mapping(plan.get("checkpoint"), "$.checkpoint", errors)

    _validate_package(package, profile, errors)
    _validate_environment(environment, errors)
    if profile == "source-4.0" and environment.get("adapter") in {"gymnasium", "pettingzoo"}:
        errors.append("source-4.0 has no Gymnasium/PettingZoo emulation adapter")
    _validate_training(training, errors)
    _validate_vectorization(vectorization, profile, training, errors)
    _validate_evaluation(evaluation, training, errors)
    _validate_logging(logging, profile, errors)
    _validate_checkpoint(checkpoint, errors)
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a strict local JSON plan. With no --config, validate the "
            "bounded built-in dry-run plan."
        )
    )
    parser.add_argument("--config", help="Explicit JSON file beneath --root")
    parser.add_argument("--root", default=".", help="Allowed local path root")
    parser.add_argument("--profile", choices=PROFILES, default="pypi-3.0.0")
    parser.add_argument("--compact", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        plan = (
            load_json_object(args.config, root=args.root)
            if args.config
            else default_plan(args.profile)
        )
        errors = validate_plan(plan)
        report = {
            "errors": errors,
            "network_used": False,
            "plan": copy.deepcopy(plan),
            "status": "valid" if not errors else "invalid",
        }
    except UserInputError as exc:
        report = {
            "errors": [str(exc)],
            "network_used": False,
            "plan": None,
            "status": "invalid",
        }
    emit_json(report, pretty=not args.compact)
    return 0 if report["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
