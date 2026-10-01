"""Real Primer3 checks for coordinates, constraints, and physical model inputs."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import skill_contract

primer3 = pytest.importorskip("primer3")

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "primer-design"
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def run_script(name, *arguments):
    return subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / name), *map(str, arguments)],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def reverse_complement(sequence):
    return sequence.translate(str.maketrans("ACGT", "TGCA"))[::-1]


def demo_sequence():
    return "".join(
        line.strip() for line in (SKILL_ROOT / "assets" / "demo-template.fasta").read_text().splitlines()
        if not line.startswith(">")
    )


def design(tmp_path, config=None, extra=(), template=None, name="design"):
    output = tmp_path / f"{name}.json"
    command = ["--template", template or SKILL_ROOT / "assets" / "demo-template.fasta",
               "--preset", "qpcr", "--output", output]
    if config is not None:
        config_path = tmp_path / f"{name}-config.json"
        config_path.write_text(json.dumps(config))
        command.extend(["--config", config_path])
    result = run_script("design_primers.py", *command, *extra)
    return result, json.loads(output.read_text()) if output.exists() else None


def write_pairs(tmp_path, rows, name="pairs.tsv"):
    path = tmp_path / name
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=[
            "pair_id", "forward", "reverse", "forward_tail", "reverse_tail",
        ])
        writer.writeheader()
        writer.writerows(rows)
    return path


def assess(tmp_path, rows, extra=(), name="thermo"):
    pairs = write_pairs(tmp_path, rows, name=f"{name}-pairs.tsv")
    output = tmp_path / f"{name}.json"
    result = run_script("check_thermodynamics.py", "--pairs", pairs, "--output", output, *extra)
    return result, json.loads(output.read_text()) if output.exists() else None


@pytest.fixture
def ordinary_pair():
    # These deliberately yield different directional end-stability energies.
    return {"pair_id": "alpha", "forward": "GTAAAACGACGGCCAGT", "reverse": "ACTGGCCGTCGTTTAC"}


def test_shipped_design_obeys_target_geometry_and_export_contract(tmp_path):
    config = json.loads((SKILL_ROOT / "assets" / "qpcr-config.json").read_text())
    pairs_path, expected_path = tmp_path / "pairs.tsv", tmp_path / "expected.tsv"
    result, report = design(tmp_path, config, extra=[
        "--pairs-out", pairs_path, "--expected-out", expected_path,
        "--forward-tail", "GGTCTC", "--reverse-tail", "ATCG",
    ])
    assert result.returncode == 0, result.stderr
    assert report["status"] == "candidates_generated"
    assert len(report["pairs"]) == config["global_args"]["PRIMER_NUM_RETURN"]
    template = demo_sequence()
    for pair in report["pairs"]:
        left, left_end = pair["forward_interval"]
        right_start, right_end = pair["reverse_interval"]
        assert pair["forward"] == template[left:left_end]
        assert pair["reverse"] == reverse_complement(template[right_start:right_end])
        assert left_end <= 235 and right_start >= 265
        assert pair["product_interval"] == [left, right_end]
        assert pair["product_sequence"] == template[left:right_end]
        assert 90 <= pair["product_size"] == right_end - left <= 180
        assert pair["tailed_product_size"] == pair["product_size"] + 10
        assert pair["tailed_product_sequence"] == "GGTCTC" + pair["product_sequence"] + "CGAT"
        assert pair["forward_order_sequence"] == "GGTCTC" + pair["forward"]
        assert pair["reverse_order_sequence"] == "ATCG" + pair["reverse"]
        assert pair["specificity_status"] == "not_screened"
    with pairs_path.open() as handle:
        exported = list(csv.DictReader(handle, delimiter="\t"))
    with expected_path.open() as handle:
        expected = list(csv.DictReader(handle, delimiter="\t"))
    assert len(exported) == len(expected) == len(report["pairs"])
    for row, coordinates, pair in zip(exported, expected, report["pairs"]):
        assert row["pair_id"] == coordinates["pair_id"] == pair["pair_id"]
        assert row["reverse"] == pair["reverse"]
        assert [int(coordinates["start"]), int(coordinates["end"])] == pair["product_interval"]
    source = SKILL_ROOT / "assets" / "demo-template.fasta"
    assert report["provenance"]["template_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert report["provenance"]["primer3_py_version"] == primer3.__version__
    assert report["provenance"]["libprimer3_version"] == primer3.thermoanalysis.get_libprimer3_version()


def test_design_and_checker_agree_under_nondefault_tm_and_salt_models(tmp_path):
    config = json.loads((SKILL_ROOT / "assets" / "qpcr-config.json").read_text())
    config["global_args"].update(PRIMER_TM_FORMULA=0, PRIMER_SALT_CORRECTIONS=2)
    pairs_path = tmp_path / "nondefault-pairs.tsv"
    result, designed = design(tmp_path, config, extra=["--pairs-out", pairs_path])
    assert result.returncode == 0, result.stderr
    output = tmp_path / "nondefault-thermo.json"
    result = run_script("check_thermodynamics.py", "--pairs", pairs_path, "--output", output,
                        "--tm-method", "breslauer", "--salt-corrections-method", "owczarzy")
    assert result.returncode == 0, result.stderr
    thermo = json.loads(output.read_text())
    oligos = {entry["oligo_id"]: entry for entry in thermo["oligos"]}
    for pair in designed["pairs"]:
        for role in ("forward", "reverse"):
            assert oligos[f"{pair['pair_id']}:{role}"]["annealing_tm_c"] == pytest.approx(pair[f"{role}_tm_c"])
    assert thermo["settings"]["tm_method"] == "breslauer"
    assert thermo["settings"]["salt_corrections_method"] == "owczarzy"
    assert thermo["provenance"]["libprimer3_version"] == primer3.thermoanalysis.get_libprimer3_version()


def test_multiple_targets_are_alternatives_not_a_joint_coverage_requirement(tmp_path):
    # No <=180 bp product can cover both targets separated by 260 bases.
    targets = [[90, 10], [350, 10]]
    config = {"sequence_args": {"SEQUENCE_TARGET": targets},
              "global_args": {"PRIMER_PRODUCT_SIZE_RANGE": [[90, 180]]}}
    result, report = design(tmp_path, config)
    assert result.returncode == 0, result.stderr
    assert report["pairs"]
    for pair in report["pairs"]:
        flanked = [pair["forward_interval"][1] <= start and
                   pair["reverse_interval"][0] >= start + size for start, size in targets]
        assert sum(flanked) == 1


def test_masked_variant_is_excluded_from_both_binding_intervals(tmp_path):
    config = json.loads((SKILL_ROOT / "assets" / "qpcr-config.json").read_text())
    result, original = design(tmp_path, config, name="initial")
    assert result.returncode == 0, result.stderr
    first = original["pairs"][0]
    positions = [first["forward_interval"][1] - 1, first["reverse_interval"][0]]
    mask = tmp_path / "variants.bed"
    mask.write_text("".join(f"synthetic_target\t{p}\t{p + 1}\n" for p in positions))
    result, screened = design(tmp_path, config, extra=["--mask-bed", mask], name="masked")
    assert result.returncode == 0, result.stderr
    for pair in screened["pairs"]:
        for start, end in [pair["forward_interval"], pair["reverse_interval"]]:
            assert all(not start <= position < end for position in positions)
    assert screened["provenance"]["mask_bed_sha256"] == hashlib.sha256(mask.read_bytes()).hexdigest()


def test_junction_index_names_base_immediately_left_of_boundary(tmp_path):
    sequence = demo_sequence()
    # These exact cores pass default design constraints. Boundary 246 has
    # precisely 8 bases at the forward 5-prime side and 12 at its 3-prime side.
    config = {"sequence_args": {
        "SEQUENCE_PRIMER": sequence[238:258],
        "SEQUENCE_PRIMER_REVCOMP": reverse_complement(sequence[356:376]),
        "SEQUENCE_OVERLAP_JUNCTION_LIST": [245],
    }, "global_args": {
        "PRIMER_MIN_5_PRIME_OVERLAP_OF_JUNCTION": 8,
        "PRIMER_MIN_3_PRIME_OVERLAP_OF_JUNCTION": 12,
    }}
    result, report = design(tmp_path, config, name="junction")
    assert result.returncode == 0, result.stderr
    assert report["pairs"][0]["forward_interval"] == [238, 258]
    config["sequence_args"]["SEQUENCE_OVERLAP_JUNCTION_LIST"] = [246]
    result, report = design(tmp_path, config, name="wrong-junction")
    assert result.returncode == 1
    assert report["status"] == "no_candidates"


def test_base_quality_excludes_low_confidence_binding_bases(tmp_path):
    result, initial = design(tmp_path, name="initial")
    assert result.returncode == 0
    site = initial["pairs"][0]["forward_interval"][0]
    scores = [50] * len(demo_sequence())
    scores[site] = 5
    result, report = design(tmp_path, {"sequence_args": {"SEQUENCE_QUALITY": scores},
                                      "global_args": {"PRIMER_MIN_QUALITY": 20}}, name="quality")
    assert result.returncode == 0, result.stderr
    assert all(not start <= site < end for pair in report["pairs"]
               for start, end in (pair["forward_interval"], pair["reverse_interval"]))


def test_ambiguous_template_site_is_not_guessed_into_a_primer(tmp_path):
    result, original = design(tmp_path, name="initial")
    assert result.returncode == 0, result.stderr
    position = original["pairs"][0]["forward_interval"][0] + 3
    sequence = demo_sequence()
    fasta = tmp_path / "ambiguous.fasta"
    fasta.write_text(f">synthetic_target\n{sequence[:position]}R{sequence[position + 1:]}\n")
    result, report = design(tmp_path, template=fasta, name="ambiguous")
    assert result.returncode == 0, result.stderr
    assert report["ambiguous_template_bases_masked"] == 1
    for pair in report["pairs"]:
        for start, end in [pair["forward_interval"], pair["reverse_interval"]]:
            assert not start <= position < end
        assert set(pair["forward"] + pair["reverse"]) <= set("ACGT")


@pytest.mark.parametrize("config", [
    {"global_arg": {}},
    {"sequence_args": []},
    {"global_args": {"PRIMER_MIN_TMM": 57}},
    {"sequence_args": {"SEQUENCE_TARGET": [[490, 30]]}},
    {"sequence_args": {"SEQUENCE_TARGET": [[-1, 10]]}},
    {"sequence_args": {"SEQUENCE_EXCLUDED_REGION": [[10, 0]]}},
    {"sequence_args": {"SEQUENCE_INCLUDED_REGION": [False, 100]}},
    {"sequence_args": {"SEQUENCE_QUALITY": [20]}},
    {"global_args": {"PRIMER_NUM_RETURN": True}},
    {"global_args": {"PRIMER_NUM_RETURN": 0}},
    {"global_args": {"PRIMER_MIN_SIZE": 26}},
    {"global_args": {"PRIMER_MIN_TM": 70}},
    {"global_args": {"PRIMER_DNA_CONC": 0}},
    {"global_args": {"PRIMER_DNA_CONC": float("nan")}},
    {"global_args": {"PRIMER_MAX_NS_ACCEPTED": 1}},
    {"global_args": {"PRIMER_PRODUCT_SIZE_RANGE": [[200, 100]]}},
    {"global_args": {"PRIMER_TM_FORMULA": 42}},
    {"global_args": {"PRIMER_SALT_CORRECTIONS": 42}},
])
def test_invalid_configuration_is_an_error_not_no_candidates(tmp_path, config):
    result, report = design(tmp_path, config)
    assert result.returncode == 2, result.stderr
    assert "error:" in result.stderr and "Traceback" not in result.stderr
    assert report is None


def test_no_candidates_is_an_explicit_scientific_result(tmp_path):
    fasta = tmp_path / "poly-a.fasta"
    fasta.write_text(">no_suitable_primers\n" + "A" * 500 + "\n")
    result, report = design(tmp_path, template=fasta)
    assert result.returncode == 1, result.stderr
    assert report["status"] == "no_candidates" and report["pairs"] == []
    assert report["engine_explanations"]
    assert "error:" not in result.stderr


def test_multiple_fasta_records_require_explicit_selection(tmp_path):
    fasta = tmp_path / "multiple.fasta"
    fasta.write_text(">first\n" + demo_sequence() + "\n>second\n" + "A" * 500 + "\n")
    result, report = design(tmp_path, template=fasta)
    assert result.returncode == 2 and report is None
    result, report = design(tmp_path, template=fasta, extra=["--record", "first"], name="selected")
    assert result.returncode == 0, result.stderr
    assert report["provenance"]["record_id"] == "first"


def assert_structure_matches(observed, expected):
    assert observed["structure_found"] == bool(expected.structure_found)
    assert observed["tm_c"] == pytest.approx(expected.tm)
    assert observed["delta_g_kcal_per_mol"] == pytest.approx(expected.dg / 1000)
    assert observed["delta_h_kcal_per_mol"] == pytest.approx(expected.dh / 1000)
    assert observed["delta_s_cal_per_mol_k"] == pytest.approx(expected.ds)


def test_thermodynamics_uses_explicit_chemistry_and_both_3prime_directions(tmp_path, ordinary_pair):
    result, report = assess(tmp_path, [ordinary_pair], extra=[
        "--mv-conc", "62", "--dv-conc", "2", "--dntp-conc", "0.8",
        "--dna-conc", "175", "--temp-c", "55",
    ])
    assert result.returncode == 0, result.stderr
    chemistry = {"mv_conc": 62, "dv_conc": 2, "dntp_conc": .8, "dna_conc": 175}
    structures = {**chemistry, "temp_c": 55}
    forward, reverse = ordinary_pair["forward"], ordinary_pair["reverse"]
    for entry in report["oligos"]:
        sequence = entry["annealing_core"]
        assert entry["annealing_tm_c"] == pytest.approx(primer3.calc_tm(sequence, **chemistry))
        assert_structure_matches(entry["full_hairpin"], primer3.calc_hairpin(sequence, **structures))
        assert_structure_matches(entry["full_homodimer"], primer3.calc_homodimer(sequence, **structures))
    interaction, = report["interactions"]
    assert_structure_matches(interaction["heterodimer"], primer3.calc_heterodimer(forward, reverse, **structures))
    assert_structure_matches(interaction["a_three_prime_to_b"], primer3.calc_end_stability(forward, reverse, **structures))
    assert_structure_matches(interaction["b_three_prime_to_a"], primer3.calc_end_stability(reverse, forward, **structures))
    assert interaction["a_three_prime_to_b"]["delta_g_kcal_per_mol"] != pytest.approx(
        interaction["b_three_prime_to_a"]["delta_g_kcal_per_mol"])
    result, changed = assess(tmp_path, [ordinary_pair], extra=["--mv-conc", "5"], name="different-chemistry")
    assert result.returncode == 0, result.stderr
    assert changed["oligos"][0]["annealing_tm_c"] != pytest.approx(report["oligos"][0]["annealing_tm_c"])


def test_tail_is_excluded_from_tm_but_included_in_structures(tmp_path, ordinary_pair):
    tailed = {**ordinary_pair, "forward_tail": reverse_complement(ordinary_pair["forward"])}
    result, report = assess(tmp_path, [tailed])
    assert result.returncode == 0, result.stderr
    forward = report["oligos"][0]
    full = tailed["forward_tail"] + tailed["forward"]
    assert forward["order_sequence"] == full
    assert forward["annealing_tm_c"] == pytest.approx(primer3.calc_tm(tailed["forward"]))
    assert_structure_matches(forward["full_hairpin"], primer3.calc_hairpin(full))
    assert_structure_matches(forward["full_homodimer"], primer3.calc_homodimer(full))
    assert_structure_matches(forward["full_self_three_prime"], primer3.calc_end_stability(full, full))
    assert_structure_matches(forward["core_self_three_prime"], primer3.calc_end_stability(tailed["forward"], tailed["forward"]))
    assert forward["full_hairpin"]["tm_c"] != pytest.approx(forward["core_hairpin"]["tm_c"])
    assert_structure_matches(report["interactions"][0]["heterodimer"], primer3.calc_heterodimer(full, tailed["reverse"]))


def test_temperature_changes_free_energy_not_core_tm(tmp_path, ordinary_pair):
    results = []
    for temperature in (20, 55):
        result, report = assess(tmp_path, [ordinary_pair], extra=["--temp-c", str(temperature)],
                                name=f"temperature-{temperature}")
        assert result.returncode == 0, result.stderr
        structure = report["interactions"][0]["heterodimer"]
        assert structure["structure_found"]
        # Independent dimensional/thermodynamic consistency, including kcal conversion.
        assert structure["delta_g_kcal_per_mol"] == pytest.approx(
            structure["delta_h_kcal_per_mol"] -
            (temperature + 273.15) * structure["delta_s_cal_per_mol_k"] / 1000
        )
        results.append(report)
    assert results[0]["oligos"][0]["annealing_tm_c"] == pytest.approx(
        results[1]["oligos"][0]["annealing_tm_c"])
    assert results[0]["interactions"][0]["heterodimer"]["delta_g_kcal_per_mol"] != pytest.approx(
        results[1]["interactions"][0]["heterodimer"]["delta_g_kcal_per_mol"])


@pytest.mark.parametrize("extra", [
    ["--mv-conc", "0", "--dv-conc", "0", "--dntp-conc", "0"],
    ["--mv-conc", "0", "--dv-conc", "1.5", "--dntp-conc", "1.5"],
    ["--dna-conc", "1e300"],
])
def test_finite_but_physically_invalid_native_tm_is_not_accepted(tmp_path, ordinary_pair, extra):
    result, report = assess(tmp_path, [ordinary_pair], extra=extra)
    assert result.returncode == 2 and report is None
    assert "invalid core Tm" in result.stderr
    assert "Traceback" not in result.stderr


def test_multiplex_computes_all_distinct_oligo_pairs(tmp_path, ordinary_pair):
    rows = [ordinary_pair, {"pair_id": "beta", "forward": "CCCCCATCCGATCAGGGGG", "reverse": "TCCTACTAGCATGGCGTATA"}]
    result, report = assess(tmp_path, rows, extra=["--multiplex"])
    assert result.returncode == 0, result.stderr
    ids = ["alpha:forward", "alpha:reverse", "beta:forward", "beta:reverse"]
    assert {(row["oligo_a"], row["oligo_b"]) for row in report["interactions"]} == set(itertools.combinations(ids, 2))
    assert sum(row["cross_pair"] for row in report["interactions"]) == 4
    assert all(row["status"] == "computed" for row in report["interactions"])
    result, capped = assess(tmp_path, rows, extra=["--multiplex", "--max-interactions", "5"], name="capped")
    assert result.returncode == 2 and capped is None
    assert "6 dimer comparisons" in result.stderr


def test_unsupported_full_length_preserves_core_and_marks_report_incomplete(tmp_path, ordinary_pair):
    tailed = {**ordinary_pair, "forward_tail": "A" * 61}
    result, report = assess(tmp_path, [tailed])
    assert result.returncode == 1, result.stderr
    assert report["status"] == "incomplete"
    forward = report["oligos"][0]
    assert forward["order_sequence"] == tailed["forward_tail"] + tailed["forward"]
    assert forward["annealing_tm_c"] == pytest.approx(primer3.calc_tm(ordinary_pair["forward"]))
    assert forward["full_oligo_status"] == "unsupported_length"
    assert "full_hairpin" not in forward and "full_homodimer" not in forward
    assert report["interactions"][0]["status"] == "unsupported_length"
    assert report["warnings"]


@pytest.mark.parametrize("change", [
    {"forward": "ACGTNACGT"}, {"reverse": "ACGUACGU"},
    {"forward": "A"}, {"forward_tail": "[FAM]"}, {"pair_id": "duplicate:name"},
])
def test_invalid_oligos_are_rejected_without_partial_reports(tmp_path, ordinary_pair, change):
    result, report = assess(tmp_path, [{**ordinary_pair, **change}])
    assert result.returncode == 2 and report is None
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("extra", [["--dna-conc", "nan"], ["--mv-conc", "-1"], ["--temp-c", "101"]])
def test_invalid_chemistry_is_rejected(tmp_path, ordinary_pair, extra):
    result, report = assess(tmp_path, [ordinary_pair], extra=extra)
    assert result.returncode == 2 and report is None


def test_output_collisions_preserve_inputs(tmp_path, ordinary_pair):
    pairs = write_pairs(tmp_path, [ordinary_pair])
    original_pairs = pairs.read_bytes()
    result = run_script("check_thermodynamics.py", "--pairs", pairs, "--output", pairs)
    assert result.returncode == 2 and pairs.read_bytes() == original_pairs
    template = tmp_path / "template.fasta"
    template.write_text(">target\n" + demo_sequence() + "\n")
    original_template = template.read_bytes()
    alias = tmp_path / "alias.fasta"
    alias.symlink_to(template)
    result = run_script("design_primers.py", "--template", template, "--output", alias)
    assert result.returncode == 2 and template.read_bytes() == original_template
    output = tmp_path / "result.json"
    result = run_script("design_primers.py", "--template", template, "--output", output, "--pairs-out", output)
    assert result.returncode == 2 and not output.exists()
    hardlink = tmp_path / "hardlink.tsv"
    hardlink.hardlink_to(template)
    result = run_script("design_primers.py", "--template", template, "--output", output, "--pairs-out", hardlink)
    assert result.returncode == 2 and template.read_bytes() == original_template
