# Surveillance caveats

Sequence databases reflect testing, specimen selection, sequencing, QC, submission and data-release
processes. These are not a probability sample of infections. Interpret every number conditional
on the database, inclusion filters, location, host, date window and lineage assignment system.

## Delays do not certify completeness

`reporting_lag.py` groups each monthly collection cohort jointly by collection and submission/release
date, then computes actual date differences. Measuring from month-end underestimates individual
collection-to-release delays by up to almost a month; the helper no longer uses that approximation.
It excludes missing/imprecise collection dates, negative delays and dates after the analysis anchor.

For each offset the reported CDF denominator is **currently visible, eligible records**, not all
records that will eventually arrive. Late-arriving records can lengthen the delay distribution.
Release dates also need not equal the first day a record was indexed by LAPIS. This is a descriptive
conditional CDF, not nowcasting or measured completeness. No printed date makes a cohort trustworthy.

Only cohorts with enough elapsed follow-up contribute a given offset. Cohorts receive equal weight;
small and large cohorts count equally. The mean curve can change its contributing cohort set and
therefore need not be monotonic, even though each individual cohort CDF is monotonic. Report the
cohort counts, ranges and exclusion totals. `--until` selects an analysis anchor using the current
database; it does not recreate a historical database state.

`lineage_prevalence.py` has a separate heuristic: compare weekly counts to the older half of the
window, flag zero-count/current partial weeks, and optionally exclude a user-selected `--lag-days`
horizon. It does not automatically consume the lag script's output. Counts can decline because
sequencing or incidence changed; neither a low flag nor an `ok` flag establishes actual completeness.

## Date precision and denominators

- Range-lower and range-upper collection fields must agree before weekly/date-delay binning. A
  year-only or month-only collection date cannot be assigned to a unique week. Report exclusions;
  retained exact dates may be a biased subset. Declared date types do not prove metadata accuracy.
- Range filters can already omit null collection dates. Exclusion counts among returned records
  are not estimates of all undated records in the source database.
- On Loculus deployments, default to `versionStatus=LATEST_VERSION` and `isRevocation=false` when
  available, to avoid counting historical revisions as different specimens. OPEN data defaults
  impose an additional inclusion condition. The remaining records may still include duplicated
  specimens across accessions/sources; accession version filtering is not biological deduplication.
- Exact labels and descendant-inclusive labels answer different questions. Nested lineage queries
  overlap, and overlapping categories cannot be added to form a prevalence total.
- Null/empty lineage calls stay in the denominator but are not discovered as named lineages.
  A literal `unassigned` value is retained as a category. Unknown names returning zero are not
  evidence of absence, particularly on unindexed fields.
- A widened ISO-week window changes the requested date boundaries. The output reports the actual
  window. A future week endpoint is only a bin boundary, not future observations.

## Sampling and scientific interpretation

Sequencing priorities can target travelers, hospitals, outbreaks, unusual assay results or a
random subset. Capacity and reporting delay vary geographically and institutionally. Host filters
matter for animal pathogens; pooled human/animal records need an explicit scientific justification.
QC failures and missing metadata can themselves depend on lineage and assay performance.

Report "share of selected submitted sequences" rather than "share of infections". Open GenBank,
Pathoplexus and GISAID-derived datasets can differ in coverage, geography, dates, pipelines and
terms. Do not assume strict set inclusion or comparable proportions; compare harmonized cohorts
and document differences before combining sources.

Wilson intervals quantify binomial sampling uncertainty, not reporting bias, clustering, missingness,
or lineage-assignment error. Interval overlap alone is not a formal test of a difference.

The optional growth calculation is weighted least squares of continuity-corrected log odds, with
weights `n*p*(1-p)`. At least five observations in three nonempty weeks are required. Dispersion
is floored at one to prevent an unusually straight short series from claiming excess precision.
It is an approximate descriptive slope among sequenced records, not a mechanistic fitness,
transmissibility, immune-escape or severity estimate. Changing denominator composition and
sequencing practice can generate the same pattern.

## Mutation interpretation

A mutation proportion divides by per-site callable sequence coverage, not total matching records
or read depth. Report both count and coverage. Missing mutation rows cannot supply a zero count
with known coverage; comparison output preserves missingness. Above/below-threshold status is not
a demonstrated ancestral gain/loss. Site-wise frequencies do not establish joint haplotypes,
full assay-binding sequences, phenotypes or experimental sensitivity. Insertions are separate.

## Reproducibility

Compare response `dataVersion` values before combining results; a changing snapshot invalidates the
run. LAPIS generally keeps only the latest data. Archive responses and request parameters, schemas,
reference/nomenclature versions, retrieval dates, processing code and inclusion decisions for
replay. A snapshot identifier alone cannot retrieve an old result.

Relevant primary documentation:
[response data versions](https://lapis.cov-spectrum.org/open/v2/docs/concepts/data-versions),
[mutation filters](https://lapis.cov-spectrum.org/open/v2/docs/concepts/mutation-filters/),
[Pathoplexus accessions and versions](https://pathoplexus.org/docs/how-to/search-download-seqs-api),
[WHO variant tracking](https://www.who.int/activities/tracking-SARS-CoV-2-variants).
