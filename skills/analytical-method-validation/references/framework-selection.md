# Which Framework Governs

Research basis: **2026-09-30**. Confirm every date and edition against the official source before
relying on it; see `source-ledger.md`.

Framework selection is the first decision and the one most often skipped. Getting it wrong
invalidates the protocol regardless of how well the studies are executed, because each framework
requires a different set of characteristics, a different study layout, and a different treatment of
acceptance criteria.

## The deciding questions, in order

**1. Is the measurand a drug concentration in a biological matrix, supporting a nonclinical or
clinical study?**
→ **ICH M10.** This covers pharmacokinetics, toxicokinetics, and bioequivalence. M10 supplies
explicit numeric criteria, and they differ between chromatographic assays and ligand binding
assays. Q2(R2) does not govern here.

**2. Is it a quality attribute of a drug substance or drug product — assay, potency, impurity,
identity, dissolution, content uniformity?**
→ **ICH Q2(R2)** for validation, with **ICH Q14** for development, robustness, the analytical
target profile (formal documentation optional), and lifecycle change management. If the procedure is compendial and being used as
written, see question 3 first.

**3. Is the procedure a compendial (pharmacopoeial) procedure?**
→ **USP <1226> verification** if it is used as written and within its stated scope. Verification
assesses selected characteristics to show the procedure works under actual conditions of use; it is
not revalidation and does not repeat the full study. → **USP <1225> validation** if the procedure
is non-compendial, or compendial but used outside its scope. Confirm the effective edition: the linked 2025 <1225> preview is a proposal. Both sit inside the **USP <1220>**
three-stage lifecycle. Regional pharmacopoeias (Ph. Eur., JP) have their own general chapters —
check which pharmacopoeia the specification cites.

**4. Is it a clinical laboratory measurement procedure reporting patient results?**
→ **CLSI EP series**, inside a CLIA/CAP or ISO 15189 quality system. The vocabulary differs from
pharmaceutical work: *verification* of a manufacturer's claims for an unmodified FDA-cleared or approved nonwaived assay is a much
smaller exercise than *establishment* of performance for a laboratory-developed test, and the
distinction is regulatory, not stylistic.

**5. Is the laboratory accredited to ISO/IEC 17025 and the method non-standard, laboratory-developed,
or a modified standard method?**
→ **ISO/IEC 17025 clause 7.2.2** requires validation as extensive as necessary to meet the needs of
the intended application, plus measurement uncertainty under clause 7.6. It does not prescribe one universal characteristic
checklist or numeric acceptance limits; the laboratory justifies both.

**6. Is it an environmental, food, or forensic method under a prescribed method system?**
→ The method system governs (for example a published EPA method, an AOAC Official Method, or a
regulator's prescribed procedure), usually with its own validation and QC requirements written into
the method itself. Do not substitute a pharmaceutical framework.

## More than one can apply

Common and legitimate. A contract laboratory accredited to ISO/IEC 17025 running a compendial assay
for a pharmaceutical client satisfies <1226> for the procedure and 17025 clause 7.2 for the
accreditation scope, with the client's specification supplying the criteria. Record which framework
each requirement traces to, so a later change can be assessed against the right one.

## Do not blend them

The failure mode is a protocol that mixes Q2(R1)-era characteristic names, an M10 numeric tolerance
imported because it was memorable, and a CLSI study layout. It satisfies none of the three and is
hard to defend because no single source can be cited for any of it. If a requirement is in the
protocol, name the framework and section it comes from.

## Where the numbers come from

| Framework | Numeric acceptance criteria |
| --- | --- |
| ICH Q2(R2) | Almost none. Derive from the specification, the ATP, or development data, and justify. |
| ICH Q14 | None. It supplies the ATP concept and the development/robustness framework. |
| ICH M10 | Explicit, and modality-dependent. Use them as written. |
| USP <1225>/<1226>/<1220> | Consult the authorised text. |
| CLSI EP | Consult the authorised text; many EP documents supply study designs rather than limits. |
| ISO/IEC 17025 | None. The laboratory sets and justifies them. |

Q2(R2)'s reticence is deliberate: a criterion that is not tied to what the result is used for is
arbitrary. An assay releasing product against a 95.0–105.0% specification needs different precision
than one supporting a 70–130% content-uniformity limit. Deriving the criterion from the decision the
result supports is the substance of the exercise, not paperwork around it.

## Related skills in this repository

- `iso-standards-readiness` — the surrounding quality system (ISO/IEC 17025, ISO 15189
  accreditation readiness, quality manual, CAPA). That skill operates at the laboratory level; this
  one operates at the level of a single procedure.
- `statistical-analysis`, `statistical-power` — general inference and study sizing.
- `uncertainty-and-units` — unit handling and measurement uncertainty propagation, which ISO/IEC
  17025 clause 7.6 requires alongside validation.
