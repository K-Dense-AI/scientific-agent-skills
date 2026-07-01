"""
BASELINE SNAPSHOT — before post-processing changes (2026-06-30).

Preserved as reference for debugging. This is the script state after T3/T4
spike runs succeeded (~320s / ~850s) but BEFORE these additions:
  - _strip_planning_json()
  - _looks_like_final_report() / _score_report_candidate() scoring in _extract_body_text
  - recursive _extract_citations() walk for ## Sources
  - poll subcommand / interim search notes helpers

Also uses the original _stream_and_collect() that drains the full SSE stream
(can block for long periods during silent search phases).

Current working copy: google_research.py
Post-process attempt snapshot: google_research.with-postprocess.py
"""

#!/usr/bin/env python3

from __future__ import annotations

import argparse
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



def _extract_body_text(interaction: Any) -> str:
    """Collect the final report text from a completed interaction (last step)."""
    steps = getattr(interaction, "steps", None) or []
    for step in reversed(steps):
        text = _step_text(step)
        if text and text.strip():
            return text.strip()

    for attr in ("output", "result", "response"):
        val = getattr(interaction, attr, None)
        if isinstance(val, str) and val.strip():
            return val.strip()

    return ""



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


def _extract_citations(interaction: Any, body: str) -> list[str]:
    """Collect source URLs from interaction metadata and report body."""
    urls: list[str] = []
    seen: set[str] = set()

    def add(url: str | None) -> None:
        if not url or not isinstance(url, str):
            return
        url = url.strip()
        if url.startswith("http") and url not in seen:
            seen.add(url)
            urls.append(url)

    citations = getattr(interaction, "citations", None)
    if citations:
        for cite in citations:
            if isinstance(cite, str):
                add(cite)
            elif isinstance(cite, dict):
                add(cite.get("url") or cite.get("uri"))
            else:
                add(getattr(cite, "url", None) or getattr(cite, "uri", None))

    grounding = getattr(interaction, "grounding_metadata", None)
    if grounding:
        chunks = getattr(grounding, "grounding_chunks", None) or []
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            if web:
                add(getattr(web, "uri", None) or getattr(web, "url", None))

    for step in getattr(interaction, "steps", None) or []:
        for item in getattr(step, "content", None) or []:
            for attr in ("url", "uri", "source_url"):
                add(getattr(item, attr, None))
            result = getattr(item, "result", None)
            if result:
                add(getattr(result, "url", None))

    for url in _urls_from_text(body):
        add(url)

    return urls



