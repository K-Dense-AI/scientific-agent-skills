"""Unplaced unmapped SAM/BAM records do not require an @SQ dictionary."""
from pathlib import Path
import json
import os
import subprocess
import sys

import pytest

pysam = pytest.importorskip("pysam")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pysam"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import alignment_qc
import filter_alignments
import inspect_hts


ROWS = (
    "first\t4\t*\t0\t0\t*\t*\t0\t0\tACGT\tIIII\n"
    "second\t1028\t*\t0\t0\t*\t*\t0\t0\tAACCGG\tIIIIII\n"
)


@pytest.fixture(params=[("sam", False), ("sam", True), ("bam", False), ("bam", True)])
def unmapped_file(request, tmp_path):
    suffix, header = request.param
    source = tmp_path / "source.sam"
    source.write_text(("@HD\tVN:1.6\tSO:unsorted\n" if header else "") + ROWS)
    if suffix == "sam":
        return source
    destination = tmp_path / "source.bam"
    with pysam.AlignmentFile(str(source), "r", check_sq=False) as inp:
        with pysam.AlignmentFile(str(destination), "wb", template=inp) as out:
            for record in inp.fetch(until_eof=True):
                out.write(record)
    return destination


def cli(script, *arguments):
    return subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / script), *map(str, arguments)],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def records(path):
    mode = "r" if path.suffix == ".sam" else "rb"
    with pysam.AlignmentFile(str(path), mode, check_sq=False) as inp:
        return inp.header.to_dict(), [record.to_string() for record in inp.fetch(until_eof=True)]


def test_qc_cli_counts_unmapped_without_dictionary(unmapped_file):
    result = cli("alignment_qc.py", unmapped_file)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["counts"]["total_records"] == 2
    assert report["counts"]["unmapped_records"] == 2
    assert report["counts"]["mapped_records"] == 0
    assert report["derived"]["mapping_rate_all_records"] == 0.0
    assert report["derived"]["duplicate_rate_all_records"] == 0.5
    assert report["derived"]["mean_query_length"] == 5.0
    assert report["derived"]["mean_mapping_quality"] is None
    assert report["derived"]["aligned_query_bases"] == 0
    limited = cli("alignment_qc.py", unmapped_file, "--max-records", 1)
    assert limited.returncode == 0, limited.stderr
    report = json.loads(limited.stdout)
    assert report["counts"]["total_records"] == 1
    assert report["selection"]["record_limit_reached"] is True


def test_filter_cli_preserves_unmapped_records_and_header(unmapped_file, tmp_path):
    output = tmp_path / ("copy" + unmapped_file.suffix)
    result = cli("filter_alignments.py", unmapped_file, output)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["counts"]["selected_records"] == 2
    assert report["counts"]["written_records"] == 2
    assert records(output) == records(unmapped_file)
    excluded = tmp_path / "excluded.bam"
    result = cli("filter_alignments.py", unmapped_file, excluded, "--exclude-unmapped")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["counts"]["written_records"] == 0
    assert records(excluded)[1] == []


def test_inspector_cli_reports_empty_dictionary_not_record_validity(unmapped_file):
    result = cli("inspect_hts.py", unmapped_file)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)["details"]
    assert report["reference_count"] == 0
    assert report["contigs"] == []
    assert report["content_scanned"] is False
    assert "first" not in result.stdout and "second" not in result.stdout


@pytest.mark.parametrize("script", ["alignment_qc.py", "filter_alignments.py"])
def test_mapped_sam_without_dictionary_still_fails(tmp_path, script):
    source = tmp_path / "invalid.sam"
    source.write_text("@HD\tVN:1.6\n" + ROWS + "mapped\t0\tchr1\t1\t60\t4M\t*\t0\t0\tACGT\tIIII\n")
    output = tmp_path / "out.bam"
    result = cli(script, source, *([output] if script == "filter_alignments.py" else []))
    assert result.returncode != 0
    assert not output.exists()


