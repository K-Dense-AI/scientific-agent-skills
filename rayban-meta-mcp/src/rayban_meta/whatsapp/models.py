"""Pydantic models for WhatsApp Cloud API webhook payloads."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── Incoming webhook models ──


class WhatsAppProfile(BaseModel):
    name: str = ""


class WhatsAppContact(BaseModel):
    profile: WhatsAppProfile = WhatsAppProfile()
    wa_id: str = ""


class WhatsAppTextMessage(BaseModel):
    body: str = ""


class WhatsAppAudioMessage(BaseModel):
    id: str = ""
    mime_type: str = ""


class WhatsAppImageMessage(BaseModel):
    id: str = ""
    mime_type: str = ""
    caption: str | None = None


class WhatsAppMessage(BaseModel):
    """A single incoming WhatsApp message."""
    from_: str = Field("", alias="from")
    id: str = ""
    timestamp: str = ""
    type: str = ""  # "text", "audio", "image", "video", etc.
    text: WhatsAppTextMessage | None = None
    audio: WhatsAppAudioMessage | None = None
    image: WhatsAppImageMessage | None = None

    model_config = {"populate_by_name": True}


class WhatsAppMetadata(BaseModel):
    display_phone_number: str = ""
    phone_number_id: str = ""


class WhatsAppValue(BaseModel):
    messaging_product: str = ""
    metadata: WhatsAppMetadata = WhatsAppMetadata()
    contacts: list[WhatsAppContact] = []
    messages: list[WhatsAppMessage] = []


class WhatsAppChange(BaseModel):
    value: WhatsAppValue = WhatsAppValue()
    field: str = ""


class WhatsAppEntry(BaseModel):
    id: str = ""
    changes: list[WhatsAppChange] = []


class WhatsAppWebhookPayload(BaseModel):
    object: str = ""
    entry: list[WhatsAppEntry] = []
