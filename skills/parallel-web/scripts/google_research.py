#!/usr/bin/env python3
"""
Google Deep Research CLI — Vertex-backed replacement for parallel-cli.

Subcommands:
  search    Fast factual lookup via deep-research-preview agent (Vertex)
  research  Comprehensive cited report via deep-research-preview agent (Vertex; max not on Vertex yet)
  poll      Fetch a completed (or interim) report by interaction_id
  extract   Single-URL content fetch (gemini-2.5-flash + url_context via generate_content)

Environment (Vertex AI — matches DendroForge production):
  GOOGLE_GENAI_USE_VERTEXAI=true
  GOOGLE_CLOUD_PROJECT          GCP project ID
  GOOGLE_CLOUD_LOCATION         Default: global
  GOOGLE_APPLICATION_CREDENTIALS  Path to service-account JSON (or use ADC)

Install: uv pip install google-genai
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from typing import Any
from urllib.parse import urlparse

# Agent / model IDs
SEARCH_MODEL = "gemini-2.5-flash"
SEARCH_AGENT = "deep-research-preview-04-2026"  # optional search --deep
RESEARCH_AGENT = "deep-research-preview-04-2026"  # Vertex default (max not on Vertex yet)
RESEARCH_AGENT_MAX = "deep-research-max-preview-04-2026"  # Gemini API only; use --max to try
EXTRACT_MODEL = "gemini-2.5-flash"

DEFAULT_POLL_INTERVAL = 10
DEFAULT_RESEARCH_TIMEOUT = 900   # deep research takes 5-15 min
DEFAULT_EXTRACT_TIMEOUT = 120
DEFAULT_SEARCH_TIMEOUT = 600     # preview agent needs several minutes for search

# Matches [cite: 3, 5, 8, 63] — agent-internal inline citation markers.
_CITE_RE = re.compile(r"\[cite:\s*([\d,\s]+)\]")


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _check_env() -> tuple[str, str]:
    """Validate and return (project, location)."""
    try:
        from google import genai  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "google-genai is not installed. Run: uv pip install google-genai"
        ) from exc

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise SystemExit(
            "GOOGLE_CLOUD_PROJECT is not set.\n"
            "Example: export GOOGLE_CLOUD_PROJECT=your-gcp-project-id"
        )

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and not os.path.isfile(creds_path):
        raise SystemExit(
            f"GOOGLE_APPLICATION_CREDENTIALS points to missing file: {creds_path}"
        )

    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
    return project, location


def _get_agent_client():
    """Client for Vertex Agent Platform (Deep Research managed agents).

    Vertex Deep Research requires enterprise=True, not vertexai=True.
    See: cloud.google.com/gemini-enterprise-agent-platform/agents/use-deep-research
    """
    from google import genai

    project, location = _check_env()
    return genai.Client(enterprise=True, project=project, location=location)


def _get_model_client():
    """Client for standard Vertex generate_content calls (extract, search fallback)."""
    from google import genai

    project, location = _check_env()
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
    return genai.Client(vertexai=True, project=project, location=location)


def _get_client():
    """Alias kept for backward compat — returns agent client."""
    return _get_agent_client()


def _step_text(step: Any) -> str | None:
    """Extract text from a single interaction step."""
    content = getattr(step, "content", None)
    if not content:
        return None
    parts: list[str] = []
    for item in content:
        text = getattr(item, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts) if parts else None


def _strip_planning_json(text: str) -> str:
    """Remove Deep Research planning JSON preamble from stream-collected text.

    The agent emits JSON planning notes (arrays of {title, content} objects)
    before writing the final report. The final report starts after the literal
    string "Generation complete." — strip everything before that marker.

    Falls back to stripping leading ```json ... ``` fenced blocks when the
    marker is absent (e.g. if the stream was captured mid-flight).
    """
    marker = "Generation complete."
    idx = text.find(marker)
    if idx != -1:
        cleaned = text[idx + len(marker):].strip()
        if cleaned:
            return cleaned
    # Fallback: strip one or more leading ```json ... ``` blocks
    cleaned = re.sub(r"^(\s*```json[\s\S]*?```\s*)+", "", text).strip()
    return cleaned if cleaned else text


def _strip_visual_elements(text: str) -> str:
    """Remove <visual_element>...</visual_element> chart-spec blocks.

    Deep Research embeds figure/chart specifications (often a ```json {...}```
    block wrapped in <visual_element> tags) meant for a downstream renderer, not
    for the final prose report.  Strip them so the markdown reads cleanly.
    """
    cleaned = re.sub(r"<visual_element>[\s\S]*?</visual_element>\s*", "", text)
    # Collapse the blank-line gaps the removal can leave behind.
    cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)
    return cleaned.strip()


def _looks_like_final_report(text: str) -> bool:
    """Heuristic: distinguish final markdown report from tool/search JSON."""
    stripped = text.strip()
    if not stripped:
        return False
    head = stripped[:800]
    # google_search tool output dumped as JSON
    if stripped.startswith("[{") and '"query"' in head and '"results"' in head:
        return False
    if stripped.startswith("{") and '"results"' in head and '"snippet"' in head:
        return False
    # planning-only JSON (no report marker, no markdown headings)
    if "Generation complete." not in text and not re.search(r"^#{1,3}\s+\S", text, re.M):
        if re.match(r"^(\s*```json\s*)?\[\s*\{", stripped) and '"title"' in head:
            return False
    if re.search(r"^#{1,3}\s+\S", text, re.M):
        return True
    if "Generation complete." in text:
        return True
    # long prose without leading JSON
    if len(stripped) > 800 and not stripped.lstrip().startswith(("[", "{")):
        return True
    return False


def _score_report_candidate(text: str) -> int:
    """Rank text chunks; prefer final markdown reports over tool JSON."""
    cleaned = _strip_planning_json(text.strip())
    if not cleaned:
        return -1
    score = min(len(cleaned) // 200, 40)
    if _looks_like_final_report(cleaned):
        score += 200
    if re.search(r"^#{1,3}\s+\S", cleaned, re.M):
        score += 80
    if "Generation complete." in text:
        score += 60
    if cleaned.lstrip().startswith(("[{", "{")) and '"query"' in cleaned[:500]:
        score -= 300
    if '"snippet"' in cleaned[:1000]:
        score -= 200
    return score


def _truncate_snippet(text: str, max_len: int = 500) -> str:
    cleaned = re.sub(r"\n{3,}", "\n\n", text.strip())
    if len(cleaned) <= max_len:
        return cleaned
    cut = cleaned[:max_len].rsplit(" ", 1)[0]
    return cut + "…"


def _parse_search_json_blocks(text: str) -> list[dict[str, Any]] | None:
    """Return google_search tool JSON blocks if *text* contains them."""
    stripped = text.strip()
    if not stripped.startswith("["):
        return None
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list) or not data:
        return None
    if not all(isinstance(item, dict) and "query" in item for item in data):
        return None
    return data


def _format_search_json_notes(blocks: list[dict[str, Any]], *, status: str | None = None) -> str:
    """Render google_search tool JSON as readable interim markdown."""
    lines = ["# Interim Search Notes\n"]
    if status:
        lines.append(f"> **Status:** `{status}` — final Deep Research report not available yet.\n")
    else:
        lines.append("> Deep Research job still running — raw google_search results below.\n")

    for i, block in enumerate(blocks, 1):
        query = block.get("query", "")
        lines.append(f"\n## Search {i}\n\n**Query:** {query}\n")
        for j, result in enumerate(block.get("results") or [], 1):
            url = result.get("url") or ""
            title = (result.get("source_title") or "Untitled").replace("\n", " — ")
            snippet = _truncate_snippet(result.get("snippet") or "")
            lines.append(f"\n### {j}. {title}\n")
            if url:
                host = urlparse(url).netloc or url
                lines.append(f"- **URL:** [{host}]({url})")
            if snippet:
                lines.append(f"\n{snippet}\n")
    return "\n".join(lines)


def _find_search_json_in_interaction(interaction: Any) -> list[dict[str, Any]] | None:
    """Collect google_search JSON from any interaction step."""
    for step in getattr(interaction, "steps", None) or []:
        text = _step_text(step)
        if not text:
            continue
        blocks = _parse_search_json_blocks(text.strip())
        if blocks:
            return blocks
    return None


def _interaction_to_report(
    interaction: Any,
    *,
    allow_interim: bool = False,
) -> tuple[str, list[tuple[str, str]], str | None]:
    """Extract report body, sources, and status from an interaction."""
    status = getattr(interaction, "status", None)
    raw_body = _extract_body_text(interaction)
    body, sources = _rewrite_body_citations(raw_body or "", interaction)

    if body and _looks_like_final_report(body):
        return body, sources, status

    if status == "completed" and body:
        return body, sources, status

    if allow_interim:
        blocks = _find_search_json_in_interaction(interaction)
        if blocks is None and body:
            blocks = _parse_search_json_blocks(body)
        if blocks:
            return _format_search_json_notes(blocks, status=status), sources, status

    interaction_id = getattr(interaction, "id", None) or getattr(interaction, "name", "?")
    if status != "completed":
        raise SystemExit(
            f"Interaction {interaction_id} status={status}; final report not ready.\n"
            f"Wait and retry: python3 google_research.py poll {interaction_id} -o report.md\n"
            f"For interim search notes: add --allow-interim"
        )
    raise SystemExit(f"No report text found (interaction_id={interaction_id}, status={status})")


def _extract_body_text(interaction: Any) -> str:
    """Assemble the final report text from a completed interaction.

    Deep Research streams the final report as several sequential
    ModelOutputStep chunks (title chunk, then continuation chunks) and *also*
    keeps one or more earlier self-contained drafts among the steps.  Picking
    the single largest step (old behaviour) can return a stale draft that still
    contains <visual_element> specs and carries no citation annotations.

    Strategy: keep every text chunk that is not raw google_search tool JSON.
    A report may arrive as one self-contained chunk (an H1-title draft) or be
    streamed across several trailing chunks (title chunk + continuations).  We
    build both kinds of candidate — each standalone H1 chunk, plus the run from
    the last H1 chunk through the end — strip planning/visual noise from each,
    and keep the longest.  That picks the most complete report whether it was
    emitted whole or in pieces, and drops shorter earlier drafts.  Fall back to
    the best-scoring single chunk when no H1 chunk exists (e.g. the fast search
    agent, whose answer is short prose without a title).
    """
    chunks: list[str] = []  # raw text, order preserved
    for step in getattr(interaction, "steps", None) or []:
        text = _step_text(step)
        if not text or not text.strip():
            continue
        if _parse_search_json_blocks(text.strip()):
            continue  # skip google_search tool-call dumps
        chunks.append(text)

    for attr in ("output", "result", "response"):
        val = getattr(interaction, attr, None)
        if isinstance(val, str) and val.strip():
            chunks.append(val)

    if not chunks:
        return ""

    candidates: list[str] = []
    last_h1: int | None = None
    for pos, text in enumerate(chunks):
        if re.match(r"^#\s+\S", text.strip()):
            candidates.append(text)          # standalone H1 draft
            last_h1 = pos
    if last_h1 is not None:
        candidates.append("".join(chunks[last_h1:]))  # trailing streamed run

    if candidates:
        cleaned = [
            _strip_visual_elements(_strip_planning_json(c)).strip()
            for c in candidates
        ]
        return max(cleaned, key=len)

    best = max((c.strip() for c in chunks), key=_score_report_candidate)
    if _score_report_candidate(best) < 0:
        return ""
    return _strip_visual_elements(_strip_planning_json(best)).strip()


def _urls_from_text(text: str) -> list[str]:
    """Pull http(s) URLs from markdown links and bare URLs."""
    urls: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"https?://[^\s\)\]>\"']+", text):
        url = match.group(0).rstrip(".,;:")
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _dedup_sources(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Deduplicate (label, url) pairs, preserving first-seen order.

    Deep Research emits a distinct grounding-redirect URL per citation even when
    two citations resolve to the same source, so we key on the human-readable
    title when present (falling back to the URL) to collapse duplicates.
    """
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for label, url in pairs:
        if not url:
            continue
        key = (label.strip() or url).strip()
        if key in seen:
            continue
        seen.add(key)
        out.append((label.strip(), url.strip()))
    return out


