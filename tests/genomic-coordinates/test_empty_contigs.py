"""Empty observations do not contradict a VCF header or reference dictionary."""

import importlib.util
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "genomic-coordinates"
SPEC = importlib.util.spec_from_file_location(
    "check_contigs", SKILL_ROOT / "scripts" / "check_contigs.py"
)
check_contigs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_contigs)

VCF_COLUMNS = "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"


def test_header_only_vcf_does_not_conflict_with_itself(tmp_path, capsys):
    vcf = tmp_path / "empty.vcf"
    vcf.write_text(
        "##fileformat=VCFv4.5\n##contig=<ID=chr1,length=248956422>\n"
        + VCF_COLUMNS
    )

    assert check_contigs.main([str(vcf)]) == 0
    output = capsys.readouterr()
    assert "GRCh38/hg38" in output.out
    assert "share no contigs" not in output.err


@pytest.mark.parametrize("extension", ["bed", "vcf"])
@pytest.mark.parametrize("reverse", [False, True])
def test_empty_observations_against_reference(tmp_path, capsys, extension, reverse):
    data = tmp_path / f"empty.{extension}"
    data.write_text("##fileformat=VCFv4.5\n" + VCF_COLUMNS if extension == "vcf" else "")
    genome = tmp_path / "reference.chrom.sizes"
    genome.write_text("chr1\t248956422\n")
    paths = [str(data), str(genome)]

    assert check_contigs.main(paths[::-1] if reverse else paths) == 0
    output = capsys.readouterr()
    assert "unknown" in output.out
    assert "share no contigs" not in output.err


@pytest.mark.parametrize(
    ("reference", "diagnostic"),
    [
        ("chr1\t249250621\n", "disagree on contig length"),
        ("1\t248956422\n", "contig naming differs"),
        ("chr2\t242193529\n", "share no contigs"),
    ],
)
def test_empty_vcf_keeps_header_conflict_checks(tmp_path, capsys, reference, diagnostic):
    vcf = tmp_path / "empty.vcf"
    vcf.write_text(
        "##fileformat=VCFv4.5\n##contig=<ID=chr1,length=248956422>\n"
        + VCF_COLUMNS
    )
    genome = tmp_path / "reference.chrom.sizes"
    genome.write_text(reference)

    assert check_contigs.main([str(vcf), "--genome", str(genome)]) == 1
    assert diagnostic in capsys.readouterr().err


def test_empty_file_does_not_hide_other_record_conflicts(tmp_path, capsys):
    empty = tmp_path / "empty.bed"
    empty.write_text("")
    observed = tmp_path / "observed.bed"
    observed.write_text("chr2\t0\t1\n")
    genome = tmp_path / "reference.chrom.sizes"
    genome.write_text("chr1\t248956422\n")

    assert check_contigs.main([str(empty), str(observed), "--genome", str(genome)]) == 1
    assert "observed.bed and reference.chrom.sizes share no contigs" in capsys.readouterr().err
