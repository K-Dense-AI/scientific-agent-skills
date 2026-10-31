#!/usr/bin/env python3
"""Safe Matplotlib export helpers with explicit, auditable settings.

This module does not certify journal compliance. Publisher profiles are dated
planning snapshots and must be confirmed against the target journal.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

from _common import CliError, checked_output_file, emit_json, positive_float

SCHEMA_VERSION = "1.0"
SUPPORTED_FORMATS = {
    "pdf",
    "svg",
    "eps",
    "ps",
    "png",
    "tiff",
    "jpeg",
    "webp",
}
FORMAT_ALIASES = {"jpg": "jpeg", "tif": "tiff"}
VECTOR_FORMATS = {"pdf", "svg", "eps", "ps"}
RASTER_FORMATS = {"png", "tiff", "jpeg", "webp"}
METADATA_FORMATS = {"pdf", "svg", "png", "eps", "ps"}
MAX_FORMATS = 8


def _normalize_formats(formats: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for item in formats:
        for value in item.split(","):
            raw_name = value.strip().lower().lstrip(".")
            name = FORMAT_ALIASES.get(raw_name, raw_name)
            if not name:
                continue
            if name not in SUPPORTED_FORMATS:
                raise CliError(
                    f"unsupported format {name!r}; "
                    f"available: {', '.join(sorted(SUPPORTED_FORMATS))}"
                )
            if name not in normalized:
                normalized.append(name)
    if not normalized:
        raise CliError("at least one output format is required")
    if len(normalized) > MAX_FORMATS:
        raise CliError(f"at most {MAX_FORMATS} output formats are allowed")
    return normalized


def _base_output_path(value: str | os.PathLike[str]) -> Path:
    path = Path(value).expanduser()
    if path.suffix.lower().lstrip(".") in SUPPORTED_FORMATS | set(FORMAT_ALIASES):
        path = path.with_suffix("")
    if not path.name:
        raise CliError("output must include a base filename")
    return path


def _font_rc(font_mode: str) -> dict[str, Any]:
    if font_mode == "current":
        return {}
    if font_mode == "truetype":
        return {
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            # Editable SVG text; unlike PDF Type 42, this is not embedded.
            "svg.fonttype": "none",
        }
    if font_mode == "paths":
        return {
            "pdf.fonttype": 3,
            "ps.fonttype": 3,
            "svg.fonttype": "path",
        }
    raise CliError("font_mode must be 'truetype', 'paths', or 'current'")


def _package_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _atomic_savefig(
    fig: Any,
    destination: Path,
    *,
    format_name: str,
    save_kwargs: dict[str, Any],
    overwrite: bool,
    tiff_rgb: bool = False,
) -> None:
    destination = checked_output_file(destination, force=overwrite)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.stem}.",
        suffix=f".{format_name}",
        dir=destination.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        fig.savefig(temporary, format=format_name, **save_kwargs)
        if tiff_rgb and format_name == "tiff":
            from PIL import Image

            with Image.open(temporary) as rendered:
                if "A" in rendered.getbands() and rendered.getchannel("A").getextrema() != (255, 255):
                    raise CliError("RGB TIFF requires an opaque rendered background")
                rgb = rendered.convert("RGB")
                pillow_options = dict(save_kwargs.get("pil_kwargs", {}))
                pillow_options.setdefault("dpi", rendered.info.get("dpi", (save_kwargs["dpi"],) * 2))
                if rendered.info.get("icc_profile"):
                    pillow_options.setdefault("icc_profile", rendered.info["icc_profile"])
            try:
                rgb.save(temporary, format="TIFF", **pillow_options)
            finally:
                rgb.close()
        if not temporary.exists() or temporary.stat().st_size == 0:
            raise CliError(f"Matplotlib produced no data for {destination}")
        if overwrite:
            os.replace(temporary, destination)
        else:
            try:
                os.link(temporary, destination)
            except FileExistsError as exc:
                raise CliError(f"refusing to overwrite existing output: {destination}") from exc
    except CliError:
        raise
    except Exception as exc:
        raise CliError(
            f"failed to export {destination.name} as {format_name}: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _validate_provenance(provenance: dict[str, Any] | None) -> dict[str, Any]:
    if provenance is None:
        return {}
    if not isinstance(provenance, dict):
        raise CliError("provenance must be a dictionary")
    try:
        encoded = json.dumps(provenance, sort_keys=True).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CliError(f"provenance must be JSON serializable: {exc}") from exc
    if len(encoded) > 1_000_000:
        raise CliError("provenance metadata is limited to 1,000,000 bytes")
    return provenance


def export_figure(
    fig: Any,
    filename: str | os.PathLike[str],
    *,
    formats: Iterable[str] = ("pdf", "png"),
    dpi: float = 300,
    transparent: bool = False,
    tiff_rgb: bool = False,
    bbox_inches: str | None = None,
    pad_inches: float = 0.1,
    facecolor: str = "white",
    edgecolor: str = "none",
    font_mode: str = "truetype",
    overwrite: bool = False,
    mkdir: bool = False,
    metadata: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
    write_manifest: bool = False,
    savefig_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Export a Matplotlib figure atomically with explicit format settings.

    ``dpi`` is passed to vector backends too because it controls rasterized
    artists and embedded raster images. ``bbox_inches=None`` preserves the
    figure's physical page dimensions; use ``"tight"`` only when that change is
    intentional.
    """
    if not (float(dpi) > 0 and math.isfinite(float(dpi))):
        raise CliError("dpi must be finite and greater than zero")
    if not (float(pad_inches) >= 0 and math.isfinite(float(pad_inches))):
        raise CliError("pad_inches must be finite and non-negative")
    normalized_formats = _normalize_formats(formats)
    if tiff_rgb and ("tiff" not in normalized_formats or transparent):
        raise CliError("tiff_rgb requires TIFF output and transparent=False")
    base = _base_output_path(filename)
    parent = base.parent
    if mkdir:
        parent.mkdir(parents=True, exist_ok=True)
    if not parent.exists() or not parent.is_dir():
        raise CliError(f"output parent directory does not exist: {parent}")
    if parent.is_symlink():
        raise CliError(f"output parent must not be a symlink: {parent}")
    for format_name in normalized_formats:
        checked_output_file(
            parent / f"{base.name}.{format_name}",
            force=overwrite,
        )
    if write_manifest:
        checked_output_file(
            parent / f"{base.name}.export.json",
            force=overwrite,
        )

    try:
        import matplotlib as mpl
    except ImportError as exc:
        raise CliError(
            "Matplotlib is required for figure export; "
            "run with --with 'matplotlib==3.11.2'"
        ) from exc

    provenance_document = _validate_provenance(provenance)
    user_metadata = dict(metadata or {})
    creator = user_metadata.setdefault(
        "Creator",
        f"scientific-visualization figure_export.py; Matplotlib {mpl.__version__}",
    )
    if not isinstance(creator, str):
        raise CliError("metadata Creator must be a string")
    extra_kwargs = dict(savefig_kwargs or {})
    if "format" in extra_kwargs:
        raise CliError("savefig_kwargs must not override format")
    protected = {
        "dpi",
        "transparent",
        "bbox_inches",
        "pad_inches",
        "facecolor",
        "edgecolor",
        "metadata",
    }
    overlap = protected.intersection(extra_kwargs)
    if overlap:
        raise CliError(
            "savefig_kwargs must not override explicit settings: "
            + ", ".join(sorted(overlap))
        )

    figure_size = [float(value) for value in fig.get_size_inches()]
    outputs: list[dict[str, Any]] = []
    warnings_list: list[str] = []
    export_rc = _font_rc(font_mode)
    if bbox_inches is None:
        # Prevent a user's global savefig.bbox="tight" from changing page size.
        export_rc["savefig.bbox"] = None
    with mpl.rc_context(export_rc):
        for format_name in normalized_formats:
            destination = parent / f"{base.name}.{format_name}"
            checked_output_file(destination, force=overwrite)
            if format_name in {"eps", "ps"}:
                format_metadata = {"Creator": user_metadata["Creator"]}
            elif format_name in METADATA_FORMATS:
                format_metadata = user_metadata
            else:
                format_metadata = None
            if user_metadata and format_name not in METADATA_FORMATS:
                warnings_list.append(
                    f"{format_name}: Matplotlib does not support savefig metadata "
                    "for this format; metadata remains in the optional manifest."
                )
            save_kwargs: dict[str, Any] = {
                "dpi": float(dpi),
                "transparent": transparent,
                "bbox_inches": bbox_inches,
                "pad_inches": float(pad_inches),
                "facecolor": "none" if transparent else facecolor,
                "edgecolor": "none" if transparent else edgecolor,
                **extra_kwargs,
            }
            if format_metadata is not None:
                save_kwargs["metadata"] = format_metadata
            if format_name == "tiff":
                save_kwargs["pil_kwargs"] = {
                    **save_kwargs.get("pil_kwargs", {}),
                    "compression": "tiff_lzw",
                }

            _atomic_savefig(
                fig,
                destination,
                format_name=format_name,
                save_kwargs=save_kwargs,
                overwrite=overwrite,
                tiff_rgb=tiff_rgb,
            )
            outputs.append(
                {
                    "path": str(destination.resolve()),
                    "format": format_name,
                    "kind": (
                        "vector-container"
                        if format_name in VECTOR_FORMATS
                        else "raster"
                    ),
                    "size_bytes": destination.stat().st_size,
                }
            )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "outputs": outputs,
        "settings": {
            "formats": normalized_formats,
            "dpi": float(dpi),
            "transparent": transparent,
            "tiff_rgb": tiff_rgb,
            "bbox_inches": bbox_inches,
            "pad_inches": float(pad_inches),
            "facecolor": facecolor,
            "font_mode": font_mode,
            "figure_size_inches": figure_size,
        },
        "versions": {
            "matplotlib": mpl.__version__,
            "pillow": _package_version("Pillow"),
        },
        "provenance": provenance_document,
        "warnings": sorted(set(warnings_list)),
        "notice": (
            "Export completed with explicit settings. This report does not "
            "establish visual, accessibility, scientific-integrity, or "
            "journal-submission compliance."
        ),
    }

    if write_manifest:
        manifest_path = parent / f"{base.name}.export.json"
        emit_json(report, output=manifest_path, force=overwrite)
        report["manifest"] = str(manifest_path.resolve())
    return report


