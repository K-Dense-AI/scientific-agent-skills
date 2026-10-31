"""Scientific failure cases and genuine offline BLAST integration for primer screens."""

from __future__ import annotations

import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "primer-design"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from _common import revcomp
from _specificity import SearchIncomplete, expand_panel_pairs, run_tool, score_window
from screen_specificity import build_parser, main, run


F = "ACGTTGCACTGATCGTACGA"
R = "TGCAGATCGACCTAGTCAGC"
SPACER = "".join(random.Random(1729).choices("ACGT", k=80))
TARGET = F + SPACER + revcomp(R)


def inputs(tmp_path, references=None, expected=True, forward=F, reverse=R, tails=None):
    pairs = tmp_path / "pairs.tsv"
    header = "pair_id\tforward\treverse"
    values = f"p1\t{forward}\t{reverse}"
    if tails:
        header += "\tforward_tail\treverse_tail"
        values += "\t" + "\t".join(tails)
    pairs.write_text(header + "\n" + values + "\n")
    reference = tmp_path / "reference.fa"
    references = references or {"target": TARGET}
    reference.write_text("".join(f">{key}\n{value}\n" for key, value in references.items()))
    args = ["--pairs", str(pairs), "--reference", str(reference), "--output", str(tmp_path / "screen.json"),
            "--max-mismatches", "0"]
    if expected:
        expected_path = tmp_path / "expected.tsv"
        expected_path.write_text("pair_id\trecord_id\tstart\tend\np1\ttarget\t0\t120\n")
        args += ["--expected", str(expected_path)]
    return args


def execute(arguments):
    return run(build_parser().parse_args(arguments))


def test_exact_intended_product_and_provenance(tmp_path):
    report, code = execute(inputs(tmp_path))
    assert code == 0
    assert report["complete_within_model"] and report["exhaustive"]
    pair = report["pairs"][0]
    assert pair["status"] == "no_off_target_found_within_search_scope"
    assert pair["hit_count"] == 2
    product, = pair["products"]
    assert (product["start"], product["end"], product["length"]) == (0, 120, 120)
    assert product["primer_roles"] == "F/R"
    assert product["classification"] == "intended"
    assert {h["strand"] for h in pair["hits"]} == {"+", "-"}
    assert len(report["provenance"]["reference"]["sha256"]) == 64
    assert len(report["provenance"]["expected"]["sha256"]) == 64


def test_unintended_second_amplicon_rejected(tmp_path):
    report, code = execute(inputs(tmp_path, {"target": TARGET, "paralog": TARGET}))
    assert code == 0
    assert report["status"] == "potential_off_target"
    pair = report["pairs"][0]
    assert pair["potential_off_target_count"] == 1
    assert {p["classification"] for p in pair["products"]} == {"intended", "potential_off_target"}


@pytest.mark.parametrize("primer,kind", [(F, "F/F"), (R, "R/R")])
def test_same_primer_products_are_reported(tmp_path, primer, kind):
    references = {"target": TARGET, "single_primer": primer + SPACER + revcomp(primer)}
    report, code = execute(inputs(tmp_path, references))
    assert code == 0
    assert report["status"] == "potential_off_target"
    product, = [p for p in report["pairs"][0]["products"] if p["record_id"] == "single_primer"]
    assert product["primer_roles"] == kind


def test_reverse_orientation_pair(tmp_path):
    report, code = execute(inputs(tmp_path, {"target": R + SPACER + revcomp(F)}))
    assert code == 0
    product, = report["pairs"][0]["products"]
    assert product["primer_roles"] == "R/F"
    assert product["classification"] == "intended"


