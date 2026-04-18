"""Abstract tool interface for pluggable capabilities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    text: str
    save_to_folder: str | None = None  # if set, auto-save to knowledge base


class BaseTool(ABC):
    name: str
    description: str
    keywords: list[str] = []

    @abstractmethod
    async def execute(self, query: str, store, llm) -> ToolResult:
        """Run the tool and return a result string."""
