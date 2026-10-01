"""Validated carbon maps and a pinned mfapy steady-state forward model."""
from __future__ import annotations

from collections import Counter
import contextlib
import io
import json
import math
from pathlib import Path
import re

import numpy as np
from scipy.linalg import cholesky, solve_triangular


class InputError(ValueError):
    """A scientific input contract was not met."""


def require(condition, message):
    if not condition:
        raise InputError(message)


def fields(value, required, optional=()):
    require(isinstance(value, dict), "Expected an object")
    require(set(required) <= value.keys(), f"Missing fields: {set(required) - value.keys()}")
    require(value.keys() <= set(required) | set(optional),
            f"Unknown fields: {value.keys() - set(required) - set(optional)}")


def number(value, label):
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value), f"{label} must be a finite number")
    return float(value)


def identifier(value):
    # mfapy generates numerical code internally; only these identifiers reach it.
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,39}", value),
            f"Invalid identifier {value!r}; use ASCII letters/digits, starting with a letter")
    return value


def unique(items, label):
    require(len(set(items)) == len(items), f"Duplicate {label}")


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise InputError(f"Non-finite JSON constant: {value}")

    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=invalid_constant)


class Network:
    def __init__(self, spec):
        fields(spec, {"schema_version", "name", "flux_unit", "provenance", "metabolites",
                      "reactions", "fragments"})
        require(type(spec["schema_version"]) is int and spec["schema_version"] == 1,
                "Only schema_version 1 is supported")
        for key in ("name", "flux_unit", "provenance"):
            require(isinstance(spec[key], str) and bool(spec[key].strip()), f"Missing {key}")
        for key, maximum in (("metabolites", 100), ("reactions", 200), ("fragments", 100)):
            require(isinstance(spec[key], list) and 0 < len(spec[key]) <= maximum,
                    f"{key} must be a nonempty list with at most {maximum} entries")
        self.spec = spec
        self.metabolites = {}
        for m in spec["metabolites"]:
            fields(m, {"id", "carbons", "boundary"}, {"symmetric"})
            name = identifier(m["id"])
            require(name not in self.metabolites, f"Duplicate metabolite {name}")
            require(type(m["carbons"]) is int and 1 <= m["carbons"] <= 12,
                    f"{name}: carbon count must be 1..12")
            require(m["boundary"] in ("source", "internal", "sink"), f"{name}: invalid boundary")
            require(type(m.get("symmetric", False)) is bool, f"{name}: symmetric must be boolean")
            require(not m.get("symmetric") or m["boundary"] == "internal",
                    "Reversal symmetry is supported only for internal pools")
            self.metabolites[name] = m
        self.ids = []
        self.lower, self.upper, self.fixed = [], [], {}
        balance = {name: [] for name, m in self.metabolites.items() if m["boundary"] == "internal"}
        self.reactions = {}
        used = set()
        for i, r in enumerate(spec["reactions"]):
            fields(r, {"id", "substrates", "products", "lower", "upper"}, {"fixed"})
            rid = identifier(r["id"])
            require(rid not in self.ids, f"Duplicate reaction {rid}")
            self.ids.append(rid)
            lo, hi = number(r["lower"], rid), number(r["upper"], rid)
            require(0 <= lo < hi, f"{rid}: require 0 <= lower < upper; use fixed for fixed fluxes")
            self.lower.append(lo)
            self.upper.append(hi)
            if "fixed" in r:
                fixed = number(r["fixed"], rid)
                require(lo <= fixed <= hi, f"{rid}: fixed flux outside bounds")
                self.fixed[rid] = fixed
            names, labels = [], []
            for side in ("substrates", "products"):
                require(isinstance(r[side], list) and bool(r[side]), f"{rid}: empty {side}")
                side_names, side_labels = [], []
                for term in r[side]:
                    require(isinstance(term, list) and len(term) == 2, f"{rid}: expected [metabolite, atoms]")
                    metabolite, atoms = term
                    require(isinstance(metabolite, str) and metabolite in self.metabolites,
                            f"{rid}: unknown metabolite {metabolite!r}")
                    m = self.metabolites[metabolite]
                    require(isinstance(atoms, str) and re.fullmatch(r"[A-Za-z]+", atoms)
                            and len(atoms) == m["carbons"], f"{rid}: atom count mismatch for {metabolite}")
                    require(not (side == "substrates" and m["boundary"] == "sink"),
                            f"{rid}: a sink cannot be consumed")
                    require(not (side == "products" and m["boundary"] == "source"),
                            f"{rid}: a source cannot be produced")
                    side_names.append(metabolite)
                    side_labels.append(atoms)
                    used.add(metabolite)
                all_atoms = "".join(side_labels)
                unique(all_atoms, f"carbon atoms on {rid} {side}")
                names.append(side_names)
                labels.append(side_labels)
            require(set("".join(labels[0])) == set("".join(labels[1])),
                    f"{rid}: carbon atoms are lost or created; include CO2 and other carbon products")
            left, right = Counter(names[0]), Counter(names[1])
            for name in balance:
                balance[name].append(right[name] - left[name])

            def stoichiometry(parts):
                return "+".join((f"{{{count}}}" if count > 1 else "") + name
                                for name, count in Counter(parts).items())

            self.reactions[rid] = dict(
                order=i, stoichiometry="-->".join(stoichiometry(side) for side in names),
                reaction="-->".join("+".join(side) for side in names),
                atommap="-->".join("+".join(side) for side in labels),
                externalids="", lb=lo, ub=hi)
        require(used == self.metabolites.keys(), "Unused metabolites must be removed")
        require(bool(balance), "At least one internal metabolite is required")
        for name, row in balance.items():
            require(any(v > 0 for v in row) and any(v < 0 for v in row),
                    f"{name}: internal pool needs production and consumption")
        self.sources = {name for name, m in self.metabolites.items() if m["boundary"] == "source"}
        require(bool(self.sources), "At least one carbon source is required")
        # Catalytic cycles require an initial pool but can receive labeled carbon;
        # connectivity is checked on the undirected graph below, not reachability.
        connected = set(self.sources)
        for _ in self.metabolites:
            for r in spec["reactions"]:
                members = {term[0] for term in r["substrates"] + r["products"]}
                if members & connected:
                    connected.update(members)
        require(connected == self.metabolites.keys(), "Network contains a pool disconnected from all sources")
        self.balance = np.array(list(balance.values()), dtype=float)
        rows, rhs = list(self.balance), [0.] * len(self.balance)
        for rid, value in self.fixed.items():
            rows.append(np.eye(len(self.ids))[self.ids.index(rid)])
            rhs.append(value)
        self.equalities = np.array(rows)
        self.rhs = np.array(rhs)
        self.lower, self.upper = np.array(self.lower), np.array(self.upper)
        self.fragments = {}
        for f in spec["fragments"]:
            fields(f, {"id", "metabolite", "carbons", "provenance"})
            fid = identifier(f["id"])
            require(fid not in self.fragments, f"Duplicate fragment {fid}")
            require(isinstance(f["metabolite"], str) and f["metabolite"] in self.metabolites,
                    f"{fid}: unknown metabolite")
            m = self.metabolites[f["metabolite"]]
            require(m["boundary"] == "internal", f"{fid}: fragment must reference an internal pool")
            require(isinstance(f["carbons"], list) and bool(f["carbons"]), f"{fid}: empty carbon positions")
            require(all(type(c) is int and 1 <= c <= m["carbons"] for c in f["carbons"]),
                    f"{fid}: carbon positions are 1-based and must exist")
            unique(f["carbons"], f"positions in {fid}")
            require(isinstance(f["provenance"], str) and bool(f["provenance"].strip()),
                    f"{fid}: document the measured carbon assignment")
            self.fragments[fid] = f
        self._engine = None

    def check_flux(self, flux):
        require(isinstance(flux, dict) and set(flux) == set(self.ids), "Supply exactly one flux for every reaction")
        vector = np.array([number(flux[rid], rid) for rid in self.ids])
        require(self.feasible(vector), "Fluxes violate mass balance, fixed constraints, or bounds")
        return vector

    def feasible(self, vector, tolerance=1e-8):
        tolerance *= max(float(np.max(np.abs(vector))), float(np.max(np.abs(self.rhs))), 1e-300)
        return bool(np.all(np.isfinite(vector)) and np.all(vector >= self.lower - tolerance)
                    and np.all(vector <= self.upper + tolerance)
                    and np.max(np.abs(self.equalities @ vector - self.rhs)) <= tolerance)

    def engine(self):
        if self._engine is None:
            import mfapy
            metabolites = {
                name: dict(C_number=m["carbons"], order=i,
                           symmetry="symmetry" if m.get("symmetric") else "no",
                           carbonsource="carbonsource" if m["boundary"] == "source" else "no",
                           excreted="excreted" if m["boundary"] == "sink" else "no",
                           externalids="", lb=0., ub=1000.)
                for i, (name, m) in enumerate(self.metabolites.items())}
            fragments = {
                fid: dict(atommap=f["metabolite"] + "_" + ":".join(map(str, sorted(f["carbons"]))),
                          type="intermediate", formula="", use="use", order=i)
                for i, (fid, f) in enumerate(self.fragments.items())}
            # The upstream constructor prints diagnostics. Return clean JSON from the CLI.
            with contextlib.redirect_stdout(io.StringIO()):
                self._engine = mfapy.metabolicmodel.MetabolicModel(self.reactions, {}, metabolites, fragments)
            require(hasattr(self._engine, "func"), "mfapy could not construct this carbon network")
        return self._engine

    def predict(self, vector, experiment):
        engine = self.engine()
        # mfapy's generated steady-state solver drops rows with absolute turnover
        # <= 0.001. MIDs are invariant to uniform flux scaling: keep every positive
        # reaction at least 1 in the forward solver, without changing fitted units.
        vector = np.asarray(vector, dtype=float)
        require(np.all(np.isfinite(vector)) and np.min(vector) >= 0,
                "Isotope simulation requires finite nonnegative directional fluxes")
        positive = vector[vector > 0]
        require(len(positive) > 0, "Isotope steady state is undefined with all fluxes zero")
        forward = vector / positive.min()
        cs = engine.generate_carbon_source_template()
        for name, distribution in experiment["substrates"].items():
            # Direct arrays avoid upstream set_each_isotopomer's exact sum > 1 check.
            values = [0.] * (2 ** self.metabolites[name]["carbons"])
            for bits, fraction in distribution.items():
                values[int(bits[::-1], 2)] = fraction
            require(cs.set_all_isotopomers(name, values, correction="no"), f"Invalid source {name}")
        state = {"reaction": {rid: {"value": value} for rid, value in zip(self.ids, forward)},
                 "metabolite": {name: {"value": 1.} for name in self.metabolites}, "reversible": {}}
        with np.errstate(all="raise"):
            mdv = engine.generate_mdv(state, cs)
        result = {}
        for fid, f in self.fragments.items():
            values = np.asarray(mdv.get_fragment_mdv(fid), dtype=float)
            require(len(values) == len(f["carbons"]) + 1 and np.all(np.isfinite(values))
                    and np.min(values) >= -1e-8 and np.max(values) <= 1 + 1e-8
                    and abs(values.sum() - 1) < 1e-6,
                    f"Invalid simulated MDV for {fid}; check zero-throughput pools and mapping")
            result[fid] = values
        return result