@pytest.mark.parametrize("strand", ["+", "-"])
def test_terminal_mismatch_is_strand_correct(tmp_path, strand):
    f = F[:-1] + "C" if strand == "+" else F
    r = R[:-1] + "A" if strand == "-" else R
    args = inputs(tmp_path, {"target": f + SPACER + revcomp(r)})
    args += ["--max-mismatches", "1"]
    strict, _ = execute(args)
    assert strict["status"] == "intended_target_not_found"
    permissive, _ = execute(args + ["--max-three-prime-mismatches", "1"])
    assert permissive["status"] == "no_off_target_found_within_search_scope"
    hit, = [h for h in permissive["pairs"][0]["hits"] if h["strand"] == strand]
    assert hit["mismatch_positions_1based"] == [20]
    assert hit["mismatch_positions_from_three_prime_1based"] == [1]
    assert hit["three_prime_mismatches"] == 1


def test_five_prime_mismatch_is_not_a_three_prime_mismatch(tmp_path):
    args = inputs(tmp_path, {"target": "T" + TARGET[1:]})
    report, _ = execute(args + ["--max-mismatches", "1"])
    assert report["status"] == "no_off_target_found_within_search_scope"
    hit, = [h for h in report["pairs"][0]["hits"] if h["strand"] == "+"]
    assert hit["mismatch_positions_1based"] == [1]
    assert hit["three_prime_mismatches"] == 0


def test_ambiguous_reference_is_conservative_and_unresolved(tmp_path):
    args = inputs(tmp_path, {"target": F[:-1] + "N" + SPACER + revcomp(R)})
    report, code = execute(args)
    assert code == 2
    assert report["status"] == "incomplete"
    assert not report["complete_within_model"]
    pair = report["pairs"][0]
    assert pair["status_before_incomplete"] == "no_off_target_found_within_search_scope"
    assert pair["unresolved_ambiguity"]
    assert pair["products"][0]["unresolved_ambiguity"]
    hit, = [h for h in pair["hits"] if h["strand"] == "+"]
    assert hit["mismatches"] == 0
    assert hit["mismatches_upper_bound"] == 1
    assert hit["three_prime_mismatches_upper_bound"] == 1
    assert hit["ambiguous_positions_from_three_prime_1based"] == [1]


def test_ambiguous_off_target_retains_evidence_and_marks_incomplete(tmp_path):
    off = F[:-1] + "N" + SPACER + revcomp(R)
    report, code = execute(inputs(tmp_path, {"target": TARGET, "ambiguous_alternative": off}))
    assert code == 2 and report["status"] == "incomplete"
    assert not report["complete_within_model"]
    pair = report["pairs"][0]
    assert pair["status_before_incomplete"] == "potential_off_target"
    assert pair["potential_off_target_count"] == 1
    assert any(p["classification"] == "potential_off_target" and p["unresolved_ambiguity"] for p in pair["products"])


def test_nonbinding_internal_ambiguity_does_not_suppress_screen(tmp_path):
    sequence = F + SPACER[:40] + "N" + SPACER[41:] + revcomp(R)
    report, code = execute(inputs(tmp_path, {"target": sequence}))
    assert code == 0
    assert report["status"] == "no_off_target_found_within_search_scope"
    assert report["complete_within_model"]
    assert report["provenance"]["reference"]["ambiguous_base_count"] == 1


def test_incompatible_iupac_base_counts_as_definite_mismatch():
    settings = {"three_prime_bases": 1, "max_mismatches": 0, "max_three_prime_mismatches": 0}
    assert score_window("A", "Y", "+", settings) is None
    assert score_window("A", "R", "+", settings)["unresolved_ambiguity"]


def test_no_expected_target_never_claims_specificity(tmp_path):
    report, code = execute(inputs(tmp_path, expected=False))
    assert code == 0
    assert report["status"] == "no_expected_target"
    assert report["pairs"][0]["products"][0]["classification"] == "unclassified"


def test_missing_expected_interval_is_reported_even_with_another_product(tmp_path):
    args = inputs(tmp_path)
    (tmp_path / "expected.tsv").write_text("pair_id\trecord_id\tstart\tend\np1\ttarget\t1\t120\n")
    report, code = execute(args)
    assert code == 0
    assert report["status"] == "intended_target_not_found"
    assert report["pairs"][0]["missing_expected"] == [{"record_id": "target", "start": 1, "end": 120}]
    assert report["pairs"][0]["potential_off_target_count"] == 1


