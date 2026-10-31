#!/usr/bin/env python3
"""Static FluidSim 0.9 configuration schema and scientific guardrails."""

from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

try:
    from ._profiles import PROFILES
    from ._common import (
        MAX_CPU_CORES,
        MAX_DIMENSION,
        MAX_GRID_POINTS,
        MAX_OUTPUT_FILES,
        MAX_WALL_MINUTES,
        ToolError,
        bounded_int,
        finite_float,
        require_mapping,
        require_text,
        require_text_list,
        safe_relative_path,
        safe_slug,
        validate_keys,
    )
except ImportError:  # Direct script execution.
    from _profiles import PROFILES
    from _common import (
        MAX_CPU_CORES,
        MAX_DIMENSION,
        MAX_GRID_POINTS,
        MAX_OUTPUT_FILES,
        MAX_WALL_MINUTES,
        ToolError,
        bounded_int,
        finite_float,
        require_mapping,
        require_text,
        require_text_list,
        safe_relative_path,
        safe_slug,
        validate_keys,
    )


FLUIDSIM_VERSION = "0.9.0"
FLUIDFFT_VERSION = "0.4.5"
PYFFTW_VERSION = "0.15.1"
MPI4PY_VERSION = "4.1.2"
REVIEW_DATE = "2026-10-01"

# Static allowlist from FluidSim 0.9.0 pyproject entry points. No module name is
# ever derived from user text.
SOLVER_IMPORTS = {
    "ad1d": "fluidsim.solvers.ad1d.solver",
    "ad1d.pseudo_spect": "fluidsim.solvers.ad1d.pseudo_spect.solver",
    "burgers1d": "fluidsim.solvers.burgers1d.solver",
    "burgers1d.skew_sym": "fluidsim.solvers.burgers1d.skew_sym.solver",
    "models0d.lorenz": "fluidsim.solvers.models0d.lorenz.solver",
    "models0d.predaprey": "fluidsim.solvers.models0d.predaprey.solver",
    "nl1d": "fluidsim.solvers.nl1d.solver",
    "ns2d": "fluidsim.solvers.ns2d.solver",
    "ns2d.bouss": "fluidsim.solvers.ns2d.bouss.solver",
    "ns2d.strat": "fluidsim.solvers.ns2d.strat.solver",
    "ns3d": "fluidsim.solvers.ns3d.solver",
    "ns3d.bouss": "fluidsim.solvers.ns3d.bouss.solver",
    "ns3d.strat": "fluidsim.solvers.ns3d.strat.solver",
    "plate2d": "fluidsim.solvers.plate2d.solver",
    "sphere.ns2d": "fluidsim.solvers.sphere.ns2d.solver",
    "sphere.sw1l": "fluidsim.solvers.sphere.sw1l.solver",
    "sw1l": "fluidsim.solvers.sw1l.solver",
    "sw1l.exactlin": "fluidsim.solvers.sw1l.exactlin.solver",
    "sw1l.modified": "fluidsim.solvers.sw1l.modified.solver",
    "sw1l.onlywaves": "fluidsim.solvers.sw1l.onlywaves.solver",
    "waves2d": "fluidsim.solvers.waves2d.solver",
}

# These Cartesian pseudospectral solvers share the parameter surface validated
# and rendered by the bundled tools.
CONFIG_SOLVER_DIMENSIONS = {
    "ns2d": 2,
    "ns2d.bouss": 2,
    "ns2d.strat": 2,
    "ns3d": 3,
    "ns3d.bouss": 3,
    "ns3d.strat": 3,
    "plate2d": 2,
    "sw1l": 2,
    "sw1l.exactlin": 2,
    "sw1l.modified": 2,
    "sw1l.onlywaves": 2,
    "waves2d": 2,
}

