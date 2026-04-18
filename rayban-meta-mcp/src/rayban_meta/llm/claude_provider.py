"""Anthropic Claude provider."""

from __future__ import annotations

import base64

import anthropic

from rayban_meta.config import settings
from rayban_meta.llm.base import LLMProvider


class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete(self, messages: list[dict], system: str | None = None, max_tokens: int = 1024) -> str:
        kwargs: dict = {"model": "claude-sonnet-4-20250514", "max_tokens": max_tokens, "messages": messages}
        if system:
            kwargs["system"] = system
        resp = await self._client.messages.create(**kwargs)
        return resp.content[0].text

    async def complete_with_vision(
        self, messages: list[dict], images: list[bytes],
        system: str | None = None, max_tokens: int = 1024,
    ) -> str:
        # Build content blocks: images first, then the text prompt
        content: list[dict] = []
        for img in images:
            b64 = base64.b64encode(img).decode()
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
            })
        # Append text from the last user message
        last_text = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_text = m["content"] if isinstance(m["content"], str) else "Describe this image."
                break
        content.append({"type": "text", "text": last_text or "Describe this image."})

        history = [m for m in messages[:-1] if isinstance(m.get("content"), str)]
        history.append({"role": "user", "content": content})

        kwargs: dict = {"model": "claude-sonnet-4-20250514", "max_tokens": max_tokens, "messages": history}
        if system:
            kwargs["system"] = system
        resp = await self._client.messages.create(**kwargs)
        return resp.content[0].text

    async def classify(self, text: str, categories: list[str], system: str | None = None) -> str:
        cats = ", ".join(categories)
        sys_prompt = (
            system or
            f"Classify the following user message into exactly ONE of these categories: {cats}. "
            f"Respond with ONLY the category name, nothing else."
        )
        resp = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            system=sys_prompt,
            messages=[{"role": "user", "content": text}],
        )
        result = resp.content[0].text.strip().lower()
        # Fuzzy match to known categories
        for cat in categories:
            if cat.lower() in result:
                return cat
        return categories[-1]  # fallback to last (usually "conversation")
