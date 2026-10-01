from pathlib import Path
import csv
import importlib.util
import math
import random
import shutil
import subprocess

import pytest
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "mageck"
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)
spec = importlib.util.spec_from_file_location("screen_analysis", SKILL_ROOT / "scripts" / "screen_analysis.py")
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)


@pytest.fixture
def counts(tmp_path):
    rng = random.Random(17)
    path = tmp_path / "counts.tsv"
    with path.open("w") as handle:
        handle.write("sgRNA\tGene\tc1\tc2\tt1\tt2\n")
        for gene in range(100):
            for guide in range(5):
                baseline = rng.randint(600, 1800)
                fold = .015 if gene == 0 else 30 if gene == 1 else 1
                values = [round(baseline * rng.uniform(.85, 1.15)) for _ in range(2)]
                values += [round(baseline * fold * rng.uniform(.85, 1.15)) for _ in range(2)]
                handle.write(f"g{gene}_{guide}\tGENE{gene}\t" + "\t".join(map(str, values)) + "\n")
    return path


def test_qc_replicates_and_missing_sample(counts):
    qc = screen.inspect_screen(counts, ["c1", "c2"], ["t1", "t2"])
    assert qc["guides"] == 500
    assert all(c > .9 for c in qc["within_condition_log2_count_correlations"].values())
    assert qc["samples"]["c1"]["zero_fraction"] == 0
    with pytest.raises(ValueError, match="Unknown sample"):
        screen.inspect_screen(counts, ["wrong"], ["t1"])
    with pytest.raises(ValueError, match="equal counts"):
        screen.inspect_screen(counts, ["c1", "c2"], ["t1"], paired=True)


def test_invalid_counts_library_and_controls(counts, tmp_path):
    bad = tmp_path / "bad.tsv"
    bad.write_text("sgRNA\tGene\ta\tb\nx\tX\t-1\t3\n")
    with pytest.raises(ValueError, match="negative"):
        screen.read_counts(bad)
    library = tmp_path / "library.tsv"
    library.write_text("x\tAAAA\tX\ny\tAAAA\tY\n")
    with pytest.raises(ValueError, match="ambiguous"):
        screen.read_library(library)
    controls = tmp_path / "controls.txt"
    controls.write_text("missing\n")
    with pytest.raises(ValueError, match="known IDs"):
        screen.inspect_screen(counts, ["c1"], ["t1"], controls_path=controls)
    with pytest.raises(ValueError, match="requires control"):
        screen.run_test(counts, tmp_path / "out", ["c1"], ["t1"], normalization="control")


@pytest.mark.skipif(shutil.which("mageck") is None, reason="MAGeCK 0.5.9.5 and RRA are external source/conda executables")
@pytest.mark.parametrize("paired", [False, True])
def test_real_mageck_ranks_known_signals(counts, tmp_path, paired):
    report = screen.run_test(counts, tmp_path / "results", ["c1", "c2"], ["t1", "t2"], paired=paired)
    negative = sorted(report["hits"]["neg"], key=lambda r: r["rank"])
    positive = sorted(report["hits"]["pos"], key=lambda r: r["rank"])
    assert negative[0]["gene"] == "GENE0" and negative[0]["lfc"] < -4
    assert positive[0]["gene"] == "GENE1" and positive[0]["lfc"] > 4
    assert (tmp_path / "results" / "screen.sgrna_summary.txt").is_file()
    assert report["normalization"]["effective_method"] == "median"
    assert list(report["normalization"]["sample_size_factors"]) == ["c1", "c2", "t1", "t2"]


@pytest.mark.skipif(shutil.which("mageck") is None, reason="MAGeCK is an external source/conda executable")
def test_real_fastq_counting(tmp_path):
    sequences = {"g1": "ACGTACGTACGTACGTACGT", "g2": "TTTTCCCCAAAAGGGGTTTT"}
    library = tmp_path / "library.tsv"
    library.write_text("\n".join(f"{g}\t{s}\tGENE{i}" for i, (g, s) in enumerate(sequences.items())) + "\n")
    fastq = tmp_path / "reads.fastq"
    reads = [sequences["g1"]] * 30 + [sequences["g2"]] * 12
    fastq.write_text("".join(f"@r{i}\n{seq}\n+\n{'I' * 20}\n" for i, seq in enumerate(reads)))
    subprocess.run(["mageck", "count", "-l", "library.tsv", "--fastq", "reads.fastq", "--sample-label", "sample", "--trim-5", "0", "--norm-method", "none", "-n", "counted"], cwd=tmp_path, check=True, capture_output=True, text=True)
    with (tmp_path / "counted.count.txt").open() as handle:
        output = list(csv.DictReader(handle, delimiter="\t"))
    assert {row["sgRNA"]: int(row["sample"]) for row in output} == {"g1": 30, "g2": 12}