STATE_FIELD_COUNTS = {
    "ns2d": (3, 2),
    "ns2d.bouss": (4, 3),
    "ns2d.strat": (4, 3),
    "ns3d": (3, 4),
    "ns3d.bouss": (4, 5),
    "ns3d.strat": (4, 5),
    "plate2d": (3, 3),
    "sw1l": (4, 4),
    "sw1l.exactlin": (4, 4),
    "sw1l.modified": (3, 4),
    "sw1l.onlywaves": (3, 4),
    "waves2d": (2, 3),
}

TIME_SCHEMES = {
    "Euler",
    "Euler_phaseshift",
    "Euler_phaseshift_random",
    "RK2",
    "RK2_phaseshift",
    "RK2_phaseshift_exact",
    "RK2_phaseshift_random",
    "RK2_phaseshift_random_split",
    "RK2_trapezoid",
    "RK4",
}
FORCING_TYPES = {
    "in_script",
    "in_script_coarse",
    "pseudo_spectral",
    "proportional",
    "tcrandom",
    "tcrandom_anisotropic",
}
INIT_TYPES = {
    "constant",
    "dipole",
    "from_file",
    "from_simul",
    "in_script",
    "jet",
    "noise",
}
_DURATION = re.compile(r"^(?:\d{1,4}):[0-5]\d:[0-5]\d$")

TOP_LEVEL_KEYS = {
    "schema_version",
    "solver",
    "parameters",
    "scientific",
    "resources",
    "execution",
    "provenance",
}
PARAMETER_KEYS = {
    "NEW_DIR_RESULTS",
    "ONLY_COARSE_OPER",
    "N",
    "beta",
    "c2",
    "f",
    "nu_2",
    "nu_4",
    "nu_8",
    "nu_m4",
    "oper",
    "time_stepping",
    "init_fields",
    "forcing",
    "output",
    "short_name_type_run",
}
OPER_KEYS = {
    "Lx",
    "Ly",
    "Lz",
    "NO_KY0",
    "NO_SHEAR_MODES",
    "coef_dealiasing",
    "nx",
    "ny",
    "nz",
    "truncation_shape",
    "type_fft",
}
TIME_KEYS = {
    "USE_CFL",
    "USE_T_END",
    "cfl_coef",
    "deltat0",
    "deltat_max",
    "it_end",
    "max_elapsed",
    "phaseshift_random",
    "t_end",
    "type_time_scheme",
}
INIT_KEYS = {"type", "constant", "from_file", "noise"}
FORCING_KEYS = {
    "enable",
    "forcing_rate",
    "key_forced",
    "nkmax_forcing",
    "nkmin_forcing",
    "normalized",
    "random",
    "tcrandom",
    "type",
}
OUTPUT_KEYS = {
    "HAS_TO_SAVE",
    "ONLINE_PLOT_OK",
    "period_refresh_plots",
    "periods_plot",
    "periods_print",
    "periods_save",
    "phys_fields",
    "sub_directory",
}
PERIOD_SAVE_KEYS = {
    "increments",
    "phys_fields",
    "spatial_means",
    "spatiotemporal_spectra",
    "spect_energy_budg",
    "spectra",
    "spectra_multidim",
    "temporal_spectra",
}


def _record(
    target: list[dict[str, str]], code: str, message: str
) -> None:
    target.append({"code": code, "message": message})


