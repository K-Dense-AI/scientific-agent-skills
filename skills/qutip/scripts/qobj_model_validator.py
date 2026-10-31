#!/usr/bin/env python3
"""Validate a bounded numeric QuTiP model described by strict JSON."""

from __future__ import annotations

import argparse
import math
import re
from collections.abc import Mapping
from typing import Any

from _common import (
    MAX_MODEL_OBJECTS,
    QUTIP_VERSION,
    CliError,
    add_output_arguments,
    bounded_dimensions,
    emit_json,
    finite_float,
    load_json_object,
    load_qutip,
    run_cli,
    validate_keys,
)


ROLES = {"hamiltonian", "initial_state", "collapse_operator", "observable"}
UNIT_CONVENTIONS = {"hbar=1-angular-frequency", "dimensionless-scaled"}
NAME_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}\Z")
MAX_ABS_ENTRY = 1.0e12


def _name(value: Any, *, context: str) -> str:
    if not isinstance(value, str) or not NAME_PATTERN.fullmatch(value):
        raise CliError(
            f"{context} must match {NAME_PATTERN.pattern!r} and be at most 64 characters"
        )
    return value


def _complex_scalar(value: Any, *, name: str) -> complex:
    if isinstance(value, Mapping):
        validate_keys(
            value,
            allowed={"real", "imag"},
            required={"real", "imag"},
            context=name,
        )
        real = finite_float(value["real"], name=f"{name}.real")
        imag = finite_float(value["imag"], name=f"{name}.imag")
        result = complex(real, imag)
    else:
        result = complex(finite_float(value, name=name), 0.0)
    if abs(result) > MAX_ABS_ENTRY:
        raise CliError(f"{name} magnitude exceeds {MAX_ABS_ENTRY}")
    return result


def _numeric_data(
    value: Any,
    *,
    role: str,
    dimension: int,
    context: str,
) -> tuple[list[complex] | list[list[complex]], bool]:
    if not isinstance(value, list) or not value:
        raise CliError(f"{context}.data must be a non-empty JSON array")

    is_matrix = all(isinstance(row, list) for row in value)
    if any(isinstance(row, list) for row in value) and not is_matrix:
        raise CliError(f"{context}.data cannot mix scalar entries and matrix rows")

    if not is_matrix:
        if role != "initial_state":
            raise CliError(f"{context}.data must be a square matrix for role {role}")
        if len(value) != dimension:
            raise CliError(
                f"{context}.data ket length is {len(value)}; expected {dimension}"
            )
        return [
            _complex_scalar(item, name=f"{context}.data[{index}]")
            for index, item in enumerate(value)
        ], True

    if len(value) != dimension:
        raise CliError(
            f"{context}.data has {len(value)} rows; expected {dimension}"
        )
    matrix: list[list[complex]] = []
    for row_index, row in enumerate(value):
        if len(row) != dimension:
            raise CliError(
                f"{context}.data[{row_index}] has {len(row)} entries; "
                f"expected {dimension}"
            )
        matrix.append(
            [
                _complex_scalar(
                    item,
                    name=f"{context}.data[{row_index}][{column_index}]",
                )
                for column_index, item in enumerate(row)
            ]
        )
    return matrix, False


def _state_summary(qobj: Any, *, tolerance: float) -> tuple[dict[str, Any], bool]:
    if qobj.isket:
        norm = float(qobj.norm())
        valid = abs(norm - 1.0) <= tolerance
        return {
            "representation": "ket",
            "norm": norm,
            "normalization_error": abs(norm - 1.0),
            "normalized_within_tolerance": valid,
        }, valid

    trace = complex(qobj.tr())
    hermitian = bool(qobj.isherm)
    if hermitian:
        eigenvalues = [float(value) for value in qobj.eigenenergies()]
        minimum_eigenvalue = min(eigenvalues)
    else:
        minimum_eigenvalue = None
    valid = (
        hermitian
        and abs(trace - 1.0) <= tolerance
        and minimum_eigenvalue is not None
        and minimum_eigenvalue >= -tolerance
    )
    return {
        "representation": "density_matrix",
        "is_hermitian": hermitian,
        "trace": trace,
        "trace_error": abs(trace - 1.0),
        "minimum_eigenvalue": minimum_eigenvalue,
        "positive_within_tolerance": (
            minimum_eigenvalue is not None and minimum_eigenvalue >= -tolerance
        ),
    }, valid


