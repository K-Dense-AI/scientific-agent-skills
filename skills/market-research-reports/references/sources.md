# Dated Source Ledger

Documentation review cutoff: **2026-10-01**. Synthetic asset dates are fixture
values and are not evidence of current market conditions.

The refresh checked current official pages, API guides, and primary methodological
sources. It did not execute authenticated data requests or collect market data.
Dates below describe the source, not a dataset vintage or an executed API test.
The EUR-Lex full notice returned an access challenge; its identity and broad scope
were checked through the official Commission page and EUR-Lex summary.

## Corporate filings and U.S. official data

| ID | Authority | Source and date | Use |
|---|---|---|---|
| SRC-SEC-ACCESS | U.S. SEC | [Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data), published 2021-03-23; updated 2024-06-26 | EDGAR history, corrections, declared user agent, 10 requests/second fair-access limit |
| SRC-SEC-DEV | U.S. SEC | [Developer Resources](https://www.sec.gov/about/developer-resources), updated 2025-03-10 | Submissions and XBRL APIs; fair-access overview |
| SRC-CENSUS-API | U.S. Census Bureau | [Census Data API User Guide](https://www.census.gov/data/developers/guidance/api-user-guide.html), dated 2026-05-12; revised 2026-05-14 | Geography/vintage concepts and API navigation |
| SRC-CENSUS-LIMIT | U.S. Census Bureau | [Query Limits](https://www.census.gov/data/developers/guidance/api-user-guide.Query_Limits.html), revised 2026-05-14 | 50 variables/query; key required for data queries |
| SRC-CENSUS-KEY | U.S. Census Bureau | [API Key](https://www.census.gov/data/developers/guidance/api-user-guide.API_Key.html), revised 2026-05-14 | Current free key-registration guidance |
| SRC-EC-METHOD | U.S. Census Bureau | [2022 Economic Census Methodology](https://www.census.gov/programs-surveys/economic-census/year/2022/technical-documentation/methodology.html), updated 2026-04-10 | Population, frame, NAICS scope, collection, administrative data, imputation, disclosure avoidance |
| SRC-NAICS | U.S. Census Bureau | [NAICS](https://www.census.gov/naics), 2022 edition | Current published structure and 2027 revision process |
| SRC-BLS-API | U.S. Bureau of Labor Statistics | [Public Data API FAQ](https://www.bls.gov/developers/api_faqs.htm), modified 2023-08-30 | Registration, daily/rate/series/year limits, metadata behavior |
| SRC-BEA-API | U.S. Bureau of Economic Analysis | [BEA API User Guide](https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf), 2026-04-20 | UserID, metadata calls, 100 requests/minute, 100 MB/minute, 30 errors/minute, HTTP 429/retry |
| SRC-BEA-CHAIN | U.S. Bureau of Economic Analysis | [Chained-Dollar Indexes: Issues and Tips](https://www.bea.gov/resources/methodologies/chained-dollar-indexes), published 2003-11; page modified 2018-05-30 | Real/current measures, chain weighting, non-additivity |
| SRC-FRED-API | Federal Reserve Bank of St. Louis | [FRED API](https://fred.stlouisfed.org/docs/api/fred/), date not stated | v1 series/ALFRED access; v2 bulk release history; metadata and vintage endpoints |
| SRC-FRED-TERMS | Federal Reserve Bank of St. Louis | [FRED API Terms](https://fred.stlouisfed.org/docs/api/terms_of_use.html), date not stated | Key requirement, changeable limits, application notice, third-party rights |

## International and national statistical systems

| ID | Authority | Source and date | Use |
|---|---|---|---|
| SRC-WB-API | World Bank | [Indicators API Documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation), date not stated | v2 current; v1 discontinued; no API authentication; source metadata |
| SRC-WB-WDI | World Bank | [World Development Indicators catalog](https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators), metadata updated 2026-07-20 | Metadata, classifications, and separately dated revision-history resources |
| SRC-IMF-API | International Monetary Fund | [IMF Data APIs](https://data.imf.org/en/Resource-Pages/IMF-API), publication date not stated | SDMX 2.1 and 3.0; portal sign-in for Swagger exploration |
| SRC-IMF-SDMX | International Monetary Fund | [IMF SDMX Central Web Services Guide](https://dsbb.imf.org/content/pdfs/IMFSDMXCentralWebServicesGuide.pdf), updated 2025-05 | Structure, validation, conversion, and registration services; separate from data-download API discovery |
| SRC-OECD-API | OECD | [OECD data via API](https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html), 2025-04-30 | SDMX syntax, dataflow version warning, formats, terms, nonnumeric rate-limiting statement |
| SRC-OECD-SUT | OECD | [Supply and Use Tables](https://www.oecd.org/en/data/datasets/supply-and-use-tables.html), date not stated | Product/industry supply-use framework and origin/use of goods and services |
| SRC-EUROSTAT-API | Eurostat | [API Introduction](https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-introduction), date not stated | Statistics/SDMX services, formats, twice-daily updates, latest-version-only caveat |
| SRC-ESS-QUALITY | Eurostat | [ESS Handbook for Quality and Metadata Reports](https://ec.europa.eu/eurostat/web/products-manuals-and-guidelines/-/ks-gq-21-021), 2021-12-09 | Standardized quality and metadata reporting |
| SRC-NACE | Eurostat | [NACE Rev. 2.1 manual announcement](https://ec.europa.eu/eurostat/web/products-eurostat-news/w/wdn-20250624-1), 2025-06-24 | Current NACE manual, principles, explanatory notes, correspondence tables |
| SRC-STATCAN-WDS | Statistics Canada | [Web Data Service User Guide](https://www.statcan.gc.ca/en/developers/wds/user-guide), revision 1.6 dated 2025-01-24 | Data/metadata service, update window, 50 server and 25 per-IP requests/second |
| SRC-ONS-API | UK Office for National Statistics | [ONS Developer Hub](https://developer.ons.gov.uk/), date not stated; beta | Open/no-key API; dataset/edition/version and breaking-change warning |

## Market definition, uncertainty, and research methods

| ID | Authority | Source and date | Use |
|---|---|---|---|
| SRC-US-MERGER | U.S. DOJ and FTC | [2023 Merger Guidelines](https://www.justice.gov/atr/merger-guidelines), 2023-12-18 | Official HTML sections for relevant markets, shares, HHI, evidence, dynamic and potential competition |
| SRC-EU-MARKET | European Commission | [Market Definition Notice](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:C_202401645), 2024-02-22 | Product/geographic scope, non-price competition, digital/dynamic markets, alternate share metrics, evidence |
| SRC-OMB-A4 | U.S. Office of Management and Budget | [Circular A-4](https://www.whitehouse.gov/wp-content/uploads/2025/08/CircularA-4.pdf), 2003-09-17; reinstated by [M-25-15](https://www.whitehouse.gov/wp-content/uploads/2025/03/M-25-15-Recission-and-Reinstatement-of-Circular-A-4.pdf), dated 2025-02-12 | Uncertainty, sensitivity, assumptions, transparent presentation; 2023 revision revoked |
| SRC-GREENBOOK | UK HM Treasury | [The Green Book 2026](https://www.gov.uk/government/publications/the-green-book-appraisal-and-evaluation-in-central-government/the-green-book-2026), updated 2026-02-05 | Appraisal, options, uncertainty, evidence, and transparent assumptions |
| SRC-AAPOR-CODE | American Association for Public Opinion Research | [Code of Professional Ethics and Practices](https://aapor.org/standards-and-ethics/), revised 2026-06 | Current participant, privacy, sponsor, public, integrity, and disclosure duties |
| SRC-AAPOR-DISC | American Association for Public Opinion Research | [Disclosure Standards](https://aapor.org/standards-and-ethics/disclosure-standards/), code approved 2021-04; page published 2022-12-02 | Sponsor, instrument, population, sample, mode, dates, weighting, precision, limitations, privacy |
| SRC-AAPOR-BEST | AAPOR | [Best Practices for Survey Research](https://aapor.org/standards-and-ethics/best-practices/), page published 2023-01-11 | Survey design, probability/non-probability samples, wording, weighting, reporting |
| SRC-FCSM-NR | Federal Committee on Statistical Methodology | [Best Practices for Nonresponse Bias Reporting](https://statspolicy.gov/assets/fcsm/files/docs/FCSM%20NRBA%20Report%20062623.pdf), 2023-06 | Response-rate and subgroup nonresponse-bias reporting |
| SRC-ICSP-QUALITY | Interagency Council on Statistical Policy | [Principles for Modernizing Production of Federal Statistics](https://statspolicy.gov/assets/fcsm/files/docs/Principles-2.pdf), 2018 | Quality, transparency, and limitations for statistical/non-statistical integrated data |
| SRC-FORCE11 | FORCE11 | [Joint Declaration of Data Citation Principles](https://force11.org/group/joint-declaration-of-data-citation-principles-final), 2014; page date not stated | Importance, credit, evidence, unique identification, access, persistence, specificity |
| SRC-ICO-MIN | UK Information Commissioner's Office | [Data minimisation](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-protection-principles/a-guide-to-the-data-protection-principles/data-minimisation), updated 2025-09-09 | Collecting data adequate, relevant, and limited to purpose where UK GDPR applies |

## Software and rendering

- [Python datetime](https://docs.python.org/3/library/datetime.html): calendar-date
  parsing accepts additional ISO formats since Python 3.11; the bundled ledgers
  deliberately require the narrower `YYYY-MM-DD` contract.
- [fontspec](https://ctan.org/pkg/fontspec): Unicode font selection for XeLaTeX
  and LuaLaTeX; the report uses TeX Gyre Heros.
- [tcolorbox](https://ctan.org/pkg/tcolorbox): breakable evidence and uncertainty
  boxes. Compilation and visual inspection validate the local template, not the
  truth of placeholder claims.

Local template checks used TeX Live 2025 (XeTeX 0.999997 and LuaHBTeX 1.21.0),
with two compilation passes per engine and rendered-page inspection. Current
fontspec documentation was reviewed; this is not a claim to have tested every
package's latest release.

## Research query record

Focused search/extract objectives covered:

- SEC EDGAR, Census, BLS, BEA, FRED access, metadata, terms, and limits;
- World Bank, IMF, OECD, Eurostat, Statistics Canada, and ONS APIs;
- NAICS/NACE versions and classification correspondence;
- supply-use/economic-census methods for sizing and double-count prevention;
- U.S. and EU competition/market-definition guidance;
- OMB and HM Treasury forecast uncertainty and sensitivity;
- AAPOR/FCSM survey disclosure and nonresponse;
- data citation, provenance, metadata quality, privacy, and ethical collection.

No Parallel search JSON artifacts are included in the skill.
