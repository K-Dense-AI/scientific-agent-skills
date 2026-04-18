"""WhatsApp Cloud API webhook – verification + message receipt."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Query, Request
from fastapi.responses import PlainTextResponse

from rayban_meta.config import settings
from rayban_meta.whatsapp.models import WhatsAppWebhookPayload

logger = logging.getLogger(__name__)
router = APIRouter(tags=["whatsapp"])


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
    hub_challenge: str = Query("", alias="hub.challenge"),
):
    """Meta sends a GET to verify the webhook URL."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_webhook_verify_token:
        logger.info("WhatsApp webhook verified successfully")
        return PlainTextResponse(hub_challenge)
    logger.warning("Webhook verification failed: bad token")
    return PlainTextResponse("Forbidden", status_code=403)


@router.post("/webhook")
async def receive_message(request: Request, bg: BackgroundTasks):
    """Receive incoming WhatsApp messages – return 200 fast, process async."""
    body = await request.json()

    # WhatsApp sends "whatsapp_business_account" as the object type
    if body.get("object") != "whatsapp_business_account":
        return {"status": "ignored"}

    payload = WhatsAppWebhookPayload.model_validate(body)

    for entry in payload.entry:
        for change in entry.changes:
            if change.field != "messages":
                continue
            for message in change.value.messages:
                bg.add_task(
                    _process_message,
                    request.app,
                    message.from_,
                    message.model_dump(by_alias=True),
                )

    return {"status": "ok"}


async def _process_message(app, sender_phone: str, raw_message: dict):
    """Background task – import here to avoid circular deps."""
    from rayban_meta.whatsapp.message_router import handle_message

    try:
        await handle_message(app, sender_phone, raw_message)
    except Exception:
        logger.exception("Error processing message from %s", sender_phone)
