"""Pure helpers for building manuscript-ready research packets."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


DOI_PATTERN = re.compile(
    r"(?:doi[:\s]*|https?://(?:dx\.)?doi\.org/)?"
    r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",
    re.IGNORECASE,
)
PMID_PATTERN = re.compile(
    r"(?:pubmed\.ncbi\.nlm\.nih\.gov/|pmid[:\s]*)(\d{6,9})",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")
SAMPLE_SIZE_PATTERN = re.compile(
    r"\b(?:n\s*=\s*|sample(?:\s+size)?\s+(?:of\s+)?)([\d,]+)\b",
    re.IGNORECASE,
)
EFFECT_PATTERN = re.compile(
    r"(?:\b\d+(?:\.\d+)?\s*%|\bp\s*[<=>]\s*0?\.\d+|"
    r"\b(?:OR|RR|HR|MD|SMD)\s*[=:]\s*-?\d+(?:\.\d+)?|"
    r"\b95\s*%\s*CI\b)",
    re.IGNORECASE,
)

SCHOLARLY_DOMAINS = {
    "pubmed.ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
    "europepmc.org",
    "crossref.org",
    "api.crossref.org",
    "openalex.org",
    "semanticscholar.org",
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
    "nature.com",
    "science.org",
    "cell.com",
    "pnas.org",
    "nejm.org",
    "thelancet.com",
    "jamanetwork.com",
    "bmj.com",
    "springer.com",
    "link.springer.com",
    "wiley.com",
    "onlinelibrary.wiley.com",
    "sciencedirect.com",
    "ieee.org",
    "ieeexplore.ieee.org",
    "acm.org",
    "dl.acm.org",
    "nih.gov",
    "who.int",
}

PREPRINT_DOMAINS = {"arxiv.org", "biorxiv.org", "medrxiv.org"}

PUBLICATION_TYPES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("systematic review", ("systematic review",)),
    ("meta-analysis", ("meta-analysis", "meta analysis")),
    (
        "randomized controlled trial",
        ("randomized controlled trial", "randomised controlled trial", " rct "),
    ),
    ("clinical trial", ("clinical trial",)),
    ("cohort study", ("cohort study", "prospective cohort", "retrospective cohort")),
    ("case-control study", ("case-control", "case control")),
    ("cross-sectional study", ("cross-sectional", "cross sectional")),
    ("methods/protocol", ("protocol", "benchmark", "methodology", "methods paper")),
    ("case report/series", ("case report", "case series")),
    ("review", ("review",)),
)

EVIDENCE_WEIGHTS = {
    "systematic review": 5,
    "meta-analysis": 5,
    "randomized controlled trial": 4,
    "clinical trial": 4,
    "cohort study": 3,
    "case-control study": 3,
    "cross-sectional study": 2,
    "methods/protocol": 2,
    "review": 2,
    "case report/series": 1,
    "primary/other": 2,
}


def canonicalize_url(url: str) -> str:
    """Return a stable URL for deduplication without tracking parameters."""
    if not url:
        return ""
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in {"ref", "source", "campaign"}
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), "")
    )


def normalize_title(title: str) -> str:
    """Normalize a title for conservative duplicate detection."""
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def source_excerpts(source: dict[str, Any]) -> list[str]:
    """Prefer Extract evidence over candidate snippets after retrieval succeeds."""
    excerpts = (
        source.get("extraction_excerpts")
        if source.get("extracted") and "extraction_excerpts" in source
        else source.get("excerpts")
    ) or []
    if isinstance(excerpts, str):
        excerpts = [excerpts]
    return [excerpt for excerpt in excerpts if isinstance(excerpt, str) and excerpt.strip()]


def source_text(source: dict[str, Any]) -> str:
    """Join source title and excerpts into searchable text."""
    return "\n".join(
        part.strip()
        for part in [str(source.get("title") or ""), *source_excerpts(source)]
        if part and str(part).strip()
    )


def extract_doi(text: str) -> str:
    """Extract the first DOI from text and strip sentence punctuation."""
    match = DOI_PATTERN.search(text or "")
    if not match:
        return ""
    return match.group(1).rstrip(".,;:)]}").lower()


def extract_pmid(text: str) -> str:
    """Extract the first PubMed identifier from text."""
    match = PMID_PATTERN.search(text or "")
    return match.group(1) if match else ""


def extract_year(source: dict[str, Any], text: str) -> str:
    """Extract a plausible publication year."""
    publish_date = str(source.get("publish_date") or "")
    match = YEAR_PATTERN.search(publish_date)
    if match:
        return match.group(1)
    match = YEAR_PATTERN.search(text)
    return match.group(1) if match else ""


def extract_label(text: str, labels: Iterable[str]) -> str:
    """Extract a simple labeled metadata value from source text."""
    joined = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"(?:^|\n)(?:{joined})\s*[:\-]\s*([^\n]{{2,300}})",
        text,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def split_sentences(text: str) -> list[str]:
    """Split excerpts into useful, reasonably bounded sentences."""
    compact = re.sub(r"\s+", " ", text or "").strip()
    if not compact:
        return []
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", compact)
    return [sentence.strip() for sentence in sentences if 30 <= len(sentence) <= 800]


def classify_publication(text: str) -> str:
    """Classify publication type from explicit wording."""
    lowered = f" {text.lower()} "
    for publication_type, terms in PUBLICATION_TYPES:
        if any(term in lowered for term in terms):
            return publication_type
    return "primary/other"


def evidence_quality(
    publication_type: str, *, preprint: bool, retracted: bool
) -> tuple[str, str]:
    """Return a transparent evidence tier and rationale."""
    if retracted:
        return "exclude", "Source is marked as retracted or withdrawn."
    weight = EVIDENCE_WEIGHTS.get(publication_type, 1)
    if preprint:
        weight = max(1, weight - 1)
    label = {5: "high", 4: "high", 3: "moderate", 2: "contextual"}.get(
        weight, "low"
    )
    rationale = f"Classified as {publication_type}"
    if preprint:
        rationale += "; preprint status lowers confidence pending peer review"
    return label, rationale + "."


def relevance_tags(text: str, publication_type: str) -> list[str]:
    """Map external evidence to manuscript sections without using Results."""
    lowered = text.lower()
    tags = {"introduction", "discussion"}
    if publication_type == "methods/protocol" or any(
        term in lowered
        for term in (
            "method",
            "protocol",
            "assay",
            "measure",
            "instrument",
            "model",
            "analysis",
            "benchmark",
        )
    ):
        tags.add("methods-rationale")
    return sorted(tags)


def _host(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def is_scholarly_url(url: str) -> bool:
    host = _host(url)
    return any(host == domain or host.endswith(f".{domain}") for domain in SCHOLARLY_DOMAINS)


def is_preprint_url(url: str) -> bool:
    host = _host(url)
    return any(host == domain or host.endswith(f".{domain}") for domain in PREPRINT_DOMAINS)


def deduplicate_sources(sources: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge duplicate search/extract records by DOI, PMID, URL, or title."""
    merged: list[dict[str, Any]] = []
    key_to_index: dict[str, int] = {}

    for raw_source in sources:
        source = dict(raw_source)
        source["url"] = canonicalize_url(str(source.get("url") or ""))
        text = source_text(source)
        doi = str(source.get("doi") or extract_doi(f"{source['url']}\n{text}"))
        pmid = str(source.get("pmid") or extract_pmid(f"{source['url']}\n{text}"))
        title_key = normalize_title(str(source.get("title") or ""))
        keys = [
            f"doi:{doi}" if doi else "",
            f"pmid:{pmid}" if pmid else "",
            f"url:{source['url']}" if source["url"] else "",
            f"title:{title_key}" if len(title_key) >= 20 else "",
        ]
        keys = [key for key in keys if key]
        existing = next((key_to_index[key] for key in keys if key in key_to_index), None)

        if existing is None:
            source["doi"] = doi
            source["pmid"] = pmid
            source["facets"] = sorted(set(source.get("facets") or []))
            source["excerpts"] = list(dict.fromkeys(source.get("excerpts") or []))
            merged.append(source)
            index = len(merged) - 1
            for key in keys:
                key_to_index[key] = index
            continue

        current = merged[existing]
        if not current.get("title") and source.get("title"):
            current["title"] = source["title"]
        if not current.get("publish_date") and source.get("publish_date"):
            current["publish_date"] = source["publish_date"]
        if not current.get("doi") and doi:
            current["doi"] = doi
        if not current.get("pmid") and pmid:
            current["pmid"] = pmid
        current["excerpts"] = list(
            dict.fromkeys([*(current.get("excerpts") or []), *(source.get("excerpts") or [])])
        )
        current["facets"] = sorted(
            set(current.get("facets") or []) | set(source.get("facets") or [])
        )
        if source.get("extracted"):
            current["extracted"] = True
            current["extraction_excerpts"] = list(
                dict.fromkeys([
                    *(current.get("extraction_excerpts") or []), *source_excerpts(source)
                ])
            )
        for key in keys:
            key_to_index[key] = existing

    return merged


