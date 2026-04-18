"""Web search tool using Serper.dev API."""

from __future__ import annotations

import httpx

from rayban_meta.config import settings
from rayban_meta.tools.base import BaseTool, ToolResult


class WebSearchTool(BaseTool):
    name = "search"
    description = "Search the web for current information, news, facts, or answers."
    keywords = ["search", "find", "look up", "what is", "who is", "google", "cauta"]

    async def execute(self, query: str, store, llm) -> ToolResult:
        # Call Serper API
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": settings.serper_api_key},
                json={"q": query, "num": 5},
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()

        # Extract snippets
        snippets = []
        for item in data.get("organic", [])[:3]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            snippets.append(f"{title}: {snippet}")

        if data.get("answerBox"):
            answer = data["answerBox"].get("answer") or data["answerBox"].get("snippet", "")
            if answer:
                snippets.insert(0, f"Direct answer: {answer}")

        context = "\n".join(snippets) if snippets else "No results found."

        # Summarize with LLM (concise for glasses)
        summary = await llm.complete(
            messages=[{"role": "user", "content": f"Based on these search results, give a concise answer (max 2 sentences) to: {query}\n\nResults:\n{context}"}],
            system="You are a concise assistant for smart glasses. Answer in 1-2 short sentences.",
            max_tokens=100,
        )
        return ToolResult(text=summary)
