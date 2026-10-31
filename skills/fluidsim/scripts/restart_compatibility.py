#!/usr/bin/env python3
"""Check FluidSim restart metadata against a validated target configuration."""

from __future__ import annotations

import argparse
import math
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

try:
    from ._common import (
        GIB,
        ToolError,
        bounded_int,
        checked_input,
        checked_root,
        emit_json,
        fail_json,
        finite_float,
        iter_local_files,
        load_json,
        relative_display,
        sha256_file,
        validate_keys,
    )
    from ._schema import FLUIDSIM_VERSION, SOLVER_IMPORTS, normalized_copy
    from ._profiles import PROFILES
except ImportError:  # Direct script execution.
    from _common import (
        GIB,
        ToolError,
        bounded_int,
        checked_input,
        checked_root,
        emit_json,
        fail_json,
        finite_float,
        iter_local_files,
        load_json,
        relative_display,
        sha256_file,
        validate_keys,
    )
    from _schema import FLUIDSIM_VERSION, SOLVER_IMPORTS, normalized_copy
    from _profiles import PROFILES


TOOL = "fluidsim-restart-compatibility"
_MODULE_TO_SOLVER = {module: key for key, module in SOLVER_IMPORTS.items()}
_STATE_SUFFIXES = (".nc", ".h5", ".hdf5")
_COMPATIBLE_OPER_KEYS = ("nx", "ny", "nz", "Lx", "Ly", "Lz")
_PHYSICS_KEYS = ("N", "beta", "c2", "f", "nu_2", "nu_4", "nu_8", "nu_m4")


def _safe_scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")[:500]
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            finite_float(value, name="restart metadata")
        return value if not isinstance(value, str) else value[:500]
    return None