def _collect_url_citations(interaction: Any) -> list[tuple[str, str]]:
    """Collect structured URLCitation annotations (Deep Research grounding).

    Each final-report TextContent carries `.annotations`, a list of
    URLCitation(url, title, start_index, end_index).  These are the *actually
    cited* sources (not every search result the agent looked at), so they are
    far more precise than harvesting URLs from raw google_search JSON.
    """
    pairs: list[tuple[str, str]] = []
    for step in getattr(interaction, "steps", None) or []:
        for item in getattr(step, "content", None) or []:
            for ann in getattr(item, "annotations", None) or []:
                url = getattr(ann, "url", None)
                if not isinstance(url, str) or not url.startswith("http"):
                    continue
                title = getattr(ann, "title", None) or ""
                pairs.append((title, url))
    return pairs


def _rewrite_body_citations(
    raw_body: str,
    interaction: Any,
) -> tuple[str, list[tuple[str, str]]]:
    """Replace [cite: N, M, ...] markers with [[1]](url)[[2]](url) inline links.

    Replicates the Gemini web UI citation model:
      1. Collect URLCitation annotations that have real start/end offsets.
      2. Group annotations by span, sort spans in document order.
      3. Align span groups 1:1 with [cite: ...] markers in the body (document
         order).  Empirically these match 93/93 for completed Deep Research runs.
      4. Assign sequential source numbers in first-appearance order, dedup by
         title so the same source cited twice keeps the same number.
      5. Replace each [cite: a, b, c] with [[1]](url_1)[[2]](url_2)[[3]](url_3).
      6. Return (rewritten_body, ordered_sources) where sources[i-1] is the
         source referenced by [[i]] inline — identical to Gemini web behaviour.

    Falls back to (raw_body, deduped_annotation_list) when:
      - No annotations with real offsets exist (fast-search / older responses).
      - Annotation span count != [cite:] marker count (structural mismatch).
      - Fewer than 80% of span/marker pairs are size-consistent.
    """
    # Step 1: collect annotations that carry real document offsets.
    real_anns: list[Any] = []
    for step in getattr(interaction, "steps", None) or []:
        for item in getattr(step, "content", None) or []:
            for ann in getattr(item, "annotations", None) or []:
                if getattr(ann, "start_index", None) is not None:
                    url = getattr(ann, "url", None)
                    if isinstance(url, str) and url.startswith("http"):
                        real_anns.append(ann)

    if not real_anns:
        fallback = _collect_url_citations(interaction)
        return raw_body, (
            _dedup_sources(fallback) if fallback
            else [("", u) for u in _urls_from_text(raw_body)]
        )

    # Step 2: group by (start_index, end_index), preserve in-list order within group.
    groups: dict[tuple[int, int], list[Any]] = {}
    span_order: list[tuple[int, int]] = []
    for a in real_anns:
        key = (int(a.start_index), int(a.end_index))
        if key not in groups:
            groups[key] = []
            span_order.append(key)
        groups[key].append(a)
    span_order.sort()

    # Step 3: align with [cite: ...] markers.
    markers = list(_CITE_RE.finditer(raw_body))

    if len(span_order) != len(markers):
        _eprint(
            f"[citations] {len(span_order)} annotation spans vs {len(markers)} "
            "cite markers — falling back to deduped sources"
        )
        fallback = [(getattr(a, "title", None) or "", getattr(a, "url", "")) for a in real_anns]
        return raw_body, _dedup_sources(fallback)

    # Check size-consistency: group size should equal number count in marker.
    size_ok = sum(
        1 for i, span in enumerate(span_order)
        if len(groups[span]) == len(re.findall(r"\d+", markers[i].group(1)))
    )
    if size_ok < len(markers) * 0.8:
        _eprint(
            f"[citations] only {size_ok}/{len(markers)} size-consistent pairs "
            "— falling back to deduped sources"
        )
        fallback = [(getattr(a, "title", None) or "", getattr(a, "url", "")) for a in real_anns]
        return raw_body, _dedup_sources(fallback)

    # Step 4: assign sequential source numbers, dedup by title.
    key_to_num: dict[str, int] = {}
    num_to_entry: dict[int, tuple[str, str]] = {}

    def _src_key(a: Any) -> str:
        t = (getattr(a, "title", None) or "").strip()
        return t or (getattr(a, "url", None) or "")

    def _assign(a: Any) -> int:
        k = _src_key(a)
        if k not in key_to_num:
            n = len(key_to_num) + 1
            key_to_num[k] = n
            title = (getattr(a, "title", None) or "").replace("\n", " — ").strip()
            url = getattr(a, "url", None) or ""
            num_to_entry[n] = (title, url)
        return key_to_num[k]

    # Step 5: rewrite body.
    out_parts: list[str] = []
    last = 0
    for i, m in enumerate(markers):
        grp = groups[span_order[i]]
        nums_seen: list[int] = []
        for a in grp:
            n = _assign(a)
            if n not in nums_seen:
                nums_seen.append(n)
        # [[n]](url) renders in markdown as a clickable [n] link.
        inline = "".join(
            f"[[{n}]]({num_to_entry[n][1]})" for n in sorted(nums_seen)
        )
        out_parts.append(raw_body[last:m.start()])
        out_parts.append(inline)
        last = m.end()
    out_parts.append(raw_body[last:])

    body = "".join(out_parts)
    sources = [num_to_entry[n] for n in sorted(num_to_entry)]
    _eprint(
        f"[citations] renumbered {len(markers)} cite markers "
        f"→ {len(sources)} unique sources"
    )
    return body, sources


def _extract_citations(interaction: Any, body: str) -> list[tuple[str, str]]:
    """Collect (label, url) sources from an interaction (fallback path).

    Used by _rewrite_body_citations when annotation-based renumbering is not
    possible, and by _extract_citations_from_id.  For normal completed Deep
    Research interactions, prefer _rewrite_body_citations instead.
    """
    annotated = _collect_url_citations(interaction)
    if annotated:
        return _dedup_sources(annotated)

    # Fallback: recursive URL discovery for shapes without annotations.
    urls: list[str] = []
    seen: set[str] = set()

    def add(url: str | None) -> None:
        if not url or not isinstance(url, str):
            return
        url = url.strip().rstrip(".,;)")
        if url.startswith("http") and url not in seen:
            seen.add(url)
            urls.append(url)

    def walk(obj: Any, depth: int = 0) -> None:
        """Recursively extract URLs from any SDK object / dict / list."""
        if depth > 8 or obj is None:
            return
        if isinstance(obj, str):
            for u in _urls_from_text(obj):
                add(u)
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("url", "uri", "source_url", "link", "href"):
                    add(v if isinstance(v, str) else None)
                else:
                    walk(v, depth + 1)
            return
        if isinstance(obj, (list, tuple)):
            for item in obj:
                walk(item, depth + 1)
            return
        for attr in ("url", "uri", "source_url", "link", "href"):
            val = getattr(obj, attr, None)
            if isinstance(val, str):
                add(val)
        for attr in ("content", "parts", "chunks", "results", "grounding_chunks",
                     "grounding_metadata", "web", "citations", "sources",
                     "tool_results", "function_response", "search_results",
                     "annotations", "text"):
            child = getattr(obj, attr, None)
            if child is not None:
                walk(child, depth + 1)

    citations_field = getattr(interaction, "citations", None)
    if citations_field:
        walk(citations_field)

    grounding = getattr(interaction, "grounding_metadata", None)
    if grounding:
        walk(grounding)

    for step in getattr(interaction, "steps", None) or []:
        walk(step)

    for url in _urls_from_text(body):
        add(url)

    return [("", url) for url in urls]


