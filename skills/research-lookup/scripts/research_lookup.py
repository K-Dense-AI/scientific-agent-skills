#!/usr/bin/env python3
"""Parallel-first research retrieval for manuscript evidence compilation.

The public ``ResearchLookup`` class and CLI remain backward compatible while
ordinary queries use Parallel Search. Parallel Chat and Research are explicit,
and Perplexity remains an optional explicit/failure fallback.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from manuscript_packet import (
    build_manuscript_packet,
    canonicalize_url,
    deduplicate_sources,
    normalize_reference,
    packet_markdown,
    reference_score,
    save_packet,
)


DEFAULT_TARGET_REFERENCES = 60
DEFAULT_MAX_RESULTS = 20
DEFAULT_EXTRACT_BATCH_SIZE = 10

ACADEMIC_DOMAINS = (
    "pubmed.ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
    "europepmc.org",
    "crossref.org",
    "openalex.org",
    "semanticscholar.org",
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
    "ncbi.nlm.nih.gov",
    "nature.com",
    "science.org",
    "cell.com",
    "pnas.org",
    "nejm.org",
    "thelancet.com",
    "jamanetwork.com",
    "bmj.com",
    "springer.com",
    "wiley.com",
    "sciencedirect.com",
    "ieee.org",
    "acm.org",
    "nih.gov",
    "who.int",
)

ACADEMIC_KEYWORDS = (
    "find papers",
    "find paper",
    "find articles",
    "find article",
    "cite ",
    "citation",
    "doi ",
    "doi:",
    "pubmed",
    "pmid",
    "journal article",
    "peer-reviewed",
    "systematic review",
    "meta-analysis",
    "literature search",
    "literature review",
    "academic papers",
    "research papers",
    "published studies",
    "scholarly",
    "arxiv",
    "preprint",
    "foundational papers",
    "seminal papers",
    "landmark papers",
    "highly cited",
    "manuscript",
    "evidence base",
)

ACADEMIC_FACETS = (
    (
        "recent-primary",
        "Find recent peer-reviewed primary studies directly addressing the topic. "
        "Prioritize complete bibliographic metadata, DOI or PMID, study design, "
        "sample size, methods, outcomes, quantitative findings, and limitations.",
        ("primary study", "peer reviewed", "recent evidence"),
    ),
    (
        "reviews",
        "Find systematic reviews, meta-analyses, evidence syntheses, and major "
        "consensus statements directly addressing the topic.",
        ("systematic review", "meta-analysis", "evidence synthesis"),
    ),
    (
        "seminal",
        "Find seminal, foundational, landmark, and field-defining publications on "
        "the topic. Prefer sources with stable identifiers and authoritative records.",
        ("seminal paper", "foundational study", "landmark research"),
    ),
    (
        "methods",
        "Find methods, protocols, measurement validation, benchmark, and mechanistic "
        "studies that can justify manuscript methods and interpretation.",
        ("methods", "protocol", "validation", "mechanism"),
    ),
    (
        "contradictory",
        "Find conflicting, contradictory, null, negative, replication, and limitation "
        "evidence on the topic. Do not assume the dominant conclusion is correct.",
        ("conflicting evidence", "null results", "limitations", "replication"),
    ),
)


class ResearchLookup:
    """Research lookup with Parallel Search as the stable default backend."""

    PARALLEL_SYSTEM_PROMPT = (
        "Compile a rigorous, citation-rich research report for manuscript preparation. "
        "Prioritize primary and peer-reviewed literature, distinguish preprints, include "
        "quantitative evidence and limitations, surface contradictory findings, and do "
        "not invent citations."
    )

    def __init__(
        self,
        force_backend: str | None = None,
        *,
        academic: bool | None = None,
        target_references: int = DEFAULT_TARGET_REFERENCES,
        search_mode: str = "basic",
        max_results: int = DEFAULT_MAX_RESULTS,
        include_domains: list[str] | None = None,
        after_date: str | None = None,
        extract_limit: int | None = None,
        extract_batch_size: int = DEFAULT_EXTRACT_BATCH_SIZE,
        processor: str = "pro-fast",
        chat_model: str = "core",
        previous_interaction_id: str | None = None,
        allow_perplexity_fallback: bool = False,
        manuscript_context: dict[str, Any] | None = None,
        cli_timeout: int = 300,
        research_timeout: int = 3600,
    ):
        """Initialize routing and retrieval options.

        ``parallel`` remains a compatibility alias for the explicit ``research``
        backend. A bare query always selects ``search``.
        """
        backend_aliases = {"parallel": "research"}
        normalized_backend = backend_aliases.get(force_backend or "", force_backend)
        if normalized_backend not in {
            None,
            "search",
            "research",
            "chat",
            "perplexity",
        }:
            raise ValueError(
                "force_backend must be one of: search, research, parallel, chat, "
                "perplexity"
            )
        if chat_model not in {"speed", "lite", "base", "core"}:
            raise ValueError("chat_model must be one of: speed, lite, base, core")
        if target_references < 1:
            raise ValueError("target_references must be at least 1")
        if max_results < 1:
            raise ValueError("max_results must be at least 1")
        if not 1 <= extract_batch_size <= 20:
            raise ValueError("extract_batch_size must be between 1 and 20")
        if search_mode not in {"turbo", "fast", "basic", "advanced"}:
            raise ValueError("search_mode must be one of: turbo, fast, basic, advanced")

        self.force_backend = normalized_backend
        self.requested_backend = force_backend
        self.academic = academic
        self.target_references = target_references
        self.search_mode = search_mode
        self.max_results = max_results
        self.include_domains = include_domains or []
        self.after_date = after_date
        self.extract_limit = (
            target_references if extract_limit is None else max(0, extract_limit)
        )
        self.extract_batch_size = extract_batch_size
        self.processor = processor
        self.chat_model = chat_model
        self.previous_interaction_id = previous_interaction_id
        self.allow_perplexity_fallback = allow_perplexity_fallback
        self.manuscript_context = manuscript_context or {}
        self.cli_timeout = cli_timeout
        self.research_timeout = research_timeout

        self.parallel_available = shutil.which("parallel-cli") is not None
        self.chat_available = bool(os.getenv("PARALLEL_API_KEY"))
        self.perplexity_available = bool(os.getenv("OPENROUTER_API_KEY"))

        if self.force_backend in {"search", "research"} and not self.parallel_available:
            raise ValueError(
                "parallel-cli is required for the selected Parallel backend. "
                "Install the pinned CLI version documented in SKILL.md."
            )
        if self.force_backend == "chat" and not self.chat_available:
            raise ValueError(
                "PARALLEL_API_KEY is required when forcing the Parallel Chat backend."
            )
        if self.force_backend == "perplexity" and not self.perplexity_available:
            raise ValueError(
                "OPENROUTER_API_KEY is required when forcing the Perplexity backend."
            )
        if (
            not self.parallel_available
            and not self.chat_available
            and not self.perplexity_available
        ):
            raise ValueError(
                "No backend is available. Install/authenticate parallel-cli or set "
                "PARALLEL_API_KEY for explicit Chat use, or OPENROUTER_API_KEY for "
                "the optional Perplexity backend."
            )

    def _select_backend(self, query: str) -> str:
        """Select Search by default; provider changes require explicit intent."""
        del query
        if self.force_backend:
            return self.force_backend
        # A stored OpenRouter key is not consent to change the destination.
        # Missing CLI errors follow the same opt-in fallback path as API failures.
        return "search"

    def _is_academic_query(self, query: str) -> bool:
        if self.academic is not None:
            return self.academic
        lowered = query.lower()
        return any(keyword in lowered for keyword in ACADEMIC_KEYWORDS)

    def _query_with_context(self, query: str) -> str:
        if not self.manuscript_context:
            return query
        context_lines = [
            f"{key.replace('_', ' ').title()}: {value}"
            for key, value in self.manuscript_context.items()
            if value not in (None, "", [], {})
        ]
        if not context_lines:
            return query
        return f"{query}\n\nManuscript context:\n" + "\n".join(context_lines)

    def _run_parallel_cli(
        self, args: list[str], *, timeout: int | None = None
    ) -> dict[str, Any]:
        """Run the pinned CLI without shell interpolation and parse JSON."""
        command = ["parallel-cli", *args]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout or self.cli_timeout,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("parallel-cli was not found on PATH.") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"parallel-cli timed out after {timeout or self.cli_timeout} seconds."
            ) from exc

        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(
                f"parallel-cli exited with status {completed.returncode}: {detail}"
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "parallel-cli returned non-JSON output despite --json."
            ) from exc
        if not isinstance(payload, dict):
            raise RuntimeError("parallel-cli returned a non-object JSON response.")
        if payload.get("type") == "error" or payload.get("error"):
            raise RuntimeError(f"parallel-cli returned an error: {payload.get('error')}")
        return payload

    @staticmethod
    def _usage_counts(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for payload in payloads:
            for item in payload.get("usage") or []:
                name = str(item.get("name") or "unknown")
                counts[name] = counts.get(name, 0) + int(item.get("count") or 0)
        return [{"name": name, "count": count} for name, count in sorted(counts.items())]

    def _search_once(
        self,
        *,
        objective: str,
        keyword_queries: tuple[str, ...],
        facet: str,
        academic_domains: bool,
        mode: str,
        session_id: str | None = None,
        apply_after_date: bool = True,
    ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        args = [
            "search",
            objective,
            "--mode",
            mode,
            "--max-results",
            str(self.max_results),
            "--excerpt-max-chars-total",
            str(max(27000, self.max_results * 2500)),
            "--json",
        ]
        for query in keyword_queries:
            args.extend(["-q", query])
        domains = list(self.include_domains)
        if academic_domains:
            domains.extend(ACADEMIC_DOMAINS)
        domains = list(dict.fromkeys(domains))
        if domains:
            args.extend(["--include-domains", ",".join(domains)])
        if self.after_date and apply_after_date:
            args.extend(["--after-date", self.after_date])
        if session_id:
            args.extend(["--session-id", session_id])

        started = datetime.now(timezone.utc).isoformat()
        payload = self._run_parallel_cli(args)
        raw_results = payload.get("results") or []
        results: list[dict[str, Any]] = []
        for raw_result in raw_results:
            source = dict(raw_result)
            source["facets"] = sorted(
                set(source.get("facets") or []) | {facet}
            )
            source["url"] = canonicalize_url(str(source.get("url") or ""))
            results.append(source)
        ledger = {
            "capability": "search",
            "facet": facet,
            "objective": objective,
            "keyword_queries": list(keyword_queries),
            "mode": mode,
            "domains": domains,
            "after_date": self.after_date if apply_after_date else None,
            "timestamp": started,
            "result_count": len(results),
            "search_id": payload.get("search_id"),
            "session_id": payload.get("session_id"),
            # V1 Search has no top-level status field.
            "status": "ok",
            "warnings": payload.get("warnings") or [],
        }
        return payload, ledger, results

    def _rank_sources_for_extraction(
        self, sources: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        ranked: list[tuple[tuple[int, int, int, int], dict[str, Any]]] = []
        for index, source in enumerate(sources, start=1):
            reference = normalize_reference(source, index)
            ranked.append((reference_score(reference), source))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [source for _, source in ranked]

    def _extract_sources(
        self,
        sources: list[dict[str, Any]],
        search_ledger: list[dict[str, Any]],
        session_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if self.extract_limit == 0:
            return sources, []
        candidates = [
            source
            for source in self._rank_sources_for_extraction(sources)
            if source.get("url")
        ][: self.extract_limit]
        extraction_payloads: list[dict[str, Any]] = []
        extracted_sources: list[dict[str, Any]] = []
        objective = (
            "Extract only source-supported bibliographic and study evidence: authors, "
            "year, journal or venue, DOI/PMID, publication type, study design, population "
            "or system, sample size, methods, intervention/exposure, comparator, outcomes, "
            "quantitative findings, uncertainty, limitations, correction/retraction status, "
            "and conclusions. Preserve exact wording for evidence excerpts."
        )
        for offset in range(0, len(candidates), self.extract_batch_size):
            batch = candidates[offset : offset + self.extract_batch_size]
            urls = [str(source["url"]) for source in batch]
            args = [
                "extract",
                *urls,
                "--objective",
                objective,
                "--excerpt-max-chars-per-result",
                "6000",
                "--excerpt-max-chars-total",
                str(max(12000, len(urls) * 6000)),
                "--json",
            ]
            if session_id:
                args.extend(["--session-id", session_id])
            timestamp = datetime.now(timezone.utc).isoformat()
            try:
                payload = self._run_parallel_cli(args)
            except RuntimeError as exc:
                search_ledger.append(
                    {
                        "capability": "extract",
                        "timestamp": timestamp,
                        "urls": urls,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                continue
            extraction_payloads.append(payload)
            session_id = session_id or payload.get("session_id")
            batch_results = payload.get("results") or []
            retrieved_urls: set[str] = set()
            for raw_result in batch_results:
                source = dict(raw_result)
                source["url"] = canonicalize_url(str(source.get("url") or ""))
                excerpts = [
                    excerpt
                    for excerpt in source.get("excerpts") or []
                    if isinstance(excerpt, str) and excerpt.strip()
                ]
                source["extraction_excerpts"] = excerpts
                source["extracted"] = bool(source["url"] and excerpts)
                if source["extracted"]:
                    retrieved_urls.add(source["url"])
                source["facets"] = ["extracted-evidence"]
                extracted_sources.append(source)
            unresolved_urls = [
                url for url in urls if canonicalize_url(url) not in retrieved_urls
            ]
            search_ledger.append(
                {
                    "capability": "extract",
                    "timestamp": timestamp,
                    "urls": urls,
                    "result_count": len(batch_results),
                    "extract_id": payload.get("extract_id"),
                    "session_id": payload.get("session_id"),
                    "status": (
                        "partial" if unresolved_urls or payload.get("errors") else "ok"
                    ),
                    "errors": payload.get("errors") or [],
                    "unresolved_urls": unresolved_urls,
                    "warnings": payload.get("warnings") or [],
                }
            )
        return deduplicate_sources([*sources, *extracted_sources]), extraction_payloads

    def _parallel_search(self, query: str) -> dict[str, Any]:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        academic = self._is_academic_query(query)
        contextual_query = self._query_with_context(query)
        search_payloads: list[dict[str, Any]] = []
        ledger: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        session_id: str | None = None
        errors: list[str] = []

        if academic:
            mode = "advanced"
            for facet, instruction, keywords in ACADEMIC_FACETS:
                objective = f"{instruction}\n\nTopic: {contextual_query}"
                keyword_queries = tuple(f"{query} {keyword}" for keyword in keywords)
                try:
                    payload, entry, facet_sources = self._search_once(
                        objective=objective,
                        keyword_queries=keyword_queries,
                        facet=facet,
                        academic_domains=True,
                        mode=mode,
                        session_id=session_id,
                        apply_after_date=facet != "seminal",
                    )
                except RuntimeError as exc:
                    errors.append(f"{facet}: {exc}")
                    ledger.append(
                        {
                            "capability": "search",
                            "facet": facet,
                            "objective": objective,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "status": "error",
                            "error": str(exc),
                        }
                    )
                    continue
                search_payloads.append(payload)
                ledger.append(entry)
                sources.extend(facet_sources)
                session_id = session_id or payload.get("session_id")

            if len(deduplicate_sources(sources)) < self.target_references:
                objective = (
                    "Find additional authoritative sources that directly address this "
                    "manuscript topic, including important evidence missed by scholarly "
                    "domain filters. Prefer sources with stable links and bibliographic "
                    f"metadata.\n\nTopic: {contextual_query}"
                )
                try:
                    payload, entry, general_sources = self._search_once(
                        objective=objective,
                        keyword_queries=(query,),
                        facet="general-companion",
                        academic_domains=False,
                        mode=mode,
                        session_id=session_id,
                    )
                    search_payloads.append(payload)
                    ledger.append(entry)
                    sources.extend(general_sources)
                except RuntimeError as exc:
                    errors.append(f"general-companion: {exc}")
                    ledger.append(
                        {
                            "capability": "search",
                            "facet": "general-companion",
                            "objective": objective,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "status": "error",
                            "error": str(exc),
                        }
                    )
        else:
            objective = (
                "Find current, authoritative, directly relevant information for this "
                f"research question:\n\n{contextual_query}"
            )
            payload, entry, sources = self._search_once(
                objective=objective,
                keyword_queries=(query,),
                facet="general",
                academic_domains=False,
                mode=self.search_mode,
            )
            search_payloads.append(payload)
            ledger.append(entry)

        sources = deduplicate_sources(sources)
        if not sources:
            detail = "; ".join(errors) if errors else "No results returned."
            raise RuntimeError(f"Parallel Search produced no usable sources. {detail}")

        extraction_payloads: list[dict[str, Any]] = []
        if academic:
            sources, extraction_payloads = self._extract_sources(sources, ledger, session_id)

        packet = build_manuscript_packet(
            query=query,
            sources=sources,
            search_ledger=ledger,
            target_references=self.target_references if academic else len(sources),
            manuscript_context=self.manuscript_context,
        )
        packet["raw_service_responses"] = {
            "search": search_payloads,
            "extract": extraction_payloads,
        }
        if errors:
            packet["warnings"].append(
                "Some bounded search passes failed: " + "; ".join(errors)
            )
        if any(
            entry.get("status") in {"partial", "error"}
            for entry in ledger
            if entry.get("capability") == "extract"
        ):
            packet["warnings"].append(
                "Some Extract URLs were unavailable or returned no excerpts; inspect "
                "errors and unresolved_urls in the search ledger. Redirected URLs may "
                "also require manual reconciliation."
            )
        response = packet_markdown(packet)
        references = packet["references"]
        citations = [
            {
                "type": "source",
                "title": reference["title"],
                "url": reference["url"],
                "date": reference["year"],
                "doi": reference["doi"],
                "pmid": reference["pmid"],
            }
            for reference in references
            if reference.get("url")
        ]
        normalized_sources = [
            {
                "title": reference["title"],
                "url": reference["url"],
                "publish_date": reference["year"],
                "excerpts": reference["supporting_excerpts"],
            }
            for reference in references
        ]
        usage = self._usage_counts([*search_payloads, *extraction_payloads])
        return {
            "success": True,
            "query": query,
            "response": response,
            "citations": citations,
            "sources": normalized_sources,
            "timestamp": timestamp,
            "backend": "search",
            "model": f"parallel-search/{'advanced' if academic else self.search_mode}",
            "usage": usage,
            "academic": academic,
            "references": references,
            "search_ledger": ledger,
            "packet": packet,
        }

    @staticmethod
    def _find_report_text(payload: Any) -> str:
        """Read the CLI text-output contract without mistaking basis for a report."""
        output = payload.get("output", {}) if isinstance(payload, dict) else {}
        content = output.get("content") if isinstance(output, dict) else None
        return content if isinstance(content, str) else ""

    @staticmethod
    def _sources_from_payload(payload: Any) -> list[dict[str, str]]:
        sources: list[dict[str, str]] = []

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                url = value.get("url")
                if isinstance(url, str) and url.startswith(("http://", "https://")):
                    sources.append(
                        {
                            "type": "source",
                            "url": canonicalize_url(url),
                            "title": str(value.get("title") or ""),
                        }
                    )
                for nested in value.values():
                    walk(nested)
            elif isinstance(value, list):
                for nested in value:
                    walk(nested)

        walk(payload)
        unique: dict[str, dict[str, str]] = {}
        for source in sources:
            unique.setdefault(source["url"], source)
        return list(unique.values())

    def _parallel_research(self, query: str) -> dict[str, Any]:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        research_query = (
            f"{self.PARALLEL_SYSTEM_PROMPT}\n\nResearch topic:\n"
            f"{self._query_with_context(query)}"
        )
        if len(research_query) > 15000:
            raise ValueError(
                "Research query plus context and instructions exceeds the CLI's "
                "15,000-character limit; shorten it to avoid silent truncation."
            )
        with tempfile.TemporaryDirectory(prefix="research-lookup-") as temp_dir:
            output_base = Path(temp_dir) / "report"
            args = [
                "research",
                "run",
                research_query,
                "--processor",
                self.processor,
                "--text",
                "--text-description",
                (
                    "Produce a manuscript-research report with complete inline citations, "
                    "quantitative evidence, methods, limitations, conflicts, and gaps."
                ),
                "--timeout",
                str(self.research_timeout),
                "--json",
                "-o",
                str(output_base),
            ]
            if self.previous_interaction_id:
                args.extend(
                    ["--previous-interaction-id", self.previous_interaction_id]
                )
            payload = self._run_parallel_cli(args, timeout=self.research_timeout + 60)
            if payload.get("status") != "completed":
                raise RuntimeError(
                    f"Parallel Research is not completed: {payload.get('status')} "
                    f"(run_id={payload.get('run_id')})."
                )
            markdown_path = output_base.with_suffix(".md")
            content = (
                markdown_path.read_text(encoding="utf-8")
                if markdown_path.exists()
                else self._find_report_text(payload)
            )
        if not content.strip():
            raise RuntimeError("Parallel Research returned no text report.")
        sources = self._sources_from_payload(
            (payload.get("output") or {}).get("basis") or []
        )
        text_citations = self._extract_citations_from_text(content)
        return {
            "success": True,
            "query": query,
            "response": content,
            "citations": [*sources, *text_citations],
            "sources": sources,
            "timestamp": timestamp,
            "backend": "research",
            "model": f"parallel-research/{self.processor}",
            "usage": payload.get("usage") or [],
            "run_id": payload.get("run_id") or payload.get("id"),
            "interaction_id": payload.get("interaction_id"),
            "raw_response": payload,
        }

    def _parallel_chat(self, query: str) -> dict[str, Any]:
        """Run the explicit OpenAI-compatible Parallel Chat backend."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        api_key = os.getenv("PARALLEL_API_KEY")
        if not api_key:
            raise RuntimeError(
                "PARALLEL_API_KEY is required for the explicit Chat backend."
            )
        try:
            import requests
        except ImportError as exc:
            raise ImportError(
                "The optional Parallel Chat backend requires requests."
            ) from exc

        payload = {
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": self.PARALLEL_SYSTEM_PROMPT},
                {"role": "user", "content": self._query_with_context(query)},
            ],
            "stream": False,
        }
        response = requests.post(
            "https://api.parallel.ai/v1beta/chat/completions",
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.research_timeout,
        )
        response.raise_for_status()
        response_payload = response.json()
        choices = response_payload.get("choices") or []
        if not choices:
            raise RuntimeError("No response choices received from Parallel Chat.")
        content = str(choices[0].get("message", {}).get("content") or "")
        basis_sources = self._sources_from_payload(
            response_payload.get("basis") or []
        )
        text_citations = self._extract_citations_from_text(content)
        return {
            "success": True,
            "query": query,
            "response": content,
            "citations": [*basis_sources, *text_citations],
            "sources": basis_sources,
            "timestamp": timestamp,
            "backend": "chat",
            "model": f"parallel-chat/{self.chat_model}",
            "usage": response_payload.get("usage") or {},
            "basis": response_payload.get("basis"),
            "raw_response": response_payload,
        }

    def _perplexity_lookup(self, query: str) -> dict[str, Any]:
        """Run the preserved optional academic backend through OpenRouter."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set.")
        try:
            import requests
        except ImportError as exc:
            raise ImportError(
                "The optional Perplexity backend requires requests."
            ) from exc

        model = "perplexity/sonar-pro-search"
        current_year = datetime.now().year
        prompt = (
            "Find high-quality academic evidence for manuscript preparation. Return "
            "complete citations with DOI/PMID where available, quantitative findings, "
            "methods, limitations, contradictory evidence, and research gaps. Prioritize "
            f"peer-reviewed literature and clearly label preprints. Current year: "
            f"{current_year}.\n\nQuery: {self._query_with_context(query)}"
        )
        data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an academic research assistant. Never invent references "
                        "or bibliographic metadata."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 8000,
            "temperature": 0.1,
            "web_search_options": {"search_context_size": "high"},
        }
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=data,
            timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("No response choices received from Perplexity.")
        content = str(choices[0].get("message", {}).get("content") or "")
        api_citations = self._extract_api_citations(payload, choices[0])
        text_citations = self._extract_citations_from_text(content)
        return {
            "success": True,
            "query": query,
            "response": content,
            "citations": [*api_citations, *text_citations],
            "sources": api_citations,
            "timestamp": timestamp,
            "backend": "perplexity",
            "model": model,
            "usage": payload.get("usage") or {},
            "raw_response": payload,
        }

    @staticmethod
    def _extract_api_citations(
        response: dict[str, Any], choice: dict[str, Any]
    ) -> list[dict[str, str]]:
        citations: list[dict[str, str]] = []
        for annotation in choice.get("message", {}).get("annotations") or []:
            if annotation.get("type") != "url_citation":
                continue
            item = annotation.get("url_citation") or {}
            citations.append(
                {
                    "type": "source",
                    "url": canonicalize_url(str(item.get("url") or "")),
                    "title": str(item.get("title") or ""),
                    "snippet": str(item.get("content") or ""),
                    "date": "",
                }
            )
        search_results = (
            response.get("search_results")
            or choice.get("search_results")
            or choice.get("message", {}).get("search_results")
            or []
        )
        for result in search_results:
            citations.append(
                {
                    "type": "source",
                    "title": str(result.get("title") or ""),
                    "url": canonicalize_url(str(result.get("url") or "")),
                    "date": str(result.get("date") or ""),
                    "snippet": str(result.get("snippet") or ""),
                }
            )
        legacy = (
            response.get("citations")
            or choice.get("citations")
            or choice.get("message", {}).get("citations")
            or []
        )
        for citation in legacy:
            if isinstance(citation, str):
                citations.append(
                    {
                        "type": "source",
                        "url": canonicalize_url(citation),
                        "title": "",
                        "date": "",
                    }
                )
            elif isinstance(citation, dict):
                citations.append(
                    {
                        "type": "source",
                        "url": canonicalize_url(str(citation.get("url") or "")),
                        "title": str(citation.get("title") or ""),
                        "date": str(citation.get("date") or ""),
                    }
                )
        unique: dict[str, dict[str, str]] = {}
        for citation in citations:
            if citation["url"]:
                unique.setdefault(citation["url"], citation)
        return list(unique.values())

    @staticmethod
    def _extract_citations_from_text(text: str) -> list[dict[str, str]]:
        citations: list[dict[str, str]] = []
        seen: set[str] = set()
        doi_pattern = re.compile(
            r"(?:doi[:\s]*|https?://(?:dx\.)?doi\.org/)"
            r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",
            re.IGNORECASE,
        )
        for doi in doi_pattern.findall(text or ""):
            clean_doi = doi.rstrip(".,;:)]}").lower()
            url = f"https://doi.org/{clean_doi}"
            if url not in seen:
                seen.add(url)
                citations.append(
                    {"type": "doi", "doi": clean_doi, "url": url, "title": ""}
                )
        url_pattern = re.compile(r"https?://[^\s)\]>,\"']+", re.IGNORECASE)
        for url in url_pattern.findall(text or ""):
            clean_url = canonicalize_url(url.rstrip(".,;:"))
            if clean_url and clean_url not in seen:
                seen.add(clean_url)
                citations.append(
                    {"type": "url", "url": clean_url, "title": ""}
                )
        return citations

    @staticmethod
    def _failure_result(query: str, backend: str, exc: Exception) -> dict[str, Any]:
        return {
            "success": False,
            "query": query,
            "error": str(exc),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "backend": backend,
            "model": "unknown",
        }

    def lookup(self, query: str) -> dict[str, Any]:
        """Perform one lookup while isolating errors in the result envelope."""
        backend = self._select_backend(query)
        print(
            f"[Research] Backend: {backend} | Query: {query[:80]}...",
            file=sys.stderr,
        )
        try:
            if backend == "search":
                return self._parallel_search(query)
            if backend == "research":
                return self._parallel_research(query)
            if backend == "chat":
                return self._parallel_chat(query)
            return self._perplexity_lookup(query)
        except Exception as exc:
            if (
                backend in {"search", "research", "chat"}
                and self.allow_perplexity_fallback
                and self.perplexity_available
            ):
                print(
                    f"[Research] Parallel failed; explicit Perplexity fallback: {exc}",
                    file=sys.stderr,
                )
                try:
                    result = self._perplexity_lookup(query)
                    result["fallback_from"] = backend
                    result["fallback_reason"] = str(exc)
                    return result
                except Exception as fallback_exc:
                    return self._failure_result(
                        query,
                        "perplexity",
                        RuntimeError(
                            f"Parallel failed: {exc}; fallback failed: {fallback_exc}"
                        ),
                    )
            return self._failure_result(query, backend, exc)

    def batch_lookup(
        self, queries: list[str], delay: float = 1.0
    ) -> list[dict[str, Any]]:
        """Perform multiple lookups with preserved per-query error isolation."""
        results: list[dict[str, Any]] = []
        for index, query in enumerate(queries):
            if index and delay > 0:
                time.sleep(delay)
            result = self.lookup(query)
            results.append(result)
            print(
                f"[Research] Completed query {index + 1}/{len(queries)}: "
                f"{query[:50]}...",
                file=sys.stderr,
            )
        return results


def _load_context(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("The manuscript context file must contain a JSON object.")
    return payload


def _split_domains(values: list[str] | None) -> list[str]:
    domains: list[str] = []
    for value in values or []:
        domains.extend(part.strip() for part in value.split(",") if part.strip())
    return list(dict.fromkeys(domains))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "research"


def _render_human_result(result: dict[str, Any], index: int) -> str:
    if not result.get("success"):
        return f"\nError in query {index}: {result.get('error', 'Unknown error')}"
    lines = [
        "",
        "=" * 80,
        f"Query {index}: {result['query']}",
        f"Timestamp: {result['timestamp']}",
        f"Backend: {result.get('backend', 'unknown')} | "
        f"Model: {result.get('model', 'unknown')}",
        "=" * 80,
        str(result.get("response") or ""),
    ]
    sources = result.get("sources") or []
    if sources and result.get("backend") != "search":
        lines.append(f"\nSources ({len(sources)}):")
        for source_index, source in enumerate(sources, start=1):
            title = source.get("title") or "Untitled"
            url = source.get("url") or ""
            lines.append(f"  [{source_index}] {title}")
            if url:
                lines.append(f"      {url}")
    if result.get("usage"):
        lines.append(f"\nUsage: {result['usage']}")
    if result.get("artifacts"):
        lines.append(f"\nArtifacts: {result['artifacts']}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Parallel-first research lookup and manuscript evidence compiler"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Academic manuscript packet (60 verified references by default)
  python research_lookup.py "CRISPR off-target effects" --academic \
    --packet-dir sources/crispr

  # Fast bounded web lookup
  python research_lookup.py "latest NIST AI guidance" --no-academic

  # Explicit deep research (legacy 'parallel' alias remains accepted)
  python research_lookup.py "comprehensive quantum error correction review" \
    --force-backend research --processor pro

  # Explicit OpenAI-compatible Parallel Chat (never selected by default)
  python research_lookup.py "synthesize the evidence" \
    --force-backend chat --chat-model core

  # Optional explicit Perplexity fallback
  python research_lookup.py "find papers on topic" --force-backend perplexity
        """,
    )
    parser.add_argument("query", nargs="?", help="Research query to look up")
    parser.add_argument("--batch", nargs="+", help="Run multiple queries")
    parser.add_argument(
        "--force-backend",
        choices=["search", "research", "parallel", "chat", "perplexity"],
        help=(
            "'parallel' is retained as a compatibility alias for 'research'; "
            "'chat' is explicit and never selected by default"
        ),
    )
    parser.add_argument(
        "--academic",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Force or disable the multi-pass academic retrieval strategy",
    )
    parser.add_argument(
        "--target-references",
        type=int,
        default=DEFAULT_TARGET_REFERENCES,
        help="Target verified references for academic retrieval (default: 60)",
    )
    parser.add_argument(
        "--search-mode",
        choices=["turbo", "fast", "basic", "advanced"],
        default="basic",
        help="Mode for non-academic Search calls (academic calls use advanced)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=DEFAULT_MAX_RESULTS,
        help="Maximum results requested per bounded Search pass",
    )
    parser.add_argument(
        "--include-domains",
        action="append",
        help="Additional comma-separated domains; may be repeated",
    )
    parser.add_argument("--after-date", help="Search results after YYYY-MM-DD")
    parser.add_argument(
        "--extract-limit",
        type=int,
        help="Maximum academic sources to verify with Extract (default: target)",
    )
    parser.add_argument(
        "--no-extract",
        action="store_true",
        help="Skip Extract verification (reference shortfalls will be reported)",
    )
    parser.add_argument(
        "--processor",
        default="pro-fast",
        help="Parallel Research processor for explicit deep research",
    )
    parser.add_argument(
        "--chat-model",
        choices=["speed", "lite", "base", "core"],
        default="core",
        help="Parallel Chat model for the explicit Chat backend (default: core)",
    )
    parser.add_argument(
        "--previous-interaction-id",
        help="Continue a related Parallel Research interaction",
    )
    parser.add_argument(
        "--fallback-perplexity",
        action="store_true",
        help="Allow Perplexity only if a Parallel call fails",
    )
    parser.add_argument(
        "--context-file",
        help="JSON object with manuscript question, study type, PICO, field, and journal",
    )
    parser.add_argument(
        "--packet-dir",
        help="Write manuscript packet artifacts to this directory",
    )
    parser.add_argument(
        "--batch-delay",
        type=float,
        default=1.0,
        help="Delay between batch queries in seconds",
    )
    parser.add_argument("-o", "--output", help="Write primary output to a file")
    parser.add_argument("--json", action="store_true", help="Output result JSON")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.query and not args.batch:
        parser.print_help()
        return 1
    try:
        context = _load_context(args.context_file)
        research = ResearchLookup(
            force_backend=args.force_backend,
            academic=args.academic,
            target_references=args.target_references,
            search_mode=args.search_mode,
            max_results=args.max_results,
            include_domains=_split_domains(args.include_domains),
            after_date=args.after_date,
            extract_limit=0 if args.no_extract else args.extract_limit,
            processor=args.processor,
            chat_model=args.chat_model,
            previous_interaction_id=args.previous_interaction_id,
            allow_perplexity_fallback=args.fallback_perplexity,
            manuscript_context=context,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    queries = args.batch or [args.query]
    print(f"Running research for {len(queries)} query(s)...", file=sys.stderr)
    results = research.batch_lookup(queries, delay=args.batch_delay)

    if args.packet_dir:
        for index, result in enumerate(results):
            packet = result.get("packet")
            if not packet:
                continue
            destination = Path(args.packet_dir)
            if len(results) > 1:
                destination = destination / f"{index + 1:02d}-{_slug(result['query'])}"
            result["artifacts"] = save_packet(packet, destination)

    if args.json:
        rendered = json.dumps(results, indent=2, ensure_ascii=False, default=str) + "\n"
    else:
        rendered = "\n".join(
            _render_human_result(result, index)
            for index, result in enumerate(results, start=1)
        )
        rendered += "\n"

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if all(result.get("success") for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
