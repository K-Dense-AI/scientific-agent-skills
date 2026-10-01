# Code Examples — U.S. Treasury Fiscal Data

Python queries and transformations below were exercised against the public API on
2026-09-30. First define `fetch_all()` from [parameters.md](parameters.md), then run
the setup. Historic dates are fixed examples, not claims about the current year.

## Setup

```python
from datetime import date
from decimal import Decimal
import requests
import pandas as pd

BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"

def fetch(endpoint, **params):
    """Fetch one page; callers requesting a complete result use fetch_all."""
    allowed = {"fields", "filter", "sort", "format", "page[size]", "page[number]"}
    if set(params) - allowed:
        raise ValueError(f"Unknown query parameters: {set(params) - allowed}")
    resp = requests.get(BASE_URL + endpoint, params=params, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if "error" in result:
        raise ValueError(result)
    return result
```

## National Debt Tracker

```python
result = fetch("/v2/accounting/od/debt_to_penny",
               sort="-record_date", **{"page[size]": 1})
d = result["data"][0]
debt = Decimal(d["tot_pub_debt_out_amt"])
print(f"National debt as of {d['record_date']}: ${debt:,.2f}")

# Complete fixed-period series; cents remain in raw strings if needed.
df = fetch_all("/v2/accounting/od/debt_to_penny", {
    "filter": "record_date:gte:2024-01-01,record_date:lte:2024-12-31",
    "sort": "record_date", "page[size]": 100,
})
df["date"] = pd.to_datetime(df["record_date"])
df["debt_trillion"] = pd.to_numeric(df["tot_pub_debt_out_amt"]) / 1e12
print(df[["date", "debt_trillion"]].tail())
```

## Treasury Reporting Exchange Rates

```python
endpoint = "/v1/accounting/od/rates_of_exchange"
quarter = fetch(endpoint, sort="-record_date", **{"page[size]": 1})["data"][0]["record_date"]
rates = fetch_all(endpoint, {
    "filter": f"record_date:eq:{quarter}",
    "sort": "country_currency_desc,effective_date,src_line_nbr",
    "page[size]": 100,
})
rates["exchange_rate"] = pd.to_numeric(rates["exchange_rate"])
# Preserve amendments as separate rows; pick the applicable reporting period first.
rates["usd_1000_in_foreign_currency"] = 1000 * rates["exchange_rate"]
print(rates[["country_currency_desc", "record_date", "effective_date",
             "exchange_rate", "usd_1000_in_foreign_currency"]].head())
```

These are foreign-currency units per USD. Divide a foreign amount by its applicable
rate to obtain USD. Amendments have later `effective_date` values; quarterly PDF
reports omit amendments, so do not collapse rows without the official period rules.

## Treasury Securities Auction Analysis

```python
# Nominal fixed-rate 10-year notes. auction_date dates the event.
result = fetch("/v1/accounting/od/auctions_query",
    filter="security_type:eq:Note,original_security_term:eq:10-Year,inflation_index_security:eq:No,floating_rate:eq:No",
    sort="-auction_date,cusip", **{"page[size]": 20})
auctions = pd.DataFrame(result["data"])
for col in ["high_yield", "bid_to_cover_ratio", "total_accepted", "indirect_bidder_accepted"]:
    auctions[col] = pd.to_numeric(auctions[col].replace("null", None), errors="coerce")
auctions["indirect_pct_of_total"] = (
    100 * auctions["indirect_bidder_accepted"] / auctions["total_accepted"].where(auctions["total_accepted"] > 0)
)
print(auctions[["auction_date", "cusip", "security_term", "reopening",
                "high_yield", "indirect_pct_of_total"]].head())
```

`original_security_term` includes reopened securities whose remaining
`security_term` is shorter. Name the denominator when reporting bidder shares;
`total_accepted` is not the same as competitive awards. Missing yields can mean an
auction has been announced but results are unavailable. Auction yields observed on
different dates do not form a same-date yield curve; do not inner-join 2-year and
10-year auctions on publication dates and label the difference a market spread.

## Daily Treasury Statement

```python
endpoint = "/v1/accounting/dts/operating_cash_balance"
closing = fetch(endpoint,
    filter="account_type:eq:Treasury General Account (TGA) Closing Balance",
    sort="-record_date", **{"page[size]": 5})
for row in closing["data"]:
    print(row["record_date"], Decimal(row["open_today_bal"]), "million USD, closing TGA")

# Named totals avoid adding category detail to summary rows.
cash = fetch_all(endpoint, {
    "filter": "record_date:gte:2024-01-01,record_date:lte:2024-01-31",
    "sort": "record_date,src_line_nbr",
})
cash = cash[cash["account_type"].isin([
    "Total TGA Deposits (Table II)", "Total TGA Withdrawals (Table II) (-)",
])].copy()
cash["million_usd"] = pd.to_numeric(cash["open_today_bal"])
print(cash.pivot(index="record_date", columns="account_type", values="million_usd"))
```

