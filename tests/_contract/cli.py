"""`--help` contract for a skill's bundled command-line scripts.

Unlike `structure`, this half actually runs the scripts, so what it proves
depends on the environment. In the bare project environment most scientific
packages are absent and the affected scripts skip; under
`python tests/run_all.py --isolated`, where each skill gets the packages it
documents, the same tests run for real. That is the point of the split: one
definition, honest in both places.

Each script runs in its own subprocess -- `--help` must not need this
interpreter's `sys.path`, and a script that hangs must not hang the suite.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

DEFAULT_TIMEOUT = 120

#: Never invoked directly: shared helpers and package markers, not CLIs.
NON_CLI_NAMES = frozenset({"__init__.py", "__main__.py", "_common.py", "conftest.py"})


def cli_scripts(skill_root: Path) -> list[Path]:
    """Top-level scripts under `scripts/` that build an argparse parser.

    Only the top level: nested directories under `scripts/` are importable
    libraries, not entry points.
    """
    scripts = []
    for path in sorted((skill_root / "scripts").glob("*.py")):
        if path.name in NON_CLI_NAMES:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue  # structure.compile_problems reports it
        imports_argparse = any(
            (isinstance(node, ast.Import) and any(a.name == "argparse" for a in node.names))
            or (isinstance(node, ast.ImportFrom) and node.module == "argparse")
            for node in ast.walk(tree)
        )
        if imports_argparse:
            scripts.append(path)
    return scripts


def run_help(script: Path, timeout: int = DEFAULT_TIMEOUT) -> subprocess.CompletedProcess:
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=environment,
        cwd=script.parent,
    )


#: A script that guards its own imports and prints a friendly install hint --
#: better behaviour than a traceback -- must still be recognised as "package
#: absent" rather than reported as a broken CLI. `exa-search` does exactly this.
_GRACEFUL_IMPORT_GUARD = re.compile(
    r"(?:^|\n)\s*([\w.\-]+) (?:is )?not installed\b"
    r"|No module named ['\"]?([\w.]+)"
    r"|pip install ([\w.\-\[\]]+)",
    re.IGNORECASE,
)


def _missing_dependency(output: str) -> str | None:
    """The package name, when a failed `--help` was caused by an absent import.

    Deliberately narrow. `ImportError: cannot import name 'PSICQUIC' from
    'bioservices'` means the package IS installed and the script is calling an
    API that no longer exists -- upstream drift, the most valuable thing this
    contract can catch. Treating that as "package absent" would skip the test
    and hide the breakage, so only a genuinely absent module counts:

    * `ModuleNotFoundError`, or an `ImportError` naming no such module;
    * a script that catches the ImportError itself and prints an install hint.
    """
    for line in reversed(output.strip().splitlines()):
        if line.startswith("ModuleNotFoundError:"):
            return line.split(":", 1)[1].strip()
        if line.startswith("ImportError:"):
            message = line.split(":", 1)[1].strip()
            return message if "No module named" in message else None

    match = _GRACEFUL_IMPORT_GUARD.search(output)
    if match:
        return next(group for group in match.groups() if group)
    return None


def help_test_case(
    skill_root: Path,
    *,
    skip: frozenset[str] | set[str] | tuple[str, ...] = (),
    timeout: int = DEFAULT_TIMEOUT,
) -> type[unittest.TestCase]:
    """Build the `--help` TestCase for one skill.

    `skip` names scripts (by filename) that legitimately have no working
    `--help` -- pass it sparingly and say why at the call site.
    """
    skipped = frozenset(skip)

    class CliHelpContractTests(unittest.TestCase):
        maxDiff = None

        def test_every_cli_answers_help(self) -> None:
            scripts = [
                path for path in cli_scripts(skill_root) if path.name not in skipped
            ]
            self.assertTrue(
                scripts,
                f"{skill_root.name} ships no argparse CLI -- drop this test case "
                "or fix the discovery",
            )
            for script in scripts:
                with self.subTest(script=script.name):
                    try:
                        result = run_help(script, timeout=timeout)
                    except subprocess.TimeoutExpired:
                        self.fail(
                            f"{script.name} --help did not return within {timeout}s; "
                            "it is doing work before parsing arguments"
                        )
                    if result.returncode != 0:
                        missing = _missing_dependency(result.stderr + result.stdout)
                        if missing:
                            self.skipTest(
                                f"{script.name} needs an uninstalled package ({missing}); "
                                "run under `tests/run_all.py --isolated` to exercise it"
                            )
                        self.fail(
                            f"{script.name} --help exited {result.returncode}:\n"
                            f"{result.stderr.strip()}"
                        )
                    self.assertIn(
                        "usage:",
                        result.stdout.lower(),
                        f"{script.name} --help printed no usage line",
                    )
                    self.assertNotIn("Traceback", result.stderr)

    CliHelpContractTests.__qualname__ = f"CliHelpContractTests[{skill_root.name}]"
    return CliHelpContractTests


def demo_test_case(
    skill_root: Path,
    scripts: tuple[str, ...],
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> type[unittest.TestCase]:
    """Build a TestCase that runs a library script's `__main__` demo block.

    Some skills ship importable modules rather than CLIs, with a worked example
    under `if __name__ == "__main__":`. That example is documentation, and
    documentation rots -- so run it and require a clean exit.

    Opt-in and explicit: pass the filenames, because a demo block that writes
    files or takes minutes should not be run by accident.
    """

    class DemoBlockTests(unittest.TestCase):
        maxDiff = None

        def test_every_demo_block_runs_clean(self) -> None:
            for name in scripts:
                script = skill_root / "scripts" / name
                with self.subTest(script=name):
                    self.assertTrue(script.is_file(), f"{name} is not shipped")
                    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
                    # Headless: a demo that plots must not open a window.
                    environment.setdefault("MPLBACKEND", "Agg")
                    try:
                        result = subprocess.run(
                            [sys.executable, str(script)],
                            capture_output=True,
                            text=True,
                            timeout=timeout,
                            env=environment,
                            cwd=script.parent,
                        )
                    except subprocess.TimeoutExpired:
                        self.fail(f"{name} did not finish within {timeout}s")
                    if result.returncode != 0:
                        missing = _missing_dependency(result.stderr + result.stdout)
                        if missing:
                            self.skipTest(
                                f"{name} needs an uninstalled package ({missing}); "
                                "run under `tests/run_all.py --isolated`"
                            )
                        self.fail(
                            f"{name} exited {result.returncode}:\n{result.stderr.strip()}"
                        )
                    self.assertTrue(
                        result.stdout.strip(), f"{name} printed nothing"
                    )

    DemoBlockTests.__qualname__ = f"DemoBlockTests[{skill_root.name}]"
    return DemoBlockTests
