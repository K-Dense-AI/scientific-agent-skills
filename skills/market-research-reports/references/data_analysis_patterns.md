# Data Analysis Patterns for Market Research

## Measurement contract

Define the quantity before collecting numbers:

- product/service inclusion and exclusion;
- buyer, user, payer, and transaction type;
- geography and treatment of imports/exports;
- historical period, forecast horizon, and as-of date;
- revenue, expenditure, gross output, value added, units, capacity, users, or
  another measure;
- stock versus flow;
- gross versus net, taxes included/excluded, and channel level;
- currency, exchange-rate convention, base year, and nominal/real basis;
- industry and product taxonomy with version;
- denominator ID used in every share or rate.

If two estimates do not share this contract, they are not directly comparable.

## TAM, SAM, and SOM

Treat all three as conditional scenario constructs.

### Definitions

- **TAM**: value or volume of all in-scope demand under the stated market
  definition and time basis.
- **SAM**: subset of TAM serviceable under explicit product, geography,
  regulatory, channel, capacity, and customer constraints.
- **SOM**: subset of SAM obtainable within a stated time horizon under explicit
  competitive, operational, sales, retention, and capacity assumptions.

Never present SOM as a guaranteed share or TAM as an objective universal truth.

### Top-down method

Use disjoint components:

```text
TAM_top = sum(value_i * in_scope_fraction_i)
```

Each component needs a unique coverage key, source IDs, period, unit, and
denominator. Do not apply a broad percentage to an unrelated aggregate merely
because the resulting number looks plausible.

### Bottom-up method

For a recurring-use market:

```text
component_i =
    customer_count_i
  * addressable_fraction_i
  * annual_quantity_per_customer_i
  * price_per_unit_i

TAM_bottom = sum(component_i)
```

Alternative physical-capacity models may use installed base, utilization,
replacement cycle, throughput, or transactions. Keep dimensions explicit so
the resulting unit can be checked.

### SAM and SOM

```text
SAM_s = TAM * serviceable_fraction_s
SOM_s = SAM_s * obtainable_share_s
```

The fractions belong to scenario `s`. At minimum, use distinct downside and
upside cases; a base case is usually useful. For each case, list assumptions,
evidence, constraints, and horizon. Do not assign probabilities without a
validated probabilistic model.

### Preventing double counting

Common failures:

- adding manufacturer revenue to distributor or end-customer spend;
- adding domestic production, imports, and sales without subtracting exports,
  inventories, or overlapping channels;
- summing parent and subsidiary revenue;
- adding product bundles and their included components;
- combining gross output and value added;
- counting the same establishment in multiple segment labels;
- adding annual transactions to installed-base stock;
- applying overlapping geography or customer filters independently.

Controls:

1. assign a unique coverage key to every component;
2. use mutually exclusive, collectively understood segments;
3. define a single denominator ID;
4. draw money and product flows through the value chain;
5. reconcile supply, use, trade, inventory, and channel margins;
6. show an ``unallocated/unknown'' residual rather than forcing totals;
7. test the sum against an independent control total.

