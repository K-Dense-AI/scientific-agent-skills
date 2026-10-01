#!/usr/bin/env python3
"""Build deep links into the AlphaGenome Atlas website. Standard library only.

The portal at https://deepmind.google.com/science/alphagenome/atlas is the
no-code face of the Atlas: AVI score, per-modality heatmaps across every
biosample, and motif maps. Linking a scored variant to it lets a reader check
the prediction tracks behind a number. Positions are 1-based, intervals are
1-based closed, and rsIDs are not accepted by the site.

Examples:
  python atlas_link.py variant chr9:128225994:G>A
  python atlas_link.py variant chr9:128225994:G>A --biosample K562 --modalities RNA_SEQ,DNASE,CHIP_TF --tf GATA1
  python atlas_link.py locus chr11:5225727-5226575 --modalities RNA_SEQ,DNASE
  python atlas_link.py gene HBB
  python atlas_link.py motifs chr11:5225727-5226575
  python atlas_link.py variant chr9:128225994:G>A --markdown
"""

from __future__ import annotations

import argparse
import sys
import urllib.parse
from collections.abc import Sequence

import _common as common

MODES = ("variant", "locus", "gene", "motifs")

#: Layout sections the portal renders (``lItems=section:<MODALITY>``).
SECTION_MODALITIES: tuple[str, ...] = (
    "RNA_SEQ",
    "DNASE",
    "ATAC",
    "CHIP_TF",
    "CHIP_HISTONE",
    "CAGE",
    "PROCAP",
    "POLYADENYLATION",
    "SPLICE_JUNCTIONS",
    "SPLICE_SITE_USAGE",
    "SPLICE_SITES",
    "CONTACT_MAPS",
)

#: ``f=SCORER_MODALITY:<display name>`` filter values used by the site.
MODALITY_FILTER_NAMES: dict[str, str] = {
    "RNA_SEQ": "RNA-seq",
    "DNASE": "DNase",
    "ATAC": "ATAC-seq",
    "CHIP_TF": "ChIP-TF",
    "CHIP_HISTONE": "ChIP-Histone",
    "CAGE": "CAGE",
    "PROCAP": "PRO-cap",
    "POLYADENYLATION": "Polyadenylation",
    "SPLICE_JUNCTIONS": "Splice junctions",
    "SPLICE_SITE_USAGE": "Splice site usage",
}

DEFAULT_MODALITIES: tuple[str, ...] = ("RNA_SEQ", "DNASE", "CHIP_TF")


def parse_modalities(text: str | Sequence[str] | None) -> list[str]:
    if not text:
        return []
    items = text.split(",") if isinstance(text, str) else list(text)
    result = []
    for item in items:
        name = item.strip().upper()
        if not name:
            continue
        if name not in SECTION_MODALITIES:
            raise ValueError(f"unknown modality {item!r}; choose from {', '.join(SECTION_MODALITIES)}")
        result.append(name)
    return result


def build_filter(
    biosample: str | None = None,
    modalities: Sequence[str] = (),
    tfs: Sequence[str] = (),
    histone_marks: Sequence[str] = (),
) -> str | None:
    """The ``f=`` predicate list.

    Biosample predicates AND together; assay predicates (modality, TF, histone
    mark) OR together. RNA-seq and DNase tracks carry no TF code, so a
    TF-only assay filter hides them; when TFs are given, RNA-seq and DNase
    are added so the expression and accessibility context stays visible.
    """
    parts: list[str] = []
    if biosample:
        parts.append(f"BIOSAMPLE_NAME:{biosample}")
    active = list(modalities)
    if tfs:
        for required in ("RNA_SEQ", "DNASE"):
            if required not in active:
                active.append(required)
    for modality in active:
        display = MODALITY_FILTER_NAMES.get(modality.upper())
        if display:
            parts.append(f"SCORER_MODALITY:{display}")
    for tf in tfs:
        parts.append(f"ASSAY_TRANSCRIPTOR_FACTOR:{tf}")
    for mark in histone_marks:
        parts.append(f"ASSAY_HISTONE_MARK:{mark}")
    return ",".join(parts) if parts else None


def build_layout(include_avi: bool = True, modalities: Sequence[str] = ()) -> str:
    items = ["avi"] if include_avi else []
    items.extend(f"section:{modality.upper()}" for modality in modalities)
    return ",".join(items) if items else "avi"


def build_url(
    mode: str,
    query: str,
    *,
    biosample: str | None = None,
    modalities: Sequence[str] = DEFAULT_MODALITIES,
    tfs: Sequence[str] = (),
    histone_marks: Sequence[str] = (),
    include_avi: bool = True,
    zoom: str | None = None,
) -> str:
    """Assemble a portal URL.

    ``mode`` is ``variant`` (``q`` = ``chr:pos:ref>alt``), ``locus`` (``q`` =
    1-based closed ``chr:start-end``), ``gene`` (``q`` = symbol or Ensembl
    ID, portal mode ``entity``), or ``motifs`` (``q`` = interval, motif view).
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if mode == "variant":
        spec = common.parse_variant_string(query)
        q = str(spec)
        portal_mode = "variant"
    elif mode in {"locus", "motifs"}:
        chromosome, start0, end = common.parse_interval_string(query)
        q = f"{chromosome}:{start0 + 1}-{end}"
        portal_mode = "locus" if mode == "locus" else "motifs"
    else:
        q = query.strip()
        if not q:
            raise ValueError("gene query is empty")
        portal_mode = "entity"

    params: dict[str, str] = {"q": q, "m": portal_mode, "lItems": build_layout(include_avi, modalities)}
    if zoom:
        chromosome, start0, end = common.parse_interval_string(zoom)
        params["i"] = f"{chromosome}:{start0 + 1}-{end}"
    filter_string = build_filter(biosample, modalities, tfs, histone_marks)
    if filter_string:
        params["f"] = filter_string
    return f"{common.ATLAS_BASE_URL}?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote, safe=":,-")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atlas_link.py",
        description="Build AlphaGenome Atlas website deep links (no network, no key).",
        epilog=__doc__.split("Examples:", 1)[-1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("mode", choices=MODES, help="what the query is")
    parser.add_argument("query", help="chr:pos:ref>alt, chr:start-end (1-based closed), or a gene symbol / Ensembl ID")
    parser.add_argument("--biosample", metavar="NAME", help="biosample name filter, e.g. K562 or 'heart left ventricle'")
    parser.add_argument("--modalities", default=",".join(DEFAULT_MODALITIES), metavar="A,B,C", help=f"layout sections (default {','.join(DEFAULT_MODALITIES)})")
    parser.add_argument("--tf", nargs="+", metavar="TF", default=(), help="ChIP-TF transcription factor filters")
    parser.add_argument("--histone-mark", nargs="+", metavar="MARK", default=(), help="ChIP-Histone mark filters, e.g. H3K27ac")
    parser.add_argument("--no-avi", action="store_true", help="omit the AVI track from the layout")
    parser.add_argument("--zoom", metavar="CHR:START-END", help="viewport interval (1-based closed); needed for motif rendering")
    parser.add_argument("--markdown", action="store_true", help="print a Markdown link instead of a bare URL")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        url = build_url(
            args.mode,
            args.query,
            biosample=args.biosample,
            modalities=parse_modalities(args.modalities),
            tfs=tuple(args.tf),
            histone_marks=tuple(args.histone_mark),
            include_avi=not args.no_avi,
            zoom=args.zoom,
        )
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.markdown:
        print(f"[{args.query} on AlphaGenome Atlas]({url})")
    else:
        print(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
