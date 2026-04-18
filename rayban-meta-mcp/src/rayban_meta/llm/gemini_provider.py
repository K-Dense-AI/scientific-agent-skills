"""Google Gemini provider."""

from __future__ import annotations

from google import genai
from google.genai import types

from rayban_meta.config import settings
from rayban_meta.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.google_gemini_api_key)

    async def complete(self, messages: list[dict], system: str | None = None, max_tokens: int = 1024) -> str:
        contents = [{"role": m["role"], "parts": [{"text": m["content"]}]} for m in messages if isinstance(m.get("content"), str)]
        config = types.GenerateContentConfig(max_output_tokens=max_tokens)
        if system:
            config.system_instruction = system
        resp = await self._client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=config,
        )
        return resp.text or ""

    async def complete_with_vision(
        self, messages: list[dict], images: list[bytes],
        system: str | None = None, max_tokens: int = 1024,
    ) -> str:
        parts = []
        for img in images:
            parts.append(types.Part.from_bytes(data=img, mime_type="image/jpeg"))
        last_text = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_text = m["content"] if isinstance(m["content"], str) else "Describe this image."
                break
        parts.append(types.Part.from_text(text=last_text or "Describe this image."))

        config = types.GenerateContentConfig(max_output_tokens=max_tokens)
        if system:
            config.system_instruction = system
        resp = await self._client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=[{"role": "user", "parts": parts}],
            config=config,
        )
        return resp.text or ""

    async def classify(self, text: str, categories: list[str], system: str | None = None) -> str:
        cats = ", ".join(categories)
        sys_prompt = (
            system or
            f"Classify the following user message into exactly ONE of these categories: {cats}. "
            f"Respond with ONLY the category name, nothing else."
        )
        config = types.GenerateContentConfig(max_output_tokens=50, system_instruction=sys_prompt)
        resp = await self._client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=[{"role": "user", "parts": [{"text": text}]}],
            config=config,
        )
        result = (resp.text or "").strip().lower()
        for cat in categories:
            if cat.lower() in result:
                return cat
        return categories[-1]
