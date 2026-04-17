from pathlib import Path

from doctor import check, main as doctor_main


def _config(tmp_path: Path) -> dict:
    return {
        "backend": "local",
        "local": {"endpoint": "http://localhost:1234/v1", "model": "m"},
        "screenpipe": {"url": "http://localhost:3030"},
    }


def _ok_probe(*_args, **_kwargs):
    return ("ok", "")


def _err_probe(*_args, **_kwargs):
    return ("error", "boom")


def test_check_all_green(tmp_path: Path):
    result = check(
        _config(tmp_path),
        skills_dir=tmp_path,
        screenpipe_probe=_ok_probe,
        llm_probe=_ok_probe,
    )

    assert result["screenpipe"] == ("ok", "")
    assert result["llm"] == ("ok", "")
    assert result["config"][0] == "ok"
    assert result["skills_dir"][0] == "ok"


def test_check_reports_screenpipe_failure(tmp_path: Path):
    result = check(
        _config(tmp_path),
        skills_dir=tmp_path,
        screenpipe_probe=_err_probe,
        llm_probe=_ok_probe,
    )
    assert result["screenpipe"] == ("error", "boom")


def test_check_reports_llm_failure(tmp_path: Path):
    result = check(
        _config(tmp_path),
        skills_dir=tmp_path,
        screenpipe_probe=_ok_probe,
        llm_probe=_err_probe,
    )
    assert result["llm"] == ("error", "boom")


def test_check_reports_missing_skills_dir(tmp_path: Path):
    missing = tmp_path / "nope"
    result = check(
        _config(tmp_path),
        skills_dir=missing,
        screenpipe_probe=_ok_probe,
        llm_probe=_ok_probe,
    )
    assert result["skills_dir"][0] == "error"
    assert str(missing) in result["skills_dir"][1]


def test_check_flags_unknown_backend(tmp_path: Path):
    bad = {"backend": "mystery", "screenpipe": {"url": "http://x"}}
    result = check(
        bad, skills_dir=tmp_path,
        screenpipe_probe=_ok_probe, llm_probe=_ok_probe,
    )
    assert result["config"][0] == "error"
    assert "mystery" in result["config"][1]


def test_cli_all_green_returns_zero(tmp_path: Path, capsys, monkeypatch):
    import yaml as _yaml
    conf_path = tmp_path / "c.yaml"
    conf_path.write_text(_yaml.safe_dump(_config(tmp_path)))
    monkeypatch.setattr("doctor.default_screenpipe_probe", _ok_probe)
    monkeypatch.setattr("doctor.default_llm_probe", _ok_probe)

    rc = doctor_main([
        "--config", str(conf_path),
        "--skills-dir", str(tmp_path),
    ])

    out = capsys.readouterr().out
    assert rc == 0
    assert "ok" in out.lower()


def test_cli_any_failure_returns_nonzero(tmp_path: Path, capsys, monkeypatch):
    import yaml as _yaml
    conf_path = tmp_path / "c.yaml"
    conf_path.write_text(_yaml.safe_dump(_config(tmp_path)))
    monkeypatch.setattr("doctor.default_screenpipe_probe", _err_probe)
    monkeypatch.setattr("doctor.default_llm_probe", _ok_probe)

    rc = doctor_main([
        "--config", str(conf_path),
        "--skills-dir", str(tmp_path),
    ])
    out = capsys.readouterr().out
    assert rc != 0
    assert "error" in out.lower() or "error" in capsys.readouterr().err.lower()
