"""Native tiny-file regressions for documented pysam 0.24.1 workflows."""
from __future__ import annotations

import ast
from array import array
from collections import Counter
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

pysam = pytest.importorskip("pysam")
import pysam.bcftools
import pysam.samtools

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pysam"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import alignment_qc
import filter_alignments
import inspect_hts
import variant_summary


def args(module, *values):
    return module.build_parser().parse_args([str(value) for value in values])


def segment(header, name="match", *, start=10, cigar="10M", sequence="A" * 10,
            flag=0, mapq=60, tid=0, quality=40):
    read = pysam.AlignedSegment(header)
    read.query_name = name
    read.flag = flag
    read.reference_id = tid
    read.reference_start = start
    read.mapping_quality = mapq
    read.cigarstring = cigar
    read.query_sequence = sequence
    if sequence is not None:
        read.query_qualities = array("B", [quality] * len(sequence))
    read.set_tag("RG", "rg1")
    return read


@pytest.fixture
def native_files(tmp_path):
    fasta = tmp_path / "reference.fa"
    fasta.write_text(">chr1\n" + "A" * 200 + "\n>chr2\n" + "C" * 100 + "\n")
    pysam.faidx(str(fasta))
    header = pysam.AlignmentHeader.from_dict({
        "HD": {"VN": "1.6", "SO": "coordinate"},
        "SQ": [{"SN": "chr1", "LN": 200}, {"SN": "chr2", "LN": 100}],
        "RG": [{"ID": "rg1", "SM": "synthetic", "LB": "library1"}],
        "PG": [{"ID": "synthetic-generator", "PN": "test-fixture"}],
    })
    bam = tmp_path / "input.bam"
    reads = [
        segment(header),
        segment(header, "deletion", cigar="4M2D4M", sequence="A" * 8),
        segment(header, "skip", cigar="4M2N4M", sequence="A" * 8),
        segment(header, "low_quality", quality=1),
        segment(header, "duplicate", flag=1024),
        segment(header, "secondary", flag=256),
        segment(header, "supplementary", flag=2048),
        segment(header, "qcfail", flag=512),
        segment(header, "unknown_mapq", mapq=255),
        segment(header, "missing_seq", start=20, cigar="4M", sequence=None),
        segment(header, "placed_unmapped", start=30, cigar=None, sequence="AAAA", flag=4, mapq=0),
        segment(header, "chr2", start=5, cigar="4M", sequence="CCCC", tid=1),
        segment(header, "unplaced", start=-1, cigar=None, sequence="AAAA", flag=4, mapq=0, tid=-1),
    ]
    with pysam.AlignmentFile(str(bam), "wb", header=header) as out:
        for read in reads:
            out.write(read)
    pysam.index(str(bam))
    return bam, fasta, header


@pytest.fixture
def variants(tmp_path):
    path = tmp_path / "variants.vcf"
    path.write_text(
        '##fileformat=VCFv4.3\n##contig=<ID=chr1,length=200>\n'
        '##FILTER=<ID=q10,Description="Low quality">\n'
        '##INFO=<ID=END,Number=1,Type=Integer,Description="End">\n'
        '##INFO=<ID=SVLEN,Number=.,Type=Integer,Description="SV length">\n'
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n'
        '#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\ts1\ts2\n'
        'chr1\t11\tsnv\tA\tG\t50\tPASS\t.\tGT\t0|1\t./.\n'
        'chr1\t15\tdel\tAAA\tA\t.\t.\t.\tGT\t1/.\t1\n'
        'chr1\t20\tstar\tA\t*\t10\tq10\t.\tGT\t1/1/0\t0\n'
        'chr1\t21\tbnd1\tA\tA.\t.\tPASS\t.\tGT\t0/1\t.\n'
        'chr1\t22\tbnd2\tA\t.A\t.\tPASS\t.\tGT\t0/1\t.\n'
        'chr1\t23\tmulti\tA\tAT,G\t.\tPASS\t.\tGT\t1/2\t0/0\n'
        'chr1\t24\tno_alt\tA\t.\t.\t.\t.\tGT\t0\t.\n'
        'chr1\t25\tequal\tA\tA\t.\t.\t.\tGT\t0/0\t.\n'
        'chr1\t26\tambiguous\tA\tN\t.\t.\t.\tGT\t0/1\t.\n'
        'chr1\t30\tsymbolic\tA\t<DEL>\t.\tPASS\tEND=40;SVLEN=-10\tGT\t0/1\t.\n'
    )
    return path


