"""Make the shared contract importable when this suite runs outside its home repo.

This skill is authored to be grafted into K-Dense-AI `scientific-agent-skills`, whose
`tests/conftest.py` installs `tests/_contract/` as the module `skill_contract`. When that
repo's conftest has already run, `skill_contract` is in `sys.modules` and this file is a
no-op -- it never shadows or re-installs the real one.

Standalone (authoring workspace, CI checkout of this repo alone) the contract package is
not on `sys.path`, so the `--help` test would fail to import. Rather than hardcode an
interpreter- or machine-specific location, look for the package at a small set of paths
relative to this file, and skip the contract test cleanly when it is genuinely absent.

Placing this at `tests/tket/conftest.py` (not `tests/conftest.py`) keeps it skill-scoped,
so grafting the suite into the upstream repo cannot collide with that repo's own root
conftest.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent

#: Candidate locations of the `_contract` package, relative to this test directory.
_CONTRACT_CANDIDATES = (
    TEST_DIR.parent / "_contract",  # grafted: scientific-agent-skills/tests/_contract
    TEST_DIR.parent.parent / "scientific-agent-skills" / "tests" / "_contract",
)


def _install_contract() -> None:
    if "skill_contract" in sys.modules:
        return
    for package in _CONTRACT_CANDIDATES:
        init = package / "__init__.py"
        if not init.is_file():
            continue
        spec = importlib.util.spec_from_file_location(
            "skill_contract",
            init,
            submodule_search_locations=[str(package)],
        )
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        # Registered before exec_module so the package's own `from . import cli` resolves.
        sys.modules["skill_contract"] = module
        spec.loader.exec_module(module)
        return


_install_contract()
