"""Tiny local checks for the command contracts documented by the DataLad skill."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "datalad"
pytestmark = pytest.mark.skipif(
    not shutil.which("datalad") or not shutil.which("git-annex"),
    reason="DataLad and git-annex executables are required",
)


@pytest.fixture
def cli(tmp_path, monkeypatch):
    # Use process-local configuration; never change the user's global Git identity.
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for name, value in {
        "GIT_AUTHOR_NAME": "Local Test",
        "GIT_COMMITTER_NAME": "Local Test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": "protocol.file.allow",
        "GIT_CONFIG_VALUE_0": "always",
        "GIT_CONFIG_KEY_1": "init.defaultBranch",
        "GIT_CONFIG_VALUE_1": "main",
        "DATALAD_UI_INTERACTIVE": "false",
    }.items():
        monkeypatch.setenv(name, value)

    def call(*args, cwd=None, ok=True):
        proc = subprocess.run(
            [str(arg) for arg in args], cwd=cwd or tmp_path,
            text=True, capture_output=True, timeout=90,
        )
        if ok:
            assert proc.returncode == 0, proc.stdout + proc.stderr
        return proc

    return call


def create(cli, path):
    cli("datalad", "create", "-c", "yoda", path)
    (path / "input.txt").write_text("2\n3\n")
    cli("datalad", "save", "-m", "input", "input.txt", cwd=path)


def status(cli, path, file):
    output = cli("datalad", "-f", "json", "status", "--annex", "availability", file, cwd=path)
    return json.loads(output.stdout.splitlines()[0])


def test_clone_get_drop_and_unlocked_save(cli, tmp_path):
    source, clone = tmp_path / "source", tmp_path / "clone"
    create(cli, source)
    cli("datalad", "clone", source, clone)
    assert not status(cli, clone, "input.txt")["has_content"]
    cli("datalad", "get", "input.txt", cwd=clone)
    assert (clone / "input.txt").read_text() == "2\n3\n"
    cli("datalad", "drop", "input.txt", cwd=clone)
    assert not status(cli, clone, "input.txt")["has_content"]
    cli("datalad", "get", "input.txt", cwd=clone)
    cli("datalad", "unlock", "input.txt", cwd=clone)
    (clone / "input.txt").write_text("7\n")
    cli("datalad", "save", "-m", "revise", "input.txt", cwd=clone)
    assert status(cli, clone, "input.txt")["has_content"]
    assert cli("datalad", "drop", "input.txt", cwd=clone, ok=False).returncode != 0
    assert (clone / "input.txt").read_text() == "7\n"


def test_run_replay_from_parent_and_dirty_scope(cli, tmp_path):
    dataset = tmp_path / "analysis"
    create(cli, dataset)
    (dataset / "code" / "sum.py").write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "Path(sys.argv[2]).write_text(str(sum(map(int, Path(sys.argv[1]).read_text().split())))+'\\n')\n"
    )
    cli("datalad", "save", "-m", "code", "code/sum.py", cwd=dataset)
    command = "python code/sum.py {inputs[0]} {outputs[0]}"
    cli("datalad", "run", "-i", "input.txt", "-i", "code/sum.py", "-o", "sum.txt", command, cwd=dataset)
    original = cli("git", "rev-parse", "HEAD", cwd=dataset).stdout.strip()
    cli("datalad", "rerun", "--report", "--since", original + "^", original, cwd=dataset)
    cli("datalad", "rerun", "--onto=", "-b", "repro-check", "--since", original + "^", original, cwd=dataset)
    assert (dataset / "sum.txt").read_text() == "5\n"
    assert not cli("git", "diff", original, "HEAD", "--", "sum.txt", cwd=dataset).stdout
    (dataset / "unrelated.txt").write_text("leave unsaved\n")
    assert cli("datalad", "run", "echo wrong > extra.txt", cwd=dataset, ok=False).returncode != 0
    assert not (dataset / "extra.txt").exists()
    cli("datalad", "run", "--explicit", "-o", "extra.txt", "echo scoped > {outputs}", cwd=dataset)
    assert "?? unrelated.txt" in cli("git", "status", "--porcelain", cwd=dataset).stdout


def test_default_push_without_wanted_transfers_content(cli, tmp_path):
    dataset = tmp_path / "dataset"
    store = tmp_path / "store"
    store.mkdir()
    create(cli, dataset)
    cli("git", "annex", "initremote", "store", "type=directory", f"directory={store}", "encryption=none", cwd=dataset)
    cli("datalad", "push", "--to", "store", cwd=dataset)
    record = json.loads(cli("git", "annex", "whereis", "--json", "input.txt", cwd=dataset).stdout)
    assert any("store" in entry["description"] for entry in record["whereis"])
    cli("datalad", "drop", "input.txt", cwd=dataset)
    cli("datalad", "get", "-s", "store", "input.txt", cwd=dataset)
    assert (dataset / "input.txt").read_text() == "2\n3\n"


def test_ria_publish_clone_get(cli, tmp_path):
    dataset, store, clone = tmp_path / "dataset", tmp_path / "ria", tmp_path / "clone"
    create(cli, dataset)
    url = "ria+" + store.as_uri()
    cli("datalad", "create-sibling-ria", "-s", "backup", "--new-store-ok", "--alias", "tiny", url, cwd=dataset)
    cli("datalad", "push", "--to", "backup", cwd=dataset)
    cli("datalad", "clone", url + "#~tiny", clone)
    assert not status(cli, clone, "input.txt")["has_content"]
    cli("datalad", "get", "input.txt", cwd=clone)
    assert (clone / "input.txt").read_text() == "2\n3\n"
    cli("git", "annex", "fsck", cwd=clone)


def test_get_structure_does_not_fetch_subdataset_bytes(cli, tmp_path):
    source, parent, clone = tmp_path / "source", tmp_path / "parent", tmp_path / "clone"
    create(cli, source)
    cli("datalad", "create", parent)
    cli("datalad", "clone", "-d", parent, source, parent / "inputs")
    cli("datalad", "clone", parent, clone)
    cli("datalad", "get", "-n", "-r", ".", cwd=clone)
    assert not status(cli, clone / "inputs", "input.txt")["has_content"]
    cli("datalad", "get", "inputs/input.txt", cwd=clone)
    assert (clone / "inputs" / "input.txt").read_text() == "2\n3\n"


def test_failed_command_save_records_nonzero_exit(cli, tmp_path):
    dataset = tmp_path / "failure-record"
    create(cli, dataset)
    cli("datalad", "run", "--on-cmd-failure", "save", "-o", "failure.txt",
        "echo partial > {outputs}; exit 7", cwd=dataset)
    message = cli("git", "log", "-1", "--format=%B", cwd=dataset).stdout
    record = json.loads(message.split("=== Do not change lines below ===\n")[1].split("\n^^^")[0])
    assert record["exit"] == 7
    assert (dataset / "failure.txt").read_text() == "partial\n"
