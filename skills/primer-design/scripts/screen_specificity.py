#!/usr/bin/env python3
"""Screen primers against an explicit local FASTA with reproducible search bounds."""

from __future__ import annotations

import argparse
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

from _common import check_output_paths, read_fasta, read_pairs, sha256_file, write_json
from _specificity import blast_hits, enumerate_products, exhaustive_hits, expand_panel_pairs, read_expected


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", required=True, type=Path, help="TSV: pair_id, forward, reverse; optional forward_tail, reverse_tail")
    parser.add_argument("--reference", required=True, type=Path, help="FASTA with unique record IDs")
    parser.add_argument("--output", required=True, type=Path, help="JSON report; incomplete runs exit 2")
    parser.add_argument("--expected", type=Path, help="TSV: pair_id, record_id, start, end (0-based half-open)")
    parser.add_argument("--engine", choices=("exhaustive", "blast"), default="exhaustive")
    parser.add_argument("--multiplex", action="store_true", help="Also screen every cross-pair oligo combination; all cross-pair products are potential off-targets")
    parser.add_argument("--max-panel-combinations", type=int, default=10_000, help="Cross-pair oligo combination cap, checked before panel expansion")
    parser.add_argument("--circular", action="append", default=[], metavar="RECORD_ID", help="Repeat for circular records; intervals can end beyond record length")
    parser.add_argument("--min-product", type=int, default=40)
    parser.add_argument("--max-product", type=int, default=2000)
    parser.add_argument("--max-mismatches", type=int, default=2)
    parser.add_argument("--three-prime-bases", type=int, default=5)
    parser.add_argument("--max-three-prime-mismatches", type=int, default=0)
    parser.add_argument("--max-comparisons", type=int, default=100_000_000, help="Base comparison cap; exceeding a cap fails closed")
    parser.add_argument("--max-hits", type=int, default=100_000)
    parser.add_argument("--max-products", type=int, default=100_000, help="Per-pair product cap")
    parser.add_argument("--max-product-combinations", type=int, default=1_000_000, help="Per-pair inward-facing candidate comparison cap")
    parser.add_argument("--max-blast-rows", type=int, default=1_000_000)
    parser.add_argument("--blastn", default="blastn", help="Local BLAST+ blastn executable")
    parser.add_argument("--makeblastdb", default="makeblastdb", help="Local BLAST+ makeblastdb executable")
    parser.add_argument("--blast-max-target-seqs", type=int, default=100_000)
    parser.add_argument("--blast-max-hsps", type=int, default=100_000)
    parser.add_argument("--blast-timeout", type=int, default=300, help="Seconds per BLAST+ invocation")
    return parser


