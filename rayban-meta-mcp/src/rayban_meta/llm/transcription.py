"""Voice-to-text transcription via Whisper / Groq / Deepgram."""

from __future__ import annotations

import logging

from rayban_meta.config import settings
from rayban_meta.utils.audio import ogg_bytes_to_file

logger = logging.getLogger(__name__)


async def transcribe(audio_bytes: bytes) -> str:
    """Transcribe audio bytes (OGG/Opus from WhatsApp) to text."""
    provider = settings.transcription_provider

    if provider == "openai":
        return await _transcribe_openai(audio_bytes)
    elif provider == "groq":
        return await _transcribe_groq(audio_bytes)
    elif provider == "deepgram":
        return await _transcribe_deepgram(audio_bytes)
    else:
        raise ValueError(f"Unknown transcription provider: {provider}")


async def _transcribe_openai(audio_bytes: bytes) -> str:
    import openai

    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    tmp = ogg_bytes_to_file(audio_bytes)
    try:
        with open(tmp, "rb") as f:
            resp = await client.audio.transcriptions.create(model="whisper-1", file=f)
        return resp.text
    finally:
        tmp.unlink(missing_ok=True)


async def _transcribe_groq(audio_bytes: bytes) -> str:
    import httpx

    tmp = ogg_bytes_to_file(audio_bytes)
    try:
        async with httpx.AsyncClient() as http:
            with open(tmp, "rb") as f:
                resp = await http.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                    files={"file": ("audio.ogg", f, "audio/ogg")},
                    data={"model": "whisper-large-v3"},
                    timeout=30.0,
                )
            resp.raise_for_status()
            return resp.json()["text"]
    finally:
        tmp.unlink(missing_ok=True)


async def _transcribe_deepgram(audio_bytes: bytes) -> str:
    import httpx

    async with httpx.AsyncClient() as http:
        resp = await http.post(
            "https://api.deepgram.com/v1/listen?model=nova-2",
            headers={
                "Authorization": f"Token {settings.deepgram_api_key}",
                "Content-Type": "audio/ogg",
            },
            content=audio_bytes,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["results"]["channels"][0]["alternatives"][0]["transcript"]