def test_all_declared_intended_products_must_be_found(tmp_path):
    args = inputs(tmp_path, {"target": TARGET, "isoform": "A" * 120})
    with (tmp_path / "expected.tsv").open("a") as handle:
        handle.write("p1\tisoform\t0\t120\n")
    report, _ = execute(args)
    assert report["status"] == "intended_target_not_found"
    assert len(report["pairs"][0]["missing_expected"]) == 1


def test_overlapping_sites_do_not_form_product(tmp_path):
    sequence = F + "AGTCAGTCGA"
    reverse = revcomp(sequence[10:])
    args = inputs(tmp_path, {"target": sequence}, expected=False, reverse=reverse)
    report, code = execute(args + ["--min-product", "1"])
    assert code == 0
    assert report["pairs"][0]["product_count"] == 0
    assert report["pairs"][0]["hit_count"] == 2


def test_circular_product_across_origin(tmp_path):
    sequence = SPACER[:30] + revcomp(R) + SPACER[30:60] + F
    args = inputs(tmp_path, {"target": sequence})
    (tmp_path / "expected.tsv").write_text("pair_id\trecord_id\tstart\tend\np1\ttarget\t80\t150\n")
    report, code = execute(args + ["--circular", "target"])
    assert code == 0
    product, = report["pairs"][0]["products"]
    assert (product["start"], product["end"], product["length"]) == (80, 150, 70)
    assert product["wraps_origin"]
    assert product["classification"] == "intended"


def test_circular_binding_site_can_cross_origin(tmp_path):
    sequence = TARGET[10:] + TARGET[:10]
    args = inputs(tmp_path, {"target": sequence})
    (tmp_path / "expected.tsv").write_text("pair_id\trecord_id\tstart\tend\np1\ttarget\t110\t230\n")
    report, code = execute(args + ["--circular", "target"])
    assert code == 0
    assert report["pairs"][0]["products"][0]["length"] == 120
    assert any(h["wraps_origin"] for h in report["pairs"][0]["hits"])


def test_tails_affect_product_length_but_not_binding(tmp_path):
    report, code = execute(inputs(tmp_path, tails=("GCGC", "ATATAT")))
    assert code == 0
    product, = report["pairs"][0]["products"]
    assert (product["length"], product["length_with_tails"]) == (120, 130)


@pytest.mark.parametrize("limit", ["--max-comparisons", "--max-hits"])
def test_resource_caps_fail_closed(tmp_path, limit):
    report, code = execute(inputs(tmp_path) + [limit, "1"])
    assert code == 2
    assert report["status"] == "incomplete"
    assert not report["complete_within_model"]
    assert report["issues"]


def test_product_cap_discards_completed_claim(tmp_path):
    report, code = execute(inputs(tmp_path, {"target": TARGET, "offtarget": TARGET}) + ["--max-products", "1"])
    assert code == 2 and report["status"] == "incomplete"


@pytest.mark.parametrize("extra", [
    ["--max-mismatches", "-1"], ["--min-product", "200", "--max-product", "100"],
    ["--three-prime-bases", "21"], ["--circular", "missing"],
])
def test_invalid_settings_fail_closed(tmp_path, extra):
    report, code = execute(inputs(tmp_path) + extra)
    assert code == 2 and report["status"] == "incomplete"


def test_unknown_expected_reference_fails_closed(tmp_path):
    args = inputs(tmp_path)
    (tmp_path / "expected.tsv").write_text("pair_id\trecord_id\tstart\tend\np1\tmissing\t0\t120\n")
    report, code = execute(args)
    assert code == 2 and report["status"] == "incomplete"


def test_cli_writes_failure_report(tmp_path):
    code = main(inputs(tmp_path) + ["--max-comparisons", "1"])
    assert code == 2
    report = json.loads((tmp_path / "screen.json").read_text())
    assert report["status"] == "incomplete"


def test_output_cannot_replace_input(tmp_path):
    args = inputs(tmp_path)
    original = (tmp_path / "pairs.tsv").read_text()
    assert main(args + ["--output", str(tmp_path / "pairs.tsv")]) == 2
    assert (tmp_path / "pairs.tsv").read_text() == original


