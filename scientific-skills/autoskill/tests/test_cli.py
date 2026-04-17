import pytest

import autoskill


def test_dispatches_to_run_subcommand(monkeypatch):
    calls = {}

    def fake_run_main(argv):
        calls["run"] = argv
        return 0

    monkeypatch.setattr("run.main", fake_run_main)
    rc = autoskill.main(["run", "--start", "a", "--end", "b"])

    assert rc == 0
    assert calls["run"] == ["--start", "a", "--end", "b"]


def test_dispatches_to_doctor_subcommand(monkeypatch):
    calls = {}

    def fake_doctor_main(argv):
        calls["doctor"] = argv
        return 0

    monkeypatch.setattr("doctor.main", fake_doctor_main)
    rc = autoskill.main(["doctor", "--config", "x", "--skills-dir", "y"])

    assert rc == 0
    assert calls["doctor"] == ["--config", "x", "--skills-dir", "y"]


def test_dispatches_to_promote_subcommand(monkeypatch):
    calls = {}

    def fake_promote_main(argv):
        calls["promote"] = argv
        return 0

    monkeypatch.setattr("promote.main", fake_promote_main)
    rc = autoskill.main(["promote", "--proposed", "p", "--skills-dir", "s", "--name", "n"])

    assert rc == 0
    assert calls["promote"] == ["--proposed", "p", "--skills-dir", "s", "--name", "n"]


def test_propagates_nonzero_exit_code(monkeypatch):
    monkeypatch.setattr("run.main", lambda argv: 7)
    rc = autoskill.main(["run", "--start", "a", "--end", "b"])
    assert rc == 7


def test_missing_subcommand_errors_out():
    with pytest.raises(SystemExit):
        autoskill.main([])


def test_unknown_subcommand_errors_out():
    with pytest.raises(SystemExit):
        autoskill.main(["nope"])
