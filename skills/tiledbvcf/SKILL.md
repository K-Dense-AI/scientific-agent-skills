---
name: tiledbvcf
description: Stores and retrieves genomic variant calls with TileDB-VCF. Use for indexed single-sample VCF/BCF ingestion, incremental cohorts, region and sample queries, streaming results, allele statistics, QC, and VCF/BCF export locally or through TileDB Cloud.
license: MIT license
compatibility: Requires a native TileDB-VCF installation and Python 3.9-3.12 for the reviewed Conda builds. bcftools compresses/indexes input fixtures. Installation and remote storage need network access; TileDB Cloud needs its Python client, account token, and storage permissions.
metadata:
  version: "1.3"
  skill-author: Jeremy Leipzig
  last-reviewed: "2026-10-01"
  upstream-version: "TileDB-VCF 0.40.3; tiledb-cloud 0.14.4"
---

# TileDB-VCF

## When to use

Use for cohort variant storage, incremental sample ingestion, interval queries, and
exporting subsets for downstream genomics. TileDB-VCF stores records; it does not
perform joint variant calling, association testing, normalization, or population
structure adjustment. Dataset size alone does not determine whether cloud execution
is appropriate: benchmark the intended sample, region, and attribute workload.

This skill targets released **TileDB-VCF 0.40.3**. Native Python/CLI checks used two
synthetic single-sample VCFs on macOS ARM64. Cloud client **0.14.4** contracts were
checked against its released wheel and mocked dispatch; hosted queries and jobs
were not executed. See [installation and verification notes](references/verification.md).

## Install and verify the native stack

The `tiledbvcf` Python distribution is not published on PyPI at this review. The
official **`tiledb` Conda channel** supplies `tiledbvcf-py` 0.40.3 for macOS ARM64,
macOS x86-64, and Linux x86-64, with Python 3.9-3.12 builds. `tiledb` on PyPI is
TileDB-Py and does not install TileDB-VCF. Native Apple Silicon no longer requires
forcing `CONDA_SUBDIR=osx-64`.

For the tested macOS ARM64 environment, pins below avoid versioned-library import
failures in the otherwise successful current Conda solve:

```bash
conda create -n tiledb-vcf -c tiledb -c conda-forge \
  python=3.12 tiledbvcf-py=0.40.3 \
  azure-core-cpp=1.16.2 azure-storage-blobs-cpp=12.16.0 \
  azure-storage-files-datalake-cpp=12.14.0 capnproto=1.4.0 c-blosc2=2.23.1
conda activate tiledb-vcf
python -c 'import tiledbvcf; print(tiledbvcf.version)'
tiledbvcf version
```

The equivalent Micromamba solve/install was executed. These extra ABI pins are a
verified macOS ARM64 workaround, not a claim about all platforms. Preserve the
resolved environment for production. Other-platform installation and official
Docker images are alternatives documented upstream, not tested here.

## Prepare and create a cohort

1. Record reference assembly, contig naming/lengths, callers, normalization rules,
   sample identity, and file checksums. Do not mix assemblies or assume `1` and
   `chr1` are equivalent. Confirm compatible headers across inputs.
2. Each input must contain **one sample**, be coordinate sorted, and have an index.
   Use BGZF-compressed VCF or BCF with a matching `.csi`/`.tbi`. Inspect
   `bcftools query -l sample1.vcf.gz`; filenames are not sample identifiers.
3. Create the dataset explicitly, then ingest. Opening `mode="w"` alone does not
   create its schema. Materialize frequently read fields at creation time.
4. Validate a small known interval and a round-trip export before scaling.

For existing sorted plain-text VCFs (run once per input; output names must be new):

```bash
bcftools view -Oz -o sample1.vcf.gz sample1.vcf
bcftools index -c sample1.vcf.gz
bcftools view -Oz -o sample2.vcf.gz sample2.vcf
bcftools index -c sample2.vcf.gz
```

The following local examples were exercised with sample IDs `S1` and `S2`, contig
`chr1`, and coordinates 1-100; substitute the verified IDs and intervals in real data.

```python
import tiledbvcf

uri = "cohort"
config = {"sm.compute_concurrency_level": "2", "sm.io_concurrency_level": "2"}
with tiledbvcf.Dataset(uri, mode="w", tiledb_config=config) as ds:
    ds.create_dataset(extra_attrs=["fmt_GT", "fmt_DP"])
    ds.ingest_samples(
        ["sample1.vcf.gz"], threads=2, total_memory_budget_mb=512
    )

# Incremental ingestion uses the existing dataset; do not call create_dataset again.
with tiledbvcf.Dataset(uri, mode="w", tiledb_config=config) as ds:
    ds.ingest_samples(
        ["sample2.vcf.gz"], threads=2, total_memory_budget_mb=512
    )
```

