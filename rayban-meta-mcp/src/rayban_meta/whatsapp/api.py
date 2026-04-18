"""WhatsApp Cloud API client – send messages, download media."""

from __future__ import annotations

import asyncio
import logging

import httpx

from rayban_meta.config import settings
from rayban_meta.utils.chunking import chunk_for_glasses

logger = logging.getLogger(__name__)

GRAPH_URL = "https://graph.facebook.com/v22.0"


class WhatsAppClient:
    """Async wrapper around the WhatsApp Cloud API."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
        )

    # ── Sending ──────────────────────────────────────────────

    async def send_text(self, recipient_phone: str, text: str) -> None:
        """Send a text message, auto-chunking for the glasses display."""
        chunks = chunk_for_glasses(text)
        for i, chunk in enumerate(chunks):
            await self._send_raw_text(recipient_phone, chunk)
            if i < len(chunks) - 1:
                await asyncio.sleep(1.5)

    async def _send_raw_text(self, recipient_phone: str, text: str) -> dict:
        url = f"{GRAPH_URL}/{settings.whatsapp_phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        resp = await self._http.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    async def send_typing_on(self, recipient_phone: str) -> None:
        """No direct typing indicator in WhatsApp Cloud API – noop."""
        pass

    # ── Media download (2-step) ──────────────────────────────

    async def download_media(self, media_id: str) -> bytes:
        """Download media: first get URL from media_id, then download bytes."""
        # Step 1: get media URL
        url = f"{GRAPH_URL}/{media_id}"
        resp = await self._http.get(url)
        resp.raise_for_status()
        media_url = resp.json().get("url", "")

        if not media_url:
            raise ValueError(f"No URL returned for media_id {media_id}")

        # Step 2: download the actual file (with auth header)
        resp = await self._http.get(media_url)
        resp.raise_for_status()
        return resp.content

    # ── Mark as read ─────────────────────────────────────────

    async def mark_as_read(self, message_id: str) -> None:
        url = f"{GRAPH_URL}/{settings.whatsapp_phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        try:
            await self._http.post(url, json=payload)
        except Exception:
            logger.warning("Failed to mark message %s as read", message_id)

    async def close(self) -> None:
        await self._http.aclose()
