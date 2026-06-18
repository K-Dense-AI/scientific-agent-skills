#!/usr/bin/env python3
"""
Mass & Chemistry Calculator

Compute masses and isotope distributions for peptides (amino-acid sequences),
empirical formulas, or both. Reports monoisotopic and average mass, m/z for a
range of charge states, the molecular formula, and the theoretical isotope
pattern.

Usage:
    python mass_calculator.py --peptide DFPIANGER
    python mass_calculator.py --peptide "PEPTIDEM(Oxidation)K" --charges 1 2 3
    python mass_calculator.py --formula C6H12O6 --isotopes 5
    python mass_calculator.py --peptide DFPIANGER --isotopes 6 --csv iso.csv
"""

import argparse
import sys

try:
    import pyopenms as ms
except ImportError:
    print("Error: pyopenms not installed. Install with: uv pip install pyopenms")
    sys.exit(1)

PROTON = 1.0072764665789


def report_isotopes(formula, n, csv=None):
    gen = ms.CoarseIsotopePatternGenerator(n)
    dist = formula.getIsotopeDistribution(gen)
    print(f"\nIsotope pattern (top {n}):")
    rows = []
    for iso in dist.getContainer():
        mz = iso.getMZ()
        prob = iso.getIntensity()
        print(f"  m/z {mz:.4f}  rel.abundance {prob*100:6.2f}%")
        rows.append((mz, prob))
    if csv:
        import csv as csvmod
        with open(csv, "w", newline="") as fh:
            w = csvmod.writer(fh)
            w.writerow(["mass", "rel_abundance"])
            w.writerows(rows)
        print(f"Wrote {csv}")


def main():
    parser = argparse.ArgumentParser(description="Compute masses and isotope distributions.")
    parser.add_argument("--peptide", help="Amino-acid sequence (TPP/OpenMS mod syntax allowed)")
    parser.add_argument("--formula", help="Empirical formula, e.g. C6H12O6")
    parser.add_argument("--charges", type=int, nargs="+", default=[1, 2, 3],
                        help="Charge states for m/z (default 1 2 3)")
    parser.add_argument("--isotopes", type=int, default=0, help="Number of isotope peaks to report")
    parser.add_argument("--negative", action="store_true", help="Report negative-mode m/z")
    parser.add_argument("--csv", help="Write isotope pattern to CSV")
    args = parser.parse_args()

    if not args.peptide and not args.formula:
        parser.error("provide --peptide and/or --formula")

    sign = -1 if args.negative else 1

    if args.peptide:
        seq = ms.AASequence.fromString(args.peptide)
        formula = seq.getFormula()
        mono = seq.getMonoWeight()
        avg = seq.getAverageWeight()
        print(f"Peptide: {seq.toString()}")
        print(f"Formula: {formula.toString()}")
        print(f"Monoisotopic mass: {mono:.5f}")
        print(f"Average mass: {avg:.5f}")
        for z in args.charges:
            mz = (mono + sign * z * PROTON) / z
            print(f"  [M{'+' if not args.negative else '-'}{z}H]{'+' if not args.negative else '-'} m/z = {mz:.5f} (z={z})")
        if args.isotopes:
            report_isotopes(formula, args.isotopes, args.csv if not args.formula else None)

    if args.formula:
        formula = ms.EmpiricalFormula(args.formula)
        print(f"\nFormula: {formula.toString()}")
        print(f"Monoisotopic mass: {formula.getMonoWeight():.5f}")
        print(f"Average mass: {formula.getAverageWeight():.5f}")
        for z in args.charges:
            mz = (formula.getMonoWeight() + sign * z * PROTON) / z
            print(f"  m/z = {mz:.5f} (z={z})")
        if args.isotopes:
            report_isotopes(formula, args.isotopes, args.csv)


if __name__ == "__main__":
    main()