The schema-v4 data array has `contig`, start-coordinate, and sample **dimensions**;
headers and optional statistics are separate arrays in the dataset group. Fields
not explicitly materialized remain in the INFO/FORMAT payloads. Query names such
as `pos_start` need not match raw storage column names.

Upstream supports parallel thread/process ingestion. Assign distinct sample work
and coordinate lifecycle/maintenance operations; do not blindly re-ingest samples.
`resume=True` supports interrupted ingestion, not arbitrary duplicate correction.

## Query completely and interpret coordinates correctly

| Surface | Coordinate convention |
| --- | --- |
| Python `regions=["chr1:10-14"]` | 1-based, closed interval |
| Returned `pos_start`, `pos_end` | 1-based, inclusive record endpoints |
| BED input and `query_bed_start`, `query_bed_end` | 0-based, half-open |
| `read_variant_stats()` / `read_allele_count()` column `pos` in 0.40.3 | **0-based**; add one before joining to VCF POS |

Queries return **overlapping records**, not just records starting inside the
interval. A deletion spanning positions 10-14 appears in `chr1:14-14`, with
`pos_start=10`. For BED `[13,14)`, the equivalent string is `chr1:14-14`.
The Python region parser requires explicit `contig:start-end`; bare `"chr1"`
is rejected in this release. Use a known contig length for a whole-contig query.

```python
cfg = tiledbvcf.ReadConfig(memory_budget_mb=128, tiledb_config=config)
attrs = ["sample_name", "contig", "pos_start", "pos_end", "alleles", "fmt_GT"]
with tiledbvcf.Dataset(uri, cfg=cfg) as ds:
    assert {"S1", "S2"}.issubset(ds.samples())
    assert set(attrs).issubset(ds.attributes())
    for batch in ds.read_iter(
        attrs=attrs, regions=["chr1:1-100"], samples=["S1", "S2"]
    ):
        print(batch)  # Replace with a bounded consumer or partitioned output.
```

- `read()` returns a pandas DataFrame; `read_arrow()` returns a PyArrow Table.
  Either can return only the first memory-limited batch. Continue with
  `continue_read()` / `continue_read_arrow()` until `read_completed()`, or use
  `read_iter()` for ordinary DataFrame queries. Avoid concatenating all batches
  when the result cannot fit in memory.
- `ReadConfig(memory_budget_mb=...)` controls reads; use
  `ingest_samples(total_memory_budget_mb=...)` for writes. A read budget is not
  a process RSS cap. `limit` truncates total output; it is not a pagination size.
- `sample_partition=(0, 2)` selects partition zero of two. Likewise,
  `region_partition=(index, number_of_partitions)` partitions query regions;
  these tuples are not coordinate bounds, tile extents, or sample capacities.
- **0.40.3 retains BED selection state** when a later call omits `bed_file`.
  Open a fresh `Dataset` for an independent query when changing BED/region inputs.
- `fmt_GT` contains allele indices: 0 refers to REF, positive values index ALT,
  and -1 means missing. Preserve multiallelic identity and ploidy; do not treat
  every positive integer as a biallelic dosage or missing calls as reference.
  The integer list alone does not encode the original phased GT string.

## Export and validate

```python
from pathlib import Path

Path("exported").mkdir(exist_ok=True)
with tiledbvcf.Dataset(uri, cfg=cfg) as ds:
    ds.export(
        samples=["S1"], regions=["chr1:1-100"],
        output_format="v", output_dir="exported",
    )
```

Python export formats: `v` VCF, `z` compressed VCF, `u` uncompressed BCF, `b`
compressed BCF. `merge=False` writes per-sample files; `merge=True` requires a
combined `output_path`. A combined export is not joint calling. Re-index exported
files before indexed downstream access. Compare sample IDs, contigs, record
counts, alleles, INFO/FORMAT values, and missing/phased genotypes; semantic
round-trip preservation does not imply byte-identical compression or headers.

The CLI accepts positional sample paths or `--samples-file` (one URI per line),
not a comma-separated `--samples` argument:

```bash
tiledbvcf create --uri cli_cohort
tiledbvcf store --uri cli_cohort --threads 2 --total-memory-budget-mb 512 \
  -- sample1.vcf.gz sample2.vcf.gz
tiledbvcf list --uri cli_cohort
tiledbvcf stat --uri cli_cohort
tiledbvcf export --uri cli_cohort --regions chr1:1-100 \
  --sample-names S1,S2 -Ot --tsv-fields 'SAMPLE,CHR,POS,REF,ALT,F:GT' \
  --output-path variants.tsv
```

`--` protects positional paths from variable-length options such as
`--tiledb-config`. Check expected artifacts and sample counts as well as the exit
code: an invalid store command returned exit zero while printing an error in the
reviewed CLI. TSV fields use `F:GT` for FORMAT/GT and `I:DP` for INFO/DP.

## Cohort statistics and QC

