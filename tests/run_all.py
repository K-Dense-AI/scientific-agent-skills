#!/usr/bin/env python3
"""Run the skill test suites, one pytest process per skill.

Separate processes are required, not a preference: skills' `scripts/`
directories share top-level module names (see tests/conftest.py).

    python tests/run_all.py                     # every skill under tests/
    python tests/run_all.py qutip pydicom       # only the named skills
    python tests/run_all.py -- -x --tb=long     # pass extra args to pytest

A full run starts with `tests/_meta`, the repo-wide guard that checks every
skill against the shared structural contract and fails if a skill ships
`scripts/` without a suite here. Naming skills explicitly skips it.

With `--isolated`, each suite instead runs in a throwaway `uv` environment
built from that skill's entry in tests/skill-requirements.toml:

    python tests/run_all.py --isolated
    python tests/run_all.py --isolated scanpy qiskit

Nothing is installed into the project environment. Each skill gets only the
packages it documents, on the interpreter it needs -- which is the point:
opentrons pins numpy<2, PyTDC needs 3.11, and esm caps transformers below the
version the transformers skill targets, so no single environment can host them
all. uv caches wheels globally, so repeat runs create each environment in
milliseconds.

Exit code is 0 only when every suite passes. Suites that collect nothing are
reported as "empty" and do not fail the run.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
REQUIREMENTS = TESTS_DIR / "skill-requirements.toml"

NO_TESTS_COLLECTED = 5


def discover(names: list[str]) -> list[Path]:
    # Underscore-prefixed directories are infrastructure, not skills:
    # `_contract/` is the shared library and `_meta/` is the repo-wide guard,
    # run separately by `run_meta()` because it spans every skill at once.
    available = sorted(
        path
        for path in TESTS_DIR.iterdir()
        if path.is_dir() and not path.name.startswith((".", "_"))
    )
    if not names:
        return available
    by_name = {path.name: path for path in available}
    unknown = [name for name in names if name not in by_name]
    if unknown:
        sys.exit(
            f"no test directory for: {', '.join(unknown)}\n"
            f"available: {', '.join(sorted(by_name))}"
        )
    return [by_name[name] for name in names]


def load_requirements() -> tuple[dict[str, dict], str, dict[str, str]]:
    """Return (per-skill entries, default interpreter, uninstallable packages)."""
    if not REQUIREMENTS.exists():
        sys.exit(f"missing {REQUIREMENTS.relative_to(REPO_ROOT)}, required by --isolated")
    manifest = tomllib.loads(REQUIREMENTS.read_text())
    default_python = manifest.get("defaults", {}).get("python", "3.13")
    return manifest.get("skills", {}), default_python, manifest.get("unavailable", {})


def isolated_command(
    entry: dict, default_python: str, target: str, pytest_args: list[str]
) -> list[str]:
    """Build the `uv run` invocation that tests one skill in its own environment."""
    command = [
        "uv", "run",
        "--no-project",  # ignore this repo's environment entirely
        "--python", entry.get("python", default_python),
        "--with", "pytest",
    ]
    if config := entry.get("uv_config"):
        config_path = (REPO_ROOT / config).resolve()
        suite_root = (REPO_ROOT / target).resolve()
        if (Path(config).is_absolute() or not config_path.is_relative_to(suite_root)
                or not config_path.is_file()):
            raise ValueError(f"uv_config must name an existing file inside {target}: {config}")
        command += ["--config-file", str(config_path)]
    for package in entry.get("packages", []):
        command += ["--with", package]
    return [*command, "python", "-m", "pytest", target, *pytest_args]


def run_meta(pytest_args: list[str]) -> int:
    """Run the repo-wide guard in this interpreter, before any skill suite.

    `tests/_meta` spans every skill at once -- it is what enforces that a skill
    shipping `scripts/` has a suite here at all -- so it cannot be one of the
    per-skill processes. It imports no skill code and needs no scientific
    packages, so it always runs in the project environment, never an isolated
    one.
    """
    print("\n=== _meta " + "=" * 55)
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/_meta", *pytest_args], cwd=REPO_ROOT
    )
    return completed.returncode


def main(argv: list[str]) -> int:
    isolated = "--isolated" in argv
    argv = [argument for argument in argv if argument != "--isolated"]

    if "--" in argv:
        separator = argv.index("--")
        names, pytest_args = argv[:separator], argv[separator + 1 :]
    else:
        names, pytest_args = argv, []

    entries: dict[str, dict] = {}
    default_python = ""
    unavailable: dict[str, str] = {}
    if isolated:
        if not shutil.which("uv"):
            sys.exit("--isolated needs uv on PATH: https://docs.astral.sh/uv/")
        entries, default_python, unavailable = load_requirements()

    suites = discover(names)
    results: dict[str, int] = {}

    # Only on a full run: when the caller named skills they want those skills,
    # not a repo-wide audit.
    if not names:
        results["_meta"] = run_meta(pytest_args)

    for suite in suites:
        print(f"\n=== {suite.name} " + "=" * max(0, 60 - len(suite.name)))
        target = str(suite.relative_to(REPO_ROOT))
        if isolated:
            entry = entries.get(suite.name)
            if entry is None:
                print(
                    f"no [skills.{suite.name}] in {REQUIREMENTS.name}; "
                    "add one (use packages = [] for standard-library-only skills)"
                )
                results[suite.name] = 1
                continue
            packages = entry.get("packages", [])
            print(
                f"uv env: python {entry.get('python', default_python)}"
                f", {len(packages)} package(s)"
                + (f": {' '.join(packages)}" if packages else "")
            )
            for package, reason in sorted(unavailable.items()):
                if reason.startswith(f"{suite.name} skill:"):
                    print(f"  not installable here -- {package}: {reason.split(': ', 1)[1]}")
            command = isolated_command(entry, default_python, target, pytest_args)
        else:
            command = [sys.executable, "-m", "pytest", target, *pytest_args]
        completed = subprocess.run(command, cwd=REPO_ROOT)
        results[suite.name] = completed.returncode

    failed = {name: code for name, code in results.items() if code not in (0, NO_TESTS_COLLECTED)}
    empty = [name for name, code in results.items() if code == NO_TESTS_COLLECTED]

    print("\n" + "=" * 68)
    print(f"{len(results) - len(failed) - len(empty)} passed, {len(failed)} failed", end="")
    print(f", {len(empty)} empty" if empty else "")
    for name, code in sorted(failed.items()):
        print(f"  FAILED {name} (pytest exit {code})")
    for name in sorted(empty):
        print(f"  empty  {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
