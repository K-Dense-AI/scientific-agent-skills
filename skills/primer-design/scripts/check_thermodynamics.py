#!/usr/bin/env python3
"""Assess annealing cores and full tailed oligos using explicit solution chemistry."""
from __future__ import annotations

import argparse
import itertools
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from _common import check_output_paths, finite_number, load_primer3, read_pairs, sha256_file, write_json


def structure(result):
    values = [result.tm, result.dg, result.dh, result.ds]
    if any(not math.isfinite(v) for v in values):
        raise ValueError("Thermodynamic engine returned nonfinite values")
    return {"structure_found": bool(result.structure_found), "tm_c": result.tm,
            "delta_g_kcal_per_mol": result.dg / 1000,
            "delta_h_kcal_per_mol": result.dh / 1000,
            "delta_s_cal_per_mol_k": result.ds,
            "ascii_structure": result.ascii_structure}


def assess(args):
    pairs = read_pairs(args.pairs)
    p3 = load_primer3()
    chemistry = {key: finite_number(getattr(args, key), key, positive=(key == "dna_conc"))
                 for key in ("mv_conc", "dv_conc", "dntp_conc", "dna_conc")}
    finite_number(args.temp_c, "temp_c", -20)
    if args.temp_c > 100:
        raise ValueError("temp_c must be between -20 and 100 Celsius")
    if args.max_interactions < 1:
        raise ValueError("max_interactions must be positive")
    count = 2 * len(pairs)
    interaction_count = count * (count - 1) // 2 if args.multiplex else len(pairs)
    if interaction_count > args.max_interactions:
        raise ValueError(f"{interaction_count} dimer comparisons exceed --max-interactions; partition deliberately or raise the limit")
    thermo_args = {**chemistry, "temp_c": args.temp_c}
    records, pair_summaries, warnings = [], [], []
    if chemistry["dntp_conc"] >= chemistry["dv_conc"] and chemistry["dv_conc"] > 0:
        warnings.append("Total dNTP is at least divalent concentration; verify the buffer/free-Mg assumptions used by the salt model.")
    for pair in pairs:
        entries = []
        for role in ("forward", "reverse"):
            core, tail = pair[role], pair[f"{role}_tail"]
            full = tail + core
            entry = {"oligo_id": f"{pair['pair_id']}:{role}", "pair_id": pair["pair_id"],
                     "role": role, "annealing_core": core, "tail": tail,
                     "order_sequence": full, "length": len(full), "core_length": len(core),
                     "core_gc_percent": 100 * sum(c in "GC" for c in core) / len(core)}
            if not 2 <= len(core) <= 60:
                raise ValueError(f"{entry['oligo_id']}: core length must be 2..60 for this nearest-neighbor workflow")
            entry["annealing_tm_c"] = p3.calc_tm(core, **chemistry, tm_method=args.tm_method, salt_corrections_method=args.salt_corrections_method)
            if not math.isfinite(entry["annealing_tm_c"]):
                raise ValueError("Thermodynamic engine returned nonfinite core Tm")
            entry["core_hairpin"] = structure(p3.calc_hairpin(core, **thermo_args, output_structure=True))
            entry["core_homodimer"] = structure(p3.calc_homodimer(core, **thermo_args, output_structure=True))
            entry["core_self_three_prime"] = structure(p3.calc_end_stability(core, core, **thermo_args))
            if len(full) <= 60:
                entry["full_oligo_status"] = "computed"
                entry["full_hairpin"] = structure(p3.calc_hairpin(full, **thermo_args, output_structure=True))
                entry["full_homodimer"] = structure(p3.calc_homodimer(full, **thermo_args, output_structure=True))
                entry["full_self_three_prime"] = structure(p3.calc_end_stability(full, full, **thermo_args))
            else:
                entry["full_oligo_status"] = "unsupported_length"
                warnings.append(f"{entry['oligo_id']}: full oligo exceeds 60 nt; full-length secondary structure is unresolved, not truncated.")
            records.append(entry)
            entries.append(entry)
        pair_summaries.append({"pair_id": pair["pair_id"],
                               "core_tm_difference_c": abs(entries[0]["annealing_tm_c"] - entries[1]["annealing_tm_c"])})
    comparisons = itertools.combinations(records, 2) if args.multiplex else ((records[i], records[i + 1]) for i in range(0, len(records), 2))
    interactions = []
    for a, b in comparisons:
        interaction = {"oligo_a": a["oligo_id"], "oligo_b": b["oligo_id"],
                       "cross_pair": a["pair_id"] != b["pair_id"]}
        if max(a["length"], b["length"]) > 60:
            interaction["status"] = "unsupported_length"
        else:
            seq_a, seq_b = a["order_sequence"], b["order_sequence"]
            interaction.update(status="computed",
                heterodimer=structure(p3.calc_heterodimer(seq_a, seq_b, **thermo_args, output_structure=True)),
                a_three_prime_to_b=structure(p3.calc_end_stability(seq_a, seq_b, **thermo_args)),
                b_three_prime_to_a=structure(p3.calc_end_stability(seq_b, seq_a, **thermo_args)))
        interactions.append(interaction)
    complete = all(r["full_oligo_status"] == "computed" for r in records)
    report = {"schema_version": "1.0", "status": "computed" if complete else "incomplete",
              "provenance": {"pairs_file": str(args.pairs), "pairs_sha256": sha256_file(args.pairs),
                             "primer3_py_version": p3.__version__,
                             "libprimer3_version": p3.thermoanalysis.get_libprimer3_version(),
                             "python_version": sys.version.split()[0]},
              "settings": {**chemistry, "temp_c": args.temp_c, "multiplex": args.multiplex,
                           "tm_method": args.tm_method, "salt_corrections_method": args.salt_corrections_method,
                           "secondary_structure_model": "libprimer3 thermodynamic alignment defaults",
                           "max_interactions": args.max_interactions},
              "units": {"mv_conc": "mM monovalent cations", "dv_conc": "mM total divalent cations",
                        "dntp_conc": "mM total dNTPs", "dna_conc": "nM oligonucleotide concentration under Primer3 conventions",
                        "temp_c": "Celsius for delta-G; not annealing temperature selection"},
              "oligos": records, "pairs": pair_summaries, "interactions": interactions, "warnings": warnings,
              "limitations": ["Predictions do not establish PCR performance or a universal pass/fail cutoff.",
                              "Core Tm excludes untemplated tails; secondary structures use complete ordered oligos.",
                              "End-stability calculations are directional and are reported in both orders.",
                              "Modified bases, degenerate mixtures, unequal multiplex concentrations, and oligos >60 nt require a suitable external model.",
                              "Multiplex dimer checks do not screen cross-pair genomic amplification."]}
    write_json(args.output, report)
    return 0 if complete else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mv-conc", type=float, default=50.0, help="Monovalent cations, mM")
    parser.add_argument("--dv-conc", type=float, default=1.5, help="Total divalent cations, mM")
    parser.add_argument("--dntp-conc", type=float, default=0.6, help="Total dNTPs, mM (sum of all four)")
    parser.add_argument("--dna-conc", type=float, default=50.0, help="Oligonucleotide concentration, nM")
    parser.add_argument("--temp-c", type=float, default=37.0, help="Temperature at which delta-G is calculated")
    parser.add_argument("--tm-method", choices=("breslauer", "santalucia"), default="santalucia")
    parser.add_argument("--salt-corrections-method", choices=("schildkraut", "santalucia", "owczarzy"), default="santalucia")
    parser.add_argument("--multiplex", action="store_true", help="Check all unordered oligo combinations, including between pairs")
    parser.add_argument("--max-interactions", type=int, default=10000)
    args = parser.parse_args(argv)
    try:
        check_output_paths([args.pairs], [args.output])
        return assess(args)
    except (ValueError, OSError, RuntimeError, TypeError, OverflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
