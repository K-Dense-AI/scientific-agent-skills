"""Synthetic, non-submission fixtures for local scientific-writing tests."""

from __future__ import annotations

import hashlib


def valid_source_manifest() -> dict:
    return {
        "schema_version": "1.0",
        "sources": [
            {
                "evidence_id": "E001",
                "source_type": "guideline",
                "title": "European Code of Conduct for Research Integrity",
                "authors": ["ALLEA"],
                "year": 2023,
                "identifiers": {
                    "doi": "10.26356/ECOC",
                    "pmid": "",
                    "pmcid": "",
                    "isbn": "",
                    "url": "https://allea.org/portfolio-item/european-code-of-conduct-2023",
                },
                "locator": "Research integrity principles",
                "confidentiality": "public",
                "verification": {
                    "status": "verified",
                    "source_opened": True,
                    "verified_by": "Test verifier",
                    "verified_on": "2026-07-24",
                },
            }
        ],
    }


def valid_claim_csv(text: str = "Verified test statement") -> str:
    digest = hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()
    return (
        "claim_id,section,claim_kind,claim_text_sha256,evidence_ids,"
        "verification_status,uncertainty,analysis_intent\n"
        f"C001,Introduction,factual,{digest},E001,verified,not_applicable,"
        "not_applicable\n"
    )


def valid_consistency_manifest() -> dict:
    return {
        "schema_version": "1.0",
        "numeric_facts": [
            {
                "fact_id": "N001",
                "concept": "synthetic_count",
                "section": "Methods",
                "value": 2,
                "unit": "records",
                "numerator": None,
                "denominator": None,
                "sample_size": 2,
                "analysis_set": "synthetic_set",
                "evidence_ids": ["E001"],
            },
            {
                "fact_id": "N002",
                "concept": "synthetic_count",
                "section": "Results",
                "value": 2,
                "unit": "records",
                "numerator": None,
                "denominator": None,
                "sample_size": 2,
                "analysis_set": "synthetic_set",
                "evidence_ids": ["E001"],
            },
        ],
        "methods": [
            {
                "method_id": "M001",
                "name": "Synthetic deterministic check",
                "analysis_intent": "descriptive",
                "protocol_status": "not_applicable",
                "outcome_ids": ["O001"],
            }
        ],
        "results": [
            {
                "result_id": "R001",
                "method_id": "M001",
                "outcome_id": "O001",
                "analysis_intent": "descriptive",
                "sample_size": 2,
                "evidence_ids": ["E001"],
                "reported_sections": ["Results"],
            }
        ],
    }


def valid_authorship_manifest() -> dict:
    digest = hashlib.sha256(b"not applicable in synthetic fixture").hexdigest()
    declaration = {
        "status": "not_applicable",
        "content_sha256": digest,
        "verified_by": "Test verifier",
        "verified_on": "2026-07-24",
    }
    return {
        "schema_version": "1.0",
        "authors": [
            {
                "author_id": "A001",
                "name": "Example Human",
                "is_human": True,
                "authorship_criteria": {
                    "substantial_contribution": True,
                    "drafted_or_critically_revised": True,
                    "final_approval": True,
                    "accountable_for_work": True,
                },
                "credit_roles": [
                    "Conceptualization",
                    "Writing – original draft",
                    "Writing – review & editing",
                ],
            }
        ],
        "contributors": [],
        "corresponding_author_id": "A001",
        "accountability": {
            "all_authors_approved": True,
            "guarantor_author_ids": ["A001"],
        },
        "ai_use": {
            "used": False,
            "tools": [],
            "disclosed_in": [],
            "human_verification_complete": True,
            "journal_policy_checked": True,
        },
        "declarations": {
            "ai_use": dict(declaration),
            "author_contributions": dict(declaration),
            "conflicts": dict(declaration),
            "funding": dict(declaration),
        },
    }


def valid_manuscript_manifest() -> dict:
    return {
        "schema_version": "1.0",
        "document_id": "test-manuscript",
        "study_design": "randomized_trial",
        "draft_status": "submission_candidate",
        "submission_ready": True,
        "registries": {
            "source_manifest": "source_manifest.json",
            "claim_evidence": "claims.csv",
            "consistency_manifest": "consistency_manifest.json",
            "authorship_manifest": "authorship.json",
            "reporting_coverage": "reporting_coverage.json",
        },
        "reporting_guidelines": ["consort-2025"],
        "human_verification": {
            "completed": True,
            "verified_by": "Test verifier",
            "verified_on": "2026-07-24",
        },
        "confidentiality_review": {
            "completed": True,
            "verified_by": "Test verifier",
            "verified_on": "2026-07-24",
            "policy_checked": True,
            "external_services_authorized": False,
        },
        "required_statements": {
            "ethics": "not_applicable",
            "consent": "not_applicable",
            "funding": "not_applicable",
            "conflicts": "not_applicable",
            "data_availability": "not_applicable",
            "code_availability": "not_applicable",
            "author_contributions": "verified",
            "ai_disclosure": "not_applicable",
        },
    }
