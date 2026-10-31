"""Pinned, network-free synthetic physics tests for QuTiP 5.3.1."""

from __future__ import annotations

import inspect
import json
import math
import sys
import unittest

import pytest
from pathlib import Path

import numpy as np
# Guarded so a bare project-environment run skips cleanly instead of failing
# collection; the real run is `tests/run_all.py --isolated qutip`.
pytest.importorskip("qutip", reason="qutip needs qutip")
import qutip


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "qutip"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _common  # noqa: E402
import convergence_sweep  # noqa: E402
import qobj_model_validator  # noqa: E402
import result_audit  # noqa: E402
import two_level_simulation  # noqa: E402


class VersionAndApiTests(unittest.TestCase):
    def test_exact_version_and_current_solver_boundaries(self) -> None:
        self.assertEqual(qutip.__version__, "5.3.1")
        self.assertFalse(hasattr(qutip, "Options"))

        sesolve_parameters = inspect.signature(qutip.sesolve).parameters
        self.assertEqual(
            sesolve_parameters["e_ops"].kind,
            inspect.Parameter.KEYWORD_ONLY,
        )
        mc_parameters = inspect.signature(qutip.mcsolve).parameters
        self.assertIn("seeds", mc_parameters)
        self.assertIn("target_tol", mc_parameters)
        stochastic_parameters = inspect.signature(qutip.smesolve).parameters
        self.assertIn("heterodyne", stochastic_parameters)
        self.assertNotIn("noise", stochastic_parameters)

    def test_qobj_dims_tensor_order_and_qobjevo(self) -> None:
        state = qutip.tensor(qutip.basis(2, 0), qutip.basis(3, 1))
        self.assertEqual(state.dims, [[2, 3], [1]])
        self.assertEqual(state.proj().ptrace(0).dims, [[2], [2]])
        self.assertEqual(state.proj().ptrace(1).dims, [[3], [3]])

        def coefficient(t, amplitude):
            return amplitude * math.cos(t)

        H = qutip.QobjEvo(
            [qutip.sigmaz(), [qutip.sigmax(), coefficient]],
            args={"amplitude": 0.25},
        )
        self.assertTrue(H(0.0).isherm)
        before = complex(H(0.0)[0, 1])
        H.arguments(amplitude=0.5)
        after = complex(H(0.0)[0, 1])
        self.assertAlmostEqual(after.real, 2.0 * before.real)

    def test_qfunc_is_called_with_state_and_axis_order_is_y_x(self) -> None:
        xvec = np.linspace(-2.0, 2.0, 7)
        yvec = np.linspace(-1.0, 1.0, 5)
        calculator = qutip.QFunc(xvec, yvec, memory=16)
        self.assertTrue(callable(calculator))
        self.assertFalse(hasattr(calculator, "eval"))
        values = calculator(qutip.fock_dm(6, 0))
        self.assertEqual(values.shape, (len(yvec), len(xvec)))
        direct = qutip.qfunc(qutip.fock_dm(6, 0), xvec, yvec)
        np.testing.assert_allclose(values, direct, atol=1.0e-13, rtol=1.0e-13)


class BundledModelTests(unittest.TestCase):
    def test_qobj_model_validator_accepts_physical_two_level_model(self) -> None:
        document = {
            "schema_version": 1,
            "unit_convention": "hbar=1-angular-frequency",
            "tolerance": 1.0e-10,
            "objects": [
                {
                    "name": "H",
                    "role": "hamiltonian",
                    "dims": [2],
                    "data": [[0.5, 0.0], [0.0, -0.5]],
                },
                {
                    "name": "psi0",
                    "role": "initial_state",
                    "dims": [2],
                    "data": [1.0, 0.0],
                },
                {
                    "name": "loss",
                    "role": "collapse_operator",
                    "dims": [2],
                    "data": [[0.0, 0.0], [1.0, 0.0]],
                    "rate": 0.2,
                },
                {
                    "name": "z",
                    "role": "observable",
                    "dims": [2],
                    "data": [[1.0, 0.0], [0.0, -1.0]],
                },
            ],
        }
        report = qobj_model_validator.validate_model(document, qutip)
        self.assertTrue(report["valid"])
        self.assertTrue(report["checks"]["all_dimensions_compatible"])
        collapse = next(
            item for item in report["objects"] if item["role"] == "collapse_operator"
        )
        self.assertEqual(collapse["scaling"], "sqrt(rate) * operator")

    def test_mesolve_matches_amplitude_decay_and_audits_result(self) -> None:
        config = two_level_simulation.SimulationConfig(
            solver="mesolve",
            initial_state="excited",
            omega=1.0,
            drive=0.0,
            decay_rate=0.2,
            dephasing_rate=0.05,
            t_final=8.0,
            time_points=161,
            trajectories=1,
            seed=20_260_723,
            method="adams",
            atol=1.0e-11,
            rtol=1.0e-9,
        )
        report = two_level_simulation.run_simulation(config, qutip)
        self.assertLess(report["analytic_reference"]["max_abs_error"], 2.0e-7)
        self.assertTrue(report["checks"]["population_within_tolerance"])
        self.assertTrue(
            report["checks"]["final_state"]["valid_within_tolerance"]
        )
        self.assertTrue(report["solver"]["stats"])

        portable = json.loads(_common.strict_json_bytes(report))
        audit = result_audit.audit_document(portable, tolerance=1.0e-6)
        self.assertEqual(audit["status"], "pass")

    def test_mcsolve_is_seed_reproducible_and_bounded(self) -> None:
        config = two_level_simulation.SimulationConfig(
            solver="mcsolve",
            initial_state="excited",
            omega=1.0,
            drive=0.0,
            decay_rate=0.3,
            dephasing_rate=0.0,
            t_final=2.0,
            time_points=21,
            trajectories=20,
            seed=12345,
            method="adams",
            atol=1.0e-9,
            rtol=1.0e-7,
        )
        first = two_level_simulation.run_simulation(config, qutip)
        second = two_level_simulation.run_simulation(config, qutip)
        np.testing.assert_allclose(
            first["expectations"]["excited_population"],
            second["expectations"]["excited_population"],
            atol=0.0,
            rtol=0.0,
        )
        self.assertEqual(
            first["trajectory_statistics"]["trajectories_run"],
            20,
        )
        self.assertEqual(len(first["trajectory_statistics"]["seeds"]), 20)

    def test_deterministic_convergence_sweep(self) -> None:
        parser = convergence_sweep.build_parser()
        args = parser.parse_args(
            [
                "--mode",
                "deterministic",
                "--time-points",
                "21,41",
                "--rtols",
                "1e-5,1e-8",
                "--t-final",
                "2",
                "--acceptance",
                "1e-4",
            ]
        )
        report = convergence_sweep.run_sweep(args, qutip)
        self.assertEqual(len(report["runs"]), 2)
        self.assertEqual(len(report["comparisons"]), 1)
        self.assertLess(
            report["comparisons"][0]["max_abs_population_difference"],
            1.0e-4,
        )


