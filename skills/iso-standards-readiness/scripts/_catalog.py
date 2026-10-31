#!/usr/bin/env python3
"""Per-standard process labels and scope vocabulary used by the local checks.

The labels are workflow topics. They are not clause text from any standard, not a
clause map, and not a substitute for an authorized copy. Listing a standard here
does not decide that the standard applies to an organization, and the profiles
carry no assurance meaning: selecting an accreditation profile does not make a
result an accreditation outcome.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Scope vocabulary ------------------------------------------------------

DEVICE_LIFECYCLE_ACTIVITIES = (
    "design-and-development",
    "manufacturing",
    "contract-manufacturing",
    "sterilization",
    "packaging-and-labeling",
    "storage",
    "distribution",
    "installation",
    "servicing",
    "software-development",
    "complaint-handling",
    "postmarket-surveillance",
    "regulatory-reporting",
)

LABORATORY_ACTIVITIES = (
    "sampling",
    "testing",
    "calibration",
    "examination",
    "point-of-care-testing",
    "specimen-collection-and-transport",
    "method-development-and-validation",
    "interpretation-and-advice",
    "subcontracted-activity",
    "storage-and-retention",
    "data-and-reporting",
)

# --- Process/evidence domains ---------------------------------------------

# Retained under its original name: the device QMS domain set stays the default
# vocabulary for manifests written against earlier versions of this skill.
PROCESS_DOMAINS = (
    "scope-and-roles",
    "document-and-record-control",
    "risk-management",
    "design-and-development",
    "supplier-controls",
    "production-and-service",
    "process-and-software-validation",
    "identification-and-traceability",
    "complaints-and-feedback",
    "postmarket-and-vigilance",
    "nonconformity-and-capa",
    "internal-audit",
    "management-review",
    "training-and-competence",
    "change-control",
)

RISK_MANAGEMENT_DOMAINS = (
    "risk-management-plan",
    "risk-management-file",
    "competence-and-authority",
    "intended-use-and-characteristics",
    "hazard-identification",
    "risk-estimation-and-evaluation",
    "risk-control-option-analysis",
    "risk-control-implementation-and-verification",
    "risk-control-side-effects-review",
    "residual-risk-evaluation",
    "benefit-risk-analysis",
    "overall-residual-risk-evaluation",
    "risk-management-review-and-report",
    "production-and-postproduction-information",
    "change-control",
)

TESTING_LABORATORY_DOMAINS = (
    "scope-and-impartiality",
    "organizational-structure-and-management",
    "personnel-competence",
    "facilities-and-environmental-conditions",
    "equipment-and-calibration",
    "metrological-traceability",
    "externally-provided-products-and-services",
    "review-of-requests-and-contracts",
    "method-selection-verification-and-validation",
    "sampling",
    "handling-of-items",
    "technical-records",
    "measurement-uncertainty",
    "validity-of-results-and-proficiency-testing",
    "reporting-and-decision-rules",
    "complaints",
    "nonconforming-work",
    "data-and-information-management",
    "internal-audit",
    "management-review",
    "corrective-action-and-improvement",
)

MEDICAL_LABORATORY_DOMAINS = (
    "scope-and-impartiality",
    "organizational-structure-and-governance",
    "personnel-competence",
    "facilities-and-safety",
    "equipment-and-calibration",
    "metrological-traceability",
    "reagents-and-consumables",
    "externally-provided-products-and-services",
    "pre-examination-processes",
    "examination-methods-verification-and-validation",
    "measurement-uncertainty",
    "validity-of-results-and-external-quality-assessment",
    "point-of-care-testing",
    "post-examination-and-reporting",
    "laboratory-information-management",
    "complaints",
    "nonconformity-and-corrective-action",
    "risk-management-and-improvement",
    "internal-audit",
    "management-review",
    "continuity-and-emergency-preparedness",
)

# --- Scope-item field sets -------------------------------------------------

DEVICE_PRODUCT_FIELDS = (
    ("family", 300),
    ("intended_use", 2_000),
    ("classification_or_rationale", 1_000),
)

CALIBRATION_SCOPE_FIELDS = (
    ("discipline", 300),
    ("method_or_procedure", 500),
    ("measurand_or_property", 500),
    ("range_and_uncertainty", 500),
)

EXAMINATION_SCOPE_FIELDS = (
    ("discipline", 300),
    ("examination_or_measurand", 500),
    ("method_or_procedure", 500),
    ("primary_sample_type", 300),
)


@dataclass(frozen=True)
class StandardProfile:
    """Declared vocabulary for one standard. Carries no conformity meaning."""

    key: str
    label: str
    assurance_lane: str
    activities_section: str
    scope_activities: tuple[str, ...]
    scope_item_section: str
    scope_item_fields: tuple[tuple[str, int], ...]
    process_domains: tuple[str, ...]


STANDARDS: dict[str, StandardProfile] = {
    "iso-13485": StandardProfile(
        key="iso-13485",
        label="ISO 13485 medical device quality management system",
        assurance_lane="third-party certification",
        activities_section="lifecycle_activities",
        scope_activities=DEVICE_LIFECYCLE_ACTIVITIES,
        scope_item_section="products",
        scope_item_fields=DEVICE_PRODUCT_FIELDS,
        process_domains=PROCESS_DOMAINS,
    ),
    "iso-14971": StandardProfile(
        key="iso-14971",
        label="ISO 14971 application of risk management to medical devices",
        assurance_lane="risk evidence assessed inside a declared assurance lane",
        activities_section="lifecycle_activities",
        scope_activities=DEVICE_LIFECYCLE_ACTIVITIES,
        scope_item_section="products",
        scope_item_fields=DEVICE_PRODUCT_FIELDS,
        process_domains=RISK_MANAGEMENT_DOMAINS,
    ),
    "iso-17025": StandardProfile(
        key="iso-17025",
        label="ISO/IEC 17025 competence of testing and calibration laboratories",
        assurance_lane="accreditation by an accreditation body",
        activities_section="laboratory_activities",
        scope_activities=LABORATORY_ACTIVITIES,
        scope_item_section="scope_items",
        scope_item_fields=CALIBRATION_SCOPE_FIELDS,
        process_domains=TESTING_LABORATORY_DOMAINS,
    ),
    "iso-15189": StandardProfile(
        key="iso-15189",
        label="ISO 15189 quality and competence of medical laboratories",
        assurance_lane="accreditation by an accreditation body",
        activities_section="laboratory_activities",
        scope_activities=LABORATORY_ACTIVITIES,
        scope_item_section="scope_items",
        scope_item_fields=EXAMINATION_SCOPE_FIELDS,
        process_domains=MEDICAL_LABORATORY_DOMAINS,
    ),
}

STANDARD_KEYS = tuple(sorted(STANDARDS))
DEFAULT_STANDARD = "iso-13485"

# --- Lane-specific catalogs ------------------------------------------------

QMSR_TRANSITION_ITEMS = (
    "qmsr-source-basis",
    "applicability-owner",
    "fda-supplemental-provisions",
    "legacy-qsr-reference-disposition",
    "pre-effective-date-record-review",
    "inspection-accessible-records",
    "inspection-process-training",
    "qsit-retirement",
    "complaint-and-servicing-records",
    "labeling-and-packaging-controls",
    "software-validation-impact",
    "supplier-and-outsourced-process-controls",
    "certificate-claims-review",
    "change-control-approval",
)

TRACEABILITY_LINKS = (
    "intended_use",
    "hazard_or_signal",
    "risk_evaluation",
    "risk_control",
    "design_input",
    "design_output",
    "verification",
    "validation",
    "production_control",
    "postmarket_source",
)
