"""RAG-based knowledge base that learns user patterns and preferences.

This tool builds an adaptive profile by tracking:
1. Frequent commands/intents → faster classification
2. Common queries → pre-cached answers
3. Activity patterns → proactive suggestions
"""

from __future__ import annotations

from rayban_meta.tools.base import BaseTool, ToolResult


class AdaptiveKnowledgeTool(BaseTool):
    name = "adaptive"
    description = "Adaptive assistant that learns your patterns and gives personalized answers."
    keywords = ["learn", "pattern", "frequent", "usual", "always"]

    async def execute(self, query: str, store, llm) -> ToolResult:
        # Get user's frequent intents and recent activities
        phone = ""  # filled by message_router
        frequent = await store.get_frequent_intents(phone, limit=5)
        recent = await store.get_recent_activities(phone, limit=10)

        # Search knowledge base for relevant context
        knowledge = await store.search_knowledge(query, limit=3)

        # Build adaptive context
        context_parts = []
        if frequent:
            top_intents = ", ".join(f"{f['intent']}({f['count']}x)" for f in frequent)
            context_parts.append(f"User's frequent actions: {top_intents}")
        if recent:
            recent_queries = [a["query"][:50] for a in recent[:5]]
            context_parts.append(f"Recent queries: {'; '.join(recent_queries)}")
        if knowledge:
            kb_ctx = "; ".join(k.content[:60] for k in knowledge)
            context_parts.append(f"Relevant notes: {kb_ctx}")

        adaptive_context = "\n".join(context_parts) if context_parts else "No prior context available."

        response = await llm.complete(
            messages=[{"role": "user", "content": query}],
            system=(
                "You are a personalized assistant for smart glasses. "
                "Use the following context about the user's habits to give better answers:\n"
                f"{adaptive_context}\n\n"
                "Be concise (1-2 sentences). If you can leverage their patterns, do so."
            ),
            max_tokens=150,
        )
        return ToolResult(text=response)
