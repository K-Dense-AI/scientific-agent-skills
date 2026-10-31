#!/usr/bin/env python3
"""Create a bounded MATLAB or Octave command plan without executing it."""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path
from typing import Any

from _common import (
    CliError,
    checked_input,
    checked_root,
    emit_json,
    fail_json,
    parse_json_text,
    relative_id,
    validate_identifier,
)

TOOL = "plan_batch_command"
SAFE_COMMAND = re.compile(r"^[A-Za-z0-9_.+-]{1,64}$")


def matlab_string(value: str, *, engine: str = "matlab") -> str:
    if len(value) > 100_000:
        raise CliError("MATLAB string literal exceeds 100000 characters")
    if any(ord(character) < 32 for character in value):
        raise CliError("control characters are not accepted in MATLAB strings")
    if engine == "octave":
        # Octave interprets backslash escapes inside double quotes. Its single
        # quotes preserve Windows paths and other literal backslashes.
        return "'" + value.replace("'", "''") + "'"
    return '"' + value.replace('"', '""') + '"'


def _numeric_row(values: list[Any]) -> str | None:
    if not values or not all(
        isinstance(item, (bool, int, float)) and not isinstance(item, str)
        for item in values
    ):
        return None
    return "[" + " ".join(matlab_literal(item) for item in values) + "]"


def matlab_literal(value: Any, *, depth: int = 0, engine: str = "matlab") -> str:
    if depth > 12:
        raise CliError("argument nesting exceeds 12")
    if value is None:
        return "[]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        if abs(value) > 2**53:
            raise CliError("JSON integers outside exact MATLAB double range are refused")
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CliError("nonfinite JSON numbers are refused")
        return format(value, ".17g")
    if isinstance(value, str):
        return matlab_string(value, engine=engine)
    if isinstance(value, list):
        row = _numeric_row(value)
        if row is not None:
            return row
        if value and all(isinstance(item, list) for item in value):
            rows = [_numeric_row(item) for item in value]
            if all(row_value is not None for row_value in rows):
                widths = {len(item) for item in value}
                if len(widths) == 1:
                    return "[" + "; ".join(
                        row_value[1:-1] for row_value in rows if row_value
                    ) + "]"
        if value and all(isinstance(item, str) for item in value):
            if engine == "matlab":
                return "[" + " ".join(matlab_string(item) for item in value) + "]"
            return "{" + ", ".join(
                matlab_string(item, engine=engine) for item in value
            ) + "}"
        return "{" + ", ".join(
            matlab_literal(item, depth=depth + 1, engine=engine) for item in value
        ) + "}"
    if isinstance(value, dict):
        fields: list[str] = []
        for key in sorted(value):
            validate_identifier(key, name="JSON object field")
            fields.extend(
                [
                    matlab_string(key, engine=engine),
                    # A scalar outer cell prevents struct() from expanding a
                    # cell-valued field into a struct array (or empty struct).
                    "{" + matlab_literal(
                        value[key], depth=depth + 1, engine=engine
                    ) + "}",
                ]
            )
        return "struct(" + ", ".join(fields) + ")"
    raise CliError(f"unsupported argument type: {type(value).__name__}")


