"""Small native VCF round trips; requires the separately installed TileDB channel build."""
from pathlib import Path
import shutil
import subprocess

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "tiledbvcf"

tiledbvcf = pytest.importorskip("tiledbvcf", reason="Install tiledb::tiledbvcf-py")
pd = pytest.importorskip("pandas")
CONFIG = {"sm.compute_concurrency_level": "2", "sm.io_concurrency_level": "2"}
ATTRS = ["sample_name", "contig", "pos_start", "pos_end", "alleles", "fmt_GT"]


@pytest.fixture(scope="module")
def cohort(tmp_path_factory):
    bcftools = shutil.which("bcftools")
    if not bcftools:
        pytest.skip("bcftools is required to compress and index the tiny fixture")
    root = tmp_path_factory.mktemp("tiledbvcf")
    header = (
        "##fileformat=VCFv4.2\n##contig=<ID=chr1,length=100>\n"
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n'
        '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">\n'
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t{sample}\n"
    )
    rows = {
        "S1": [(1, "A", "G", "0|1:10"), (10, "ACGTA", "A", "0/1:15"),
               (20, "A", "C,G", "1/2:20"), (30, "C", "T", "./.:.")],
        "S2": [(1, "A", "G", "1/1:12"), (20, "A", "C,G", "0/2:18")],
    }
    files = []
    for index, (sample, records) in enumerate(rows.items(), start=1):
        plain = root / f"sample{index}.vcf"
        plain.write_text(header.format(sample=sample) + "".join(
            f"chr1\t{pos}\t.\t{ref}\t{alt}\t50\tPASS\t.\tGT:DP\t{gt}\n"
            for pos, ref, alt, gt in records
        ))
        compressed = root / f"sample{index}.vcf.gz"
        subprocess.run([bcftools, "view", "-Oz", "-o", str(compressed), str(plain)], check=True)
        subprocess.run([bcftools, "index", "-c", str(compressed)], check=True)
        files.append(str(compressed))
    uri = str(root / "cohort")
    with tiledbvcf.Dataset(uri, mode="w", tiledb_config=CONFIG) as ds:
        ds.create_dataset(extra_attrs=["fmt_GT", "fmt_DP"])
        ds.ingest_samples(files[:1], threads=2, total_memory_budget_mb=512)
    with tiledbvcf.Dataset(uri, mode="w", tiledb_config=CONFIG) as ds:
        ds.ingest_samples(files[1:], threads=2, total_memory_budget_mb=512)
    return root, uri, files


def open_read(uri, **kwargs):
    return tiledbvcf.Dataset(uri, cfg=tiledbvcf.ReadConfig(
        memory_budget_mb=128, tiledb_config=CONFIG, **kwargs))


def test_incremental_ingestion_and_genotypes(cohort):
    _, uri, _ = cohort
    with open_read(uri) as ds:
        assert set(ds.samples()) == {"S1", "S2"}
        assert ds.sample_count() == 2
        assert ds.schema_version() == 4
        df = pd.concat(ds.read_iter(attrs=ATTRS, regions=["chr1:1-100"]), ignore_index=True)
        assert len(df) == ds.count(regions=["chr1:1-100"]) == 6
        missing = df[(df.sample_name == "S1") & (df.pos_start == 30)].iloc[0]
        assert list(missing.fmt_GT) == [-1, -1]
        multi = df[(df.sample_name == "S1") & (df.pos_start == 20)].iloc[0]
        assert list(multi.alleles) == ["A", "C", "G"]
        assert list(multi.fmt_GT) == [1, 2]


def test_inclusive_overlap_and_bed_half_open(cohort):
    root, uri, _ = cohort
    bed = root / "window.bed"
    bed.write_text("chr1\t13\t14\n")
    with open_read(uri) as ds:
        df = ds.read(attrs=ATTRS, regions=["chr1:14-14"])
        assert list(zip(df.pos_start, df.pos_end)) == [(10, 14)]
        assert ds.read(attrs=ATTRS, regions=["chr1:15-15"]).empty
        bed_df = ds.read(attrs=ATTRS + ["query_bed_start", "query_bed_end"], bed_file=str(bed))
        assert list(zip(bed_df.pos_start, bed_df.pos_end)) == [(10, 14)]
        assert list(zip(bed_df.query_bed_start, bed_df.query_bed_end)) == [(13, 14)]
    # 0.40.3 retains BED state when the next call omits bed_file. Reopen before
    # changing from BED-based to region-string selection.
    with open_read(uri) as ds:
        assert len(ds.read(attrs=ATTRS, regions=["chr1:1-1"])) == 2


