# Interest Rates & Exchange Rate Datasets — U.S. Treasury Fiscal Data

## Average Interest Rates on U.S. Treasury Securities

**Endpoint:** `/v2/accounting/od/avg_interest_rates`  
**Frequency:** Monthly  
**Date Range:** January 2001 to present

Average interest rates for marketable and non-marketable Treasury securities, broken down by security type.

**Key fields:**
| Field | Type | Description |
|-------|------|-------------|
| `record_date` | DATE | Month end date |
| `security_desc` | STRING | Security description (e.g., "Treasury Bills") |
| `security_type_desc` | STRING | "Marketable" or "Non-marketable" |
| `avg_interest_rate_amt` | PERCENTAGE | Average interest rate (%) |

```python
# Get average rates for all marketable securities, most recent month
resp = requests.get(
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates",
    params={
        "filter": "security_type_desc:eq:Marketable",
        "sort": "-record_date",
        "page[size]": 50
    },
    timeout=30,
)
resp.raise_for_status()
df = pd.DataFrame(resp.json()["data"])
latest = df[df["record_date"] == df["record_date"].max()]
print(latest[["security_desc", "avg_interest_rate_amt"]])

# First-page preview of historical rates for a specific security type
resp = requests.get(
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates",
    params={
        "fields": "record_date,avg_interest_rate_amt",
        "filter": "security_desc:eq:Treasury Notes,record_date:gte:2010-01-01",
        "sort": "-record_date"
    },
    timeout=30,
)
resp.raise_for_status()
```

**Common security descriptions:**
- `Treasury Bills`
- `Treasury Notes`
- `Treasury Bonds`
- `Treasury Inflation-Protected Securities (TIPS)`
- `Treasury Floating Rate Notes (FRN)`
- `Federal Financing Bank`
- `United States Savings Securities`
- `Government Account Series`
- `Total Marketable`
- `Total Non-marketable`
- `Total Interest-bearing Debt`

---

## Treasury Reporting Rates of Exchange

**Endpoint:** `/v1/accounting/od/rates_of_exchange`  
**Frequency:** Quarterly  
**Date Range:** March 2001 to present

Official Treasury exchange rates for foreign currencies used by federal agencies for reporting purposes. Updated quarterly (March 31, June 30, September 30, December 31).

**Key fields:**
| Field | Type | Description |
|-------|------|-------------|
| `record_date` | DATE | Quarter end date |
| `country` | STRING | Country name |
| `currency` | STRING | Currency name |
| `country_currency_desc` | STRING | Combined "Country-Currency" (e.g., "Canada-Dollar") |
| `exchange_rate` | NUMBER | Units of foreign currency per 1 USD |
| `effective_date` | DATE | Date rate became effective |

Fetch the latest `record_date` first, then fetch **all pages** for that date with
all columns retained. A fixed page of 200 rows can omit currencies/amendments.
Use `country_currency_desc:eq:Euro Zone-Euro` for euro history, preserving both
`record_date` and `effective_date`. See [examples.md](examples.md).

Amendments are separate rows with later effective dates; a rate amended at month
end applies to the remaining months of the quarter described in the official
notes. Do not silently deduplicate a currency without choosing a reporting period.
Multiply USD by the rate for foreign currency; divide foreign currency by the rate
for USD. These are reporting rates, not daily market quotes.

---

## TIPS and CPI Data

Two data tables under `/v1/accounting/od/`:

| Table | Endpoint | Description |
|-------|----------|-------------|
| Summary | `/v1/accounting/od/tips_cpi_data_summary` | Reference CPI numbers and daily index ratios (summary) |
| Detail | `/v1/accounting/od/tips_cpi_data_detail` | Reference CPI numbers and daily index ratios (detail) |

**Frequency:** Monthly  
**Date Range:** April 1998 to present

Treasury Inflation-Protected Securities (TIPS) reference CPI data and index ratios used to calculate TIPS values.

The summary table describes securities; daily observations live in detail. Neither table uses `record_date`.

**Key fields:**
| Field | Type | Description |
|-------|------|-------------|
| `cusip` | STRING | Security identifier in both tables |
| `index_date` | DATE | Daily observation date in the detail table |
| `index_ratio` | NUMBER | Detail table index ratio |
| `ref_cpi` | NUMBER | Detail table reference CPI |
| `ref_cpi_on_dated_date` | NUMBER | Base CPI in the summary table |

---

## FRN Daily Indexes

**Endpoint:** `/v1/accounting/od/frn_daily_indexes`  
**Frequency:** Monthly release (daily index rows per CUSIP)  
**Date Range:** October 2024 onward (current API coverage)

Daily index values for Treasury Floating Rate Notes (FRNs). The rate is based on the 13-week Treasury bill auction rate. Data is published monthly with daily index rows for each CUSIP.

---

## Treasury Certified Interest Rates

Four certification periods, each with their own endpoint set:

### Annual Certification
**Frequency:** Annual  
**Date Range:** October 2006 to present (9 data tables)

### Monthly Certification  
**Frequency:** Monthly  
**Date Range:** October 2006 to present (6 data tables)

### Quarterly Certification
**Frequency:** Quarterly  
**Date Range:** October 2006 to present (4 data tables)

### Semi-Annual Certification
**Frequency:** Semi-Annual  
**Date Range:** January 2008 to present (1 data table)

These certified interest rates are used for federal loans, financing programs, and other purposes requiring official Treasury-certified rates.

---

## Federal Credit Similar Maturity Rates

**Endpoint:** `/v1/accounting/od/federal_maturity_rates`  
**Frequency:** Annual  
**Date Range:** September 1992 to present

Interest rates used for valuing federal credit programs (loans and loan guarantees) under the Federal Credit Reform Act.

---

## Historical Qualified Tax Credit Bond Interest Rates

**Frequency:** Daily (Discontinued)  
**Date Range:** March 2009 – January 2018

Historical interest rates for Qualified Tax Credit Bonds (QTCB). No longer updated.

---

## State and Local Government Series (SLGS) Daily Rate Table

**Endpoints:** `/v1/accounting/od/slgs_demand_deposit_rates` and
`/v1/accounting/od/slgs_time_deposit_rates`
**Frequency:** Daily  
**Date Range:** June 1992 to present

Daily interest rates for State and Local Government Series securities, used by state and local issuers to comply with federal tax law arbitrage restrictions.

## Official sources

Reviewed 2026-09-30 against the current dataset dictionaries and live API responses.

- [Average Interest Rates Treasury Securities](https://fiscaldata.treasury.gov/datasets/average-interest-rates-treasury-securities/)
- [Treasury Reporting Rates Exchange](https://fiscaldata.treasury.gov/datasets/treasury-reporting-rates-exchange/)
- [Tips Cpi Data](https://fiscaldata.treasury.gov/datasets/tips-cpi-data/)
- [Slgs Daily Rate Table](https://fiscaldata.treasury.gov/datasets/slgs-daily-rate-table/)
