# LAPIS API reference

Reviewed 2026-10-01 against live `/api-docs`, `/sample/databaseConfig` and `/sample/info`.
SARS-CoV-2 used LAPIS 0.8.7/SILO 0.14.3. The other 14 registry entries used LAPIS 0.8.0/SILO
0.11.0. Upstream had released 0.8.8 on 2026-09-16; hosted deployments lag it.
This is a per-deployment contract; a current documentation page can describe features
an older server does not support.

## Deployment discovery and access

| Registry names | Base URL |
| --- | --- |
| `sars-cov-2` | `https://lapis.cov-spectrum.org/open/v2` |
| `influenza-a`, `h1n1pdm`, `h3n2`, `h5n1` | `https://lapis.genspectrum.org/<name>` |
| `rsv-a`, `rsv-b`, `hmpv`, `measles`, `mpox`, `west-nile`, `dengue`, `ebola-zaire`, `ebola-sudan`, `cchf` | `https://lapis.pathoplexus.org/<name>` |

All 15 schema/info endpoints answered without authentication in this review. Pathoplexus and
GenSpectrum use Loculus records; applicable terms, versions and revocations matter. The helpers
select latest, nonrevoked and OPEN records when those schema fields exist. Inspect and report
these filters; do not assume every publicly queryable record permits unrestricted reuse.

Other deployments can require OAuth bearer tokens or separate access controls. These CLIs do
not implement authenticated access. Do not put credentials in `--base-url`. GISAID-derived access
is outside the verified open workflow; do not infer its access method from these deployments.
Open GenBank/INSDC and GISAID datasets have different coverage and submission processes, so neither
strict set inclusion nor comparable proportions should be assumed.

