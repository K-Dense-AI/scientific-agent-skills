"""Abstract LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Every LLM backend implements these three methods."""

    name: str

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        system: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        """Text completion."""

    @abstractmethod
    async def complete_with_vision(
        self,
        messages: list[dict],
        images: list[bytes],
        system: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        """Text + image completion."""

    @abstractmethod
    async def classify(
        self,
        text: str,
        categories: list[str],
        system: str | None = None,
    ) -> str:
        """Return exactly one of *categories*."""
