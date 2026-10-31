# Market Report Formatting Guide

Use formatting to expose evidence quality and uncertainty, not to make estimates
look more certain. The bundled LaTeX files are optional; Markdown, HTML, DOCX, or
another user-requested format is equally acceptable.

## Information hierarchy

Use the following order within each analytical section:

1. finding or question;
2. evidence and exact claim IDs;
3. calculation or interpretation;
4. assumptions and uncertainty;
5. implication or decision threshold.

Keep these statement types visually and verbally distinct:

- **Observed fact** — directly represented by cited evidence.
- **Estimate** — a source's or analyst's uncertain estimate.
- **Calculation** — deterministic result from listed inputs and formula.
- **Scenario** — conditional result, not a prediction or confidence interval.
- **Recommendation** — judgment based on findings and stated objectives.

## Required labels for quantitative content

Every quantitative table, figure, callout, or headline metric should show:

- geography and coverage;
- period or as-of date;
- currency and base year when monetary;
- nominal, real, current-price, constant-price, or chained basis;
- stock, flow, count, share, rate, price, or index;
- unit and denominator;
- taxonomy and version when classifications define scope;
- historical versus forecast status;
- source IDs and calculation ID;
- revision status and material limitations.

Do not combine differently defined values in one visual scale. Normalize them
first and retain the conversion record.

## Color and accessibility

The style uses a restrained, colorblind-aware palette:

- navy: structure and observed evidence;
- teal: calculated values;
- amber: assumptions or uncertainty;
- red: limitations or unresolved conflicts;
- gray: context and unavailable evidence.

Never rely on color alone. Add labels, symbols, line styles, or direct
annotations. Check grayscale legibility and reading order.

## LaTeX usage

Place `market_research.sty` next to the report and use:

```latex
\documentclass[11pt]{report}
\usepackage{market_research}
```

Compile from that directory with a TeX Live or MiKTeX installation containing
`fontspec`, TeX Gyre Heros, and the packages required by the style. Use XeLaTeX or
LuaLaTeX; the Unicode font setup does not target pdfLaTeX. Run twice for the contents:

```bash
xelatex -no-shell-escape -halt-on-error -interaction=nonstopmode market_report_template.tex
xelatex -no-shell-escape -halt-on-error -interaction=nonstopmode market_report_template.tex
```

The template and snippets contain placeholders and synthetic examples, not current
market findings. Inspect every rendered page for clipping, table overflow, font
substitution, and unresolved references. Bracketed placeholder text after `\item`
must be braced (`\item {[Finding]}`); otherwise LaTeX treats it as the list label.

The package provides:

```latex
\begin{evidencebox}[Observed evidence]
Claim C-014 maps to sources S-003 and S-011.
\end{evidencebox}

\begin{calculationbox}[Calculation CALC-007]
Top-down and bottom-up estimates differ by 12.4\% of their midpoint.
\end{calculationbox}

\begin{assumptionbox}[Scenario assumptions]
The upside case assumes faster adoption; it is not assigned a probability.
\end{assumptionbox}

\begin{limitationbox}[Material limitation]
The source series was revised after the original retrieval date.
\end{limitationbox}
```

The compatibility aliases `keyinsightbox`, `marketdatabox`, `riskbox`,
`recommendationbox`, and `calloutbox` remain available for existing reports,
but prefer the evidence-specific environments above.

## Tables

Put units in column headers and scope in the caption. Do not mix percentages and
currency on a single unlabelled axis.

```latex
\begin{table}[htbp]
\centering
\caption{Conditional market-size scenarios, Exampleland, nominal 2025 USD/year}
\begin{tabular}{@{}lrrrl@{}}
\toprule
Scenario & TAM & SAM & SOM & Evidence \\
\midrule
Downside & [value] & [value] & [value] & S-001; S-004 \\
Base     & [value] & [value] & [value] & S-001; S-004 \\
Upside   & [value] & [value] & [value] & S-001; S-004 \\
\bottomrule
\end{tabular}
\end{table}
```

Use `unknown` rather than a zero when evidence is missing. Explain suppression,
rounding, residual categories, and totals that do not add because of chain
weighting or independent seasonal adjustment.

## Optional figures

Figures are optional and should be created only when they improve
understanding. A figure caption must identify:

```latex
\caption{Scenario range by year. USD/year at current prices; Exampleland;
historical through 2025 and conditional scenarios thereafter.
Sources: S-001, S-004. Calculation: CALC-FCST-002.}
```

Never use decorative imagery as evidence. Never infer market share from logo
size, search rank, or an unlabelled generated graphic.
For nominal forecasts, the historical anchor year is not a constant-price base:
label each year's current-price currency. Use "constant 2025 USD" only after an
explicit inflation adjustment.

## Citations

Use stable source IDs in the report body and a complete evidence ledger in the
appendix. A suggested compact notation is:

```text
The published count increased after the latest revision [C-014; S-003].
```

The bibliography entry alone is not enough: the claims ledger must map each
claim to the exact source record, retrieval date, and applicable calculation or
assumption IDs.

## Final checks

- No placeholder numbers or unsupported precision remain.
- Forecasts and TAM/SAM/SOM are visibly labeled as scenarios.
- Observed and forecast periods are visually separated.
- All monetary content states currency, base year, and price basis.
- Every table and optional figure has source and calculation IDs.
- Unknowns, conflicts, revisions, and limitations are visible.
- Layout does not imply endorsement, legal advice, or investment advice.
