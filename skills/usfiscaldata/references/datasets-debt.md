# Debt Datasets — U.S. Treasury Fiscal Data

## Debt to the Penny

**Endpoint:** `/v2/accounting/od/debt_to_penny`  
**Frequency:** Daily  
**Date Range:** 1993-04-01 to present

Tracks the exact total public debt outstanding each business day.

**Key fields:**
| Field | Type | Description |
|-------|------|-------------|
| `record_date` | DATE | Date of record |
| `debt_held_public_amt` | CURRENCY | Debt held by the public |
| `intragov_hold_amt` | CURRENCY | Intragovernmental holdings |
| `tot_pub_debt_out_amt` | CURRENCY | **Total public debt outstanding** |

```python
# Current national debt
resp = requests.get(
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny",
    params={"sort": "-record_date", "page[size]": 1},
    timeout=30,
)
resp.raise_for_status()
latest = resp.json()["data"][0]
from decimal import Decimal
print(f"As of {latest['record_date']}: ${Decimal(latest['tot_pub_debt_out_amt']):,.2f}")

# Preview of debt since January 2024; fetch_all() is needed for the full series
resp = requests.get(
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny",
    params={
        "fields": "record_date,tot_pub_debt_out_amt",
        "filter": "record_date:gte:2024-01-01",
        "sort": "-record_date"
    },
    timeout=30,
)
resp.raise_for_status()
df = pd.DataFrame(resp.json()["data"])
df["tot_pub_debt_out_amt"] = df["tot_pub_debt_out_amt"].astype(float)
```

## Historical Debt Outstanding

**Endpoint:** `/v2/accounting/od/debt_outstanding`  
**Frequency:** Annual  
**Date Range:** 1790 to present

Annual record of U.S. national debt going back to the founding of the republic.

**Key fields:**
| Field | Type | Description |
|-------|------|-------------|
| `record_date` | DATE | Annual record date; historical fiscal-year conventions differ |
| `debt_outstanding_amt` | CURRENCY | Total debt outstanding |

```python
# Full historical debt series (verify it fits in the requested page)
resp = requests.get(
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_outstanding",
    params={"sort": "-record_date", "page[size]": 10000},
    timeout=30,
)
resp.raise_for_status()
assert resp.json()["meta"]["total-pages"] <= 1, "Use fetch_all for more pages"
df = pd.DataFrame(resp.json()["data"])
```

## Schedules of Federal Debt

**Endpoint:** `/v1/accounting/od/schedules_fed_debt`  
**Frequency:** Monthly  
**Date Range:** October 2005 to present

Monthly debt balances and activity by holder and classification. Do not sum opening/closing balances with activity lines. Unlike Debt to the Penny, these schedules exclude Federal Financing Bank debt; reconcile scope and units before comparing totals.

**Key fields:**
| Field | Type | Description |
|-------|------|-------------|
| `record_date` | DATE | End of month date |
| `debt_holder_type` | STRING | Held by public or intragovernmental |
| `security_class1_desc` | STRING | Primary classification or balance/activity line |
| `security_class2_desc` | STRING | Secondary classification |
| `principal_mil_amt` | CURRENCY0 | Principal, in millions of USD |
| `accrued_int_payable_mil_amt` | CURRENCY0 | Accrued interest payable, in millions |
| `net_unamortized_mil_amt` | CURRENCY0 | Net unamortized amounts, in millions |

## Schedules of Federal Debt by Day

Two daily data tables under `/v1/accounting/od/`:

| Table | Endpoint | Description |
|-------|----------|-------------|
| Daily Activity | `/v1/accounting/od/schedules_fed_debt_daily_activity` | Daily debt activity |
| Daily Summary | `/v1/accounting/od/schedules_fed_debt_daily_summary` | Daily debt summary |

**Related:** `/v1/accounting/od/schedules_fed_debt_fytd` — fiscal year-to-date schedules.

## Treasury Report on Receivables (TROR)

**Endpoint:** `/v2/debt/tror`  
**Frequency:** Quarterly  
**Date Range:** December 2016 to present

Federal agency compliance and receivables data. Also includes:
- `/v2/debt/tror/data_act_compliance` — 120 Day Delinquent Debt Referral Compliance Report

**Key fields:**
| Field | Type | Description |
|-------|------|-------------|
| `record_date` | DATE | Quarter end date |
| `funding_type_description` | STRING | Funding classification |
| `receivable_type_description` | STRING | Receivable class |
| `ddebt_by_age_total_amt` | CURRENCY | Delinquent debt total by age |

```python
# TROR data, sorted by funding type
resp = requests.get(
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/debt/tror",
    params={"sort": "funding_type_id"},
    timeout=30,
)
resp.raise_for_status()
```

## Gift Contributions to Reduce the Public Debt

**Endpoint:** `/v2/accounting/od/gift_contributions`  
**Frequency:** Monthly  
**Date Range:** September 1996 to present

Records voluntary contributions from the public to reduce the national debt.

## Interest Expense on the Public Debt Outstanding

**Endpoint:** `/v2/accounting/od/interest_expense`  
**Frequency:** Monthly  
**Date Range:** May 2010 to present

Monthly interest expense broken down by security type.

**Key fields:**
| Field | Type | Description |
|-------|------|-------------|
| `record_date` | DATE | Reporting month end |
| `expense_catg_desc` | STRING | Public issues or government account series |
| `expense_group_desc` | STRING | Expense group/accounting basis |
| `expense_type_desc` | STRING | Expense component |
| `month_expense_amt` | CURRENCY | Monthly expense in USD |
| `fytd_expense_amt` | CURRENCY | Cumulative fiscal-year expense in USD |

Use `month_expense_amt` for monthly flows, or the September `fytd_expense_amt`
for a completed fiscal year. Preserve all three expense dimensions when checking
the components. Never sum cumulative FYTD observations over months. This dataset
uses modified accrual accounting and some GAS cash-basis entries; its expense
measure is not the MTS budget net-interest measure. See the worked fiscal-year
example in [examples.md](examples.md).

## Advances to State Unemployment Funds (Title XII)

**Endpoint:** `/v2/accounting/od/title_xii`  
**Frequency:** Daily  
**Date Range:** October 2016 to present

States and territories borrowing from the federal Unemployment Trust Fund.

**Key fields:**
| Field | Type | Description |
|-------|------|-------------|
| `record_date` | DATE | Date of record |
| `state_nm` | STRING | State name |
| `outstanding_advance_bal` | CURRENCY | Outstanding advance balance |

## Official sources

Reviewed 2026-09-30 against the current dataset dictionaries and live API responses.

- [Debt To The Penny](https://fiscaldata.treasury.gov/datasets/debt-to-the-penny/)
- [Schedules Federal Debt](https://fiscaldata.treasury.gov/datasets/schedules-federal-debt/)
- [Treasury Report On Receivables](https://fiscaldata.treasury.gov/datasets/treasury-report-on-receivables/)
- [Interest Expense Debt Outstanding](https://fiscaldata.treasury.gov/datasets/interest-expense-debt-outstanding/)
- [Ssa Title Xii Advance Activities](https://fiscaldata.treasury.gov/datasets/ssa-title-xii-advance-activities/)
