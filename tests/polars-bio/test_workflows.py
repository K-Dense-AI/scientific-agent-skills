"""Native scientific boundary and format examples for polars-bio 0.36.0.

All fixtures are small and generated locally. No network or external service is
required. Known native limitations are asserted so an upstream fix triggers a
review of the corresponding skill caveat rather than silently leaving it stale.
"""
from pathlib import Path
import gzip

import pytest

pl = pytest.importorskip("polars")
pb = pytest.importorskip("polars_bio")

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "polars-bio"


@pytest.fixture(autouse=True)
def coordinate_options():
    keys = ["datafusion.bio.coordinate_system_zero_based",
            "datafusion.bio.coordinate_system_check"]
    previous = {key: pb.get_option(key) for key in keys}
    for key in keys:
        pb.set_option(key, True)
    yield
    for key, value in previous.items():
        pb.set_option(key, value)


def intervals(rows, zero_based=True):
    frame = pl.DataFrame(rows, schema=["chrom", "start", "end"], orient="row")
    frame.config_meta.set(coordinate_system_zero_based=zero_based)
    return frame


@pytest.fixture
def query_target():
    return (intervals([("chr1", 0, 10), ("chr1", 10, 20), ("chr2", 0, 10)]),
            intervals([("chr1", 5, 12), ("chr1", 8, 15)]))


def test_pair_count_and_union_length_are_different(query_target):
    query, target = query_target
    assert pb.overlap(query, target).collect().height == 4
    assert query.lazy().pb.overlap(target).collect().height == 4
    assert pb.count_overlaps(query, target).collect().sort("chrom", "start")["count"].to_list() == [2, 2, 0]
    assert pb.coverage(query, target).collect().sort("chrom", "start")["coverage"].to_list() == [5, 5, 0]


def test_left_distinct_preserves_duplicate_source_rows():
    query = intervals([("chr1", 0, 10), ("chr1", 0, 10)])
    target = intervals([("chr1", 1, 4), ("chr1", 3, 6)])
    assert pb.overlap(query, target, overlap_output="left").collect().height == 4
    assert pb.overlap(query, target, overlap_output="left", distinct_output=True).collect().height == 2


def test_half_open_bookends_do_not_overlap():
    a = intervals([("chr1", 0, 10)])
    b = intervals([("chr1", 10, 20)])
    assert pb.overlap(a, b).collect().height == 0
    assert pb.nearest(a, b).collect()["distance"][0] == 0


def test_nearest_k_null_candidates_and_distance_toggle(query_target):
    query, target = query_target
    result = pb.nearest(query, target, k=3).collect()
    assert result.height == 5
    assert result.filter(pl.col("chrom_1") == "chr2")["distance"].to_list() == [None]
    assert "distance" not in pb.nearest(query, target, distance=False).collect().columns
    assert pb.nearest(query, target, overlap=False).collect()["start_2"].null_count() == 3


@pytest.mark.parametrize("operation", ["overlap", "count_overlaps", "coverage", "nearest", "merge"])
def test_on_cols_currently_rejected(operation, query_target):
    a, b = query_target
    args = (a,) if operation == "merge" else (a, b)
    with pytest.raises(AssertionError, match="on_cols is not supported"):
        getattr(pb, operation)(*args, on_cols=["strand"])


def test_merge_cluster_bookend_threshold(query_target):
    query, _ = query_target
    assert pb.merge(query).collect().height == 3
    merged = pb.merge(query, min_dist=1).collect().sort("chrom")
    assert merged.select("start", "end", "n_intervals").rows() == [(0, 20, 2), (0, 10, 1)]
    clustered = pb.cluster(query, min_dist=1).collect().sort("chrom", "start")
    assert clustered["cluster"].n_unique() == 2
    assert clustered["cluster_end"].to_list() == [20, 20, 10]


def test_subtract_and_complement_finite_view(query_target):
    query, target = query_target
    view = intervals([("chr1", 0, 20), ("chr2", 0, 10)])
    expected = [("chr1", 0, 5), ("chr1", 15, 20), ("chr2", 0, 10)]
    assert pb.subtract(query, target).collect().sort("chrom", "start").rows() == expected
    assert pb.complement(target, view_df=view).collect().sort("chrom", "start").rows() == expected


def test_metadata_is_not_coordinate_conversion(query_target):
    a, b = query_target
    b.config_meta.set(coordinate_system_zero_based=False)
    assert b["start"].to_list() == [5, 8]
    with pytest.raises(pb.CoordinateSystemMismatchError):
        pb.overlap(a, b)
    unlabelled = pl.DataFrame({"chrom": ["chr1"], "start": [0], "end": [10]})
    with pytest.raises(pb.MissingCoordinateSystemError):
        pb.overlap(unlabelled, a)


