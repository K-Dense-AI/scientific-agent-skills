"""Audio format helpers – OGG/Opus → WAV conversion."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path


def ogg_to_wav(ogg_bytes: bytes) -> bytes:
    """Convert OGG/Opus audio to WAV using pydub (requires ffmpeg)."""
    from pydub import AudioSegment

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(ogg_bytes)
        tmp_path = Path(tmp.name)

    try:
        audio = AudioSegment.from_ogg(str(tmp_path))
        buf = io.BytesIO()
        audio.export(buf, format="wav")
        return buf.getvalue()
    finally:
        tmp_path.unlink(missing_ok=True)


def ogg_bytes_to_file(ogg_bytes: bytes) -> Path:
    """Write OGG bytes to a temp file and return the path."""
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(ogg_bytes)
        return Path(tmp.name)