def save_publication_figure(
    fig: Any,
    filename: str | os.PathLike[str],
    formats: Iterable[str] = ("pdf", "png"),
    dpi: float = 300,
    transparent: bool = False,
    bbox_inches: str | None = None,
    pad_inches: float = 0.1,
    facecolor: str = "white",
    *,
    overwrite: bool = False,
    provenance: dict[str, Any] | None = None,
    write_manifest: bool = False,
    **kwargs: Any,
) -> list[Path]:
    """Compatibility wrapper returning saved paths.

    Unlike the previous implementation, this function refuses implicit
    overwrite, does not silently swallow export errors, does not cap vector
    DPI, and preserves figure dimensions unless ``bbox_inches="tight"`` is
    requested.
    """
    report = export_figure(
        fig,
        filename,
        formats=formats,
        dpi=dpi,
        transparent=transparent,
        bbox_inches=bbox_inches,
        pad_inches=pad_inches,
        facecolor=facecolor,
        overwrite=overwrite,
        provenance=provenance,
        write_manifest=write_manifest,
        savefig_kwargs=kwargs,
    )
    return [Path(item["path"]) for item in report["outputs"]]


def _load_profiles() -> dict[str, Any]:
    profile_path = Path(__file__).resolve().parents[1] / "assets" / "publisher_profiles.json"
    try:
        document = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"cannot load publisher profiles: {exc}") from exc
    if not isinstance(document.get("profiles"), dict):
        raise CliError("publisher profile asset is malformed")
    return document