def test_int64_input_does_not_remove_native_int32_bound():
    a = intervals([("chr1", 2**31, 2**31 + 10)])
    with pytest.raises(pl.exceptions.ComputeError, match="Int32"):
        pb.overlap(a, a).collect()


def test_bed_conversion_extended_fields_and_named_table_schema(tmp_path):
    bed = tmp_path / "regions.bed"
    bed.write_text("chr1\t0\t10\tx\t2\t+\n")
    zero = pb.read_bed(str(bed), use_zero_based=True)
    closed = pb.read_bed(str(bed), use_zero_based=False)
    assert zero.columns == ["chrom", "start", "end", "name"]
    assert zero.select("start", "end").row(0) == (0, 10)
    assert closed.select("start", "end").row(0) == (1, 10)
    full = pb.scan_table(str(bed), schema="bed6").collect()
    assert full["strand"].to_list() == ["+"]
    assert full["start"].to_list() == [0]
    zipped = tmp_path / "regions.bed.gz"
    with gzip.open(zipped, "wt") as stream:
        stream.write(bed.read_text())
    assert pb.read_bed(str(zipped), use_zero_based=True).rows() == zero.rows()


VCF = '''##fileformat=VCFv4.3
##contig=<ID=chr1,length=30>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1
chr1\t2\t.\tA\tC\t50\tPASS\tDP=9\tGT:DP\t0/1:8
'''


def test_vcf_schema_layout_and_write_sink_round_trip(tmp_path):
    source = tmp_path / "source.vcf"
    source.write_text(VCF)
    frame = pb.read_vcf(str(source), use_zero_based=True, preserve_record_layout=True)
    assert frame.select("start", "end", "DP", "GT", "fmt_DP").row(0) == (1, 2, 9, "0/1", 8)
    assert "info" not in frame.columns
    assert frame.schema["qual"] == pl.Float64
    destination = tmp_path / "written.vcf"
    assert pb.write_vcf(frame, str(destination)) == 1
    assert destination.read_text() == VCF
    compressed = tmp_path / "stream.vcf.bgz"
    assert pb.sink_vcf(pb.scan_vcf(str(source), use_zero_based=True), str(compressed)) is None
    assert pb.read_vcf(str(compressed), use_zero_based=True).select("start", "end").rows() == [(1, 2)]
    assert pb.describe_vcf(str(source)).height > 0


@pytest.mark.parametrize("format_name,extension,text,expected", [
    ("fasta", "fa", ">r1 description\nACGT\n", ["name", "description", "sequence"]),
    ("fastq", "fq", "@r1 description\nACGT\n+\nIIII\n", ["name", "description", "sequence", "quality_scores"]),
])
def test_sequence_writes_sinks_and_sql_registration(tmp_path, format_name, extension, text, expected):
    source = tmp_path / ("source." + extension)
    source.write_text(text)
    frame = getattr(pb, "read_" + format_name)(str(source))
    assert frame.columns == expected
    destination = tmp_path / ("written." + extension)
    assert getattr(pb, "write_" + format_name)(frame, str(destination)) == 1
    assert destination.read_text() == text
    streamed = tmp_path / ("sink." + extension)
    assert getattr(pb, "sink_" + format_name)(getattr(pb, "scan_" + format_name)(str(source)), str(streamed)) is None
    assert streamed.read_text() == text
    getattr(pb, "register_" + format_name)(str(source), name="fixture_" + format_name)
    assert pb.sql("SELECT COUNT(*) AS n FROM fixture_" + format_name).collect()["n"][0] == 1


def test_annotation_attributes_and_pairs(tmp_path):
    gff = tmp_path / "genes.gff3"
    gff.write_text("##gff-version 3\nchr1\tsrc\tgene\t2\t8\t.\t+\t.\tID=g1;Name=Gene1\n")
    raw = pb.read_gff(str(gff), use_zero_based=True)
    assert raw["attributes"].to_list() == [[{"tag": "ID", "value": "g1"}, {"tag": "Name", "value": "Gene1"}]]
    projected = pb.read_gff(str(gff), use_zero_based=True, attr_fields=["ID", "Name"])
    assert projected.select("start", "end", "ID").rows() == [(1, 8, "g1")]
    gtf = tmp_path / "genes.gtf"
    gtf.write_text('chr1\tsrc\tgene\t2\t8\t.\t+\t.\tgene_id "g1"; gene_name "Gene1";\n')
    assert pb.read_gtf(str(gtf), attr_fields=["gene_id"])["gene_id"].to_list() == ["g1"]
    pairs = tmp_path / "contacts.pairs"
    pairs.write_text("## pairs format v1.0.0\n#columns: readID chrom1 pos1 chrom2 pos2 strand1 strand2\nr1\tchr1\t2\tchr1\t8\t+\t-\n")
    assert pb.read_pairs(str(pairs), use_zero_based=True).select("pos1", "pos2").rows() == [(1, 7)]


