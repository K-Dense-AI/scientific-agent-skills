# Fiscal Statement Datasets — U.S. Treasury Fiscal Data

## Daily Treasury Statement (DTS)

The DTS dataset has **9 data tables**, all under `/v1/accounting/dts/`. Updated daily (business days).

**Date Range:** October 2005 to present

### DTS Tables

| Table | Endpoint | Description |
|-------|----------|-------------|
| Operating Cash Balance | `/v1/accounting/dts/operating_cash_balance` | Treasury General Account balance |
| Deposits & Withdrawals | `/v1/accounting/dts/deposits_withdrawals_operating_cash` | Changes to TGA |
| Public Debt Transactions | `/v1/accounting/dts/public_debt_transactions` | Issues and redemptions of securities |
| Adjustment of Public Debt | `/v1/accounting/dts/adjustment_public_debt_transactions_cash_basis` | Cash basis adjustments |
| Debt Subject to Limit | `/v1/accounting/dts/debt_subject_to_limit` | Debt vs. statutory limit |
| Inter-Agency Tax Transfers | `/v1/accounting/dts/inter_agency_tax_transfers` | Intra-government tax transfers |
| Federal Tax Deposits | `/v1/accounting/dts/federal_tax_deposits` | Tax deposit activity |
| Short-Term Cash Investments | `/v1/accounting/dts/short_term_cash_investments` | Cash investment activity |
| Income Tax Refunds Issued | `/v1/accounting/dts/income_tax_refunds_issued` | Tax refund issuances |

### Common DTS Fields

| Field | Type | Description |
|-------|------|-------------|
| `record_date` | DATE | Business date |
| `account_type` | STRING | Account/balance type |
| `open_today_bal` | CURRENCY | Opening balance |
| `open_month_bal` | CURRENCY | Opening month balance |
| `open_fiscal_year_bal` | CURRENCY | Opening fiscal year balance |
| `close_today_bal` | CURRENCY | Closing balance |
| `transaction_today_amt` | CURRENCY | Today's transaction amount |
| `transaction_mtd_amt` | CURRENCY | Month-to-date amount |
| `transaction_fytd_amt` | CURRENCY | Fiscal year-to-date amount |

```python
# Get current Treasury General Account (TGA) balance
resp = requests.get(
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance",
    params={"sort": "-record_date", "page[size]": 5}
)
for row in resp.json()["data"]:
    print(f"{row['record_date']}: ${float(row['close_today_bal']):,.0f}M (closing balance)")

# Get deposits and withdrawals for a specific period
resp = requests.get(
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash",
    params={
        "filter": "record_date:gte:2024-01-01,record_date:lte:2024-01-31",
        "sort": "record_date",
        "page[size]": 1000
    }
)
```

### Aggregation Example (DTS)

```python
# Get sum of today's transaction amounts by transaction type
resp = requests.get(
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/deposits_withdrawals_operating_cash",
    params={
        "fields": "record_date,transaction_type,transaction_today_amt",
        "filter": "record_date:eq:2024-01-15"
    }
)
```

---

## Monthly Treasury Statement (MTS)

The MTS dataset has **18 data tables**, all under `/v1/accounting/mts/`. Updated monthly.

**Date Range:** October 1980 to present

### MTS Tables

| Endpoint | Description |
|----------|-------------|
| `/v1/accounting/mts/mts_table_1` | Summary of receipts, outlays, and deficit/surplus |
| `/v1/accounting/mts/mts_table_2` | Summary of budget and off-budget results |
| `/v1/accounting/mts/mts_table_3` | Summary of receipts and outlays |
| `/v1/accounting/mts/mts_table_4` | Receipts of the U.S. Government |
| `/v1/accounting/mts/mts_table_5` | Outlays of the U.S. Government |
| `/v1/accounting/mts/mts_table_5m` | Receipts and outlays by month |
| `/v1/accounting/mts/mts_table_6` | Means of financing the deficit or disposition of surplus |
| `/v1/accounting/mts/mts_table_6a` | Analysis of change in excess of liabilities |
| `/v1/accounting/mts/mts_table_6b` | Securities issued under special financing authorities |
| `/v1/accounting/mts/mts_table_6c` | Federal agency borrowing via Treasury securities |
| `/v1/accounting/mts/mts_table_6d` | Investments of federal accounts in federal securities |
| `/v1/accounting/mts/mts_table_6e` | Guaranteed and direct loan financing, net activity |
| `/v1/accounting/mts/mts_table_7` | Receipts and outlays by month |
| `/v1/accounting/mts/mts_table_8` | Trust fund impact on budget results and holdings |
| `/v1/accounting/mts/mts_table_9` | Summary of receipts by source and outlays by function |
| `/v1/accounting/mts/mts_table_9_outlays_functions_subfunctions` | Outlays by function and subfunction |
| `/v1/accounting/mts/mts_distributed_offsetting_receipts` | Distributed offsetting receipts |
| `/v1/accounting/mts/mts_receipts_outlays_deficit_surplus` | Receipts, outlays, and deficit/surplus |

