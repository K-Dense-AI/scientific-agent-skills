"""Shared I/O, formatting, and reporting helpers for the pkpd-modeling scripts.

Every script in this skill follows the same contract:

* data goes to **stdout**, provenance and findings go to **stderr**, so
  ``script.py ... > out.tsv`` keeps them apart;
* ``--format table|tsv|json`` selects the stdout rendering, and ``json`` is
  self-contained (it carries findings and notes too, because a machine reading
  stdout should not have to also parse stderr);
* exit status is ``0`` when nothing was flagged, ``1`` when at least one
  finding was raised, and ``2`` for unusable input — so any script can gate a
  pipeline.

Nothing here does pharmacology. The numerics live in ``_models.py`` and in the
individual scripts; this module only moves tables around.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_INPUT = 2

_MISSING = {"", ".", "na", "n/a", "nan", "null", "none", "-"}


class InputError(Exception):
    """Unusable input. Callers map this to exit code 2."""


# --------------------------------------------------------------- formatting


def fmt(value: Any, digits: int = 6) -> str:
    """Render a value for a fixed-width table without lying about precision."""
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, str):
        return value
    if isinstance(value, (int,)):
        return str(value)
    try:
        x = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(x):
        return "n/a"
    if math.isinf(x):
        return "inf" if x > 0 else "-inf"
    if x == 0:
        return "0"
    return f"{x:.{digits}g}"


def parse_float(text: Any, field_name: str = "value", allow_missing: bool = False):
    """Parse a float, treating the usual missing-value spellings as ``None``."""
    if text is None:
        if allow_missing:
            return None
        raise InputError(f"{field_name}: missing")
    if isinstance(text, (int, float)):
        x = float(text)
        if math.isnan(x) and allow_missing:
            return None
        if not math.isfinite(x):
            raise InputError(f"{field_name}: must be finite")
        return x
    s = str(text).strip()
    if s.lower() in _MISSING:
        if allow_missing:
            return None
        raise InputError(f"{field_name}: missing")
    try:
        x = float(s)
        if not math.isfinite(x):
            raise InputError(f"{field_name}: must be finite")
        return x
    except ValueError as exc:
        raise InputError(f"{field_name}: {s!r} is not a number") from exc


def parse_positive(text: Any, field_name: str) -> float:
    x = parse_float(text, field_name)
    if x is None or x <= 0:
        raise InputError(f"{field_name}: must be greater than zero, got {text!r}")
    return x


# ------------------------------------------------------------------- tables


def _sniff_delimiter(sample: str, path: Path) -> str:
    if path.suffix.lower() in {".tsv", ".tab"}:
        return "\t"
    if path.suffix.lower() == ".csv":
        return ","
    counts = {d: sample.count(d) for d in (",", "\t", ";")}
    return max(counts, key=lambda d: counts[d]) if max(counts.values()) else ","


def read_table(source: str | Path) -> list[dict[str, str]]:
    """Read a delimited table into a list of row dicts.

    Accepts ``-`` for stdin. Column names are lower-cased and stripped so a
    file with ``Time`` and one with ``TIME`` behave the same; blank lines and
    lines beginning with ``#`` are skipped, which lets a fixture carry a
    provenance header.
    """
    if str(source) == "-":
        text = sys.stdin.read()
        path = Path("stdin.csv")
    else:
        path = Path(source)
        if not path.is_file():
            raise InputError(f"no such file: {path}")
        text = path.read_text(encoding="utf-8-sig")

    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        raise InputError(f"{path}: no data rows")

    delimiter = _sniff_delimiter(lines[0], path)
    reader = csv.DictReader(lines, delimiter=delimiter)
    if not reader.fieldnames:
        raise InputError(f"{path}: no header row")

    fieldnames = [(name or "").strip().lower() for name in reader.fieldnames]
    if len(set(fieldnames)) != len(fieldnames):
        dupes = sorted({n for n in fieldnames if fieldnames.count(n) > 1})
        raise InputError(f"{path}: duplicate column names: {', '.join(dupes)}")

    rows: list[dict[str, str]] = []
    for raw in reader:
        row = {}
        for key, value in zip(fieldnames, (raw.get(orig) for orig in reader.fieldnames)):
            row[key] = (value or "").strip()
        rows.append(row)
    if not rows:
        raise InputError(f"{path}: header only, no data rows")
    return rows


def require_columns(rows: Sequence[Mapping[str, Any]], required: Iterable[str], where: str) -> None:
    present = set(rows[0].keys())
    missing = [c for c in required if c not in present]
    if missing:
        raise InputError(
            f"{where}: missing required column(s): {', '.join(missing)}. "
            f"Found: {', '.join(sorted(present))}"
        )


def column(rows: Sequence[Mapping[str, Any]], name: str, allow_missing: bool = False) -> list:
    return [parse_float(r.get(name), f"{name} (row {i + 1})", allow_missing) for i, r in enumerate(rows)]


def group_by(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, list[Mapping[str, Any]]]:
    """Stable grouping that preserves first-seen order of the keys."""
    out: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        out.setdefault(str(row.get(key, "")).strip(), []).append(row)
    return out


# ------------------------------------------------------------------ reports


@dataclass
class Table:
    title: str
    rows: list[dict[str, Any]]
    columns: list[str] | None = None

    def headers(self) -> list[str]:
        if self.columns:
            return list(self.columns)
        seen: list[str] = []
        for row in self.rows:
            for key in row:
                if key not in seen:
                    seen.append(key)
        return seen


@dataclass
class Report:
    """Accumulates output, then renders it once at the end.

    Findings are the reason a script exits non-zero. They are deliberately
    plain sentences rather than codes: they are read by a person deciding
    whether an analysis is defensible.
    """

    tables: list[Table] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    scalars: dict[str, Any] = field(default_factory=dict)

    def table(self, title: str, rows: Sequence[Mapping[str, Any]], columns: Sequence[str] | None = None) -> None:
        self.tables.append(Table(title, [dict(r) for r in rows], list(columns) if columns else None))

    def scalar(self, name: str, value: Any) -> None:
        self.scalars[name] = value

    def note(self, text: str) -> None:
        self.notes.append(text)

    def finding(self, text: str) -> None:
        self.findings.append(text)

    # -- rendering

    def _render_table(self, table: Table) -> str:
        headers = table.headers()
        cells = [[fmt(row.get(h)) for h in headers] for row in table.rows]
        widths = [len(h) for h in headers]
        for line in cells:
            for i, value in enumerate(line):
                widths[i] = max(widths[i], len(value))
        out = [""]
        if table.title:
            out.append(table.title)
        out.append("  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)).rstrip())
        for line in cells:
            out.append("  ".join(v.ljust(widths[i]) for i, v in enumerate(line)).rstrip())
        return "\n".join(out)

    def emit(self, fmt_name: str, stream=None, err=None) -> int:
        stream = stream or sys.stdout
        err = err or sys.stderr

        if fmt_name == "json":
            payload = {
                "scalars": self.scalars,
                "tables": [
                    {"title": t.title, "columns": t.headers(), "rows": t.rows} for t in self.tables
                ],
                "findings": self.findings,
                "notes": self.notes,
            }
            print(json.dumps(_json_finite(payload), indent=2, allow_nan=False, default=_json_default), file=stream)
        elif fmt_name == "tsv":
            for key, value in self.scalars.items():
                print(f"{key}\t{fmt(value)}", file=stream)
            for table in self.tables:
                headers = table.headers()
                print("\t".join(headers), file=stream)
                for row in table.rows:
                    print("\t".join(fmt(row.get(h)) for h in headers), file=stream)
        else:
            if self.scalars:
                width = max(len(k) for k in self.scalars)
                for key, value in self.scalars.items():
                    print(f"{key.ljust(width)}  {fmt(value)}", file=stream)
            for table in self.tables:
                print(self._render_table(table), file=stream)

        if fmt_name != "json":
            for note in self.notes:
                print(f"note: {note}", file=err)
            for finding in self.findings:
                print(f"finding: {finding}", file=err)

        return EXIT_FINDINGS if self.findings else EXIT_OK


def _json_finite(obj: Any) -> Any:
    """Missing numerical diagnostics become JSON null, never nonstandard NaN/Infinity."""
    if isinstance(obj, dict):
        return {k: _json_finite(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_finite(v) for v in obj]
    if hasattr(obj, "tolist"):
        return _json_finite(obj.tolist())
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def validate_numeric_args(args: argparse.Namespace) -> None:
    """Reject nonfinite CLI scalars before they enter a numerical model."""
    for name, value in vars(args).items():
        values = value if isinstance(value, (list, tuple)) else [value]
        if any(isinstance(v, float) and not math.isfinite(v) for v in values):
            raise InputError(f"--{name.replace('_', '-')}: must be finite")


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "item"):  # numpy scalar
        return obj.item()
    if hasattr(obj, "tolist"):  # numpy array
        return obj.tolist()
    if isinstance(obj, float) and math.isnan(obj):
        return None
    raise TypeError(f"not JSON serialisable: {type(obj).__name__}")


# --------------------------------------------------------------------- CLI


def add_format_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("table", "tsv", "json"),
        default="table",
        help="stdout rendering (default: table). json is self-contained.",
    )


def main_wrapper(func, argv: Sequence[str] | None = None) -> int:
    """Run a script body, mapping InputError to exit code 2.

    Keeps the ``if __name__`` block in every script down to one line and makes
    the exit-code contract impossible to get wrong in one script and right in
    another.
    """
    try:
        return func(argv)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT
    except BrokenPipeError:  # `| head`
        return EXIT_OK


__all__ = [
    "EXIT_OK",
    "EXIT_FINDINGS",
    "EXIT_INPUT",
    "InputError",
    "Report",
    "Table",
    "add_format_argument",
    "column",
    "fmt",
    "group_by",
    "main_wrapper",
    "parse_float",
    "parse_positive",
    "read_table",
    "require_columns",
]
