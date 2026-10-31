# Official Source Ledger

**Review date: 2026-09-30.** This is a source baseline, not a regional applicability decision.
The offline helpers make no service/API calls, require no credentials, and have no endpoint,
authentication, pagination or response contract to refresh. The collection-citation lookup is
separate from the analytical workflow. Retain controlled editions, raw data and calculation outputs.

## ICH primary sources

The full public PDFs were downloaded and inspected during this review. Copyright belongs to ICH;
these summaries and script tables are adaptations, not ICH-endorsed implementations. ICH permits
reuse with acknowledgement under the legal notice in each guideline.

| Source | Reviewed baseline and scope |
| --- | --- |
| [Q2(R2)](https://database.ich.org/sites/default/files/ICH_Q2%28R2%29_Guideline_2023_1130.pdf) | Step 4 adopted 1 Nov 2023; 30 Nov correction. Sections 2–3, Tables 1–2 and Annex 2 checked against catalogue and references. |
| [Q14](https://database.ich.org/sites/default/files/ICH_Q14_Guideline_2023_1116.pdf) | Final adopted 1 Nov 2023. Minimal/enhanced approaches, optional formal ATP (section 3), robustness, established conditions, lifecycle and multivariate development. |
| [M10](https://database.ich.org/sites/default/files/M10_Guideline_Step4_2022_0524.pdf) | Step 4, 24 May 2022. Chromatographic section 3 and LBA section 4 numerical criteria, ISR section 5, partial/cross validation section 6 and biomarker exclusion checked. |
| [EMA Q2(R2) landing page](https://www.ema.europa.eu/en/scientific-guidelines/ich-q2r2-validation-analytical-procedures) | Lists current R2, effective 14 Jun 2024. This regional date is not a universal implementation date. |
| [ICH training map](https://database.ich.org/sites/default/files/ICH_Q2%28R2%29Q14_TrainingMat_MapofContents_2025_0620.pdf) | Training modules are interpretation support, not replacement guideline editions. |

Material corrections from this review:

- M10 LBA selectivity uses ten individual matrix sources, not the chromatographic six (4.2.2).
  LBA medium QC is near the geometric mean of the calibration range (4.2.4.1).
- Calibration acceptance requires six **passing** levels, not six attempted levels. Exclusion
  requires curve refitting/re-evaluation; routine sample/QC bracketing and plate/batch checks remain
  outside this checker. Anchor exclusion is LBA-specific. The percent pass rules do not themselves
  establish run acceptability.
- Q2 3.2.3.3 names the SD of intercepts of regression lines. The SE of one intercept is a different
  statistic and is no longer substituted. Q2 does not provide generic 20% QL confirmation limits.
- Table 2's shared dissolution upper-range cell is 130% of the highest strength's declared content.
- M10 ISR has a study-size minimum; the availability qualification in cross validation is not an
  ISR exemption. Section 6.2 names bias/agreement methods, not a mandatory TOST equivalence test.

## Publisher metadata and public previews only

No subscription standard was accessed. Do not reconstruct the full standard from this skill.
Public catalogue scopes/edition metadata are cited below; operational requirements come from the
laboratory's authorised controlled text.

### USP

- [1220 preview](https://doi.usp.org/USPNF/USPNF_M10975_02_01.html) identifies the lifecycle chapter.
  [USP Council of Experts report](https://www.usp.org/sites/default/files/usp/document/about/expert-volunteers/fy-22-coe-report-to-bot.pdf)
  confirms it became official 1 May 2022. Current revision status still requires USP–NF access.
- [1225 preview](https://doi.usp.org/USPNF/USPNF_M99945_40101_01.html) explicitly describes a **2025
  proposal** based on the chapter official from 1 Aug 2017. It proposes Q2(R2) alignment and discusses
  a proposed 1221 chapter. A DOI page or proposal is not proof of an official effective revision.
- [1226 preview](https://doi.usp.org/USPNF/USPNF_M870_03_01.html) describes selected-characteristic
  verification for first use; it distinguishes verification from repeating full validation.
- 1224, 1010, 621, 711 and 1092 are pointers only; no adjustment allowances, thresholds or current
  revision dates are supplied. Verify those in [USP–NF](https://www.uspnf.com/).

### CLSI

Current publisher pages were read for every listed document. Full standards were not read.

| Document | Source | Listed edition |
| --- | --- | --- |
| EP05 | <https://clsi.org/shop/standards/ep05-plus/> | 4th, 11 Dec 2025; Plus includes Quick Guide |
| EP06 | <https://clsi.org/shop/standards/ep06/> | 2nd, 24 Nov 2020 |
| EP07 | <https://clsi.org/shop/standards/ep07-plus/> | 3rd, 30 Apr 2018; additional guide 17 Mar 2026 |
| EP09 | <https://clsi.org/shop/standards/ep09/> | corrected 3rd, 20 Jun 2018 |
| EP15 | <https://clsi.org/shop/standards/ep15/> | 3rd, 11 Sep 2014 |
| EP17 | <https://clsi.org/shop/standards/ep17/> | 2nd |
| EP25 | <https://clsi.org/shop/standards/ep25/> | 2nd |
| EP28 | <https://clsi.org/shop/standards/ep28/> | 3rd; EP28IG companion listed |

The [publisher's May 2026 update](https://clsi.org/resources/insights-blog/purpose-driven-content-for-ep-documents-a-strategic-update/)
discusses modular guides and EP09 revision work. These are not evidence of a new technical edition.

### ISO and clinical regulatory context

- [ISO/IEC 17025:2017 catalogue](https://www.iso.org/standard/66912.html): edition 3, published
  November 2017, current catalogue stage confirmed. Clause labels identify the subject only;
  full requirements were not read. ISO 15189, ISO 21748 and ISO 5725 remain scope pointers, without
  asserted editions or detailed requirements.
- [CMS CLIA regulation entrypoint](https://www.cms.gov/medicare/health-safety-standards/clinical-laboratory-improvement-amendments-clia/clia-regulations-compliance)
  and [CMS performance-specification interpretation](https://www.cms.gov/Medicare/Provider-Enrollment-and-Certification/SurveyCertificationGenInfo/Downloads/Survey-and-Cert-Letter-15-17.pdf)
  support the distinction between establishment and verification for unmodified FDA-cleared or
  approved tests. Do not infer US CLIA applicability from CE marking.

## Statistical implementation and validation boundaries

These are general statistical methods, not framework-prescribed universal decisions.
[NIST weighted least squares](https://itl.nist.gov/div898/handbook/pmd/section1/pmd143.htm),
[NIST weighted fitting](https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd432.htm), and
[NIST calibration model checking](https://www.itl.nist.gov/div898/handbook/mpc/section3/mpc365.htm)
were checked for variance-model and calibration assumptions. The routines implement t, chi-square
and F distributions, weighted linear regression with replicate lack-of-fit, approximate residual
runs diagnostics, one-way variance components, Deming/jackknife, a bounded Passing–Bablok subset,
Bland–Altman and paired TOST. Tests exercise published quantiles and synthetic numerical cases.

- The scripts are not certified statistical software or a full implementation of any CLSI document.
- Small-sample, normality, independence and variance-model assumptions require review. Grouped
  accuracy intervals use equal-weight independent group means; a single grouping factor cannot
  separate confounded day, analyst and instrument effects.
- TOST tests mean-difference equivalence. Individual agreement and decision-point bias need
  additional pre-stated criteria. Passing–Bablok does not remove all statistical assumptions.
- Synthetic fixtures validate computation, not physical selectivity, robustness, stability, assay
  performance, instrument integration or regulatory acceptability.