def test_partitions_cover_samples_once(cohort):
    _, uri, _ = cohort
    names = []
    for partition in range(2):
        with open_read(uri, sample_partition=(partition, 2)) as ds:
            df = ds.read(attrs=ATTRS, regions=["chr1:1-1"])
            names.extend(df.sample_name)
    assert sorted(names) == ["S1", "S2"]


def test_limit_truncates_without_pagination(cohort):
    _, uri, _ = cohort
    with open_read(uri, limit=1) as ds:
        batches = list(ds.read_iter(attrs=ATTRS, regions=["chr1:1-100"]))
        assert sum(len(batch) for batch in batches) == 1
        assert ds.read_completed()


def test_population_stats_and_sample_qc(cohort):
    _, uri, _ = cohort
    with open_read(uri) as ds:
        stats = ds.read_variant_stats(regions=["chr1:1-1"], drop_ref=True)
        assert len(stats) == 1
        row = stats.iloc[0]
        assert row["pos"] == 0  # Statistics positions differ from pos_start.
        assert row["ac"] == 3
        assert row["an"] == 4
        assert row["af"] == pytest.approx(0.75)
        counts = ds.read_allele_count(regions=["chr1:1-1"])
        assert set(counts["pos"]) == {0}
        assert counts["count"].sum() == 2
    qc = tiledbvcf.sample_qc(uri, samples=["S1"], config=CONFIG)
    assert len(qc) == 1
    assert qc.iloc[0]["sample"] == "S1"


def test_export_preserves_sample_records(cohort):
    root, uri, files = cohort
    output = root / "export"
    output.mkdir()
    with open_read(uri) as ds:
        ds.export(samples=["S1"], regions=["chr1:1-100"], output_format="v", output_dir=str(output))
    bcftools = shutil.which("bcftools")
    fmt = "%CHROM\t%POS\t%REF\t%ALT[\t%GT\t%DP]\n"
    original = subprocess.check_output([bcftools, "query", "-f", fmt, files[0]])
    restored = subprocess.check_output([bcftools, "query", "-f", fmt, str(output / "S1.vcf")])
    assert restored == original
    assert b"0|1" in restored
    with open_read(uri) as ds:
        ds.export(samples=["S1", "S2"], regions=["chr1:1-100"], output_format="v",
                  merge=True, output_path=str(output / "combined.vcf"))
    names = subprocess.check_output([bcftools, "query", "-l", str(output / "combined.vcf")], text=True)
    assert set(names.splitlines()) == {"S1", "S2"}


def test_bare_contig_is_not_a_python_region(cohort):
    _, uri, _ = cohort
    with open_read(uri) as ds:
        with pytest.raises(Exception, match="format"):
            ds.read(regions=["chr1"])


def test_frequency_filter_is_not_recomputed_for_selected_samples(cohort):
    _, uri, _ = cohort
    with open_read(uri) as ds:
        df = ds.read(attrs=ATTRS, samples=["S1"], regions=["chr1:1-1"], set_af_filter=">0.6")
        assert len(df) == 1  # Cohort AF 3/4 passes; S1-only AF 1/2 would fail.


def test_cli_create_store_query_and_export(cohort):
    root, _, files = cohort
    # Conda installs the CLI beside Python; keep this independent of global PATH.
    import sys
    cli = Path(sys.executable).with_name("tiledbvcf")
    if not cli.exists():
        pytest.skip("TileDB-VCF CLI was not installed")
    uri = str(root / "cli_cohort")
    config = ",".join(f"{key}={value}" for key, value in CONFIG.items())
    subprocess.run([str(cli), "create", "--uri", uri, "--tiledb-config", config], check=True)
    subprocess.run([str(cli), "store", "--uri", uri, "--threads", "2",
                    "--total-memory-budget-mb", "512", "--tiledb-config", config, "--", *files], check=True)
    names = subprocess.check_output([str(cli), "list", "--uri", uri, "--tiledb-config", config], text=True)
    assert "S1" in names and "S2" in names
    subprocess.run([str(cli), "stat", "--uri", uri, "--tiledb-config", config], check=True)
    tsv = root / "query.tsv"
    subprocess.run([str(cli), "export", "--uri", uri, "--regions", "chr1:1-1",
                    "--sample-names", "S1,S2", "-Ot", "--tsv-fields", "SAMPLE,CHR,POS,REF,ALT,F:GT",
                    "--output-path", str(tsv), "--tiledb-config", config], check=True)
    lines = tsv.read_text().splitlines()
    assert len(lines) == 3
    assert {line.split("\t")[0] for line in lines[1:]} == {"S1", "S2"}
