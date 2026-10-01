"""
Contract for the one script imaging-data-commons bundles, `scripts/check_version.py`.

The skill's startup step. It reports whether `idc-index` is installed and at least the
version the skill was tested against, prints the install command for the interpreter
that ran it, and exits non-zero so the agent stops rather than querying a stale index.
It never installs anything — see `TestNeverInstalls` for why that is load-bearing.

Offline and dependency-free: no network, no `idc-index`, standard library plus pytest.
Importing the module is side-effect free — `idc_index`, `json`, and `urllib` are all
imported inside the functions that need them — so this suite runs in the bare project
environment, not only under `tests/run_all.py --isolated`.

Adapted from the upstream copy at
https://github.com/ImagingDataCommons/imaging-data-commons-skill/blob/main/tests/test_check_version.py
with repository-local paths and regression coverage for safely quoted install commands.
"""

import os
import re
import shlex
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "imaging-data-commons"
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
import check_version  # noqa: E402

_SKILL_MD = os.path.join(SKILL_ROOT, "SKILL.md")


class TestParseVersion:
    def test_orders_numerically(self):
        # String comparison would (wrongly) order "0.12.0" < "0.9.0".
        assert check_version.parse_version("0.12.0") > check_version.parse_version("0.9.0")

    def test_strips_v_prefix(self):
        assert check_version.parse_version("v1.6.5") == (1, 6, 5)

    def test_tolerates_prereleases(self):
        # A pre-release tag upstream must not crash the startup check. It compares equal
        # to its base release, so the update notices stay conservative.
        assert check_version.parse_version("0.13.0rc1") == (0, 13, 0)
        assert check_version.parse_version("v1.7.0-beta") == (1, 7, 0)
        assert check_version.parse_version("0.13.0rc1") == check_version.parse_version("0.13.0")

    def test_pads_short_versions(self):
        assert check_version.parse_version("1.7") == (1, 7, 0)
        assert check_version.parse_version("2") == (2, 0, 0)

    def test_ignores_components_past_the_third(self):
        assert check_version.parse_version("1.2.3.4") == (1, 2, 3)


class TestInstallCommands:
    """The printed command must name this interpreter, and must not override PEP 668."""

    def test_pip_form_targets_the_running_interpreter(self, monkeypatch):
        monkeypatch.setattr(check_version.shutil, "which", lambda _: None)
        commands = check_version.install_commands("idc-index==0.12.5")
        assert shlex.split(commands[0]) == [sys.executable, "-m", "pip", "install", "idc-index==0.12.5"]
        assert len(commands) == 1

    def test_uv_form_is_preferred_when_uv_is_available(self, monkeypatch):
        monkeypatch.setattr(check_version.shutil, "which", lambda name: f"/usr/bin/{name}")
        commands = check_version.install_commands("idc-index==0.12.5")
        assert len(commands) == 2
        # uv pip install without --python targets the *active* environment, which is not
        # necessarily the one that failed to import idc_index.
        assert shlex.split(commands[0]) == [
            "uv", "pip", "install", "--python", sys.executable, "idc-index==0.12.5"
        ]
        assert commands[1].startswith(f"{sys.executable} -m pip install")

    def test_upgrade_flag_applies_to_every_form(self, monkeypatch):
        monkeypatch.setattr(check_version.shutil, "which", lambda name: f"/usr/bin/{name}")
        commands = check_version.install_commands("idc-index", upgrade=True)
        assert all("--upgrade" in command for command in commands)

    def test_shell_metacharacters_and_spaces_remain_literal_arguments(self, monkeypatch):
        executable = "/tmp/Python Env/$(touch unexpected)/python"
        monkeypatch.setattr(check_version.sys, "executable", executable)
        monkeypatch.setattr(check_version.shutil, "which", lambda _: "/usr/bin/uv")
        spec = "idc-index>=0.12.5; python_version >= '3.10'"
        uv_command, pip_command = map(shlex.split, check_version.install_commands(spec))
        assert uv_command == ["uv", "pip", "install", "--python", executable, spec]
        assert pip_command == [executable, "-m", "pip", "install", spec]

    def test_no_command_bypasses_an_externally_managed_interpreter(self, monkeypatch):
        monkeypatch.setattr(check_version.shutil, "which", lambda name: f"/usr/bin/{name}")
        for spec in ("idc-index", "idc-index==0.12.5"):
            for command in check_version.install_commands(spec, upgrade=True):
                assert "--break-system-packages" not in command
                assert "--system" not in command

    def test_instructions_name_the_version_and_the_interpreter(self, capsys):
        check_version.print_install_instructions(f"idc-index=={check_version.MIN_VERSION}")
        out = capsys.readouterr().out
        assert check_version.MIN_VERSION in out
        assert sys.executable in out
        assert "virtual environment" in out
        assert "--user" not in out


