# Science Skill Routing

Use this reference to decide what to load next and what to deliver.

## Literature And Evidence

Use `$scientific-literature-review` when the user asks what is known, what papers show, or how mechanisms compare. Deliver:

- search scope and date
- source table with study type, model/population, endpoints, main findings, and limitations
- synthesis by evidence strength
- explicit uncertainty and next searches

Use `$scientific-critical-thinking` when the task is to judge validity, bias, causal strength, or review a paper. Deliver:

- claim-by-claim assessment
- bias/confounding table
- statistical and design risks
- corrected interpretation

## Data And Computation

Use `$data-analysis` or `$statistical-analysis` for general tabular analysis. Use `$multiomics-data-analysis` for omics, then modality-specific skills when present.

Deliver:

- data provenance and schema audit
- executable scripts or notebooks
- QC summaries
- statistical method record
- result tables and figures
- limitations and sensitivity checks

Never report a derived number unless it is produced by code or read from a result file.

## Experiment Design

Use `$experiment-designer` for wet-lab, animal, clinical, computational benchmark, or validation plans.

Deliver:

- hypothesis and falsifiable predictions
- model/system choice and rationale
- primary/secondary endpoints
- controls and randomization/blinding
- sample-size/power assumptions when possible
- go/no-go criteria
- safety, ethics, and feasibility constraints

## Scientific Writing

Use `$scientific-writing` for manuscripts and scientific reports, `$grant-writer` for proposals, and `$scientific-visualization` for publication figures.

Deliver:

- claims tied to evidence
- methods sufficient to reproduce
- limitations that match actual evidence
- figure/table callouts
- source/artifact paths

## High-Stakes Or Sensitive Topics

For clinical, legal, policy, biosafety, or chemical-safety questions:

- browse current primary or official sources
- state the date searched
- avoid operational hazardous instructions
- distinguish general scientific information from professional advice
- recommend qualified oversight when real-world action is implied
