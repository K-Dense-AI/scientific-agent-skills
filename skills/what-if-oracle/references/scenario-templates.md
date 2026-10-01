# What-If Oracle — Research Scenario Templates

Use the template that matches the scientific decision. Treat all example values and mechanisms below as illustrative assumptions unless the user supplies relevant evidence.

## Experimental yield or sample attrition

> "What if [usable-sample fraction / recruitment / retention] changes from [baseline] to [range] by [date]? Our target is [measurable outcome], with [capacity and budget]. Which responses remain feasible?"

Check the denominator and experimental unit: participants, independent biological samples, technical replicates, or batches. More technical replicates do not automatically replace independent samples. Track failure mechanisms and whether missingness differs by group or outcome; a sufficient retained count does not establish unbiased inference or adequate power.

Compare favorable, reference, adverse, and second-order scenarios. A reagent issue may reduce yield and increase reruns simultaneously, coupling capacity and cost.

## Method transfer across sites or instruments

> "What if the measurement/model performance changes on [target site/cohort/instrument] relative to [validation setting]? Which evidence would justify proceeding, recalibrating, or collecting a new validation set?"

Specify outcome metric, units, target population, protocol version, and acceptance criterion. Distinguish measurement drift, changed population composition, batch effects, and genuine biological change. A central assumption of unchanged performance is not a validated forecast. Use controls or independent target-setting data to challenge it, and keep evaluation data separate from method selection.

## Reagent, instrument, or data-access disruption

> "What if [critical dependency] is unavailable for [duration] during [research milestone]? What is affected, what can continue, and what would trigger the backup plan?"

Record lead time, sample stability, backup compatibility, and rerun capacity. A replacement instrument or reagent can change the measurement process; include validation time in the recovery scenario. Do not treat a vendor estimate as a guarantee or availability of a backup as evidence that its results are interchangeable.

## Competing hypotheses and research direction

> "If [hypothesis A] and [hypothesis B] both explain current observations, which feasible measurement would lead to different predictions under the two hypotheses? What happens to the project under each result?"

Describe each hypothesis's conditional prediction, assumptions, and observations that would weaken it. Include ambiguous results and assay failure. A contrarian hypothesis earns attention through testable differences, not novelty alone. Predefine how the measurement affects the choice; do not select only a favorable branch after seeing results.

## Worked example: usable-sample planning

**Synthetic setup:** a one-month batch has capacity for 100 independent samples. The planning target is 80 samples passing a prespecified QC rule. Usable fraction assumptions are 0.90, 0.80, and 0.60. No empirical failure history is supplied.

**Question:** if the usable fraction falls to 0.60, which contingency should be investigated before the main batch?

| Scenario | Assumed usable fraction | Expected usable count from 100 | Planning implication |
| --- | --- | --- | --- |
| Favorable yield | 0.90 | 90 | Expected count exceeds the target; individual batches can still miss it |
| Reference yield | 0.80 | 80 | Expected count equals the target; this is not assurance of reaching it |
| Adverse yield | 0.60 | 60 | Expected count is 20 below target; the current capacity is insufficient in expectation |
| Second-order capacity loss | Not estimated | Not calculated | Rework could consume capacity; estimate a joint yield/rework model before quantifying |

The arithmetic is `expected usable count = processed count × assumed usable probability`. At 0.60, `ceil(80 / 0.60) = 134` processed samples gives an expected 80.4 usable samples, which exceeds the current capacity of 100. It does **not** guarantee at least 80 usable samples. These expectations do not require independence if each sample has the stated marginal probability, but a binomial distribution for the final count additionally requires independent trials with a common fixed probability. Batch-wide failures or uncertain yield can invalidate that model.

**Likelihood:** not estimated for any scenario. There is no evidence for assigning branch probabilities. A probability of meeting the target would require a justified outcome model, information about dependence, and uncertainty in the yield estimate.

**Evidence confidence:** limited; the fractions are assumptions. QC criteria, independent sample counts, and failure causes must be recorded before transfer to a real study.

**Compare responses:** retain the 100-sample plan, evaluate an upstream QC pilot, or investigate additional capacity. The pilot consumes resources and may not improve yield. Extra capacity is useful only if its cost, timing, and measurement comparability are acceptable. Record those trade-offs rather than declaring any option universally beneficial.

**Illustrative trigger:** at the agreed pilot review, a measured yield below the planning threshold prompts a review of failure causes and the capacity plan. Set the pilot size, threshold, review time, and responsible role before observing results; quantify sampling uncertainty before treating a threshold crossing as evidence that the process changed.

**Next evidence:** a representative pilot with fixed QC criteria and batch identifiers, plus a capacity/lead-time estimate. If attrition depends on biological group or outcome, assess that bias separately. Reaching 80 usable samples alone does not establish statistical power, causal identification, or representativeness.

## Chained scenarios and forecast tracking

Expand a branch because it could change the decision, not because it has the most appealing story. Record the parent conditions at every step; alternatives and shared causes remain relevant. For an illustrative dependency calculation, `P(A)=0.4` and `P(B given A)=0.7` imply `P(A and B)=0.28`. They do not establish `P(B)` or justify multiplying `P(A)` by an unrelated marginal estimate.

When producing repeated numerical forecasts, retain the original event definition, horizon, estimate, information available at forecast time, and resolution rule before observing outcomes. Evaluate calibration and forecasting performance on resolved forecasts; a plausible narrative, normalized numbers, or confidence label is not calibration evidence. A single outcome cannot demonstrate calibration.

## Sources and provenance

Reviewed 2026-10-01:

- [Upstream What-If Oracle](https://github.com/ashrafkahoush-ux/Claude-consciousness-skills/tree/main/what-if-oracle): source of the branch-lens format, adapted here for scientific planning. Upstream's probability and golden-ratio recommendations are not treated as validated decision rules.
- [Zenodo What-If record](https://zenodo.org/records/18736841) and [IDNA record](https://zenodo.org/records/18807387): titles, author, DOI, and preprint classification verified through the public record metadata. These are provenance sources, not independent validation.
- [Government Office for Science Futures Toolkit](https://www.gov.uk/government/publications/futures-toolkit-for-policy-makers-and-analysts/the-futures-toolkit-html): scenarios and option stress-testing; no claim of validation of this skill's six lenses.
- [IPCC uncertainty guidance](https://www.ipcc.ch/site/assets/uploads/2017/08/AR5_Uncertainty_Guidance_Note.pdf): distinction between evidence confidence and assessed likelihood. Do not import climate-specific likelihood labels as an unannounced universal scale.
- [Hernán and Robins, Causal Inference: What If](https://miguelhernan.org/whatifbook): causal contrasts and identification assumptions; use the author's current download because the online text can be revised.

No API, SDK, executable script, or authenticated service is part of this skill. The arithmetic above was checked locally; the synthetic scenarios are not an empirical evaluation of forecasting quality.