class TestNeverInstalls:
    """The script reports and instructs; it must not mutate the environment.

    Auto-installing into whatever interpreter `pip` happens to resolve to can silently
    rewrite a user's global site-packages — and, with a capped dependency, downgrade a
    package the environment needs. Installation is the caller's decision.
    """

    def _source(self):
        with open(check_version.__file__, encoding="utf-8") as handle:
            return handle.read()

    def test_source_has_no_installer_call(self):
        for forbidden in ("subprocess", "--break-system-packages", "pip3", "os.system"):
            assert forbidden not in self._source(), (
                f"check_version.py must not use {forbidden}"
            )

    def test_source_has_no_dynamic_execution(self):
        # Downstream registries reject bundled scripts that call eval/exec.
        for forbidden in ("eval(", "exec("):
            assert forbidden not in self._source()


class TestMinimumCheck:
    """check_minimum() reports the installed version, or None with instructions."""

    def test_missing_package_reports_none_and_instructs(self, monkeypatch, capsys):
        # `None` in sys.modules makes `import idc_index` raise ImportError, so this test
        # exercises the not-installed path whether or not the package is present.
        monkeypatch.setitem(sys.modules, "idc_index", None)
        assert check_version.check_minimum() is None
        out = capsys.readouterr().out
        assert "not installed" in out
        assert check_version.MIN_VERSION in out

    def test_older_version_reports_none(self, monkeypatch, capsys):
        monkeypatch.setitem(sys.modules, "idc_index", _FakeIdcIndex("0.9.0"))
        assert check_version.check_minimum() is None
        assert "below the pinned minimum" in capsys.readouterr().out

    def test_current_version_is_returned(self, monkeypatch, capsys):
        monkeypatch.setitem(sys.modules, "idc_index", _FakeIdcIndex("99.0.0"))
        assert check_version.check_minimum() == "99.0.0"
        assert "meets pinned minimum" in capsys.readouterr().out

    def test_main_exit_code_follows_the_check(self, monkeypatch):
        monkeypatch.setattr(check_version, "notify_updates", lambda _: None)
        monkeypatch.setattr(check_version, "check_minimum", lambda: None)
        assert check_version.main() == 1
        monkeypatch.setattr(check_version, "check_minimum", lambda: "0.12.5")
        assert check_version.main() == 0


class TestNetworkChecksAreBestEffort:
    def test_fetch_json_returns_none_when_unreachable(self):
        # .invalid never resolves (RFC 2606), so this stays offline.
        assert check_version.fetch_json("https://pypi.invalid/pypi/idc-index/json", "info") is None

    def test_notify_updates_survives_an_unreachable_network(self, monkeypatch):
        monkeypatch.setattr(check_version, "fetch_json", lambda *args, **kwargs: None)
        check_version.notify_updates("0.12.5")  # must not raise

    def test_skill_update_notice_is_conservative(self, monkeypatch, capsys):
        # A GitHub tag equal to the shipped version is not an update.
        monkeypatch.setattr(
            check_version, "fetch_json", lambda *args, **kwargs: f"v{check_version.SKILL_VERSION}"
        )
        check_version.notify_updates(None)
        assert "available" not in capsys.readouterr().out


class TestVersionsMatchFrontmatter:
    """The pins in the script and in SKILL.md are read by different consumers."""

    def _frontmatter(self):
        with open(_SKILL_MD, encoding="utf-8") as handle:
            return handle.read().split("---", 2)[1]

    def test_min_version_matches_metadata(self):
        meta = re.search(r'idc-index:\s*"?([\d.]+)"?', self._frontmatter()).group(1)
        assert check_version.MIN_VERSION == meta

    def test_skill_version_matches_metadata(self):
        # `metadata.version` is this repository's skill version; the script pins the
        # upstream release it came from, recorded as `source-skill-version`. The script
        # compares it against upstream's GitHub releases to notify about skill updates,
        # so a stale value points users at a release they already have.
        meta = re.search(
            r"source-skill-version:\s*\"?([\d.]+)\"?", self._frontmatter()
        ).group(1)
        assert check_version.SKILL_VERSION == meta


class _FakeIdcIndex:
    """Stand-in for the real package, so the check runs with nothing installed."""

    def __init__(self, version):
        self.__version__ = version


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