def check_figure_size(
    fig: Any,
    journal: str = "nature",
    *,
    tolerance_mm: float = 1.0,
) -> dict[str, Any]:
    """Compare figure dimensions with a dated profile without claiming compliance."""
    if not (tolerance_mm >= 0 and math.isfinite(tolerance_mm)):
        raise CliError("tolerance_mm must be finite and non-negative")
    document = _load_profiles()
    try:
        profile = document["profiles"][journal]
    except KeyError as exc:
        raise CliError(
            f"unknown profile {journal!r}; "
            f"available: {', '.join(sorted(document['profiles']))}"
        ) from exc
    width_inches, height_inches = (float(value) for value in fig.get_size_inches())
    width_mm = width_inches * 25.4
    height_mm = height_inches * 25.4
    candidates = {
        name: float(value)
        for name, value in (profile.get("widths_mm") or {}).items()
    }
    nearest_name = None
    nearest_width = None
    difference = None
    if candidates:
        nearest_name, nearest_width = min(
            candidates.items(), key=lambda item: abs(width_mm - item[1])
        )
        difference = abs(width_mm - nearest_width)
    max_height = profile.get("max_height_mm")
    return {
        "schema_version": SCHEMA_VERSION,
        "profile": journal,
        "profile_label": profile["label"],
        "profile_scope": profile["scope"],
        "profile_accessed": profile.get("accessed", document["accessed"]),
        "source_status": profile.get("source_status", "reviewed"),
        "figure": {
            "width_inches": width_inches,
            "height_inches": height_inches,
            "width_mm": width_mm,
            "height_mm": height_mm,
        },
        "nearest_profile_width": {
            "name": nearest_name,
            "width_mm": nearest_width,
            "difference_mm": difference,
            "matches_tolerance": (
                difference is not None and difference <= tolerance_mm
            ),
        },
        "height_screen": {
            "maximum_mm": max_height,
            "within_snapshot": (
                None if max_height is None else height_mm <= float(max_height)
            ),
        },
        "notice": (
            "A dimensional match to this dated snapshot is not a journal "
            "compliance determination."
        ),
    }


