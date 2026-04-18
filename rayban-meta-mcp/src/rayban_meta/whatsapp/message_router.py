"""Central message router – dispatches WhatsApp messages to LLM + tools.

Flow:
  1. Extract message type (text / audio / image)
  2. Audio → download via media_id + transcribe → treat as text
  3. Image → download via media_id + store + send to vision LLM
  4. Text → classify intent → dispatch to tool or conversation
  5. Record activity for RAG learning
  6. Send response back via WhatsApp
"""

from __future__ import annotations

import logging
from datetime import datetime

from rayban_meta.config import settings
from rayban_meta.llm.router import LLMRouter
from rayban_meta.llm.transcription import transcribe
from rayban_meta.memory.sqlite_store import SQLiteStore
from rayban_meta.tools.base import ToolResult
from rayban_meta.tools.registry import (
    INTENT_CATEGORIES,
    ToolRegistry,
    detect_save_command,
)
from rayban_meta.whatsapp.api import WhatsAppClient

logger = logging.getLogger(__name__)

# Singletons (initialized on first call)
_whatsapp_client: WhatsAppClient | None = None
_llm_router: LLMRouter | None = None
_tool_registry: ToolRegistry | None = None


def _get_whatsapp_client() -> WhatsAppClient:
    global _whatsapp_client
    if _whatsapp_client is None:
        _whatsapp_client = WhatsAppClient()
    return _whatsapp_client


def _get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router


def _get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        from rayban_meta.tools.calendar import CalendarTool
        from rayban_meta.tools.knowledge_base import AdaptiveKnowledgeTool
        from rayban_meta.tools.notes import SaveNoteTool, SearchKnowledgeTool
        from rayban_meta.tools.vision import VisionTool
        from rayban_meta.tools.web_search import WebSearchTool

        _tool_registry = ToolRegistry()
        _tool_registry.register(WebSearchTool())
        _tool_registry.register(CalendarTool())
        _tool_registry.register(SaveNoteTool())
        _tool_registry.register(SearchKnowledgeTool())
        _tool_registry.register(VisionTool())
        _tool_registry.register(AdaptiveKnowledgeTool())
    return _tool_registry


SYSTEM_PROMPT = """You are a concise AI assistant running on Ray-Ban Meta smart glasses via WhatsApp.
Keep answers SHORT (1-3 sentences max) because the glasses display truncates long text.
Be direct and helpful. The user is speaking to you through voice commands.
Current time: {now}

Available tools: {tools}
User's frequent actions: {frequent}
"""


async def handle_message(app, sender_phone: str, raw_message: dict) -> None:
    """Process a single incoming WhatsApp message."""
    store: SQLiteStore = app.state.store
    wa = _get_whatsapp_client()
    llm_router = _get_llm_router()
    registry = _get_tool_registry()

    llm = llm_router.get()
    response_text = ""

    # Mark as read
    msg_id = raw_message.get("id", "")
    if msg_id:
        await wa.mark_as_read(msg_id)

    try:
        msg_type = raw_message.get("type", "")

        if msg_type == "audio":
            audio_data = raw_message.get("audio", {})
            media_id = audio_data.get("id", "")
            if media_id:
                response_text = await _handle_audio(media_id, "", sender_phone, store, llm, registry)
            else:
                response_text = "I received audio but couldn't process it."

        elif msg_type == "image":
            image_data = raw_message.get("image", {})
            media_id = image_data.get("id", "")
            caption = image_data.get("caption", "")
            if media_id:
                response_text = await _handle_image(media_id, caption, sender_phone, store, llm)
            else:
                response_text = "I received an image but couldn't process it."

        elif msg_type == "text":
            text_data = raw_message.get("text", {})
            text = text_data.get("body", "") if isinstance(text_data, dict) else ""
            if text:
                response_text = await _handle_text(text, sender_phone, store, llm, registry)
            else:
                response_text = "I didn't catch that. Could you repeat?"

        else:
            response_text = f"I received a {msg_type} message but I can only handle text, voice, and images for now."

    except Exception:
        logger.exception("Error handling message")
        response_text = "Sorry, something went wrong. Please try again."

    # Send response
    if response_text:
        await wa.send_text(sender_phone, response_text)