class Observations:
    def __init__(self, spec, network):
        fields(spec, {"schema_version", "steady_state", "shared_fluxes", "mdv_basis",
                      "correction_notes", "experiments"})
        require(type(spec["schema_version"]) is int and spec["schema_version"] == 1, "Unsupported schema")
        require(spec["steady_state"] == {"metabolic": True, "isotopic": True}
                and all(type(v) is bool for v in spec["steady_state"].values()),
                "This solver requires metabolic AND isotopic steady state; use an INST-MFA engine for time courses")
        require(spec["shared_fluxes"] is True, "Experiments in a joint fit must share the same flux state")
        require(spec["mdv_basis"] == "tracer_only", "Correct natural abundance externally; raw MDVs are not accepted")
        require(isinstance(spec["correction_notes"], str) and bool(spec["correction_notes"].strip()),
                "Record the correction method and how tracer purity was handled")
        require(isinstance(spec["experiments"], list) and bool(spec["experiments"]), "No experiments")
        self.spec, self.network, self.blocks, self.flux_blocks = spec, network, [], []
        self.warnings = []
        ids = []
        for exp in spec["experiments"]:
            fields(exp, {"id", "substrates", "measurements"}, {"flux_measurements"})
            ids.append(identifier(exp["id"]))
            require(isinstance(exp["substrates"], dict) and set(exp["substrates"]) == network.sources,
                    "Every experiment must explicitly describe every source, including unlabeled inputs")
            for name, distribution in exp["substrates"].items():
                require(isinstance(distribution, dict) and bool(distribution), f"{name}: missing isotopomers")
                total = 0.
                for bits, fraction in distribution.items():
                    require(isinstance(bits, str) and re.fullmatch(r"[01]+", bits)
                            and len(bits) == network.metabolites[name]["carbons"], f"{name}: invalid positional isotopomer")
                    total += number(fraction, name)
                    require(fraction >= 0, f"{name}: negative fraction")
                require(abs(total - 1) < 1e-10, f"{name}: isotopomer fractions must sum to one; no implicit unlabeled remainder")
            require(isinstance(exp["measurements"], list), "measurements must be a list")
            seen = []
            for obs in exp["measurements"]:
                fields(obs, {"fragment", "mdv", "omit"}, {"sem", "covariance"})
                fid = obs["fragment"]
                require(isinstance(fid, str) and fid in network.fragments, f"Unknown fragment {fid!r}")
                seen.append(fid)
                n = len(network.fragments[fid]["carbons"]) + 1
                require(isinstance(obs["mdv"], list) and len(obs["mdv"]) == n, f"{fid}: expected M+0 through M+{n-1}")
                y = np.array([number(v, fid) for v in obs["mdv"]])
                require(np.all(y >= 0) and np.all(y <= 1) and abs(y.sum() - 1) < 1e-6,
                        f"{fid}: MDV must be nonnegative and sum to one; do not silently clip or renormalize")
                omit = obs["omit"]
                require(type(omit) is int and 0 <= omit < n, f"{fid}: invalid omitted bin")
                keep = np.array([i for i in range(n) if i != omit])
                require(("sem" in obs) != ("covariance" in obs), f"{fid}: supply exactly one of sem or covariance")
                if "covariance" in obs:
                    cov = np.asarray(obs["covariance"], dtype=float)
                    require(cov.shape == (n, n) and np.all(np.isfinite(cov)), f"{fid}: invalid covariance shape/values")
                    require(np.all(np.diag(cov) > 0), f"{fid}: covariance of retained bins must be positive definite")
                    std = np.sqrt(np.diag(cov))
                    correlation = cov / np.outer(std, std)
                    require(np.max(np.abs(correlation - correlation.T)) <= 1e-10
                            and np.all(np.abs(cov.sum(axis=0)) <= np.sum(np.abs(cov), axis=0) * 1e-10)
                            and np.all(np.abs(cov.sum(axis=1)) <= np.sum(np.abs(cov), axis=1) * 1e-10),
                            f"{fid}: full MDV covariance must be symmetric with zero row/column sums")
                    require(np.linalg.eigvalsh(correlation).min() >= -1e-10,
                            f"{fid}: full MDV covariance must be positive semidefinite")
                    reduced = cov[np.ix_(keep, keep)]
                else:
                    require(isinstance(obs["sem"], list) and len(obs["sem"]) == n, f"{fid}: invalid sem length")
                    sem = np.array([number(v, fid) for v in obs["sem"]])
                    require(np.all(sem > 0), f"{fid}: sem values must be positive")
                    reduced = np.diag(sem[keep] ** 2)
                    self.warnings.append(f"{exp['id']}/{fid}: diagonal SEM approximation; correlations ignored, intervals and goodness-of-fit approximate")
                uncertainty = float(np.sqrt(np.diag(reduced)).min())
                require(abs(y.sum() - 1) <= min(1e-10, uncertainty * 1e-5),
                        f"{fid}: MDV normalization error exceeds numerical/error-scale tolerance; revisit upstream normalization")
                try:
                    chol = cholesky(reduced, lower=True)
                except np.linalg.LinAlgError as exc:
                    raise InputError(f"{fid}: covariance of retained bins must be positive definite") from exc
                self.blocks.append((exp, fid, y, keep, chol))
            unique(seen, f"fragment measurements in {exp['id']}; combine replicates with an explicit error model")
            flux_obs = exp.get("flux_measurements", [])
            require(isinstance(flux_obs, list), "flux_measurements must be a list")
            flux_ids = []
            for obs in flux_obs:
                fields(obs, {"reaction", "value", "sem"})
                require(obs["reaction"] in network.ids, "Unknown measured reaction")
                require(number(obs["sem"], "flux sem") > 0, "Flux sem must be positive")
                number(obs["value"], "measured flux")
                flux_ids.append(obs["reaction"])
                self.flux_blocks.append((exp["id"], network.ids.index(obs["reaction"]), obs))
            unique(flux_ids, f"flux measurements in {exp['id']}")
        unique(ids, "experiment IDs")
        self.size = sum(len(block[3]) for block in self.blocks) + len(self.flux_blocks)

    def residuals(self, vector, details=False):
        predictions = {exp["id"]: self.network.predict(vector, exp) for exp in self.spec["experiments"]}
        residuals, records = [], []
        for exp, fid, observed, keep, chol in self.blocks:
            predicted = predictions[exp["id"]][fid]
            white = solve_triangular(chol, (predicted - observed)[keep], lower=True)
            residuals.extend(white)
            records.append(dict(experiment=exp["id"], fragment=fid, observed=observed.tolist(),
                                predicted=predicted.tolist(), retained_bins=keep.tolist(),
                                whitened_residuals=white.tolist()))
        for exp_id, index, obs in self.flux_blocks:
            value = (vector[index] - obs["value"]) / obs["sem"]
            residuals.append(value)
            records.append(dict(experiment=exp_id, reaction=obs["reaction"], observed=obs["value"],
                                predicted=float(vector[index]), standardized_residual=float(value)))
        return (np.array(residuals), records) if details else np.array(residuals)
