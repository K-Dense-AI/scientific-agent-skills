"""Constrained multistart fitting and nuisance-reoptimized flux profiles."""
from __future__ import annotations

import numpy as np
from scipy.linalg import null_space
from scipy.optimize import Bounds, LinearConstraint, linprog, minimize
from scipy.stats import chi2

from _mfa_model import InputError, require


def fixed_range(low, high):
    """Compare a feasible range to its own magnitude, independent of flux units."""
    return high - low <= 1e-10 * max(abs(low), abs(high), np.finfo(float).tiny)


class FluxSpace:
    def __init__(self, network, fixed=None):
        self.network = network
        self.a = network.equalities.copy()
        self.b = network.rhs.copy()
        if fixed:
            for rid, value in fixed.items():
                row = np.eye(len(network.ids))[network.ids.index(rid)]
                self.a = np.vstack((self.a, row))
                self.b = np.append(self.b, value)
        anchors = np.abs(self.b[self.b != 0])
        self.scale = float(np.median(anchors)) if len(anchors) else float(np.median(network.upper))
        self.bounds = list(zip(network.lower / self.scale, network.upper / self.scale))
        feasible = self.linear(np.zeros(len(network.ids)))
        require(feasible.success, "Flux constraints are infeasible")
        # A profile endpoint can collapse a face of the feasible polytope.
        # Promote bounds that fix a reaction throughout this face to equalities.
        initial_basis = null_space(self.a)
        for i in range(len(network.ids)):
            if np.linalg.norm(initial_basis[i]) < 1e-10:
                continue
            axis = np.eye(len(network.ids))[i]
            low, high = self.linear(axis), self.linear(-axis)
            require(low.success and high.success, "Cannot determine feasible flux ranges")
            if fixed_range(low.x[i], high.x[i]):
                self.a = np.vstack((self.a, axis))
                self.b = np.append(self.b, (high.x[i] + low.x[i]) / 2)
        feasible = self.linear(np.zeros(len(network.ids)))
        require(feasible.success, "Flux constraints are infeasible after reducing fixed ranges")
        self.base = feasible.x
        self.basis = null_space(self.a) * self.scale
        self.dimension = self.basis.shape[1]

    def linear(self, objective):
        result = linprog(objective, A_eq=self.a, b_eq=self.b / self.scale, bounds=self.bounds,
                         method="highs", options={"time_limit": 10., "primal_feasibility_tolerance": 1e-9,
                                                   "dual_feasibility_tolerance": 1e-9})
        if result.success:
            result.x = result.x * self.scale
            if not self.feasible(result.x):
                result.success = False
                result.message = "LP returned a vector that fails explicit feasibility checks"
        return result

    def coordinates(self, flux):
        return self.basis.T @ (flux - self.base) / self.scale ** 2

    def flux(self, coordinates):
        return self.base + self.basis @ coordinates

    def feasible(self, flux):
        scale = max(float(np.max(np.abs(flux))), float(np.max(np.abs(self.b))), 1e-300)
        return self.network.feasible(flux) and np.max(np.abs(self.a @ flux - self.b)) < 1e-8 * scale

    def starting_points(self, count, rng, warm=None):
        if not self.dimension:
            return [self.base]
        vertices = [self.base]
        for _ in range(max(12, 3 * self.dimension)):
            result = self.linear(rng.normal(size=len(self.base)))
            if result.success:
                vertices.append(result.x)
        vertices = np.array(vertices)
        center = vertices.mean(axis=0)
        starts = [center]
        if warm is not None:
            projected = self.flux(self.coordinates(warm))
            if self.feasible(projected):
                starts[0] = projected
        for _ in range(count - 1):
            weights = rng.dirichlet(np.ones(len(vertices)) * .3)
            starts.append(.05 * center + .95 * weights @ vertices)
        return starts


