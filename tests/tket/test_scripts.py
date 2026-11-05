"""Tests for the TKET (pytket) environment, simulation, and compilation scripts.

Four failure modes are worth guarding here, and every assertion below is justified by
either a piece of quantum mechanics known before the code runs, or by the construction of
the input.

First, `check_environment` is the script an agent trusts to decide whether the environment
is usable, so both directions matter: a healthy install must report `ok`, the core-API and
simulator smoke checks must pass, and a version drift must land in `warnings` normally but
in `errors` under `--strict`. It must also flag the distributions that look real but are
not (`pytket-aer` does not exist on PyPI).

Second, the half-turn angle convention is the single easiest thing to get wrong in pytket:
`Circuit(1).Rx(0.5, 0)` must read back a parameter of `0.5` half-turns (pi/2 radians), not
`0.5` radians. The core-API smoke check pins this.

Third, `run_local_simulation` claims specific physics. `H(0)` then `CX(0,1)` is the Bell
state (|00> + |11>)/sqrt(2): no basis state other than |00> and |11> has amplitude, so the
sampler can only ever see those two bit-tuples, in ILO-BE order, and the exact statevector
has magnitude 1/sqrt(2) at indices 0 and 3 and ~0 elsewhere. For the ansatz
`Ry(theta).CX(0,1).Rz(theta)`, both |00> and |11> are +1 eigenstates of Z0 Z1, so
<Z0 Z1> is exactly 1.0 for *every* theta -- a strong invariant, not a lucky number.

Fourth, `compile_and_report` promises to route a circuit onto a coupling graph and report
what changed. Routing the `adder-ish` demo (every CX targets the last qubit) onto a 6-node
line must increase the CX count, must satisfy `GateSetPredicate` and
`ConnectivityPredicate`, and must record an `initial_map`/`final_map` covering every qubit
and classical bit.
"""

from __future__ import annotations

import json
import math
import sys
import unittest
from importlib import metadata
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "tket"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("pytket", reason="tket scripts need pytket")
pytest.importorskip(
    "pytket.extensions.qiskit",
    reason="Aer backends ship in pytket-qiskit behind the [aer] extra",
)

import check_environment  # noqa: E402
import compile_and_report  # noqa: E402
import run_local_simulation  # noqa: E402

# The shared `--help` contract lives in scientific-agent-skills' tests/_contract package.
# tests/tket/conftest.py installs it as `skill_contract` when present; standalone checkouts
# without that repo simply skip the contract test and still run everything else.
try:
    import skill_contract
except ModuleNotFoundError:  # pragma: no cover - depends on graft location
    skill_contract = None

if skill_contract is not None:
    CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def installed(distribution: str) -> str | None:
    """The installed version, read independently of the script under test."""
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


class ImportProbeTests(unittest.TestCase):
    def test_a_distribution_that_is_not_installed_has_no_version(self) -> None:
        self.assertIsNone(check_environment.installed_version("no-such-distribution"))

    def test_an_installed_distribution_reports_its_version(self) -> None:
        self.assertEqual(check_environment.installed_version("pytket"), installed("pytket"))

    def test_a_missing_module_is_reported_with_the_import_error(self) -> None:
        status = check_environment.import_status("no_such_module_at_all")
        self.assertFalse(status["ok"])
        self.assertIsNone(status["module_file"])
        self.assertIn("ModuleNotFoundError", status["error"])

    def test_an_importable_module_reports_where_it_came_from(self) -> None:
        # module_file is what distinguishes "installed" from "importable": a broken
        # optional environment must be nameable, not just falsy.
        status = check_environment.import_status("pytket.circuit")
        self.assertTrue(status["ok"])
        self.assertIsNone(status["error"])
        self.assertTrue(status["module_file"].endswith("__init__.py"))


class EnvironmentReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report, self.errors, self.warnings = check_environment.collect_report(
            require_simulator=False, strict=False
        )

    def test_pytket_alone_is_required_by_default(self) -> None:
        required = {
            name for name, details in self.report["packages"].items() if details["required"]
        }
        self.assertEqual(required, {"pytket"})

    def test_the_simulator_extras_become_required_on_request(self) -> None:
        report, _, _ = check_environment.collect_report(require_simulator=True, strict=False)
        required = {
            name for name, details in report["packages"].items() if details["required"]
        }
        self.assertEqual(required, {"pytket", "pytket-qiskit", "qiskit-aer"})

    def test_ok_is_exactly_the_absence_of_errors(self) -> None:
        # main() turns this into the process exit code.
        self.assertEqual(self.report["ok"], not self.errors)

    def test_a_healthy_environment_reports_no_errors(self) -> None:
        self.assertEqual(self.errors, [])

    def test_installed_versions_are_read_from_the_metadata(self) -> None:
        for name, details in self.report["packages"].items():
            with self.subTest(distribution=name):
                self.assertEqual(details["installed"], installed(name))

    def test_the_nonexistent_pytket_aer_distribution_is_not_installed(self) -> None:
        # pytket-aer does not exist on PyPI; the Aer backends ship in pytket-qiskit[aer].
        # If it ever appears, BOGUS_DISTRIBUTIONS must turn it into an error.
        self.assertIsNone(installed("pytket-aer"))
        self.assertIn("pytket-aer", check_environment.BOGUS_DISTRIBUTIONS)

    def test_version_drift_is_a_warning_but_an_error_under_strict(self) -> None:
        # Expectations come from importlib.metadata and the script's own published
        # baseline, not from the report being checked.
        drifted = {
            name: (installed(name), verified)
            for name, verified in check_environment.VERIFIED_VERSIONS.items()
            if installed(name) is not None and installed(name) != verified
        }
        strict_report, strict_errors, strict_warnings = check_environment.collect_report(
            require_simulator=True, strict=True
        )
        for name, (current, verified) in drifted.items():
            message = (
                f"{name} {current} differs from the verified {verified}; "
                "re-check the snippets in this skill"
            )
            with self.subTest(distribution=name):
                self.assertIn(message, self.warnings)
                self.assertNotIn(message, self.errors)
                if name in {"pytket", "pytket-qiskit", "qiskit-aer"}:
                    self.assertIn(message, strict_errors)
                    self.assertNotIn(message, strict_warnings)

    def test_the_report_survives_json_serialisation(self) -> None:
        # --json is the machine-readable contract, so every value has to be JSON-safe.
        round_tripped = json.loads(json.dumps(self.report, sort_keys=True, default=str))
        self.assertEqual(round_tripped["packages"].keys(), self.report["packages"].keys())


class CoreApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.smoke = check_environment.core_api_smoke()

    def test_the_core_api_smoke_check_reports_no_error(self) -> None:
        self.assertNotIn("error", self.smoke)

    def test_a_bell_circuit_has_the_expected_shape(self) -> None:
        # H(0).CX(0,1).measure_all() on Circuit(2,2): 2 qubits, 2 bits, one CX,
        # and n_gates counts H + CX + 2 Measure = 4.
        self.assertEqual(self.smoke["bell_n_qubits"], 2)
        self.assertEqual(self.smoke["bell_n_bits"], 2)
        self.assertEqual(self.smoke["bell_cx_count"], 1)
        self.assertEqual(self.smoke["bell_n_gates"], 4)

    def test_angles_are_half_turns_not_radians(self) -> None:
        # The single most error-prone pytket convention: Rx(0.5) stores 0.5 half-turns
        # (= pi/2 radians) and reads back exactly 0.5, unnormalised.
        self.assertEqual(self.smoke["rx_half_turn_params"], [0.5])

    def test_passes_mutate_in_place_and_return_a_bool(self) -> None:
        self.assertTrue(self.smoke["optimise_returns_bool"])
        self.assertTrue(self.smoke["sequence_pass_applies"])

    def test_predicates_verify_a_valid_circuit(self) -> None:
        self.assertTrue(self.smoke["predicates_verify"])


class SimulatorSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.smoke = check_environment.simulator_smoke()

    def test_the_simulator_smoke_check_reports_no_error(self) -> None:
        self.assertNotIn("error", self.smoke)

    def test_aer_backend_capability_flags_are_as_documented(self) -> None:
        # AerBackend samples shots but cannot return a statevector or unitary.
        self.assertEqual(self.smoke["backend_name"], "AerBackend")
        self.assertTrue(self.smoke["supports_shots"])
        self.assertTrue(self.smoke["supports_counts"])
        self.assertFalse(self.smoke["supports_state"])
        self.assertTrue(self.smoke["supports_expectation"])

    def test_a_three_qubit_ghz_state_only_ever_yields_all_zero_or_all_one(self) -> None:
        # H then a CX chain prepares (|000> + |111>)/sqrt(2); no other bitstring has
        # amplitude, so exactly those two outcomes appear, in ILO-BE tuple order.
        outcomes = [tuple(bits) for bits in self.smoke["ghz_distinct_outcomes"]]
        self.assertEqual(set(outcomes), {(0, 0, 0), (1, 1, 1)})
        self.assertEqual(self.smoke["ghz_total_shots"], 200)


class ArchitectureParsingTests(unittest.TestCase):
    def test_none_means_no_routing_constraint(self) -> None:
        self.assertIsNone(compile_and_report.parse_architecture("none"))

    def test_a_linear_chain_has_the_requested_nodes(self) -> None:
        arch = compile_and_report.parse_architecture("linear:6")
        self.assertEqual([str(node) for node in arch.nodes], [f"node[{i}]" for i in range(6)])

    def test_ring_grid_and_star_build_the_right_architecture_types(self) -> None:
        from pytket.architecture import RingArch, SquareGrid

        self.assertIsInstance(compile_and_report.parse_architecture("ring:4"), RingArch)
        grid = compile_and_report.parse_architecture("grid:2x3")
        self.assertIsInstance(grid, SquareGrid)
        self.assertEqual(len(grid.nodes), 6)
        star = compile_and_report.parse_architecture("star:5")
        # A 5-node star: centre node 0 plus 4 leaves = 4 undirected arcs.
        self.assertEqual(len(star.nodes), 5)
        self.assertEqual(len(star.coupling), 4)

    def test_malformed_topology_specs_are_rejected(self) -> None:
        for spec in ("linear", "ring:2", "grid:3", "star:2", "hexagon:4"):
            with self.subTest(spec=spec):
                with self.assertRaises(ValueError):
                    compile_and_report.parse_architecture(spec)

    def test_the_target_gateset_has_six_operations(self) -> None:
        # TARGET_GATESET = CX,Rz,H,Measure,Reset,Barrier
        self.assertEqual(len(compile_and_report.target_gateset()), 6)


class DemoCircuitTests(unittest.TestCase):
    def test_the_adder_ish_demo_forces_routing_to_insert_swaps(self) -> None:
        # Every CX targets the last qubit, which is not nearest-neighbour on a line, so
        # the pre-compile CX count equals the number of source qubits (n-1).
        before = compile_and_report.measure_circuit(compile_and_report.demo_circuit("adder-ish", 5))
        self.assertEqual(before["cx_count"], 4)
        self.assertEqual(before["n_gates"], 10)

    def test_an_unknown_demo_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            compile_and_report.demo_circuit("shor", 4)


class CompilationReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = compile_and_report.compile_report(
            compile_and_report.demo_circuit("adder-ish", 5),
            compile_and_report.parse_architecture("linear:6"),
            optimisation_level=2,
            use_backend_pass=False,
            check_semantics=False,
        )

    def test_routing_onto_a_line_increases_the_two_qubit_gate_count(self) -> None:
        # Inserted swaps show up as extra CX gates; the router cannot reduce them here.
        self.assertGreater(self.report["after"]["cx_count"], self.report["before"]["cx_count"])
        self.assertGreater(self.report["cx_delta"], 0)
        self.assertGreater(self.report["depth_delta"], 0)

    def test_the_compiled_circuit_satisfies_the_gateset_and_connectivity_predicates(self) -> None:
        # These two are the ones that must hold for a real device; a FAIL is a real bug.
        predicates = self.report["predicates"]
        self.assertTrue(predicates["GateSetPredicate({CX,Rz,H,Measure,Reset,Barrier})"])
        self.assertTrue(predicates["ConnectivityPredicate(architecture)"])

    def test_benign_post_routing_predicate_failures_are_present_and_expected(self) -> None:
        # After routing, DefaultRegisterPredicate and DirectednessPredicate legitimately
        # FAIL (registers renamed; some arcs used against their direction). The report
        # surfaces them rather than hiding them; an agent must compare against
        # backend.required_predicates, not against every predicate.
        predicates = self.report["predicates"]
        self.assertIn("DefaultRegisterPredicate", predicates)
        self.assertIn("DirectednessPredicate(architecture)", predicates)

    def test_the_initial_and_final_maps_cover_every_qubit_and_classical_bit(self) -> None:
        # 5 qubits + 5 classical bits = 10 entries in each map; classical bits map to
        # themselves, qubits map to architecture nodes.
        self.assertEqual(len(self.report["initial_map"]), 10)
        self.assertEqual(len(self.report["final_map"]), 10)
        for bit in range(5):
            self.assertEqual(self.report["initial_map"][f"c[{bit}]"], f"c[{bit}]")
        self.assertTrue(
            all(value.startswith("node[") for key, value in self.report["initial_map"].items()
                if key.startswith("q["))
        )

    def test_the_architecture_nodes_are_reported(self) -> None:
        self.assertEqual(len(self.report["architecture_nodes"]), 6)

    def test_the_report_survives_json_serialisation(self) -> None:
        round_tripped = json.loads(json.dumps(self.report, sort_keys=True, default=str))
        self.assertEqual(round_tripped["after"]["cx_count"], self.report["after"]["cx_count"])


class BellStatePhysicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from pytket.extensions.qiskit import AerBackend, AerStateBackend

        cls.shot_backend = AerBackend()
        cls.state_backend = AerStateBackend()

    def test_the_bell_circuit_is_fully_measured(self) -> None:
        self.assertEqual(run_local_simulation.bell_circuit().n_bits, 2)

    def test_sampling_a_bell_pair_only_ever_yields_correlated_outcomes(self) -> None:
        # (|00> + |11>)/sqrt(2): the only possible bit-tuples are (0,0) and (1,1), and
        # every requested shot is accounted for.
        result = self.shot_backend.run_circuit(
            run_local_simulation.bell_circuit(), n_shots=256, seed=5
        )
        counts = result.get_counts()
        self.assertEqual(set(counts), {(0, 0), (1, 1)})
        self.assertEqual(sum(counts.values()), 256)

    def test_the_same_seed_reproduces_the_same_counts(self) -> None:
        first = self.shot_backend.run_circuit(
            run_local_simulation.bell_circuit(), n_shots=512, seed=42
        ).get_counts()
        second = self.shot_backend.run_circuit(
            run_local_simulation.bell_circuit(), n_shots=512, seed=42
        ).get_counts()
        self.assertEqual(first, second)

    def test_the_exact_bell_statevector_has_amplitude_only_at_zero_and_three(self) -> None:
        # Indices 0 (|00>) and 3 (|11>) each carry magnitude 1/sqrt(2); 1 and 2 are ~0.
        summary = run_local_simulation.statevector_summary(
            self.state_backend, run_local_simulation._bell_unmeasured()
        )
        significant = {entry["index"]: entry["magnitude"] for entry in summary["significant_amplitudes"]}
        self.assertEqual(set(significant), {0, 3})
        expected = 1.0 / math.sqrt(2.0)
        self.assertAlmostEqual(significant[0], expected, places=12)
        self.assertAlmostEqual(significant[3], expected, places=12)

    def test_get_shots_returns_one_uint8_row_per_shot(self) -> None:
        shape = run_local_simulation._shots_shape(self.shot_backend, 100, seed=1)
        self.assertEqual(shape["shape"], [100, 3])
        self.assertEqual(shape["dtype"], "uint8")


class ExpectationValueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from pytket.extensions.qiskit import AerBackend

        cls.backend = AerBackend()

    def test_z0z1_on_the_ansatz_is_exactly_one_for_every_theta(self) -> None:
        # Ry(theta).CX(0,1).Rz(theta) only ever populates |00> and |11>, and both are +1
        # eigenstates of Z0 Z1, so the expectation is 1.0 regardless of theta. All four
        # routes (exact operator, exact Pauli string, shot-based helper, from_counts) must
        # agree -- this is the invariant that catches a swapped observable or a wrong
        # operator/string type.
        for theta in (0.0, 0.25, 0.5, 1.0):
            with self.subTest(theta=theta):
                report = run_local_simulation.expectation_report(self.backend, theta, 4000)
                self.assertAlmostEqual(report["exact_operator"], 1.0, places=10)
                self.assertAlmostEqual(report["exact_pauli_string"], 1.0, places=10)
                self.assertAlmostEqual(report["shot_based_operator_helper"], 1.0, places=2)
                self.assertAlmostEqual(report["from_counts"], 1.0, places=2)

    def test_the_observable_label_is_reported(self) -> None:
        report = run_local_simulation.expectation_report(self.backend, 0.25, 500)
        self.assertEqual(report["observable"], "<Z0 Z1>")
        self.assertEqual(report["shots"], 500)


class VersionSpecifierTests(unittest.TestCase):
    """`version_satisfies` is hand-rolled because the script may not depend on packaging.

    The expectations here come from PEP 440, not from the implementation. Two of them are
    load-bearing for the tket ecosystem specifically: `~=1.26` admits `1.34.0` (which is why
    pytket-qsharp is uninstallable beside pytket 2.x but not beside 1.34), and the marker
    form must be refused rather than silently mis-parsed.
    """

    def test_plain_upper_bound_pins(self) -> None:
        for version, expected in (("0.77.0", True), ("0.78.0", False), ("0.78.1", False)):
            with self.subTest(version=version):
                self.assertIs(check_environment.version_satisfies(version, "<0.78"), expected)

    def test_lower_and_equal_bounds(self) -> None:
        self.assertIs(check_environment.version_satisfies("2.18.4", ">=2.11.0"), True)
        self.assertIs(check_environment.version_satisfies("2.10.9", ">=2.11.0"), False)
        self.assertIs(check_environment.version_satisfies("2.18.4", "==2.18.4"), True)
        self.assertIs(check_environment.version_satisfies("2.18.4", "!=2.18.4"), False)

    def test_compatible_release_follows_pep_440(self) -> None:
        # ~=X.Y is >=X.Y together with ==X.*
        self.assertIs(check_environment.version_satisfies("1.34.0", "~=1.26"), True)
        self.assertIs(check_environment.version_satisfies("1.27.0", "~=1.26"), True)
        self.assertIs(check_environment.version_satisfies("2.18.4", "~=1.26"), False)
        self.assertIs(check_environment.version_satisfies("1.25.9", "~=1.26"), False)

    def test_conjunctions_must_all_hold(self) -> None:
        self.assertIs(check_environment.version_satisfies("2.18.4", ">=2.11,<3.0"), True)
        self.assertIs(check_environment.version_satisfies("3.1.0", ">=2.11,<3.0"), False)

    def test_forms_the_helper_does_not_model_are_reported_as_unknown(self) -> None:
        # Guessing here would either hide a real conflict or invent a fake one. The `;`
        # case is a regression guard: the environment marker's quoted version used to be
        # parsed as a comparison target.
        for specifier in (
            ">=2.11; python_version<'3.14'",
            ">=2.11,<3.0.*",
            "==2.18.*",
            "not a specifier",
        ):
            with self.subTest(specifier=specifier):
                self.assertIsNone(check_environment.version_satisfies("2.18.4", specifier))

    def test_an_empty_specifier_is_vacuously_satisfied(self) -> None:
        # PEP 508: an empty specifier set is equivalent to `>=0`, i.e. every version
        # satisfies it -- not "unknown". An unparseable version string, by contrast, is
        # genuinely unknown.
        self.assertIs(check_environment.version_satisfies("2.18.4", ""), True)
        self.assertIsNone(check_environment.version_satisfies("not.a.version", "<0.78"))

    def test_pre_release_and_local_segments_truncate_to_the_release(self) -> None:
        self.assertEqual(check_environment._version_tuple("0.8.0.dev8"), (0, 8, 0))
        self.assertEqual(check_environment._version_tuple("1.2.3rc1"), (1, 2, 3))
        self.assertEqual(check_environment._version_tuple("2.18.4"), (2, 18, 4))


