#!/usr/bin/env python3
"""List and query the templates actually bundled with venue-templates.

Examples:
    python scripts/query_template.py --list-all
    python scripts/query_template.py --venue NeurIPS --requirements
    python scripts/query_template.py --type grants
    python scripts/query_template.py --keyword author-year
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


CHECKED_DATE = "2026-10-01"

TEMPLATES = {
    "journals": {
        "nature": {
            "file": "nature_article.tex",
            "full_name": "Nature-oriented article scaffold",
            "status": "Generic writing scaffold; not an official Nature template.",
            "source": "https://www.nature.com/nature/for-authors/initial-submission",
            "requirements": "Initial submissions are format-flexible within reason; check the exact article type.",
        },
        "plos-one": {
            "file": "plos_one.tex",
            "full_name": "PLOS ONE-oriented article scaffold",
            "status": "Drafting scaffold; compare with the current official PLOS LaTeX package.",
            "source": "https://journals.plos.org/plosone/s/submission-guidelines",
            "requirements": "Follow the current PLOS ONE submission and file-upload instructions.",
        },
        "neurips-2026": {
            "file": "neurips_article.tex",
            "full_name": "NeurIPS 2026 paper wrapper",
            "status": "Requires the official neurips_2026.sty and checklist files.",
            "source": "https://neurips.cc/Conferences/2026/MainTrackHandbook",
            "requirements": (
                "Main track initial submission: 9 content pages; references, checklist, "
                "and optional technical appendices do not count. Initial submission is anonymous."
            ),
        },
        "elsevier-numeric": {
            "file": "elsarticle-template-num.tex",
            "full_name": "Elsevier elsarticle numeric example",
            "status": "Bundled example; the journal's Guide for Authors controls.",
            "source": "https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions",
            "requirements": "Numeric citations using the bundled elsarticle-num.bst.",
        },
        "elsevier-numeric-names": {
            "file": "elsarticle-template-num-names.tex",
            "full_name": "Elsevier elsarticle numeric-with-names example",
            "status": "Bundled example; the journal's Guide for Authors controls.",
            "source": "https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions",
            "requirements": "Numeric citations with author names supported by elsarticle-num-names.bst; sorting/compression is a natbib option.",
        },
        "elsevier-author-year": {
            "file": "elsarticle-template-harv.tex",
            "full_name": "Elsevier elsarticle author-year example",
            "status": "Bundled example; the journal's Guide for Authors controls.",
            "source": "https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions",
            "requirements": "Author-year citations using the bundled elsarticle-harv.bst.",
        },
    },
    "posters": {
        "beamerposter": {
            "file": "beamerposter_academic.tex",
            "full_name": "Venue-agnostic beamerposter scaffold",
            "status": "Set dimensions and orientation from the event's current presenter instructions.",
            "source": None,
            "requirements": "A0 portrait by default; customize size before use.",
        }
    },
    "grants": {
        "nsf": {
            "file": "nsf_proposal_template.tex",
            "full_name": "NSF narrative planning scaffold",
            "status": "Not an NSF-issued upload package; split components in the submission portal.",
            "source": "https://www.nsf.gov/policies/pappg",
            "requirements": (
                "Check the current PAPPG and solicitation. Use SciENcv for required "
                "senior/key-person forms."
            ),
        },
        "nih-specific-aims": {
            "file": "nih_specific_aims.tex",
            "full_name": "NIH Specific Aims writing scaffold",
            "status": "Drafting scaffold; the NOFO and current application guide control.",
            "source": (
                "https://grants.nih.gov/grants-process/write-application/"
                "how-to-apply-application-guide/page-limits"
            ),
            "requirements": "Specific Aims is generally limited to one page unless the NOFO says otherwise.",
        },
    },
}


def skill_path() -> Path:
    return Path(__file__).resolve().parent.parent


def template_path(category: str, filename: str) -> Path:
    return skill_path() / "assets" / category / filename


def search_templates(
    venue: str | None = None,
    template_type: str | None = None,
    keyword: str | None = None,
) -> list[dict]:
    results = []
    for category_name, category in TEMPLATES.items():
        if template_type and template_type != "all" and category_name != template_type:
            continue

        for template_id, template in category.items():
            searchable = json.dumps(
                {"id": template_id, "category": category_name, **template}
            ).lower()
            if venue and venue.lower() not in searchable:
                continue
            if keyword and keyword.lower() not in searchable:
                continue

            results.append(
                {
                    "id": template_id,
                    "category": category_name,
                    **template,
                }
            )
    return results


def print_template(template: dict, detailed: bool = True) -> None:
    path = template_path(template["category"], template["file"])
    print(f"\n{template['full_name']}")
    print(f"  ID: {template['id']}")
    print(f"  Category: {template['category']}")
    print(f"  File: {path}")
    print(f"  Exists: {'yes' if path.is_file() else 'NO'}")
    if not detailed:
        return

    print(f"  Status: {template['status']}")
    print(f"  Requirements note: {template['requirements']}")
    if template["source"]:
        print(f"  Official source: {template['source']}")
        print(f"  Source checked: {CHECKED_DATE}; recheck before submission")
    else:
        print("  Official source: event-specific presenter instructions required")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query templates actually bundled with venue-templates"
    )
    parser.add_argument("--venue", help="Venue or agency name")
    parser.add_argument(
        "--type",
        choices=["journals", "posters", "grants", "all"],
        dest="template_type",
        help="Template category",
    )
    parser.add_argument("--keyword", help="Search all template metadata")
    parser.add_argument("--list-all", action="store_true", help="List every template")
    parser.add_argument(
        "--requirements",
        action="store_true",
        help="Show status, requirement note, and official source",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not any([args.list_all, args.venue, args.template_type, args.keyword]):
        print("Specify --list-all, --venue, --type, or --keyword.")
        return 2

    results = search_templates(
        venue=args.venue,
        template_type="all" if args.list_all else args.template_type,
        keyword=args.keyword,
    )
    if not results:
        print("No bundled templates match the query.")
        print("Use the venue's official author instructions when no asset is bundled.")
        return 1

    print(f"Bundled templates: {len(results)}")
    for result in results:
        print_template(result, detailed=args.requirements or not args.list_all)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