def normalize_reference(source: dict[str, Any], index: int) -> dict[str, Any]:
    """Convert a source into a structured evidence-matrix record."""
    text = source_text(source)
    url = canonicalize_url(str(source.get("url") or ""))
    doi = str(source.get("doi") or extract_doi(f"{url}\n{text}"))
    pmid = str(source.get("pmid") or extract_pmid(f"{url}\n{text}"))
    publication_type = classify_publication(text)
    preprint = is_preprint_url(url) or "preprint" in text.lower()
    retracted = any(
        marker in text.lower()
        for marker in ("retracted", "retraction notice", "withdrawn")
    )
    corrected = any(marker in text.lower() for marker in ("correction", "erratum"))
    quality, quality_rationale = evidence_quality(
        publication_type, preprint=preprint, retracted=retracted
    )
    sentences = split_sentences(text)
    findings = [
        sentence
        for sentence in sentences
        if any(
            term in sentence.lower()
            for term in (
                "found",
                "showed",
                "demonstrated",
                "associated",
                "increased",
                "decreased",
                "effect",
                "result",
                "concluded",
            )
        )
    ][:3]
    if not findings:
        findings = sentences[:2]
    quantitative = [sentence for sentence in sentences if EFFECT_PATTERN.search(sentence)][:5]
    limitations = [
        sentence
        for sentence in sentences
        if any(
            term in sentence.lower()
            for term in ("limitation", "limited by", "bias", "uncertain", "caution")
        )
    ][:3]
    sample_match = SAMPLE_SIZE_PATTERN.search(text)
    authors = extract_label(text, ("authors", "author"))
    venue = extract_label(text, ("journal", "venue", "published in"))
    methods = extract_label(text, ("methods", "methodology", "design"))
    outcomes = extract_label(text, ("outcomes", "outcome", "endpoints", "endpoint"))
    verification_status = (
        "extracted"
        if source.get("extracted") and source_excerpts(source)
        else "search-only"
    )

    return {
        "reference_id": f"ref-{index:03d}",
        "title": str(source.get("title") or "Untitled source").strip(),
        "authors": authors,
        "year": extract_year(source, text),
        "venue": venue,
        "url": url,
        "doi": doi,
        "pmid": pmid,
        "publication_type": publication_type,
        "study_design": publication_type,
        "population_or_system": extract_label(
            text, ("population", "participants", "subjects", "system")
        ),
        "sample_size": sample_match.group(1).replace(",", "") if sample_match else "",
        "methods": methods,
        "intervention_or_exposure": extract_label(
            text, ("intervention", "exposure", "treatment")
        ),
        "comparator": extract_label(text, ("comparator", "control")),
        "outcomes": outcomes,
        "key_findings": findings,
        "quantitative_findings": quantitative,
        "limitations": limitations,
        "evidence_quality": quality,
        "quality_rationale": quality_rationale,
        "preprint": preprint,
        "retracted": retracted,
        "corrected": corrected,
        "verification_status": verification_status,
        "manuscript_sections": relevance_tags(text, publication_type),
        "supporting_excerpts": source_excerpts(source)[:5],
        "facets": list(source.get("facets") or []),
        "scholarly_source": is_scholarly_url(url),
    }


