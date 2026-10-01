# ML Conference Writing Style

**Reviewed: 2026-10-01.** Applies to drafting for NeurIPS, ICML, ICLR, CVPR,
and related ML/vision venues. The exact year, track, and submission stage control
formatting. ICCV and ECCV have independent instructions.

## Primary sources

- https://neurips.cc/Conferences/2026/MainTrackHandbook
- https://icml.cc/Conferences/2026/AuthorInstructions
- https://iclr.cc/Conferences/2026/AuthorGuide
- https://cvpr.thecvf.com/Conferences/2026/AuthorGuidelines

See `conferences_formatting.md` for the dated limits and official author-kit
workflow. A 2026 snapshot is not a rule for an upcoming 2027 submission.

## Choose the contribution before the prose template

ML venues admit theory, methods, analysis, datasets, applications, and other
contribution types. Match evidence to the contribution. A theory result need
not be forced into a benchmark-and-ablation paper; a careful negative result
need not claim state-of-the-art accuracy. Research, position, and evaluations/
datasets tracks can have different contracts.

A useful abstract covers the problem, limitation of prior work, approach or
analysis, principal supported result, and scope. Include quantitative evidence
when material, with dataset, metric, comparator, and evaluation conditions.
Avoid invented improvements, unqualified “optimal” claims, and a universal
150–250-word requirement; use the actual template/portal limit.

## Introduction and contribution statement

1. Define the problem and why it matters.
2. Identify the precise gap using relevant prior work.
3. Explain the key idea at the level needed to understand the contribution.
4. State what the paper establishes and where its evidence appears.

Contribution bullets are a useful convention, **not a universal conference
requirement**. Do not call a method novel unless its difference from prior work
has been established. An introduction has no universal two-to-three-page quota.

Example, intentionally unexecuted and placeholder-based:

```text
We study [problem] in [setting]. Existing approaches leave [specific gap].
Our contribution is [method, theorem, analysis, or resource]. Under [conditions],
we establish [supported result], evaluated against [appropriate comparator].
The evidence does not yet establish [important limitation].
```

For a worked drafting pattern, use `assets/examples/neurips_introduction_example.md`
(relative to the skill root). Its method name and placeholders are illustrative.
Do not attribute fictional results or pseudocode to FlashAttention or any other
real project.

## Methods and theory

Define symbols, input/output semantics, assumptions, and the precise objective.
Separate implementation complexity from asymptotic analysis; specify what is
held fixed. For an attention example, materializing one N-by-N float32 matrix
uses `4*N*N` bytes, but computational work also depends on head dimension and
other operations, and fused exact-attention kernels need not materialize that
matrix. Do not equate matrix entries with total FLOPs.

State theorem assumptions next to the claim. A proof outline is not an executable
implementation, and an omitted normalization/scaling term can invalidate an
algorithm. Use tested project code or accurate pseudocode rather than filling a
venue template with a purported implementation of a named method.

## Empirical evidence

For empirical claims, report:

- dataset versions, provenance, licensing, splits, preprocessing, and exclusions;
- unit of splitting and protection against subject/group/time or benchmark leakage;
- appropriate current and simple strong baselines, with justified selection;
- tuning budgets, stopping rules, model selection, and held-out evaluation;
- metrics and uncertainty, with the number and meaning of independent runs;
- hardware, software versions, memory, training/inference time, and comparison conditions;
- failure cases and the population or task scope not covered by the study.

A standard deviation across seeds is not a confidence interval for a new dataset
or population. “3.2% improvement” must distinguish percentage points from relative
percent. Small improvements can be important; magnitude alone is not a rejection
criterion. An older baseline can still be the right comparator.

Use ablations or sensitivity analyses where needed to assess the claimed
mechanism. Report null or adverse ablations too; the purpose is to discover which
components matter, not to ensure every component looks beneficial. Theory,
observational analysis, and resource papers may need different validation.

## Reproducibility and limitations

Keep details essential to evaluation in the main paper. References and appendices
can be outside the main-text page budget, but reviewers may not read optional
material. Report resource access conditions honestly; promise public code/data
only when the authors can actually release it.

Follow the actual checklist or statement used by the venue. NeurIPS 2026 requires
the Paper Checklist. It does not universally require a separately titled Broader
Impacts section, but authors must address relevant impacts and the checklist.
Describe limitations precisely: unsupported regimes, dataset coverage, compute
constraints, failed assumptions, or unresolved validation.

## Figures and citations

Show legible labels at final column width, uncertainty and units on quantitative
plots, and consistent visual encodings. Use vector output where supported;
convert SVG when the chosen LaTeX toolchain cannot include it directly. Raster
resolution must be assessed at the final physical size.

Cite the work needed to understand and evaluate the contribution, including
relevant contemporaneous and foundational research. Use the official style's
citation mode rather than imposing one style across all ML venues.

## Review, rebuttal, and final version

- Use anonymous review mode and inspect all supplementary and linked materials.
- Follow the venue's self-citation, code-link, and frozen-repository rules.
- Prioritize substantive reviewer misunderstandings and concerns.
- Add experiments or revised manuscripts only where the current response rules
  permit them. CVPR 2026 restricts new contributions/unrequested experiments;
  ICML 2026 does not permit a revised paper during author feedback.
- State what was changed or tested accurately. Do not turn a planned experiment
  into a completed one in a rebuttal example.
- Recheck the camera-ready allowance before enabling `final`; the helper presets
  describe initial submission, not final acceptance.
