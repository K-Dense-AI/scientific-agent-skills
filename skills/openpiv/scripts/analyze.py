"""Post-processing helpers for a params.npz written by runner.py.

Verified against openpiv 0.25.4. Pure numpy -- no OpenPIV import needed here.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np


class PIVAnalyzer:
    """Derived quantities from a saved PIV velocity field.

    The fields in params.npz are already scaled to physical units by runner.py, so
    x and y are in the same unit as the scaling factor and u and v are that unit per
    second. Pass the matching grid spacing to the gradient methods -- the default
    dx=1.0 yields per-grid-cell derivatives, not per-unit-length ones.
    """

    def __init__(self, params_file: str):
        self.params_file = Path(params_file)

        data = np.load(self.params_file)
        self.x = data["x"]
        self.y = data["y"]
        self.u = data["u"]
        self.v = data["v"]
        # Boolean: True marks a vector flagged as spurious during processing.
        self.flags = data["flags"].astype(bool)

    @property
    def grid_spacing(self) -> Tuple[float, float]:
        """(dx, dy) inferred from the coordinate arrays, in physical units."""
        dx = float(np.abs(np.diff(self.x, axis=1)).mean()) if self.x.shape[1] > 1 else 1.0
        dy = float(np.abs(np.diff(self.y, axis=0)).mean()) if self.y.shape[0] > 1 else 1.0
        return dx, dy

    def plot_vector_field(
        self,
        scale: int = 50,
        width: float = 0.0035,
        save_path: Optional[str] = None,
    ):
        """Quiver plot of the valid vectors. Saves to save_path, or shows interactively."""
        import matplotlib.pyplot as plt

        valid = ~self.flags
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
        """Out-of-plane vorticity, dv/dx - du/dy. Defaults to the inferred grid spacing."""
        gx, gy = self.grid_spacing
        dx = gx if dx is None else dx
        dy = gy if dy is None else dy
        return np.gradient(self.v, dx, axis=1) - np.gradient(self.u, dy, axis=0)

    def compute_strain(
        self, dx: Optional[float] = None, dy: Optional[float] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return (exx, eyy, exy) of the 2D strain-rate tensor."""
        gx, gy = self.grid_spacing
        dx = gx if dx is None else dx
        dy = gy if dy is None else dy
        du_dx = np.gradient(self.u, dx, axis=1)
        du_dy = np.gradient(self.u, dy, axis=0)
        dv_dx = np.gradient(self.v, dx, axis=1)
        dv_dy = np.gradient(self.v, dy, axis=0)
        return du_dx, dv_dy, 0.5 * (du_dy + dv_dx)

    def compute_statistics(self) -> Dict[str, float]:
        """Spatial mean and RMS over this single frame.

        This is NOT Reynolds decomposition: subtracting one frame's spatial mean
        measures spatial variance, which equals turbulent intensity only for a
        homogeneous field. True turbulence statistics need an ensemble of pairs --
        average over the time axis, then subtract that mean field from each frame.
        """
        u_prime = self.u - np.nanmean(self.u)
        v_prime = self.v - np.nanmean(self.v)
        rms_u = float(np.nanstd(u_prime))
        rms_v = float(np.nanstd(v_prime))
        return {
            "u_mean": float(np.nanmean(self.u)),
            "v_mean": float(np.nanmean(self.v)),
            "rms_u": rms_u,
            "rms_v": rms_v,
            "tke": 0.5 * (rms_u**2 + rms_v**2),
        }
