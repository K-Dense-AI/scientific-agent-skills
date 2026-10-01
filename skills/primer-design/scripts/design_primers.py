#!/usr/bin/env python3
"""Design paired PCR primers with Primer3 and export auditable coordinates."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from _common import (PAIR_FIELDS, check_output_paths, dna, finite_number, integer,
                     load_primer3, read_fasta, revcomp, sha256_file, write_json)

# A deliberately explicit supported interface prevents misspelled tags being
# silently ignored by Primer3. More advanced Primer3 tasks use its native API.
GLOBAL_KEYS = set("""
PRIMER_NUM_RETURN PRIMER_MIN_SIZE PRIMER_OPT_SIZE PRIMER_MAX_SIZE
PRIMER_MIN_TM PRIMER_OPT_TM PRIMER_MAX_TM PRIMER_PAIR_MAX_DIFF_TM
PRIMER_MIN_GC PRIMER_OPT_GC_PERCENT PRIMER_MAX_GC PRIMER_MAX_POLY_X
PRIMER_GC_CLAMP PRIMER_MAX_END_GC PRIMER_MAX_END_STABILITY
PRIMER_MAX_SELF_ANY_TH PRIMER_MAX_SELF_END_TH PRIMER_MAX_HAIRPIN_TH
PRIMER_PAIR_MAX_COMPL_ANY_TH PRIMER_PAIR_MAX_COMPL_END_TH
PRIMER_SALT_MONOVALENT PRIMER_SALT_DIVALENT PRIMER_DNTP_CONC
PRIMER_DNA_CONC PRIMER_TM_FORMULA PRIMER_SALT_CORRECTIONS
PRIMER_PRODUCT_SIZE_RANGE PRIMER_MIN_5_PRIME_OVERLAP_OF_JUNCTION
PRIMER_MIN_3_PRIME_OVERLAP_OF_JUNCTION PRIMER_MAX_NS_ACCEPTED
PRIMER_WT_TM_GT PRIMER_WT_TM_LT PRIMER_WT_SIZE_GT PRIMER_WT_SIZE_LT
PRIMER_PAIR_WT_DIFF_TM PRIMER_PAIR_WT_PR_PENALTY
PRIMER_MIN_QUALITY PRIMER_MIN_END_QUALITY PRIMER_QUALITY_RANGE_MIN
PRIMER_QUALITY_RANGE_MAX PRIMER_WT_SEQ_QUAL PRIMER_WT_END_QUAL
""".split())
SEQUENCE_KEYS = set("""
SEQUENCE_TARGET SEQUENCE_INCLUDED_REGION SEQUENCE_EXCLUDED_REGION
SEQUENCE_PRIMER_PAIR_OK_REGION_LIST SEQUENCE_OVERLAP_JUNCTION_LIST
SEQUENCE_PRIMER SEQUENCE_PRIMER_REVCOMP SEQUENCE_QUALITY
""".split())


def region(value, length, name):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{name} requires [start, length]")
    start, size = value
    integer(start, name + ' start')
    integer(size, name + ' length', 1)
    if start + size > length:
        raise ValueError(f"{name} lies outside the selected FASTA record")


def validate_config(config, length):
    if not isinstance(config, dict) or set(config) - {"sequence_args", "global_args"}:
        raise ValueError("Config accepts only sequence_args and global_args mappings")
    sequence, global_args = config.get("sequence_args", {}), config.get("global_args", {})
    if not isinstance(sequence, dict) or not isinstance(global_args, dict):
        raise ValueError("sequence_args and global_args must be JSON objects")
    for values, allowed, label in [(sequence, SEQUENCE_KEYS, "sequence_args"), (global_args, GLOBAL_KEYS, "global_args")]:
        if set(values) - allowed:
            raise ValueError(f"Unsupported {label}: {sorted(set(values) - allowed)}; see input-contract.md")
    for key in ("SEQUENCE_TARGET", "SEQUENCE_EXCLUDED_REGION"):
        if key in sequence:
            if not isinstance(sequence[key], list):
                raise ValueError(f"{key} must be a list of [start, length] intervals")
            for value in sequence[key]:
                region(value, length, key)
    if "SEQUENCE_INCLUDED_REGION" in sequence:
        region(sequence["SEQUENCE_INCLUDED_REGION"], length, "SEQUENCE_INCLUDED_REGION")
    for key in ("SEQUENCE_PRIMER", "SEQUENCE_PRIMER_REVCOMP"):
        if key in sequence:
            sequence[key] = dna(sequence[key], key)
            if not 15 <= len(sequence[key]) <= 36:
                raise ValueError(f"{key}: supported annealing core length is 15..36")
    if "SEQUENCE_OVERLAP_JUNCTION_LIST" in sequence:
        junctions = sequence["SEQUENCE_OVERLAP_JUNCTION_LIST"]
        if not isinstance(junctions, list):
            raise ValueError("SEQUENCE_OVERLAP_JUNCTION_LIST must be a list")
        for value in junctions:
            integer(value, "junction")
            if value >= length - 1:
                raise ValueError("Junction must name the base immediately left of an internal template boundary")
    if "SEQUENCE_QUALITY" in sequence:
        quality = sequence["SEQUENCE_QUALITY"]
        if not isinstance(quality, list) or len(quality) != length:
            raise ValueError("SEQUENCE_QUALITY needs one integer per template base")
        for value in quality:
            integer(value, "quality")
    if "SEQUENCE_PRIMER_PAIR_OK_REGION_LIST" in sequence:
        rows = sequence["SEQUENCE_PRIMER_PAIR_OK_REGION_LIST"]
        if not isinstance(rows, list):
            raise ValueError("SEQUENCE_PRIMER_PAIR_OK_REGION_LIST must be a list")
        for row in rows:
            if not isinstance(row, list) or len(row) != 4:
                raise ValueError("OK region requires [left_start,left_length,right_start,right_length]")
            for value in (row[:2], row[2:]):
                if value != [-1, -1]:
                    region(value, length, "OK region")
    for key, value in global_args.items():
        if key == "PRIMER_PRODUCT_SIZE_RANGE":
            if not isinstance(value, list) or not value:
                raise ValueError("Product ranges must be a nonempty list of [minimum,maximum]")
            for limits in value:
                if not isinstance(limits, list) or len(limits) != 2:
                    raise ValueError("Product range requires [minimum,maximum]")
                integer(limits[0], "minimum product", 1)
                integer(limits[1], "maximum product", limits[0])
        else:
            finite_number(value, key)
    if global_args.get("PRIMER_MAX_NS_ACCEPTED", 0) != 0:
        raise ValueError("This workflow requires unambiguous primers; PRIMER_MAX_NS_ACCEPTED must be 0")
    return sequence, global_args


def bed_exclusions(path, records, record_id):
    exclusions = []
    with Path(path).open(encoding="utf-8") as handle:
        for number, raw in enumerate(handle, 1):
            if not raw.strip() or raw.startswith(("#", "track ", "browser ")):
                continue
            parts = raw.rstrip().split("\t")
            if len(parts) < 3 or parts[0] not in records:
                raise ValueError(f"BED line {number}: unknown record or fewer than 3 tab-separated columns")
            start, end = int(parts[1]), int(parts[2])
            region([start, end - start], len(records[parts[0]]), "BED interval")
            if parts[0] == record_id:
                exclusions.append([start, end - start])
    return exclusions


def design(args):
    records = read_fasta(args.template)
    record_id = args.record or (next(iter(records)) if len(records) == 1 else None)
    if record_id not in records:
        raise ValueError("Choose --record from the FASTA IDs when the template has multiple records")
    original = records[record_id]
    # Primer3's sequence alphabet is narrower than IUPAC. Unknown positions are
    # made explicitly unavailable, never guessed into a concrete nucleotide.
    template = "".join(base if base in "ACGT" else "N" for base in original)
    config = json.loads(Path(args.config).read_text()) if args.config else {}
    sequence_args, overrides = validate_config(config, len(template))
    global_args = {
        "PRIMER_TASK": "generic", "PRIMER_PICK_LEFT_PRIMER": 1,
        "PRIMER_PICK_RIGHT_PRIMER": 1, "PRIMER_PICK_INTERNAL_OLIGO": 0,
        "PRIMER_FIRST_BASE_INDEX": 0, "PRIMER_EXPLAIN_FLAG": 1,
        "PRIMER_THERMODYNAMIC_OLIGO_ALIGNMENT": 1,
        "PRIMER_NUM_RETURN": 5, "PRIMER_MIN_SIZE": 18, "PRIMER_OPT_SIZE": 20,
        "PRIMER_MAX_SIZE": 25, "PRIMER_MIN_TM": 57.0, "PRIMER_OPT_TM": 60.0,
        "PRIMER_MAX_TM": 63.0, "PRIMER_PAIR_MAX_DIFF_TM": 3.0,
        "PRIMER_MIN_GC": 20.0, "PRIMER_MAX_GC": 80.0,
        "PRIMER_MAX_POLY_X": 4, "PRIMER_MAX_NS_ACCEPTED": 0,
        "PRIMER_SALT_MONOVALENT": 50.0, "PRIMER_SALT_DIVALENT": 1.5,
        "PRIMER_DNTP_CONC": 0.6, "PRIMER_DNA_CONC": 50.0,
        "PRIMER_TM_FORMULA": 1, "PRIMER_SALT_CORRECTIONS": 1,
        "PRIMER_PRODUCT_SIZE_RANGE": [[70, 200]] if args.preset == "qpcr" else [[100, 1000]],
    }
    global_args.update(overrides)
    for key in ("PRIMER_NUM_RETURN", "PRIMER_MIN_SIZE", "PRIMER_OPT_SIZE", "PRIMER_MAX_SIZE", "PRIMER_MAX_POLY_X", "PRIMER_GC_CLAMP", "PRIMER_MAX_END_GC", "PRIMER_TM_FORMULA", "PRIMER_SALT_CORRECTIONS", "PRIMER_MIN_5_PRIME_OVERLAP_OF_JUNCTION", "PRIMER_MIN_3_PRIME_OVERLAP_OF_JUNCTION", "PRIMER_MAX_NS_ACCEPTED", "PRIMER_MIN_QUALITY", "PRIMER_MIN_END_QUALITY", "PRIMER_QUALITY_RANGE_MIN", "PRIMER_QUALITY_RANGE_MAX"):
        if key in global_args:
            integer(global_args[key], key)
    if global_args["PRIMER_TM_FORMULA"] not in (0, 1):
        raise ValueError("PRIMER_TM_FORMULA must be 0 (Breslauer) or 1 (SantaLucia)")
    if global_args["PRIMER_SALT_CORRECTIONS"] not in (0, 1, 2):
        raise ValueError("PRIMER_SALT_CORRECTIONS must be 0 (Schildkraut), 1 (SantaLucia), or 2 (Owczarzy)")
    if not 1 <= global_args["PRIMER_NUM_RETURN"] <= 100:
        raise ValueError("PRIMER_NUM_RETURN must be 1..100")
    if not 15 <= global_args["PRIMER_MIN_SIZE"] <= global_args["PRIMER_OPT_SIZE"] <= global_args["PRIMER_MAX_SIZE"] <= 36:
        raise ValueError("Require 15 <= MIN_SIZE <= OPT_SIZE <= MAX_SIZE <= 36")
    if not global_args["PRIMER_MIN_TM"] <= global_args["PRIMER_OPT_TM"] <= global_args["PRIMER_MAX_TM"]:
        raise ValueError("Require MIN_TM <= OPT_TM <= MAX_TM")
    if not 0 <= global_args["PRIMER_MIN_GC"] <= global_args["PRIMER_MAX_GC"] <= 100:
        raise ValueError("Require 0 <= MIN_GC <= MAX_GC <= 100")
    finite_number(global_args["PRIMER_DNA_CONC"], "PRIMER_DNA_CONC", positive=True)
    if args.mask_bed:
        sequence_args.setdefault("SEQUENCE_EXCLUDED_REGION", []).extend(bed_exclusions(args.mask_bed, records, record_id))
    sequence_args.update(SEQUENCE_ID=record_id, SEQUENCE_TEMPLATE=template)
    tails = {name: dna(getattr(args, name), name, empty=True) for name in ("forward_tail", "reverse_tail")}
    p3 = load_primer3()
    result = p3.bindings.design_primers(sequence_args, global_args)
    if result.get("PRIMER_ERROR"):
        raise ValueError(result["PRIMER_ERROR"])
    pairs = []
    for i in range(result.get("PRIMER_PAIR_NUM_RETURNED", 0)):
        left, left_length = result[f"PRIMER_LEFT_{i}"]
        right, right_length = result[f"PRIMER_RIGHT_{i}"]
        forward, reverse = result[f"PRIMER_LEFT_{i}_SEQUENCE"], result[f"PRIMER_RIGHT_{i}_SEQUENCE"]
        if template[left:left + left_length] != forward or revcomp(template[right - right_length + 1:right + 1]) != reverse:
            raise ValueError("Primer3 output failed template/orientation verification")
        product = template[left:right + 1]
        if len(product) != result[f"PRIMER_PAIR_{i}_PRODUCT_SIZE"]:
            raise ValueError("Primer3 output failed product-length verification")
        pairs.append({
            "pair_id": f"pair_{i + 1}", "forward": forward, "reverse": reverse, **tails,
            "forward_order_sequence": tails["forward_tail"] + forward,
            "reverse_order_sequence": tails["reverse_tail"] + reverse,
            "record_id": record_id, "forward_interval": [left, left + left_length],
            "reverse_interval": [right - right_length + 1, right + 1],
            "product_interval": [left, right + 1], "product_size": len(product),
            "tailed_product_size": len(product) + sum(map(len, tails.values())),
            "product_sequence": product,
            "tailed_product_sequence": tails["forward_tail"] + product + revcomp(tails["reverse_tail"]),
            "forward_tm_c": result[f"PRIMER_LEFT_{i}_TM"],
            "reverse_tm_c": result[f"PRIMER_RIGHT_{i}_TM"],
            "penalty": result[f"PRIMER_PAIR_{i}_PENALTY"],
            "specificity_status": "not_screened",
        })
    report = {
        "schema_version": "1.0", "status": "candidates_generated" if pairs else "no_candidates",
        "coordinate_system": "0-based half-open on supplied FASTA record; reverse oligos are 5-prime to 3-prime",
        "provenance": {"template_file": str(args.template), "template_sha256": sha256_file(args.template),
                       "record_id": record_id, "template_length": len(template),
                       "primer3_py_version": p3.__version__,
                       "libprimer3_version": p3.thermoanalysis.get_libprimer3_version(),
                       "python_version": sys.version.split()[0],
                       "config_sha256": sha256_file(args.config) if args.config else None,
                       "mask_bed_sha256": sha256_file(args.mask_bed) if args.mask_bed else None},
        "settings": {"preset": args.preset, "sequence_args": sequence_args, "global_args": global_args, "tails": tails},
        "ambiguous_template_bases_masked": sum(c not in "ACGT" for c in original),
        "pairs": pairs,
        "engine_explanations": {key: value for key, value in result.items() if key.endswith("EXPLAIN") or key in ("PRIMER_WARNING", "PRIMER_ERROR")},
        "limitations": ["Primer3 penalty is a design ranking, not experimental validation or genomic specificity.",
                        "Coordinates refer to the supplied template, not a genome unless the FASTA itself is that reference.",
                        "Defaults are starting conditions; record the actual polymerase/buffer and validate experimentally.",
                        "Tails were appended after design; assess full oligos separately for secondary structures."],
    }
    write_json(args.output, report)
    for path in (args.pairs_out, args.expected_out):
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
    if args.pairs_out:
        with Path(args.pairs_out).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=PAIR_FIELDS, delimiter="\t", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(pairs)
    if args.expected_out:
        with Path(args.expected_out).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(["pair_id", "record_id", "start", "end"])
            writer.writerows([p["pair_id"], record_id, *p["product_interval"]] for p in pairs)
    return 0 if pairs else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path, help="Local FASTA; no remote retrieval")
    parser.add_argument("--record", help="Exact FASTA ID; required for multi-record input")
    parser.add_argument("--preset", choices=("pcr", "qpcr"), default="pcr")
    parser.add_argument("--config", type=Path, help="JSON sequence_args/global_args overrides")
    parser.add_argument("--mask-bed", type=Path, help="Exclude primer binding in BED intervals in template coordinates")
    parser.add_argument("--forward-tail", default="", help="5-prime tail appended to forward core")
    parser.add_argument("--reverse-tail", default="", help="5-prime tail appended to reverse core")
    parser.add_argument("--output", required=True, type=Path, help="JSON design report")
    parser.add_argument("--pairs-out", type=Path, help="TSV for downstream thermodynamics/screening")
    parser.add_argument("--expected-out", type=Path, help="TSV intended product coordinates on this template")
    args = parser.parse_args(argv)
    try:
        check_output_paths([args.template, args.config, args.mask_bed], [args.output, args.pairs_out, args.expected_out])
        return design(args)
    except (ValueError, OSError, RuntimeError, TypeError, OverflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
