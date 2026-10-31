#!/usr/bin/env python3
"""Inspect a submission PDF using a verified limit or an explicit source.

This tool does not infer where references or appendices begin and cannot prove
margin or font-size compliance. Supply --content-pages after counting pages
according to the official venue rule.

Examples:
    python scripts/validate_format.py --file paper.pdf --venue icml-2026 \
        --content-pages 8
    python scripts/validate_format.py --file proposal.pdf --max-pages 15 \
        --content-pages 15 --source-url https://www.nsf.gov/policies/pappg
"""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PRESETS = {
    "neurips-2026": {
        "max_content_pages": 9,
        "excluded": "references, checklist, and optional technical appendices; omit acknowledgments for review",
        "source": "https://neurips.cc/Conferences/2026/MainTrackHandbook",
        "checked": "2026-10-01",
    },
    "icml-2026": {
        "max_content_pages": 8,
        "excluded": "references and appendices",
        "source": "https://icml.cc/Conferences/2026/AuthorInstructions",
        "checked": "2026-10-01",
    },
    "iclr-2026": {
        "max_content_pages": 9,
        "excluded": "references and appendices",
        "source": "https://iclr.cc/Conferences/2026/AuthorGuide",
        "checked": "2026-10-01",
    },
    "cvpr-2026": {
        "max_content_pages": 8,
        "excluded": "cited references only",
        "source": "https://cvpr.thecvf.com/Conferences/2026/AuthorGuidelines",
        "checked": "2026-10-01",
    },
    "nsf-standard": {
        "max_content_pages": 15,
        "excluded": "all separately uploaded proposal components",
        "source": "https://www.nsf.gov/policies/pappg",
        "checked": "2026-10-01",
    },
    "nih-r01": {
        "max_content_pages": 12,
        "excluded": "all attachments outside the Research Strategy",
        "source": (
            "https://grants.nih.gov/grants-process/write-application/"
            "how-to-apply-application-guide/page-limits"
        ),
        "checked": "2026-10-01",
    },
}


def run_poppler(command: str, pdf_path: Path) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            [command, str(pdf_path.resolve())],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"{command} timed out after 30 seconds") from error
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or str(error)
        raise RuntimeError(f"{command} failed: {message}") from error


def pdf_info(pdf_path: Path) -> dict[str, str] | None:
    result = run_poppler("pdfinfo", pdf_path)
    if result is None:
        return None

    info = {}
    for line in result.stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    return info


def embedded_fonts(pdf_path: Path) -> list[dict[str, str | bool]] | None:
    """Read all font rows, including fonts whose Poppler `emb` column is no."""
    result = run_poppler("pdffonts", pdf_path)
    if result is None:
        return None

    fonts = []
    for line in result.stdout.splitlines()[2:]:
        fields = line.split()
        if not fields:
            continue
        # Type can contain spaces ("CID TrueType", "Type 1"). The last
        # five columns are always emb, sub, uni, object number, generation.
        if len(fields) < 7 or fields[-5] not in {"yes", "no"}:
            raise RuntimeError("Unrecognized pdffonts row; inspect font output manually")
        fonts.append({"name": fields[0], "embedded": fields[-5] == "yes"})
    return fonts


def page_count_result(
    total_pages: int | None,
    content_pages: int | None,
    max_content_pages: int | None,
    excluded: str | None,
) -> dict[str, str]:
    if total_pages is None:
        return {
            "status": "skip",
            "message": "pdfinfo is unavailable; install Poppler to inspect the PDF.",
        }
    if max_content_pages is None:
        return {
            "status": "info",
            "message": (
                f"Total PDF pages: {total_pages}. No limit was supplied; verify the "
                "official instructions manually."
            ),
        }
    if content_pages is None:
        exclusion_note = f" Excluded scope: {excluded}." if excluded else ""
        return {
            "status": "manual",
            "message": (
                f"Total PDF pages: {total_pages}; maximum content pages: "
                f"{max_content_pages}.{exclusion_note} Re-run with --content-pages "
                "after counting according to the official rule."
            ),
        }
    if content_pages > total_pages:
        return {
            "status": "fail",
            "message": (
                f"Reported content pages ({content_pages}) exceed total PDF pages "
                f"({total_pages})."
            ),
        }
    if content_pages > max_content_pages:
        return {
            "status": "fail",
            "message": (
                f"Content-page limit exceeded: {content_pages}/{max_content_pages}."
            ),
        }
    return {
        "status": "pass",
        "message": (
            f"Content-page count is within the supplied limit: "
            f"{content_pages}/{max_content_pages}. Total PDF pages: {total_pages}."
        ),
    }


