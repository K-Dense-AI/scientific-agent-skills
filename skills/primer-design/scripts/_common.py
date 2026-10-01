"""Validated local inputs and provenance shared by primer-design tools."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path

IUPAC = "ACGTRYSWKMBDHVN"
PAIR_FIELDS = ("pair_id", "forward", "reverse", "forward_tail", "reverse_tail")


def dna(value: str, label: str, *, ambiguous: bool = False, empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label}: sequence must be a string")
    seq = value.strip().upper()
    if (not seq and not empty) or any(c not in (IUPAC if ambiguous else "ACGT") for c in seq):
        raise ValueError(f"{label}: expected {'IUPAC' if ambiguous else 'ACGT'} DNA, 5-prime to 3-prime, without internal whitespace")
    return seq


def revcomp(seq: str) -> str:
    return seq.translate(str.maketrans(IUPAC, "TGCAYRSWMKVHDBN"))[::-1]


def read_fasta(path) -> dict[str, str]:
    records, chunks, current = {}, [], None
    with Path(path).open(encoding="utf-8-sig") as handle:
        for number, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current is not None:
                    records[current] = dna("".join(chunks), current, ambiguous=True)
                current = line[1:].split()[0] if line[1:].split() else ""
                if not current or current in records:
                    raise ValueError(f"FASTA line {number}: empty or duplicate record ID")
                chunks = []
            else:
                if current is None:
                    raise ValueError(f"FASTA line {number}: sequence before header")
                chunks.append(line)
    if current is not None:
        records[current] = dna("".join(chunks), current, ambiguous=True)
    if not records:
        raise ValueError("FASTA contains no records")
    return records


def read_pairs(path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        header = reader.fieldnames or []
        if len(set(header)) != len(header) or not {"pair_id", "forward", "reverse"} <= set(header):
            raise ValueError("Pair TSV needs unique columns pair_id, forward, reverse; optional forward_tail, reverse_tail")
        if set(header) - set(PAIR_FIELDS):
            raise ValueError(f"Unknown pair TSV columns: {sorted(set(header) - set(PAIR_FIELDS))}")
        result, seen = [], set()
        for number, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Pair TSV line {number}: wrong column count")
            pair_id = row["pair_id"].strip()
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", pair_id) or pair_id in seen:
                raise ValueError(f"Pair TSV line {number}: duplicate or invalid pair_id")
            seen.add(pair_id)
            result.append({"pair_id": pair_id, **{
                field: dna(row.get(field, ""), f"{pair_id}.{field}", empty=field.endswith("_tail"))
                for field in PAIR_FIELDS[1:]
            }})
    if not result:
        raise ValueError("Pair TSV contains no primer pairs")
    return result


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_output_paths(inputs, outputs):
    sources = {Path(p).resolve() for p in inputs if p is not None}
    destinations = [Path(p).resolve() for p in outputs if p is not None]
    if len(set(destinations)) != len(destinations) or sources.intersection(destinations):
        raise ValueError("Output paths must be distinct from each other and all inputs")
    paths = list(sources) + destinations
    for index, path in enumerate(paths):
        if path.exists():
            for other in paths[index + 1:]:
                if other.exists() and path.samefile(other):
                    raise ValueError("Output paths must not be hardlink aliases of inputs or other outputs")


def write_json(path, data):
    """Replace a complete JSON document atomically, never serialize NaN/Infinity."""
    destination = Path(path)
    serialized = json.dumps(data, indent=2, allow_nan=False) + "\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(serialized)
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def load_primer3():
    try:
        import primer3
    except ImportError as exc:
        raise ValueError("primer3-py is not installed; install primer3-py==2.3.1 in an isolated environment") from exc
    return primer3


def finite_number(value, name, minimum=0, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if value < minimum or (positive and value == minimum):
        raise ValueError(f"{name} must be {'greater than' if positive else 'at least'} {minimum}")
    return value


def integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value
