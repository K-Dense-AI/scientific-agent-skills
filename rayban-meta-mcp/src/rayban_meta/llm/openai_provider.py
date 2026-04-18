"""OpenAI GPT-4 provider."""

from __future__ import annotations

import base64

import openai

from rayban_meta.config import settings
from rayban_meta.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self) -> None:
        self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    async def complete(self, messages: list[dict], system: str | None = None, max_tokens: int = 1024) -> str:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)
        resp = await self._client.chat.completions.create(model="gpt-4o", max_tokens=max_tokens, messages=msgs)
        return resp.choices[0].message.content or ""

    async def complete_with_vision(
        self, messages: list[dict], images: list[bytes],
        system: str | None = None, max_tokens: int = 1024,
    ) -> str:
        content: list[dict] = []
        for img in images:
            b64 = base64.b64encode(img).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
        last_text = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_text = m["content"] if isinstance(m["content"], str) else "Describe this image."
                break
        content.append({"type": "text", "text": last_text or "Describe this image."})

        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(m for m in messages[:-1] if isinstance(m.get("content"), str))
        msgs.append({"role": "user", "content": content})

        resp = await self._client.chat.completions.create(model="gpt-4o", max_tokens=max_tokens, messages=msgs)
        return resp.choices[0].message.content or ""

    async def classify(self, text: str, categories: list[str], system: str | None = None) -> str:
        cats = ", ".join(categories)
        sys_prompt = (
            system or
            f"Classify the following user message into exactly ONE of these categories: {cats}. "
            f"Respond with ONLY the category name, nothing else."
        )
        resp = await self._client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=50,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": text},
            ],
        )
        result = (resp.choices[0].message.content or "").strip().lower()
        for cat in categories:
            if cat.lower() in result:
                return cat
        return categories[-1]
