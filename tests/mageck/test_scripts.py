from pathlib import Path
import csv
import importlib.util
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
def test_real_mageck_ranks_known_signals(counts, tmp_path):
    report = screen.run_test(counts, tmp_path / "results", ["c1", "c2"], ["t1", "t2"])
    negative = sorted(report["hits"]["neg"], key=lambda r: r["rank"])
    positive = sorted(report["hits"]["pos"], key=lambda r: r["rank"])
    assert negative[0]["gene"] == "GENE0" and negative[0]["lfc"] < -4
    assert positive[0]["gene"] == "GENE1" and positive[0]["lfc"] > 4
    assert (tmp_path / "results" / "screen.sgrna_summary.txt").is_file()


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
