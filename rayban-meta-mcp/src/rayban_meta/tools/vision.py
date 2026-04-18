"""Vision tool – analyze images from the glasses camera."""

from __future__ import annotations

from rayban_meta.tools.base import BaseTool, ToolResult


class VisionTool(BaseTool):
    name = "image_analysis"
    description = "Analyze photos taken by the glasses camera."
    keywords = ["photo", "image", "see", "look", "describe", "what is this"]

    async def execute(self, query: str, store, llm) -> ToolResult:
        # This is called when there's an image; the actual image bytes
        # are passed via the message_router (not through this method).
        # This serves as a fallback / text-only reference.
        return ToolResult(
            text="Send a photo from your glasses and I'll analyze it. "
            "Just take a picture and ask your question."
        )
