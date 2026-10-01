#!/usr/bin/env python3
"""Check, simulate, fit, and profile steady-state 13C metabolic flux models."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "simulate", "fit"):
        p = sub.add_parser(name)
        p.add_argument("--model", type=Path, required=True)
        p.add_argument("--data", type=Path, required=True, help="Experiment/measurement JSON")
        p.add_argument("--output", type=Path, help="JSON output; defaults to stdout")
        if name == "simulate":
            p.add_argument("--fluxes", type=Path, required=True, help="JSON mapping of reaction IDs to fluxes")
        if name == "fit":
            p.add_argument("--starts", type=int, default=8)
            p.add_argument("--seed", type=int, default=2026)
            p.add_argument("--maxiter", type=int, default=1000)
            p.add_argument("--profile", action="append", default=[], help="Reaction to profile; repeat for multiple reactions")
            p.add_argument("--profile-points", type=int, default=21)
            p.add_argument("--profile-starts", type=int, default=4)
            p.add_argument("--confidence", type=float, default=.95)
    args = parser.parse_args()
    from _mfa_model import InputError, Network, Observations, read_json, require
    from _mfa_fit import FluxSpace, diagnostics, fit, profile
    import numpy as np
    try:
        inputs = [args.model, args.data]
        if args.command == "simulate":
            inputs.append(args.fluxes)
        require(args.output is None or all(args.output.resolve() != path.resolve() for path in inputs),
                "Output must not overwrite an input file")
        network = Network(read_json(args.model))
        observations = Observations(read_json(args.data), network)
        space = FluxSpace(network)
        versions = {}
        for package in ("mfapy", "numpy", "scipy"):
            try:
                versions[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                versions[package] = "not installed"
        result = dict(command=args.command, model=network.spec["name"], versions=versions,
                      input_sha256={str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs})
        if args.command == "check":
            result.update(status="input_contract_valid", free_flux_dimensions=space.dimension,
                          independent_measurements=observations.size, warnings=observations.warnings,
                          note="Checks declared mapping consistency and feasibility, not biological correctness or isotope steady state")
        elif args.command == "simulate":
            vector = network.check_flux(read_json(args.fluxes))
            result["predictions"] = {exp["id"]: {key: value.tolist() for key, value in network.predict(vector, exp).items()}
                                     for exp in observations.spec["experiments"]}
        else:
            fitted = fit(observations, args.starts, args.seed, args.maxiter)
            result.update(diagnostics(observations, fitted))
            result["settings"] = dict(starts=args.starts, seed=args.seed, maxiter=args.maxiter,
                                      profile_points=args.profile_points, profile_starts=args.profile_starts,
                                      confidence=args.confidence)
            result["profiles"] = [profile(observations, fitted, rid, args.profile_points,
                                          args.profile_starts, args.seed, args.maxiter, args.confidence)
                                  for rid in dict.fromkeys(args.profile)]
        text = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 0
    except (InputError, ValueError, TypeError, KeyError, OSError, np.linalg.LinAlgError,
            FloatingPointError, ZeroDivisionError) as exc:
        print(f"mfa: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
