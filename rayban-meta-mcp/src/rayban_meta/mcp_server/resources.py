"""MCP Resources – expose glasses data as browsable resources."""

from __future__ import annotations

from rayban_meta.config import settings
from rayban_meta.mcp_server.server import mcp


@mcp.resource("glasses://status")
async def glasses_status() -> str:
    """Current glasses connection status."""
    from rayban_meta.mcp_server.server import get_glasses_status
    status = await get_glasses_status()
    lines = [f"{k}: {v}" for k, v in status.items()]
    return "\n".join(lines)


@mcp.resource("glasses://conversations/recent")
async def recent_conversations() -> str:
    """Last 20 messages exchanged with the glasses."""
    from rayban_meta.mcp_server.server import get_recent_messages
    messages = await get_recent_messages(limit=20)
    lines = [f"[{m['timestamp']}] {m['role']}: {m['content']}" for m in messages]
    return "\n".join(lines) or "No conversations yet."


@mcp.resource("glasses://knowledge/folders")
async def knowledge_folders() -> str:
    """All knowledge base folders."""
    from rayban_meta.mcp_server.server import list_knowledge_folders
    folders = await list_knowledge_folders()
    return "\n".join(folders) or "No folders yet."


@mcp.resource("glasses://patterns")
async def activity_patterns() -> str:
    """User activity patterns and frequent commands."""
    from rayban_meta.mcp_server.server import get_activity_patterns
    data = await get_activity_patterns()
    lines = []
    for f in data.get("frequent_intents", []):
        lines.append(f"  {f['intent']}: {f['count']}x (last: {f['last_used']})")
    return "Frequent intents:\n" + "\n".join(lines) if lines else "No patterns yet."