def _extract_grounding_sources(response: Any, body: str) -> list[tuple[str, str]]:
    """Collect (label, url) citations from generate_content grounding metadata."""
    pairs: list[tuple[str, str]] = []

    for candidate in getattr(response, "candidates", None) or []:
        grounding = getattr(candidate, "grounding_metadata", None)
        if grounding is None:
            continue
        for chunk in getattr(grounding, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            if web is not None:
                url = getattr(web, "uri", None) or getattr(web, "url", None)
                if isinstance(url, str) and url.startswith("http"):
                    pairs.append((getattr(web, "title", None) or "", url))

    for url in _urls_from_text(body):
        pairs.append(("", url))

    return _dedup_sources(pairs)


def _format_markdown_report(
    body: str,
    sources: list[tuple[str, str]],
    title: str | None = None,
) -> str:
    """Format report body with an optional title and ## Sources section.

    *sources* is a list of (label, url) pairs; an empty label falls back to the
    URL's host.
    """
    sections: list[str] = []
    if title:
        sections.append(f"# {title}\n")
    sections.append(body.strip())
    if sources:
        sections.append("\n## Sources\n")
        for i, (label, url) in enumerate(sources, 1):
            text = label.replace("\n", " — ").strip() if label else ""
            if not text:
                text = urlparse(url).netloc or url
            sections.append(f"{i}. [{text}]({url})")
    return "\n".join(sections) + "\n"


def _write_output(content: str, output_path: str | None) -> None:
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        _eprint(f"Wrote {output_path}")
    print(content)


def _poll_interaction(
    client: Any,
    interaction_id: str,
    *,
    timeout: int,
    poll_interval: int = DEFAULT_POLL_INTERVAL,
    label: str = "task",
) -> Any:
    """Poll an interaction until completed, failed, or timeout."""
    start = time.monotonic()
    last_status: str | None = None
    last_steps = 0
    last_heartbeat_min = -1

    while True:
        elapsed = time.monotonic() - start
        if elapsed >= timeout:
            raise SystemExit(
                f"{label} timed out after {elapsed:.0f}s (interaction_id={interaction_id})"
            )

        interaction = client.interactions.get(interaction_id)
        status = getattr(interaction, "status", None)

        if status != last_status:
            _eprint(f"[{label}] status={status} elapsed={elapsed:.0f}s id={interaction_id}")
            last_status = status

        step_count = len(getattr(interaction, "steps", None) or [])
        if step_count > last_steps:
            _eprint(f"[{label}] steps={step_count} elapsed={elapsed:.0f}s")
            last_steps = step_count
        elif status == "in_progress":
            heartbeat_min = int(elapsed // 60)
            if heartbeat_min > 0 and heartbeat_min != last_heartbeat_min:
                _eprint(f"[{label}] still {status} steps={step_count} elapsed={elapsed:.0f}s")
                last_heartbeat_min = heartbeat_min

        if status == "completed":
            return interaction
        if status in ("failed", "cancelled", "canceled"):
            error = getattr(interaction, "error", None)
            raise SystemExit(f"{label} {status}: {error} (interaction_id={interaction_id})")

        time.sleep(poll_interval)


def _create_interaction_with_retry(client: Any, *, max_attempts: int = 5, **kwargs: Any) -> Any:
    """Create an interaction, retrying transient GCP setup errors."""
    delay = 5
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return client.interactions.create(**kwargs)
        except Exception as exc:
            last_error = exc
            message = str(exc).lower()
            transient = any(
                phrase in message
                for phrase in (
                    "resource setup is in progress",
                    "please try again shortly",
                    "rate limit",
                    "429",
                    "503",
                )
            )
            if not transient or attempt == max_attempts:
                raise
            _eprint(f"Transient API error (attempt {attempt}/{max_attempts}): {exc}")
            _eprint(f"Retrying in {delay}s...")
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise last_error  # pragma: no cover


def _stream_and_collect(
    client: Any,
    *,
    agent: str,
    query: str,
    tools: list[dict[str, str]] | None,
    timeout: int,
    label: str,
    verbose: bool = False,
) -> tuple[str, list[tuple[str, str]], str]:
    """Start a Deep Research agent, then poll until complete.

    Vertex background Deep Research can go silent for many minutes while the
    agent searches.  Draining the full SSE stream blocks on ``for event in raw``
    with no timeout between events, so we only read the stream long enough to
    get ``interaction_id``, then poll ``interactions.get()`` (reliable path).
    """
    kwargs: dict[str, Any] = {
        "agent": agent,
        "input": query,
        "background": True,
        "stream": True,
        "store": True,
    }
    if tools is not None:
        kwargs["tools"] = tools

    raw = _create_interaction_with_retry(client, **kwargs)
    start = time.monotonic()

    if hasattr(raw, "id"):
        interaction_id = raw.id
    else:
        _eprint(f"[{label}] extracting interaction_id from stream...")
        interaction_id = _interaction_id_from_stream(raw)

    _eprint(f"[{label}] interaction_id={interaction_id}")
    if verbose:
        _eprint(
            f"[{label}] verbose: polling for progress (stream not drained — "
            "Deep Research can be silent for several minutes between events)"
        )

    completed = _poll_interaction(
        client,
        interaction_id,
        timeout=timeout,
        label=label,
    )
    raw_body = _extract_body_text(completed)
    if not raw_body:
        raise SystemExit(f"[{label}] completed but no text (id={interaction_id})")

    body, sources = _rewrite_body_citations(raw_body, completed)
    elapsed_total = time.monotonic() - start
    _eprint(f"[{label}] completed in {elapsed_total:.0f}s")
    return body, sources, interaction_id


def _extract_citations_from_id(client: Any, interaction_id: str, body: str) -> list[tuple[str, str]]:
    """Fetch completed interaction and extract citations."""
    try:
        completed = client.interactions.get(interaction_id)
        return _extract_citations(completed, body)
    except Exception:
        return [("", url) for url in _urls_from_text(body)]


def _interaction_id_from_stream(stream: Any) -> str:
    """Consume stream events until we get the interaction_id, then stop.

    When interactions.create() is called with stream=True it returns a Stream
    object.  The first event has event_type="interaction.created" and carries
    the interaction ID.  Once we have the ID we stop consuming and let the
    poll loop take over via interactions.get().
    """
    for event in stream:
        # Shape 1: event.interaction.id  (Cloud docs example)
        iobj = getattr(event, "interaction", None)
        if iobj is not None:
            iid = getattr(iobj, "id", None)
            if iid:
                return iid
        # Shape 2: event.id directly
        iid = getattr(event, "id", None)
        if iid and isinstance(iid, str) and iid.startswith("Ch"):
            return iid
        # Shape 3: event.interaction_id
        iid = getattr(event, "interaction_id", None)
        if iid:
            return iid
    raise SystemExit("Could not extract interaction_id from stream — no creation event received")


def _run_agent(
    client: Any,
    *,
    agent: str,
    query: str,
    tools: list[dict[str, str]] | None,
    timeout: int,
    label: str,
) -> tuple[str, list[tuple[str, str]], str]:
    """Start a Deep Research agent job, poll, and return (body, sources, interaction_id)."""
    kwargs: dict[str, Any] = {
        "agent": agent,
        "input": query,
        "background": True,
        "stream": True,   # required by Vertex Agent Platform; returns Stream object
        "store": True,
    }
    if tools is not None:
        kwargs["tools"] = tools

    raw = _create_interaction_with_retry(client, **kwargs)

    # stream=True → SDK returns Stream, not Interaction; extract ID from first event
    if hasattr(raw, "id"):
        interaction_id = raw.id
    else:
        _eprint(f"[{label}] stream returned, extracting interaction_id from events...")
        interaction_id = _interaction_id_from_stream(raw)

    _eprint(f"[{label}] started interaction_id={interaction_id}")

    completed = _poll_interaction(
        client, interaction_id, timeout=timeout, label=label
    )
    raw_body = _extract_body_text(completed)
    if not raw_body:
        raise SystemExit(f"{label} completed but returned no text (id={interaction_id})")

    body, sources = _rewrite_body_citations(raw_body, completed)
    return body, sources, interaction_id


def cmd_search(args: argparse.Namespace) -> None:
    if args.fast:
        # Explicit fast fallback: gemini-2.5-flash + google_search (~10s, no agent)
        from google.genai import types

        client = _get_model_client()
        prompt = (
            f"{args.query}\n\n"
            "Provide a concise, factual summary with inline citations. "
            "Prefer recent peer-reviewed and institutional sources when relevant."
        )
        _eprint(f"[search] --fast: querying via {SEARCH_MODEL} + google_search")
        t0 = time.monotonic()
        response = client.models.generate_content(
            model=SEARCH_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        body = (getattr(response, "text", None) or "").strip()
        if not body:
            raise SystemExit("search returned no text")
        sources = _extract_grounding_sources(response, body)
        _eprint(f"[search] completed in {time.monotonic() - t0:.0f}s")
    else:
        # Primary path: deep-research-preview agent (matches step2 spec)
        client = _get_agent_client()
        body, sources, _ = _stream_and_collect(
            client,
            agent=SEARCH_AGENT,
            query=args.query,
            tools=[{"type": "google_search"}],
            timeout=args.timeout,
            label="search",
            verbose=args.verbose,
        )

    report = _format_markdown_report(body, sources)
    _write_output(report, args.output)


def cmd_research(args: argparse.Namespace) -> None:
    client = _get_agent_client()
    agent = RESEARCH_AGENT_MAX if args.max else RESEARCH_AGENT
    if args.max:
        _eprint(f"[research] --max: trying {agent} (404s on Vertex; use without --max)")
    body, sources, interaction_id = _stream_and_collect(
        client,
        agent=agent,
        query=args.query,
        tools=None,
        timeout=args.timeout,
        label="research",
        verbose=args.verbose,
    )
    report = _format_markdown_report(body, sources)
    _eprint(f"[research] interaction_id={interaction_id} (save for follow-ups)")
    _write_output(report, args.output)


def cmd_poll(args: argparse.Namespace) -> None:
    client = _get_agent_client()
    interaction_id = args.interaction_id
    _eprint(f"[poll] fetching interaction_id={interaction_id}")
    interaction = client.interactions.get(interaction_id)
    status = getattr(interaction, "status", None)
    _eprint(f"[poll] status={status}")

    body, sources, _ = _interaction_to_report(
        interaction,
        allow_interim=args.allow_interim,
    )
    report = _format_markdown_report(body, sources)
    _write_output(report, args.output)


def cmd_extract(args: argparse.Namespace) -> None:
    from google.genai import types

    # Extract uses generate_content (not the agent) — url_context not supported by Deep Research agent on Vertex
    client = _get_model_client()
    url = args.url
    objective = args.objective or "Extract the main content, title, and key findings."
    prompt = (
        f"Read and summarize the content at this URL: {url}\n\n"
        f"Objective: {objective}\n\n"
        "Return structured markdown with: title, authors (if available), "
        "abstract/summary, and key findings. Only include facts present in the source."
    )

    _eprint(f"[extract] fetching via {EXTRACT_MODEL} + url_context")
    t0 = time.monotonic()
    response = client.models.generate_content(
        model=EXTRACT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(url_context=types.UrlContext())],
        ),
    )

    body = (getattr(response, "text", None) or "").strip()
    if not body:
        raise SystemExit("extract returned no text")

    sources: list[tuple[str, str]] = [("", u) for u in _urls_from_text(body)]
    existing = {u for _, u in sources}
    candidate = response.candidates[0] if getattr(response, "candidates", None) else None
    if candidate is not None:
        metadata = getattr(candidate, "url_context_metadata", None)
        if metadata is not None:
            for item in getattr(metadata, "url_metadata", None) or []:
                retrieved = getattr(item, "retrieved_url", None)
                if retrieved and retrieved not in existing:
                    existing.add(retrieved)
                    sources.insert(0, ("", retrieved))

    if url not in existing:
        sources.insert(0, ("", url))

    report = _format_markdown_report(body, sources, title=f"Extract: {url}")
    _eprint(f"[extract] completed in {time.monotonic() - t0:.0f}s")
    _write_output(report, args.output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Google Deep Research CLI (Vertex AI Interactions API)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Fast web search synthesis")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("-o", "--output", help="Write markdown to file")
    p_search.add_argument(
        "--fast",
        action="store_true",
        help="Use gemini-2.5-flash + google_search instead of Deep Research agent (~10s, less depth)",
    )
    p_search.add_argument(
        "--timeout", type=int, default=DEFAULT_SEARCH_TIMEOUT, help="Poll timeout seconds"
    )
    p_search.add_argument("--verbose", action="store_true", help="Print all stream events and agent thoughts")
    p_search.set_defaults(func=cmd_search)

    p_research = sub.add_parser("research", help="Comprehensive deep research report")
    p_research.add_argument("query", help="Research topic / question")
    p_research.add_argument("-o", "--output", help="Write markdown to file")
    p_research.add_argument(
        "--max",
        action="store_true",
        help="Try deep-research-max agent (Gemini API only; not available on Vertex yet)",
    )
    p_research.add_argument(
        "--timeout", type=int, default=DEFAULT_RESEARCH_TIMEOUT, help="Poll timeout (seconds)"
    )
    p_research.add_argument("--verbose", action="store_true", help="Print all stream events and agent thoughts")
    p_research.set_defaults(func=cmd_research)

    p_poll = sub.add_parser("poll", help="Fetch report by interaction_id (after research completes)")
    p_poll.add_argument("interaction_id", help="Interaction ID from a prior research run")
    p_poll.add_argument("-o", "--output", help="Write markdown to file")
    p_poll.add_argument(
        "--allow-interim",
        action="store_true",
        help="If job still running, write formatted search notes instead of erroring",
    )
    p_poll.set_defaults(func=cmd_poll)

    p_extract = sub.add_parser("extract", help="Extract content from a URL")
    p_extract.add_argument("url", help="URL to extract")
    p_extract.add_argument(
        "--objective", help="What to extract (default: title, abstract, key findings)"
    )
    p_extract.add_argument("-o", "--output", help="Write markdown to file")
    p_extract.add_argument(
        "--timeout", type=int, default=DEFAULT_EXTRACT_TIMEOUT, help="Poll timeout (seconds)"
    )
    p_extract.set_defaults(func=cmd_extract)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