@pytest.mark.skipif(shutil.which("mageck") is None, reason="MAGeCK is an external source/conda executable")
def test_control_normalization_retains_control_provenance(counts, tmp_path):
    import hashlib
    controls = tmp_path / "negative-guides.txt"
    controls.write_text("".join(f"g{gene}_{guide}\n" for gene in range(2, 22) for guide in range(5)))
    report = screen.run_test(counts, tmp_path / "control-normalized", ["c1", "c2"], ["t1", "t2"],
                             controls_path=controls, normalization="control")
    assert report["control_guide_ids"] == controls.read_text().splitlines()
    assert report["control_guides_sha256"] == hashlib.sha256(controls.read_bytes()).hexdigest()
    assert min(report["hits"]["neg"], key=lambda row: row["rank"])["gene"] == "GENE0"
    assert report["normalization"]["effective_method"] == "median"
    assert report["normalization"]["reference_guides"] == "control_guides"


@pytest.mark.parametrize("label", ["0", "1", "1.5", "NaN", "Infinity"])
def test_numeric_labels_cannot_select_the_wrong_sample(counts, label):
    counts.write_text(counts.read_text().replace("\tc1\t", f"\t{label}\t", 1))
    with pytest.raises(ValueError, match="Numeric sample"):
        screen.inspect_screen(counts, [label, "c2"], ["t1", "t2"])


def test_headerless_counts_and_whitespace_ids_are_rejected(counts):
    original = counts.read_text()
    counts.write_text("\n".join(original.splitlines()[1:]) + "\n")
    with pytest.raises(ValueError, match="requires a header"):
        screen.read_counts(counts)
    counts.write_text(original.replace("GENE0", "GENE 0"))
    with pytest.raises(ValueError, match="free of whitespace"):
        screen.read_counts(counts)


def test_controls_must_include_at_least_two_and_whole_gene_groups(counts, tmp_path):
    controls = tmp_path / "controls.txt"
    controls.write_text("g2_0\n")
    with pytest.raises(ValueError, match="at least two"):
        screen.inspect_screen(counts, ["c1"], ["t1"], controls_path=controls)
    controls.write_text("g2_0\ng2_1\n")
    with pytest.raises(ValueError, match="mix control"):
        screen.inspect_screen(counts, ["c1"], ["t1"], controls_path=controls)


def test_constant_counts_warn_of_undefined_correlations(tmp_path):
    path = tmp_path / "constant.tsv"
    path.write_text("sgRNA\tGene\tc1\tc2\tt1\n" + "".join(f"g{i}\tG\t3\t3\t4\n" for i in range(4)))
    qc = screen.inspect_screen(path, ["c1", "c2"], ["t1"])
    assert qc["within_condition_log2_count_correlations"]["c1 vs c2"] is None
    assert any("undefined" in warning for warning in qc["warnings"])


@pytest.mark.parametrize("column,value", [("neg|fdr", "nan"), ("neg|fdr", "1.1"),
                                         ("pos|lfc", "inf"), ("pos|rank", "0")])
def test_nonfinite_or_invalid_gene_results_cannot_be_reported(tmp_path, column, value):
    row = {"id": "G", "neg|fdr": ".01", "neg|lfc": "-2", "neg|rank": "1",
           "pos|fdr": ".9", "pos|lfc": "-2", "pos|rank": "2"}
    row[column] = value
    path = tmp_path / "summary.tsv"
    path.write_text("\t".join(row) + "\n" + "\t".join(row.values()) + "\n")
    with pytest.raises(ValueError, match="Invalid FDR"):
        screen.read_gene_hits(path, .05)


@pytest.mark.skipif(shutil.which("mageck") is None, reason="MAGeCK is an external source/conda executable")
@pytest.mark.parametrize("normalization", ["median", "control"])
def test_sparse_inputs_record_actual_total_normalization(counts, tmp_path, normalization):
    rows = list(csv.reader(counts.open(), delimiter="\t"))
    controls = tmp_path / "controls.txt"
    controls.write_text("".join(f"g{gene}_{guide}\n" for gene in range(2, 22) for guide in range(5)))
    for row in rows[1:]:
        gene = int(row[1][4:])
        if (normalization == "median" and gene < 48) or (normalization == "control" and 2 <= gene < 12):
            row[2] = "0"
    with counts.open("w", newline="") as handle:
        csv.writer(handle, delimiter="\t").writerows(rows)
    report = screen.run_test(counts, tmp_path / "sparse", ["c1", "c2"], ["t1", "t2"],
                             normalization=normalization,
                             controls_path=controls if normalization == "control" else None)
    assert report["normalization"]["fallback_to_total"]
    assert report["normalization"]["effective_method"] == "total"
    assert report["normalization"]["warnings"]


