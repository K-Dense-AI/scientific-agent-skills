"""SQLite-backed conversation store with FTS5 knowledge search."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from rayban_meta.memory.store import (
    ConversationStore,
    KnowledgeEntry,
    StoredMedia,
    StoredMessage,
)

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    phone     TEXT NOT NULL,
    role      TEXT NOT NULL,
    content   TEXT NOT NULL,
    media_id  TEXT,
    media_type TEXT,
    intent    TEXT,
    ts        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS media (
    media_id  TEXT PRIMARY KEY,
    data      BLOB NOT NULL,
    mime_type TEXT NOT NULL,
    phone     TEXT NOT NULL,
    ts        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS knowledge (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    source  TEXT NOT NULL DEFAULT 'user',
    folder  TEXT NOT NULL DEFAULT 'general',
    ts      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    content, source, folder, content='knowledge', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
    INSERT INTO knowledge_fts(rowid, content, source, folder)
    VALUES (new.id, new.content, new.source, new.folder);
END;

CREATE TABLE IF NOT EXISTS activities (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    phone  TEXT NOT NULL,
    intent TEXT NOT NULL,
    query  TEXT NOT NULL,
    ts     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_phone ON messages(phone, ts DESC);
CREATE INDEX IF NOT EXISTS idx_media_phone ON media(phone, ts DESC);
CREATE INDEX IF NOT EXISTS idx_activities_phone ON activities(phone, ts DESC);
"""


class SQLiteStore(ConversationStore):
    def __init__(self, db_path: str) -> None:
        self._path = db_path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)
        await self._db.commit()
        logger.info("SQLite store initialized at %s", self._path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    # ── Messages ─────────────────────────────────────────────

    async def add_message(
        self, phone: str, role: str, content: str,
        media_id: str | None = None, media_type: str | None = None,
        intent: str | None = None,
    ) -> int:
        cur = await self._db.execute(
            "INSERT INTO messages (phone, role, content, media_id, media_type, intent) VALUES (?, ?, ?, ?, ?, ?)",
            (phone, role, content, media_id, media_type, intent),
        )
        await self._db.commit()
        return cur.lastrowid

    async def get_history(self, phone: str, limit: int = 20) -> list[StoredMessage]:
        rows = await self._db.execute_fetchall(
            "SELECT * FROM messages WHERE phone = ? ORDER BY ts DESC LIMIT ?",
            (phone, limit),
        )
        return [self._row_to_message(r) for r in reversed(rows)]

    # ── Media ────────────────────────────────────────────────

    async def store_media(self, media_id: str, data: bytes, mime_type: str, phone: str) -> None:
        await self._db.execute(
            "INSERT OR REPLACE INTO media (media_id, data, mime_type, phone) VALUES (?, ?, ?, ?)",
            (media_id, data, mime_type, phone),
        )
        await self._db.commit()

    async def get_media(self, media_id: str) -> StoredMedia | None:
        row = await self._db.execute_fetchall(
            "SELECT * FROM media WHERE media_id = ?", (media_id,),
        )
        return self._row_to_media(row[0]) if row else None

    async def get_recent_media(self, phone: str, media_type: str = "image", limit: int = 5) -> list[StoredMedia]:
        mime_prefix = {"image": "image/", "audio": "audio/", "video": "video/"}.get(media_type, media_type)
        rows = await self._db.execute_fetchall(
            "SELECT * FROM media WHERE phone = ? AND mime_type LIKE ? ORDER BY ts DESC LIMIT ?",
            (phone, f"{mime_prefix}%", limit),
        )
        return [self._row_to_media(r) for r in rows]

    # ── Knowledge base ───────────────────────────────────────

    async def add_knowledge(self, content: str, source: str, folder: str = "general") -> int:
        cur = await self._db.execute(
            "INSERT INTO knowledge (content, source, folder) VALUES (?, ?, ?)",
            (content, source, folder),
        )
        await self._db.commit()
        return cur.lastrowid

    async def search_knowledge(self, query: str, folder: str | None = None, limit: int = 5) -> list[KnowledgeEntry]:
        if folder:
            rows = await self._db.execute_fetchall(
                """SELECT k.* FROM knowledge k
                   JOIN knowledge_fts f ON k.id = f.rowid
                   WHERE knowledge_fts MATCH ? AND k.folder = ?
                   ORDER BY rank LIMIT ?""",
                (query, folder, limit),
            )
        else:
            rows = await self._db.execute_fetchall(
                """SELECT k.* FROM knowledge k
                   JOIN knowledge_fts f ON k.id = f.rowid
                   WHERE knowledge_fts MATCH ?
                   ORDER BY rank LIMIT ?""",
                (query, limit),
            )
        return [self._row_to_knowledge(r) for r in rows]

    async def list_folders(self) -> list[str]:
        rows = await self._db.execute_fetchall(
            "SELECT DISTINCT folder FROM knowledge ORDER BY folder",
        )
        return [r["folder"] for r in rows]

    # ── Activity patterns ────────────────────────────────────

    async def record_activity(self, phone: str, intent: str, query: str) -> None:
        await self._db.execute(
            "INSERT INTO activities (phone, intent, query) VALUES (?, ?, ?)",
            (phone, intent, query),
        )
        await self._db.commit()

    async def get_frequent_intents(self, phone: str, limit: int = 10) -> list[dict]:
        rows = await self._db.execute_fetchall(
            """SELECT intent, COUNT(*) as cnt, MAX(ts) as last_used
               FROM activities WHERE phone = ?
               GROUP BY intent ORDER BY cnt DESC LIMIT ?""",
            (phone, limit),
        )
        return [{"intent": r["intent"], "count": r["cnt"], "last_used": r["last_used"]} for r in rows]

    async def get_recent_activities(self, phone: str, limit: int = 20) -> list[dict]:
        rows = await self._db.execute_fetchall(
            "SELECT * FROM activities WHERE phone = ? ORDER BY ts DESC LIMIT ?",
            (phone, limit),
        )
        return [{"intent": r["intent"], "query": r["query"], "ts": r["ts"]} for r in rows]

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _row_to_message(r) -> StoredMessage:
        return StoredMessage(
            id=r["id"], phone=r["phone"], role=r["role"],
            content=r["content"], media_id=r["media_id"],
            media_type=r["media_type"], intent=r["intent"],
            timestamp=datetime.fromisoformat(r["ts"]),
        )

    @staticmethod
    def _row_to_media(r) -> StoredMedia:
        return StoredMedia(
            media_id=r["media_id"], data=r["data"],
            mime_type=r["mime_type"], phone=r["phone"],
            timestamp=datetime.fromisoformat(r["ts"]),
        )

    @staticmethod
    def _row_to_knowledge(r) -> KnowledgeEntry:
        return KnowledgeEntry(
            id=r["id"], content=r["content"], source=r["source"],
            folder=r["folder"], timestamp=datetime.fromisoformat(r["ts"]),
        )