def run(args):
    settings = {key: value for key, value in vars(args).items()
                if key not in {"pairs", "reference", "expected", "output"}}
    report = {
        "schema_version": "1.0", "analysis": "local_primer_specificity", "status": "incomplete",
        "complete_within_model": False, "exhaustive": False,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "coordinate_convention": "0-based half-open forward-reference; circular end may exceed record length",
        "strand_convention": "+ matches reference sequence and extends right; - matches its reverse complement and extends left",
        "settings": settings, "provenance": {"python": platform.python_version()},
        "limitations": [
            "Potential amplification under a bounded ungapped mismatch model; not experimental specificity.",
            "Only supplied reference records, mismatch thresholds, 3-prime window and product-size range are screened.",
            "Unrepresented variants, contaminants, insertions/deletions, and chemistry are not screened.",
            "Reference ambiguity is conservatively compatible when a primer base is possible; mismatches are lower bounds.",
            "Only annealing cores are searched. Tails affect final length but tail-created later-cycle binding is not searched.",
            "F/F, R/R and both F/R orientations are enumerated; overlapping binding sites are excluded.",
        ],
        "issues": [], "pairs": [],
    }
    report["limitations"].append(
        "Multiplex mode treats all cross-pair products as unintended; predeclared intentional cross-pair "
        "designs should be assessed as explicit standalone pairs. Same-oligo products remain in original-pair results."
        if args.multiplex else "Cross-pair multiplex products are not screened; enable --multiplex for a panel."
    )
    try:
        input_paths = [args.pairs, args.reference] + ([args.expected] if args.expected else [])
        check_output_paths(input_paths, [args.output])
        for key in ("min_product", "max_product", "three_prime_bases", "max_comparisons", "max_hits",
                    "max_products", "max_product_combinations", "max_blast_rows", "blast_max_target_seqs",
                    "blast_max_hsps", "blast_timeout", "max_panel_combinations"):
            if settings[key] <= 0:
                raise ValueError(f"{key} must be positive")
        if args.min_product > args.max_product:
            raise ValueError("min_product must not exceed max_product")
        if args.max_mismatches < 0 or args.max_three_prime_mismatches < 0:
            raise ValueError("Mismatch thresholds must be nonnegative")
        if args.max_three_prime_mismatches > args.three_prime_bases:
            raise ValueError("3-prime mismatch threshold exceeds its window")
        pairs, references = read_pairs(args.pairs), read_fasta(args.reference)
        circular = set(args.circular)
        if circular - set(references):
            raise ValueError("Unknown circular record IDs: " + ", ".join(sorted(circular - set(references))))
        primers = sorted({pair[key] for pair in pairs for key in ("forward", "reverse")})
        if not primers or not references:
            raise ValueError("Nonempty primer pairs and reference records are required")
        if any(args.three_prime_bases > len(primer) for primer in primers):
            raise ValueError("3-prime window exceeds a primer's annealing-core length")
        if any(set(primer) - set("ACGT") for primer in primers):
            raise ValueError("Only unambiguous ACGT annealing cores are supported")
        report["provenance"].update({
            "implementation_sha256": {
                name: sha256_file(Path(__file__).parent / name)
                for name in ("screen_specificity.py", "_specificity.py", "_common.py")
            },
            "pairs": {"path": str(args.pairs), "sha256": sha256_file(args.pairs)},
            "reference": {"path": str(args.reference), "sha256": sha256_file(args.reference),
                          "record_count": len(references), "total_bases": sum(map(len, references.values())),
                          "record_lengths": {key: len(value) for key, value in references.items()},
                          "ambiguous_base_count": sum(base not in "ACGT" for sequence in references.values() for base in sequence)},
            "expected": {"path": str(args.expected), "sha256": sha256_file(args.expected)} if args.expected else None,
        })
        expected = read_expected(args.expected, pairs, references, circular)
        original_pair_count = len(pairs)
        if args.multiplex:
            pairs = expand_panel_pairs(pairs, args.max_panel_combinations)
        report["provenance"]["panel"] = {
            "enabled": args.multiplex, "original_pair_count": original_pair_count,
            "source_oligo_count": original_pair_count * 2,
            "cross_pair_count": len(pairs) - original_pair_count,
            "unique_annealing_cores_searched": len(primers),
            "generated_pair_ids": [pair["pair_id"] for pair in pairs if pair.get("cross_pair")],
        }
        search = exhaustive_hits if args.engine == "exhaustive" else blast_hits
        if args.engine == "blast":
            report["limitations"].append(
                "BLAST discovery is heuristic, uses exact 7-base seeds and E-value 1000; full-length ungapped "
                "realignment validates only discovered sites. No-hit output never proves absence of binding sites."
            )
        hits, engine_provenance, issues = search(primers, references, circular, settings)
        report["provenance"].update(engine_provenance)
        report["issues"].extend(issues)
        for pair in pairs:
            result = enumerate_products(pair, hits, references, circular, settings, expected.get(pair["pair_id"], []))
            if result["unresolved_ambiguity"]:
                report["issues"].append(
                    f"Pair {pair['pair_id']}: ambiguous reference bases at potential binding sites; "
                    "binding and 3-prime mismatch counts remain unresolved"
                )
            if issues:
                result.setdefault("status_before_incomplete", result["status"])
                result["status"] = "incomplete"
            report["pairs"].append(result)
        report["complete_within_model"] = args.engine == "exhaustive" and not report["issues"]
        report["exhaustive"] = args.engine == "exhaustive" and not report["issues"]
        report["discovery_completed"] = not issues
        statuses = {pair["status"] for pair in report["pairs"]}
        report["status"] = next(status for status in (
            "incomplete", "intended_target_not_found", "potential_off_target", "no_expected_target",
            "no_off_target_found_within_search_scope",
        ) if status in statuses)
        return report, 2 if report["issues"] else 0
    except (ValueError, OSError, KeyError) as exc:
        report["issues"].append(str(exc))
        report["status"] = "incomplete"
        report["complete_within_model"] = False
        report["exhaustive"] = False
        report["discovery_completed"] = False
        for pair in report["pairs"]:
            pair.setdefault("status_before_incomplete", pair["status"])
            pair["status"] = "incomplete"
        return report, 2


def main(argv=None):
    args = build_parser().parse_args(argv)
    # Never replace an input with an error report, either.
    inputs = [args.pairs, args.reference] + ([args.expected] if args.expected else [])
    try:
        check_output_paths(inputs, [args.output])
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    report, exit_code = run(args)
    try:
        write_json(args.output, report)
    except OSError as exc:
        print(f"Cannot write report: {exc}", file=sys.stderr)
        return 2
    print(f"{report['status']}: {args.output}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
