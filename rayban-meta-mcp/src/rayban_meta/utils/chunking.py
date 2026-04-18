"""Chunk long text for the glasses 15-word display limit."""

from __future__ import annotations

MAX_WORDS_PER_CHUNK = 14  # leave margin under 15


def chunk_for_glasses(text: str, max_words: int = MAX_WORDS_PER_CHUNK) -> list[str]:
    """Split *text* into chunks of at most *max_words* words.

    Tries to break on sentence boundaries when possible.
    """
    if not text.strip():
        return [text]

    sentences = _split_sentences(text)
    chunks: list[str] = []
    current: list[str] = []
    word_count = 0

    for sentence in sentences:
        words = sentence.split()
        if word_count + len(words) > max_words and current:
            chunks.append(" ".join(current))
            current = []
            word_count = 0

        # If a single sentence is longer than max_words, hard-split it
        if len(words) > max_words:
            for i in range(0, len(words), max_words):
                part = words[i : i + max_words]
                if current:
                    combined = current + part
                    if len(combined) <= max_words:
                        current = combined
                        word_count = len(current)
                        continue
                    chunks.append(" ".join(current))
                    current = []
                    word_count = 0
                chunks.append(" ".join(part))
            continue

        current.extend(words)
        word_count += len(words)

    if current:
        chunks.append(" ".join(current))

    return chunks or [text]


def _split_sentences(text: str) -> list[str]:
    """Naive sentence splitter."""
    import re

    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]
