"""Abstract conversation + media store interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StoredMessage:
    id: int
    phone: str
    role: str          # "user" | "assistant"
    content: str
    media_id: str | None
    media_type: str | None
    timestamp: datetime
    intent: str | None = None


@dataclass
class StoredMedia:
    media_id: str
    data: bytes
    mime_type: str
    phone: str
    timestamp: datetime


@dataclass
class KnowledgeEntry:
    id: int
    content: str
    source: str
    folder: str
    timestamp: datetime
    embedding: bytes | None = None


class ConversationStore(ABC):
    """Minimal interface every store backend must implement."""

    @abstractmethod
    async def initialize(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    # ── Messages ──
    @abstractmethod
    async def add_message(
        self, phone: str, role: str, content: str,
        media_id: str | None = None, media_type: str | None = None,
        intent: str | None = None,
    ) -> int: ...

    @abstractmethod
    async def get_history(self, phone: str, limit: int = 20) -> list[StoredMessage]: ...

    # ── Media ──
    @abstractmethod
    async def store_media(self, media_id: str, data: bytes, mime_type: str, phone: str) -> None: ...

    @abstractmethod
    async def get_media(self, media_id: str) -> StoredMedia | None: ...

    @abstractmethod
    async def get_recent_media(self, phone: str, media_type: str = "image", limit: int = 5) -> list[StoredMedia]: ...

    # ── Knowledge base ──
    @abstractmethod
    async def add_knowledge(self, content: str, source: str, folder: str = "general") -> int: ...

    @abstractmethod
    async def search_knowledge(self, query: str, folder: str | None = None, limit: int = 5) -> list[KnowledgeEntry]: ...

    @abstractmethod
    async def list_folders(self) -> list[str]: ...

    # ── Activity patterns (RAG learning) ──
    @abstractmethod
    async def record_activity(self, phone: str, intent: str, query: str) -> None: ...

    @abstractmethod
    async def get_frequent_intents(self, phone: str, limit: int = 10) -> list[dict]: ...

    @abstractmethod
    async def get_recent_activities(self, phone: str, limit: int = 20) -> list[dict]: ...
