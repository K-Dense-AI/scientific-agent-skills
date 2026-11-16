"""Optional anonymous Search MCP backend for bounded public-source lookups."""

import asyncio
import json
from urllib.parse import urlsplit

MCP_URL = "https://search.parallel.ai/mcp"
USER_AGENT = "scientific-agent-skills/research-lookup (+https://github.com/K-Dense-AI/scientific-agent-skills)"


def decode_result(result):
    """Keep tool failures distinct from valid empty results and partial fetches."""
    text = "\n".join(item.text for item in result.content if item.type == "text")
    if result.isError:
        raise RuntimeError(f"Parallel MCP tool failed: {text[:2000]}")
    data = result.structuredContent
    if data is None:
        data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ValueError("Parallel MCP returned an invalid results object")
    for source in data["results"]:
        if (not isinstance(source, dict) or not isinstance(source.get("url"), str)
                or not isinstance(source.get("excerpts"), list)
                or not all(isinstance(s, str) for s in source["excerpts"])):
            raise ValueError("Parallel MCP returned an invalid source")
    return data


async def research(query, *, max_results, fetch_limit, timeout):
    # Lazy imports keep the authenticated CLI and existing tests dependency-free.
    try:
        import anyio
        import httpx
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
    except ImportError as exc:
        raise RuntimeError("Keyless lookup requires mcp>=1.28,<2; see SKILL.md") from exc

    # Bound each HTTP response before the SDK buffers JSON or SSE content.
    class BoundedStream(httpx.AsyncByteStream):
        def __init__(self, stream):
            self.stream = stream

        async def __aiter__(self):
            size = 0
            async for chunk in self.stream:
                size += len(chunk)
                if size > 4 * 1024 * 1024:
                    raise ValueError("Parallel MCP response exceeds 4 MiB")
                yield chunk

        async def aclose(self):
            await self.stream.aclose()

    async def bound_response(response):
        # A compressed wire body can expand beyond the limit before JSON parsing.
        if response.headers.get("content-encoding", "identity").lower() != "identity":
            raise ValueError("Parallel MCP must return an uncompressed response")
        if response.is_stream_consumed:
            if len(response.content) > 4 * 1024 * 1024:
                raise ValueError("Parallel MCP response exceeds 4 MiB")
        else:
            response.stream = BoundedStream(response.stream)

    with anyio.fail_after(timeout):
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}, timeout=timeout,
            follow_redirects=False, event_hooks={"response": [bound_response]},
        ) as client:
            async with streamable_http_client(MCP_URL, http_client=client) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    names = {tool.name for tool in tools.tools}
                    if "web_search" not in names or (fetch_limit and "web_fetch" not in names):
                        raise RuntimeError("Parallel MCP is missing required search/fetch tools")
                    search = decode_result(await session.call_tool("web_search", {
                        "objective": query, "search_queries": [query],
                    }))
                    search["results"] = search["results"][:max_results]
                    urls = []
                    for source in search["results"]:
                        url = source["url"]
                        try:
                            parsed = urlsplit(url)
                            valid = parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password
                        except ValueError:
                            valid = False
                        if valid and url not in urls:
                            urls.append(url)
                    pages = {"results": [], "errors": []}
                    if fetch_limit and urls:
                        arguments = {"urls": urls[:fetch_limit], "objective": query[:200]}
                        # Reuse only this lookup's returned task ID, never process-global state.
                        if isinstance(search.get("session_id"), str):
                            arguments["session_id"] = search["session_id"]
                        pages = decode_result(await session.call_tool("web_fetch", arguments))
                    return {"search": search, "pages": pages}


def lookup(query, *, max_results=20, fetch_limit=3, timeout=60):
    if not query.strip():
        raise ValueError("A nonempty research query is required")
    if timeout <= 0 or max_results < 1:
        raise ValueError("Timeout and maximum results must be positive")
    if not 0 <= fetch_limit <= 10:
        raise ValueError("MCP extract limit must be between 0 and 10")
    return asyncio.run(research(query, max_results=max_results, fetch_limit=fetch_limit, timeout=timeout))
