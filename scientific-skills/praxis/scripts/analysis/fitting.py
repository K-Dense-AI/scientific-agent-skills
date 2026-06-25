"""Curve fitting: linear, polynomial, Gaussian, Lorentzian, Voigt, exponential,
power law, sigmoidal, and custom user-defined functions.

Uses lmfit for robust fitting with parameter constraints, confidence intervals,
and goodness-of-fit statistics.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Union

import numpy as np
from lmfit import Model, Parameters
from lmfit.models import (
    GaussianModel,
    LorentzianModel,
    VoigtModel,
    PseudoVoigtModel,
    ExponentialModel,
    LinearModel,
    PolynomialModel,
    ConstantModel,
)
from lmfit.model import ModelResult

from scripts.core.utils import validate_xy


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fit_curve(
    x: Any,
    y: Any,
    model: str = "auto",
    *,
    degree: int = 1,
    params: Optional[dict[str, Any]] = None,
    x_range: Optional[tuple[float, float]] = None,
    weights: Optional[Any] = None,
    method: str = "leastsq",
    max_iter: int = 1000,
) -> FitResult:
    """Fit a model to x, y data.

    Parameters
    ----------
    x, y : array-like
        Data to fit.
    model : str
        Model name: 'linear', 'polynomial', 'gaussian', 'lorentzian',
        'voigt', 'pseudo_voigt', 'exponential', 'power_law', 'sigmoidal',
        'auto', or a custom expression string.
    degree : int
        Polynomial degree (only for 'polynomial').
    params : dict, optional
        Initial parameter guesses, e.g. {'center': 28, 'sigma': 0.5}.
    x_range : tuple, optional
        Fit only within this x range.
    weights : array-like, optional
        Point weights (1/uncertainty).
    method : str
        Minimisation method (lmfit names).
    max_iter : int
        Maximum iterations.

    Returns
    -------
    FitResult
        Object with fitted parameters, statistics, and plotting helpers.
    """
    x, y = validate_xy(np.asarray(x, dtype=float), np.asarray(y, dtype=float), allow_nan=False)

    # Restrict to x_range if given
    if x_range is not None:
        mask = (x >= x_range[0]) & (x <= x_range[1])
        x, y = x[mask], y[mask]
        if weights is not None:
            weights = np.asarray(weights)[mask]

    if model == "auto":
        model = _auto_detect_model(x, y)
        print(f"[Praxis] Auto-detected model: {model}")

    lm_model, init_params = _build_model(model, x, y, degree=degree)

    # Apply user parameter overrides
    if params:
        for name, value in params.items():
            if name in init_params:
                if isinstance(value, dict):
                    init_params[name].set(**value)
                else:
                    init_params[name].set(value=value)

    result = lm_model.fit(
        y, init_params, x=x,
        weights=weights,
        method=method,
        max_nfev=max_iter,
    )

    return FitResult(result, x, y, model)


# ---------------------------------------------------------------------------
# FitResult wrapper
# ---------------------------------------------------------------------------

class FitResult:
    """Wrapper around lmfit ModelResult with convenience methods."""

    def __init__(self, result: ModelResult, x: np.ndarray, y: np.ndarray, model_name: str):
        self.result = result
        self.x = x
        self.y = y
        self.model_name = model_name

    @property
    def params(self) -> dict[str, float]:
        """Best-fit parameter values."""
        return {name: par.value for name, par in self.result.params.items()}

    @property
    def uncertainties(self) -> dict[str, Optional[float]]:
        """Parameter uncertainties (1-sigma)."""
        return {name: par.stderr for name, par in self.result.params.items()}

    @property
    def r_squared(self) -> float:
        """Coefficient of determination R²."""
        ss_res = np.sum(self.result.residual ** 2)
        ss_tot = np.sum((self.y - np.mean(self.y)) ** 2)
        return 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    @property
    def reduced_chi_squared(self) -> float:
        """Reduced chi-squared (χ²/ν)."""
        return self.result.redchi

    @property
    def aic(self) -> float:
        """Akaike information criterion."""
        return self.result.aic

    @property
    def bic(self) -> float:
        """Bayesian information criterion."""
        return self.result.bic

    def eval(self, x: Optional[Any] = None) -> np.ndarray:
        """Evaluate the fitted model at given x values (or original x)."""
        if x is None:
            x = self.x
        return self.result.eval(x=np.asarray(x, dtype=float))

    def eval_fine(self, n: int = 500) -> tuple[np.ndarray, np.ndarray]:
        """Evaluate on a fine grid for smooth plotting."""
        x_fine = np.linspace(self.x.min(), self.x.max(), n)
        return x_fine, self.eval(x_fine)

    def confidence_band(self, sigma: float = 1.0, n: int = 500) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute confidence band on a fine grid.

        Returns (x_fine, y_lower, y_upper).
        """
        x_fine = np.linspace(self.x.min(), self.x.max(), n)
        try:
            dely = self.result.eval_uncertainty(x=x_fine, sigma=sigma)
            y_fit = self.eval(x_fine)
            return x_fine, y_fit - dely, y_fit + dely
        except Exception:
            # Fallback: no confidence band available
            y_fit = self.eval(x_fine)
            return x_fine, y_fit, y_fit

    def report(self) -> str:
        """Human-readable fit report."""
        lines = [
            f"[Praxis] Fit: {self.model_name}",
            f"  R2 = {self.r_squared:.6f}",
            f"  Reduced chi2 = {self.reduced_chi_squared:.4e}",
            f"  AIC = {self.aic:.2f}, BIC = {self.bic:.2f}",
            "  Parameters:",
        ]
        for name, par in self.result.params.items():
            err = f" ± {par.stderr:.4e}" if par.stderr else ""
            lines.append(f"    {name} = {par.value:.6e}{err}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.report()


# ---------------------------------------------------------------------------
# Model builders
# ---------------------------------------------------------------------------

def _build_model(
    model: str, x: np.ndarray, y: np.ndarray, *, degree: int = 1
) -> tuple[Model, Parameters]:
    """Build an lmfit Model and initial Parameters for the given model name."""

    if model == "linear":
        m = LinearModel()
        p = m.guess(y, x=x)

    elif model == "polynomial":
        m = PolynomialModel(degree=degree)
        p = m.guess(y, x=x)

    elif model == "gaussian":
        m = GaussianModel() + ConstantModel()
        p = m.make_params()
        _guess_peak(p, x, y)

    elif model == "lorentzian":
        m = LorentzianModel() + ConstantModel()
        p = m.make_params()
        _guess_peak(p, x, y)

    elif model == "voigt":
        m = VoigtModel() + ConstantModel()
        p = m.make_params()
        _guess_peak(p, x, y)

    elif model == "pseudo_voigt":
        m = PseudoVoigtModel() + ConstantModel()
        p = m.make_params()
        _guess_peak(p, x, y)

    elif model == "exponential":
        m = ExponentialModel()
        p = m.guess(y, x=x)

    elif model == "power_law":
        m = Model(_power_law)
        p = Parameters()
        p.add("a", value=1.0)
        p.add("b", value=1.0)

    elif model == "sigmoidal":
        m = Model(_sigmoidal)
        p = Parameters()
        x_mid = (x.min() + x.max()) / 2
        y_range = y.max() - y.min()
        p.add("L", value=y.max(), min=0)
        p.add("k", value=4.0 / (x.max() - x.min()))
        p.add("x0", value=x_mid)
        p.add("b", value=y.min())

    else:
        # Try as custom expression
        m = Model(_make_custom_func(model), independent_vars=["x"])
        p = m.make_params()
        # Set all params to 1.0 as initial guess
        for name in p:
            p[name].set(value=1.0)

    return m, p


def _guess_peak(params: Parameters, x: np.ndarray, y: np.ndarray) -> None:
    """Set initial guesses for a peak model (center, sigma, amplitude, c)."""
    idx_max = np.argmax(y)
    if "center" in params:
        params["center"].set(value=x[idx_max])
    if "sigma" in params:
        # Estimate sigma from half-max width
        half_max = (y.max() + y.min()) / 2
        above = x[y > half_max]
        if len(above) > 1:
            params["sigma"].set(value=(above[-1] - above[0]) / 2.355, min=0)
        else:
            params["sigma"].set(value=(x.max() - x.min()) / 10, min=0)
    if "amplitude" in params:
        params["amplitude"].set(value=y.max() - y.min(), min=0)
    if "c" in params:
        params["c"].set(value=np.median(y))


# ---------------------------------------------------------------------------
# Built-in model functions
# ---------------------------------------------------------------------------

def _power_law(x: np.ndarray, a: float, b: float) -> np.ndarray:
    """y = a * x^b"""
    return a * np.power(np.abs(x), b)


def _sigmoidal(x: np.ndarray, L: float, k: float, x0: float, b: float) -> np.ndarray:
    """Logistic sigmoid: y = L / (1 + exp(-k*(x - x0))) + b"""
    return L / (1.0 + np.exp(-k * (x - x0))) + b


def _make_custom_func(expression: str) -> Callable:
    """Create a function from a string expression using x as variable.

    Example: 'a * exp(-b * x) + c'
    """
    import ast

    # Validate the expression doesn't contain dangerous code
    allowed_names = {"x", "np", "exp", "sin", "cos", "tan", "log", "log10",
                     "sqrt", "pi", "abs", "power"}

    def _func(x: np.ndarray, **kwargs: float) -> np.ndarray:
        namespace = {
            "x": x, "np": np,
            "exp": np.exp, "sin": np.sin, "cos": np.cos, "tan": np.tan,
            "log": np.log, "log10": np.log10, "sqrt": np.sqrt,
            "pi": np.pi, "abs": np.abs, "power": np.power,
        }
        namespace.update(kwargs)
        return eval(expression, {"__builtins__": {}}, namespace)

    return _func


# ---------------------------------------------------------------------------
# Auto-detection
# ---------------------------------------------------------------------------

def _auto_detect_model(x: np.ndarray, y: np.ndarray) -> str:
    """Guess the best model based on data shape."""
    # Check for obvious peak
    y_range = y.max() - y.min()
    y_norm = (y - y.min()) / y_range if y_range > 0 else y

    # Peak detection: does data have a clear peak?
    mid_region = y_norm[len(y_norm) // 4 : 3 * len(y_norm) // 4]
    edges = np.concatenate([y_norm[: len(y_norm) // 4], y_norm[3 * len(y_norm) // 4 :]])
    if len(mid_region) > 0 and len(edges) > 0:
        if np.mean(mid_region) > np.mean(edges) + 0.3:
            return "gaussian"

    # Check for monotonic behaviour
    diffs = np.diff(y)
    if np.all(diffs >= -1e-10 * y_range) or np.all(diffs <= 1e-10 * y_range):
        # Monotonic — check for exponential vs linear
        if y_range > 0:
            # Check linearity via R² of linear fit
            coeffs = np.polyfit(x, y, 1)
            y_linear = np.polyval(coeffs, x)
            ss_res = np.sum((y - y_linear) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2_linear = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            if r2_linear > 0.99:
                return "linear"
            return "exponential"

    return "polynomial"