def test_tool_failure_and_timeout_fail_closed(monkeypatch):
    def failure(*args, **kwargs):
        raise subprocess.CalledProcessError(3, args[0], stderr="fixture failure")
    monkeypatch.setattr(subprocess, "run", failure)
    with pytest.raises(SearchIncomplete, match="exit 3"):
        run_tool(["fake-blastn", "-version"], 1)
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 1)
    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(SearchIncomplete, match="timed out"):
        run_tool(["fake-blastn", "-version"], 1)


HAS_BLAST = bool(shutil.which("blastn") and shutil.which("makeblastdb"))


@pytest.mark.skipif(not HAS_BLAST, reason="Requires local NCBI BLAST+ executables")
def test_real_blast_finds_intended_and_second_product(tmp_path):
    report, code = execute(inputs(tmp_path, {"target": TARGET, "paralog": TARGET}) + ["--engine", "blast"])
    assert code == 0, report["issues"]
    assert report["status"] == "potential_off_target"
    assert not report["exhaustive"] and not report["complete_within_model"]
    assert report["discovery_completed"]
    assert report["pairs"][0]["product_count"] == 2
    assert "blastn:" in report["provenance"]["tools"]["blastn"]["version"]


@pytest.mark.skipif(not HAS_BLAST, reason="Requires local NCBI BLAST+ executables")
def test_real_blast_rechecks_clipped_three_prime_mismatch(tmp_path):
    off = F[:-1] + "C" + SPACER + revcomp(R)
    args = inputs(tmp_path, {"target": TARGET, "clipped_mismatch": off}) + ["--engine", "blast", "--max-mismatches", "1"]
    strict, code = execute(args)
    assert code == 0, strict["issues"]
    assert strict["pairs"][0]["potential_off_target_count"] == 0
    permissive, code = execute(args + ["--max-three-prime-mismatches", "1"])
    assert code == 0, permissive["issues"]
    assert permissive["pairs"][0]["potential_off_target_count"] == 1


@pytest.mark.skipif(not HAS_BLAST, reason="Requires local NCBI BLAST+ executables")
def test_real_blast_rechecks_clipped_reverse_primer(tmp_path):
    off = F + SPACER + revcomp(R[:-1] + "A")
    args = inputs(tmp_path, {"target": TARGET, "clipped_reverse": off}) + ["--engine", "blast", "--max-mismatches", "1"]
    strict, code = execute(args)
    assert code == 0, strict["issues"]
    assert strict["pairs"][0]["potential_off_target_count"] == 0
    permissive, code = execute(args + ["--max-three-prime-mismatches", "1"])
    assert code == 0, permissive["issues"]
    assert permissive["pairs"][0]["potential_off_target_count"] == 1


@pytest.mark.skipif(not HAS_BLAST, reason="Requires local NCBI BLAST+ executables")
def test_real_blast_hsp_limit_fails_closed(tmp_path):
    args = inputs(tmp_path, {"target": TARGET + "A" * 30 + TARGET})
    report, code = execute(args + ["--engine", "blast", "--blast-max-hsps", "1"])
    assert code == 2
    assert report["status"] == "incomplete"
    assert any("max_hsps" in issue for issue in report["issues"])


@pytest.mark.skipif(not HAS_BLAST, reason="Requires local NCBI BLAST+ executables")
def test_real_blast_target_limit_fails_closed(tmp_path):
    args = inputs(tmp_path, {"target": TARGET, "paralog": TARGET})
    report, code = execute(args + ["--engine", "blast", "--blast-max-target-seqs", "1"])
    assert code == 2
    assert report["status"] == "incomplete"
    assert any("max_target_seqs" in issue for issue in report["issues"])


