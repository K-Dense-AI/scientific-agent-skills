"""Repo tooling must name its text encoding explicitly.

`scan_skills.py` and `scan_pr_skills.py` write reports full of emoji and
em dashes, and `run_all.py` reads a TOML manifest. `open()`, `read_text()` and
`write_text()` without `encoding=` use the locale codec, which is cp1252 on
Windows: writing a report there raises UnicodeEncodeError. Read this
statically, like `test_console_output.py`, so it needs no scanner packages.
"""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

TOOLING = [
    *REPO_ROOT.glob("*.py"),
    *(REPO_ROOT / "scripts").glob("*.py"),
    *(REPO_ROOT / "tests").glob("*.py"),
    *(REPO_ROOT / "tests" / "_contract").glob("*.py"),
]


def _mode(call: ast.Call, position: int) -> str | None:
    """The literal text-or-binary mode of an open() call, if it has one."""
    node = call.args[position] if len(call.args) > position else None
    for keyword in call.keywords:
        if keyword.arg == "mode":
            node = keyword.value
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _missing_encoding(call: ast.Call) -> bool:
    if any(keyword.arg == "encoding" for keyword in call.keywords):
        return False
    func = call.func
    if isinstance(func, ast.Name) and func.id == "open":
        mode = _mode(call, 1)
        return mode is None or "b" not in mode
    if isinstance(func, ast.Attribute):
        # Path.open() takes the mode first; Path.read_text/write_text are text only.
        if func.attr == "open":
            mode = _mode(call, 0)
            return mode is None or "b" not in mode
        return func.attr in {"read_text", "write_text"}
    return False


def test_tooling_text_io_names_its_encoding():
    assert TOOLING, "no tooling files found -- the anchor is wrong"
    failures = []
    for path in sorted(TOOLING):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _missing_encoding(node):
                failures.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
    assert not failures, "text I/O without encoding=:\n" + "\n".join(failures)