def fit(observations, starts=8, seed=2026, maxiter=1000, fixed=None, warm=None):
    require(type(starts) is int and 1 <= starts <= 100, "starts must be 1..100")
    require(type(maxiter) is int and 1 <= maxiter <= 10000, "maxiter must be 1..10000")
    require(observations.size > 0, "Fitting needs measurements")
    network = observations.network
    space = FluxSpace(network, fixed)
    rng = np.random.default_rng(seed)
    records, solutions = [], []
    numerical_errors = (InputError, np.linalg.LinAlgError, FloatingPointError, ZeroDivisionError)

    def rss(flux):
        residual = observations.residuals(flux)
        value = float(residual @ residual)
        require(np.isfinite(value), "Nonfinite objective")
        return value

    if not space.dimension:
        value = rss(space.base)
        return dict(vector=space.base, rss=value, space=space,
                    starts=[dict(success=True, rss=value, message="All fluxes fixed by constraints")])
    varying = np.linalg.norm(space.basis / space.scale, axis=1) > 1e-10
    linear = LinearConstraint(space.basis[varying] / space.scale,
                              (network.lower - space.base)[varying] / space.scale,
                              (network.upper - space.base)[varying] / space.scale)
    # Loose finite coordinate bounds limit excursions while the linear constraint
    # enforces all actual reaction bounds. They cannot exclude a feasible vector.
    radius = np.linalg.norm(network.upper - network.lower) / space.scale + 1
    for initial in space.starting_points(starts, rng, warm):
        try:
            scale = max(1., rss(initial))

            def objective(z):
                try:
                    return rss(space.flux(z)) / scale
                except numerical_errors:
                    return 1e20

            result = minimize(objective, space.coordinates(initial), method="SLSQP",
                              bounds=Bounds(-radius, radius), constraints=[linear],
                              options={"maxiter": maxiter, "ftol": 1e-12})
            vector = space.flux(result.x)
            value = rss(vector)
            success = bool(result.success and space.feasible(vector) and np.isfinite(value))
            records.append(dict(success=success, rss=value, message=str(result.message),
                                iterations=int(result.nit)))
            if success:
                solutions.append((value, vector))
        except numerical_errors as exc:
            records.append(dict(success=False, rss=None, message=str(exc)))
    require(bool(solutions), "No converged feasible fit; check flux bounds, zero-throughput pools, and starting conditions")
    value, vector = min(solutions, key=lambda item: item[0])
    return dict(vector=vector, rss=value, space=space, starts=records)


def diagnostics(observations, fitted):
    network, vector, space = observations.network, fitted["vector"], fitted["space"]
    residual, predictions = observations.residuals(vector, details=True)
    columns = []
    z = space.coordinates(vector)
    for i in range(space.dimension):
        step = np.eye(space.dimension)[i] * 1e-5
        plus, minus = space.flux(z + step), space.flux(z - step)
        if space.feasible(plus) and space.feasible(minus):
            columns.append((observations.residuals(plus) - observations.residuals(minus)) / 2e-5)
        elif space.feasible(plus):
            columns.append((observations.residuals(plus) - residual) / 1e-5)
        elif space.feasible(minus):
            columns.append((residual - observations.residuals(minus)) / 1e-5)
        else:
            columns = None
            break
    rank, singular, null_directions = None, [], []
    if columns is not None:
        jacobian = np.column_stack(columns) if columns else np.empty((observations.size, 0))
        _, values, vh = np.linalg.svd(jacobian, full_matrices=True)
        threshold = max(1e-4, (float(values[0]) if len(values) else 0.) * 1e-6)
        rank = int(np.sum(values > threshold))
        singular = values.tolist()
        for direction in vh[rank:]:
            flux_direction = space.basis @ direction
            flux_direction /= np.max(np.abs(flux_direction))
            null_directions.append({rid: float(v) for rid, v in zip(network.ids, flux_direction)
                                    if abs(v) > 1e-5})
    active = [rid for i, rid in enumerate(network.ids) if rid not in network.fixed and
              (abs(vector[i] - network.lower[i]) < 1e-6 * space.scale or
               abs(vector[i] - network.upper[i]) < 1e-6 * space.scale)]
    dof = observations.size - space.dimension
    regular = rank == space.dimension and dof > 0 and not active
    warnings = list(observations.warnings)
    if rank is None:
        warnings.append("Sensitivity rank could not be evaluated along feasible directions; inspect profiles")
    elif rank < space.dimension:
        warnings.append("Locally rank-deficient fit: some flux combinations are not constrained by these measurements")
    if active:
        warnings.append("Active flux bounds invalidate ordinary interior asymptotic confidence claims")
    if any(not record["success"] for record in fitted["starts"]):
        warnings.append("Some optimizer starts failed; inspect start records and repeat with more starts")
    return dict(
        fluxes={rid: float(v) for rid, v in zip(network.ids, vector)}, flux_unit=network.spec["flux_unit"],
        rss=fitted["rss"], independent_measurements=observations.size,
        free_flux_dimensions=space.dimension, local_sensitivity_rank=rank,
        sensitivity_singular_values=singular, weak_flux_directions=null_directions,
        active_bounds=active, max_mass_balance_error=float(np.max(np.abs(network.balance @ vector))),
        goodness_of_fit=dict(degrees_of_freedom=dof,
                             approximate_p_value=float(chi2.sf(fitted["rss"], dof)) if regular else None,
                             interpretation="Asymptotic Gaussian diagnostic; not evidence that the biological model is correct"
                             if regular else "Not reported: rank, bounds, or degrees of freedom violate regular assumptions"),
        predictions=predictions, optimizer_starts=fitted["starts"], warnings=warnings)


