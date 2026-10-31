# Official Data and Filing Sources

Reviewed against first-party guidance on 2026-10-01. API rules can change:
recheck the linked terms and limits before automated or high-volume use. The
bundled scripts do not call these services and do not require API keys.
This is a routing and metadata guide, not an executed API client: documentation
review does not establish authenticated retrieval or current service availability.

## Routing by claim

Start with the original authority most fit for the claim:

- company financials and risk disclosures: the jurisdiction's official filing
  system, then the filed document;
- establishment, employment, prices, production, trade, population, and GDP:
  the responsible national statistical office or central bank;
- rules, approvals, enforcement, licenses, and consultations: the responsible
  regulator or official legal gazette;
- cross-country indicators: the original national source when comparability is
  not required; otherwise an international harmonized dataset with metadata;
- classifications: the current official NAICS, NACE, ISIC, product, trade, or
  sector taxonomy and its correspondence tables.

Do not treat an aggregator as an independent corroborating source when it
reproduces the same underlying series.

## United States

### SEC EDGAR and company filings

- [SEC Developer Resources](https://www.sec.gov/about/developer-resources)
  documents company submissions and extracted XBRL data APIs.
- [Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
  requires a declared user agent and states a current maximum of 10 requests per
  second across the user's machines. Download only what is needed.
- EDGAR filings can be corrected or removed after acceptance. Record accession
  number, form, filing date, reporting period, amendment status, exact table or
  XBRL fact, units, and retrieval date.
- Consolidated company revenue is not automatically market revenue. Remove
  out-of-scope products/geographies and avoid summing parent/subsidiary or
  channel/end-customer values twice.

### U.S. Census Bureau

- The [Census Data API User Guide](https://www.census.gov/data/developers/guidance/api-user-guide.html)
  links data to a geographic boundary and a dataset vintage.
- As revised 2026-05-14, the
  [query-limits page](https://www.census.gov/data/developers/guidance/api-user-guide.Query_Limits.html)
  permits up to 50 variables per query and requires a key for all data queries.
  The [key page](https://www.census.gov/data/developers/guidance/api-user-guide.API_Key.html)
  describes free registration. The key travels in the query URL; redact `key`
  before storing source URLs, logs, or request provenance. Never place a key in a
  report, source ledger, or bundled script.
- Use program-specific methodology, margins of error, universe, geography, and
  vintage. ACS estimates, Population Estimates, and decennial counts are not
  interchangeable.
- The [2022 Economic Census methodology](https://www.census.gov/programs-surveys/economic-census/year/2022/technical-documentation/methodology.html)
  defines the target population, sampling frame, exclusions, administrative
  data, imputation, disclosure avoidance, and product collection.
- The [NAICS site](https://www.census.gov/naics) identifies 2022 NAICS as the
  current published structure while a 2027 revision process is underway. Store
  the version used.

### Bureau of Labor Statistics

The [BLS API FAQ](https://www.bls.gov/developers/api_faqs.htm), last modified
2023-08-30, documents:

- registered v2: 500 queries/day, 50 series/query, 20 years/query;
- unregistered v1: 25 queries/day, 25 series/query, 10 years/query;
- both: 50 requests per 10 seconds;
- v2 registration renewal at least annually;
- v1 returns observations and footnotes without descriptive metadata.

Record series ID, survey/program, seasonal adjustment, units, frequency,
footnotes, publication date, and revision status. Consult the program's
methodology and release calendar rather than relying on the API response alone.
Inspect `message` and each series' observations even when the response says
`REQUEST_SUCCEEDED`: the FAQ shows invalid-series messages with that status.

### Bureau of Economic Analysis

The [BEA API User Guide](https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf),
dated 2026-04-20, requires a registered UserID and documents three rolling
per-minute limits:

- 100 requests;
- 100 MB retrieved;
- 30 errors.

BEA returns HTTP 429 and a `Retry-After` header when throttled. The guide warns
that limits may change. Query metadata methods before data, restrict years and
dimensions, and avoid broad `ALL` requests. Record current versus chained
dollars, reference year, table/line code, frequency, seasonality, and release
vintage. Chained-dollar components may not be additive; use published
contributions or current-dollar shares where appropriate.
Check `BEAAPI.Results.Error` as well as HTTP status; request parameters may be
echoed in the response, so redact `UserID` before archiving it.

### Federal Reserve and FRED/ALFRED

- [FRED API documentation](https://fred.stlouisfed.org/docs/api/fred/) describes
  v2 bulk release history and v1 series-level FRED/ALFRED access.
- A registered key is required under the
  [FRED API Terms](https://fred.stlouisfed.org/docs/api/terms_of_use.html).
  The reviewed terms do not state one fixed numerical request ceiling; they
  reserve the right to impose or change limits.
- The terms warn that third parties may own series and impose additional
  restrictions. Follow the original producer's rights and attribution.
- FRED normally presents latest values; ALFRED preserves real-time vintages.
  Record source, release, series ID, frequency, units, seasonal adjustment,
  notes, and vintage dates.

## International and harmonized sources

### World Bank

The [Indicators API documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation)
states that v2 is current, v1 is discontinued, and API authentication is not
required. Preserve indicator code, database/source, source note, source
organization, unit, income/region classification vintage, and retrieval date.
The [WDI catalog](https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators)
publishes metadata and revision-history resources. A World Bank indicator may
originate with a national agency or another international organization; retain
that lineage.

### International Monetary Fund

The [IMF Data API page](https://data.imf.org/en/Resource-Pages/IMF-API) states
that IMF data are available through SDMX 2.1 and SDMX 3.0 APIs. Use the
dataset's data structure, codelists, unit, scale, frequency, observation status,
and methodological metadata. Do not assume similarly named indicators across
IMF datasets have identical definitions.
Use the current API portal linked on that page (its Swagger explorer requires
portal sign-in) to select a data service and verify its access requirements.
The separate SDMX Central guide concerns structure, validation, conversion, and
registration services; it does not establish a data-download endpoint contract.

### OECD

The [OECD Data Explorer API guide](https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html),
published 2025-04-30, describes the SDMX API, free access subject to OECD terms,
and rate limiting without publishing one universal numerical ceiling on that
page. It warns that omitting a dataflow version selects the latest version and
that later structures may not be backward compatible. Store agency, dataset,
dataflow version, dimensions, codes, attributes, and query.

### Eurostat

The [Eurostat API introduction](https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-introduction)
documents Statistics, SDMX 2.1, SDMX 3.0, catalogue, and asynchronous services.
It states that datasets are updated twice daily when changes are available and
that the database contains only the latest version, without past-version
documentation. Preserve the retrieved file and update timestamp when a
reproducible vintage matters.

The [ESS quality and metadata handbook](https://ec.europa.eu/eurostat/web/products-manuals-and-guidelines/-/ks-gq-21-021)
is a standard for reporting source, process, quality, and metadata. Record flags,
breaks, seasonal adjustment, units, NUTS/geography version, and dataset code.

### Other national statistical agencies

Use the relevant country's official agency before secondary compilations.
Examples of current first-party interfaces:

- [Statistics Canada Web Data Service](https://www.statcan.gc.ca/en/developers/wds/user-guide)
  provides data and metadata. Guide revision 1.6 (2025-01-24) documents a
  50-request/second server limit and 25-request/second individual IP limit, and
  possible HTTP 409 responses during update windows.
- The [UK ONS Developer Hub](https://developer.ons.gov.uk/) describes an open,
  no-key beta API. It warns that breaking changes can occur; store dataset,
  edition, and version because new versions reflect corrections, revisions, or
  new data.

For any country, confirm:

1. the official statistics producer and legal mandate;
2. release calendar, methodology, quality statement, and revision policy;
3. classification and geography versions;
4. API/download terms and current operational limits;
5. whether the dataset is official, experimental, modeled, or an administrative
   extract.

## Industry and product classifications

- [NAICS](https://www.census.gov/naics) classifies establishments by primary
  economic activity; it is not itself a product-market definition.
- [NACE Rev. 2.1](https://ec.europa.eu/eurostat/web/products-eurostat-news/w/wdn-20250624-1)
  began feeding European statistics from 2025. Use the 2025 manual and
  correspondence tables when comparing Rev. 2 and Rev. 2.1.
- Product classifications (NAPCS, CPA, PRODCOM, CPC, HS/CN) may fit market
  outputs better than an establishment-based industry code.
- A concordance can be one-to-many or many-to-many. Never apply it as a
  lossless conversion without weights and uncertainty.

## API handling rules

- Use APIs only during research, with user-approved network access.
- Keep credentials outside reports and scripts; never commit keys.
- Respect official terms, user-agent requirements, rate limits, retries, and
  bulk-download guidance.
- Cache lawful downloads, record the exact query and retrieval time, and avoid
  repeatedly requesting unchanged data.
- Validate response status, metadata, units, flags, suppression, and missing
  values before analysis.
- Treat current limits in this file as a dated snapshot, not a permanent
  entitlement.