def validate_model(document: Mapping[str, Any], qutip_module: Any | None = None) -> dict[str, Any]:
    """Validate one bounded model and return a portable report."""

    validate_keys(
        document,
        allowed={"schema_version", "unit_convention", "tolerance", "objects"},
        required={"schema_version", "unit_convention", "objects"},
        context="model",
    )
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise CliError("schema_version must be the integer 1")
    convention = document["unit_convention"]
    if convention not in UNIT_CONVENTIONS:
        raise CliError(
            "unit_convention must be one of: "
            + ", ".join(sorted(UNIT_CONVENTIONS))
        )
    tolerance = finite_float(
        document.get("tolerance", 1.0e-9),
        name="tolerance",
        minimum=1.0e-14,
        maximum=1.0e-3,
    )
    objects = document["objects"]
    if not isinstance(objects, list) or not 1 <= len(objects) <= MAX_MODEL_OBJECTS:
        raise CliError(
            f"objects must contain from 1 through {MAX_MODEL_OBJECTS} entries"
        )

    qutip = qutip_module or load_qutip()
    summaries: list[dict[str, Any]] = []
    names: set[str] = set()
    dimensions_seen: list[list[int]] = []
    hamiltonians = 0
    initial_states = 0
    valid = True

    for index, raw in enumerate(objects):
        context = f"objects[{index}]"
        if not isinstance(raw, Mapping):
            raise CliError(f"{context} must be a JSON object")
        validate_keys(
            raw,
            allowed={"name", "role", "dims", "data", "rate"},
            required={"name", "role", "dims", "data"},
            context=context,
        )
        name = _name(raw["name"], context=f"{context}.name")
        if name in names:
            raise CliError(f"object names must be unique; duplicate {name!r}")
        names.add(name)
        role = raw["role"]
        if role not in ROLES:
            raise CliError(f"{context}.role must be one of: {', '.join(sorted(ROLES))}")
        dimensions = bounded_dimensions(raw["dims"], name=f"{context}.dims")
        dimension = math.prod(dimensions)
        dimensions_seen.append(dimensions)
        data, is_ket = _numeric_data(
            raw["data"],
            role=role,
            dimension=dimension,
            context=context,
        )
        if is_ket:
            qobj = qutip.Qobj(
                data,
                dims=[dimensions, [1] * len(dimensions)],
            )
        else:
            qobj = qutip.Qobj(data, dims=[dimensions, dimensions])

        summary: dict[str, Any] = {
            "name": name,
            "role": role,
            "dims": qobj.dims,
            "shape": list(qobj.shape),
            "qobj_type": qobj.type,
        }

        object_valid = True
        if role == "hamiltonian":
            hamiltonians += 1
            if "rate" in raw:
                raise CliError(f"{context}.rate is valid only for collapse_operator")
            object_valid = bool(qobj.isoper and qobj.isherm)
            summary["is_hermitian"] = bool(qobj.isherm)
        elif role == "initial_state":
            initial_states += 1
            if "rate" in raw:
                raise CliError(f"{context}.rate is valid only for collapse_operator")
            state_summary, object_valid = _state_summary(
                qobj,
                tolerance=tolerance,
            )
            summary.update(state_summary)
        elif role == "observable":
            if "rate" in raw:
                raise CliError(f"{context}.rate is valid only for collapse_operator")
            object_valid = bool(qobj.isoper and qobj.isherm)
            summary["is_hermitian"] = bool(qobj.isherm)
        else:
            if is_ket:
                raise CliError(f"{context}.data must be an operator matrix")
            if "rate" not in raw:
                raise CliError(f"{context}.rate is required for collapse_operator")
            rate = finite_float(
                raw["rate"],
                name=f"{context}.rate",
                minimum=0.0,
                maximum=10_000.0,
            )
            scaled = math.sqrt(rate) * qobj
            object_valid = bool(qobj.isoper)
            summary.update(
                {
                    "rate": rate,
                    "scaling": "sqrt(rate) * operator",
                    "scaled_operator_norm": float(scaled.norm()),
                }
            )

        summary["valid"] = object_valid
        valid = valid and object_valid
        summaries.append(summary)

    if hamiltonians != 1:
        raise CliError(f"model must contain exactly one hamiltonian; found {hamiltonians}")
    if initial_states != 1:
        raise CliError(
            f"model must contain exactly one initial_state; found {initial_states}"
        )

    reference_dims = dimensions_seen[0]
    compatible_dims = all(item == reference_dims for item in dimensions_seen)
    valid = valid and compatible_dims

    return {
        "report_type": "qutip.qobj_model_validation",
        "schema_version": 1,
        "qutip_version": QUTIP_VERSION,
        "unit_convention": convention,
        "tolerance": tolerance,
        "limits": {
            "hilbert_dimension": 64,
            "model_objects": MAX_MODEL_OBJECTS,
        },
        "checks": {
            "exactly_one_hamiltonian": True,
            "exactly_one_initial_state": True,
            "all_dimensions_compatible": compatible_dims,
            "numeric_data_only": True,
            "collapse_rates_nonnegative": True,
        },
        "objects": summaries,
        "valid": valid,
        "interpretation": (
            "Structural/numerical preflight only; physical assumptions and "
            "approximation validity require independent review."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a bounded strict-JSON QuTiP model containing one "
            "Hamiltonian, one initial state, and optional collapse/observable objects."
        )
    )
    parser.add_argument("model", help="local strict-JSON model path")
    add_output_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    document = load_json_object(args.model)
    report = validate_model(document)
    emit_json(report, output=args.output, force=args.force)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(run_cli(main))
