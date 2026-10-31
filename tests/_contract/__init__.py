"""Shared test contract for every skill in this repository.

Suites do not import this package by name from `sys.path` -- putting `tests/`
on `sys.path` would turn `tests/simpy/`, `tests/qutip/`, `tests/neurokit2/` and
friends into importable namespace packages that shadow the real libraries (see
the comment on `addopts` in `pyproject.toml`). Instead `tests/conftest.py`
loads this package by file location and registers it as `skill_contract`, so a
suite writes:

    import skill_contract

    CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

Two halves, split by what they need from the environment:

`structure`
    Never imports skill code -- scripts are parsed with `ast`, not executed --
    so it is safe to run across every skill in one interpreter.
    `tests/_meta` does exactly that.

`cli`
    Runs each script's `--help` in a subprocess. Skips when the skill's
    packages are absent, and runs for real under
    `python tests/run_all.py --isolated`.

`schematic`
    The AI schematic generator that scientific-schematics, latex-posters,
    literature-review, and scientific-slides each ship a byte-identical copy of.
"""

from __future__ import annotations

from . import cli, schematic, structure

__all__ = ["cli", "schematic", "structure"]