def _validate_parameter_structure(parameters: Mapping[str, Any]) -> None:
    validate_keys(
        parameters, allowed=PARAMETER_KEYS, required={"oper", "time_stepping"}, context="parameters"
    )
    nested_specs: tuple[tuple[str, set[str]], ...] = (
        ("oper", OPER_KEYS),
        ("time_stepping", TIME_KEYS),
        ("init_fields", INIT_KEYS),
        ("forcing", FORCING_KEYS),
        ("output", OUTPUT_KEYS),
    )
    for name, keys in nested_specs:
        if name in parameters:
            validate_keys(
                require_mapping(parameters[name], context=f"parameters.{name}"),
                allowed=keys,
                context=f"parameters.{name}",
            )

    init = parameters.get("init_fields", {})
    if "constant" in init:
        validate_keys(
            require_mapping(init["constant"], context="init_fields.constant"),
            allowed={"value"},
            context="init_fields.constant",
        )
    if "from_file" in init:
        validate_keys(
            require_mapping(init["from_file"], context="init_fields.from_file"),
            allowed={"path"},
            context="init_fields.from_file",
        )
    if "noise" in init:
        validate_keys(
            require_mapping(init["noise"], context="init_fields.noise"),
            allowed={"length", "velo_max"},
            context="init_fields.noise",
        )

    forcing = parameters.get("forcing", {})
    nested_forcing = {
        "normalized": {"constant_rate_of", "type", "which_root"},
        "random": {"only_positive"},
        "tcrandom": {"time_correlation"},
    }
    for name, keys in nested_forcing.items():
        if name in forcing:
            validate_keys(
                require_mapping(forcing[name], context=f"forcing.{name}"),
                allowed=keys,
                context=f"forcing.{name}",
            )

    output = parameters.get("output", {})
    for name, keys in (
        ("periods_save", PERIOD_SAVE_KEYS),
        ("periods_print", {"print_stdout"}),
        ("periods_plot", {"phys_fields"}),
        ("phys_fields", {"field_to_plot", "file_with_it"}),
    ):
        if name in output:
            validate_keys(
                require_mapping(output[name], context=f"output.{name}"),
                allowed=keys,
                context=f"output.{name}",
            )

    time = parameters["time_stepping"]
    if "phaseshift_random" in time:
        validate_keys(
            require_mapping(
                time["phaseshift_random"], context="time_stepping.phaseshift_random"
            ),
            allowed={"nb_pairs", "nb_steps_compute_new_pair"},
            context="time_stepping.phaseshift_random",
        )


