"""Catch console glyphs that crash Python on legacy Windows output streams.

Inspect literal print/log messages without importing scientific packages or
constraining Unicode in documentation, image prompts, or generated artifacts.
Dynamic data (such as user-supplied filenames) needs runtime coverage separately.
"""

import ast
from pathlib import Path


SKILLS = Path(__file__).resolve().parents[2] / "skills"


def _literal_output(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node
    elif isinstance(node, ast.JoinedStr):
        for part in node.values:
            yield from _literal_output(part)
    elif isinstance(node, ast.FormattedValue):
        yield from _literal_output(node.value)
    elif isinstance(node, ast.IfExp):
        yield from _literal_output(node.body)
        yield from _literal_output(node.orelse)
    # Do not inspect arbitrary calls: their arguments need not be printed,
    # and serializers may escape Unicode before returning a console string.


def test_literal_console_messages_fit_cp1252():
    failures = []
    for path in sorted(SKILLS.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            console_call = (
                isinstance(node.func, ast.Name) and node.func.id == "print"
            ) or (
                isinstance(node.func, ast.Attribute) and node.func.attr == "_log"
            )
            if not console_call:
                continue
            for argument in node.args:
                for literal in _literal_output(argument):
                    try:
                        literal.value.encode("cp1252")
                    except UnicodeEncodeError:
                        failures.append(f"{path.relative_to(SKILLS)}:{literal.lineno}")
    assert not failures, "Console literals cannot encode as cp1252:\n" + "\n".join(failures)
