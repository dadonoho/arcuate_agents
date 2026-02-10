"""Embedding generation using Anthropic's Voyager or a local model via ChromaDB defaults."""

from __future__ import annotations

import hashlib


def content_hash(text: str) -> str:
    """Generate a deterministic ID for a piece of content."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def chunk_text(text: str, max_chars: int = 2000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks for embedding.

    Uses paragraph boundaries when possible, falls back to character splitting.
    """
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    paragraphs = text.split("\n\n")

    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                # Keep overlap from end of current chunk
                current_chunk = current_chunk[-overlap:] + "\n\n" + para
            else:
                # Single paragraph too long — hard split
                for i in range(0, len(para), max_chars - overlap):
                    chunks.append(para[i : i + max_chars])
                current_chunk = ""
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks
