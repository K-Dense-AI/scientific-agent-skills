#!/usr/bin/env python3
"""Generate a reviewable, opt-in FluidSim launch script without running it."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from ._common import (
        ToolError,
        atomic_write,
        checked_input,
        checked_output,
        emit_json,
        fail_json,
        load_json,
    )
    from ._schema import SOLVER_IMPORTS, flatten_parameters, normalized_copy
except ImportError:  # Direct script execution.
    from _common import (
        ToolError,
        atomic_write,
        checked_input,
        checked_output,
        emit_json,
        fail_json,
        load_json,
    )
    from _schema import SOLVER_IMPORTS, flatten_parameters, normalized_copy


TOOL = "fluidsim-simulation-dry-run"


def _literal(value: Any) -> str:
    """Render validated JSON scalars as fixed Python literals."""

    if value is None or isinstance(value, (bool, int, float, str)):
        return repr(value)
    raise ToolError("only JSON scalar parameter values can be rendered")


def render_script(config: dict[str, Any]) -> str:
    """Render a script with a dry-run default and explicit execution gate."""

    config = normalized_copy(config)
    init_type = config["parameters"].get("init_fields", {}).get("type")
    if init_type in {"in_script", "from_simul"}:
        raise ToolError("in_script/from_simul initialization requires a separately implemented scientific script")
    forcing = config["parameters"].get("forcing", {})
    if forcing.get("enable") and forcing.get("type") in {"in_script", "in_script_coarse", "pseudo_spectral"}:
        raise ToolError("this forcing requires an explicitly implemented forcing callback")
    restart = config["provenance"].get("restart")
    if init_type == "from_file":
        if not restart or restart["path"] != config["parameters"]["init_fields"]["from_file"]["path"]:
            raise ToolError("from_file requires matching restart path and SHA-256 provenance")
    solver = config["solver"]
    module_name = SOLVER_IMPORTS[solver]
    assignments = []
    for path, value in flatten_parameters(config["parameters"]):
        dotted = ".".join(("params", *path))
        assignments.append(f"    {dotted} = {_literal(value)}")

    resources = config["resources"]
    execution = config["execution"]
    provenance = config["provenance"]
    plan = {
        "config_id": provenance["config_id"],
        "cpu_cores": resources["cpu_cores"],
        "disk_gib": resources["disk_gib"],
        "fluidfft": provenance["fluidfft"],
        "fluidsim": provenance["fluidsim"],
        "max_output_files": resources["max_output_files"],
        "mode": execution["mode"],
        "mpi_ranks": resources["mpi_ranks"],
        "output_root": execution["output_root"],
        "ram_gib": resources["ram_gib"],
        "solver": solver,
        "threads_per_rank": resources["threads_per_rank"],
        "wall_time_minutes": resources["wall_time_minutes"],
    }
    plan_json = json.dumps(plan, allow_nan=False, sort_keys=True)
    assignment_block = "\n".join(assignments)
    expected_ranks = int(resources["mpi_ranks"])
    return f'''#!/usr/bin/env python3
"""Generated FluidSim {provenance["fluidsim"]} plan. Dry-run unless explicitly approved."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from importlib.metadata import version
from pathlib import Path


PLAN = json.loads({plan_json!r})
CONFIG_ID = {provenance["config_id"]!r}
OUTPUT_ROOT = {execution["output_root"]!r}
EXPECTED_RANKS = {expected_ranks}
MODE = {execution["mode"]!r}
RESTART = {restart!r}


def _detected_mpi_size() -> int:
    for name in ("OMPI_COMM_WORLD_SIZE", "PMI_SIZE", "PMIX_SIZE", "MPI_LOCALNRANKS"):
        value = os.environ.get(name)
        if value and value.isdecimal():
            return int(value)
    return 1


def _prepare_output_root() -> Path:
    base = Path(__file__).resolve().parent
    destination = base / OUTPUT_ROOT
    if destination.exists() and destination.is_symlink():
        raise RuntimeError("refusing a symlink output root")
    destination.mkdir(mode=0o700, exist_ok=True)
    resolved = destination.resolve(strict=True)
    if resolved.parent != base:
        raise RuntimeError("output root escaped the script directory")
    os.environ["FLUIDSIM_PATH"] = str(resolved)
    return resolved


