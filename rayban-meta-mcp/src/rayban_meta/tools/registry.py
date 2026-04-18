"""Tool registry – register, discover, and dispatch tools."""

from __future__ import annotations

import logging
import re

from rayban_meta.tools.base import BaseTool

logger = logging.getLogger(__name__)

# Intent categories the LLM classifies into
INTENT_CATEGORIES = [
    "search",
    "calendar",
    "notes",
    "save",          # "save this to <folder>"
    "knowledge",     # "what did I save about …"
    "image_analysis",
    "conversation",  # fallback
]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        logger.info("Registered tool: %s", tool.name)

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def match_intent(self, intent: str) -> BaseTool | None:
        """Map an LLM-classified intent to a tool."""
        return self._tools.get(intent)

    def list_tools(self) -> list[dict]:
        return [{"name": t.name, "description": t.description} for t in self._tools.values()]

    def tools_description(self) -> str:
        """Formatted string for the LLM system prompt."""
        lines = [f"- {t.name}: {t.description}" for t in self._tools.values()]
        return "\n".join(lines)


def detect_save_command(text: str) -> tuple[bool, str]:
    """Check if the user wants to save to a specific folder.

    Returns (is_save, folder_name). Supports patterns like:
      - "save this to work/meetings"
      - "salveaza in proiecte/alpha"
      - "remember this in personal/ideas"
    """
    patterns = [
        r"(?:save|salveaz[aă]|remember|noteaz[aă])\s+(?:this|asta|it)?\s*(?:to|in|la|into)\s+(\S+)",
        r"(?:save|salveaz[aă])\s+(?:to|in|la)\s+(\S+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            folder = m.group(1).strip("/")
            return True, folder
    return False, "general"
