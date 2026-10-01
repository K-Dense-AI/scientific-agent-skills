#!/usr/bin/env python3
"""Plan bounded inference batches from numbers or a JSON model card only."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any

from _common import (
    CliError,
    MAX_JSON_BYTES,
    emit_json,
    finite_float,
    load_json_object,
    run_cli,
    validate_keys,
)


DTYPE_BYTES = {
    "uint8": 1,
    "int8": 1,
    "float16": 2,
    "bfloat16": 2,
    "float32": 4,
    "float64": 8,
}
MODEL_SUFFIXES = {
    ".bin",
    ".ckpt",
    ".joblib",
    ".onnx",
    ".pickle",
    ".pkl",
    ".pt",
    ".pth",
    ".safetensors",
}
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def _load_card(path: str | None, root: str) -> dict[str, Any]:
    if path is None:
        return {}
    if Path(path).suffix.lower() in MODEL_SUFFIXES:
        raise CliError(
            "--model-card accepts JSON metadata only; model/checkpoint files "
            "are intentionally never loaded"
        )
    card = load_json_object(path, root=root, max_bytes=MAX_JSON_BYTES)
    validate_keys(
        card,
        allowed={
            "schema_version",
            "model_id",
            "artifact_sha256",
            "input_shape",
            "dtype",
            "output_elements_per_tile",
            "activation_multiplier",
            "parameter_bytes",
            "runtime_workspace_mib",
        },
        required={"schema_version", "model_id", "input_shape", "dtype"},
        context="model card",
    )
    if card["schema_version"] != "1.0":
        raise CliError("model card schema_version must be '1.0'")
    if not isinstance(card["model_id"], str) or not 1 <= len(card["model_id"]) <= 128:
        raise CliError("model_id must be a nonempty string of at most 128 characters")
    digest = card.get("artifact_sha256")
    if digest is not None and (
        not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest)
    ):
        raise CliError("artifact_sha256 must be exactly 64 hexadecimal characters")
    shape = card["input_shape"]
    if (
        not isinstance(shape, list)
        or len(shape) != 3
        or any(isinstance(value, bool) or not isinstance(value, int) for value in shape)
    ):
        raise CliError("input_shape must be [channels, height, width] integers")
    return card


def _select(cli_value: Any, card: dict[str, Any], card_key: str, default: Any) -> Any:
    return cli_value if cli_value is not None else card.get(card_key, default)


def make_plan(args: argparse.Namespace) -> dict[str, Any]:
    card = _load_card(args.model_card, args.root)
    shape = card.get("input_shape", [3, 256, 256])
    channels = _select(args.channels, card, "channels", shape[0])
    height = _select(args.height, card, "height", shape[1])
    width = _select(args.width, card, "width", shape[2])
    dtype = _select(args.dtype, card, "dtype", "float32")
    output_elements = _select(
        args.output_elements_per_tile,
        card,
        "output_elements_per_tile",
        0,
    )
    activation_multiplier = _select(
        args.activation_multiplier,
        card,
        "activation_multiplier",
        8.0,
    )
    parameter_bytes = _select(
        args.parameter_bytes,
        card,
        "parameter_bytes",
        0,
    )
    runtime_workspace_mib = _select(
        args.runtime_workspace_mib,
        card,
        "runtime_workspace_mib",
        512.0,
    )

    integers = {
        "tile_count": (args.tile_count, 1, 100_000_000),
        "batch_size": (args.batch_size, 1, 1_000_000),
        "channels": (channels, 1, 4096),
        "height": (height, 1, 16384),
        "width": (width, 1, 16384),
        "output_elements_per_tile": (output_elements, 0, 10_000_000_000),
        "parameter_bytes": (parameter_bytes, 0, 10_000_000_000_000),
    }
    checked: dict[str, int] = {}
    for name, (value, minimum, maximum) in integers.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise CliError(f"{name} must be an integer")
        if not minimum <= value <= maximum:
            raise CliError(f"{name} must be between {minimum} and {maximum}")
        checked[name] = value
    if not isinstance(dtype, str) or dtype not in DTYPE_BYTES:
        raise CliError(
            "--dtype must be one of: " + ", ".join(sorted(DTYPE_BYTES))
        )
    activation_multiplier = finite_float(
        activation_multiplier,
        name="activation_multiplier",
        minimum=0,
        maximum=10_000,
    )
    runtime_workspace_mib = finite_float(
        runtime_workspace_mib,
        name="runtime_workspace_mib",
        minimum=0,
        maximum=1_000_000,
    )
    max_memory_mib = finite_float(
        args.max_memory_mib,
        name="max_memory_mib",
        minimum=1,
        maximum=10_000_000,
    )

    bytes_per_element = DTYPE_BYTES[dtype]
    input_elements = checked["channels"] * checked["height"] * checked["width"]
    input_bytes_per_tile = input_elements * bytes_per_element
    output_bytes_per_tile = (
        checked["output_elements_per_tile"] * bytes_per_element
    )
    activation_bytes_per_tile = math.ceil(
        input_bytes_per_tile * activation_multiplier
    )
    variable_bytes_per_tile = (
        input_bytes_per_tile + output_bytes_per_tile + activation_bytes_per_tile
    )
    persistent_bytes = checked["parameter_bytes"] + round(
        runtime_workspace_mib * 1024**2
    )
    memory_budget_bytes = round(max_memory_mib * 1024**2)
    available_variable_bytes = max(0, memory_budget_bytes - persistent_bytes)
    recommended_max_batch = (
        available_variable_bytes // variable_bytes_per_tile
        if variable_bytes_per_tile
        else checked["tile_count"]
    )
    recommended_max_batch = min(recommended_max_batch, checked["tile_count"])
    planned_peak_bytes = persistent_bytes + (
        variable_bytes_per_tile * checked["batch_size"]
    )
    within_memory = planned_peak_bytes <= memory_budget_bytes
    number_of_batches = math.ceil(
        checked["tile_count"] / checked["batch_size"]
    )
    final_batch_size = checked["tile_count"] % checked["batch_size"]
    if final_batch_size == 0:
        final_batch_size = min(checked["batch_size"], checked["tile_count"])

    warnings = [
        "Estimate excludes allocator fragmentation, framework caches, graph "
        "workspace, postprocessing, stitching, and concurrent workers."
    ]
    if not within_memory:
        warnings.append(
            "Requested batch exceeds the planning memory budget; reduce batch "
            "size or change the explicit budget."
        )
    if checked["output_elements_per_tile"] == 0:
        warnings.append(
            "No output tensor size was supplied; output memory is omitted."
        )
    if checked["parameter_bytes"] == 0:
        warnings.append("No parameter size was supplied; model weights are omitted.")

    return {
        "model_card_used": bool(card),
        "model_id": card.get("model_id"),
        "artifact_sha256": card.get("artifact_sha256"),
        "checkpoint_or_model_loaded": False,
        "input_shape_chw": [
            checked["channels"],
            checked["height"],
            checked["width"],
        ],
        "dtype": dtype,
        "bytes_per_element": bytes_per_element,
        "tile_count": checked["tile_count"],
        "requested_batch_size": checked["batch_size"],
        "number_of_batches": number_of_batches,
        "final_batch_size": final_batch_size,
        "input_bytes_per_tile": input_bytes_per_tile,
        "output_bytes_per_tile": output_bytes_per_tile,
        "activation_bytes_per_tile_estimate": activation_bytes_per_tile,
        "persistent_bytes_estimate": persistent_bytes,
        "planned_peak_memory_mib": round(planned_peak_bytes / 1024**2, 6),
        "memory_budget_mib": max_memory_mib,
        "within_memory_budget": within_memory,
        "recommended_max_batch_under_estimate": int(recommended_max_batch),
        "estimated_total_output_gib": round(
            checked["tile_count"] * output_bytes_per_tile / 1024**3,
            6,
        ),
        "warnings": warnings,
        "note": (
            "This planner reads numbers or strict JSON metadata only. It never "
            "opens model/checkpoint artifacts or imports PathML/Torch/ONNX."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan bounded inference batches from dimensions or a strict JSON "
            "model card. Model/checkpoint files are never loaded."
        )
    )
    parser.add_argument("--tile-count", type=int, required=True)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--model-card")
    parser.add_argument("--root", default=".")
    parser.add_argument("--channels", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--width", type=int)
    parser.add_argument("--dtype", choices=sorted(DTYPE_BYTES))
    parser.add_argument("--output-elements-per-tile", type=int)
    parser.add_argument("--activation-multiplier", type=float)
    parser.add_argument("--parameter-bytes", type=int)
    parser.add_argument("--runtime-workspace-mib", type=float)
    parser.add_argument("--max-memory-mib", type=float, default=4096.0)
    parser.add_argument("--output")
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = make_plan(args)
    emit_json(report, output=args.output, root=args.root, force=args.force)


if __name__ == "__main__":
    raise SystemExit(run_cli(main))
