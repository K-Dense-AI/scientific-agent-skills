#!/usr/bin/env python3
"""Drug-drug interaction prediction: ICH M12 basic models and the mechanistic static model.

ICH M12 (Step 4, 2024) sets out a stepwise risk assessment: in vitro data feed
basic models whose cut-offs trigger further evaluation, and a
mechanistic static or PBPK model can be used to refine a positive basic-model
signal. The basic models are deliberately conservative — they are designed to
over-predict under their assumptions. Uncertain inputs or unmodeled mechanisms
can invalidate a negative screen; a positive screen needs further evaluation.

    python3 ddi_static.py --basic --ki 0.5 --imax 2.0 --fu 0.05 --dose 100
    python3 ddi_static.py --basic --tdi --ki-inact 1.2 --kinact 0.04 --imax 2.0 --fu 0.05
    python3 ddi_static.py --msm --ki 0.5 --imax 2.0 --fu 0.05 --dose 100 --fm 0.9 --fg 0.7

All concentrations are in the same molar or mass units as Ki, KI and EC50. The
script does not know your units and cannot check them; a Ki in micromolar
against an Imax in ng/mL is a silent, and common, error.
"""

from __future__ import annotations

import argparse
import math
from typing import Sequence

from _common import InputError, Report, add_format_argument, main_wrapper

# ICH M12 basic-model cut-offs.
CUTOFF_R1_HEPATIC = 1.02
CUTOFF_R1_GUT = 11.0
CUTOFF_R2_TDI = 1.25
CUTOFF_R3_INDUCTION = 0.80
CUTOFF_TRANSPORTER_HEPATIC_UPTAKE = 1.1
CUTOFF_TRANSPORTER_INTESTINAL = 10.0
CUTOFF_TRANSPORTER_RENAL = 0.1
CUTOFF_TRANSPORTER_MATE = 0.02

# Default intestinal dissolution volume used to form the nominal gut
# concentration, and the hepatic blood flow used for the inlet concentration.
GUT_VOLUME_ML = 250.0
HEPATIC_BLOOD_FLOW_L_H = 97.0
DEFAULT_KDEG_HEPATIC = 0.0005  # per minute; roughly a 23 h enzyme half-life


def r1_reversible(i_conc: float, ki: float) -> float:
    """Basic reversible inhibition ratio, ``1 + [I]/Ki``."""
    if ki <= 0:
        raise InputError("Ki must be positive")
    return 1.0 + i_conc / ki


def r2_time_dependent(i_conc: float, ki_inact: float, kinact: float, kdeg: float) -> float:
    """Basic TDI ratio, ``(kobs + kdeg) / kdeg``."""
    if ki_inact <= 0 or kdeg <= 0:
        raise InputError("KI and kdeg must be positive")
    kobs = kinact * i_conc / (ki_inact + i_conc)
    return (kobs + kdeg) / kdeg


def r3_induction(i_conc: float, emax: float, ec50: float, scaling: float = 1.0) -> float:
    """Basic induction ratio; values at or below 0.80 flag a potential inducer."""
    if ec50 <= 0:
        raise InputError("EC50 must be positive")
    return 1.0 / (1.0 + scaling * emax * i_conc / (ec50 + i_conc))


def inlet_concentration(imax: float, fu: float, dose: float, fa: float, fg: float, ka: float, blood_ratio: float = 1.0) -> float:
    """Maximum unbound hepatic inlet concentration.

    ``Iu,inlet,max = fu * (Imax + Fa*Fg*ka*Dose / (Qh*RB))``. This is the
    estimated inlet concentration under these assumptions, rather than
    measured systemic Imax and is what M12 asks for in hepatic uptake-transporter
    assessments.
    """
    portal = fa * fg * (ka * 60.0) * dose / (HEPATIC_BLOOD_FLOW_L_H * blood_ratio)
    return fu * (imax + portal)