def save_for_journal(
    fig: Any,
    filename: str | os.PathLike[str],
    journal: str,
    figure_type: str = "combination",
    *,
    confirm_profile: bool = False,
    format_name: str | None = None,
    dpi: float | None = None,
    overwrite: bool = False,
) -> list[Path]:
    """Use a dated profile only after explicit caller confirmation.

    This compatibility helper intentionally requires ``confirm_profile=True``.
    Prefer ``export_plan.py`` and ``export_figure`` for an auditable workflow.
    """
    if not confirm_profile:
        raise CliError(
            "publisher rules are date-sensitive; run export_plan.py, verify the "
            "target journal, then pass confirm_profile=True if this snapshot is "
            "appropriate"
        )
    document = _load_profiles()
    try:
        profile = document["profiles"][journal]
    except KeyError as exc:
        raise CliError(f"unknown publisher profile: {journal!r}") from exc
    profile_formats = profile.get("formats") or {}
    allowed = profile_formats.get(figure_type) or []
    selected = (
        _normalize_formats([format_name])[0]
        if format_name is not None
        else next((name for name in allowed if name in SUPPORTED_FORMATS), None)
    )
    if selected is None:
        raise CliError(
            f"profile {journal!r} has no directly exportable {figure_type!r} "
            "format; choose settings manually"
        )
    if selected not in allowed:
        raise CliError(
            f"format {selected!r} is not recorded for {journal} "
            f"{figure_type}; recorded formats: {', '.join(allowed)}"
        )
    if dpi is None:
        raise CliError(
            "provide an explicit dpi after reviewing embedded raster content; "
            "the compatibility helper does not choose one automatically"
        )
    dpi_profile = (profile.get("raster_dpi") or {}).get(figure_type) or {}
    if dpi_profile.get("min") is not None and dpi < float(dpi_profile["min"]):
        raise CliError(f"dpi is below the profile snapshot minimum: {dpi_profile}")
    if (
        dpi_profile.get("min_exclusive") is not None
        and dpi <= float(dpi_profile["min_exclusive"])
    ):
        raise CliError(
            f"dpi does not exceed the profile snapshot threshold: {dpi_profile}"
        )
    if dpi_profile.get("max") is not None and dpi > float(dpi_profile["max"]):
        raise CliError(f"dpi is above the profile snapshot maximum: {dpi_profile}")
    return save_publication_figure(
        fig,
        filename,
        formats=[selected],
        dpi=dpi,
        overwrite=overwrite,
        provenance={
            "publisher_profile": journal,
            "profile_accessed": profile.get("accessed", document["accessed"]),
            "source_status": profile.get("source_status", "reviewed"),
            "profile_scope": profile["scope"],
            "caller_confirmed_snapshot": True,
        },
        write_manifest=True,
    )