def font_result(fonts: list[dict[str, str | bool]] | None) -> dict[str, str]:
    if fonts is None:
        return {
            "status": "skip",
            "message": "pdffonts is unavailable; install Poppler to list embedded fonts.",
        }
    if not fonts:
        return {
            "status": "manual",
            "message": "No font rows were reported; text may be outlined or rasterized. Inspect manually.",
        }
    missing = sorted({str(font["name"]) for font in fonts if not font["embedded"]})
    if missing:
        return {
            "status": "fail",
            "message": "Fonts not embedded: " + ", ".join(missing) + ". Re-export with fonts embedded.",
        }
    return {
        "status": "info",
        "message": (
            "Embedded font names: "
            + ", ".join(sorted({str(font["name"]) for font in fonts}))
            + ". This does not verify font family or point size compliance."
        ),
    }


def metadata_result(info: dict[str, str] | None) -> dict[str, str]:
    if info is None:
        return {
            "status": "skip",
            "message": "pdfinfo is unavailable; metadata was not inspected.",
        }
    fields = ["Title", "Author", "Creator", "Producer"]
    values = [f"{field}={info[field]!r}" for field in fields if info.get(field)]
    if not values:
        return {"status": "info", "message": "No common identity metadata fields were set."}
    return {
        "status": "manual",
        "message": (
            "PDF metadata: "
            + "; ".join(values)
            + ". Check these fields for blind-review identity leaks."
        ),
    }


def write_report(
    report_path: Path,
    pdf_path: Path,
    source_url: str | None,
    checked: str | None,
    results: dict[str, dict[str, str]],
) -> None:
    lines = [
        "Submission PDF Inspection",
        "=" * 60,
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"File: {pdf_path}",
        f"Official source: {source_url or 'not supplied'}",
        f"Preset checked: {checked or 'not applicable'}",
        "",
    ]
    for name, result in results.items():
        lines.extend(
            [
                name.upper(),
                f"Status: {result['status']}",
                result["message"],
                "",
            ]
        )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect page count, fonts, and metadata without claiming full compliance"
    )
    parser.add_argument("--file", required=True, help="PDF file to inspect")
    limits = parser.add_mutually_exclusive_group()
    limits.add_argument("--venue", choices=sorted(PRESETS), help="Dated initial-submission preset")
    limits.add_argument("--max-pages", type=int, help="Explicit maximum content pages")
    parser.add_argument(
        "--content-pages",
        type=int,
        help="Content pages counted manually according to the official rule",
    )
    parser.add_argument("--source-url", help="Official source for an explicit limit")
    parser.add_argument(
        "--check",
        default="page-count,fonts,metadata",
        help="Comma-separated: page-count, fonts, metadata, all",
    )
    parser.add_argument("--report", help="Write a text report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pdf_path = Path(args.file)
    if not pdf_path.is_file():
        print(f"Error: file not found: {pdf_path}")
        return 2
    if pdf_path.suffix.lower() != ".pdf":
        print(f"Error: expected a PDF file: {pdf_path}")
        return 2
    if args.max_pages is not None and args.max_pages < 1:
        print("Error: --max-pages must be positive.")
        return 2
    if args.content_pages is not None and args.content_pages < 0:
        print("Error: --content-pages cannot be negative.")
        return 2

    preset = PRESETS.get(args.venue, {})
    max_content_pages = args.max_pages or preset.get("max_content_pages")
    source_url = args.source_url or preset.get("source")
    excluded = preset.get("excluded")
    checked = preset.get("checked")

    if args.max_pages is not None and not source_url:
        print("Warning: supply --source-url so the explicit limit is auditable.")

    checks = {item.strip() for item in args.check.split(",") if item.strip()}
    if not checks:
        print("Error: --check must select at least one inspection.")
        return 2
    allowed = {"page-count", "fonts", "metadata", "all"}
    unknown = checks - allowed
    if unknown:
        print(f"Error: unknown checks: {', '.join(sorted(unknown))}")
        return 2
    if "all" in checks:
        checks = {"page-count", "fonts", "metadata"}

    try:
        info = pdf_info(pdf_path)
        total_pages = int(info["Pages"]) if info and info.get("Pages") else None
        results = {}
        if "page-count" in checks:
            results["page-count"] = page_count_result(
                total_pages,
                args.content_pages,
                max_content_pages,
                excluded,
            )
        if "fonts" in checks:
            results["fonts"] = font_result(embedded_fonts(pdf_path))
        if "metadata" in checks:
            results["metadata"] = metadata_result(info)
    except (RuntimeError, ValueError) as error:
        print(f"Error: {error}")
        return 2

    print(f"File: {pdf_path}")
    if args.venue:
        print(f"Preset: {args.venue} (checked {checked})")
    print(f"Official source: {source_url or 'not supplied'}")
    for name, result in results.items():
        print(f"\n{name.upper()} [{result['status'].upper()}]")
        print(result["message"])

    if args.report:
        report_path = Path(args.report)
        write_report(report_path, pdf_path, source_url, checked, results)
        print(f"\nReport saved to: {report_path}")

    return 1 if any(result["status"] == "fail" for result in results.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