@pytest.mark.parametrize("script", ["alignment_qc.py", "filter_alignments.py"])
def test_inconsistent_mapped_bam_without_dictionary_still_fails(tmp_path, script):
    source = tmp_path / "invalid.bam"
    header = pysam.AlignmentHeader.from_dict({"HD": {"VN": "1.6"}})
    with pysam.AlignmentFile(str(source), "wb", header=header) as out:
        for flag in [4, 0]:
            read = pysam.AlignedSegment(header)
            read.query_name = "read"
            read.flag = flag
            read.query_sequence = "ACGT"
            out.write(read)
    output = tmp_path / "out.bam"
    result = cli(script, source, *([output] if script == "filter_alignments.py" else []))
    assert result.returncode != 0
    assert not output.exists()


@pytest.mark.parametrize("script", ["alignment_qc.py", "filter_alignments.py"])
def test_truncated_record_still_fails(tmp_path, script):
    source = tmp_path / "invalid.sam"
    source.write_text("@HD\tVN:1.6\n" + ROWS + "broken\t4\t*\t0\n")
    output = tmp_path / "out.bam"
    result = cli(script, source, *([output] if script == "filter_alignments.py" else []))
    assert result.returncode != 0
    assert not output.exists()


def test_mixed_mapped_unmapped_with_dictionary_preserves_qc(tmp_path):
    source = tmp_path / "mixed.sam"
    source.write_text("@HD\tVN:1.6\n@SQ\tSN:chr1\tLN:100\n" + ROWS + "mapped\t0\tchr1\t1\t60\t4M\t*\t0\t0\tACGT\tIIII\n")
    result = cli("alignment_qc.py", source)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["counts"]["total_records"] == 3
    assert report["counts"]["mapped_records"] == 1
    assert report["derived"]["mapping_rate_all_records"] == pytest.approx(1 / 3)
    output = tmp_path / "out.bam"
    result = cli("filter_alignments.py", source, output)
    assert result.returncode == 0, result.stderr
    assert records(source) == records(output)


def test_cram_reference_requirement_remains(tmp_path):
    source = tmp_path / "placeholder.cram"
    source.write_bytes(b"CRAM")
    for script in ["alignment_qc.py", "filter_alignments.py", "inspect_hts.py"]:
        output = tmp_path / "out.bam"
        result = cli(script, source, *([output] if script == "filter_alignments.py" else []))
        assert result.returncode != 0
        assert "reference" in result.stderr.lower()
        assert not output.exists()


def test_empty_dictionary_inspection_does_not_scan_or_certify_records(tmp_path):
    source = tmp_path / "header-only-inspection.sam"
    source.write_text("@HD\tVN:1.6\n" + ROWS + "broken\t4\n")
    result = cli("inspect_hts.py", source)
    assert result.returncode == 0, result.stderr
    details = json.loads(result.stdout)["details"]
    assert details["reference_count"] == 0
    assert details["content_scanned"] is False
    assert cli("alignment_qc.py", source).returncode != 0


@pytest.mark.parametrize("script", ["alignment_qc.py", "filter_alignments.py"])
def test_region_selection_still_requires_dictionary_and_index(tmp_path, script):
    source = tmp_path / "unmapped.sam"
    source.write_text("@HD\tVN:1.6\n" + ROWS)
    output = tmp_path / "out.bam"
    result = cli(script, source, *([output] if script == "filter_alignments.py" else []), "--region", "chr1:1-10")
    assert result.returncode != 0
    assert not output.exists()


def test_header_only_qc_does_not_invent_denominators(tmp_path):
    source = tmp_path / "empty.sam"
    source.write_text("@HD\tVN:1.6\n")
    result = cli("alignment_qc.py", source)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["counts"]["total_records"] == 0
    assert report["derived"]["mapping_rate_all_records"] is None
    assert report["derived"]["mean_query_length"] is None