def mechanistic_static(
    ih: float,
    ig: float,
    fm: float,
    fg: float,
    ki: float | None = None,
    ki_inact: float | None = None,
    kinact: float | None = None,
    kdeg_h: float = DEFAULT_KDEG_HEPATIC,
    kdeg_g: float = 0.0005,
    ind_emax: float = 0.0,
    ind_ec50: float | None = None,
    ind_scaling: float = 1.0,
) -> dict[str, float]:
    """Mechanistic static model AUC ratio, combining reversible, TDI and induction terms.

    ``AUCR = 1/(Ag*Bg*Cg*(1-Fg) + Fg) * 1/(Ah*Bh*Ch*fm + (1-fm))``

    The two fractions that dominate the answer are ``fm`` (the fraction of
    systemic clearance through the affected enzyme) and ``Fg`` (the fraction
    escaping gut metabolism). Hepatic inhibition alone is limited
    by ``1/(1-fm)``; including gut inhibition gives ``1/((1-fm)*Fg)``, so an fm assumed at 1.0 when it is
    really 0.7 changes an unbounded prediction into a 3.3-fold ceiling.
    """
    if not all(math.isfinite(x) for x in (ih, ig, fm, fg, kdeg_h, kdeg_g, ind_emax, ind_scaling)):
        raise InputError("MSM inputs must be finite")
    if ih < 0 or ig < 0 or not 0 <= fm <= 1 or not 0 < fg <= 1 or min(kdeg_h, kdeg_g) <= 0 or min(ind_emax, ind_scaling) < 0:
        raise InputError("MSM concentrations/fm/induction must be non-negative, Fg in (0,1], fm <= 1, and kdeg positive")
    for value in (ki, ki_inact, ind_ec50):
        if value is not None and (not math.isfinite(value) or value <= 0):
            raise InputError("Ki, KI and EC50 must be finite and positive when supplied")
    if (ki_inact is None) != (kinact is None) or (kinact is not None and (not math.isfinite(kinact) or kinact < 0)):
        raise InputError("TDI requires paired KI and non-negative kinact")
    def terms(i_conc: float, kdeg: float) -> tuple[float, float, float]:
        a = 1.0 / (1.0 + i_conc / ki) if ki else 1.0
        if ki_inact and kinact:
            b = kdeg / (kdeg + kinact * i_conc / (ki_inact + i_conc))
        else:
            b = 1.0
        c = 1.0 + ind_scaling * ind_emax * i_conc / (ind_ec50 + i_conc) if ind_ec50 else 1.0
        return a, b, c

    ah, bh, ch = terms(ih, kdeg_h)
    ag, bg, cg = terms(ig, kdeg_g)
    gut = 1.0 / (ag * bg * cg * (1.0 - fg) + fg)
    hepatic = 1.0 / (ah * bh * ch * fm + (1.0 - fm))
    return {
        "Ah_reversible": ah,
        "Bh_tdi": bh,
        "Ch_induction": ch,
        "Ag_reversible": ag,
        "Bg_tdi": bg,
        "Cg_induction": cg,
        "gut_component": gut,
        "hepatic_component": hepatic,
        "auc_ratio": gut * hepatic,
        "maximum_possible_auc_ratio": 1.0 / ((1.0 - fm) * fg) if fm < 1 else float("inf"),
        "hepatic_only_auc_ceiling": 1.0 / (1.0 - fm) if fm < 1 else float("inf"),
    }


def classify(auc_ratio: float) -> str:
    """FDA/ICH perpetrator classification bands for an AUC ratio."""
    if auc_ratio >= 5.0:
        return "strong inhibitor (AUCR >= 5)"
    if auc_ratio >= 2.0:
        return "moderate inhibitor (2 <= AUCR < 5)"
    if auc_ratio >= 1.25:
        return "weak inhibitor (1.25 <= AUCR < 2)"
    if auc_ratio > 0.8:
        return "within the 0.8-1.25 screening band; clinical relevance requires substrate-specific assessment"
    if auc_ratio > 0.5:
        return "weak inducer (0.5 < AUCR <= 0.8)"
    if auc_ratio > 0.2:
        return "moderate inducer (0.2 < AUCR <= 0.5)"
    return "strong inducer (AUCR <= 0.2)"