def documented_functions(tmp_path):
    """Import the actual documented function bodies, not copies in the test."""
    definitions = []
    for name in ("common_workflows.md", "sequence_files.md"):
        text = (SKILL_ROOT / "references" / name).read_text()
        for block in re.findall(r"```python\n(.*?)```", text, flags=re.S):
            tree = ast.parse(block)
            definitions.extend(node for node in tree.body if isinstance(node, ast.FunctionDef))
    module = ast.Module(body=definitions, type_ignores=[])
    path = tmp_path / "documented_examples.py"
    path.write_text("from __future__ import annotations\nimport pysam\nfrom collections import Counter\n" + ast.unparse(module))
    spec = importlib.util.spec_from_file_location("pysam_documented_examples", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_alignment_coordinates_and_placed_unmapped(native_files):
    bam, _, _ = native_files
    with pysam.AlignmentFile(str(bam), "rb") as handle:
        assert [r.query_name for r in handle.fetch("chr1", 10, 20)] == [r.query_name for r in handle.fetch(region="chr1:11-20")]
        placed = list(handle.fetch("chr1", 30, 31))
        assert len(placed) == 1 and placed[0].is_unmapped
        assert "placed_unmapped" in {r.query_name for r in handle.fetch()}
        assert [r.query_name for r in handle.fetch("*")] == ["unplaced"]
    with pysam.AlignmentFile(str(bam), "rb") as handle:
        assert len(list(handle.fetch(until_eof=True))) == 13


def test_iterator_independence_and_unindexed_scan(native_files, tmp_path):
    bam, _, _ = native_files
    with pysam.AlignmentFile(str(bam), "rb") as handle:
        first = handle.fetch("chr1", multiple_iterators=True)
        assert next(first).query_name == "match"
        assert next(handle.fetch("chr2", multiple_iterators=True)).query_name == "chr2"
        assert next(first).query_name == "deletion"
    unindexed = tmp_path / "unindexed.bam"
    unindexed.write_bytes(bam.read_bytes())
    with pysam.AlignmentFile(str(unindexed), "rb") as handle:
        with pytest.raises(ValueError):
            list(handle.fetch("chr1", 10, 20))
        assert len(list(handle.fetch(until_eof=True))) == 13


def test_head_splice_junctions_and_count_callback(native_files):
    bam, _, _ = native_files
    with pysam.AlignmentFile(str(bam), "rb") as handle:
        assert [r.query_name for r in handle.head(2)] == ["match", "deletion"]
        assert handle.find_introns(handle.fetch("chr1")) == {(14, 16): 1}
        assert handle.count("chr1", 10, 20, read_callback="nofilter") == 9
        assert handle.count("chr1", 10, 20, read_callback="all") == 6
        assert handle.count("chr1", 10, 20, read_callback=lambda r: r.mapping_quality != 255) == 8


def test_qc_excludes_unmapped_and_missing_seq_from_aligned_bases(native_files):
    bam, _, _ = native_files
    report = alignment_qc.inspect_alignments(args(alignment_qc, bam))
    assert report["counts"]["total_records"] == 13
    assert report["counts"]["mapped_records"] == 11
    assert report["counts"]["sequence_missing_records"] == 1
    assert report["counts"]["mapq_255_records"] == 1
    assert report["derived"]["mean_mapping_quality"] == 60
    assert report["derived"]["mean_query_length"] == pytest.approx(98 / 12)
    assert report["derived"]["aligned_query_bases"] == 90
    limited = alignment_qc.inspect_alignments(args(alignment_qc, bam, "--max-records", 2))
    assert limited["counts"]["total_records"] == 2
    assert limited["selection"]["record_limit_reached"]


def test_pileup_deletions_and_skips_are_not_observed_bases(native_files, tmp_path):
    bam, fasta, _ = native_files
    functions = documented_functions(tmp_path)
    with pysam.AlignmentFile(str(bam), "rb") as handle:
        for column in handle.pileup("chr1", 14, 15, truncate=True, compute_baq=False, min_base_quality=20):
            assert column.reference_pos == 14
            assert column.nsegments == 6  # includes the low-quality read before baseQ filtering
            assert column.get_num_aligned() == 5  # includes D and N
            assert sum(not r.is_del and not r.is_refskip for r in column.pileups) == 3
        coverage = functions.base_depth(handle, "chr1", 14, 16)
        assert coverage == [3, 3]
        assert functions.base_depth(handle, "chr1", 100, 105) == [0] * 5
        with pytest.raises(ValueError):
            functions.base_depth(handle, "chr1", 195, 205)
    # Test the documented helper with BAQ disabled only in the test handle so
    # the deliberately all-A synthetic deletion does not get BAQ-downweighted.
    class NoBaqHandle:
        def pileup(self, *values, **kwargs):
            kwargs["compute_baq"] = False
            return handle.pileup(*values, **kwargs)
    with pysam.AlignmentFile(str(bam), "rb") as handle, pysam.FastaFile(str(fasta)) as ref:
        assert functions.aligned_depth_at(NoBaqHandle(), ref, "chr1", 14) == 3
        assert functions.aligned_depth_at(NoBaqHandle(), ref, "chr1", 100) == 0


def test_count_coverage_numeric_bounds_and_alias_trap(native_files):
    bam, _, _ = native_files
    with pysam.AlignmentFile(str(bam), "rb") as handle:
        assert [len(a) for a in handle.count_coverage("chr1", 195, 205)] == [5] * 4
        assert [len(a) for a in handle.count_coverage("chr1", 10, 20)] == [10] * 4
        # This is an upstream 0.24.1 behavior: region= does not size arrays.
        assert [len(a) for a in handle.count_coverage("chr1", region="chr1:11-20")] == [200] * 4


def test_cigar_geometry_md_and_orientation(native_files):
    _, _, header = native_files
    read = segment(header, cigar="2S3M1I2M2D2M3N1M1S", sequence="ACGTACGTACGT")
    assert read.reference_end == 23
    assert read.query_alignment_length == 9
    assert read.get_blocks() == [(10, 13), (13, 15), (17, 19), (22, 23)]
    positions = read.get_reference_positions(full_length=True)
    assert positions == [None, None, 10, 11, 12, None, 13, 14, 17, 18, 22, None]
    assert any(q is None and op == pysam.CIGAR_OPS.CDEL for q, r, op in read.get_aligned_pairs(with_cigar=True))
    assert read.infer_query_length() == 12
    with pytest.raises(ValueError):
        read.get_aligned_pairs(with_seq=True)
    simple = segment(header, sequence="AACG", cigar="4M", flag=16)
    simple.set_tag("MD", "4")
    assert simple.get_reference_sequence() == "AACG"
    assert simple.get_forward_sequence() == "CGTT"
    original_qualities = simple.get_forward_qualities()
    simple.query_sequence = "TT"
    assert simple.query_qualities is None
    simple.query_qualities = original_qualities[:2]
    assert len(simple.query_qualities) == 2


def test_modified_bases_empty_and_orientation(native_files):
    _, _, header = native_files
    read = segment(header, sequence="ACCC", cigar="4M")
    read.set_tag("MM", "C+m,0;")
    read.set_tag("ML", array("B", [200]))
    assert read.modified_bases == {("C", 0, "m"): [(1, 200)]}
    assert read.modified_bases_forward == read.modified_bases
    read.set_tag("MM", "C+m;")
    read.set_tag("ML", None)
    assert read.modified_bases == {}


def test_filter_preserves_records_header_and_can_write_csi(native_files, tmp_path):
    bam, _, _ = native_files
    output = tmp_path / "filtered.bam"
    options = args(filter_alignments, bam, output, "--exclude-secondary", "--exclude-unmapped", "--index", "--csi")
    report = filter_alignments.filter_file(options)
    assert report["counts"]["written_records"] == 10
    assert report["index_format"] == "CSI"
    assert Path(str(output) + ".csi").exists()
    with pysam.AlignmentFile(str(bam), "rb") as source, pysam.AlignmentFile(str(output), "rb") as result:
        assert result.header.to_dict() == source.header.to_dict()
        expected = [r.to_string() for r in source.fetch(until_eof=True) if not r.is_secondary and not r.is_unmapped]
        assert [r.to_string() for r in result.fetch(until_eof=True)] == expected
        assert result.check_index()
    pysam.samtools.quickcheck(str(output))


def test_filter_refuses_orphan_indexes_and_preserves_existing_file(native_files, tmp_path):
    bam, _, _ = native_files
    output = tmp_path / "filtered.bam"
    stale = output.with_suffix(".bai")
    stale.write_bytes(b"do not overwrite")
    with pytest.raises(FileExistsError, match="index"):
        filter_alignments.filter_file(args(filter_alignments, bam, output, "--index"))
    assert stale.read_bytes() == b"do not overwrite"
    assert not output.exists()
    stale.unlink()
    output.write_bytes(b"do not overwrite")
    assert filter_alignments.main([str(bam), str(output)]) == 2
    assert output.read_bytes() == b"do not overwrite"


def test_filter_does_not_remove_racing_destination(native_files, tmp_path, monkeypatch):
    bam, _, _ = native_files
    output = tmp_path / "race.bam"
    original = filter_alignments.validate_destinations
    def raced(*values):
        original(*values)
        output.write_bytes(b"created after preflight")
    monkeypatch.setattr(filter_alignments, "validate_destinations", raced)
    with pytest.raises(FileExistsError):
        filter_alignments.filter_file(args(filter_alignments, bam, output))
    assert output.read_bytes() == b"created after preflight"


@pytest.mark.parametrize("extension", ["sam", "cram"])
def test_filter_sam_cram_conversion(native_files, tmp_path, extension):
    bam, fasta, _ = native_files
    output = tmp_path / ("converted." + extension)
    filter_alignments.filter_file(args(filter_alignments, bam, output, "--reference", fasta))
    mode = "r" if extension == "sam" else "rc"
    with pysam.AlignmentFile(str(output), mode, reference_filename=str(fasta)) as handle:
        records = list(handle.fetch(until_eof=True))
        assert len(records) == 13
        assert [r.query_name for r in records][-1] == "unplaced"
        assert all(r.get_tag("RG") == "rg1" for r in records)
    if extension == "cram":
        assert output.read_bytes()[:6] == b"CRAM\x03\x01"


@pytest.mark.parametrize("version", ["3.0", "3.1"])
def test_cram_reference_rg_and_no_fabricated_crai_counts(native_files, tmp_path, version):
    bam, fasta, header = native_files
    cram = tmp_path / ("reads-" + version + ".cram")
    with pysam.AlignmentFile(str(cram), "wc", header=header,
                             reference_filename=str(fasta), format_options=["version=" + version]) as out:
        out.write(segment(header))
    pysam.samtools.index(str(cram), catch_stdout=False)
    assert cram.read_bytes()[:6] == b"CRAM" + bytes(map(int, version.split(".")))
    with pysam.AlignmentFile(str(cram), "rc", reference_filename=str(fasta)) as source:
        read = next(source.fetch("chr1", 10, 20))
        assert (read.reference_start, read.reference_end, read.query_sequence, read.get_tag("RG")) == (10, 20, "A" * 10, "rg1")
        assert source.header.to_dict()["RG"] == header.to_dict()["RG"]
        assert source.header.to_dict()["SQ"][0]["M5"]
        assert source.mapped == 0
    report = inspect_hts.inspect_file(args(inspect_hts, cram, "--reference", fasta))
    assert report["details"]["has_index"]
    assert report["details"]["index_statistics"] is None
    assert alignment_qc.inspect_alignments(args(alignment_qc, cram, "--reference", fasta))["counts"]["mapped_records"] == 1
    roundtrip = tmp_path / ("roundtrip-" + version + ".bam")
    filter_alignments.filter_file(args(filter_alignments, cram, roundtrip, "--reference", fasta, "--index"))
    with pysam.AlignmentFile(str(roundtrip), "rb") as result:
        assert next(result.fetch()).get_tag("RG") == "rg1"


def test_variant_summary_and_missing_genotype_ploidy(variants):
    report = variant_summary.summarize_variants(args(variant_summary, variants))
    assert report["record_counts"]["total"] == 10
    assert report["record_counts"]["symbolic_or_breakend"] == 4
    assert report["record_counts"]["snv"] == 2
    assert report["record_counts"]["indel_or_mixed"] == 2
    assert report["record_counts"]["other"] == 1
    assert report["substitution_counts"] == {"transitions": 1}
    assert report["genotypes"]["partially_missing_genotypes"] == 1
    assert sum(report["observed_genotype_ploidy_counts"].values()) == 20
    assert report["observed_genotype_ploidy_counts"]["3"] == 1
    assert "decoded_samples" not in report["selection"]
    subset = variant_summary.summarize_variants(args(variant_summary, variants, "--sample", "s2", "--include-sample-names"))
    assert subset["selection"]["decoded_samples"] == ["s2"]
    assert subset["genotypes"]["genotypes_seen"] == 10


def test_variant_fetch_no_index_rewinds_and_indexed_overlap(variants, tmp_path):
    with pysam.VariantFile(str(variants)) as source:
        assert next(source).pos == 11
        assert next(iter(source)).pos == 15
        assert next(source.fetch()).pos == 11
        assert len(list(source.fetch(reference="chr1", start=15, stop=16))) == 10
        with pytest.raises(ValueError, match="index"):
            list(source.fetch("chr1", 10, 20))
    compressed = tmp_path / "variants.vcf.gz"
    pysam.tabix_compress(str(variants), str(compressed))
    pysam.bcftools.index("--csi", str(compressed), catch_stdout=False)
    with pysam.VariantFile(str(compressed)) as source:
        numeric = [r.id for r in source.fetch("chr1", 15, 16)]
        assert numeric == ["del"]  # POS=15 spans through position 17
        assert numeric == [r.id for r in source.fetch(region="chr1:16-16")]
        sv = next(source.fetch("chr1", 35, 36))
        assert (sv.id, sv.start, sv.stop) == ("symbolic", 29, 40)
    report = variant_summary.summarize_variants(args(variant_summary, compressed, "--region", "chr1:16-16"))
    assert report["record_counts"]["total"] == 1


def test_variant_translation_bcf_and_write_modes(variants, tmp_path):
    output = tmp_path / "translated.bcf"
    with pysam.VariantFile(str(variants)) as source:
        source.subset_samples(["s1"])
        header = source.header.copy()
        header.info.add("BAM_DP", number=1, type="Integer", description="Test base depth")
        with pysam.VariantFile(str(output), "wb0", header=header) as out:
            for original in source:
                record = original.copy()
                record.translate(header)
                record.info["BAM_DP"] = 3
                out.write(record)
    with pysam.VariantFile(str(output)) as handle:
        assert handle.is_bcf
        assert handle.compression == "BGZF"
        assert list(handle.header.samples) == ["s1"]
        records = list(handle.fetch())  # no index needed
        assert records[0].samples["s1"]["GT"] == (0, 1)
        assert records[0].samples["s1"].phased
        assert all(r.info["BAM_DP"] == 3 for r in records)
    with pytest.raises(ValueError, match="conflicting"):
        pysam.VariantFile(str(tmp_path / "bad.bcf"), "wbu", header=header)
    pysam.bcftools.index(str(output), catch_stdout=False)
    assert inspect_hts.inspect_file(args(inspect_hts, output))["details"]["format"] == "BCF"


def test_current_local_allele_and_ploidy_number_fields(tmp_path):
    path = tmp_path / "vcf45.vcf"
    path.write_text(
        '##fileformat=VCFv4.5\n##contig=<ID=chr1,length=200>\n'
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n'
        '##FORMAT=<ID=LAA,Number=.,Type=Integer,Description="Local ALT indices">\n'
        '##FORMAT=<ID=LAD,Number=LR,Type=Integer,Description="Local allelic depths">\n'
        '##FORMAT=<ID=LPL,Number=LG,Type=Integer,Description="Local likelihoods">\n'
        '##FORMAT=<ID=PSL,Number=P,Type=String,Description="Phase sets">\n'
        '#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\ts1\n'
        'chr1\t11\t.\tA\tC,G\t.\tPASS\t.\tGT:LAA:LAD:LPL:PSL\t0/2:2:8,4:0,10,30:a,b\n'
    )
    with pysam.VariantFile(str(path)) as source:
        record = next(source)
        assert source.header.version == "VCFv4.5"
        call = record.samples["s1"]
        assert call["LAA"] == (2,)
        assert call["LAD"] == (8, 4)
        assert call["LPL"] == (0, 10, 30)
        assert call["PSL"] == ("a", "b")
        call["LAD"] = (9, 5)
        call["PSL"] = ("x", "y")
        assert call["LAD"] == (9, 5)


def test_fasta_readonly_inspection_and_bounds(native_files, tmp_path):
    _, fasta, _ = native_files
    functions = documented_functions(tmp_path)
    with pysam.FastaFile(str(fasta)) as source:
        assert source.fetch("chr1", 0, 2) == source.fetch(region="chr1:1-2") == "AA"
        assert source.fetch("chr1", 195, 205) == "AAAAA"
        assert source.fetch("chr1", 200, 205) == ""
        assert functions.variant_context(source, "chr1", 1, "AA", flank=2) == ("AAAA", True)
        with pytest.raises(ValueError):
            functions.variant_context(source, "chr1", 200, "AA")
    unindexed = tmp_path / "unindexed.fa"
    unindexed.write_text(">x\nACGT\n")
    with pytest.raises(FileNotFoundError, match="FASTA index"):
        inspect_hts.inspect_file(args(inspect_hts, unindexed))
    assert not Path(str(unindexed) + ".fai").exists()
    assert inspect_hts.inspect_file(args(inspect_hts, fasta))["details"]["total_bases"] == 300


def test_fastx_persistence_quality_and_reverse_complement(tmp_path):
    fastq = tmp_path / "reads.fastq"
    fastq.write_text("@r1 comment\nACGT\n+\nIIII\n@r2\nAAAA\n+\n!!!!\n")
    with pysam.FastxFile(str(fastq)) as source:
        first = next(source)
        next(source)
        assert (first.name, first.comment, list(first.get_quality_array())) == ("r1", "comment", [40] * 4)
        assert str(first) == "@r1 comment\nACGT\n+\nIIII"
    functions = documented_functions(tmp_path)
    assert functions.fastx_stats(str(fastq)) == {"records": 2, "bases": 8, "mean_length": 4.0, "mean_quality": 20.0}
    assert pysam.reverse_complement("ACGTRYMKBDHVNSW") == "WSNBDHVMKRYACGT"
    mutable = bytearray(b"ACGTN")
    pysam.reverse_complement_inplace(mutable)
    assert mutable == b"NACGT"
    assert inspect_hts.inspect_file(args(inspect_hts, fastq))["details"]["content_scanned"] is False


@pytest.mark.parametrize("csi", [False, True])
def test_tabix_index_coordinates_and_inspection(tmp_path, csi):
    bed = tmp_path / "regions.bed"
    bed.write_text("#header\nchr1\t10\t20\tgene\t0\t-\n")
    compressed = str(bed) + ".gz"
    pysam.tabix_compress(str(bed), compressed)
    pysam.tabix_index(compressed, preset="bed", csi=csi)
    index = compressed + (".csi" if csi else ".tbi")
    assert bed.exists()
    with pysam.TabixFile(compressed, index=index, parser=pysam.asBed()) as table:
        row = next(table.fetch("chr1", 19, 20))
        assert (row.start, row.end, row.strand) == (10, 20, "-")
        assert list(table.fetch("chr1", 20, 21)) == []
        assert str(next(table.fetch(region="chr1:20-20"))) == str(row)
        assert table.filename_index == index.encode()
    assert inspect_hts.inspect_file(args(inspect_hts, compressed))["details"]["has_index"]


@pytest.mark.parametrize("parser,line,preset", [
    (pysam.asGTF, 'chr1\tx\texon\t11\t20\t.\t+\t.\tgene_id "g";\n', "gff"),
    (pysam.asGFF3, "chr1\tx\texon\t11\t20\t.\t+\t.\tID=g\n", "gff"),
])
def test_annotation_parser_coordinate_conversion(tmp_path, parser, line, preset):
    path = tmp_path / "annotation.tsv"
    path.write_text(line)
    compressed = pysam.tabix_index(str(path), preset=preset, keep_original=True)
    with pysam.TabixFile(compressed, parser=parser()) as handle:
        row = next(handle.fetch("chr1", 10, 11))
        assert (row.start, row.end) == (10, 20)
    assert path.exists()


def test_asvcf_is_zero_based_and_missing_compress_input_raises(variants, tmp_path):
    compressed = str(variants) + ".gz"
    pysam.tabix_compress(str(variants), compressed)
    pysam.tabix_index(compressed, preset="vcf")
    with pysam.TabixFile(compressed, parser=pysam.asVCF()) as handle:
        assert next(handle.fetch("chr1", 10, 11)).pos == 10
    with pytest.raises(OSError):
        pysam.tabix_compress(str(tmp_path / "absent"), str(tmp_path / "bad.gz"))


def test_bam_csi_high_coordinate(tmp_path):
    header = pysam.AlignmentHeader.from_dict({"HD": {"SO": "coordinate"}, "SQ": [{"SN": "large", "LN": 600_000_000}]})
    path = tmp_path / "large.bam"
    with pysam.AlignmentFile(str(path), "wb", header=header) as out:
        out.write(segment(header, start=550_000_000))
    pysam.index("-c", str(path), catch_stdout=False)
    with pysam.AlignmentFile(str(path), "rb") as handle:
        assert next(handle.fetch("large", 550_000_000, 550_000_001)).reference_start == 550_000_000


def test_snp_helper_rejects_star_and_ref_mismatch(native_files, tmp_path):
    bam, fasta, _ = native_files
    functions = documented_functions(tmp_path)
    header = pysam.VariantHeader()
    header.contigs.add("chr1", length=200)
    with pysam.AlignmentFile(str(bam), "rb") as source, pysam.FastaFile(str(fasta)) as ref:
        star = header.new_record(contig="chr1", start=10, alleles=("A", "*"))
        with pytest.raises(ValueError, match="simple SNP"):
            functions.snp_base_counts(source, ref, star)
        wrong = header.new_record(contig="chr1", start=10, alleles=("C", "G"))
        with pytest.raises(ValueError, match="does not match"):
            functions.snp_base_counts(source, ref, wrong)
        valid = header.new_record(contig="chr1", start=10, alleles=("A", "G"))
        assert set(functions.snp_base_counts(source, ref, valid)) <= {"A"}


def test_documented_annotation_preserves_samples_and_output(native_files, variants, tmp_path):
    bam, fasta, _ = native_files
    functions = documented_functions(tmp_path)
    output = tmp_path / "annotated.vcf.gz"
    functions.annotate_depth(str(variants), str(bam), str(fasta), str(output))
    with pysam.VariantFile(str(output)) as handle:
        assert "BAM_BASE_DP" in handle.header.info
        assert list(handle.header.samples) == ["s1", "s2"]
        records = list(handle)
        assert len(records) == 10
        assert records[0].samples["s1"].phased
        assert all(r.info["BAM_BASE_DP"] >= 0 for r in records)
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        functions.annotate_depth(str(variants), str(bam), str(fasta), str(output))
    assert output.read_bytes() == original


def test_dispatcher_norm_sort_output_and_error(native_files, variants, tmp_path):
    bam, fasta, _ = native_files
    sorted_bam = tmp_path / "sorted.bam"
    pysam.samtools.sort("-o", str(sorted_bam), str(bam), catch_stdout=False)
    pysam.samtools.index(str(sorted_bam), catch_stdout=False)
    assert pysam.samtools.view("-c", str(sorted_bam)).strip() == "13"
    saved = tmp_path / "count.txt"
    pysam.samtools.view("-c", str(sorted_bam), save_stdout=str(saved))
    assert saved.read_text().strip() == "13"
    with pytest.raises(pysam.SamtoolsError, match="returned with error"):
        pysam.samtools.quickcheck(str(tmp_path / "absent.bam"))
    # A valid multi-ALT SNP gives an independently checkable split-GT policy.
    multi = tmp_path / "multi.vcf"
    multi.write_text('##fileformat=VCFv4.3\n##contig=<ID=chr1,length=200>\n##FORMAT=<ID=GT,Number=1,Type=String,Description="GT">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\ts1\nchr1\t11\t.\tA\tC,G\t.\tPASS\t.\tGT\t1/2\n')
    normalized = tmp_path / "norm.vcf.gz"
    pysam.bcftools.norm("-f", str(fasta), "-m", "-any", "--multi-overlaps", ".", "-Oz", "-o", str(normalized), str(multi), catch_stdout=False)
    pysam.bcftools.index("--csi", str(normalized), catch_stdout=False)
    with pysam.VariantFile(str(normalized)) as source:
        assert [r.samples["s1"]["GT"] for r in source.fetch("chr1", 10, 11)] == [(1, None), (None, 1)]