```python
with tiledbvcf.Dataset(uri, cfg=cfg) as ds:
    stats = ds.read_variant_stats(regions=["chr1:1-100"], drop_ref=True)
    stats["vcf_pos"] = stats["pos"] + 1
    print(stats[["contig", "vcf_pos", "alleles", "ac", "an", "af"]])

qc = tiledbvcf.sample_qc(uri, samples=["S1"], config=config)
print(qc)
```

Statistics arrays are enabled by default at creation; older/disabled arrays may
not support these operations. `read_variant_stats` has no `samples` argument.
The older `read_allele_frequency(dataset_uri, region)` wrapper accepts a single
region and delegates to the deprecated singular argument; prefer the Dataset
method above. `sample_qc` uses `dataset_uri`, not `uri`, as its first argument.

The `ac`, `an`, and `af` values summarize the ingested cohort, not a selected
ancestry or query sample subset. A `read(samples=[...], set_af_filter=">0.6")`
filter still used cohort AF in the tested release. Compute subgroup frequencies
from correctly selected calls with explicit missingness, ploidy, callable-region,
and gVCF reference-block policies. Use an appropriate called-allele denominator,
not universally `2 * number_of_samples`; a missing VCF record is not proof of a
homozygous-reference call. QC metrics and sparse storage do not establish GWAS
readiness or scientific validity.

## Object storage and TileDB Cloud

Direct storage uses `s3://bucket/path`, `azure://container/path`, or
`gcs://bucket/path`, supported by the installed TileDB backend and its provider
credentials. This does not automatically distribute the computation. Use the
provider's credential chain or scoped configuration, and verify access to both
the dataset and source indexes. A TileDB Cloud token is distinct from bucket
credentials. Remote storage examples below are illustrative, source-verified,
and not authenticated end-to-end tests.

Install `tiledb-cloud==0.14.4` in a compatible environment. Its `life-sciences`
extra adds TileDB-SOMA, **not TileDB-VCF**. Supply `TILEDB_REST_TOKEN` through the
execution environment before importing the client; `TILEDB_REST_HOST` selects a
custom deployment if required. Do not embed tokens in code or print configuration.

```python
# Illustrative: requires an accessible registered cohort and a billing namespace.
import tiledb.cloud
import tiledb.cloud.vcf

cloud_cfg = tiledb.cloud.Config()
with tiledbvcf.Dataset("tiledb://my-namespace/cohort", tiledb_config=cloud_cfg) as ds:
    sample_names = ds.samples()

result = tiledb.cloud.vcf.read(
    dataset_uri="tiledb://my-namespace/cohort",
    config=cloud_cfg, attrs=["sample_name", "pos_start", "fmt_GT"],
    regions=["chr1:1-100"], samples=sample_names[:2],
    num_region_partitions=1, namespace="my-namespace", max_workers=2,
)
frame = result.to_pandas()  # read returns an Arrow table, not a DataFrame.
```

Distributed reads assemble an Arrow result and may use significant worker/client
memory. Bound the requested regions/samples and worker count; partitioning does
not make the final concatenated result memory-free. This is SDK task execution,
not a paginated VCF REST-list API.

```python
# Illustrative, mutating cloud job: use only for an authorized ingestion task.
submission = tiledb.cloud.vcf.ingest(
    dataset_uri="s3://my-bucket/cohort",
    sample_list_uri="s3://my-bucket/inputs/sample-uris.txt",
    namespace="my-namespace", acn="registered-storage-role",
    register_name="cohort", max_samples=2,
    ingest_resources={"cpu": "2", "memory": "4Gi"},
)
print(submission["graph_id"])
```

Use exactly one of `search_uri`, `sample_list_uri`, or `metadata_uri`; file-search
patterns apply to `search_uri`. Registration requires the access credential name
(`acn`). `vcf.ingest` submits asynchronously and returns
`{"status": "started", "graph_id": ...}`; track that graph to terminal success
and verify ingested samples before claiming completion. There is no released
`ingest_vcf_dataset(source=..., output=...)` API. Pricing, availability, security
controls, and deployment obligations require the current account/service terms.

## Official references

- [TileDB-VCF 0.40.3 release](https://github.com/TileDB-Inc/TileDB-VCF/releases/tag/0.40.3)
- [Dataset API](https://tiledb-inc.github.io/TileDB-VCF/documentation/reference/Dataset.html)
- [Ingestion](https://tiledb-inc.github.io/TileDB-VCF/documentation/how-to/ingest-samples.html)
- [Large queries](https://tiledb-inc.github.io/TileDB-VCF/documentation/how-to/handle-large-queries.html)
- [Cloud storage](https://tiledb-inc.github.io/TileDB-VCF/documentation/how-to/work-with-cloud-object-stores.html)
- [TileDB Cloud client release](https://pypi.org/project/tiledb-cloud/0.14.4/)
- [Verification details and known release issues](references/verification.md)