class PinConflictTests(unittest.TestCase):
    """The qermit conflict is real and pip does NOT report it: it silently backtracks.

    Verified 2026-10-01 by reading `Requires-Dist` out of every qermit wheel (0.8.5 through
    0.9.3): all of them pin `pytket-qiskit<0.78` and `pytket-quantinuum[pecos]<0.59`. A clean
    resolve of the current extension set *with* qermit exits 0 and picks qermit 0.7.1, a
    release that predates the documented API. So the script has to surface it itself.
    """

    def test_qermit_is_registered_as_a_conflicting_package(self) -> None:
        self.assertIn("qermit", check_environment.KNOWN_PIN_CONFLICTS)
        pins = dict(check_environment.KNOWN_PIN_CONFLICTS["qermit"])
        self.assertEqual(pins["pytket-qiskit"], "<0.78")
        self.assertEqual(pins["pytket-quantinuum"], "<0.59")

    def test_a_conflicting_set_warns_only_when_both_sides_are_installed(self) -> None:
        # check_pin_conflicts reads real metadata, so the assertion is about the shape of
        # the decision, not about a fabricated environment.
        qermit_version = installed("qermit")
        qiskit_version = installed("pytket-qiskit")
        messages = check_environment.check_pin_conflicts(["qermit", "pytket-qiskit"])
        if qermit_version is None or qiskit_version is None:
            self.assertEqual(messages, [], "an absent package cannot conflict")
            return
        conflicting = check_environment.version_satisfies(qiskit_version, "<0.78") is False
        if conflicting:
            self.assertEqual(len(messages), 1)
            self.assertIn("qermit", messages[0])
            self.assertIn("pytket-qiskit<0.78", messages[0])
            self.assertIn("references/setup.md", messages[0])
        else:
            self.assertEqual(messages, [])

    def test_a_package_absent_from_the_conflict_table_is_never_queried(self) -> None:
        self.assertEqual(
            check_environment.check_pin_conflicts(["pytket", "pytket-qiskit", "qiskit-aer"]),
            [],
        )

    def test_the_report_carries_any_conflict_as_a_warning_not_an_error(self) -> None:
        # A conflicting environment is still usable for the core workflows the skill
        # documents, so it must not flip the exit code -- but it must not be silent either.
        report, errors, warnings = check_environment.collect_report(
            require_simulator=False, strict=False
        )
        qermit_version = installed("qermit")
        if qermit_version is None or installed("pytket-qiskit") is None:
            self.assertEqual([w for w in warnings if "qermit" in w], [])
        else:
            expected = check_environment.check_pin_conflicts(["qermit", "pytket-qiskit"])
            for message in expected:
                with self.subTest(message=message):
                    self.assertIn(message, warnings)
                    self.assertNotIn(message, errors)
        self.assertEqual(report["ok"], not errors)


class BatchSubmissionTests(unittest.TestCase):
    def test_a_batch_returns_one_result_per_circuit_in_order(self) -> None:
        from pytket.extensions.qiskit import AerBackend

        report = run_local_simulation.batch_report(AerBackend(), 100)
        self.assertEqual(report["circuits_submitted"], 3)
        self.assertEqual(report["results_returned"], 3)
        # bell(2), ghz(3), ghz(4): each is a 2-outcome correlated state, 100 shots each.
        for summary in report["counts_per_circuit"]:
            self.assertEqual(summary["total_shots"], 100)
            self.assertEqual(summary["distinct_outcomes"], 2)


if __name__ == "__main__":
    unittest.main()