def run() -> None:
    size = _detected_mpi_size()
    if MODE == "serial" and size != 1:
        raise RuntimeError("serial plan detected an MPI launcher")
    if MODE == "mpi-preview" and size != EXPECTED_RANKS:
        raise RuntimeError("launch manually with exactly the reviewed MPI rank count")
    for package in ("fluidsim", "fluidfft"):
        if version(package) != PLAN[package]:
            raise RuntimeError("installed package version differs from the reviewed plan: " + package)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = {str(resources["threads_per_rank"])!r}
    restart_path = None
    if RESTART:
        base = Path(__file__).resolve().parent
        restart_path = base / RESTART["path"]
        for part in (restart_path, *restart_path.parents):
            if part.is_symlink():
                raise RuntimeError("restart path contains a symlink")
        restart_path = restart_path.resolve(strict=True)
        if not restart_path.is_relative_to(base):
            raise RuntimeError("restart path escaped the script directory")
        if not restart_path.is_file() or restart_path.stat().st_nlink != 1:
            raise RuntimeError("restart must be a singly linked regular file")
        if restart_path.stat().st_size > 8 * 1024**3:
            raise RuntimeError("restart exceeds the reviewed eight-GiB hash limit")
        digest = hashlib.sha256()
        with restart_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024**2), b""):
                digest.update(chunk)
        if digest.hexdigest() != RESTART["sha256"]:
            raise RuntimeError("restart SHA-256 differs from the reviewed checkpoint")
    _prepare_output_root()

    import numpy as np
    from {module_name} import Simul
    from fluiddyn.util import mpi

    if mpi.nb_proc != EXPECTED_RANKS:
        raise RuntimeError("actual MPI rank count differs from the reviewed plan")

    np.random.seed({int(execution["random_seed"])})
    params = Simul.create_default_params()
{assignment_block}
    if restart_path is not None:
        params.init_fields.from_file.path = str(restart_path)
    sim = Simul(params)
    sim.time_stepping.start()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--acknowledge-config-id")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({{"dry_run": True, "plan": PLAN}}, indent=2, sort_keys=True))
        return 0
    if args.acknowledge_config_id != CONFIG_ID:
        parser.error("--execute requires the exact reviewed --acknowledge-config-id")
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def build_plan(config: dict[str, Any], script: str) -> dict[str, Any]:
    execution = config["execution"]
    resources = config["resources"]
    execute_argv = [
        "<python>",
        execution["script_name"],
        "--execute",
        "--acknowledge-config-id",
        config["provenance"]["config_id"],
    ]
    mpi_preview = None
    if execution["mode"] == "mpi-preview":
        mpi_preview = [
            "<site-mpi-launcher>",
            "-n",
            str(resources["mpi_ranks"]),
            *execute_argv,
        ]
    return {
        "approval_gate": [
            "review the validated scientific assumptions and acceptance criteria",
            "review the resource estimate against CPU, RAM, disk, wall-time, and file limits",
            "verify FFT/MPI backend on the target host with a tiny pilot",
            "record the config, script, lock, environment, and restart hashes",
        ],
        "commands_executed": False,
        "dry_run": True,
        "execute_argv_after_approval": execute_argv,
        "job_submitted": False,
        "mpi_launch_preview_only": mpi_preview,
        "mpi_launched": False,
        "network_used": False,
        "physical_validity_established": False,
        "script": script,
        "script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "tool": TOOL,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate an opt-in FluidSim script from validated local JSON. The "
            "generator never imports FluidSim, invokes MPI, submits a job, or runs code."
        )
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--output",
        help="Optional .py file within --root; parent must exist.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow replacement of an existing regular output file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config_path = checked_input(
            args.config,
            root=args.root,
            kind="file",
            suffixes={".json"},
        )
        config = normalized_copy(load_json(config_path))
        script = render_script(config)
        report = build_plan(config, script)
        if args.output:
            output = checked_output(
                args.output,
                root=args.root,
                suffixes={".py"},
                force=args.force,
            )
            atomic_write(output, script.encode("utf-8"), force=args.force)
            report["script"] = None
            report["script_written"] = output.name
        else:
            report["script_written"] = None
        emit_json(report)
        return 0
    except (OSError, ToolError, UnicodeError) as exc:
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    raise SystemExit(main())
