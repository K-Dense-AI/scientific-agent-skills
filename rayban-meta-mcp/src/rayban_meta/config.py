"""Centralized configuration loaded from environment / .env file."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── WhatsApp Cloud API ──
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_webhook_verify_token: str = "my-secret-token"
    whatsapp_recipient_phone: str = ""  # Your phone number (e.g. +40722889321)

    # ── LLM ──
    llm_default_provider: Literal["claude", "openai", "gemini"] = "gemini"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_gemini_api_key: str = ""

    # ── Transcription ──
    transcription_provider: Literal["openai", "groq", "deepgram"] = "openai"
    groq_api_key: str = ""
    deepgram_api_key: str = ""

    # ── Tools ──
    serper_api_key: str = ""
    google_calendar_credentials: str = ""
    notion_integration_secret: str = ""
    notion_database_id: str = ""

    # ── Storage ──
    database_path: str = "data/rayban.db"

    # ── Server ──
    mcp_server_port: int = 8080

    # ── TTS ──
    tts_enabled: bool = False
    tts_provider: Literal["openai", "elevenlabs"] = "openai"
    elevenlabs_api_key: str = ""


settings = Settings()
