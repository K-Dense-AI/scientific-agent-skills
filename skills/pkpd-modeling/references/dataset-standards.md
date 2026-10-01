# Population PK event data

## Preserve event meaning

Keep one record per event/observation with numeric ID and a time basis interpretable across the
complete subject history. TIME generally advances from a subject/occasion origin; TAD is separate.
NONMEM reset events (EVID 3/4) can restart the model/time; do not treat every dose as a reset.
IDs must remain contiguous in the file. Sorting by TIME alone can corrupt tied-event order.

| Field | Meaning and common checks |
| --- | --- |
| ID | Numeric subject identifier in NONMEM; do not concatenate discontinuous blocks silently |
| TIME | Actual event time; units consistent with CL, Q, ka and infusion rate |
| DV | Numeric observation when MDV=0; missing placeholders only under declared semantics |
| EVID | 0 observation, 1 dose, 2 other, 3 reset, 4 reset+dose (ordinary cases) |
| MDV | Whether DV contributes to likelihood; advanced values are engine-specific |
| AMT | Amount administered, with stated units and input compartment |
| RATE | 0 bolus; positive infusion rate; -1 modeled rate Rn; -2 modeled duration Dn |
| II/ADDL | Interval and additional doses; ADDL requires a meaningful positive interval |
| SS | Engine-specific steady-state instruction; does not prove real-world steady state |
| CMT | Model compartment, not an assay or analyte label |
| BLQ/LLOQ | Separate censoring indicator and assay threshold |

For an ongoing constant steady-state infusion, SS with AMT=0 and positive RATE uses II=0;
a blanket rule requiring AMT>0 and II>0 would reject valid data. Other advanced dosing conventions
must be checked against the installed engine manual. NONMEM was not run in this refresh.
[Vendor platform and documentation access](https://www.iconplc.com/solutions/technologies/nonmem).

## Ordering and missingness

A pre-dose sample belongs before the same-time dose; a post-dose sample belongs after it. Infer
order from collection/administration records, not an arbitrary epsilon. The checker cannot resolve
unknown order. Do not invent dose history from nominal schedules when actual doses are available.

Nonnumeric DV is not a safe representation of BLQ. Use documented numeric placeholders plus
censoring flags and a model likelihood. The parser's treatment of tokens depends on engine/data
configuration; there is no universal guarantee that text becomes zero. Genuine missing samples,
BLQ observations and data excluded for a prespecified reason are separate categories.

Carry units and provenance for covariates (weight, age, renal function estimate, genotype).
Time-varying weight or organ function should not silently become baseline constants. Renal
estimates in mL/min and mL/min/1.73m² are not interchangeable; record the equation and indexing.

## What the bundled checker establishes

`check_popk_dataset.py` checks common row consistency, finite numeric values, subject blocks,
time/reset ordering, dosing fields, observation count, covariates and duplicate/tied records.
It is not an NM-TRAN validator, dose reconstruction engine, censoring-likelihood check or proof that
a particular control stream interprets the data correctly. Pure PD, placebo, multi-analyte and
advanced dosing workflows need a tailored schema. Keep the derivation code and compare model
predictions around event boundaries using an independent simple case.