Official sources: [authentication](https://lapis.cov-spectrum.org/open/v2/docs/concepts/authentication),
[Pathoplexus API usage](https://pathoplexus.org/docs/how-to/search-download-seqs-api),
[Pathoplexus terms](https://pathoplexus.org/about/terms-of-use).

## Endpoint methods and response shapes

Use `<base>/api-docs` for the deployment's generated OpenAPI. The introductory documentation's
statement that every endpoint supports GET and POST is too broad; inspected schemas distinguish:

| Path | Methods | Response/purpose |
| --- | --- | --- |
| `/sample/aggregated` | GET, POST | `data` rows with `count`, grouped by `fields`; `info` envelope |
| `/sample/details` | GET, POST | metadata rows; `fields` is a projection |
| `/sample/aminoAcidMutations`, `/sample/nucleotideMutations` | GET, POST | site-wise mutation count, coverage, proportion |
| `/sample/aminoAcidInsertions`, `/sample/nucleotideInsertions` | GET, POST | insertion counts; separate from mutations |
| `/sample/databaseConfig` | GET | raw schema object, including `schema.metadata` |
| `/sample/referenceGenome` | GET | `nucleotideSequences` and `genes`, each with `name` and reference sequence |
| `/sample/lineageDefinition/{column}` | GET | raw lineage dictionary for an indexed column |
| `/sample/info` | GET | raw `dataVersion`, `lapisVersion`, `siloVersion`, request provenance |
| `/sample/unalignedNucleotideSequences`, `/sample/alignedNucleotideSequences` | GET, POST | nucleotide sequences; FASTA or specified supported format |
| `/sample/unalignedNucleotideSequences/{segment}`, `/sample/alignedNucleotideSequences/{segment}` | GET, POST | per-segment forms on segmented instances |
| `/sample/alignedAminoAcidSequences`, `/sample/alignedAminoAcidSequences/{gene}` | GET, POST | all or selected translated sequences |
| `/sample/mostRecentCommonAncestor`, `/sample/phyloSubtree` | GET, POST | tree queries requiring a supported `phyloTreeField` |
| `/component/queriesOverTime` | POST | JSON `filters`, `dateField`, `dateRanges`, `queries` |
| `/component/aminoAcidMutationsOverTime`, `/component/nucleotideMutationsOverTime` | POST | JSON `filters`, `dateField`, `dateRanges`, `includeMutations` |

Component `dateRanges` entries use `dateFrom`/`dateTo`; `dateField` chooses the actual schema
column. `queries` entries specify `countQuery`, optional `coverageQuery` and `displayLabel`.
These component/tree/download routes were schema-reviewed, not exercised with large datasets.
Tree results ignore records absent from the tree; MRCA reports `missingNodeCount` and supports
`printNodesNotInTree`. Inspect the response schema rather than assume every filtered record has
an evolutionary placement.

GET uses URL parameters. POST query routes accept JSON with `Content-Type: application/json`;
arrays are JSON arrays. Form-encoded POST uses repeated keys. For GET, comma-delimited lists are
documented and repeated keys also work for metadata list filters. Unknown keys fail rather than
being silently ignored. The bundled CLIs issue GET requests only.

Sources: [SARS-CoV-2 OpenAPI](https://lapis.cov-spectrum.org/open/v2/api-docs),
[H5N1 OpenAPI](https://lapis.genspectrum.org/h5n1/api-docs),
[RSV-A OpenAPI](https://lapis.pathoplexus.org/rsv-a/api-docs),
[request methods](https://lapis.cov-spectrum.org/open/v2/docs/concepts/request-methods).

## Read the schema before filtering

`schema.metadata[]` declares `name`, `type` and optional `generateLineageIndex`. Since LAPIS 0.6,
that index value can be a string naming the index. Test for an enabled value, not identity with
boolean `true`. Indexed taxonomic fields such as `hostTaxonId` are not necessarily lineage calls.

`date`, `int`, and `float` fields support inclusive `<field>From`/`<field>To`; the date-analysis
scripts require `date`, not merely any range-capable field. A string holding a date is still a
string. In the reviewed schemas:

| Deployment | Collection | Submission/release | Geography |
| --- | --- | --- | --- |
| SARS-CoV-2 | `date` | `dateSubmitted` | `country` |
| GenSpectrum influenza | `sampleCollectionDateRangeLower` / `RangeUpper` | `ncbiReleaseDate` | `country` |
| Pathoplexus | `sampleCollectionDateRangeLower` / `RangeUpper` | `earliestReleaseDate` or `ncbiReleaseDate` | `geoLocCountry` |

`sampleCollectionDate` in the latter deployments is a string that can encode partial dates.
Choosing the lower range endpoint as though it were an exact date would put a month/year-only
sample into one arbitrary week. The bundled date analyses retain only equal lower/upper bounds.
A submission/release field is a provenance choice: NCBI release and first Pathoplexus release are
different events; neither guarantees the date the record first became queryable in this LAPIS.

Null filtering uses `<field>.isNull=true` or `false`; empty strings no longer mean null. The
scripts' `--where` is a narrow metadata filter interface; it does not expose every advanced
query feature, and repeated identical keys overwrite, rather than append, in these CLIs.

Sources: [database config](https://lapis.cov-spectrum.org/open/v2/sample/databaseConfig),
[LAPIS changelog](https://github.com/GenSpectrum/LAPIS/blob/main/CHANGELOG.md).

## Lineages and mutation rows

For an indexed column, `pangoLineage=XFG` is exact and `pangoLineage=XFG*` includes descendants.
Without an index, `*` is a literal string and can silently match zero records. The helper refuses
that query. An indexed invalid name can produce HTTP 400 while an unindexed typo produces zero.
The lineage-definition route is queried using the **metadata column name**, not the index ID.
It describes the query hierarchy; recombinant ancestry must be checked against the nomenclature
source. The observed Pango tree roots recombinant labels rather than linking their biological
parents.

Mutation rows contain `mutation`, `sequenceName`, `position`, `mutationFrom`, `mutationTo`,
`count`, `coverage`, `proportion`. The denominator is matching sequences with resolvable calls
at that site, not all matching sequences and not raw read depth. Deletions can occur as `-` in
mutation results; insertions have separate endpoints.

`minProportion` defaults to 0.05. Comparisons fetch with zero cutoff, then apply the reporting
threshold locally. A missing mutation row still does not provide the opposite side's coverage
or prove a zero frequency; the comparison preserves missing values and labels `not_comparable`.
AA genes and nucleotide sequence names are distinct namespaces (`HA` versus `seg4`, `S` versus
`main`). Validate against `referenceGenome`; positions refer to that declared reference.

Source: [mutation filters](https://lapis.cov-spectrum.org/open/v2/docs/concepts/mutation-filters/).

## Aggregation, ordering and pagination

`fields` is group-by on `/sample/aggregated`. The current SARS-CoV-2 deployment accepts
`fields=date.isoWeek`, returning keys named `date.isoWeek` and values such as `2026-W36`.
This computed field was introduced after the older deployment versions. The scripts retain
client-side ISO-week grouping for compatibility and exact-date checks.

The previous blanket claim that aggregation rejects `limit`, `offset`, and `orderBy` is stale.
SARS-CoV-2 0.8.7/0.14.3 accepts them; bounded live checks succeeded for `fields=country&orderBy=count&limit=2`
and for `limit=2` without order. The latter is not stable pagination. Use an explicit deterministic
order, unique tie-breakers among grouped fields, and consistent response versions when paging.
`count:desc` is not a valid GET field syntax on this server. Consult that deployment's order schema
rather than invent suffixes. Older SILO deployments may reject aggregate pagination.
The bundled aggregate helper retrieves all groups without limits, so it cannot accidentally
compute totals from only one page. Keep group cardinality and date windows bounded.

Sources: [computed fields](https://lapis.cov-spectrum.org/open/v2/docs/concepts/computed-fields),
[OpenAPI](https://lapis.cov-spectrum.org/open/v2/api-docs).

## Errors and reproducibility

HTTP errors can contain either `{"error":{"detail":...},"info":...}` or a bare problem-details
object. Surface the message while treating it as untrusted data. Retry transient 429/500/502/503/504
at most three times with 1.5/3-second waits; these scripts do not implement server-specific quotas
or `Retry-After`, so stop and wait manually if a deployment continues throttling.

JSON data responses carry `info.dataVersion`; raw info uses `dataVersion`, and the HTTP header is
`lapis-data-version`. The client compares actual successful response versions and fails before
emitting a result when they change. An independent info request alone cannot certify all data.
Schema responses need not carry versions. The helpers use a schema cache only inside the process.

Data versions identify the currently served snapshot, not an archive or a request parameter for
replaying old data. Preserve actual responses, source/configuration files, request parameters and
retrieval time for an auditable result. Pango file digests are SHA-256 of fetched content, not
GitHub ETags interpreted as Git IDs. Moving Pango files can update between independent requests;
archive a single repository commit when coherent historical nomenclature is required.

Source: [data versions](https://lapis.cov-spectrum.org/open/v2/docs/concepts/data-versions).
