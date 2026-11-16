"""Official gene/transcript datasets, cached as archives without extracting paths."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

from transport import BASE, RMBaseError, atomic_write, utc_now

COUNTS = ("m6a", "m1a", "m5c", "m7g", "pseudo", "nm", "editing", "other")
MAX_ARCHIVE = 64_000_000
MAX_EXPANDED = 256_000_000


def dataset_route(assembly, kind):
    folder = "geneFiles" if kind == "genes" else "transFiles"
    return f"download/modGene/{folder}/{kind}.{assembly}.tar.gz"


def parse_row(line, kind="genes"):
    cols = line.rstrip("\r\n").split("\t")
    if len(cols) != 22:
        raise RMBaseError("dataset_schema_changed", "Expected 22 columns in the official gene/transcript dataset.", 4)
    keys = ("geneID", "geneName", "transID") if kind == "genes" else ("transID", "geneID", "geneName")
    row = dict(zip(keys, cols[:3]))
    row.update(geneType=cols[3], region=cols[4])
    try:
        for i, name in enumerate(COUNTS):
            row[name + "Num"] = int(cols[5 + i * 2])
            row[name + "List"] = [] if cols[6 + i * 2] in {"na", ""} else cols[6 + i * 2].split(",")
            if row[name + "Num"] < 0:
                raise ValueError("negative count")
        row["totalNum"] = int(cols[21])
        if row["totalNum"] < 0:
            raise ValueError("negative total")
    except ValueError as exc:
        raise RMBaseError("dataset_schema_changed", "Invalid modification count in dataset.", 4) from exc
    return row


def archive_rows(raw, kind):
    """Reject links, multiple tables, and unbounded decompression; never extractall."""
    if len(raw) > MAX_ARCHIVE:
        raise RMBaseError("dataset_too_large", "Compressed dataset exceeds 64 MB.", 5)
    files = 0
    expanded = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r|gz") as archive:
            for member in archive:
                expanded += member.size
                if expanded > MAX_EXPANDED or member.issym() or member.islnk():
                    raise RMBaseError("unsafe_archive", "Dataset contains links or exceeds the expansion limit.", 5)
                if member.isdir():
                    continue
                if not member.isfile() or not member.name.endswith((".txt", ".tsv")):
                    raise RMBaseError("dataset_schema_changed", "Unexpected file in gene/transcript archive.", 4)
                files += 1
                if files > 1:
                    raise RMBaseError("dataset_schema_changed", "Expected one data table per archive.", 4)
                stream = archive.extractfile(member)
                for raw_line in stream:
                    if len(raw_line) > 2_000_000:
                        raise RMBaseError("dataset_too_large", "Dataset row exceeds the safety limit.", 5)
                    if raw_line.strip():
                        yield parse_row(raw_line.decode("utf-8"), kind)
            if files != 1:
                raise RMBaseError("dataset_schema_changed", "Archive contains no data table.", 4)
    except (tarfile.TarError, UnicodeDecodeError, EOFError, OSError) as exc:
        raise RMBaseError("invalid_archive", "Could not read the official dataset format.", 4) from exc


class Datasets:
    def __init__(self, transport):
        self.transport = transport
        self.root = transport.cache_dir / "datasets"

    def paths(self, assembly, kind):
        stem = self.root / f"{kind}.{assembly}"
        return Path(str(stem) + ".tar.gz"), Path(str(stem) + ".json")

    def available(self, assembly, kind="genes"):
        archive, metadata = self.paths(assembly, kind)
        return archive.exists() and metadata.exists()

    def sync(self, assembly, kind="genes", archive_path=None):
        route = dataset_route(assembly, kind)
        if archive_path:
            path = Path(archive_path)
            if path.stat().st_size > MAX_ARCHIVE:
                raise RMBaseError("dataset_too_large", "Imported archive exceeds 64 MB.", 5)
            raw = path.read_bytes()
            source = {"kind": "user_supplied_archive", "retrieved_at": None,
                      "expected_download_url": BASE + route,
                      "warning": "Imported content is schema-checked; its origin was not authenticated."}
        elif self.available(assembly, kind) and not self.transport.refresh:
            # Verify the checksum before reporting a reusable cache.
            _, meta = self.load(assembly, kind)
            return meta
        else:
            raw = self.transport.request(route, cache=False, max_bytes=MAX_ARCHIVE)
            source = self.transport.sources[-1]
        count = sum(1 for _ in archive_rows(raw, kind))
        meta = {"rmbase_version": "3.0", "dataset_version": None, "assembly": assembly,
                "kind": kind, "source": source, "cached_at": utc_now(),
                "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "rows": count}
        archive, metadata = self.paths(assembly, kind)
        atomic_write(archive, raw)
        atomic_write(metadata, json.dumps(meta, sort_keys=True).encode())
        return meta

    def load(self, assembly, kind="genes"):
        archive, metadata = self.paths(assembly, kind)
        if not self.available(assembly, kind):
            raise RMBaseError("dataset_missing", "Run sync for this assembly and dataset kind first.", 6)
        try:
            meta = json.loads(metadata.read_text(encoding="utf-8"))
            if archive.stat().st_size > MAX_ARCHIVE:
                raise RMBaseError("dataset_too_large", "Cached archive exceeds 64 MB.", 5)
            raw = archive.read_bytes()
            if (hashlib.sha256(raw).hexdigest() != meta["sha256"]
                    or meta["assembly"] != assembly or meta["kind"] != kind):
                raise RMBaseError("cache_corrupt", "Dataset checksum or assembly mismatch.", 6)
        except (ValueError, KeyError, TypeError) as exc:
            raise RMBaseError("cache_corrupt", "Invalid dataset metadata.", 6) from exc
        return raw, meta

    def query(self, query, assembly, mode="genename", kind="genes"):
        raw, meta = self.load(assembly, kind)
        field = {"genename": "geneName", "geneid": "geneID", "transcript": "transID"}[mode]
        # Consume the whole stream, so corruption after the matching row is detected.
        rows = [row for row in archive_rows(raw, kind) if row[field] == query]
        self.transport.sources.append({"mode": "LOCAL_DATASET", **meta})
        return rows