def write_sam(path, cigar="4M", sequence="AAAA", read_count=1, contig_length=30):
    header = f"@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:chr1\tLN:{contig_length}\n"
    records = "".join(f"r{i}\t0\tchr1\t2\t60\t{cigar}\t*\t0\t0\t{sequence}\t{'I' * len(sequence)}\n" for i in range(read_count))
    path.write_text(header + records)
    return str(path)


@pytest.mark.parametrize("format_name", ["bam", "sam", "cram"])
def test_alignment_unindexed_round_trips_and_sinks(tmp_path, format_name):
    source = write_sam(tmp_path / "input.sam")
    frame = pb.read_sam(source, use_zero_based=True)
    reference = tmp_path / "reference.fa"
    reference.write_text(">chr1\n" + "A" * 30 + "\n")
    (tmp_path / "reference.fa.fai").write_text("chr1\t30\t6\t30\t31\n")
    kwargs = {"reference_path": str(reference)} if format_name == "cram" else {}
    destination = str(tmp_path / ("written." + format_name))
    assert getattr(pb, "write_" + format_name)(frame, destination, **kwargs) == 1
    actual = getattr(pb, "read_" + format_name)(destination, use_zero_based=True, **kwargs)
    assert actual.select("start", "end", "sequence").rows() == [(1, 5, "AAAA")]
    streamed = str(tmp_path / ("sink." + format_name))
    assert getattr(pb, "sink_" + format_name)(pb.scan_sam(source, use_zero_based=True), streamed, **kwargs) is None
    assert getattr(pb, "read_" + format_name)(streamed, **kwargs).height == 1


def test_depth_cigar_zeroes_and_weighted_summary(tmp_path):
    source = write_sam(tmp_path / "spliced.sam", "3M2D2M3N2M", "ACGTACG")
    blocks = pb.depth(source, use_zero_based=True).collect()
    assert blocks.select("pos_start", "pos_end", "coverage").rows() == [(1, 4, 1), (6, 8, 1), (11, 13, 1)]
    assert blocks.schema["coverage"] == pl.Int16
    per_base = pb.depth(source, use_zero_based=True, per_base=True).collect()
    assert per_base.height == 30
    assert per_base["coverage"].sum() == 7
    assert per_base.filter(pl.col("pos").is_in([4, 5, 8, 9, 10]))["coverage"].sum() == 0
    weighted = blocks.select(((pl.col("pos_end").cast(pl.Int64) - pl.col("pos_start").cast(pl.Int64)) * pl.col("coverage").cast(pl.Int64)).sum()).item()
    assert weighted / 30 == pytest.approx(7 / 30)


def test_native_depth_int16_overflow_limit(tmp_path):
    source = write_sam(tmp_path / "deep.sam", "1M", "A", read_count=32768, contig_length=3)
    blocks = pb.depth(source, use_zero_based=True).collect()
    assert blocks["coverage"].to_list() == [-32768], "Review the documented 0.36.0 Int16 limitation if upstream fixed it"


def test_sql_interval_counts_preserve_unmatched_queries(query_target):
    query, target = query_target
    query = query.with_row_index("query_id")
    pb.from_polars("fixture_query", query)
    pb.from_polars("fixture_target", target)
    counts = pb.sql('''SELECT q.query_id,
        SUM(CASE WHEN q.start<t.end AND t.start<q.end THEN 1 ELSE 0 END) AS hits
        FROM fixture_query q LEFT JOIN fixture_target t
        ON q.chrom=t.chrom
        GROUP BY q.query_id ORDER BY q.query_id''').collect()
    assert counts["hits"].to_list() == [2, 2, 0]
    pb.register_view("fixture_view", "SELECT * FROM fixture_target WHERE chrom='chr1'")
    assert pb.sql("SELECT COUNT(*) AS n FROM fixture_view").collect()["n"][0] == 2