def reference_score(reference: dict[str, Any]) -> tuple[int, int, int, int]:
    """Sort by exclusion status, verification, quality, and recency."""
    quality_score = {
        "high": 4,
        "moderate": 3,
        "contextual": 2,
        "low": 1,
        "exclude": 0,
    }.get(str(reference.get("evidence_quality")), 0)
    verification_score = {
        "extracted": 2,
        "search-only": 0,
    }.get(str(reference.get("verification_status")), 0)
    try:
        year = int(reference.get("year") or 0)
    except (TypeError, ValueError):
        year = 0
    return (
        0 if reference.get("retracted") else 1,
        verification_score,
        quality_score,
        year,
    )


def _claim_map(references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for reference in references:
        if reference.get("retracted"):
            continue
        for finding in reference.get("key_findings") or []:
            claims.append(
                {
                    "claim": finding,
                    "reference_ids": [reference["reference_id"]],
                    "supporting_excerpts": (reference.get("supporting_excerpts") or [])[:2],
                    "status": (
                        "single-source" if reference.get("verification_status") == "extracted"
                        else "unverified-source"
                    ),
                }
            )
    return claims


def _synthesis(references: list[dict[str, Any]]) -> dict[str, Any]:
    references = [reference for reference in references if not reference.get("retracted")]
    conflict_terms = (
        "conflict",
        "contradict",
        "no significant",
        "null result",
        "did not",
        "failed to",
        "inconsistent",
    )
    consensus: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    for reference in references:
        for finding in reference.get("key_findings") or []:
            item = {"reference_id": reference["reference_id"], "finding": finding}
            if any(term in finding.lower() for term in conflict_terms):
                conflicts.append(item)
            elif len(consensus) < 20:
                consensus.append(item)

    design_counts = Counter(
        str(reference.get("publication_type") or "unknown")
        for reference in references
    )
    gaps: list[str] = []
    if not any(
        reference.get("evidence_quality") == "high"
        and reference.get("verification_status") == "extracted"
        for reference in references
    ):
        gaps.append("No high-tier synthesis or trial evidence was verified.")
    if not conflicts:
        gaps.append(
            "No explicit contradictory or null evidence was identified; run a targeted "
            "negative-results search before asserting consensus."
        )
    if not any(reference.get("year") for reference in references):
        gaps.append("Publication years remain incomplete.")
    return {
        "consensus_evidence": consensus,
        "conflicting_evidence": conflicts,
        "methodological_patterns": dict(design_counts),
        "research_gaps": gaps,
    }


def _section_briefs(references: list[dict[str, Any]]) -> dict[str, Any]:
    briefs: dict[str, Any] = {
        "introduction": {
            "purpose": "Established background, significance, and unresolved gap.",
            "reference_ids": [],
            "candidate_evidence": [],
        },
        "methods-rationale": {
            "purpose": "Published precedent for measures, protocols, models, and analyses.",
            "reference_ids": [],
            "candidate_evidence": [],
        },
        "discussion": {
            "purpose": "Supporting and conflicting studies, mechanisms, limits, and implications.",
            "reference_ids": [],
            "candidate_evidence": [],
        },
    }
    for reference in references:
        if reference.get("retracted"):
            continue
        for section in reference.get("manuscript_sections") or []:
            brief = briefs.get(section)
            if not brief:
                continue
            brief["reference_ids"].append(reference["reference_id"])
            if reference.get("key_findings"):
                brief["candidate_evidence"].append(
                    {
                        "reference_id": reference["reference_id"],
                        "finding": reference["key_findings"][0],
                    }
                )
    for brief in briefs.values():
        brief["reference_ids"] = brief["reference_ids"][:30]
        brief["candidate_evidence"] = brief["candidate_evidence"][:20]
    return briefs


def _coverage(
    references: list[dict[str, Any]], target_references: int
) -> dict[str, Any]:
    verified = [
        reference
        for reference in references
        if reference.get("verification_status") == "extracted"
        and not reference.get("retracted")
    ]
    years = Counter(
        str(reference["year"])
        for reference in references
        if reference.get("year")
    )
    quality = Counter(
        str(reference.get("evidence_quality") or "unknown")
        for reference in references
    )
    verification = Counter(
        str(reference.get("verification_status") or "unknown")
        for reference in references
    )
    return {
        "requested_references": target_references,
        "total_unique_references": len(references),
        "verified_references": len(verified),
        "shortfall": max(0, target_references - len(verified)),
        "evidence_quality_mix": dict(quality),
        "verification_mix": dict(verification),
        "publication_years": dict(sorted(years.items())),
        "scholarly_sources": sum(
            1 for reference in references if reference.get("scholarly_source")
        ),
        "preprints": sum(1 for reference in references if reference.get("preprint")),
        "retracted_or_withdrawn": sum(
            1 for reference in references if reference.get("retracted")
        ),
        "corrections_or_errata": sum(
            1 for reference in references if reference.get("corrected")
        ),
        "missing_doi_or_pmid": sum(
            1
            for reference in references
            if not reference.get("doi") and not reference.get("pmid")
        ),
        "full_text_note": (
            "Verified means nonempty excerpts were retrieved by Extract, not that "
            "bibliographic identity or claims were manually verified. Paywalled full "
            "text may remain unavailable and must not be represented as reviewed."
        ),
    }


def build_manuscript_packet(
    *,
    query: str,
    sources: list[dict[str, Any]],
    search_ledger: list[dict[str, Any]],
    target_references: int = 60,
    manuscript_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured packet without adding facts beyond source excerpts."""
    deduplicated = deduplicate_sources(sources)
    references = [
        normalize_reference(source, index)
        for index, source in enumerate(deduplicated, start=1)
    ]
    references.sort(key=reference_score, reverse=True)
    for index, reference in enumerate(references, start=1):
        reference["reference_id"] = f"ref-{index:03d}"

    coverage = _coverage(references, target_references)
    warnings: list[str] = []
    if coverage["shortfall"]:
        warnings.append(
            f"Verified {coverage['verified_references']} of "
            f"{target_references} requested references; the list was not padded."
        )
    if coverage["retracted_or_withdrawn"]:
        warnings.append(
            "Retracted or withdrawn records are marked for exclusion and must not support claims."
        )
    if not manuscript_context:
        warnings.append(
            "No structured manuscript context was supplied; section briefs are broad."
        )

    return {
        "schema_version": "1.0",
        "query": query,
        "manuscript_context": manuscript_context or {},
        "target_references": target_references,
        "references": references,
        "evidence_matrix": references,
        "claim_source_map": _claim_map(references),
        "synthesis": _synthesis(references),
        "section_briefs": _section_briefs(references),
        "coverage": coverage,
        "search_ledger": search_ledger,
        "warnings": warnings,
    }


def citation_text(reference: dict[str, Any]) -> str:
    """Render a conservative citation without inventing missing metadata."""
    authors = str(reference.get("authors") or "").strip()
    title = str(reference.get("title") or "Untitled source").strip()
    year = str(reference.get("year") or "n.d.")
    venue = str(reference.get("venue") or "").strip()
    identifier = (
        f"https://doi.org/{reference['doi']}"
        if reference.get("doi")
        else str(reference.get("url") or "")
    )
    lead = f"{authors} ({year}). " if authors else f"({year}). "
    venue_text = f" {venue}." if venue else ""
    return f"{lead}{title}.{venue_text} {identifier}".strip()


def packet_markdown(packet: dict[str, Any]) -> str:
    """Render the packet as a concise, source-linked Markdown artifact."""
    coverage = packet["coverage"]
    lines = [
        "# Manuscript Research Packet",
        "",
        f"**Query:** {packet['query']}",
        f"**Verified references:** {coverage['verified_references']} / "
        f"{coverage['requested_references']}",
        "",
    ]
    if packet.get("warnings"):
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in packet["warnings"])
        lines.append("")

    lines.extend(["## References", ""])
    for reference in packet["references"]:
        status = reference.get("verification_status", "unknown")
        quality = reference.get("evidence_quality", "unknown")
        lines.append(
            f"- **{reference['reference_id']}** {citation_text(reference)} "
            f"_[{status}; {quality}]_"
        )

    lines.extend(["", "## Evidence Synthesis", "", "### Consensus candidates", ""])
    consensus = packet["synthesis"]["consensus_evidence"]
    lines.extend(
        f"- [{item['reference_id']}] {item['finding']}" for item in consensus
    )
    if not consensus:
        lines.append("- No consensus statements could be extracted.")

    lines.extend(["", "### Conflicting or null evidence", ""])
    conflicts = packet["synthesis"]["conflicting_evidence"]
    lines.extend(
        f"- [{item['reference_id']}] {item['finding']}" for item in conflicts
    )
    if not conflicts:
        lines.append("- No explicit conflicting evidence was identified.")

    lines.extend(["", "### Research gaps", ""])
    gaps = packet["synthesis"]["research_gaps"]
    lines.extend(f"- {gap}" for gap in gaps)
    if not gaps:
        lines.append("- No automatic gap signal was detected; expert review remains required.")

    lines.extend(["", "## Section Briefs", ""])
    for section, brief in packet["section_briefs"].items():
        lines.extend([f"### {section.replace('-', ' ').title()}", "", brief["purpose"], ""])
        for item in brief["candidate_evidence"]:
            lines.append(f"- [{item['reference_id']}] {item['finding']}")
        if not brief["candidate_evidence"]:
            lines.append("- No section-specific evidence extracted.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def bibtex_text(references: list[dict[str, Any]]) -> str:
    """Render minimal BibTeX records using only verified metadata."""
    records: list[str] = []
    for reference in references:
        if reference.get("retracted"):
            continue
        key_base = re.sub(
            r"[^A-Za-z0-9]+",
            "",
            f"{reference.get('authors') or 'source'}"
            f"{reference.get('year') or 'nd'}"
            f"{reference.get('reference_id')}",
        )
        fields = {
            "title": reference.get("title"),
            "author": reference.get("authors"),
            "year": reference.get("year"),
            "journal": reference.get("venue"),
            "doi": reference.get("doi"),
            "url": reference.get("url"),
        }
        lines = [f"@article{{{key_base},"]
        for name, value in fields.items():
            if value:
                escaped = str(value).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
                lines.append(f"  {name} = {{{escaped}}},")
        lines.append("}")
        records.append("\n".join(lines))
    return "\n\n".join(records) + ("\n" if records else "")


def save_packet(packet: dict[str, Any], directory: str | Path) -> dict[str, str]:
    """Write reproducible packet artifacts and return their paths."""
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "packet_json": destination / "packet.json",
        "packet_markdown": destination / "packet.md",
        "references_json": destination / "references.json",
        "references_bib": destination / "references.bib",
        "evidence_matrix": destination / "evidence-matrix.json",
        "claim_source_map": destination / "claim-source-map.json",
        "synthesis": destination / "synthesis.json",
        "section_briefs": destination / "section-briefs.json",
        "coverage": destination / "coverage.json",
        "search_ledger": destination / "search-ledger.json",
    }
    payloads: dict[str, Any] = {
        "packet_json": packet,
        "references_json": packet["references"],
        "evidence_matrix": packet["evidence_matrix"],
        "claim_source_map": packet["claim_source_map"],
        "synthesis": packet["synthesis"],
        "section_briefs": packet["section_briefs"],
        "coverage": packet["coverage"],
        "search_ledger": packet["search_ledger"],
    }
    for name, payload in payloads.items():
        artifacts[name].write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    artifacts["packet_markdown"].write_text(packet_markdown(packet), encoding="utf-8")
    artifacts["references_bib"].write_text(
        bibtex_text(packet["references"]), encoding="utf-8"
    )
    return {name: str(path) for name, path in artifacts.items()}