def validate_config(document: Any) -> dict[str, Any]:
    """Validate a strict FluidSim planning configuration without imports."""

    config = require_mapping(document, context="configuration")
    validate_keys(
        config,
        allowed=TOP_LEVEL_KEYS,
        required=TOP_LEVEL_KEYS,
        context="configuration",
    )
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if config["schema_version"] != "1.1":
        _record(errors, "schema_version", "schema_version must be '1.1'")

    solver = require_text(config["solver"], name="solver", maximum=80)
    if solver not in SOLVER_IMPORTS:
        _record(errors, "unknown_solver", "solver is not a FluidSim 0.9 entry-point key")
    if solver not in CONFIG_SOLVER_DIMENSIONS:
        _record(
            errors,
            "unsupported_parameter_profile",
            "bundled config tools cover Cartesian FluidSim CFD solver profiles only",
        )

    parameters = require_mapping(config["parameters"], context="parameters")
    _validate_parameter_structure(parameters)
    for path, value in flatten_parameters(parameters):
        if not (value is None or isinstance(value, (str, bool, int, float))):
            raise ToolError(f"parameters.{'.'.join(path)} must be a scalar")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            finite_float(value, name=f"parameters.{'.'.join(path)}")
    profile = PROFILES.get(solver)
    if profile:
        for key in {"N", "beta", "c2", "f"} & parameters.keys():
            if key not in profile["physics"]:
                _record(errors, "unsupported_solver_parameter", f"{solver} has no {key} parameter")
        if solver.startswith("ns3d") and "NO_KY0" in parameters["oper"]:
            _record(errors, "unsupported_solver_parameter", f"{solver} has no oper.NO_KY0 parameter")
        if solver == "waves2d" and parameters.get("init_fields", {}).get("noise"):
            _record(errors, "unsupported_solver_parameter", "waves2d noise has a different parameter surface")
        for key in parameters.get("output", {}).get("periods_save", {}):
            if key not in profile["outputs"]:
                _record(errors, "unsupported_solver_output", f"{solver} has no periods_save.{key}")
    oper = require_mapping(parameters["oper"], context="parameters.oper")
    time = require_mapping(
        parameters["time_stepping"], context="parameters.time_stepping"
    )

    dimension = CONFIG_SOLVER_DIMENSIONS.get(solver)
    dimensions: list[int] = []
    if dimension is not None:
        required_axes = ("x", "y", "z")[:dimension]
        for axis in required_axes:
            n_key, length_key = f"n{axis}", f"L{axis}"
            if n_key not in oper or length_key not in oper:
                _record(
                    errors,
                    "incomplete_grid",
                    f"oper requires {n_key} and {length_key} for {solver}",
                )
                continue
            try:
                size = bounded_int(
                    oper[n_key],
                    name=f"oper.{n_key}",
                    minimum=2,
                    maximum=MAX_DIMENSION,
                )
                dimensions.append(size)
                finite_float(
                    oper[length_key], name=f"oper.{length_key}", minimum=1e-15
                )
            except ToolError as exc:
                _record(errors, "invalid_grid", str(exc))
        for axis in ("x", "y", "z")[dimension:]:
            if f"n{axis}" in oper or f"L{axis}" in oper:
                _record(
                    errors,
                    "extra_grid_axis",
                    f"{solver} does not use Cartesian {axis}-axis grid fields",
                )
        if dimensions:
            points = 1
            for size in dimensions:
                points *= size
            if points > MAX_GRID_POINTS:
                _record(errors, "grid_too_large", "grid-point product exceeds hard bound")
    if "coef_dealiasing" not in oper:
        _record(errors, "missing_dealiasing", "oper.coef_dealiasing must be explicit")
    else:
        try:
            coefficient = finite_float(
                oper["coef_dealiasing"],
                name="oper.coef_dealiasing",
                minimum=1e-12,
                maximum=1.0,
            )
            if coefficient is not None and coefficient > 2 / 3 + 1e-12:
                _record(
                    warnings,
                    "dealiasing_above_two_thirds",
                    "justify truncation above 2/3 or use a verified phase-shift scheme",
                )
        except ToolError as exc:
            _record(errors, "invalid_dealiasing", str(exc))
    if not isinstance(oper.get("type_fft", "default"), str):
        _record(errors, "invalid_fft_method", "oper.type_fft must be a string")

    required_time = {
        "USE_CFL",
        "USE_T_END",
        "cfl_coef",
        "deltat0",
        "deltat_max",
        "max_elapsed",
        "t_end",
        "type_time_scheme",
    }
    missing_time = sorted(required_time - set(time))
    if missing_time:
        _record(
            errors,
            "incomplete_time_bounds",
            f"time_stepping must explicitly set: {', '.join(missing_time)}",
        )
    else:
        if not isinstance(time["USE_CFL"], bool) or not isinstance(
            time["USE_T_END"], bool
        ):
            _record(errors, "invalid_time_flags", "USE_CFL and USE_T_END must be booleans")
        try:
            finite_float(time["deltat0"], name="deltat0", minimum=1e-15)
            finite_float(time["deltat_max"], name="deltat_max", minimum=1e-15)
            finite_float(time["t_end"], name="t_end", minimum=0.0)
            if time["USE_CFL"]:
                finite_float(
                    time["cfl_coef"], name="cfl_coef", minimum=1e-6, maximum=2.0
                )
        except ToolError as exc:
            _record(errors, "invalid_time_bound", str(exc))
        if not isinstance(time["max_elapsed"], str) or not _DURATION.fullmatch(
            time["max_elapsed"]
        ):
            _record(
                errors,
                "invalid_max_elapsed",
                "max_elapsed must use bounded HH:MM:SS text",
            )
        if not isinstance(time["type_time_scheme"], str) or time["type_time_scheme"] not in TIME_SCHEMES:
            _record(errors, "unknown_time_scheme", "unsupported FluidSim 0.9 time scheme")
        if not time["USE_T_END"]:
            try:
                bounded_int(time.get("it_end"), name="it_end", minimum=1, maximum=2_000_000)
            except ToolError as exc:
                _record(errors, "iteration_termination", str(exc))
        if isinstance(time["max_elapsed"], str) and _DURATION.fullmatch(time["max_elapsed"]):
            hours, minutes, seconds = map(int, time["max_elapsed"].split(":"))
            wall_minutes = config.get("resources", {}).get("wall_time_minutes") if isinstance(config.get("resources"), Mapping) else None
            elapsed = 3600 * hours + 60 * minutes + seconds
            if elapsed <= 0 or (isinstance(wall_minutes, int) and elapsed > wall_minutes * 60):
                _record(errors, "wall_time_mismatch", "max_elapsed must be positive and within declared wall time")

    for key in ("nu_2", "nu_4", "nu_8", "nu_m4"):
        if key in parameters:
            try:
                finite_float(parameters[key], name=key, minimum=0.0)
            except ToolError as exc:
                _record(errors, "invalid_dissipation", str(exc))

    init = require_mapping(parameters.get("init_fields", {}), context="init_fields")
    init_type = init.get("type")
    if not isinstance(init_type, str) or init_type not in (profile["initializations"] if profile else INIT_TYPES):
        _record(errors, "unknown_initialization", "init_fields.type is not recognized")
    if init_type == "from_file":
        try:
            source = require_mapping(init.get("from_file"), context="from_file")
            safe_relative_path(
                source.get("path"),
                name="init_fields.from_file.path",
                suffixes={".nc", ".h5", ".hdf5"},
                allow_nested=True,
            )
        except ToolError as exc:
            _record(errors, "unsafe_restart_path", str(exc))

    forcing = require_mapping(parameters.get("forcing", {}), context="forcing")
    forcing_enabled = forcing.get("enable", False)
    if not isinstance(forcing_enabled, bool):
        _record(errors, "invalid_forcing_enable", "forcing.enable must be a boolean")
    if forcing_enabled:
        if not isinstance(forcing.get("type"), str) or forcing.get("type") not in (profile["forcing"] if profile else FORCING_TYPES):
            _record(errors, "unknown_forcing", "forcing.type is not recognized")
        for key in ("forcing_rate", "nkmin_forcing", "nkmax_forcing"):
            if key not in forcing:
                _record(errors, "incomplete_forcing", f"forcing.{key} must be explicit")
        try:
            finite_float(
                forcing.get("forcing_rate"), name="forcing_rate", minimum=0.0
            )
            minimum_k = finite_float(
                forcing.get("nkmin_forcing"), name="nkmin_forcing", minimum=0.0
            )
            maximum_k = finite_float(
                forcing.get("nkmax_forcing"), name="nkmax_forcing", minimum=0.0
            )
            if (
                minimum_k is not None
                and maximum_k is not None
                and maximum_k < minimum_k
            ):
                _record(errors, "forcing_band", "nkmax_forcing is below nkmin_forcing")
        except ToolError as exc:
            _record(errors, "invalid_forcing", str(exc))
        if forcing.get("type") == "tcrandom":
            tcrandom = forcing.get("tcrandom")
            if not isinstance(tcrandom, Mapping) or "time_correlation" not in tcrandom:
                _record(
                    errors,
                    "missing_time_correlation",
                    "forcing.tcrandom.time_correlation must be explicit",
                )
            elif tcrandom["time_correlation"] == "based_on_forcing_rate":
                if forcing.get("forcing_rate") == 0:
                    _record(errors, "invalid_forcing", "rate-derived correlation requires positive forcing_rate")
            else:
                try:
                    finite_float(tcrandom["time_correlation"], name="time_correlation", minimum=1e-15)
                except ToolError as exc:
                    _record(errors, "invalid_time_correlation", str(exc))

    output = require_mapping(parameters.get("output", {}), context="output")
    for key in ("HAS_TO_SAVE", "ONLINE_PLOT_OK"):
        if key not in output or not isinstance(output[key], bool):
            _record(errors, "output_flag", f"output.{key} must be an explicit boolean")
    try:
        safe_slug(output.get("sub_directory"), name="output.sub_directory")
    except ToolError as exc:
        _record(errors, "unsafe_output_subdirectory", str(exc))
    periods_save = output.get("periods_save")
    if not isinstance(periods_save, Mapping):
        _record(errors, "missing_output_periods", "output.periods_save must be explicit")
    else:
        for key, value in periods_save.items():
            try:
                finite_float(value, name=f"periods_save.{key}", minimum=0.0)
            except ToolError as exc:
                _record(errors, "invalid_output_period", str(exc))
    if output.get("ONLINE_PLOT_OK"):
        _record(
            warnings,
            "online_plotting",
            "disable online plotting for unattended/HPC runs",
        )
    if output.get("HAS_TO_SAVE") and isinstance(periods_save, Mapping):
        if isinstance(periods_save.get("phys_fields", 0.0), (int, float)) and periods_save.get("phys_fields", 0.0) <= 0:
            _record(
                warnings,
                "no_restart_checkpoint",
                "physical-field saves are disabled, so no new restart checkpoint is planned",
            )

    scientific = require_mapping(config["scientific"], context="scientific")
    scientific_required = {
        "units_or_nondimensionalization",
        "boundary_conditions",
        "initial_conditions",
        "forcing",
        "resolution_and_dealiasing",
        "timestep_and_cfl",
        "conservation_and_budgets",
        "convergence_and_refinement",
        "acceptance_criteria",
    }
    validate_keys(
        scientific,
        allowed=scientific_required,
        required=scientific_required,
        context="scientific",
    )
    for key in scientific_required - {"conservation_and_budgets", "acceptance_criteria"}:
        require_text(scientific[key], name=f"scientific.{key}", maximum=2_000)
    require_text_list(
        scientific["conservation_and_budgets"],
        name="scientific.conservation_and_budgets",
    )
    require_text_list(
        scientific["acceptance_criteria"], name="scientific.acceptance_criteria"
    )
    if "periodic" not in scientific["boundary_conditions"].casefold():
        _record(
            errors,
            "boundary_conditions",
            "Cartesian bundled pseudospectral solver plans must state periodic boundaries",
        )

    resources = require_mapping(config["resources"], context="resources")
    resource_keys = {
        "cpu_cores",
        "mpi_ranks",
        "threads_per_rank",
        "ram_gib",
        "disk_gib",
        "wall_time_minutes",
        "max_output_files",
    }
    validate_keys(
        resources,
        allowed=resource_keys,
        required=resource_keys,
        context="resources",
    )
    try:
        cores = bounded_int(
            resources["cpu_cores"],
            name="cpu_cores",
            minimum=1,
            maximum=MAX_CPU_CORES,
        )
        ranks = bounded_int(
            resources["mpi_ranks"],
            name="mpi_ranks",
            minimum=1,
            maximum=MAX_CPU_CORES,
        )
        threads = bounded_int(
            resources["threads_per_rank"],
            name="threads_per_rank",
            minimum=1,
            maximum=MAX_CPU_CORES,
        )
        finite_float(resources["ram_gib"], name="ram_gib", minimum=0.001)
        finite_float(resources["disk_gib"], name="disk_gib", minimum=0.001)
        bounded_int(
            resources["wall_time_minutes"],
            name="wall_time_minutes",
            minimum=1,
            maximum=MAX_WALL_MINUTES,
        )
        bounded_int(
            resources["max_output_files"],
            name="max_output_files",
            minimum=1,
            maximum=MAX_OUTPUT_FILES,
        )
        if ranks * threads > cores:
            _record(
                errors,
                "cpu_oversubscription",
                "mpi_ranks * threads_per_rank exceeds cpu_cores",
            )
    except ToolError as exc:
        _record(errors, "invalid_resource_bound", str(exc))

    execution = require_mapping(config["execution"], context="execution")
    execution_keys = {"mode", "output_root", "random_seed", "script_name"}
    validate_keys(
        execution,
        allowed=execution_keys,
        required=execution_keys,
        context="execution",
    )
    mode = execution["mode"]
    if not isinstance(mode, str) or mode not in {"serial", "mpi-preview"}:
        _record(errors, "execution_mode", "mode must be serial or mpi-preview")
    try:
        safe_slug(execution["output_root"], name="execution.output_root")
        safe_relative_path(
            execution["script_name"],
            name="execution.script_name",
            suffixes={".py"},
        )
        bounded_int(
            execution["random_seed"],
            name="random_seed",
            minimum=0,
            maximum=2**32 - 1,
        )
    except ToolError as exc:
        _record(errors, "invalid_execution", str(exc))
    if mode == "serial" and resources.get("mpi_ranks") != 1:
        _record(errors, "serial_ranks", "serial mode requires mpi_ranks = 1")
    if mode == "mpi-preview" and isinstance(resources.get("mpi_ranks"), int):
        if resources["mpi_ranks"] < 2:
            _record(errors, "mpi_ranks", "mpi-preview requires at least two ranks")

    provenance = require_mapping(config["provenance"], context="provenance")
    provenance_keys = {
        "config_id",
        "created_utc",
        "dependency_lock_sha256",
        "fluidfft",
        "fluidsim",
        "python",
        "restart",
    }
    validate_keys(
        provenance,
        allowed=provenance_keys,
        required={
            "config_id",
            "created_utc",
            "dependency_lock_sha256",
            "fluidfft",
            "fluidsim",
            "python",
        },
        context="provenance",
    )
    for key in (
        "config_id",
        "created_utc",
        "dependency_lock_sha256",
        "fluidfft",
        "fluidsim",
        "python",
    ):
        require_text(provenance[key], name=f"provenance.{key}", maximum=256)
    if provenance["fluidsim"] != FLUIDSIM_VERSION:
        _record(errors, "fluidsim_version", f"pin fluidsim to {FLUIDSIM_VERSION}")
    if provenance["fluidfft"] != FLUIDFFT_VERSION:
        _record(errors, "fluidfft_version", f"pin fluidfft to {FLUIDFFT_VERSION}")
    if "restart" in provenance:
        restart = require_mapping(provenance["restart"], context="provenance.restart")
        validate_keys(
            restart,
            allowed={"path", "sha256", "source_fluidsim"},
            required={"path", "sha256", "source_fluidsim"},
            context="provenance.restart",
        )
        safe_relative_path(
            restart["path"],
            name="provenance.restart.path",
            suffixes={".nc", ".h5", ".hdf5", ".json"},
            allow_nested=True,
        )
        if not re.fullmatch(r"[0-9a-f]{64}", str(restart["sha256"])):
            _record(errors, "restart_digest", "restart sha256 must be 64 lowercase hex")

    return {
        "errors": errors,
        "numerical_convergence_established": False,
        "ok": not errors,
        "physical_validity_established": False,
        "recognized_solver_keys": sorted(SOLVER_IMPORTS),
        "review_date": REVIEW_DATE,
        "schema_version": "1.1",
        "solver": solver,
        "warnings": warnings,
    }