### Common MTS Fields

| Field | Type | Description |
|-------|------|-------------|
| `record_date` | DATE | Month end date |
| `record_fiscal_year` | STRING | Fiscal year (Oct–Sep) |
| `record_fiscal_quarter` | STRING | Fiscal quarter (1–4) |
| `classification_desc` | STRING | Line item description |
| `classification_id` | STRING | Line item code |
| `parent_id` | STRING | Parent classification ID |
| `current_month_gross_rcpt_amt` | CURRENCY | Current month gross receipts |
| `current_fytd_gross_rcpt_amt` | CURRENCY | Fiscal year-to-date gross receipts |
| `prior_fytd_gross_rcpt_amt` | CURRENCY | Prior year fiscal-year-to-date |

```python
# MTS Table 1: Summary of receipts and outlays
resp = requests.get(
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/mts/mts_table_1",
    params={
        "filter": "record_fiscal_year:eq:2024",
        "sort": "record_date"
    }
)
df = pd.DataFrame(resp.json()["data"])

# MTS Table 9: Get line 120 (Total Receipts) for most recent period
resp = requests.get(
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/mts/mts_table_9",
    params={
        "filter": "line_code_nbr:eq:120",
        "sort": "-record_date",
        "page[size]": 1
    }
)
```

---

## U.S. Government Revenue Collections

**Endpoint:** `/v2/revenue/rcm`  
**Frequency:** Daily  
**Date Range:** October 2004 to present

Daily tax and non-tax revenue collections.

---

## Financial Report of the U.S. Government

**Endpoint:** (8 tables)  
**Frequency:** Annual  
**Date Range:** September 1995 to present (FY2024 latest)

Annual audited financial statements. Includes:
- Balance sheets
- Statement of net cost
- Statement of operations
- Statement of changes in net position

---

## Monthly Treasury Disbursements

**Frequency:** Monthly  
**Date Range:** October 2013 to present

Monthly federal disbursements data.

---

## Receipts by Department

**Endpoint:** `/v1/accounting/od/receipts_by_department`  
**Frequency:** Annual  
**Date Range:** September 2015 to present

Annual breakdown of federal receipts by department.

---

## Treasury Managed Accounts

**Frequency:** Quarterly  
**Date Range:** December 2022 to present (3 data tables)

Treasury-managed trust and special funds account data.

---

## Treasury Bulletin

**Frequency:** Quarterly  
**Date Range:** March 2021 to present (13 tables)

Quarterly financial report covering government finances, public debt, savings bonds, and more. Endpoints use the `/v1/accounting/tb/` prefix (not `/v1/accounting/od/`).

| Endpoint | Description |
|----------|-------------|
| `/v1/accounting/tb/esf1_balances` | Exchange Stabilization Fund balances |
| `/v1/accounting/tb/esf2_statement_net_cost` | ESF statement of net cost |
| `/v1/accounting/tb/fcp1_weekly_report_major_market_participants` | Major market participants (weekly) |
| `/v1/accounting/tb/fcp2_monthly_report_major_market_participants` | Major market participants (monthly) |
| `/v1/accounting/tb/fcp3_quarterly_report_large_market_participants` | Large market participants (quarterly) |
| `/v1/accounting/tb/ffo5_internal_revenue_by_state` | Internal revenue receipts by state |
| `/v1/accounting/tb/ffo6_customs_border_protection_collections` | Customs and border protection collections |
| `/v1/accounting/tb/ofs1_distribution_federal_securities_class_investors_type_issues` | Distribution of federal securities by class and investor |
| `/v1/accounting/tb/ofs2_estimated_ownership_treasury_securities` | Estimated ownership of Treasury securities |
| `/v1/accounting/tb/pdo1_offerings_regular_weekly_treasury_bills` | Offerings of regular weekly Treasury bills |
| `/v1/accounting/tb/pdo2_offerings_marketable_securities_other_regular_weekly_treasury_bills` | Other marketable securities offerings |
| `/v1/accounting/tb/uscc1_amounts_outstanding_circulation` | Amounts outstanding and in circulation |
| `/v1/accounting/tb/uscc2_amounts_outstanding_circulation` | Amounts outstanding and in circulation (continued) |
