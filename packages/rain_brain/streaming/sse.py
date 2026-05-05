"""SSE (Server-Sent Events) helpers for Rain backend.

Follows Contract 2 streaming envelope format.
"""

import json
from typing import Any
from rain_brain.providers.base import ChatChunk


def to_sse(chunk: ChatChunk) -> str:
    """Convert a ChatChunk to SSE format: 'data: <json>\n\n'."""
    return f"data: {chunk.model_dump_json()}\n\n"


def sse_error(code: str, message: str) -> str:
    """Create an SSE error chunk."""
    chunk = ChatChunk(
        type="error",
        data={"code": code, "message": message},
    )
    return to_sse(chunk)


def sse_done(usage: dict[str, Any]) -> str:
    """Create an SSE done chunk with usage stats."""
    chunk = ChatChunk(
        type="done",
        data=usage,
    )
    return to_sse(chunk)


def sse_token(content: str) -> str:
    """Create an SSE token chunk."""
    chunk = ChatChunk(
        type="token",
        data=content,
    )
    return to_sse(chunk)