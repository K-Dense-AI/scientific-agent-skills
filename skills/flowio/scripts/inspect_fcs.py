#!/usr/bin/env python3
"""Inspect local FCS files with FlowIO without network or environment access.

Metadata-only parsing is the default. Event statistics are opt-in because
FlowIO loads each dataset into memory and ``as_array`` allocates another array.
Statistics first perform a metadata-only pass so an estimated array-memory
limit can be enforced before DATA is loaded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterator, Optional

import numpy as np
import flowio
from flowio import FlowData
from flowio.exceptions import FlowIOException, MultipleDataSetsError


DEFAULT_MAX_BYTES = 2_000_000_000
DEFAULT_MAX_ARRAY_BYTES = 512_000_000
DEFAULT_MAX_DATASETS = 128


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect FCS structure and channels as JSON. Event data is not "
            "loaded unless --stats is supplied."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="local FCS file")
    parser.add_argument(
        "--output",
        type=Path,
        help="write JSON to a new file instead of stdout; refuses overwrite",
    )
    parser.add_argument(
        "--include-text",
        action="store_true",
        help="include all normalized TEXT metadata (may contain identifiers)",
    )
    parser.add_argument(
        "--include-analysis",
        action="store_true",
        help="include all normalized ANALYSIS metadata (may contain identifiers)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="load events and calculate per-channel finite-value statistics",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="with --stats, use encoded values (preprocess=False)",
    )
    parser.add_argument(
        "--sha256",
        action="store_true",
        help="calculate a SHA-256 checksum (requires a full additional file read)",
    )
    parser.add_argument(
        "--max-bytes",
        type=nonnegative_int,
        default=DEFAULT_MAX_BYTES,
        help="reject larger inputs before parsing; use 0 to disable",
    )
    parser.add_argument(
        "--max-array-bytes",
        type=nonnegative_int,
        default=DEFAULT_MAX_ARRAY_BYTES,
        help=(
            "with --stats, reject a dataset whose estimated float64 array "
            "exceeds this size; use 0 to disable"
        ),
    )
    parser.add_argument(
        "--max-datasets",
        type=positive_int,
        default=DEFAULT_MAX_DATASETS,
        help="stop suspicious or unexpectedly long multi-dataset chains",
    )
    parser.add_argument(
        "--null-channel",
        action="append",
        default=[],
        metavar="PNN",
        help=(
            "PnN label to classify as null; repeat for multiple labels. "
            "The event column is retained."
        ),
    )
    parser.add_argument(
        "--ignore-offset-error",
        action="store_true",
        help="allow a known off-by-one DATA end offset and review warnings",
    )
    parser.add_argument(
        "--ignore-offset-discrepancy",
        action="store_true",
        help="use TEXT offsets when HEADER/TEXT offsets differ",
    )
    parser.add_argument(
        "--use-header-offsets",
        action="store_true",
        help="use HEADER DATA offsets and suppress offset-discrepancy errors",
    )
    return parser


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_datasets(
    path: Path,
    *,
    max_datasets: int,
    null_channel_list: list[str],
    ignore_offset_error: bool,
    ignore_offset_discrepancy: bool,
    use_header_offsets: bool,
) -> Iterator[tuple[int, int, FlowData]]:
    """Yield metadata-only datasets for safe offset and memory inspection."""

    offset = 0
    file_size = path.stat().st_size

    for dataset_index in range(max_datasets):
        flow = FlowData(
            path,
            ignore_offset_error=ignore_offset_error,
            ignore_offset_discrepancy=ignore_offset_discrepancy,
            use_header_offsets=use_header_offsets,
            only_text=True,
            nextdata_offset=offset,
            null_channel_list=null_channel_list,
        )
        yield dataset_index, offset, flow

        relative_offset = int(flow.text.get("nextdata", "0"))
        if relative_offset == 0:
            return
        if relative_offset < 0:
            raise MultipleDataSetsError(
                "input contains a negative relative offset to the next dataset"
            )

        next_offset = offset + relative_offset
        if next_offset <= offset:
            raise MultipleDataSetsError(
                "input contains a non-increasing multi-dataset offset"
            )
        if next_offset >= file_size:
            raise MultipleDataSetsError(
                "next dataset offset is outside the input file"
            )
        offset = next_offset

    raise MultipleDataSetsError(
        f"input exceeds the --max-datasets limit ({max_datasets})"
    )


def channel_kind(flow: FlowData, array_index: int) -> str:
    if flow.pnn_labels[array_index] in flow.null_channels:
        return "null"
    if array_index == flow.time_index:
        return "time"
    if array_index in flow.scatter_indices:
        return "scatter"
    if array_index in flow.fluoro_indices:
        return "fluorescence"
    return "other"


def channel_records(flow: FlowData) -> list[dict[str, Any]]:
    records = []
    for array_index, pnn in enumerate(flow.pnn_labels):
        parameter_number = array_index + 1
        metadata = flow.channels[parameter_number]
        records.append(
            {
                "array_index": array_index,
                "parameter_number": parameter_number,
                "pnn": pnn,
                "pns": flow.pns_labels[array_index],
                "kind": channel_kind(flow, array_index),
                "pne": list(metadata["pne"]),
                "png": metadata["png"],
                "pnr": metadata["pnr"],
            }
        )
    return records


def finite_statistics(
    events: np.ndarray,
    labels: list[str],
) -> list[dict[str, Any]]:
    records = []
    for array_index, label in enumerate(labels):
        values = events[:, array_index]
        finite_mask = np.isfinite(values)
        finite_values = values[finite_mask]
        records.append(
            {
                "array_index": array_index,
                "pnn": label,
                "finite_count": int(finite_mask.sum()),
                "nan_count": int(np.isnan(values).sum()),
                "positive_infinity_count": int(np.isposinf(values).sum()),
                "negative_infinity_count": int(np.isneginf(values).sum()),
                "minimum": (
                    float(finite_values.min()) if finite_values.size else None
                ),
                "maximum": (
                    float(finite_values.max()) if finite_values.size else None
                ),
                "mean": (
                    float(finite_values.mean()) if finite_values.size else None
                ),
            }
        )
    return records


def dataset_record(
    dataset_index: int,
    offset: int,
    flow: FlowData,
    *,
    include_text: bool,
    include_analysis: bool,
    stats: bool,
    raw: bool,
    estimated_array_bytes: int,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "dataset_index": dataset_index,
        "byte_offset": offset,
        "fcs_version": flow.version,
        "data_type": flow.data_type,
        "event_count": flow.event_count,
        "channel_count": flow.channel_count,
        "estimated_array_bytes": estimated_array_bytes,
        "channels": channel_records(flow),
        "metadata_summary": {
            "text_key_count": len(flow.text),
            "analysis_key_count": len(flow.analysis),
            "has_acquisition_date": "date" in flow.text,
            "has_instrument": "cyt" in flow.text,
            "has_spillover": (
                "spillover" in flow.text or "spill" in flow.text
            ),
            "nextdata": flow.text.get("nextdata", "0"),
        },
    }

    if include_text:
        record["text"] = flow.text
    if include_analysis:
        record["analysis"] = flow.analysis

    if stats:
        events = flow.as_array(preprocess=not raw)
        record["event_semantics"] = (
            "encoded DATA values reshaped; preprocess=False"
            if raw
            else "gain/log/time scaled; uncompensated; ungated"
        )
        record["array_shape"] = list(events.shape)
        record["statistics"] = finite_statistics(events, flow.pnn_labels)
    else:
        record["event_semantics"] = "not loaded; metadata-only inspection"

    return record


def inspect_file(args: argparse.Namespace) -> dict[str, Any]:
    path = args.input.expanduser()
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise ValueError(f"input is not a regular file: {path}")

    size_bytes = path.stat().st_size
    if args.max_bytes and size_bytes > args.max_bytes:
        raise ValueError(
            f"input is {size_bytes} bytes, above --max-bytes={args.max_bytes}"
        )

    datasets = []
    for dataset_index, offset, metadata_flow in iter_datasets(
        path,
        max_datasets=args.max_datasets,
        null_channel_list=args.null_channel,
        ignore_offset_error=args.ignore_offset_error,
        ignore_offset_discrepancy=args.ignore_offset_discrepancy,
        use_header_offsets=args.use_header_offsets,
    ):
        estimated_array_bytes = (
            metadata_flow.event_count * metadata_flow.channel_count * 8
        )
        if (
            args.stats
            and args.max_array_bytes
            and estimated_array_bytes > args.max_array_bytes
        ):
            raise ValueError(
                f"dataset {dataset_index} needs an estimated "
                f"{estimated_array_bytes} bytes for as_array(), above "
                f"--max-array-bytes={args.max_array_bytes}"
            )

        flow = metadata_flow
        if args.stats:
            flow = FlowData(
                path,
                ignore_offset_error=args.ignore_offset_error,
                ignore_offset_discrepancy=args.ignore_offset_discrepancy,
                use_header_offsets=args.use_header_offsets,
                only_text=False,
                nextdata_offset=offset,
                null_channel_list=args.null_channel,
            )

        datasets.append(
            dataset_record(
                dataset_index,
                offset,
                flow,
                include_text=args.include_text,
                include_analysis=args.include_analysis,
                stats=args.stats,
                raw=args.raw,
                estimated_array_bytes=estimated_array_bytes,
            )
        )

    report: dict[str, Any] = {
        "schema_version": "1.0",
        "flowio_version": flowio.__version__,
        "file_name": path.name,
        "size_bytes": size_bytes,
        "parse_options": {
            "metadata_only": not args.stats,
            "ignore_offset_error": args.ignore_offset_error,
            "ignore_offset_discrepancy": args.ignore_offset_discrepancy,
            "use_header_offsets": args.use_header_offsets,
            "max_bytes": args.max_bytes,
            "max_array_bytes": args.max_array_bytes,
            "max_datasets": args.max_datasets,
            "null_channels": args.null_channel,
        },
        "dataset_count": len(datasets),
        "datasets": datasets,
    }
    if args.sha256:
        report["sha256"] = sha256_file(path)
    return report


def write_report(report: dict[str, Any], output: Optional[Path]) -> None:
    text = json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    )
    if output is None:
        sys.stdout.write(text + "\n")
        return

    output = output.expanduser()
    with output.open("x", encoding="utf-8") as handle:
        handle.write(text + "\n")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.raw and not args.stats:
        parser.error("--raw requires --stats")

    if args.output is not None:
        try:
            if args.output.expanduser().resolve() == args.input.expanduser().resolve():
                parser.error("--output must not overwrite the input FCS file")
        except OSError:
            pass

    try:
        report = inspect_file(args)
        write_report(report, args.output)
    except (
        FlowIOException,
        FileExistsError,
        IndexError,
        KeyError,
        MemoryError,
        NotImplementedError,
        OSError,
        OverflowError,
        TypeError,
        ValueError,
    ) as error:
        print(f"inspect_fcs: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