@pytest.mark.skipif(not HAS_BLAST, reason="Requires local NCBI BLAST+ executables")
def test_real_blast_circular_binding_and_product(tmp_path):
    sequence = TARGET[10:] + TARGET[:10]
    args = inputs(tmp_path, {"target": sequence})
    (tmp_path / "expected.tsv").write_text("pair_id\trecord_id\tstart\tend\np1\ttarget\t110\t230\n")
    report, code = execute(args + ["--engine", "blast", "--circular", "target"])
    assert code == 0, report["issues"]
    assert report["pairs"][0]["products"][0]["classification"] == "intended"


@pytest.mark.parametrize("engine", ["exhaustive", pytest.param("blast", marks=pytest.mark.skipif(
    not HAS_BLAST, reason="Requires local NCBI BLAST+ executables"))])
def test_reference_reverse_complement_preserves_product_and_swaps_roles(tmp_path, engine):
    # Unequal flanks ensure the transformed interval cannot accidentally match itself.
    sequence = "AAAAAAA" + TARGET + "CCCCCCCCCCCCC"
    length = len(sequence)
    args = inputs(tmp_path, {"target": sequence}) + ["--engine", engine]
    expected_path = tmp_path / "expected.tsv"
    expected_path.write_text("pair_id\trecord_id\tstart\tend\np1\ttarget\t7\t127\n")
    original, code = execute(args)
    assert code == 0, original["issues"]
    (tmp_path / "reference.fa").write_text(f">target\n{revcomp(sequence)}\n")
    expected_path.write_text(
        f"pair_id\trecord_id\tstart\tend\np1\ttarget\t{length - 127}\t{length - 7}\n")
    transformed, code = execute(args)
    assert code == 0, transformed["issues"]
    before, = original["pairs"][0]["products"]
    after, = transformed["pairs"][0]["products"]
    assert after["start"] == length - before["end"]
    assert after["end"] == length - before["start"]
    assert after["length"] == before["length"] == 120
    assert (before["primer_roles"], after["primer_roles"]) == ("F/R", "R/F")
    assert before["classification"] == after["classification"] == "intended"


def test_missing_blast_executable_fails_closed(tmp_path):
    report, code = execute(inputs(tmp_path) + ["--engine", "blast", "--blastn", "nonexistent-primer-test-blastn"])
    assert code == 2
    assert report["status"] == "incomplete"


F2 = "GATCCAGTTCGACGATGTCA"
R2 = "CGTAGCTACCGTATGACGTC"


def panel_inputs(tmp_path, cross_roles=None):
    references = {"target": TARGET, "target2": F2 + SPACER + revcomp(R2)}
    if cross_roles:
        second = F2 if cross_roles == "F/F" else R2
        references["cross_product"] = F + SPACER + revcomp(second)
    args = inputs(tmp_path, references, tails=("AAA", "CCC"))
    with (tmp_path / "pairs.tsv").open("a") as handle:
        handle.write(f"p2\t{F2}\t{R2}\tGGG\tTTT\n")
    with (tmp_path / "expected.tsv").open("a") as handle:
        handle.write("p2\ttarget2\t0\t120\n")
    return args


@pytest.mark.parametrize("cross_roles", ["F/F", "F/R"])
def test_multiplex_detects_cross_product_despite_individually_clean_pairs(tmp_path, cross_roles):
    args = panel_inputs(tmp_path, cross_roles)
    individual, code = execute(args)
    assert code == 0 and individual["status"] == "no_off_target_found_within_search_scope"
    report, code = execute(args + ["--multiplex"])
    assert code == 0 and report["status"] == "potential_off_target"
    originals = [pair for pair in report["pairs"] if not pair["cross_pair"]]
    assert originals == individual["pairs"]
    generated = [pair for pair in report["pairs"] if pair["cross_pair"]]
    assert len(generated) == 4
    cross_pair, = [pair for pair in generated if pair["product_count"]]
    product, = cross_pair["products"]
    assert product["classification"] == "potential_off_target"
    assert product["source_primer_roles"] == cross_roles
    assert product["left_source_oligo_id"] == "p1:F"
    assert product["right_source_oligo_id"] == "p2:" + cross_roles[-1]
    assert product["cross_pair"]
    assert product["length_with_tails"] == 126
    assert cross_pair["source_oligos"]["F"]["tail_5prime"] == "AAA"
    assert cross_pair["source_oligos"]["R"]["tail_5prime"] == ("GGG" if cross_roles == "F/F" else "TTT")
    assert all(pair["status"] != "no_expected_target" for pair in generated)