async def _handle_audio(media_id: str, caption: str, sender_phone: str, store, llm, registry) -> str:
    """Download audio via media_id → transcribe → process as text."""
    wa = _get_whatsapp_client()
    audio_bytes = await wa.download_media(media_id)
    text = await transcribe(audio_bytes)
    logger.info("Transcribed audio from %s: %s", sender_phone, text[:100])

    await store.add_message(sender_phone, "user", f"[voice] {text}", media_type="audio")

    response = await _handle_text(text, sender_phone, store, llm, registry)
    await store.add_message(sender_phone, "assistant", response)
    return response


async def _handle_image(media_id: str, caption: str, sender_phone: str, store, llm) -> str:
    """Download image via media_id → analyze with vision LLM."""
    wa = _get_whatsapp_client()
    image_bytes = await wa.download_media(media_id)

    # Store image
    stored_id = f"wa_{sender_phone}_{int(datetime.now().timestamp())}"
    await store.store_media(stored_id, image_bytes, "image/jpeg", sender_phone)
    await store.add_message(sender_phone, "user", f"[photo] {caption or 'Image sent'}", media_id=stored_id, media_type="image")

    # Analyze with vision
    prompt = caption or "Describe what you see in this image. Be concise."
    history = await _build_context(sender_phone, store)
    response = await llm.complete_with_vision(
        messages=history + [{"role": "user", "content": prompt}],
        images=[image_bytes],
        system="You are a concise assistant on smart glasses. Describe images in 1-2 sentences.",
        max_tokens=150,
    )

    await store.add_message(sender_phone, "assistant", response)
    return response


async def _handle_text(text: str, sender_phone: str, store, llm, registry) -> str:
    """Classify intent → dispatch to tool or general conversation."""
    if not text.strip():
        return "I didn't catch that. Could you repeat?"

    # Check for explicit save command first
    is_save, folder = detect_save_command(text)
    if is_save:
        tool = registry.get("save")
        if tool:
            result = await tool.execute(text, store, llm)
            await store.record_activity(sender_phone, "save", text)
            await store.add_message(sender_phone, "user", text, intent="save")
            await store.add_message(sender_phone, "assistant", result.text)
            return result.text

    # Classify intent using LLM
    frequent = await store.get_frequent_intents(sender_phone, limit=5)
    intent = await llm.classify(text, INTENT_CATEGORIES)
    logger.info("Intent for '%s': %s", text[:50], intent)

    # Record activity for learning
    await store.record_activity(sender_phone, intent, text)
    await store.add_message(sender_phone, "user", text, intent=intent)

    # Dispatch to tool
    tool = registry.match_intent(intent)
    if tool and intent != "conversation":
        result = await tool.execute(text, store, llm)

        if result.save_to_folder:
            await store.add_knowledge(result.text, source=tool.name, folder=result.save_to_folder)

        await store.add_message(sender_phone, "assistant", result.text)
        return result.text

    # General conversation
    history = await _build_context(sender_phone, store)
    frequent_str = ", ".join(f"{f['intent']}({f['count']}x)" for f in frequent) if frequent else "none yet"
    tools_str = registry.tools_description()

    system = SYSTEM_PROMPT.format(
        now=datetime.now().strftime("%Y-%m-%d %H:%M"),
        tools=tools_str,
        frequent=frequent_str,
    )

    response = await llm.complete(
        messages=history + [{"role": "user", "content": text}],
        system=system,
        max_tokens=200,
    )
    await store.add_message(sender_phone, "assistant", response)
    return response


async def _build_context(sender_phone: str, store) -> list[dict]:
    """Build conversation context from recent messages."""
    history = await store.get_history(sender_phone, limit=10)
    return [{"role": m.role, "content": m.content} for m in history]