def verify_font_embedding(pdf_path: str | os.PathLike[str]) -> dict[str, Any]:
    """Return a conservative PDF font-resource report using the metadata tool."""
    try:
        from image_metadata import inspect_file
    except ImportError as exc:
        raise CliError(f"cannot import image_metadata.py: {exc}") from exc
    report = inspect_file(pdf_path)
    if report["metadata"]["format"] != "PDF":
        raise CliError("font embedding inspection requires a PDF input")
    return {
        "path": report["input"]["path"],
        "font_resources": report["metadata"].get("font_resources"),
        "notice": (
            "Inspection covers declared first-page font resources only; "
            "publisher preflight may apply additional checks."
        ),
    }


def _demo_figure() -> Any:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise CliError(
            "Matplotlib is required for --demo; "
            "run with --with 'matplotlib==3.11.2'"
        ) from exc
    x_values = [index / 20.0 for index in range(121)]
    first = [math.sin(value) for value in x_values]
    second = [math.cos(value) for value in x_values]
    fig, ax = plt.subplots(figsize=(3.5, 2.5), layout="constrained")
    ax.plot(x_values, first, label="sin(x)", marker="o", markevery=20)
    ax.plot(
        x_values,
        second,
        label="cos(x)",
        linestyle="--",
        marker="s",
        markevery=20,
    )
    ax.axhline(0, color="0.35", linewidth=0.7)
    ax.set(xlabel="Angle (radians)", ylabel="Amplitude (unitless)")
    ax.legend()
    return fig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render a deterministic Matplotlib export smoke-test. Programmatic "
            "helpers in this module support explicit, safe figure export."
        )
    )
    parser.add_argument(
        "--demo",
        metavar="BASE_PATH",
        help="render a deterministic demo to this base path",
    )
    parser.add_argument(
        "--formats",
        default="pdf,png",
        help="comma-separated formats (default: pdf,png)",
    )
    parser.add_argument("--dpi", type=positive_float, default=300.0)
    parser.add_argument(
        "--font-mode",
        choices=("truetype", "paths", "current"),
        default="truetype",
    )
    parser.add_argument("--transparent", action="store_true")
    parser.add_argument(
        "--tight",
        action="store_true",
        help="use bbox_inches='tight' (changes physical page dimensions)",
    )
    parser.add_argument("--manifest", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--style",
        choices=("default", "nature", "science", "cell", "minimal", "presentation"),
        default="default",
    )
    parser.add_argument("--palette", default="okabe_ito_on_white")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if not args.demo:
            parser.error("--demo BASE_PATH is required")
        try:
            from style_presets import style_context
        except ImportError as exc:
            raise CliError(f"cannot import style_presets.py: {exc}") from exc
        with style_context(args.style, palette_name=args.palette):
            fig = _demo_figure()
            try:
                report = export_figure(
                    fig,
                    args.demo,
                    formats=args.formats.split(","),
                    dpi=args.dpi,
                    transparent=args.transparent,
                    bbox_inches="tight" if args.tight else None,
                    font_mode=args.font_mode,
                    overwrite=args.force,
                    provenance={
                        "purpose": "deterministic export smoke test",
                        "raw_data": "analytical sin/cos values generated in code",
                        "transformations": ["none"],
                    },
                    write_manifest=args.manifest,
                )
            finally:
                import matplotlib.pyplot as plt

                plt.close(fig)
        emit_json(report)
        return 0
    except CliError as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
