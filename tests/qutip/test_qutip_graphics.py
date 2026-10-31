"""Pinned plotting smoke tests for the QuTiP 5.3 graphics extra."""

from __future__ import annotations

import unittest

import pytest

# Guarded so a bare project-environment run skips cleanly instead of failing
# collection; the real run is `tests/run_all.py --isolated qutip`.
matplotlib = pytest.importorskip("matplotlib", reason="qutip graphics need matplotlib")
pytest.importorskip("qutip", reason="qutip needs qutip")

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import qutip  # noqa: E402


class GraphicsApiTests(unittest.TestCase):
    def tearDown(self) -> None:
        plt.close("all")

    def test_phase_space_and_matrix_plotting_apis(self) -> None:
        self.assertEqual(qutip.__version__, "5.3.1")
        state = qutip.fock_dm(6, 1)
        coordinates = np.linspace(-2.0, 2.0, 15)

        fig, ax = qutip.plot_wigner(
            state,
            xvec=coordinates,
            yvec=coordinates,
            projection="2d",
            colorbar=True,
        )
        self.assertIsNotNone(fig)
        self.assertIsNotNone(ax)

        fig, ax = qutip.plot_fock_distribution(state)
        self.assertIsNotNone(fig)
        self.assertIsNotNone(ax)

        fig, ax = qutip.hinton(state, color_style="phase")
        self.assertIsNotNone(fig)
        self.assertIsNotNone(ax)

        fig, ax = qutip.matrix_histogram(
            state,
            bar_style="abs",
            color_style="phase",
        )
        self.assertIsNotNone(fig)
        self.assertIsNotNone(ax)

    def test_result_plot_expect_current_method(self) -> None:
        result = qutip.sesolve(
            0.5 * qutip.sigmax(),
            qutip.basis(2, 0),
            np.linspace(0.0, 1.0, 11),
            e_ops=[qutip.sigmaz()],
        )
        fig, axes = result.plot_expect(labels=["sigma_z"])
        self.assertIsNotNone(fig)
        self.assertTrue(np.asarray(axes, dtype=object).size >= 1)


if __name__ == "__main__":
    unittest.main()