class PhysicsApiTests(unittest.TestCase):
    def test_steady_state_correlation_and_spectrum_are_finite(self) -> None:
        H = 0.5 * qutip.sigmaz()
        c_ops = [
            np.sqrt(0.2) * qutip.sigmam(),
            np.sqrt(0.05) * qutip.sigmap(),
        ]
        rho_ss = qutip.steadystate(H, c_ops, method="direct")
        residual = (
            qutip.liouvillian(H, c_ops)
            * qutip.operator_to_vector(rho_ss)
        ).norm()
        self.assertLess(residual, 1.0e-11)
        self.assertAlmostEqual(complex(rho_ss.tr()).real, 1.0, places=12)
        self.assertGreaterEqual(min(rho_ss.eigenenergies()), -1.0e-12)

        taulist = np.linspace(0.0, 8.0, 81)
        correlation = qutip.correlation_2op_1t(
            H,
            rho_ss,
            taulist,
            c_ops,
            qutip.sigmap(),
            qutip.sigmam(),
        )
        self.assertTrue(np.isfinite(correlation).all())
        frequencies = np.linspace(-3.0, 3.0, 61)
        values = qutip.spectrum(
            H,
            frequencies,
            c_ops,
            qutip.sigmap(),
            qutip.sigmam(),
            solver="es",
        )
        self.assertTrue(np.isfinite(values).all())

    def test_brmesolve_and_stochastic_solver_synthetic_runs(self) -> None:
        times = np.linspace(0.0, 0.1, 6)

        def spectrum(w):
            return 0.02 * w if w > 0.0 else 0.0

        br_result = qutip.brmesolve(
            0.5 * qutip.sigmaz(),
            qutip.basis(2, 0),
            times,
            a_ops=[(qutip.sigmax(), spectrum)],
            e_ops=[qutip.sigmaz()],
            options={"progress_bar": ""},
        )
        self.assertTrue(np.isfinite(br_result.expect[0]).all())

        stochastic = qutip.ssesolve(
            0.5 * qutip.sigmaz(),
            qutip.basis(2, 0),
            times,
            sc_ops=[np.sqrt(0.05) * qutip.sigmaz()],
            heterodyne=False,
            e_ops=[qutip.sigmaz()],
            ntraj=2,
            seeds=123,
            options={"dt": 0.005, "progress_bar": ""},
        )
        self.assertTrue(np.isfinite(stochastic.expect[0]).all())
        self.assertEqual(stochastic.num_trajectories, 2)

    def test_floquet_heom_and_piqs_current_namespaces(self) -> None:
        def drive(t, amplitude, omega):
            return amplitude * math.cos(omega * t)

        omega = 2.0
        period = 2.0 * math.pi / omega
        H_periodic = qutip.QobjEvo(
            [qutip.sigmaz(), [qutip.sigmax(), drive]],
            args={"amplitude": 0.1, "omega": omega},
        )
        floquet = qutip.FloquetBasis(H_periodic, period)
        self.assertEqual(len(floquet.e_quasi), 2)
        self.assertEqual(len(floquet.mode(0.0)), 2)

        from qutip import piqs
        from qutip.solver.heom import DrudeLorentzBath, HEOMSolver

        bath = DrudeLorentzBath(
            qutip.sigmaz(),
            lam=0.01,
            gamma=1.0,
            T=1.0,
            Nk=1,
        )
        heom_solver = HEOMSolver(
            0.5 * qutip.sigmax(),
            bath,
            max_depth=1,
            options={"progress_bar": "", "store_states": True},
        )
        heom_result = heom_solver.run(
            qutip.basis(2, 0).proj(),
            [0.0, 0.02],
        )
        self.assertEqual(len(heom_result.states), 2)
        self.assertAlmostEqual(
            complex(heom_result.states[-1].tr()).real,
            1.0,
            places=8,
        )

        ensemble = piqs.Dicke(2, emission=0.1)
        rho0 = piqs.dicke(2, 1, 1)
        piqs_result = qutip.mesolve(
            ensemble.liouvillian(),
            rho0,
            [0.0, 0.1],
            e_ops=[piqs.jspin(2, "z", basis="dicke")],
        )
        self.assertEqual(len(piqs_result.expect[0]), 2)
        self.assertTrue(hasattr(ensemble, "pisolve"))
        self.assertFalse(hasattr(ensemble, "solve"))


if __name__ == "__main__":
    unittest.main()