Since April 18, 2022, `close_today_bal` is null. The closing-balance account row
stores its value in `open_today_bal`. Earlier layouts need separate handling.
DTS cash movements include financing and differ from MTS budget receipts/outlays.

## Monthly Budget Summary

```python
budget = fetch_all("/v1/accounting/mts/mts_receipts_outlays_deficit_surplus", {
    "filter": "record_fiscal_year:eq:2024",
    "sort": "record_date,src_line_nbr",
})
budget = budget[budget["amt_category"].isin(["Receipts", "Outlays", "Deficit/Surplus (-)"])].copy()
budget["million_usd"] = pd.to_numeric(budget["mil_amt"])
monthly = budget.pivot(index="record_date", columns="amt_category", values="million_usd")
assert len(monthly) == 12, "Fiscal year is incomplete"
# Published values are rounded to millions; allow rounding differences.
residual = monthly["Outlays"] - monthly["Receipts"] - monthly["Deficit/Surplus (-)"]
if (residual.abs() > 1).any():
    print("[WARN] Reconcile source revisions/footnotes before using these months:")
    print(residual[residual.abs() > 1])
print(monthly)
```

The live FY2024 extract on the review date had a March 2024 reconciliation
residual of -270 million USD, beyond rounding. This example exposes that source
discrepancy; it does not treat the series as reconciled or overwrite the published
values. Check the matching report/revisions before drawing budget conclusions.

This summary has explicit million-dollar units. Tables 1 and 9 have different
fields and dollar-scale API values; Table 1 repeats prior months and fiscal-year
sections in each publication. Never add all Table 1 rows to obtain monthly totals.

## Average Treasury and I Bond Rates

```python
rates = fetch_all("/v2/accounting/od/avg_interest_rates", {
    "filter": "security_type_desc:eq:Marketable,record_date:gte:2024-01-01,record_date:lte:2024-12-31",
    "sort": "record_date,src_line_nbr",
})
rates["rate_pct"] = pd.to_numeric(rates["avg_interest_rate_amt"])
print(rates.pivot(index="record_date", columns="security_desc", values="rate_pct"))

# One issue vintage and a fixed earning-period cutoff, not a universal I Bond rate.
issue_month = "2024-05"
bonds = fetch("/v1/accounting/od/i_bonds_interest_rates",
    filter=f"issue_year_month:eq:{issue_month},earning_period_start:lte:2024-11-01",
    sort="-earning_period_start", **{"page[size]": 1})
print(pd.DataFrame(bonds["data"])[["issue_year_month", "earning_period_start",
                                  "earning_period_end", "fixed_rate", "combined_rate"]])
```

Average interest rates describe the outstanding debt portfolio, not current
market yields. I Bond fixed rates depend on issue vintage; the earning-period
columns and issue month must be retained together.

## Completed Fiscal-Year Interest Expense

```python
fy = 2024
expenses = fetch_all("/v2/accounting/od/interest_expense", {
    "filter": f"record_fiscal_year:eq:{fy}",
    "sort": "record_date,src_line_nbr",
})
assert expenses["record_date"].nunique() == 12, "Fiscal year is incomplete"
assert expenses["record_date"].max() == f"{fy}-09-30"
assert not expenses.duplicated(["record_date", "src_line_nbr"]).any()
monthly_total = sum(Decimal(x) for x in expenses["month_expense_amt"])
september = expenses[expenses["record_date"] == f"{fy}-09-30"]
fytd_total = sum(Decimal(x) for x in september["fytd_expense_amt"])
assert abs(monthly_total - fytd_total) <= Decimal("0.01"), "Reconcile revisions/components"
print(f"FY{fy} public-debt interest expense: ${fytd_total:,.2f}")
```

This uses the expense dataset's components and accounting basis, not budget net
interest. Sum monthly flows once, or take September FYTD once; never sum FYTD
values across months. Preserve category/group/type fields to inspect components.

## R example (illustrative; R runtime not exercised)

```r
library(httr)
library(jsonlite)
base <- "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
response <- GET(paste0(base, "/v1/accounting/mts/mts_table_9"),
                query = list(filter = "line_code_nbr:eq:120",
                             sort = "-record_date", `page[size]` = 1),
                timeout(30))
stop_for_status(response)
result <- fromJSON(rawToChar(response$content))
stopifnot(nrow(result$data) == 1)
print(result$data[c("record_date", "classification_desc", "current_month_rcpt_outly_amt")])
```

## Discovering fields and datasets

```python
result = fetch("/v2/accounting/od/debt_to_penny", **{"page[size]": 1})
for field, label in result["meta"]["labels"].items():
    print(field, result["meta"]["dataTypes"][field], label)
```

Use the [dataset catalog](https://fiscaldata.treasury.gov/datasets/) and each
API Quick Guide/data dictionary for current paths, table coverage, units and
limitations. The [API guide](https://fiscaldata.treasury.gov/api-documentation/)
documents common filters, pagination and response metadata.
