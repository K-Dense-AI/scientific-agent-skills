"""Analysis utilities for PIV data."""

from pathlib import Path
from typing import Optional
import numpy as np


class PypivAnalyzer:
    """Wrapper for PIV data analysis using pivpy."""

    def __init__(self, params_file: str):
        """Initialize analyzer with params.npz file."""
        self.params_file = Path(params_file)

        data = np.load(self.params_file)
        self.x = data["x"]
        self.y = data["y"]
        self.u = data["u"]
        self.v = data["v"]
        self.flags = data["flags"]

    def plot_vector_field(self, scale: int = 50, width: float = 0.0035):
        """Plot velocity vectors."""
        import matplotlib.pyplot as plt

        valid_mask = self.flags == 0
        plt.figure(figsize=(10, 8))
        plt.quiver(
            self.x[valid_mask],
            self.y[valid_mask],
            self.u[valid_mask],
            self.v[valid_mask],
            scale=scale,
            width=width,
        )
        plt.xlabel("X (pixels)")
        plt.ylabel("Y (pixels)")
        plt.title("Velocity Field")
        plt.gca().invert_yaxis()
        plt.axis("equal")
        plt.show()

    def compute_vorticity(self, dx: float = 1.0):
        """Compute vorticity from velocity field."""
        dv_dx = np.gradient(self.v, dx, axis=1)
        du_dy = np.gradient(self.u, dx, axis=0)
        return dv_dx - du_dy

    def get_velocity_magnitude(self):
        """Calculate velocity magnitude."""
        return np.sqrt(self.u**2 + self.v**2)
