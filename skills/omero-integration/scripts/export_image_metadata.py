#!/usr/bin/env python3
"""Export bounded annotations and ROI geometry for explicit image IDs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

from omero_common import (
    ConfigError,
    DependencyError,
    OutputPathError,
    bounded_int,
    config_summary,
    emit_json,
    gateway_session,
    json_safe,
    load_connection_config,
    scrubbed_error,
    take_bounded,
    unwrap_omero,
)


SHAPE_GEOMETRY = {
    "EllipseI": ("X", "Y", "RadiusX", "RadiusY"),
    "LabelI": ("X", "Y"),
    "LineI": ("X1", "Y1", "X2", "Y2"),
    "MaskI": ("X", "Y", "Width", "Height"),
    "PointI": ("X", "Y"),
    "PolygonI": ("Points",),
    "PolylineI": ("Points",),
    "RectangleI": ("X", "Y", "Width", "Height"),
}


def positive_argument(value: str) -> int:
    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or execute a read-only JSON export of annotations and ROI "
            "geometry for explicit image IDs. No pixels or attachment bytes "
            "are retrieved."
        )
    )
    parser.add_argument(
        "--image-id",
        action="append",
        required=True,
        type=positive_argument,
        help="Explicit image ID; repeat for additional images.",
    )
    parser.add_argument(
        "--group-id",
        type=positive_argument,
        help="Optional explicit group ID; cross-group -1 is not supported.",
    )
    parser.add_argument(
        "--max-images",
        type=positive_argument,
        default=25,
        help="Maximum explicit images, 1..100 (default: 25).",
    )
    parser.add_argument(
        "--max-annotations-per-image",
        type=positive_argument,
        default=100,
        help="Per-image annotation cap, 1..1000 (default: 100).",
    )
    parser.add_argument(
        "--max-rois-per-image",
        type=positive_argument,
        default=100,
        help="Per-image ROI serialization cap, 1..1000 (default: 100).",
    )
    parser.add_argument(
        "--max-shapes-per-roi",
        type=positive_argument,
        default=500,
        help="Per-ROI shape cap, 1..5000 (default: 500).",
    )
    parser.add_argument(
        "--max-string-length",
        type=positive_argument,
        default=512,
        help="Maximum exported string length, 32..4096.",
    )
    parser.add_argument(
        "--max-value-items",
        type=positive_argument,
        default=100,
        help="Maximum items in an included annotation value, 1..1000.",
    )
    parser.add_argument(
        "--include-annotation-values",
        action="store_true",
        help="Include bounded annotation values; redacted by default.",
    )
    parser.add_argument(
        "--include-owner-names",
        action="store_true",
        help="Include annotation owner usernames; IDs only by default.",
    )
    parser.add_argument(
        "--include-file-names",
        action="store_true",
        help="Include FileAnnotation filenames; redacted by default.",
    )
    parser.add_argument(
        "--include-roi-labels",
        action="store_true",
        help="Include shape text labels; redacted by default.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Required .json destination in an existing directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing regular output file, never a symlink.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Connect and perform the read-only export.",
    )
    parser.add_argument(
        "--allow-insecure-transport",
        action="store_true",
        help=(
            "Permit OMERO_SECURE=false after explicit policy review. "
            "Encrypted transport remains the default."
        ),
    )
    return parser


def call_or_none(obj: Any, method: str) -> Any:
    function = getattr(obj, method, None)
    if not callable(function):
        return None
    return function()


def normalized(
    value: Any,
    *,
    max_string_length: int,
    max_value_items: int,
) -> Any:
    return json_safe(
        unwrap_omero(value),
        max_string_length=max_string_length,
        max_collection_length=max_value_items,
    )


def owner_record(
    obj: Any,
    *,
    include_owner_names: bool,
    max_string_length: int,
) -> dict[str, Any]:
    details = call_or_none(obj, "getDetails")
    owner = call_or_none(details, "getOwner") if details is not None else None
    record = {
        "owner_id": normalized(
            call_or_none(owner, "getId"),
            max_string_length=max_string_length,
            max_value_items=1,
        )
    }
    if include_owner_names:
        record["owner_username"] = normalized(
            call_or_none(owner, "getOmeName"),
            max_string_length=max_string_length,
            max_value_items=1,
        )
    else:
        record["owner_name_redacted"] = True
    return record


def annotation_record(
    annotation: Any,
    *,
    include_values: bool,
    include_owner_names: bool,
    include_file_names: bool,
    max_string_length: int,
    max_value_items: int,
) -> dict[str, Any]:
    kind = getattr(
        annotation,
        "OMERO_CLASS",
        type(annotation).__name__.removesuffix("Wrapper"),
    )
    record: dict[str, Any] = {
        "id": call_or_none(annotation, "getId"),
        "type": kind,
        "namespace": normalized(
            call_or_none(annotation, "getNs"),
            max_string_length=max_string_length,
            max_value_items=1,
        ),
        **owner_record(
            annotation,
            include_owner_names=include_owner_names,
            max_string_length=max_string_length,
        ),
    }

    if include_values:
        record["value"] = normalized(
            call_or_none(annotation, "getValue"),
            max_string_length=max_string_length,
            max_value_items=max_value_items,
        )
    else:
        record["value_redacted"] = True

    if kind == "FileAnnotation" or type(annotation).__name__ == (
        "FileAnnotationWrapper"
    ):
        original = call_or_none(annotation, "getFile")
        file_record = {
            "original_file_id": call_or_none(original, "getId"),
            "size_bytes": call_or_none(original, "getSize"),
            "mimetype": normalized(
                call_or_none(original, "getMimetype"),
                max_string_length=128,
                max_value_items=1,
            ),
            "bytes_downloaded": False,
        }
        if include_file_names:
            file_record["name"] = normalized(
                call_or_none(original, "getName"),
                max_string_length=max_string_length,
                max_value_items=1,
            )
        else:
            file_record["name_redacted"] = True
        record["file"] = file_record
    return record


def shape_record(
    shape: Any,
    *,
    include_labels: bool,
    max_string_length: int,
) -> dict[str, Any]:
    model_name = type(shape).__name__
    shape_type = model_name.removesuffix("I")
    record: dict[str, Any] = {
        "id": normalized(
            call_or_none(shape, "getId"),
            max_string_length=max_string_length,
            max_value_items=1,
        ),
        "type": shape_type,
        "the_z": normalized(
            call_or_none(shape, "getTheZ"),
            max_string_length=max_string_length,
            max_value_items=1,
        ),
        "the_t": normalized(
            call_or_none(shape, "getTheT"),
            max_string_length=max_string_length,
            max_value_items=1,
        ),
        "the_c": normalized(
            call_or_none(shape, "getTheC"),
            max_string_length=max_string_length,
            max_value_items=1,
        ),
    }
    if include_labels:
        record["label"] = normalized(
            call_or_none(shape, "getTextValue"),
            max_string_length=max_string_length,
            max_value_items=1,
        )
    else:
        record["label_redacted"] = True

    geometry: dict[str, Any] = {}
    for field in SHAPE_GEOMETRY.get(model_name, ()):
        geometry[field[0].lower() + field[1:]] = normalized(
            call_or_none(shape, f"get{field}"),
            max_string_length=max_string_length,
            max_value_items=1,
        )
    record["geometry"] = geometry
    if model_name == "MaskI":
        record["mask_bytes_omitted"] = True
    return record


def roi_record(
    roi: Any,
    *,
    max_shapes: int,
    include_labels: bool,
    max_string_length: int,
) -> dict[str, Any]:
    shapes = take_bounded(roi.copyShapes(), max_shapes)
    return {
        "id": normalized(
            call_or_none(roi, "getId"),
            max_string_length=max_string_length,
            max_value_items=1,
        ),
        "shapes": [
            shape_record(
                shape,
                include_labels=include_labels,
                max_string_length=max_string_length,
            )
            for shape in shapes.items
        ],
        "returned_shapes": len(shapes.items),
        "shapes_truncated": shapes.truncated,
    }


def export_one_image(
    connection: Any,
    roi_service: Any,
    image_id: int,
    args: argparse.Namespace,
) -> dict[str, Any]:
    image = connection.getObject("Image", image_id)
    if image is None:
        return {"id": image_id, "accessible": False}

    annotation_result = take_bounded(
        image.listAnnotations(),
        args.max_annotations_per_image,
    )
    roi_result = roi_service.findByImage(image_id, None)
    roi_items = take_bounded(
        roi_result.rois,
        args.max_rois_per_image,
    )

    details = call_or_none(image, "getDetails")
    group = call_or_none(details, "getGroup") if details is not None else None
    owner = call_or_none(details, "getOwner") if details is not None else None
    return {
        "id": image_id,
        "accessible": True,
        "name_redacted": True,
        "group_id": call_or_none(group, "getId"),
        "owner_id": call_or_none(owner, "getId"),
        "dimensions": {
            "x": call_or_none(image, "getSizeX"),
            "y": call_or_none(image, "getSizeY"),
            "z": call_or_none(image, "getSizeZ"),
            "c": call_or_none(image, "getSizeC"),
            "t": call_or_none(image, "getSizeT"),
        },
        "annotations": [
            annotation_record(
                annotation,
                include_values=args.include_annotation_values,
                include_owner_names=args.include_owner_names,
                include_file_names=args.include_file_names,
                max_string_length=args.max_string_length,
                max_value_items=args.max_value_items,
            )
            for annotation in annotation_result.items
        ],
        "returned_annotations": len(annotation_result.items),
        "annotations_truncated": annotation_result.truncated,
        "rois": [
            roi_record(
                roi,
                max_shapes=args.max_shapes_per_roi,
                include_labels=args.include_roi_labels,
                max_string_length=args.max_string_length,
            )
            for roi in roi_items.items
        ],
        "returned_rois": len(roi_items.items),
        "rois_truncated": roi_items.truncated,
    }


def scope_payload(
    args: argparse.Namespace,
    image_ids: list[int],
) -> dict[str, Any]:
    return {
        "image_ids": image_ids,
        "group_id": args.group_id,
        "cross_group": False,
        "max_images": args.max_images,
        "max_annotations_per_image": args.max_annotations_per_image,
        "max_rois_per_image": args.max_rois_per_image,
        "max_shapes_per_roi": args.max_shapes_per_roi,
        "max_string_length": args.max_string_length,
        "max_value_items": args.max_value_items,
    }


def redaction_payload(args: argparse.Namespace) -> dict[str, bool]:
    return {
        "annotation_values_included": args.include_annotation_values,
        "owner_names_included": args.include_owner_names,
        "file_names_included": args.include_file_names,
        "roi_labels_included": args.include_roi_labels,
        "file_bytes_included": False,
        "pixel_data_included": False,
        "mask_bytes_included": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        bounded_int(
            args.max_images,
            name="max-images",
            minimum=1,
            maximum=100,
        )
        bounded_int(
            args.max_annotations_per_image,
            name="max-annotations-per-image",
            minimum=1,
            maximum=1000,
        )
        bounded_int(
            args.max_rois_per_image,
            name="max-rois-per-image",
            minimum=1,
            maximum=1000,
        )
        bounded_int(
            args.max_shapes_per_roi,
            name="max-shapes-per-roi",
            minimum=1,
            maximum=5000,
        )
        bounded_int(
            args.max_string_length,
            name="max-string-length",
            minimum=32,
            maximum=4096,
        )
        bounded_int(
            args.max_value_items,
            name="max-value-items",
            minimum=1,
            maximum=1000,
        )

        image_ids = list(dict.fromkeys(args.image_id))
        if len(image_ids) != len(args.image_id):
            raise ValueError("duplicate --image-id values are not allowed")
        if len(image_ids) > args.max_images:
            raise ValueError("explicit image count exceeds --max-images")

        config = load_connection_config(require_auth=args.execute)
        if not args.execute:
            print(
                json.dumps(
                    {
                        "mode": "dry-run",
                        "server_contacted": False,
                        "output_not_written": True,
                        "requested_output": args.output,
                        "configuration": config_summary(config),
                        "scope": scope_payload(args, image_ids),
                        "redaction": redaction_payload(args),
                        "next_step": (
                            "Review scope/redaction, then add --execute."
                        ),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        with gateway_session(
            config,
            allow_insecure_transport=args.allow_insecure_transport,
        ) as connection:
            if args.group_id is not None:
                connection.SERVICE_OPTS.setOmeroGroup(str(args.group_id))
            roi_service = connection.getRoiService()
            images = [
                export_one_image(
                    connection,
                    roi_service,
                    image_id,
                    args,
                )
                for image_id in image_ids
            ]

        payload = {
            "mode": "executed-read-only",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "configuration": config_summary(config),
            "scope": scope_payload(args, image_ids),
            "redaction": redaction_payload(args),
            "api_notes": [
                (
                    "IRoi.findByImage is used by current official Python "
                    "examples but IRoi is deprecated."
                ),
                (
                    "ROI limits bound serialization; findByImage itself "
                    "does not expose pagination."
                ),
            ],
            "images": images,
        }
        emit_json(
            payload,
            output=args.output,
            overwrite=args.overwrite,
        )
        return 0
    except (
        ConfigError,
        DependencyError,
        OutputPathError,
        FileExistsError,
        ValueError,
        RuntimeError,
    ) as error:
        print(scrubbed_error(error), file=sys.stderr)
        return 2
    except Exception as error:
        print(scrubbed_error(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
