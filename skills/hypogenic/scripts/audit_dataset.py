#!/usr/bin/env python3
"""Audit pinned HypoGeniC dataset files, schemas, splits, and duplicates."""

from __future__ import annotations

import argparse
import hashlib
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__:
    from ._common import (
        MAX_CONFIG_BYTES,
        MAX_JSON_BYTES,
        MAX_ROWS,
        CliError,
        bounded_int,
        canonical_json_bytes,
        checked_input_file,
        checked_root,
        count_values,
        emit_error,
        emit_json,
        load_json_document,
        resolve_manifest_path,
        sha256_file,
        validate_dataset_manifest,
    )
else:
    from _common import (  # type: ignore
        MAX_CONFIG_BYTES,
        MAX_JSON_BYTES,
        MAX_ROWS,
        CliError,
        bounded_int,
        canonical_json_bytes,
        checked_input_file,
        checked_root,
        count_values,
        emit_error,
        emit_json,
        load_json_document,
        resolve_manifest_path,
        sha256_file,
        validate_dataset_manifest,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit immutable local dataset files without network access and without "
            "rendering or following instructions in dataset text."
        )
    )
    parser.add_argument("--manifest", required=True, help="Strict local manifest JSON")
    parser.add_argument(
        "--manifest-root",
        default=".",
        help="Existing boundary containing the manifest",
    )
    parser.add_argument(
        "--data-root",
        default=None,
        help=(
            "Existing pinned dataset directory. If omitted, use manifest.root "
            "beneath --manifest-root."
        ),
    )
    parser.add_argument(
        "--max-file-bytes",
        type=int,
        default=MAX_JSON_BYTES,
        help=f"Per-split byte cap (default {MAX_JSON_BYTES})",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=100_000,
        help="Per-split row cap (default 100000)",
    )
    parser.add_argument(
        "--max-evidence-groups",
        type=int,
        default=20,
        help="Maximum hashed duplicate groups reported per category",
    )
    return parser


def _data_root_from_manifest(
    manifest_root: str,
    relative_root: str,
) -> Path:
    base = checked_root(manifest_root)
    candidate = base / relative_root
    current = base
    for part in Path(relative_root).parts:
        current /= part
        if current.is_symlink():
            raise CliError(f"manifest root contains a symlink: {part!r}")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(base)
    except (OSError, ValueError) as exc:
        raise CliError("manifest root is not an existing directory within its boundary") from exc
    return checked_root(resolved)


def _field_names(row: Mapping[str, Any], *, context: str) -> tuple[str, ...]:
    if not row or len(row) > 128:
        raise CliError(f"{context} must contain 1 to 128 fields")
    fields: list[str] = []
    for key in row:
        if not isinstance(key, str) or not key or len(key) > 128:
            raise CliError(f"{context} contains an invalid field name")
        fields.append(key)
    return tuple(fields)