@pytest.mark.skipif(shutil.which("mageck") is None, reason="MAGeCK is an external source/conda executable")
def test_fastq_technical_lanes_trimming_orientation_and_zero_guide(tmp_path):
    sequences = {"g1": "AGGTACGTACGTACGTACGT", "g2": "TTTTCCCCAAAAGGGGTTTT", "g3": "CCCCAGTCAGTCAGTCAGTC"}
    (tmp_path / "library.tsv").write_text("".join(f"{g}\t{s}\tG{i}\n" for i, (g, s) in enumerate(sequences.items())))
    for lane, guides in [("lane1", ["g1"] * 10), ("lane2", ["g1"] * 5 + ["g2"] * 7)]:
        reads = ["GAT" + sequences[g].translate(str.maketrans("ACGT", "TGCA"))[::-1] for g in guides]
        (tmp_path / f"{lane}.fastq").write_text("".join(f"@r{i}\n{s}\n+\n{'I' * len(s)}\n" for i, s in enumerate(reads)))
    subprocess.run(["mageck", "count", "-l", "library.tsv", "--fastq", "lane1.fastq,lane2.fastq",
                    "--sample-label", "sample", "--trim-5", "3", "--reverse-complement",
                    "--norm-method", "none", "-n", "lanes"], cwd=tmp_path, check=True, capture_output=True, text=True)
    with (tmp_path / "lanes.count.txt").open() as handle:
        output = list(csv.DictReader(handle, delimiter="\t"))
    assert {row["sgRNA"]: int(row["sample"]) for row in output} == {"g1": 15, "g2": 7, "g3": 0}


@pytest.mark.skipif(shutil.which("mageck") is None, reason="MAGeCK is an external source/conda executable")
def test_named_mle_design_reorders_samples_and_recovers_beta_signs(counts, tmp_path):
    counts.write_text("\n".join(counts.read_text().splitlines()[:151]) + "\n")
    (tmp_path / "design.tsv").write_text(
        "Samples\tbaseline\ttreatment\nc2\t1\t0\nc1\t1\t0\nt2\t1\t1\nt1\t1\t1\n")
    process = subprocess.run(["mageck", "mle", "-k", str(counts), "-d", "design.tsv", "-n", "mle",
                              "--norm-method", "median", "--permutation-round", "1",
                              "--genes-varmodeling", "30", "--threads", "1"],
                             cwd=tmp_path, capture_output=True, text=True, check=True)
    assert "Sample index: 1;0;3;2" in process.stdout + process.stderr
    with (tmp_path / "mle.gene_summary.txt").open() as handle:
        rows = {row["Gene"]: row for row in csv.DictReader(handle, delimiter="\t")}
    assert len(rows) == 30
    assert float(rows["GENE0"]["treatment|beta"]) < 0
    assert float(rows["GENE1"]["treatment|beta"]) > 0
    assert all(math.isfinite(float(row["treatment|beta"])) for row in rows.values())


@pytest.mark.skipif(shutil.which("mageck") is None, reason="MAGeCK is an external source/conda executable")
def test_normalization_factors_follow_group_order_not_count_column_order(counts, tmp_path):
    with counts.open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    # Distinct depths make a mislabeled factor observable; sample columns interleave conditions.
    for row in rows:
        for sample, multiplier in {"c1": 1, "c2": 2, "t1": 3, "t2": 4}.items():
            row[sample] = str(int(row[sample]) * multiplier)
    with counts.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sgRNA", "Gene", "t2", "c2", "t1", "c1"], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    report = screen.run_test(counts, tmp_path / "reordered", ["c1", "c2"], ["t1", "t2"])
    factors = report["normalization"]["sample_size_factors"]
    assert list(factors) == ["c1", "c2", "t1", "t2"]
    with (tmp_path / "reordered" / "screen.normalized.txt").open() as handle:
        normalized = {row["sgRNA"]: row for row in csv.DictReader(handle, delimiter="\t")}
    for row in rows:
        for sample, factor in factors.items():
            assert float(normalized[row["sgRNA"]][sample]) / int(row[sample]) == pytest.approx(factor, rel=1e-4)
