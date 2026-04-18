"""MCP Server – expose Ray-Ban Meta glasses as tools for Claude Code.

Mounted on the same FastAPI process at /mcp (SSE transport).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP

from rayban_meta.config import settings

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="Ray-Ban Meta Glasses",
    instructions=(
        "Tools for interacting with Ray-Ban Meta smart glasses via WhatsApp. "
        "The glasses can send voice messages, take photos, and receive text responses. "
        "Messages are chunked to ~15 words for the glasses display."
    ),
)


def _get_store():
    """Lazy import to avoid circular deps at module load."""
    from rayban_meta.memory.sqlite_store import SQLiteStore
    import asyncio

    store = SQLiteStore(settings.database_path)
    # Ensure initialized
    loop = asyncio.get_event_loop()
    if not store._db:
        loop.run_until_complete(store.initialize())
    return store


def _get_whatsapp_client():
    from rayban_meta.whatsapp.api import WhatsAppClient
    return WhatsAppClient()


# ── Tools ────────────────────────────────────────────────────


@mcp.tool()
async def send_message_to_glasses(message: str) -> str:
    """Send a text message to the Ray-Ban Meta glasses via WhatsApp.

    The wearer will hear/see this message. Keep under 15 words for best
    glasses display. Longer messages are auto-chunked.
    """
    wa = _get_whatsapp_client()
    try:
        await wa.send_text(settings.whatsapp_recipient_phone, message)
        return f"Message sent to glasses: {message[:80]}..."
    except Exception as e:
        return f"Failed to send: {e}"


@mcp.tool()
async def get_recent_messages(limit: int = 10) -> list[dict]:
    """Get recent conversation messages with the glasses.

    Returns both user messages (from glasses) and assistant responses.
    Useful for reviewing what was discussed.
    """
    store = _get_store()
    messages = await store.get_history(settings.whatsapp_recipient_phone, limit=limit)
    return [
        {
            "role": m.role,
            "content": m.content,
            "intent": m.intent,
            "timestamp": m.timestamp.isoformat(),
            "media_type": m.media_type,
        }
        for m in messages
    ]


@mcp.tool()
async def get_recent_photos(limit: int = 5) -> list[dict]:
    """Get metadata about recent photos taken by the glasses camera.

    Returns media IDs, timestamps. Use analyze_photo to examine an image.
    """
    store = _get_store()
    media = await store.get_recent_media(settings.whatsapp_recipient_phone, "image", limit)
    return [
        {
            "media_id": m.media_id,
            "mime_type": m.mime_type,
            "timestamp": m.timestamp.isoformat(),
            "size_bytes": len(m.data),
        }
        for m in media
    ]


@mcp.tool()
async def analyze_photo(media_id: str, prompt: str = "Describe this image in detail") -> str:
    """Analyze a photo from the glasses using the configured vision LLM.

    Get media_ids from get_recent_photos first.
    """
    store = _get_store()
    media = await store.get_media(media_id)
    if not media:
        return f"No photo found with media_id: {media_id}"

    from rayban_meta.llm.router import LLMRouter
    llm = LLMRouter().get()
    result = await llm.complete_with_vision(
        messages=[{"role": "user", "content": prompt}],
        images=[media.data],
        max_tokens=500,
    )
    return result


@mcp.tool()
async def get_conversation_summary(hours: int = 24) -> str:
    """Summarize all glasses interactions in the last N hours.

    Great for daily reviews or catching up on what happened.
    """
    store = _get_store()
    messages = await store.get_history(settings.whatsapp_recipient_phone, limit=50)

    cutoff = datetime.now() - timedelta(hours=hours)
    recent = [m for m in messages if m.timestamp >= cutoff]

    if not recent:
        return f"No interactions in the last {hours} hours."

    conversation = "\n".join(f"[{m.role}] {m.content}" for m in recent)

    from rayban_meta.llm.router import LLMRouter
    llm = LLMRouter().get()
    summary = await llm.complete(
        messages=[{"role": "user", "content": f"Summarize this conversation from smart glasses:\n{conversation}"}],
        system="Create a structured summary with key topics, decisions, and action items.",
        max_tokens=500,
    )
    return summary


@mcp.tool()
async def search_knowledge_base(query: str, folder: str | None = None) -> list[dict]:
    """Search the personal knowledge base built from glasses interactions.

    Knowledge is organized in folders (e.g., 'work/meetings', 'personal/ideas').
    """
    store = _get_store()
    results = await store.search_knowledge(query, folder=folder, limit=10)
    return [
        {
            "id": r.id,
            "content": r.content,
            "folder": r.folder,
            "source": r.source,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in results
    ]


@mcp.tool()
async def add_to_knowledge_base(content: str, folder: str = "general", source: str = "claude_code") -> str:
    """Add information to the knowledge base.

    Can be retrieved later by the glasses assistant or via search_knowledge_base.
    Organize with folders like 'work/projects', 'personal/health', etc.
    """
    store = _get_store()
    entry_id = await store.add_knowledge(content, source=source, folder=folder)
    return f"Added to knowledge base in folder '{folder}' (#{entry_id})"


@mcp.tool()
async def list_knowledge_folders() -> list[str]:
    """List all folders in the knowledge base."""
    store = _get_store()
    return await store.list_folders()


@mcp.tool()
async def get_activity_patterns() -> dict:
    """Get the user's activity patterns from glasses usage.

    Shows frequent commands, recent activities, and usage insights.
    Useful for understanding how the user interacts with their glasses.
    """
    store = _get_store()
    phone = settings.whatsapp_recipient_phone
    frequent = await store.get_frequent_intents(phone, limit=10)
    recent = await store.get_recent_activities(phone, limit=20)
    return {
        "frequent_intents": frequent,
        "recent_activities": recent,
        "total_patterns": len(frequent),
    }


@mcp.tool()
async def get_glasses_status() -> dict:
    """Get the current status of the glasses connection.

    Returns last message time, total messages today, connection health.
    """
    store = _get_store()
    phone = settings.whatsapp_recipient_phone
    messages = await store.get_history(phone, limit=1)
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    all_today = await store.get_history(phone, limit=100)
    today_count = sum(1 for m in all_today if m.timestamp >= today_start)

    return {
        "connected": bool(settings.whatsapp_access_token),
        "last_message": messages[0].timestamp.isoformat() if messages else None,
        "messages_today": today_count,
        "llm_provider": settings.llm_default_provider,
        "transcription_provider": settings.transcription_provider,
    }


# ── App factory ──────────────────────────────────────────────

def create_mcp_app():
    """Return the Starlette/ASGI app for mounting on FastAPI."""
    return mcp.sse_app()