def _extract_grounding_sources(response: Any, body: str) -> list[str]:
    """Collect citation URLs from generate_content grounding metadata."""
    urls: list[str] = []
    seen: set[str] = set()

    def add(url: str | None) -> None:
        if not url or not isinstance(url, str):
            return
        url = url.strip()
        if url.startswith("http") and url not in seen:
            seen.add(url)
            urls.append(url)

    for candidate in getattr(response, "candidates", None) or []:
        grounding = getattr(candidate, "grounding_metadata", None)
        if grounding is None:
            continue
        for chunk in getattr(grounding, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            if web is not None:
                add(getattr(web, "uri", None) or getattr(web, "url", None))

    for url in _urls_from_text(body):
        add(url)

    return urls


def _format_markdown_report(body: str, sources: list[str], title: str | None = None) -> str:
    """Format report body with an optional title and ## Sources section."""
    sections: list[str] = []
    if title:
        sections.append(f"# {title}\n")
    sections.append(body.strip())
    if sources:
        sections.append("\n## Sources\n")
        for i, url in enumerate(sources, 1):
            parsed = urlparse(url)
            label = parsed.netloc or url
            sections.append(f"{i}. [{label}]({url})")
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
) -> tuple[str, list[str], str]:
    """Start a Deep Research agent with live stream logging.

    Unlike _run_agent which polls, this reads all events from the stream
    so we can see agent thoughts, searches, and any errors in real time.
    Falls back to poll-based completion after the initial stream closes.
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

    interaction_id: str | None = None
    final_text: str = ""
    start = time.monotonic()

    _eprint(f"[{label}] streaming events (verbose={verbose})...")

    try:
        for event in raw:
            elapsed = time.monotonic() - start

            # Always try to capture interaction_id
            for path in [
                lambda e: getattr(getattr(e, "interaction", None), "id", None),
                lambda e: getattr(e, "id", None) if isinstance(getattr(e, "id", None), str) and str(getattr(e, "id", None)).startswith("Ch") else None,
                lambda e: getattr(e, "interaction_id", None),
            ]:
                val = path(event)
                if val and not interaction_id:
                    interaction_id = val
                    _eprint(f"[{label}] interaction_id={interaction_id}")

            event_type = getattr(event, "event_type", None) or getattr(event, "type", None) or type(event).__name__

            if verbose:
                _eprint(f"[{label}] +{elapsed:.0f}s event_type={event_type}")

            # Print thought / text deltas
            delta = getattr(event, "delta", None)
            if delta is not None:
                delta_type = getattr(delta, "type", None)
                delta_text = getattr(delta, "text", None) or ""
                if delta_type == "thought" and delta_text:
                    _eprint(f"[{label}] thought: {delta_text[:120]}")
                elif delta_type == "text" and delta_text:
                    if verbose:
                        _eprint(f"[{label}] text chunk: {delta_text[:80]}")
                    final_text += delta_text

            # Completion / error events
            if event_type in ("interaction.completed", "completed"):
                _eprint(f"[{label}] stream completed at +{elapsed:.0f}s")
                break
            if event_type in ("error", "interaction.failed", "failed"):
                err = getattr(event, "error", None) or getattr(event, "message", None) or str(event)
                _eprint(f"[{label}] stream error at +{elapsed:.0f}s: {err}")
                break

            if elapsed >= timeout:
                _eprint(f"[{label}] stream timeout at +{elapsed:.0f}s")
                break

    except Exception as exc:
        _eprint(f"[{label}] stream exception: {exc}")

    if not interaction_id:
        raise SystemExit(f"[{label}] no interaction_id from stream")

    # If streaming gave us final text, use it; otherwise fall back to poll
    if final_text.strip():
        body = final_text.strip()
    else:
        _eprint(f"[{label}] no text from stream, polling interactions.get({interaction_id})")
        completed = _poll_interaction(client, interaction_id, timeout=max(60, timeout - int(time.monotonic() - start)), label=label)
        body = _extract_body_text(completed)

    if not body:
        raise SystemExit(f"[{label}] completed but no text (id={interaction_id})")

    sources = _extract_citations_from_id(client, interaction_id, body)
    elapsed_total = time.monotonic() - start
    _eprint(f"[{label}] completed in {elapsed_total:.0f}s")
    return body, sources, interaction_id




def _extract_citations_from_id(client: Any, interaction_id: str, body: str) -> list[str]:
    """Fetch completed interaction and extract citations."""
    try:
        completed = client.interactions.get(interaction_id)
        return _extract_citations(completed, body)
    except Exception:
        return _urls_from_text(body)


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
) -> tuple[str, list[str], str]:
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
    body = _extract_body_text(completed)
    if not body:
        raise SystemExit(f"{label} completed but returned no text (id={interaction_id})")

    sources = _extract_citations(completed, body)
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

    sources = _urls_from_text(body)
    candidate = response.candidates[0] if getattr(response, "candidates", None) else None
    if candidate is not None:
        metadata = getattr(candidate, "url_context_metadata", None)
        if metadata is not None:
            for item in getattr(metadata, "url_metadata", None) or []:
                retrieved = getattr(item, "retrieved_url", None)
                if retrieved and retrieved not in sources:
                    sources.insert(0, retrieved)

    if url not in sources:
        sources.insert(0, url)

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
