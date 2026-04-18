"""Multi-provider LLM router – picks the right backend per request."""

from __future__ import annotations

import logging

from rayban_meta.config import settings
from rayban_meta.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class LLMRouter:
    """Holds all configured providers and routes requests."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._init_providers()

    def _init_providers(self) -> None:
        if settings.anthropic_api_key:
            from rayban_meta.llm.claude_provider import ClaudeProvider
            self._providers["claude"] = ClaudeProvider()
            logger.info("Claude provider initialized")

        if settings.openai_api_key:
            from rayban_meta.llm.openai_provider import OpenAIProvider
            self._providers["openai"] = OpenAIProvider()
            logger.info("OpenAI provider initialized")

        if settings.google_gemini_api_key:
            from rayban_meta.llm.gemini_provider import GeminiProvider
            self._providers["gemini"] = GeminiProvider()
            logger.info("Gemini provider initialized")

        if not self._providers:
            raise RuntimeError("No LLM provider configured – set at least one API key")

    def get(self, name: str | None = None) -> LLMProvider:
        """Return the requested (or default) provider."""
        target = name or settings.llm_default_provider
        if target in self._providers:
            return self._providers[target]
        # Fallback to first available
        logger.warning("Provider %s not available, falling back", target)
        return next(iter(self._providers.values()))

    @property
    def available(self) -> list[str]:
        return list(self._providers.keys())
