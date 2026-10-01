"""Per-suite uv build configuration stays local and does not leak to peers."""

import importlib.util
from pathlib import Path
import tomllib

import pytest


SPEC = importlib.util.spec_from_file_location(
    "skill_test_runner", Path(__file__).resolve().parents[1] / "run_all.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_suite_build_configuration_is_scoped(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    config = tmp_path / "tests/example/uv.toml"
    config.parent.mkdir(parents=True)
    config.write_text('[extra-build-dependencies]\nexample = ["setuptools"]\n')
    command = runner.isolated_command(
        {"uv_config": "tests/example/uv.toml", "python": "3.10", "packages": ["example"]},
        "3.13", "tests/example", ["-q"],
    )
    assert command[command.index("--config-file") + 1] == str(config)
    assert command[command.index("--python") + 1] == "3.10"
    assert "--no-project" in command
    peer = runner.isolated_command({}, "3.13", "tests/peer", [])
    assert "--config-file" not in peer


@pytest.mark.parametrize("config", ["missing.toml", "tests/peer/uv.toml", "../outside.toml"])
def test_suite_build_configuration_rejects_missing_or_escaping_paths(tmp_path, monkeypatch, config):
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    peer = tmp_path / "tests/peer/uv.toml"
    peer.parent.mkdir(parents=True)
    peer.write_text("")
    with pytest.raises(ValueError, match="inside tests/example"):
        runner.isolated_command({"uv_config": config}, "3.13", "tests/example", [])


def test_all_declared_build_configurations_are_valid():
    entries, default_python, _ = runner.load_requirements()
    for name, entry in entries.items():
        if "uv_config" in entry:
            command = runner.isolated_command(entry, default_python, f"tests/{name}", [])
            config = Path(command[command.index("--config-file") + 1])
            tomllib.loads(config.read_text(encoding="utf-8"))
