"""Post-processing helpers for a params.npz written by runner.py.

Verified against openpiv 0.26.1. Pure numpy -- no OpenPIV import needed here.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np


class PIVAnalyzer:
    """Derived quantities from a saved PIV velocity field.

    The fields in params.npz are already scaled to physical units by runner.py, so
    x and y are in the same unit as the scaling factor and u and v are that unit per
    second. Gradient methods infer spacing and orientation from saved coordinates.
    Derivatives use interpolated fluid vectors; permanently masked regions stay NaN.
    """

    def __init__(self, params_file: str):
        self.params_file = Path(params_file)

        with np.load(self.params_file, allow_pickle=False) as data:
            self.x = data["x"]
            self.y = data["y"]
            self.u = data["u"]
            self.v = data["v"]
            self.flags = data["flags"].astype(bool)
            self.mask = data["mask"].astype(bool) if "mask" in data else np.zeros_like(self.flags)
        self.u = np.where(self.mask, np.nan, self.u)
        self.v = np.where(self.mask, np.nan, self.v)

    @property
    def grid_spacing(self) -> Tuple[float, float]:
        """(dx, dy) inferred from the coordinate arrays, in physical units."""
        dx = float(np.abs(np.diff(self.x, axis=1)).mean()) if self.x.shape[1] > 1 else 1.0
        dy = float(np.abs(np.diff(self.y, axis=0)).mean()) if self.y.shape[0] > 1 else 1.0
        return dx, dy

    @property
    def axis_signs(self) -> Tuple[float, float]:
        """(+-1, +-1): whether x and y increase or decrease along the array axes.

        runner.py converts to a physical right-handed (y-up) frame while leaving rows in
        image order -- so physical y *decreases* as the row index grows. np.gradient
        only sees the array, so differentiating with a positive spacing would return
        -du/dy there and change the vorticity and shear-strain contributions.
        These signs put the derivatives back on the physical axes.
        """
        x_sign = -1.0 if self.x.shape[1] > 1 and self.x[0, 1] < self.x[0, 0] else 1.0
        y_sign = -1.0 if self.y.shape[0] > 1 and self.y[1, 0] < self.y[0, 0] else 1.0
        return x_sign, y_sign

    def _steps(
        self, dx: Optional[float], dy: Optional[float]
    ) -> Tuple[float, float, float, float]:
        """(dx, dy, x_sign, y_sign) for a gradient call, defaulting to the grid."""
        gx, gy = self.grid_spacing
        x_sign, y_sign = self.axis_signs
        return (
            gx if dx is None else abs(float(dx)),
            gy if dy is None else abs(float(dy)),
            x_sign,
            y_sign,
        )

    def plot_vector_field(
        self,
        scale: int = 50,
        width: float = 0.0035,
        save_path: Optional[str] = None,
    ):
        """Quiver plot of the valid vectors. Saves to save_path, or shows interactively."""
        import matplotlib.pyplot as plt

        valid = ~(self.flags | self.mask) & np.isfinite(self.u) & np.isfinite(self.v)
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.quiver(
            self.x[valid],
            self.y[valid],
            self.u[valid],
            self.v[valid],
            scale=scale,
            width=width,
        )
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_title("Velocity Field")
        ax.set_aspect("equal")
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
        else:
            plt.show()
        return fig

    def get_velocity_magnitude(self) -> np.ndarray:
        return np.sqrt(self.u**2 + self.v**2)

    def compute_vorticity(
        self, dx: Optional[float] = None, dy: Optional[float] = None
    ) -> np.ndarray:
        """Out-of-plane vorticity, dv/dx - du/dy. Defaults to the inferred grid spacing.

        dx and dy are spacing magnitudes; the axis orientation comes from the saved
        coordinates (see axis_signs), so a counter-clockwise flow gives positive
        vorticity whichever way the rows run.
        """
        dx, dy, x_sign, y_sign = self._steps(dx, dy)
        dv_dx = x_sign * np.gradient(self.v, dx, axis=1)
        du_dy = y_sign * np.gradient(self.u, dy, axis=0)
        return dv_dx - du_dy

    def compute_strain(
        self, dx: Optional[float] = None, dy: Optional[float] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return (exx, eyy, exy) of the 2D strain-rate tensor."""
        dx, dy, x_sign, y_sign = self._steps(dx, dy)
        du_dx = x_sign * np.gradient(self.u, dx, axis=1)
        du_dy = y_sign * np.gradient(self.u, dy, axis=0)
        dv_dx = x_sign * np.gradient(self.v, dx, axis=1)
        dv_dy = y_sign * np.gradient(self.v, dy, axis=0)
        return du_dx, dv_dy, 0.5 * (du_dy + dv_dx)

    def compute_statistics(self, include_interpolated: bool = False) -> Dict[str, float]:
        """Spatial mean and RMS over this single frame.

        This is NOT Reynolds decomposition: subtracting one frame's spatial mean
        measures spatial variance, which equals turbulent intensity only for a
        homogeneous field. True turbulence statistics need an ensemble of pairs --
        average over the time axis, then subtract that mean field from each frame.
        By default exclude flagged/interpolated vectors and masked obstacles.
        The legacy key 'tke' is only two-component spatial variance energy, not
        three-component turbulent kinetic energy.
        """
        valid = ~self.mask & np.isfinite(self.u) & np.isfinite(self.v)
        if not include_interpolated:
            valid &= ~self.flags
        if not valid.any():
            raise ValueError("No valid fluid vectors remain for statistics")
        u, v = self.u[valid], self.v[valid]
        u_prime = u - np.mean(u)
        v_prime = v - np.mean(v)
        rms_u = float(np.nanstd(u_prime))
        rms_v = float(np.nanstd(v_prime))
        return {
            "u_mean": float(np.mean(u)),
            "v_mean": float(np.mean(v)),
            "rms_u": rms_u,
            "rms_v": rms_v,
            "tke": 0.5 * (rms_u**2 + rms_v**2),
        }