def _rows_from_document(
    document: Any,
    *,
    max_rows: int,
    split_name: str,
) -> tuple[list[dict[str, Any]], str]:
    """Normalize upstream column-oriented JSON or a strict list of row objects."""

    if isinstance(document, dict):
        fields = _field_names(document, context=f"{split_name} columns")
        columns: dict[str, list[Any]] = {}
        lengths: set[int] = set()
        for field in fields:
            value = document[field]
            if not isinstance(value, list):
                raise CliError(f"{split_name}.{field} must be a list")
            columns[field] = value
            lengths.add(len(value))
        if len(lengths) != 1:
            raise CliError(f"{split_name} columns do not have equal lengths")
        row_count = next(iter(lengths))
        if row_count == 0 or row_count > max_rows:
            raise CliError(f"{split_name} must contain 1 to {max_rows} rows")
        rows = [
            {field: columns[field][index] for field in fields}
            for index in range(row_count)
        ]
        return rows, "column_oriented"

    if isinstance(document, list):
        if not document or len(document) > max_rows:
            raise CliError(f"{split_name} must contain 1 to {max_rows} rows")
        if not all(isinstance(row, dict) for row in document):
            raise CliError(f"{split_name} row-oriented data must contain only objects")
        first_fields = _field_names(document[0], context=f"{split_name}[0]")
        field_set = set(first_fields)
        rows = []
        for index, row in enumerate(document):
            if set(row) != field_set:
                raise CliError(f"{split_name}[{index}] has a different schema")
            rows.append(dict(row))
        return rows, "row_oriented"

    raise CliError(
        f"{split_name} JSON root must be a column object or a list of row objects"
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _bounded_groups(
    groups: Mapping[str, list[tuple[str, int]]],
    *,
    maximum: int,
    cross_split_only: bool,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if maximum == 0:
        return result
    for digest in sorted(groups):
        occurrences = groups[digest]
        split_names = sorted({split for split, _ in occurrences})
        if cross_split_only and len(split_names) < 2:
            continue
        if not cross_split_only and len(occurrences) < 2:
            continue
        result.append(
            {
                "sha256": digest,
                "splits": split_names,
                "occurrence_count": len(occurrences),
                "occurrences": [
                    {"split": split, "row_index": index}
                    for split, index in occurrences[:20]
                ],
                "occurrences_truncated": len(occurrences) > 20,
            }
        )
        if len(result) >= maximum:
            break
    return result


def audit(
    manifest: dict[str, Any],
    *,
    data_root: Path,
    max_file_bytes: int,
    max_rows: int,
    max_evidence_groups: int,
    manifest_sha256: str,
) -> dict[str, Any]:
    label_field = manifest["label_field"]
    identity_fields = manifest["identity_fields"]
    exact_groups: dict[str, list[tuple[str, int]]] = defaultdict(list)
    identity_groups: dict[str, list[tuple[str, int]]] = defaultdict(list)
    split_reports: list[dict[str, Any]] = []
    schemas: dict[str, tuple[str, ...]] = {}
    checksum_failures: list[str] = []
    within_split_duplicate_extras = 0

    for split in manifest["splits"]:
        name = split["name"]
        path = resolve_manifest_path(
            split["path"],
            data_root=data_root,
            suffixes={".json"},
            max_bytes=max_file_bytes,
        )
        actual_sha256 = sha256_file(path, max_bytes=max_file_bytes)
        checksum_matches = actual_sha256 == split["sha256"]
        if not checksum_matches:
            checksum_failures.append(name)
        document = load_json_document(
            split["path"],
            root=data_root,
            max_bytes=max_file_bytes,
        )
        rows, layout = _rows_from_document(
            document,
            max_rows=max_rows,
            split_name=name,
        )
        schema = tuple(rows[0])
        schemas[name] = schema
        missing = [
            field for field in [label_field, *identity_fields] if field not in schema
        ]
        if missing:
            raise CliError(f"{name} is missing manifest fields: {', '.join(missing)}")

        labels: list[str] = []
        split_exact = Counter()
        for index, row in enumerate(rows):
            label = row[label_field]
            if not isinstance(label, str) or not label or len(label) > 256:
                raise CliError(f"{name}[{index}].{label_field} must be a bounded string")
            labels.append(label)
            exact = _digest(row)
            identity = _digest({field: row[field] for field in identity_fields})
            exact_groups[exact].append((name, index))
            identity_groups[identity].append((name, index))
            split_exact[exact] += 1
        duplicates = sum(count - 1 for count in split_exact.values() if count > 1)
        within_split_duplicate_extras += duplicates
        split_reports.append(
            {
                "name": name,
                "path": split["path"],
                "layout": layout,
                "row_count": len(rows),
                "field_count": len(schema),
                "fields": list(schema),
                "label_counts_redacted": count_values(labels),
                "expected_sha256": split["sha256"],
                "actual_sha256": actual_sha256,
                "checksum_matches": checksum_matches,
                "within_split_exact_duplicate_extra_rows": duplicates,
                "raw_text_included": False,
            }
        )

    schema_sets = {tuple(sorted(schema)) for schema in schemas.values()}
    schemas_match = len(schema_sets) == 1
    cross_exact_all = {
        digest: occurrences
        for digest, occurrences in exact_groups.items()
        if len({split for split, _ in occurrences}) > 1
    }
    cross_identity_all = {
        digest: occurrences
        for digest, occurrences in identity_groups.items()
        if len({split for split, _ in occurrences}) > 1
    }
    ok = (
        not checksum_failures
        and schemas_match
        and not cross_exact_all
        and not cross_identity_all
    )
    warnings: list[str] = []
    if within_split_duplicate_extras:
        warnings.append("within-split exact duplicates were found")
    if not schemas_match:
        warnings.append("split schemas differ")
    return {
        "ok": ok,
        "audit_kind": "hypogenic_dataset_local_audit",
        "schema_version": manifest["schema_version"],
        "manifest_sha256": manifest_sha256,
        "source": manifest["source"],
        "data_root_redacted": True,
        "label_field": label_field,
        "identity_fields": identity_fields,
        "splits": split_reports,
        "checksums": {
            "all_match": not checksum_failures,
            "failed_splits": checksum_failures,
        },
        "schemas_match_across_splits": schemas_match,
        "duplicates": {
            "within_split_exact_duplicate_extra_rows": within_split_duplicate_extras,
            "cross_split_exact_group_count": len(cross_exact_all),
            "cross_split_identity_group_count": len(cross_identity_all),
            "cross_split_exact_evidence": _bounded_groups(
                cross_exact_all,
                maximum=max_evidence_groups,
                cross_split_only=True,
            ),
            "cross_split_identity_evidence": _bounded_groups(
                cross_identity_all,
                maximum=max_evidence_groups,
                cross_split_only=True,
            ),
            "evidence_is_hashes_and_indices_only": True,
        },
        "split_policy": {
            "preserved": ok and not cross_identity_all,
            "train_use": "generation_and_update",
            "validation_use": "selection_only",
            "test_use": "locked_until_final_evaluation",
        },
        "warnings": warnings,
        "dataset_text_interpreted_as_instructions": False,
        "raw_dataset_text_included": False,
        "network_access": False,
        "model_called": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        max_file_bytes = bounded_int(
            args.max_file_bytes,
            name="max_file_bytes",
            minimum=1,
            maximum=MAX_JSON_BYTES,
        )
        max_rows = bounded_int(
            args.max_rows,
            name="max_rows",
            minimum=1,
            maximum=MAX_ROWS,
        )
        max_evidence = bounded_int(
            args.max_evidence_groups,
            name="max_evidence_groups",
            minimum=0,
            maximum=1000,
        )
        manifest_path = checked_input_file(
            args.manifest,
            root=args.manifest_root,
            suffixes={".json"},
            max_bytes=MAX_CONFIG_BYTES,
        )
        manifest = validate_dataset_manifest(
            load_json_document(
                args.manifest,
                root=args.manifest_root,
                max_bytes=MAX_CONFIG_BYTES,
            )
        )
        data_root = (
            checked_root(args.data_root)
            if args.data_root is not None
            else _data_root_from_manifest(args.manifest_root, manifest["root"])
        )
        report = audit(
            manifest,
            data_root=data_root,
            max_file_bytes=max_file_bytes,
            max_rows=max_rows,
            max_evidence_groups=max_evidence,
            manifest_sha256=sha256_file(
                manifest_path,
                max_bytes=MAX_CONFIG_BYTES,
            ),
        )
        emit_json(report)
        return 0 if report["ok"] else 3
    except (CliError, OSError) as error:
        return emit_error(error)


if __name__ == "__main__":
    raise SystemExit(main())