Supply-use tables distinguish products from industries and the origin/use of
goods and services. Use the
[OECD Supply and Use Tables](https://www.oecd.org/en/data/datasets/supply-and-use-tables.html)
and national accounts methodology when the value chain spans intermediate and
final demand.

### Reconciliation

Keep methods separate:

```text
absolute_gap = abs(TAM_top - TAM_bottom)
midpoint = (TAM_top + TAM_bottom) / 2
gap_percent = absolute_gap / midpoint
```

Investigate gaps in this order:

1. definition and denominator;
2. geography, period, currency, and price basis;
3. taxonomy and segment concordance;
4. gross/net, taxes, channel margins, imports/exports;
5. missing or duplicate coverage;
6. source revision and sample limitations;
7. price, volume, penetration, and utilization assumptions.

Do not average the methods until their scopes are demonstrably compatible. If
uncertainty remains, report both or retain a range.

## Growth and forecasts

### Historical growth

```text
YoY_t = value_t / value_(t-1) - 1
CAGR = (end / start)^(1 / periods) - 1
```

CAGR compresses the path. Always show start/end values and period count. It is
undefined when the start is nonpositive and can hide volatility, breaks, and
revisions.

### Scenario forecast

```text
value_(t+1,s) = value_(t,s) * (1 + growth_rate_(t,s))
```

Build rate paths from named drivers rather than copying a paid headline
forecast. Separate:

- historical observed period;
- nowcast or estimate period;
- conditional forecast period.

For each scenario, state demand, price, supply, regulation, competition,
capacity, and timing assumptions. Use different paths, not merely different
labels.

### Sensitivity

One-way sensitivity varies one input while holding others fixed. Report:

- tested range and rationale;
- resulting endpoints;
- switching value where the decision changes;
- nonlinearities or constraints;
- interactions omitted by one-way analysis.

Scenario analysis explores coherent joint states. It is not a confidence
interval. Statistical prediction intervals require a specified model, error
process, diagnostics, and coverage interpretation.

The reinstated 2003
[OMB Circular A-4](https://www.whitehouse.gov/wp-content/uploads/2025/08/CircularA-4.pdf)
provides primary guidance on characterizing uncertainty, sensitivity, and
transparent assumptions. The 2023 revision was revoked by
[memorandum M-25-15](https://www.whitehouse.gov/wp-content/uploads/2025/03/M-25-15-Recission-and-Reinstatement-of-Circular-A-4.pdf);
do not present it as current OMB guidance. The
[UK Green Book 2026](https://www.gov.uk/government/publications/the-green-book-appraisal-and-evaluation-in-central-government/the-green-book-2026)
provides additional public-sector appraisal guidance. Adapt principles
proportionately; do not imply that a market report is a regulatory appraisal.

## Units, currencies, and price bases

### Nominal and real

- **Nominal/current-price** values reflect prices in each period.
- **Real/constant-price** values remove price change using an identified
  deflator and base/reference year.
- Never combine nominal and real values in one total or growth rate.
- Match nominal values to nominal assumptions and real values to real
  assumptions.

Record:

```text
real_value_base_year = nominal_value_t * price_index_base / price_index_t
```

Identify the index, geography, category, vintage, and whether it is appropriate
for the market. A broad CPI may be unsuitable for a specialized B2B input.

### Chained measures

Chained-dollar components may not add to published aggregates. BEA's
[chained-dollar guidance](https://www.bea.gov/resources/methodologies/chained-dollar-indexes)
explains why. Use published contributions to growth or current-dollar
composition rather than forcing additivity.

### Currency conversion

Record:

- source and target currency;
- spot, period-average, or period-end convention;
- rate date/period and source;
- order of currency conversion and deflation;
- effects of high inflation or multiple exchange-rate regimes.

Do not mix converted flows using period-end rates with balances using averages
without explanation.

### Stock and flow

A stock is measured at a point in time; a flow over an interval. Installed
base, employees on a date, and capacity are stocks. Revenue, transactions, and
shipments during a year are flows. A stock-to-flow conversion requires an
explicit turnover, utilization, or replacement-cycle assumption.

## Shares and concentration

```text
share_i = in_scope_measure_i / same_scope_total
HHI = sum((100 * share_i)^2)
CR4 = sum(four_largest_shares)
```

Before computing:

- define product and geographic scope;
- use one share metric and denominator;
- include the same period and channel level;
- account for unknown/residual firms;
- disclose whether values are revenue, units, capacity, or active users;
- avoid false precision when company and total estimates use different methods.

The [2023 U.S. Merger Guidelines](https://www.justice.gov/atr/merger-guidelines)
describe HHI as one indicator in case-specific merger analysis. The
[2024 EU Market Definition Notice](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:C_202401645)
addresses product/geographic scope, non-price parameters, dynamic and digital
markets, alternate share metrics, and evidence. A market report's HHI is
descriptive and is not a legal conclusion.

## Survey and interview synthesis

### Survey estimate

For a probability sample, report the design-based or model-based estimator,
weights, design effect, and appropriate uncertainty. Do not infer population
precision from sample size alone.

For a non-probability sample, disclose recruitment and model assumptions. Use
careful labels such as ``among respondents'' unless a validated adjustment
supports broader inference.

### Interview themes

Use a structured coding frame:

```text
theme_id | definition | inclusion rule | exclusion rule |
supporting excerpts | disconfirming excerpts | roles represented
```

Report a theme as qualitative evidence. Do not translate mention counts into
market prevalence.

## Confidence labels

Confidence is an analyst assessment, not a substitute for uncertainty:

- **High**: directly observed, well-defined primary evidence with compatible
  scope and low material revision risk.
- **Medium**: triangulated evidence with manageable assumptions or limitations.
- **Low**: sparse, conflicting, indirect, modeled, or scope-mismatched evidence.
- **Not assessed**: opinion or recommendation where an evidence-confidence
  label is inappropriate.

Always state the reasons. Multiple low-quality sources do not automatically
produce high confidence.
