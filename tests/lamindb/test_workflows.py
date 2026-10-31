"""Execute documentation/API regressions in disposable local Lamin instances."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "lamindb"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

pytestmark = pytest.mark.skipif(
    any(importlib.util.find_spec(name) is None for name in ("lamindb", "bionty", "IPython")),
    reason="Run tests/run_all.py --isolated lamindb for the reviewed environment",
)


def run_local(tmp_path: Path, source: str) -> str:
    # Strip inherited instance selection and keys before any Lamin import.
    env = {k: v for k, v in os.environ.items() if not k.startswith("LAMIN")}
    env.update(
        LAMIN_SETTINGS_DIR=str(tmp_path / "settings"),
        LAMIN_CACHE_DIR=str(tmp_path / "cache"),
        NO_RICH="1",
    )
    script = tmp_path / "workflow.py"
    script.write_text(source, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script)], cwd=tmp_path, env=env,
        capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_documented_local_example(tmp_path):
    document = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    example = re.findall(r"```python\n(.*?)```", document, re.S)[0]
    source = (
        "import lamindb_setup as setup\n"
        "setup.init(storage='./storage', name='documented-example', modules='bionty')\n"
        + example
        + "\nassert artifact.run.finished_at is not None\n"
        + "assert artifact.run.output_artifacts.filter(uid=artifact.uid).exists()\n"
    )
    run_local(tmp_path, source)


def test_curation_lineage_and_query_contracts(tmp_path):
    output = run_local(tmp_path, (FIXTURES / "local_workflows.py").read_text())
    assert "[OK] local Lamin contracts" in output


def test_documented_cli_commands_are_available(tmp_path):
    source = '''from click.testing import CliRunner
from lamin_cli.__main__ import main
for arguments in [
    ["init", "--help"], ["connect", "--help"], ["disconnect", "--help"],
    ["settings", "cache-dir", "get", "--help"],
    ["settings", "cache-dir", "set", "--help"],
    ["settings", "dev-dir", "set", "--help"],
    ["settings", "modules", "get", "--help"], ["migrate", "deploy", "--help"],
]:
    result = CliRunner().invoke(main, arguments)
    assert result.exit_code == 0, (arguments, result.output, result.exception)
'''
    run_local(tmp_path, source)