# --------------------------------------------------------------------- CLI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ICH M12 basic DDI models and the mechanistic static model.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--basic", action="store_true", help="run the basic models and report against their cut-offs")
    parser.add_argument("--msm", action="store_true", help="run the mechanistic static model")

    parser.add_argument("--imax", type=float, help="maximum total systemic plasma concentration of the perpetrator")
    parser.add_argument("--fu-validated", action="store_true", help="accuracy and precision of fu < 0.01 demonstrated")
    parser.add_argument("--fu", type=float, default=1.0, help="unbound fraction in plasma (default: 1.0)")
    parser.add_argument("--dose", type=float, help="perpetrator amount; use micromoles when concentrations are micromolar (amount/L)")
    parser.add_argument("--ka", type=float, default=0.1, help="perpetrator absorption rate constant, per min (default: 0.1)")
    parser.add_argument("--fa", type=float, default=1.0, help="fraction absorbed (default: 1.0)")
    parser.add_argument("--fg-perpetrator", type=float, default=1.0, help="perpetrator gut availability (default: 1.0)")
    parser.add_argument("--blood-ratio", type=float, default=1.0, help="blood-to-plasma ratio (default: 1.0)")

    parser.add_argument("--ki", type=float, help="reversible inhibition constant")
    parser.add_argument("--tdi", action="store_true", help="evaluate time-dependent inhibition")
    parser.add_argument("--ki-inact", type=float, help="KI for time-dependent inactivation")
    parser.add_argument("--kinact", type=float, help="maximum inactivation rate constant, per min")
    parser.add_argument("--kdeg", type=float, default=DEFAULT_KDEG_HEPATIC, help="hepatic enzyme degradation rate, per min")
    parser.add_argument("--ind-emax", type=float, default=0.0, help="maximum fold induction minus one")
    parser.add_argument("--ind-ec50", type=float, help="induction EC50")
    parser.add_argument("--ind-scaling", type=float, default=1.0, help="induction scaling factor d (default: 1.0)")

    parser.add_argument("--fm", type=float, help="fraction of victim clearance via the affected enzyme")
    parser.add_argument("--fg", type=float, default=1.0, help="victim fraction escaping gut metabolism (default: 1.0)")
    parser.add_argument("--transporter", choices=("hepatic-uptake", "intestinal", "renal", "mate", "systemic-efflux"), help="also run the transporter basic model")
    parser.add_argument("--transporter-ki", type=float)
    add_format_argument(parser)
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from _common import validate_numeric_args
    validate_numeric_args(args)
    if args.basic == args.msm:
        raise InputError("choose exactly one of --basic or --msm")
    if args.imax is None:
        raise InputError("--imax is required")
    if not 0 < args.fu <= 1:
        raise InputError("--fu must be in (0, 1]")

    report = Report()
    for name in ("imax", "dose", "kinact", "ind_emax", "ind_scaling"):
        value = getattr(args, name)
        if value is not None and value < 0:
            raise InputError(f"--{name.replace('_', '-')} must be non-negative")
    for name in ("ki", "ki_inact", "ind_ec50", "transporter_ki", "ka", "kdeg", "blood_ratio"):
        value = getattr(args, name)
        if value is not None and value <= 0:
            raise InputError(f"--{name.replace('_', '-')} must be positive")
    if not 0 <= args.fa <= 1 or not 0 <= args.fg_perpetrator <= 1:
        raise InputError("--fa and --fg-perpetrator must be in [0, 1]")
    if args.fu < 0.01 and not args.fu_validated:
        report.finding("fu below 0.01 without demonstrated assay reliability: using M12's 0.01 floor")
        args.fu = 0.01
    if args.tdi and (args.ki_inact is None or args.kinact is None):
        raise InputError("--tdi needs --ki-inact and --kinact")
    if (args.ind_emax > 0) != (args.ind_ec50 is not None):
        raise InputError("supply --ind-emax > 0 together with --ind-ec50")
    unbound = args.imax * args.fu
    gut = (args.dose / (GUT_VOLUME_ML / 1000.0)) if args.dose is not None else None
    report.scalar("imax_total", args.imax)
    report.scalar("imax_unbound", unbound)
    if gut is not None:
        report.scalar("gut_concentration", gut)
    report.note(
        "Units are not checked. Ki, KI, EC50, Imax and dose must all be expressed on the same molar "
        "basis; the gut concentration is dose divided by 250 mL."
    )

    if args.basic:
        rows = []
        if args.ki:
            r1 = r1_reversible(unbound, args.ki)
            rows.append(
                {
                    "model": "reversible inhibition, hepatic",
                    "value": r1,
                    "cutoff": f">= {CUTOFF_R1_HEPATIC}",
                    "triggers_study": r1 >= CUTOFF_R1_HEPATIC,
                    "basis": "1 + Imax,u/Ki",
                }
            )
            if gut is not None:
                r1g = r1_reversible(gut, args.ki)
                rows.append(
                    {
                        "model": "reversible inhibition, intestinal (CYP3A4)",
                        "value": r1g,
                        "cutoff": f">= {CUTOFF_R1_GUT}",
                        "triggers_study": r1g >= CUTOFF_R1_GUT,
                        "basis": "1 + Igut/Ki, Igut = dose/250 mL",
                    }
                )
        if args.tdi:
            if args.ki_inact is None or args.kinact is None:
                raise InputError("--tdi needs --ki-inact and --kinact")
            r2 = r2_time_dependent(unbound * 5.0, args.ki_inact, args.kinact, args.kdeg)
            rows.append(
                {
                    "model": "time-dependent inhibition, hepatic",
                    "value": r2,
                    "cutoff": f">= {CUTOFF_R2_TDI}",
                    "triggers_study": r2 >= CUTOFF_R2_TDI,
                    "basis": "(kobs + kdeg)/kdeg at 5 x Imax,u",
                }
            )
        if args.ind_ec50 and args.ind_emax:
            r3 = r3_induction(unbound * 10.0, args.ind_emax, args.ind_ec50, args.ind_scaling)
            rows.append(
                {
                    "model": "induction",
                    "value": r3,
                    "cutoff": f"<= {CUTOFF_R3_INDUCTION}",
                    "triggers_study": r3 <= CUTOFF_R3_INDUCTION,
                    "basis": "1/(1 + d*Emax*I/(EC50+I)) at 10 x Imax,u",
                }
            )
        if args.transporter:
            if not args.transporter_ki:
                raise InputError("--transporter needs --transporter-ki")
            if args.transporter == "hepatic-uptake":
                if args.dose is None:
                    raise InputError("hepatic uptake needs --dose for the inlet concentration")
                conc = inlet_concentration(args.imax, args.fu, args.dose, args.fa, args.fg_perpetrator, args.ka, args.blood_ratio)
                value = 1.0 + conc / args.transporter_ki
                cutoff, triggers = CUTOFF_TRANSPORTER_HEPATIC_UPTAKE, value >= CUTOFF_TRANSPORTER_HEPATIC_UPTAKE
                basis = "1 + Iu,inlet,max/Ki,u (OATP1B1/1B3)"
            elif args.transporter == "intestinal":
                if gut is None:
                    raise InputError("intestinal transporter assessment needs --dose")
                value = gut / args.transporter_ki
                cutoff, triggers = CUTOFF_TRANSPORTER_INTESTINAL, value >= CUTOFF_TRANSPORTER_INTESTINAL
                basis = "Igut/IC50 (P-gp, BCRP)"
            else:
                value = unbound / args.transporter_ki
                cutoff = CUTOFF_TRANSPORTER_MATE if args.transporter in {"mate", "systemic-efflux"} else CUTOFF_TRANSPORTER_RENAL
                triggers = value >= cutoff
                basis = "Imax,u/IC50,u (MATE1/2-K or systemic P-gp/BCRP)" if cutoff == CUTOFF_TRANSPORTER_MATE else "Imax,u/IC50,u (OAT1/3, OCT2)"
            rows.append(
                {
                    "model": f"transporter inhibition, {args.transporter}",
                    "value": value,
                    "cutoff": f">= {cutoff}",
                    "triggers_study": triggers,
                    "basis": basis,
                }
            )
        if not rows:
            raise InputError("--basic needs at least one of --ki, --tdi, or --ind-ec50 with --ind-emax")
        report.table("ICH M12 basic models", rows)
        for row in rows:
            if row["triggers_study"]:
                report.finding(
                    f"{row['model']}: {row['value']:.4g} meets the cut-off {row['cutoff']} - a clinical "
                    "DDI study or a refined mechanistic/PBPK assessment is indicated"
                )
        report.note(
            "Basic models are intentionally conservative. A result below the cut-off supports not "
            "studying the interaction; a result above it is a trigger for further evaluation, not a "
            "prediction of clinical magnitude."
        )

    else:
        if args.fm is None:
            raise InputError("--msm needs --fm")
        if not 0 < args.fm <= 1:
            raise InputError("--fm must be in (0, 1]")
        if not 0 < args.fg <= 1:
            raise InputError("--fg must be in (0, 1]")
        if args.dose is None:
            raise InputError("--msm needs --dose (use 0 for a systemic-only scenario)")
        ih = inlet_concentration(args.imax, args.fu, args.dose, args.fa, args.fg_perpetrator, args.ka, args.blood_ratio)
        ig = args.fa * args.ka * 60.0 * args.dose / 18.0
        report.scalar("msm_hepatic_inlet_unbound", ih)
        report.scalar("msm_enterocyte_concentration", ig)
        result = mechanistic_static(
            ih=ih,
            ig=ig,
            fm=args.fm,
            fg=args.fg,
            ki=args.ki,
            ki_inact=args.ki_inact if args.tdi else None,
            kinact=args.kinact if args.tdi else None,
            kdeg_h=args.kdeg,
            ind_emax=args.ind_emax,
            ind_ec50=args.ind_ec50,
            ind_scaling=args.ind_scaling,
        )
        report.table("mechanistic static model", [{"term": k, "value": v} for k, v in result.items()])
        report.scalar("predicted_auc_ratio", result["auc_ratio"])
        report.scalar("classification", classify(result["auc_ratio"]))
        report.note(
            f"With fm = {args.fm} and Fg = {args.fg}, the combined hepatic/gut inhibition ceiling is "
            f"{result['maximum_possible_auc_ratio']:.2f}-fold. If the prediction approaches that "
            "ceiling, fm is doing more work than the inhibition constants."
        )
        if gut is None:
            report.note("no --dose given, so the intestinal component was evaluated at zero inhibitor concentration")
        if args.fm > 0.95:
            report.finding(
                f"fm = {args.fm} implies almost all clearance goes through one enzyme. This is rarely "
                "established and it drives the prediction; state the evidence for it or run a sensitivity "
                "analysis across a plausible range."
            )
        if result["auc_ratio"] >= 2.0:
            report.finding(
                f"predicted AUC ratio {result['auc_ratio']:.2f} - {classify(result['auc_ratio'])}; "
                "this screening prediction needs confirmation before clinical or labelling conclusions"
            )
        report.note(
            "The mechanistic static model assumes a single constant perpetrator concentration and no "
            "time course. It is a screening refinement; where the interaction is decision-relevant, "
            "ICH M12 points to PBPK with a verified perpetrator model."
        )

    if args.msm and args.ind_emax and (args.ki is not None or args.tdi):
        report.finding("Run inhibition-only and induction-only scenarios separately as well: combined effects can mask either mechanism (ICH M12 7.5.1.1)")
    return report.emit(args.format)


if __name__ == "__main__":
    raise SystemExit(main_wrapper(run))
