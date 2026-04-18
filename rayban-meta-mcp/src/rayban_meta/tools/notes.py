"""Notes tool – save and retrieve notes via folders.

Supports voice commands like:
  - "save this to work/meetings"
  - "salveaza in proiecte/alpha"
  - "what did I save about meetings?"
"""

from __future__ import annotations

from rayban_meta.tools.base import BaseTool, ToolResult


class SaveNoteTool(BaseTool):
    name = "save"
    description = "Save information to a named folder. Say 'save this to <folder>' to organize."
    keywords = ["save", "salveaza", "remember", "noteaza", "store"]

    async def execute(self, query: str, store, llm) -> ToolResult:
        from rayban_meta.tools.registry import detect_save_command

        is_save, folder = detect_save_command(query)
        if not is_save:
            folder = "general"

        # Clean the content (remove the save command prefix)
        content = query
        for prefix in ["save this to", "save to", "salveaza in", "remember in", "noteaza in"]:
            if content.lower().startswith(prefix):
                content = content[len(prefix):].strip()
                # Remove folder name from beginning of content
                if content.lower().startswith(folder.lower()):
                    content = content[len(folder):].strip()

        if not content or len(content) < 3:
            return ToolResult(text="What should I save? Please include some content.")

        entry_id = await store.add_knowledge(content=content, source="voice", folder=folder)
        return ToolResult(text=f"Saved to folder '{folder}' (#{entry_id}).")


class SearchKnowledgeTool(BaseTool):
    name = "knowledge"
    description = "Search saved notes and knowledge base. Ask 'what did I save about X?'"
    keywords = ["knowledge", "recall", "what did I", "find note", "search notes"]

    async def execute(self, query: str, store, llm) -> ToolResult:
        # Check if searching in a specific folder
        folder = None
        for prefix in ["in folder", "in", "din"]:
            if f" {prefix} " in query.lower():
                parts = query.lower().split(f" {prefix} ")
                if len(parts) > 1:
                    folder = parts[-1].strip()
                    query = parts[0].strip()
                    break

        results = await store.search_knowledge(query, folder=folder, limit=3)
        if not results:
            return ToolResult(text="Nothing found in my notes.")

        lines = []
        for r in results:
            lines.append(f"[{r.folder}] {r.content[:80]}")

        # Summarize for glasses
        context = "\n".join(lines)
        summary = await llm.complete(
            messages=[{"role": "user", "content": f"Summarize these notes relevant to '{query}':\n{context}"}],
            system="Be very concise, 1-2 sentences max.",
            max_tokens=100,
        )
        return ToolResult(text=summary)
