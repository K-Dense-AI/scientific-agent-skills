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
| `open_today_bal` | CURRENCY0 | Opening balance |
| `open_month_bal` | CURRENCY0 | Opening month balance |
| `open_fiscal_year_bal` | CURRENCY0 | Opening fiscal year balance |
| `close_today_bal` | CURRENCY0 | Closing balance |
| `transaction_today_amt` | CURRENCY0 | Today's transaction amount |
| `transaction_mtd_amt` | CURRENCY0 | Month-to-date amount |
| `transaction_fytd_amt` | CURRENCY0 | Fiscal year-to-date amount |

Since April 18, 2022, `close_today_bal` is null. Select
`account_type:eq:Treasury General Account (TGA) Closing Balance` and read
`open_today_bal` for the closing balance (millions of USD). The similarly named
opening-balance row is a different observation. See [examples.md](examples.md).

Table II has category hierarchies; preserve `account_type`, `transaction_type`,
`transaction_catg` and `transaction_catg_desc` before selecting totals. Use the
explicit Table I total deposit/withdrawal rows for a daily cash-flow summary.
Do not add cumulative `transaction_mtd_amt`/`transaction_fytd_amt` across dates.

Federal Tax Deposits is historical; the current reporting structure uses
Inter-Agency Tax Transfers and Table II. Short-Term Cash Investments is
historical and was removed from the published report in February 2023.

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
| `/v1/accounting/mts/mts_table_5m` | Receipts offset against outlays |
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

### MTS field and unit differences

| Table | Amount fields | Interpretation |
|-------|---------------|----------------|
| Table 1 | `current_month_gross_rcpt_amt`, `current_month_gross_outly_amt`, `current_month_dfct_sur_amt` | Dollar amounts; each publication includes multiple months, fiscal years and YTD rows |
| Table 9 | `current_month_rcpt_outly_amt`, `current_fytd_rcpt_outly_amt`, `prior_fytd_rcpt_outly_amt` | Dollar amounts by receipt source/outlay function |
| Monthly summary | `amt_category`, `mil_amt` | One category per reporting month; amount in millions of USD |

`record_date` dates the publication, not necessarily the month described by a
Table 1 row. For a simple monthly budget series use
`mts_receipts_outlays_deficit_surplus` as shown in [examples.md](examples.md).
Deficit is positive and surplus negative in its `Deficit/Surplus (-)` category.

Tables have totals, subtotals and structural rows with null values. Reconcile
`parent_id`/`classification_id` within each publication before aggregating;
classification IDs change between publications. Do not filter Table 1 for
"Total Receipts": its receipt and outlay values are columns on month/YTD rows.
Table 9 line 120 is the documented total-receipts example; inspect its label and
hierarchy and use `current_month_rcpt_outly_amt`.

The dataset's generic notes describe published reports in millions, but live
Table 1/9 API amounts are dollar-scale while `mil_amt` explicitly represents
millions. Validate each field against the matching report; never apply one
scaling factor to all MTS endpoints. API coverage starts at different dates by
table; the dataset-wide 1980 start is not every table's first API observation.

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
**Date Range:** September 1995 onward; inspect the latest published fiscal year

Annual audited financial statements. Includes:
- Balance sheets
- Statement of net cost
- Statement of operations
- Statement of changes in net position

---

## Monthly Treasury Disbursements

**Frequency:** Monthly  
**Date Range:** October 2013 to present

Monthly federal disbursements reports. The current catalog has no REST endpoint for this table; use its dataset-page downloads.

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

Agency-level Contract Disputes Receivables, No FEAR Act Receivables and Unclaimed Money balances. This dataset does not identify unclaimed money owed to individual people.

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

## Official sources

Reviewed 2026-09-30 against the current dataset dictionaries and live API responses.

- [Daily Treasury Statement](https://fiscaldata.treasury.gov/datasets/daily-treasury-statement/)
- [Monthly Treasury Statement](https://fiscaldata.treasury.gov/datasets/monthly-treasury-statement/)
- [Treasury Bulletin](https://fiscaldata.treasury.gov/datasets/treasury-bulletin/)
