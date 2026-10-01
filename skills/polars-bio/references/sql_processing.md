# DataFusion SQL in polars-bio 0.36.0

Registration is `register_<format>(path, name=...)`, `from_polars(name, frame)`
or `register_view(name, query_string)`. `pb.sql(query)` returns a Polars LazyFrame.
Consult the [SQL reference](https://biodatageeks.org/polars-bio/api/sql/)
and [registration implementation](https://github.com/biodatageeks/polars-bio/blob/0.36.0/polars_bio/sql.py)
for each function's actual arguments; there is no universal registration signature.

## Small reference query for half-open hit counts

This synthetic workflow was executed. It uses a chromosome equijoin followed by
conditional aggregation to retain zero-hit queries. It is a correctness fixture,
not a scalable range-join plan: the within-contig candidate product can be huge.
Use `pb.count_overlaps` for real interval-count workloads.

```python
import polars as pl
import polars_bio as pb

pb.set_option("datafusion.bio.coordinate_system_zero_based", True)
query = pl.DataFrame({"query_id": ["q1", "q2", "q3"],
    "chrom": ["chr1", "chr1", "chr2"],
    "start": [0, 10, 0], "end": [10, 20, 10]})
target = pl.DataFrame({"chrom": ["chr1", "chr1"],
    "start": [5, 8], "end": [12, 15]})
for frame in (query, target):
    frame.config_meta.set(coordinate_system_zero_based=True)
pb.from_polars("query_regions", query)
pb.from_polars("target_regions", target)

counts = pb.sql('''
    SELECT q.query_id,
           SUM(CASE WHEN q.start < t.end AND t.start < q.end
                    THEN 1 ELSE 0 END) AS hit_count
    FROM query_regions q
    LEFT JOIN target_regions t
      ON q.chrom = t.chrom
    GROUP BY q.query_id ORDER BY q.query_id
''').collect()
assert counts["hit_count"].to_list() == [2, 2, 0]

pb.register_view("chr1_targets", "SELECT * FROM target_regions WHERE chrom = 'chr1'")
assert pb.sql("SELECT COUNT(*) AS n FROM chr1_targets").collect()["n"][0] == 2
```

For **closed** intervals use `q.start <= t.end AND t.start <= q.end`. `BETWEEN`
is inclusive at both ends, so it is not the half-open point-in-interval rule.
A containment join (`v.start >= r.start AND v.end <= r.end`) is a different
question from an overlap join. Decide whether a variant is counted by its
anchor start or its full record span. `COUNT(*)` on a left join includes the
null target row; count a non-null target key instead. Grouping only by
coordinates collapses distinct duplicate query rows, so preserve a query ID.

### Native SQL range-join limitation

In 0.36.0, the optimizer's interval join path is not interchangeable with a
standard SQL left join. A tested `LEFT JOIN ... ON q.chrom=t.chrom AND
q.start<t.end AND t.start<q.end` failed for Int64/UInt32 coordinates with a
mixed-width arithmetic error. Casting bounds to Int32 made it execute but
**dropped the unmatched query**, violating left-join expectations. Do not use
that cast as a correctness fix. The conditional-aggregation fixture above
avoids the range predicate in ON; prefer the explicit interval APIs for normal
work. Check zero-hit preservation and numerical results after future upgrades.

## Register files with a chosen session convention

File examples below are templates. Set the convention **before** registering
files: several registration helpers do not accept `use_zero_based`.

```python
pb.set_option("datafusion.bio.coordinate_system_zero_based", True)
pb.register_vcf("cohort.vcf.gz", name="variants", info_fields=[], format_fields=[])
pb.register_bcf("cohort.bcf", name="binary_variants", format_fields=["GT"])
pb.register_bed("regions.bed", name="regions")
pb.register_fasta("reference.fa", name="reference_sequences")
pb.register_gff("genes.gff3", name="genes", attr_fields=["ID", "gene_biotype"])

coding = pb.sql('''
    SELECT chrom, start, end, "ID"
    FROM genes
    WHERE type = 'gene' AND gene_biotype = 'protein_coding'
''').collect()
```

Annotation keys vary by producer: request and verify actual keys from the file.
Do not apply `attributes LIKE ...` to the GFF list-of-structs column. Attribute
projection gives directly queryable scalar columns. Column names such as `end`
or mixed-case identifiers can require double quotes in complex SQL.

`register_fasta` exists. `register_sam` has no cloud-parameter suite. `register_vcf_zarr` exists for local stores and accepts `use_zero_based`; its
arguments differ from the text VCF helper. `register_cram` cannot accept an external
reference; use `scan_cram(..., reference_path="ref.fa")` then `from_polars`.
This differs from the separate `read_cram`/`scan_cram` capability.

## Combine SQL and interval calls safely

```python
# Template: tables were registered above in half-open coordinates.
high_quality = pb.sql('SELECT chrom, start, "end" FROM variants WHERE qual > 30').collect()
regions = pb.sql('SELECT chrom, start, "end" FROM regions').collect()
for frame in (high_quality, regions):
    # Label only because the registration convention and SQL are known.
    frame.config_meta.set(coordinate_system_zero_based=True)
hits = pb.overlap(regions, high_quality).collect()
```

SQL outputs are not guaranteed to carry coordinate/format metadata. Inspect and
reattach the confirmed convention before range operations; reconstructing full
format headers after arbitrary SQL is a separate task. Repeated registration
uses a process-global context: use distinct, predictable table names.

DataFusion SQL supports aggregation, CTEs, windows and joins, but it is neither
Polars SQL nor a database with server-side cursor pagination. A LazyFrame result
does not make arbitrary SQL joins bounded-memory. Inspect cardinality on a small
subset and use interval APIs where their semantics and index strategy fit.
Never interpolate untrusted table names, paths or values directly into SQL.