def example_config() -> dict[str, Any]:
    """Return a bounded pilot configuration used by docs and tests."""

    return {
        "schema_version": "1.1",
        "solver": "ns2d",
        "parameters": {
            "nu_2": 0.001,
            "nu_4": 0.0,
            "nu_8": 0.0,
            "nu_m4": 0.0,
            "oper": {
                "nx": 32,
                "ny": 32,
                "Lx": 6.283185307179586,
                "Ly": 6.283185307179586,
                "coef_dealiasing": 0.6666666666666666,
                "truncation_shape": "cubic",
                "type_fft": "default",
            },
            "time_stepping": {
                "USE_CFL": True,
                "USE_T_END": True,
                "cfl_coef": 0.5,
                "deltat0": 0.001,
                "deltat_max": 0.01,
                "max_elapsed": "00:05:00",
                "t_end": 0.1,
                "type_time_scheme": "RK4",
            },
            "init_fields": {
                "type": "noise",
                "noise": {"length": 0.0, "velo_max": 0.01},
            },
            "forcing": {
                "enable": False,
                "type": "",
                "forcing_rate": 1.0,
                "nkmin_forcing": 4,
                "nkmax_forcing": 5,
                "key_forced": None,
            },
            "output": {
                "HAS_TO_SAVE": True,
                "ONLINE_PLOT_OK": False,
                "sub_directory": "bounded-pilot",
                "periods_save": {
                    "phys_fields": 0.05,
                    "spatial_means": 0.01,
                    "spectra": 0.05,
                    "spect_energy_budg": 0.0,
                    "increments": 0.0,
                    "spectra_multidim": 0.0,
                    "temporal_spectra": 0.0,
                    "spatiotemporal_spectra": 0.0,
                },
                "periods_print": {"print_stdout": 0.01},
                "periods_plot": {"phys_fields": 0.0},
                "phys_fields": {"field_to_plot": "rot", "file_with_it": False},
            },
        },
        "scientific": {
            "units_or_nondimensionalization": (
                "All quantities are nondimensionalized by stated L0 and U0 scales."
            ),
            "boundary_conditions": "Periodic in x and y.",
            "initial_conditions": (
                "Seeded low-amplitude noise; document spectrum and amplitude."
            ),
            "forcing": "No forcing in this pilot.",
            "resolution_and_dealiasing": (
                "32x32 pilot with cubic 2/3 truncation; not a production resolution."
            ),
            "timestep_and_cfl": (
                "Adaptive CFL with cfl_coef=0.5 and deltat_max=0.01."
            ),
            "conservation_and_budgets": [
                "Track energy and enstrophy balances including dissipation.",
                "Check divergence and spectral-tail contamination.",
            ],
            "convergence_and_refinement": (
                "Repeat at finer grids and smaller CFL/deltat_max before inference."
            ),
            "acceptance_criteria": [
                "No unexplained budget residual trend.",
                "Reported observables stable under planned refinement.",
            ],
        },
        "resources": {
            "cpu_cores": 1,
            "mpi_ranks": 1,
            "threads_per_rank": 1,
            "ram_gib": 2.0,
            "disk_gib": 1.0,
            "wall_time_minutes": 5,
            "max_output_files": 32,
        },
        "execution": {
            "mode": "serial",
            "output_root": "fluidsim-runs",
            "random_seed": 12345,
            "script_name": "run_ns2d.py",
        },
        "provenance": {
            "config_id": "replace-with-study-config-id",
            "created_utc": "2026-10-01T00:00:00Z",
            "dependency_lock_sha256": "replace-with-uv-lock-sha256",
            "fluidfft": FLUIDFFT_VERSION,
            "fluidsim": FLUIDSIM_VERSION,
            "python": "3.11",
        },
    }


def flatten_parameters(
    parameters: Mapping[str, Any], prefix: tuple[str, ...] = ()
) -> list[tuple[tuple[str, ...], Any]]:
    """Flatten validated parameter mappings into deterministic assignments."""

    flattened: list[tuple[tuple[str, ...], Any]] = []
    for key in sorted(parameters):
        value = parameters[key]
        path = (*prefix, key)
        if isinstance(value, Mapping):
            flattened.extend(flatten_parameters(value, path))
        else:
            flattened.append((path, value))
    return flattened


def normalized_copy(document: Any) -> dict[str, Any]:
    """Return an isolated JSON-compatible copy after successful validation."""

    report = validate_config(document)
    if not report["ok"]:
        messages = "; ".join(item["message"] for item in report["errors"][:5])
        raise ToolError(f"configuration is not valid: {messages}")
    return deepcopy(dict(document))