def _attrs(group: Any, names: tuple[str, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in names:
        if name not in group.attrs:
            continue
        identifier = group.attrs.get_id(name)
        if identifier.shape != ():
            continue
        value = _safe_scalar(group.attrs[name])
        if value is not None:
            result[name] = value
    return result


def _find_state_file(path: Path) -> Path:
    if path.is_file():
        return path
    candidates = [
        item
        for item in iter_local_files(
            path, suffixes=_STATE_SUFFIXES, max_files=256, recursive=False
        )
        if item.name.casefold().startswith("state_phys")
    ]
    if not candidates:
        raise ToolError("no state_phys .nc/.h5 file found in restart directory")
    ranked = []
    for candidate in candidates:
        state = load_hdf5_state(candidate, digest_limit=0)["state"]
        time, iteration = state["time"], state["iteration"]
        if not isinstance(time, (int, float)) or not math.isfinite(time):
            raise ToolError("checkpoint time is missing/nonfinite; select and inspect an explicit file")
        if not isinstance(iteration, int) or isinstance(iteration, bool) or iteration < 0:
            raise ToolError("checkpoint iteration is missing/invalid")
        ranked.append((time, iteration, candidate))
    ranked.sort()
    if len(ranked) > 1 and ranked[-1][:2] == ranked[-2][:2]:
        raise ToolError("multiple checkpoints share the latest time/iteration; select an explicit file")
    return ranked[-1][2]


def _hard_child(group: Any, name: str, h5py: Any) -> Any:
    """Access one local object without following a soft/external HDF5 link."""
    link = group.get(name, getlink=True)
    if link is None:
        return None
    if not isinstance(link, h5py.HardLink):
        raise ToolError("restart metadata must not contain soft or external links")
    return group[name]


def load_hdf5_state(path: Path, *, digest_limit: int) -> dict[str, Any]:
    """Read restart metadata and dataset names without reading field arrays."""

    try:
        import h5py  # Lazy optional dependency.
    except ImportError as exc:
        raise ToolError(
            "restart HDF5 inspection requires optional h5py from the pinned environment"
        ) from exc

    try:
        with h5py.File(path, "r") as handle:
            state_group = _hard_child(handle, "state_phys", h5py)
            if not isinstance(state_group, h5py.Group):
                raise ToolError("restart file has no /state_phys group")
            datasets = {}
            for count, name in enumerate(state_group, start=1):
                if count > 128:
                    raise ToolError("restart dataset-count limit exceeded")
                obj = _hard_child(state_group, name, h5py)
                if isinstance(obj, h5py.Dataset):
                    if obj.is_virtual or obj.external:
                        raise ToolError("restart state uses external or virtual dataset storage")
                    datasets[name] = {"shape": list(obj.shape), "dtype": str(obj.dtype), "numeric": obj.dtype.kind in "iufc"}
            state_params = _hard_child(handle, "state_params", h5py)
            forcing_state = _hard_child(state_params, "forcing", h5py) if isinstance(state_params, h5py.Group) else None
            forcing_attrs = _attrs(forcing_state, ("seed0", "seed1", "t_last_change")) if isinstance(forcing_state, h5py.Group) else {}
            state = {
                "datasets": sorted(datasets),
                "dataset_metadata": datasets,
                "iteration": _attrs(state_group, ("it",)).get("it"),
                "state_parameters_present": isinstance(state_params, h5py.Group),
                "forcing_state_complete": (
                    len(forcing_attrs) == 3
                    and all(isinstance(forcing_attrs[key], int) and not isinstance(forcing_attrs[key], bool) and 0 <= forcing_attrs[key] < 2**32 for key in ("seed0", "seed1"))
                    and isinstance(forcing_attrs["t_last_change"], (int, float))
                ),
                "time": _attrs(state_group, ("time",)).get("time"),
            }
            parameters: dict[str, Any] = {}
            solver = None
            source_version = None
            info = _hard_child(handle, "info_simul", h5py)
            if isinstance(info, h5py.Group):
                params_group = _hard_child(info, "params", h5py)
                if isinstance(params_group, h5py.Group):
                    parameters.update(_attrs(params_group, _PHYSICS_KEYS))
                    for child, keys in (
                        ("oper", _COMPATIBLE_OPER_KEYS + ("coef_dealiasing", "type_fft")),
                        (
                            "time_stepping",
                            ("t_end", "it_end", "type_time_scheme"),
                        ),
                        ("forcing", ("enable", "type", "forcing_rate")),
                    ):
                        child_group = _hard_child(params_group, child, h5py)
                        if isinstance(child_group, h5py.Group):
                            parameters[child] = _attrs(child_group, keys)
                solver_group = _hard_child(info, "solver", h5py)
                if isinstance(solver_group, h5py.Group):
                    solver_attrs = _attrs(
                        solver_group,
                        ("module_name", "short_name", "version", "fluidsim"),
                    )
                    module_name = solver_attrs.get("module_name")
                    solver = _MODULE_TO_SOLVER.get(str(module_name), None)
                    source_version = solver_attrs.get(
                        "fluidsim", solver_attrs.get("version")
                    )
    except OSError as exc:
        raise ToolError("restart file is not readable HDF5/netCDF4") from exc

    return {
        "parameters": parameters,
        "provenance": {
            "fluidfft": None,
            "fluidsim": source_version,
            "state_sha256": sha256_file(path, max_bytes=digest_limit),
            "digest_origin": "computed",
        },
        "solver": solver,
        "state": state,
    }


def load_manifest(path: Path) -> dict[str, Any]:
    document = load_json(path)
    if not isinstance(document, Mapping):
        raise ToolError("restart manifest must be a JSON object")
    validate_keys(
        document,
        allowed={"schema_version", "solver", "parameters", "state", "provenance"},
        required={"schema_version", "solver", "parameters", "state", "provenance"},
        context="restart manifest",
    )
    if document["schema_version"] != "1.1":
        raise ToolError("restart manifest schema_version must be '1.1'")
    if not isinstance(document["solver"], str) or document["solver"] not in SOLVER_IMPORTS:
        raise ToolError("restart manifest solver is unknown")
    parameters = document["parameters"]
    state = document["state"]
    provenance = document["provenance"]
    if not all(isinstance(item, Mapping) for item in (parameters, state, provenance)):
        raise ToolError("restart manifest parameters/state/provenance must be objects")
    validate_keys(
        state,
        allowed={"datasets", "dataset_metadata", "forcing_state_complete", "iteration", "state_parameters_present", "time"},
        required={"datasets", "iteration", "state_parameters_present", "time"},
        context="restart manifest state",
    )
    validate_keys(
        provenance,
        allowed={"fluidfft", "fluidsim", "state_sha256"},
        required={"fluidfft", "fluidsim", "state_sha256"},
        context="restart manifest provenance",
    )
    if not isinstance(state["datasets"], list) or not all(
        isinstance(item, str) and 0 < len(item) <= 128 for item in state["datasets"]
    ):
        raise ToolError("restart manifest datasets must be bounded strings")
    if len(state["datasets"]) > 128 or len(set(state["datasets"])) != len(state["datasets"]):
        raise ToolError("restart manifest has too many or duplicate datasets")
    if not isinstance(state["state_parameters_present"], bool):
        raise ToolError("state_parameters_present must be a boolean")
    finite_float(state["time"], name="state.time", minimum=0)
    bounded_int(state["iteration"], name="state.iteration", minimum=0, maximum=2**63-1)
    for key in ("oper", "time_stepping", "forcing"):
        if key in parameters and not isinstance(parameters[key], Mapping):
            raise ToolError(f"restart parameters.{key} must be an object")
    digest = provenance["state_sha256"]
    if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
        raise ToolError("restart manifest state_sha256 must be lowercase SHA-256")
    return {
        "parameters": dict(parameters),
        "provenance": {**provenance, "digest_origin": "manifest"},
        "solver": document["solver"],
        "state": dict(state),
    }


def _same(left: Any, right: Any) -> bool:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        try:
            a, b = float(left), float(right)
        except OverflowError:
            return False
        return math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=1e-12, abs_tol=0.0)
    return left == right


def compare(source: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    def add(target_list: list[dict[str, str]], code: str, message: str) -> None:
        target_list.append({"code": code, "message": message})

    if source.get("solver") is None:
        add(blockers, "missing_solver", "source solver metadata is unavailable")
    elif source["solver"] != target["solver"]:
        add(blockers, "solver_mismatch", "source and target solver keys differ")

    source_params = source.get("parameters", {})
    target_params = target["parameters"]
    source_oper = source_params.get("oper", {})
    target_oper = target_params.get("oper", {})
    for key in _COMPATIBLE_OPER_KEYS:
        if key not in target_oper:
            continue
        if key not in source_oper:
            add(blockers, "missing_grid_metadata", f"source oper.{key} is unavailable")
        elif not _same(source_oper[key], target_oper[key]):
            add(
                blockers,
                "grid_or_domain_mismatch",
                f"oper.{key} differs; use the reviewed resolution-change workflow",
            )
    for key in ("coef_dealiasing", "type_fft"):
        if key in source_oper and key in target_oper and not _same(
            source_oper[key], target_oper[key]
        ):
            add(
                warnings,
                "operator_change",
                f"oper.{key} changes across restart and requires justification",
            )

    for key in _PHYSICS_KEYS:
        if key in source_params and key in target_params and not _same(
            source_params[key], target_params[key]
        ):
            add(
                warnings,
                "physics_parameter_change",
                f"{key} changes across restart; reassess equations and budgets",
            )

    source_state = source.get("state", {})
    if not source_state.get("datasets"):
        add(blockers, "empty_state", "source contains no state datasets")
    needed = PROFILES[target["solver"]]["required_state"]
    metadata = source_state.get("dataset_metadata", {})
    shape = [target_oper[f"n{axis}"] for axis in ("z", "y", "x") if f"n{axis}" in target_oper]
    for key in needed:
        if key not in source_state.get("datasets", []):
            add(blockers, "missing_state_variable", f"required state variable {key} is absent")
        entry = metadata.get(key) if isinstance(metadata, Mapping) else None
        if not isinstance(entry, Mapping) or entry.get("shape") != shape or entry.get("numeric") is not True:
            add(blockers, "state_shape_or_dtype", f"{key} must have a verified numeric dataset with shape {shape}")
    source_time = source_state.get("time")
    target_end = target_params["time_stepping"].get("t_end")
    if isinstance(source_time, (int, float)) and math.isfinite(source_time) and isinstance(target_end, (int, float)):
        if float(target_end) <= float(source_time):
            add(blockers, "nonadvancing_end_time", "target t_end does not exceed state time")
    else:
        add(blockers, "missing_time", "source time or target t_end is unavailable/nonfinite")

    init = target_params.get("init_fields", {})
    if init.get("type") != "from_file":
        add(
            blockers,
            "target_not_from_file",
            "target init_fields.type must be 'from_file' for this restart plan",
        )

    source_provenance = source.get("provenance", {})
    source_version = source_provenance.get("fluidsim")
    if source_version is None:
        add(
            warnings,
            "missing_source_version",
            "source FluidSim version is unavailable; do not assume migration compatibility",
        )
    elif source_version != FLUIDSIM_VERSION:
        add(
            warnings,
            "version_migration",
            "source version differs from 0.9.0; review release notes and merge_missing_params",
        )

    target_restart = target["provenance"].get("restart")
    if not isinstance(target_restart, Mapping):
        add(blockers, "missing_restart_provenance", "target provenance.restart is required")
    else:
        if target_restart.get("path") != init.get("from_file", {}).get("path"):
            add(blockers, "restart_path_mismatch", "provenance.restart.path and init_fields.from_file.path differ")
        expected_digest = target_restart.get("sha256")
        observed_digest = source_provenance.get("state_sha256")
        if observed_digest is None:
            add(
                blockers,
                "digest_not_checked",
                "source state exceeded the hash bound or lacks a manifest digest",
            )
        elif expected_digest != observed_digest:
            add(blockers, "digest_mismatch", "restart SHA-256 does not match target provenance")

    forcing = target_params.get("forcing", {})
    if (
        forcing.get("enable")
        and forcing.get("type", "").startswith("tcrandom")
        and source_state.get("forcing_state_complete") is not True
    ):
        add(
            blockers,
            "forcing_state_missing",
            "time-correlated forcing restart lacks seed0/seed1/t_last_change in /state_params/forcing",
        )

    return {
        "blockers": blockers,
        "compatible_for_mechanical_restart": not blockers,
        "numerical_convergence_established": False,
        "ok": not blockers,
        "physical_validity_established": False,
        "source": {
            "dataset_count": len(source_state.get("datasets", [])),
            "fluidfft": source_provenance.get("fluidfft"),
            "fluidsim": source_version,
            "iteration": source_state.get("iteration"),
            "sha256_checked": source_provenance.get("digest_origin") == "computed" and source_provenance.get("state_sha256") is not None,
            "digest_origin": source_provenance.get("digest_origin", "manifest"),
            "solver": source.get("solver"),
            "state_parameters_present": source_state.get(
                "state_parameters_present"
            ),
            "time": source_time,
        },
        "target": {
            "fluidfft": target["provenance"]["fluidfft"],
            "fluidsim": target["provenance"]["fluidsim"],
            "solver": target["solver"],
            "t_end": target_end,
        },
        "tool": TOOL,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare local restart metadata with validated target JSON. Field arrays "
            "are never loaded; no restart, MPI launch, or job submission occurs."
        )
    )
    parser.add_argument("--source", required=True, help="State file, run directory, or manifest.")
    parser.add_argument("--target-config", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--hash-max-gib",
        type=int,
        default=1,
        help="Hash source state only up to this many GiB, 0..8 (default: 1).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        hash_gib = bounded_int(
            args.hash_max_gib, name="hash_max_gib", minimum=0, maximum=8
        )
        root = checked_root(args.root)
        source_path = checked_input(args.source, root=root, kind="any")
        target_path = checked_input(
            args.target_config,
            root=root,
            kind="file",
            suffixes={".json"},
        )
        target = normalized_copy(load_json(target_path))
        if source_path.is_file() and source_path.name.casefold().endswith(".json"):
            source = load_manifest(source_path)
            selected = source_path
        else:
            selected = _find_state_file(source_path)
            source = load_hdf5_state(
                selected,
                digest_limit=hash_gib * GIB,
            )
        report = compare(source, target)
        report.update(
            {
                "arrays_loaded": False,
                "commands_executed": False,
                "network_used": False,
                "selected_source": relative_display(selected, root),
            }
        )
        emit_json(report)
        return 0 if report["ok"] else 2
    except (OSError, ToolError, UnicodeError) as exc:
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    raise SystemExit(main())