def test_multiplex_with_no_cross_products_has_scoped_clear_result(tmp_path):
    report, code = execute(panel_inputs(tmp_path) + ["--multiplex"])
    assert code == 0 and report["status"] == "no_off_target_found_within_search_scope"
    assert len(report["pairs"]) == 6
    assert all(pair["product_count"] == 0 for pair in report["pairs"] if pair["cross_pair"])
    assert report["provenance"]["panel"]["cross_pair_count"] == 4


def test_multiplex_still_requires_original_expected_targets(tmp_path):
    args = panel_inputs(tmp_path)
    (tmp_path / "expected.tsv").write_text("pair_id\trecord_id\tstart\tend\np1\ttarget\t0\t120\n")
    report, code = execute(args + ["--multiplex"])
    assert code == 0 and report["status"] == "no_expected_target"
    assert next(pair for pair in report["pairs"] if pair["pair_id"] == "p2")["status"] == "no_expected_target"


def test_expected_manifest_cannot_whitelist_generated_cross_pairs(tmp_path):
    args = panel_inputs(tmp_path, "F/F")
    with (tmp_path / "expected.tsv").open("a") as handle:
        handle.write("multiplex-cross-000001\tcross_product\t0\t120\n")
    report, code = execute(args + ["--multiplex"])
    assert code == 2 and report["status"] == "incomplete"
    assert "Unknown pair_id" in report["issues"][0]


def test_multiplex_combination_cap_fails_before_search(tmp_path, monkeypatch):
    import screen_specificity
    def unexpected_search(*args, **kwargs):
        raise AssertionError("Binding search must not begin after panel cap exceeded")
    monkeypatch.setattr(screen_specificity, "exhaustive_hits", unexpected_search)
    report, code = execute(panel_inputs(tmp_path) + ["--multiplex", "--max-panel-combinations", "3"])
    assert code == 2 and report["status"] == "incomplete"
    assert "4 cross-oligo combinations" in report["issues"][0]
    assert not report["pairs"]


def test_multiplex_uses_single_deduplicated_binding_search(tmp_path, monkeypatch):
    import screen_specificity
    original = screen_specificity.exhaustive_hits
    searches = []
    def counting_search(primers, *args, **kwargs):
        searches.append(tuple(primers))
        return original(primers, *args, **kwargs)
    monkeypatch.setattr(screen_specificity, "exhaustive_hits", counting_search)
    report, code = execute(panel_inputs(tmp_path, "F/R") + ["--multiplex"])
    assert code == 0
    assert len(searches) == 1
    assert set(searches[0]) == {F, R, F2, R2}
    assert report["provenance"]["panel"]["unique_annealing_cores_searched"] == 4


def test_panel_expansion_is_deterministic_collision_safe_and_does_not_mutate():
    originals = [
        {"pair_id": "multiplex-cross-000001", "forward": F, "reverse": R},
        {"pair_id": "p2", "forward": F2, "reverse": R2},
    ]
    before = json.dumps(originals, sort_keys=True)
    first = expand_panel_pairs(originals, 4)
    second = expand_panel_pairs(list(reversed(originals)), 4)
    assert json.dumps(originals, sort_keys=True) == before
    assert first[2:] == second[2:]
    assert len({pair["pair_id"] for pair in first}) == 6


def test_specificity_output_cannot_replace_hardlinked_input(tmp_path):
    args = inputs(tmp_path)
    original = (tmp_path / "pairs.tsv").read_text()
    alias = tmp_path / "alias.json"
    alias.hardlink_to(tmp_path / "pairs.tsv")
    assert main(args + ["--output", str(alias)]) == 2
    assert (tmp_path / "pairs.tsv").read_text() == original
    assert alias.read_text() == original