def _executable(value: str, engine: str) -> str:
    default = "matlab" if engine == "matlab" else "octave"
    command = value or default
    if not SAFE_COMMAND.fullmatch(command):
        raise CliError(
            "executable must be a bare command name; edit the reviewed argv "
            "manually for an absolute installation path"
        )
    return command


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    root = checked_root(args.root)
    target = checked_input(
        args.target,
        root=root,
        suffixes={".m"},
        max_bytes=args.max_input_bytes,
    )
    executable = _executable(args.executable, args.engine)
    function_name = args.function_name or target.stem
    validate_identifier(function_name, name="function name")
    if args.mode == "function" and function_name != target.stem:
        raise CliError("function name must match the target .m filename")
    if args.arg_json and args.mode != "function":
        raise CliError("--arg-json is accepted only in function mode")
    literals = [
        matlab_literal(parse_json_text(argument), engine=args.engine)
        for argument in args.arg_json
    ]
    target_literal = matlab_string(str(target), engine=args.engine)
    warnings = [
        "This plan does not execute or prove the target safe.",
        "Confirm the exact runtime, products, licenses, startup behavior, "
        "inputs, outputs, and external effects before execution.",
    ]
    argv: list[str]
    statement: str | None
    if args.engine == "matlab":
        argv = [executable]
        if args.disable_graphics:
            argv.append("-noFigureWindows")
        startup = target.parent if args.mode == "function" else root
        argv.extend(["-sd", str(startup)])
        if args.mode == "script":
            statement = f"run({target_literal})"
        elif args.mode == "function":
            statement = f"{function_name}({', '.join(literals)})"
        else:
            statement = (
                f"results = runtests({target_literal}); assertSuccess(results)"
            )
            warnings.append(
                "R2026a runtests can automatically open and close a containing "
                "project, including reviewed startup/shutdown actions."
            )
        argv.extend(["-batch", statement])
        warnings.append(
            "MATLAB -batch still processes launcher/startup configuration; "
            "-sd is not isolation."
        )
        prerequisites = [
            "Installed MATLAB compatible with the reviewed source",
            "Confirmed MATLAB and required-product license availability",
        ]
    else:
        argv = [
            executable,
            "--no-init-all",
            "--no-history",
            "--quiet",
            "--no-gui",
        ]
        if args.disable_graphics:
            argv.append("--no-window-system")
        statement = None
        if args.mode == "script":
            argv.append(str(target))
        elif args.mode == "function":
            statement = f"{function_name}({', '.join(literals)})"
            argv.extend(["--path", str(target.parent), "--eval", statement])
        else:
            statement = (
                f"success = test({target_literal}, "
                f'{matlab_string("quiet", engine="octave")}); assert(success)'
            )
            argv.extend(["--eval", statement])
            warnings.append(
                "Octave BIST test is not MATLAB matlab.unittest compatibility."
            )
        prerequisites = [
            "Installed GNU Octave compatible with the reviewed source",
            "Confirmed required Octave package availability",
        ]
    return {
        "arguments": {
            "count": len(literals),
            "json_arrays": "numeric rectangular arrays map to numeric arrays; "
            "string lists map to MATLAB string arrays or Octave cell arrays; "
            "other arrays map to cells; JSON objects map to scalar structs",
        },
        "command_argv": argv,
        "disable_graphics": bool(args.disable_graphics),
        "engine": args.engine,
        "executes": False,
        "mode": args.mode,
        "network_accessed": False,
        "ok": True,
        "prerequisites": prerequisites,
        "root": str(root),
        "statement": statement,
        "target": relative_id(target, root),
        "tool": TOOL,
        "warnings": warnings,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Plan a MATLAB -batch or GNU Octave command. The tool validates "
            "local paths and JSON literals but never launches either runtime."
        )
    )
    result.add_argument("engine", choices=("matlab", "octave"))
    result.add_argument("mode", choices=("script", "function", "tests"))
    result.add_argument("target", help="reviewed local .m file")
    result.add_argument("--root", default=".", help="allowed local root")
    result.add_argument(
        "--arg-json",
        action="append",
        default=[],
        help="one bounded JSON function argument; repeat as needed",
    )
    result.add_argument("--function-name", help="must match target stem")
    result.add_argument(
        "--executable",
        default="",
        help="bare command name only (default: matlab or octave)",
    )
    result.add_argument(
        "--disable-graphics",
        action="store_true",
        help="plan no figure windows/window system",
    )
    result.add_argument(
        "--max-input-bytes",
        type=int,
        default=4 * 1024 * 1024,
        help="maximum target .m bytes (default: 4194304)",
    )
    return result


def main() -> int:
    try:
        args = parser().parse_args()
        if args.max_input_bytes < 1 or args.max_input_bytes > 64 * 1024 * 1024:
            raise CliError("--max-input-bytes must be between 1 and 67108864")
        emit_json(build_plan(args))
        return 0
    except CliError as exc:
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
