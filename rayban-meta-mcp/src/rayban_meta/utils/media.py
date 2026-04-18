"""Media download and temp-file helpers."""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path


def bytes_to_base64(data: bytes, mime_type: str = "image/jpeg") -> str:
    """Encode raw bytes as a data URI suitable for LLM vision APIs."""
    b64 = base64.b64encode(data).decode()
    return f"data:{mime_type};base64,{b64}"


def save_temp(data: bytes, suffix: str = ".jpg") -> Path:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        return Path(f.name)
