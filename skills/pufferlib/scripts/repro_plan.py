#!/usr/bin/env python3
"""Generate a bounded reproducibility and held-out evaluation plan."""

from __future__ import annotations

import argparse
from typing import Any

try:
    from ._common import (
        SOURCE_4_COMMIT,
        STABLE_SDIST_SHA256,
        UserInputError,
        bounded_int,
        emit_json,
        validate_slug,
    )
    from .validate_plan import PROFILES
except ImportError:  # Direct script execution.
    from _common import (
        SOURCE_4_COMMIT,
        STABLE_SDIST_SHA256,
        UserInputError,
        bounded_int,
        emit_json,
        validate_slug,
    )
    from validate_plan import PROFILES


def generate_plan(
    *,
    profile: str,
    environment: str,
    base_seed: int,
    replicates: int,
    eval_episodes: int,
    benchmark_repeats: int,
) -> dict[str, Any]:
    """Create non-overlapping train/eval seeds and reporting requirements."""
    train_seeds = [base_seed + index for index in range(replicates)]
    eval_seed_base = base_seed + 1_000_000
    eval_seeds = [eval_seed_base + index for index in range(replicates)]
    if set(train_seeds) & set(eval_seeds):
        raise UserInputError("training and evaluation seeds overlap")

    if profile == "pypi-3.0.0":
        upstream = {
            "artifact": "pufferlib-3.0.0.tar.gz",
            "package": "pufferlib==3.0.0",
            "python": ">=3.9",
            "sha256": STABLE_SDIST_SHA256,
            "warning": (
                "PyPI provides only an sdist. Its build can download and compile native "
                "dependencies; audit and sandbox the build before installation."
            ),
        }
    else:
        upstream = {
            "commit": SOURCE_4_COMMIT,
            "package": "pufferlib source 4.0",
            "python": ">=3.10",
            "torch": ">=2.9",
            "warning": (
                "The historical 4.0 snapshot is not current native 5.0 or a PyPI artifact. Pin the "
                "commit and use an audited CUDA/CPU build environment."
            ),
        }

    return {
        "benchmarking": {
            "aggregate": ["median", "p10", "p90"],
            "exclude_setup": False,
            "fixed_workload": True,
            "record": [
                "CPU model and logical/physical cores",
                "GPU model, driver, CUDA, and precision when applicable",
                "OS, Python, PufferLib, NumPy, Gymnasium, and PyTorch versions",
                "backend, start method, workers, envs, buffers, and batch size",
                "warmup, repeats, wall time, agent steps, and reset count",
            ],
            "repeats": benchmark_repeats,
            "warning": "Do not compare SPS across changed workloads or hardware.",
        },
        "environment": {
            "name": environment,
            "record": [
                "source URL and immutable revision",
                "license and asset/ROM rights",
                "environment and wrapper configuration",
                "observation/action spaces and dtypes",
                "termination, truncation, autoreset, and frame-skip semantics",
            ],
        },
        "evaluation": {
            "checkpoint_selected_without_eval_feedback": True,
            "deterministic_policy_pass": True,
            "episodes_per_seed": eval_episodes,
            "learning_disabled": True,
            "report_per_seed_and_aggregate": True,
            "seeds": eval_seeds,
            "separate_environment_instances": True,
            "stochastic_policy_pass": True,
        },
        "network_used": False,
        "profile": profile,
        "provenance": {
            "checkpoint_sha256_required": True,
            "dependency_lock_required": True,
            "record_git_diff": True,
            "record_source_commit": True,
            "upstream": upstream,
        },
        "schema_version": 1,
        "training": {
            "determinism_limitations_recorded": True,
            "seeds": train_seeds,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Emit a local reproducibility/evaluation plan; no packages, checkpoints, "
            "environments, GPU, or network services are opened."
        )
    )
    parser.add_argument("--profile", choices=PROFILES, default="pypi-3.0.0")
    parser.add_argument("--environment", default="synthetic")
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--replicates", type=int, default=3, help="1..32")
    parser.add_argument("--eval-episodes", type=int, default=100, help="1..10000")
    parser.add_argument("--benchmark-repeats", type=int, default=5, help="3..20")
    parser.add_argument("--compact", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        environment = validate_slug(args.environment, name="environment")
        base_seed = bounded_int(
            args.base_seed, name="base_seed", minimum=0, maximum=2**32 - 1_000_033
        )
        replicates = bounded_int(
            args.replicates, name="replicates", minimum=1, maximum=32
        )
        eval_episodes = bounded_int(
            args.eval_episodes,
            name="eval_episodes",
            minimum=1,
            maximum=10_000,
        )
        repeats = bounded_int(
            args.benchmark_repeats,
            name="benchmark_repeats",
            minimum=3,
            maximum=20,
        )
        plan = generate_plan(
            profile=args.profile,
            environment=environment,
            base_seed=base_seed,
            replicates=replicates,
            eval_episodes=eval_episodes,
            benchmark_repeats=repeats,
        )
    except (UserInputError, ValueError) as exc:
        parser.error(str(exc))
    emit_json(plan, pretty=not args.compact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