def profile(observations, fitted, reaction, points=21, starts=4, seed=2026,
            maxiter=1000, confidence=.95):
    network, space = observations.network, fitted["space"]
    require(reaction in network.ids, f"Unknown profile reaction {reaction}")
    require(type(points) is int and 5 <= points <= 201, "profile points must be 5..201")
    require(0 < confidence < 1, "confidence must be between zero and one")
    index = network.ids.index(reaction)
    objective = np.eye(len(network.ids))[index]
    lower = space.linear(objective)
    upper = space.linear(-objective)
    require(lower.success and upper.success, "Cannot compute feasible profile range")
    lo, hi = float(lower.x[index]), float(upper.x[index])
    if fixed_range(lo, hi):
        return dict(reaction=reaction, status="fixed_by_constraints", feasible_range=[lo, hi], points=[])
    grid = np.unique(np.append(np.linspace(lo, hi, points), fitted["vector"][index]))
    records = []
    cutoff = float(chi2.ppf(confidence, 1))
    for i, value in enumerate(grid):
        try:
            result = fit(observations, starts=starts, seed=seed + i, maxiter=maxiter,
                         fixed={reaction: float(value)}, warm=fitted["vector"])
            delta = result["rss"] - fitted["rss"]
            records.append(dict(flux=float(value), rss=result["rss"], delta_rss=float(delta),
                                accepted=bool(delta <= cutoff), converged=True,
                                failed_starts=sum(not start["success"] for start in result["starts"])))
        except (InputError, np.linalg.LinAlgError, FloatingPointError) as exc:
            records.append(dict(flux=float(value), rss=None, delta_rss=None,
                                accepted=None, converged=False, error=str(exc)))
    valid = [r for r in records if r["converged"]]
    better = any(r["delta_rss"] < -max(1e-5, abs(fitted["rss"]) * 1e-5) for r in valid)
    failed = any(not r["converged"] for r in records)
    all_accepted = len(valid) == len(records) and all(r["accepted"] for r in valid)
    crossings = []
    for left, right in zip(records, records[1:]):
        if left["converged"] and right["converged"] and left["accepted"] != right["accepted"]:
            crossings.append([left["flux"], right["flux"]])
    if better:
        status = "baseline_not_optimal_refit_required"
    elif failed:
        status = "incomplete_profile"
    elif all_accepted:
        status = "unresolved_within_bounds"
    elif records[0]["accepted"] or records[-1]["accepted"]:
        status = "bound_limited"
    else:
        status = "threshold_crossings_bracketed"
    return dict(reaction=reaction, status=status, feasible_range=[lo, hi],
                confidence=confidence, delta_rss_cutoff=cutoff,
                threshold_crossing_brackets=crossings,
                lower_bound_accepted=records[0]["accepted"], upper_bound_accepted=records[-1]["accepted"],
                note="Grid profile with nuisance fluxes reoptimized. Crossings are brackets, not exact confidence limits. "
                     "Chi-square threshold is asymptotic and requires a suitable error model and regularity; "
                     "a flat finite profile is not proof of global structural non-identifiability.", points=records)
